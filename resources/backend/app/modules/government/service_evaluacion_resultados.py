from decimal import Decimal
from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.government.models import (
    GovernmentProcurementCommitteeMember,
    GovernmentProcurementEvalContribution,
    GovernmentProcurementEvalCriterion,
    GovernmentProcurementEvalResult,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentProcurementOpeningOffer,
)
from app.modules.government.service_evaluacion import _criterios, _doc_soporte, _matriz, obtener_evaluacion
from app.modules.government.service_expedientes import _auditar, _evento
from app.modules.government.service_identidad import _funcionario_del_actor, _politica_de
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio, instante_actual


def _err(campo: str, mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_EVAL_INVALID_BODY",
        message="Datos inválidos para la evaluación",
        status_code=422,
        field_errors={campo: [mensaje]},
    )


def _validar_matriz_y_oferta(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    oferta_id: str,
    criterio_id: str,
    matriz_version: int,
) -> tuple:
    matriz = _matriz(db, ctx.company_id, str(expediente.id))
    if matriz is None:
        raise NotFoundError("GOV_EVAL_MATRIX_NOT_FOUND", "No hay matriz de evaluación registrada")
    if matriz_version != matriz.version:
        raise ConflictError("GOV_EVAL_MATRIX_STALE", "La versión de la matriz no es la vigente")
    if matriz.estado != "BLOQUEADA":
        raise ConflictError("GOV_EVAL_MATRIX_NOT_BLOCKED", "La matriz debe estar bloqueada para evaluar")
    oferta = db.get(GovernmentProcurementOffer, oferta_id)
    if oferta is None or oferta.company_id != ctx.company_id or oferta.file_id != expediente.id:
        raise NotFoundError("GOV_EVAL_OFFER_NOT_FOUND", "Oferta no encontrada")
    abierta = (
        db.query(GovernmentProcurementOpeningOffer)
        .filter(
            GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
            GovernmentProcurementOpeningOffer.offer_id == oferta_id,
        )
        .one_or_none()
        is not None
    )
    if not abierta:
        raise ConflictError("GOV_OFFER_NOT_OPENED", "La oferta no está abierta")
    criterio = db.get(GovernmentProcurementEvalCriterion, criterio_id)
    if criterio is None or criterio.company_id != ctx.company_id or criterio.matrix_id != matriz.id:
        raise _err("criterio_id", "Criterio no pertenece a la matriz vigente")
    return matriz, oferta, criterio


def _validar_miembro(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    miembro_id: str,
    permitir_secretario: bool = False,
) -> GovernmentProcurementCommitteeMember:
    miembro = db.get(GovernmentProcurementCommitteeMember, miembro_id)
    if miembro is None or miembro.company_id != ctx.company_id or miembro.committee_id != expediente.committee_id:
        raise KontrolError(
            code="GOV_EVAL_NOT_MEMBER",
            message="El miembro no pertenece a la comisión vinculada",
            status_code=403,
        )
    if not permitir_secretario and miembro.funcion != "MIEMBRO":
        raise _err("miembro_id", "Solo los miembros con función MIEMBRO pueden registrar aportes")
    return miembro


def _validar_escala(criterio: GovernmentProcurementEvalCriterion, puntaje: Decimal | None, cumple: bool | None) -> None:
    if criterio.escala == "PUNTAJE":
        if criterio.puntaje_maximo is None:
            raise _err("puntaje", "Se requiere puntaje máximo para criterio PUNTAJE")
        if puntaje is None:
            raise _err("puntaje", "Se requiere puntaje para criterio PUNTAJE")
        if not (0 <= puntaje <= criterio.puntaje_maximo):
            raise _err("puntaje", "Puntaje fuera del rango permitido")
        if cumple is not None:
            raise _err("cumple", "No se admite cumple para criterio PUNTAJE")
    else:
        if cumple is None:
            raise _err("cumple", "Se requiere cumple para criterio CUMPLE")
        if puntaje is not None:
            raise _err("puntaje", "No se admite puntaje para criterio CUMPLE")


def _get_expediente(
    db: Session,
    ctx: CompanyContext,
    expediente_id: str,
    for_update: bool = False,
) -> GovernmentProcurementFile:
    query = db.query(GovernmentProcurementFile).filter(
        GovernmentProcurementFile.company_id == ctx.company_id,
        GovernmentProcurementFile.id == expediente_id,
    )
    if for_update:
        query = query.with_for_update()
    expediente = query.one_or_none()
    if expediente is None:
        raise NotFoundError("GOV_NOT_FOUND", "Expediente no encontrado")
    if expediente.evaluacion_concluida_en is not None:
        raise ConflictError("GOV_EVALUATION_CONCLUDED", "La evaluación ya fue concluida")
    return expediente


def _validar_identidad(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    miembro: GovernmentProcurementCommitteeMember,
    permitir_secretario: bool = False,
) -> None:
    politica = _politica_de(db, ctx)
    if politica is None or politica.exige_identidad is False:
        return
    official_id = _funcionario_del_actor(db, ctx)
    if official_id is None:
        raise PermissionDeniedError(
            code="GOV_EVAL_IDENTITY_REQUIRED",
            message="La cuenta debe estar vinculada a un funcionario para registrar evaluaciones",
        )
    if official_id != miembro.official_id:
        raise KontrolError(
            code="GOV_EVAL_NOT_MEMBER",
            message="La identidad del actor no corresponde al miembro indicado",
            status_code=403,
        )
    if not permitir_secretario and miembro.funcion != "MIEMBRO":
        raise _err("miembro_id", "Solo los miembros con función MIEMBRO pueden registrar aportes")


_T = TypeVar("_T", GovernmentProcurementEvalContribution, GovernmentProcurementEvalResult)


def _cadena_vigente(filas: list[_T]) -> _T | None:
    reemplazadas = {f.reemplaza_id for f in filas if f.reemplaza_id is not None}
    raices = [f for f in filas if f.id not in reemplazadas]
    if len(raices) != 1:
        return None
    return raices[0]


def _validar_evidencia(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, evidencia_documento_id: str | None) -> tuple[str | None, str | None]:
    if not evidencia_documento_id:
        return None, None
    _, version, _ = _doc_soporte(
        db,
        ctx.company_id,
        evidencia_documento_id,
        "evidencia_documento_id",
        expediente_id=str(expediente.id),
    )
    return evidencia_documento_id, str(version.id)


def registrar_aporte(db: Session, ctx: CompanyContext, user: User, expediente_id: str, cuerpo: dict) -> dict:
    evaluar_antes_de_actuar(db, ctx, "PROC03_EVALUAR", "GovernmentProcurementFile", str(expediente_id))
    expediente = _get_expediente(db, ctx, expediente_id, for_update=True)

    oferta_id = cuerpo.get("oferta_id")
    criterio_id = cuerpo.get("criterio_id")
    miembro_id = cuerpo.get("miembro_id")
    matriz_version = cuerpo.get("matriz_version")
    puntaje = cuerpo.get("puntaje")
    cumple = cuerpo.get("cumple")
    observacion = cuerpo.get("observacion")
    evidencia_documento_id = cuerpo.get("evidencia_documento_id")

    if not oferta_id or not criterio_id or not miembro_id or matriz_version is None:
        raise _err("body", "Faltan campos requeridos")

    matriz, oferta, criterio = _validar_matriz_y_oferta(
        db, ctx, expediente, oferta_id, criterio_id, int(matriz_version)
    )
    miembro = _validar_miembro(db, ctx, expediente, miembro_id)
    _validar_identidad(db, ctx, expediente, miembro)
    _validar_escala(criterio, Decimal(str(puntaje)) if puntaje is not None else None, cumple)

    evidencia_document_id, evidencia_version_id = _validar_evidencia(db, ctx, expediente, evidencia_documento_id)

    filas_cadena = (
        db.query(GovernmentProcurementEvalContribution)
        .filter(
            GovernmentProcurementEvalContribution.company_id == ctx.company_id,
            GovernmentProcurementEvalContribution.offer_id == oferta_id,
            GovernmentProcurementEvalContribution.criterion_id == criterio_id,
            GovernmentProcurementEvalContribution.member_id == miembro_id,
        )
        .all()
    )
    vigente = _cadena_vigente(filas_cadena)

    nuevo = GovernmentProcurementEvalContribution(
        company_id=ctx.company_id,
        offer_id=oferta_id,
        criterion_id=criterio_id,
        matrix_id=matriz.id,
        matrix_version=matriz.version,
        member_id=miembro_id,
        official_id=miembro.official_id,
        puntaje=Decimal(str(puntaje)) if puntaje is not None else None,
        cumple=cumple,
        observacion=observacion,
        evidencia_document_id=evidencia_document_id,
        evidencia_version_id=evidencia_version_id,
        created_by=user.id,
        reemplaza_id=str(vigente.id) if vigente else None,
    )
    db.add(nuevo)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_CONTRIBUTION_RECORDED",
        expediente_id=str(expediente.id),
        after={
            "offer_id": oferta_id,
            "criterion_id": criterio_id,
            "aspecto": criterio.aspecto,
            "matriz_version": matriz.version,
            "reemplaza_id": str(vigente.id) if vigente else None,
        },
    )
    return obtener_evaluacion(db, ctx, user, expediente_id)


def registrar_resultado(db: Session, ctx: CompanyContext, user: User, expediente_id: str, cuerpo: dict) -> dict:
    evaluar_antes_de_actuar(db, ctx, "PROC03_EVALUAR", "GovernmentProcurementFile", str(expediente_id))
    expediente = _get_expediente(db, ctx, expediente_id, for_update=True)

    oferta_id = cuerpo.get("oferta_id")
    criterio_id = cuerpo.get("criterio_id")
    miembro_id = cuerpo.get("miembro_id")
    matriz_version = cuerpo.get("matriz_version")
    puntaje = cuerpo.get("puntaje")
    cumple = cuerpo.get("cumple")
    observacion = cuerpo.get("observacion")
    evidencia_documento_id = cuerpo.get("evidencia_documento_id")

    if not oferta_id or not criterio_id or not miembro_id or matriz_version is None:
        raise _err("body", "Faltan campos requeridos")

    matriz, oferta, criterio = _validar_matriz_y_oferta(
        db, ctx, expediente, oferta_id, criterio_id, int(matriz_version)
    )
    miembro = _validar_miembro(db, ctx, expediente, miembro_id, permitir_secretario=True)
    if miembro.funcion not in ("MIEMBRO", "SECRETARIO"):
        raise _err("miembro_id", "Solo MIEMBRO o SECRETARIO pueden registrar resultados")
    _validar_identidad(db, ctx, expediente, miembro, permitir_secretario=True)
    _validar_escala(criterio, Decimal(str(puntaje)) if puntaje is not None else None, cumple)

    evidencia_document_id, evidencia_version_id = _validar_evidencia(db, ctx, expediente, evidencia_documento_id)

    filas_cadena = (
        db.query(GovernmentProcurementEvalResult)
        .filter(
            GovernmentProcurementEvalResult.company_id == ctx.company_id,
            GovernmentProcurementEvalResult.offer_id == oferta_id,
            GovernmentProcurementEvalResult.criterion_id == criterio_id,
        )
        .all()
    )
    vigente = _cadena_vigente(filas_cadena)

    nuevo = GovernmentProcurementEvalResult(
        company_id=ctx.company_id,
        offer_id=oferta_id,
        criterion_id=criterio_id,
        matrix_id=matriz.id,
        matrix_version=matriz.version,
        member_id=miembro_id,
        official_id=miembro.official_id,
        puntaje=Decimal(str(puntaje)) if puntaje is not None else None,
        cumple=cumple,
        observacion=observacion,
        evidencia_document_id=evidencia_document_id,
        evidencia_version_id=evidencia_version_id,
        created_by=user.id,
        reemplaza_id=str(vigente.id) if vigente else None,
    )
    db.add(nuevo)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_RESULT_RECORDED",
        expediente_id=str(expediente.id),
        after={
            "offer_id": oferta_id,
            "criterion_id": criterio_id,
            "aspecto": criterio.aspecto,
            "matriz_version": matriz.version,
            "reemplaza_id": str(vigente.id) if vigente else None,
        },
    )
    return obtener_evaluacion(db, ctx, user, expediente_id)


def concluir_evaluacion(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None) -> dict:
    if version is None:
        raise KontrolError(
            code="GOV_EVAL_IF_MATCH_REQUIRED",
            message="Se requiere If-Match con la versión del expediente",
            status_code=428,
        )
    expediente = _get_expediente(db, ctx, expediente_id, for_update=True)
    if expediente.version != version:
        raise ConflictError("GOV_EVAL_VERSION_STALE", "La versión del expediente no es la vigente")
    matriz = _matriz(db, ctx.company_id, str(expediente.id))
    if matriz is None or matriz.estado != "BLOQUEADA":
        raise KontrolError(
            code="GOV_EVAL_MATRIX_NOT_READY",
            message="La matriz debe estar bloqueada",
            status_code=422,
        )
    criterios = _criterios(db, ctx.company_id, str(matriz.id))
    ofertas = (
        db.query(GovernmentProcurementOffer)
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente_id,
        )
        .all()
    )
    ofertas_abiertas = [
        o
        for o in ofertas
        if db.query(GovernmentProcurementOpeningOffer)
        .filter(
            GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
            GovernmentProcurementOpeningOffer.offer_id == o.id,
        )
        .one_or_none()
        is not None
    ]
    if not ofertas_abiertas:
        raise KontrolError(
            code="GOV_EVAL_NO_OPEN_OFFERS",
            message="No hay ofertas abiertas para concluir la evaluación",
            status_code=422,
        )
    faltantes: dict[str, list[str]] = {}
    for oferta in ofertas_abiertas:
        resultados = (
            db.query(GovernmentProcurementEvalResult)
            .filter(
                GovernmentProcurementEvalResult.company_id == ctx.company_id,
                GovernmentProcurementEvalResult.offer_id == oferta.id,
            )
            .all()
        )
        resultados_ids = {r.criterion_id for r in resultados}
        faltantes_oferta = [str(c.id) for c in criterios if str(c.id) not in resultados_ids]
        if faltantes_oferta:
            faltantes[str(oferta.id)] = faltantes_oferta
    if faltantes:
        raise KontrolError(
            code="GOV_EVAL_RESULTS_INCOMPLETE",
            message=f"Faltan resultados: {sum(len(v) for v in faltantes.values())} criterio(s)",
            status_code=422,
        )
    ahora = instante_actual()
    expediente.evaluacion_concluida_en = ahora
    expediente.evaluacion_concluida_por = str(user.id)
    expediente.version += 1
    db.add(expediente)
    db.flush()
    _evento(
        db,
        ctx,
        expediente,
        "EVALUACION",
        hoy_de_negocio(),
        f"Evaluación concluida: {len(ofertas_abiertas)} oferta(s)",
    )
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVALUATION_CONCLUDED",
        expediente_id=str(expediente.id),
        after={"ofertas": len(ofertas_abiertas)},
    )
    return obtener_evaluacion(db, ctx, user, expediente_id)
