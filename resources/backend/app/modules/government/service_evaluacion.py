from __future__ import annotations

from datetime import UTC

from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.documents.service import congelar_vinculo, documento_sellado, liberar_sello
from app.modules.government.models import (
    GovernmentOfficial,
    GovernmentProcurementCommittee,
    GovernmentProcurementCommitteeMember,
    GovernmentProcurementEvalContribution,
    GovernmentProcurementEvalCriterion,
    GovernmentProcurementEvalMatrix,
    GovernmentProcurementEvalResult,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentProcurementOfferDocument,
    GovernmentProcurementOpening,
    GovernmentProcurementOpeningAttendee,
    GovernmentProcurementOpeningOffer,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_comisiones import situacion_de
from app.modules.government.service_expedientes import (
    _abierto,
    _auditar,
    _cargar,
    _err,
    _evento,
    _para_escribir,
)
from app.modules.government.service_identidad import _funcionario_del_actor, _politica_de
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.service_sod_funciones import verificar_antes_de_asumir_funcion
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio, instante_actual

_ASPECTOS = ("TECNICO", "ECONOMICO", "LEGAL")


def _matriz(db: Session, company_id: str, file_id: str) -> GovernmentProcurementEvalMatrix | None:
    return (
        db.query(GovernmentProcurementEvalMatrix)
        .filter(
            GovernmentProcurementEvalMatrix.company_id == company_id,
            GovernmentProcurementEvalMatrix.file_id == file_id,
        )
        .one_or_none()
    )


def _criterios(db: Session, company_id: str, matrix_id: str) -> list[GovernmentProcurementEvalCriterion]:
    return (
        db.query(GovernmentProcurementEvalCriterion)
        .filter(
            GovernmentProcurementEvalCriterion.company_id == company_id,
            GovernmentProcurementEvalCriterion.matrix_id == matrix_id,
        )
        .order_by(GovernmentProcurementEvalCriterion.aspecto, GovernmentProcurementEvalCriterion.orden)
        .all()
    )


def _doc_soporte(db: Session, company_id: str, documento_id: str, campo: str, *, expediente_id: str) -> tuple[Document, DocumentVersion, DocumentLink]:
    doc = db.get(Document, documento_id)
    if doc is None or doc.company_id != company_id:
        raise _err(campo, "El documento no existe")
    if doc.status not in ("DRAFT", "ACTIVE"):
        raise _err(campo, "El documento debe estar en borrador o activo")
    if doc.current_version_id is None:
        raise _err(campo, "El documento no tiene versión vigente")
    version = db.get(DocumentVersion, doc.current_version_id)
    if version is None:
        raise _err(campo, "El documento no tiene versión vigente")
    if documento_sellado(db, str(doc.id)):
        raise _err(campo, "El documento no puede estar sellado")
    vinculo = (
        db.query(DocumentLink)
        .filter(
            DocumentLink.document_id == doc.id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == expediente_id,
        )
        .one_or_none()
    )
    if vinculo is None:
        raise _err(campo, "El documento debe estar vinculado al expediente")
    return doc, version, vinculo


def _miembros_comision(db: Session, company_id: str, committee_id: str) -> list[GovernmentProcurementCommitteeMember]:
    hoy = hoy_de_negocio()
    _ = hoy
    return (
        db.query(GovernmentProcurementCommitteeMember)
        .filter(
            GovernmentProcurementCommitteeMember.company_id == company_id,
            GovernmentProcurementCommitteeMember.committee_id == committee_id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
        .all()
    )


def crear_matriz(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, cuerpo: dict) -> dict:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    if _matriz(db, ctx.company_id, str(expediente.id)) is not None:
        raise ConflictError(code="GOV_EVAL_MATRIX_EXISTS", message="Ya existe una matriz de evaluación")
    doc, doc_version, vinculo = _doc_soporte(
        db,
        ctx.company_id,
        cuerpo["pliego_documento_id"],
        "pliego_documento_id",
        expediente_id=str(expediente.id),
    )
    primera_oferta = (
        db.query(GovernmentProcurementOffer)
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOffer.recibida_en)
        .first()
    )
    transcripcion = False
    if primera_oferta is not None:
        if vinculo.created_at >= primera_oferta.recibida_en:
            raise _err("pliego_documento_id", "El pliego debe estar incorporado antes de la primera oferta")
        transcripcion = True
    congelar_vinculo(db, link=vinculo, version_id=str(doc_version.id), actor=user)
    matriz = GovernmentProcurementEvalMatrix(
        id=str(__import__("uuid").uuid4()),
        company_id=ctx.company_id,
        file_id=expediente.id,
        estado="BORRADOR",
        pliego_document_id=doc.id,
        pliego_version_id=doc_version.id,
        pliego_sha256=doc_version.sha256,
        transcripcion=transcripcion,
        version=1,
        created_by=user.id,
    )
    db.add(matriz)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_MATRIX_CREATED",
        expediente_id=str(expediente.id),
        after=_estado_evaluacion(db, ctx, expediente, user),
    )
    return _estado_evaluacion(db, ctx, expediente, user)


def anadir_criterio(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, cuerpo: dict) -> dict:
    matriz = db.query(GovernmentProcurementEvalMatrix).filter(
        GovernmentProcurementEvalMatrix.company_id == ctx.company_id,
        GovernmentProcurementEvalMatrix.file_id == expediente_id,
    ).one_or_none()
    if matriz is None:
        raise NotFoundError("GOV_EVAL_MATRIX_NOT_FOUND", "Matriz no encontrada")
    if version is None:
        raise KontrolError(code="GOV_EVAL_MATRIX_IF_MATCH_REQUIRED", message="Se requiere la version de la matriz", status_code=428)
    if matriz.version != version:
        raise ConflictError(code="GOV_EVAL_MATRIX_STALE", message="La matriz fue modificada por otro usuario")
    if matriz.estado != "BORRADOR":
        raise ConflictError(code="GOV_EVAL_MATRIX_LOCKED", message="La matriz está bloqueada")
    tiene_ofertas = (
        db.query(GovernmentProcurementOffer)
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente_id,
        )
        .first()
        is not None
    )
    if tiene_ofertas and not matriz.transcripcion:
        raise ConflictError(
            code="GOV_EVAL_MATRIX_LOCKED",
            message="Tras la primera oferta solo puede bloquearse la matriz (LCP art. 95)",
        )
    if cuerpo["aspecto"] not in _ASPECTOS:
        raise _err("aspecto", "Aspecto inválido")
    if cuerpo["escala"] not in ("PUNTAJE", "CUMPLE"):
        raise _err("escala", "Escala inválida")
    if cuerpo["escala"] == "PUNTAJE" and (cuerpo.get("puntaje_maximo") is None or cuerpo["puntaje_maximo"] <= 0):
        raise _err("puntaje_maximo", "La escala PUNTAJE exige un puntaje máximo mayor a cero")
    if cuerpo["escala"] == "CUMPLE" and cuerpo.get("puntaje_maximo") is not None:
        raise _err("puntaje_maximo", "La escala CUMPLE no admite puntaje máximo")
    if cuerpo.get("ponderacion") is not None and cuerpo["ponderacion"] <= 0:
        raise _err("ponderacion", "La ponderación debe ser mayor a cero")
    criterio = GovernmentProcurementEvalCriterion(
        id=str(__import__("uuid").uuid4()),
        company_id=ctx.company_id,
        matrix_id=matriz.id,
        aspecto=cuerpo["aspecto"],
        orden=cuerpo["orden"],
        nombre=cuerpo["nombre"],
        descripcion=cuerpo.get("descripcion"),
        escala=cuerpo["escala"],
        puntaje_maximo=cuerpo.get("puntaje_maximo"),
        ponderacion=cuerpo.get("ponderacion"),
        created_by=user.id,
    )
    db.add(criterio)
    matriz.version += 1
    db.add(matriz)
    db.flush()
    expediente = _cargar(db, ctx, expediente_id)
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_CRITERION_ADDED",
        expediente_id=str(expediente.id),
        after={
            "aspecto": criterio.aspecto,
            "criterio": criterio.nombre,
            "version": expediente.version,
        },
    )
    return _estado_evaluacion(db, ctx, expediente, user)


def quitar_criterio(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, criterio_id: str) -> dict:
    matriz = db.query(GovernmentProcurementEvalMatrix).filter(
        GovernmentProcurementEvalMatrix.company_id == ctx.company_id,
        GovernmentProcurementEvalMatrix.file_id == expediente_id,
    ).one_or_none()
    if matriz is None:
        raise NotFoundError("GOV_EVAL_MATRIX_NOT_FOUND", "Matriz no encontrada")
    if version is None:
        raise KontrolError(code="GOV_EVAL_MATRIX_IF_MATCH_REQUIRED", message="Se requiere la version de la matriz", status_code=428)
    if matriz.version != version:
        raise ConflictError(code="GOV_EVAL_MATRIX_STALE", message="La matriz fue modificada por otro usuario")
    if matriz.estado != "BORRADOR":
        raise ConflictError(code="GOV_EVAL_MATRIX_LOCKED", message="La matriz está bloqueada")
    tiene_ofertas = (
        db.query(GovernmentProcurementOffer)
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente_id,
        )
        .first()
        is not None
    )
    if tiene_ofertas and not matriz.transcripcion:
        raise ConflictError(
            code="GOV_EVAL_MATRIX_LOCKED",
            message="Tras la primera oferta solo puede bloquearse la matriz (LCP art. 95)",
        )
    criterio = db.get(GovernmentProcurementEvalCriterion, criterio_id)
    if criterio is None or criterio.matrix_id != matriz.id or criterio.company_id != ctx.company_id:
        raise NotFoundError("GOV_EVAL_CRITERION_NOT_FOUND", "Criterio no encontrado")
    db.delete(criterio)
    matriz.version += 1
    db.add(matriz)
    db.flush()
    expediente = _cargar(db, ctx, expediente_id)
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_CRITERION_REMOVED",
        expediente_id=str(expediente.id),
        after={"aspecto": criterio.aspecto, "criterio": criterio.nombre, "version": expediente.version},
    )
    return _estado_evaluacion(db, ctx, expediente, user)


def bloquear_matriz(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None) -> dict:
    matriz = db.query(GovernmentProcurementEvalMatrix).filter(
        GovernmentProcurementEvalMatrix.company_id == ctx.company_id,
        GovernmentProcurementEvalMatrix.file_id == expediente_id,
    ).one_or_none()
    if matriz is None:
        raise NotFoundError("GOV_EVAL_MATRIX_NOT_FOUND", "Matriz no encontrada")
    if version is None:
        raise KontrolError(code="GOV_EVAL_MATRIX_IF_MATCH_REQUIRED", message="Se requiere la version de la matriz", status_code=428)
    if matriz.version != version:
        raise ConflictError(code="GOV_EVAL_MATRIX_STALE", message="La matriz fue modificada por otro usuario")
    if matriz.estado != "BORRADOR":
        raise ConflictError(code="GOV_EVAL_MATRIX_LOCKED", message="La matriz ya está bloqueada")
    criterios = _criterios(db, ctx.company_id, str(matriz.id))
    faltantes = [a for a in _ASPECTOS if not any(c.aspecto == a for c in criterios)]
    if faltantes:
        raise _err("criterios", f"Faltan criterios para los aspectos: {', '.join(faltantes)}")
    matriz.estado = "BLOQUEADA"
    matriz.locked_at = instante_actual()
    matriz.locked_by = str(user.id)
    matriz.version += 1
    db.add(matriz)
    db.flush()
    expediente = _cargar(db, ctx, expediente_id)
    _evento(
        db,
        ctx,
        expediente,
        "EVALUACION",
        hoy_de_negocio(),
        "Matriz de evaluación bloqueada",
        detalle=f"Versión {matriz.version} de la matriz bloqueada",
    )
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_EVAL_MATRIX_LOCKED",
        expediente_id=str(expediente.id),
        after={"matriz": matriz.id, "version": expediente.version},
    )
    return _estado_evaluacion(db, ctx, expediente, user)


def abrir_ofertas(db: Session, ctx: CompanyContext, user: User, expediente_id: str, version: int | None, cuerpo: dict) -> dict:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    if expediente.recepcion_concluida_en is None:
        raise ConflictError(
            code="GOV_OPENING_RECEPTION_OPEN",
            message="La recepción de ofertas no ha concluido (LCP art. 93)",
        )
    if expediente.committee_id is None:
        raise _err("comision", "El expediente no tiene comisión vinculada")
    comision = db.get(GovernmentProcurementCommittee, expediente.committee_id)
    if comision is None or comision.company_id != ctx.company_id:
        raise _err("comision", "La comisión no existe")
    if situacion_de(comision, hoy_de_negocio()) != "EN_VIGOR":
        raise _err("comision", "La comisión no está vigente hoy")
    oferta_ids = cuerpo["oferta_ids"]
    if not oferta_ids:
        raise _err("oferta_ids", "Debe abrir al menos una oferta")
    if len(set(oferta_ids)) != len(oferta_ids):
        raise _err("oferta_ids", "No se permiten ofertas repetidas")
    ofertas = []
    for oid in oferta_ids:
        oferta = db.get(GovernmentProcurementOffer, oid)
        if oferta is None or oferta.company_id != ctx.company_id or oferta.file_id != expediente.id:
            raise _err("oferta_ids", "La oferta no pertenece al expediente")
        ya_abierta = (
            db.query(GovernmentProcurementOpeningOffer)
            .filter(
                GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
                GovernmentProcurementOpeningOffer.offer_id == oferta.id,
            )
            .one_or_none()
        )
        if ya_abierta is not None:
            raise ConflictError(code="GOV_OFFER_ALREADY_OPENED", message="La oferta ya fue abierta")
        ofertas.append(oferta)
    miembros = _miembros_comision(db, ctx.company_id, str(comision.id))
    miembro_ids = cuerpo["miembro_ids"]
    if not miembro_ids:
        raise _err("asistentes", "Debe indicar al menos un asistente")
    por_id = {m.id: m for m in miembros}
    for mid in miembro_ids:
        if mid not in por_id:
            raise _err("asistentes", "El asistente no pertenece a la comisión")
    verificar_antes_de_asumir_funcion(
        db,
        ctx,
        expediente,
        "EVALUADOR",
        user_ids=[ctx.user_id],
        official_ids=[por_id[mid].official_id for mid in miembro_ids],
    )
    principales = [m for m in miembros if m.funcion == "MIEMBRO" and m.condicion == "PRINCIPAL"]
    suplentes = [m for m in miembros if m.funcion == "MIEMBRO" and m.condicion == "SUPLENTE"]
    asistentes_con_voto = 0
    asistentes_registro = []
    for principal in principales:
        asiste_principal = principal.id in miembro_ids
        suplente_activo = next(
            (s for s in suplentes if s.suplente_de_id == principal.id and s.id in miembro_ids),
            None,
        )
        if asiste_principal or suplente_activo is not None:
            asistentes_con_voto += 1
            elegido = principal if asiste_principal else suplente_activo
            if elegido is not None:
                asistentes_registro.append(elegido)
    secretarios = [m for m in miembros if m.funcion == "SECRETARIO" and m.id in miembro_ids]
    for s in secretarios:
        asistentes_registro.append(s)
    miembros_con_voto = len(principales)
    quorum_requerido = miembros_con_voto // 2 + 1
    if asistentes_con_voto < quorum_requerido:
        raise _err("asistentes", f"Sin quórum: se requieren {quorum_requerido} de {miembros_con_voto} miembros con voto")
    politica = _politica_de(db, ctx)
    if politica is not None and politica.exige_identidad:
        official_id = _funcionario_del_actor(db, ctx)
        if official_id is None:
            raise PermissionDeniedError(
                code="GOV_EVAL_IDENTITY_REQUIRED",
                message="La cuenta debe estar vinculada a un funcionario para actuar en la apertura",
            )
        if official_id not in {m.official_id for m in asistentes_registro if m is not None}:
            raise PermissionDeniedError(
                code="GOV_OPENING_NOT_ATTENDEE",
                message="El funcionario de la cuenta debe estar entre los asistentes",
            )
    acta_doc, acta_version, acta_vinculo = _doc_soporte(
        db,
        ctx.company_id,
        cuerpo["acta_documento_id"],
        "acta_documento_id",
        expediente_id=str(expediente.id),
    )
    congelar_vinculo(db, link=acta_vinculo, version_id=str(acta_version.id), actor=user)
    abierta_en = cuerpo["abierta_en"]
    if abierta_en.tzinfo is None:
        abierta_en = abierta_en.replace(tzinfo=__import__("zoneinfo").ZoneInfo("America/Caracas"))
    if abierta_en > instante_actual():
        raise _err("abierta_en", "La fecha de apertura no puede ser futura")
    recepcion_concluida_en = expediente.recepcion_concluida_en
    if recepcion_concluida_en.tzinfo is None:
        recepcion_concluida_en = recepcion_concluida_en.replace(tzinfo=UTC)
    inicio_minuto_recepcion = recepcion_concluida_en.replace(second=0, microsecond=0)
    if abierta_en < inicio_minuto_recepcion:
        raise _err("abierta_en", "La fecha de apertura no puede ser anterior a la recepción concluida")
    evaluar_antes_de_actuar(db, ctx, "PROC03_ABRIR", "GovernmentProcurementFile", str(expediente.id))
    numero = (
        db.query(GovernmentProcurementOpening)
        .filter(
            GovernmentProcurementOpening.company_id == ctx.company_id,
            GovernmentProcurementOpening.file_id == expediente.id,
        )
        .count()
        + 1
    )
    referencia = f"A-{numero:02d}"
    apertura = GovernmentProcurementOpening(
        id=str(__import__("uuid").uuid4()),
        company_id=ctx.company_id,
        file_id=expediente.id,
        committee_id=comision.id,
        numero=numero,
        abierta_en=abierta_en,
        acta_document_id=acta_doc.id,
        acta_version_id=acta_version.id,
        acta_sha256=acta_version.sha256,
        observaciones=cuerpo.get("observaciones"),
        miembros_con_voto=miembros_con_voto,
        asistentes_con_voto=asistentes_con_voto,
        quorum_requerido=quorum_requerido,
        created_by=user.id,
    )
    db.add(apertura)
    db.flush()
    for miembro in asistentes_registro:
        db.add(
            GovernmentProcurementOpeningAttendee(
                id=str(__import__("uuid").uuid4()),
                company_id=ctx.company_id,
                opening_id=apertura.id,
                member_id=miembro.id,
                official_id=miembro.official_id,
                funcion=miembro.funcion,
                condicion=miembro.condicion,
                cuenta_voto=miembro.funcion == "MIEMBRO" and miembro.condicion == "PRINCIPAL",
                created_by=str(user.id),
            )
        )
    for oferta in ofertas:
        db.add(
            GovernmentProcurementOpeningOffer(
                id=str(__import__("uuid").uuid4()),
                company_id=ctx.company_id,
                opening_id=apertura.id,
                offer_id=oferta.id,
                created_by=user.id,
            )
        )
        oferta_docs = (
            db.query(GovernmentProcurementOfferDocument)
            .filter(
                GovernmentProcurementOfferDocument.company_id == ctx.company_id,
                GovernmentProcurementOfferDocument.offer_id == oferta.id,
            )
            .all()
        )
        for od in oferta_docs:
            if documento_sellado(db, od.document_id):
                liberar_sello(
                    db,
                    document_id=od.document_id,
                    actor_id=str(user.id),
                    motivo=f"Apertura {referencia} (LCP art. 93)",
                    resource_type="GovernmentProcurementOpening",
                    resource_id=str(apertura.id),
                )
    _evento(
        db,
        ctx,
        expediente,
        "APERTURA_OFERTA",
        hoy_de_negocio(),
        f"Apertura {referencia}: {len(ofertas)} oferta(s)",
        detalle=(
            f"Hora del acto en Caracas; "
            f"Asistentes con voto: {asistentes_con_voto}; "
            f"Quórum requerido: {quorum_requerido}; "
            f"Ofertas: {len(ofertas)}"
        ),
    )
    expediente.version += 1
    db.add(expediente)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_OFFERS_OPENED",
        expediente_id=str(expediente.id),
        after={
            "apertura": referencia,
            "ofertas": len(ofertas),
            "asistentes": asistentes_con_voto,
            "quorum": quorum_requerido,
            "version": expediente.version,
        },
    )
    return _estado_evaluacion(db, ctx, expediente, user)


def _estado_evaluacion(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile, user: User) -> dict:
    matriz = _matriz(db, ctx.company_id, str(expediente.id))
    criterios = _criterios(db, ctx.company_id, str(matriz.id)) if matriz else []
    aperturas_db = (
        db.query(GovernmentProcurementOpening)
        .filter(
            GovernmentProcurementOpening.company_id == ctx.company_id,
            GovernmentProcurementOpening.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOpening.numero)
        .all()
    )
    aperturas = []
    for ap in aperturas_db:
        asistentes = (
            db.query(GovernmentProcurementOpeningAttendee)
            .filter(
                GovernmentProcurementOpeningAttendee.company_id == ctx.company_id,
                GovernmentProcurementOpeningAttendee.opening_id == ap.id,
            )
            .all()
        )
        asistentes_out = []
        for a in asistentes:
            oficial = db.get(GovernmentOfficial, a.official_id)
            asistentes_out.append(
                {
                    "member_id": a.member_id,
                    "oficial": oficial.nombre if oficial else a.official_id,
                    "funcion": a.funcion,
                    "condicion": a.condicion,
                    "cuenta_voto": a.cuenta_voto,
                }
            )
        ofertas_ap = (
            db.query(GovernmentProcurementOpeningOffer)
            .filter(
                GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
                GovernmentProcurementOpeningOffer.opening_id == ap.id,
            )
            .all()
        )
        ofertas_refs = []
        for oa in ofertas_ap:
            oferta = db.get(GovernmentProcurementOffer, oa.offer_id)
            if oferta is not None:
                ofertas_refs.append({"id": oa.offer_id, "oferta": f"O-{oferta.numero:02d}"})
        acta = db.get(Document, ap.acta_document_id)
        if acta is not None:
            aperturas.append(
            {
                "id": ap.id,
                "referencia": f"A-{ap.numero:02d}",
                "abierta_en": ap.abierta_en.isoformat(),
                "abierta_por": _usuarios_por_ids(db, [ap.created_by], ctx.tenant_id).get(str(ap.created_by)) if ap.created_by is not None else None,
                "acta": {"documento_id": acta.id, "titulo": acta.title, "huella": ap.acta_sha256},
                "observaciones": ap.observaciones,
                "miembros_con_voto": ap.miembros_con_voto,
                "asistentes_con_voto": ap.asistentes_con_voto,
                "quorum_requerido": ap.quorum_requerido,
                "asistentes": asistentes_out,
                "ofertas": ofertas_refs,
            }
        )
    ofertas_db = (
        db.query(GovernmentProcurementOffer)
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOffer.numero)
        .all()
    )
    ofertas_out = []
    for oferta in ofertas_db:
        abierta = (
            db.query(GovernmentProcurementOpeningOffer)
            .filter(
                GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
                GovernmentProcurementOpeningOffer.offer_id == oferta.id,
            )
            .one_or_none()
            is not None
        )
        docs = (
            db.query(GovernmentProcurementOfferDocument)
            .filter(
                GovernmentProcurementOfferDocument.company_id == ctx.company_id,
                GovernmentProcurementOfferDocument.offer_id == oferta.id,
            )
            .all()
        )
        sellada = any(documento_sellado(db, d.document_id) for d in docs)
        ofertas_out.append(
            {
                "id": oferta.id,
                "oferta": f"O-{oferta.numero:02d}",
                "oferente": oferta.oferente_nombre,
                "situacion": "ABIERTA" if abierta else "PENDIENTE_APERTURA",
                "situacion_etiqueta": "Abierta" if abierta else "Pendiente de apertura",
                "sellada": sellada,
            }
        )
    miembros_out = []
    if expediente.committee_id:
        for m in _miembros_comision(db, ctx.company_id, expediente.committee_id):
            oficial = db.get(GovernmentOfficial, m.official_id)
            miembros_out.append(
                {
                    "id": m.id,
                    "oficial": oficial.nombre if oficial else m.official_id,
                    "funcion": m.funcion,
                    "condicion": m.condicion,
                    "suplente_de_id": m.suplente_de_id,
                }
            )
    siguiente_accion = "Registre la matriz de evaluación"
    ofertas_resultado = []
    resultados_faltantes_por_oferta: dict[str, list[str]] = {}
    ofertas_abiertas_ids: list[str] = []
    resultados_registrados = 0

    if matriz is not None:
        ofertas_abiertas_ids = [str(o["id"]) for o in ofertas_out if o["situacion"] == "ABIERTA"]
        for oid in ofertas_abiertas_ids:
            resultados = (
                db.query(GovernmentProcurementEvalResult)
                .filter(
                    GovernmentProcurementEvalResult.company_id == ctx.company_id,
                    GovernmentProcurementEvalResult.offer_id == oid,
                )
                .all()
            )
            reemplazadas_resultado = {r.reemplaza_id for r in resultados if r.reemplaza_id is not None}
            vigentes_resultado = [r for r in resultados if r.id not in reemplazadas_resultado]
            resultados_por_criterio = {str(r.criterion_id): r for r in vigentes_resultado}
            faltantes = [str(c.id) for c in criterios if str(c.id) not in resultados_por_criterio]
            resultados_faltantes_por_oferta[oid] = faltantes

            for c in criterios:
                aportes_db = (
                    db.query(GovernmentProcurementEvalContribution)
                    .filter(
                        GovernmentProcurementEvalContribution.company_id == ctx.company_id,
                        GovernmentProcurementEvalContribution.offer_id == oid,
                        GovernmentProcurementEvalContribution.criterion_id == c.id,
                    )
                    .all()
                )
                reemplazadas_aporte = {aporte.reemplaza_id for aporte in aportes_db if aporte.reemplaza_id is not None}
                aportes_vigentes = [aporte for aporte in aportes_db if aporte.id not in reemplazadas_aporte]
                aportes_por_id = {str(aporte.id): aporte for aporte in aportes_db}
                aportes_criterio = []
                for aporte in aportes_vigentes:
                    miembro_comite = db.get(GovernmentProcurementCommitteeMember, aporte.member_id)
                    official = None
                    nombre_miembro = aporte.member_id
                    if miembro_comite is not None:
                        official = db.get(GovernmentOfficial, miembro_comite.official_id)
                        if official is not None:
                            nombre_miembro = official.nombre

                    historicos = []
                    cursor = aporte
                    while cursor.reemplaza_id is not None and str(cursor.reemplaza_id) in aportes_por_id:
                        anterior = aportes_por_id[str(cursor.reemplaza_id)]
                        historicos.append(anterior)
                        cursor = anterior
                    historicos_ordenados = sorted(historicos, key=lambda h: h.created_at)
                    historico_out = [
                        {
                            "id": h.id,
                            "puntaje": str(h.puntaje) if h.puntaje is not None else None,
                            "cumple": h.cumple,
                            "observacion": h.observacion,
                            "registrado_en": h.created_at.isoformat(),
                        }
                        for h in historicos_ordenados
                    ]
                    aportes_criterio.append(
                        {
                            "id": aporte.id,
                            "miembro_id": aporte.member_id,
                            "miembro": nombre_miembro,
                            "puntaje": str(aporte.puntaje) if aporte.puntaje is not None else None,
                            "cumple": aporte.cumple,
                            "observacion": aporte.observacion,
                            "evidencia_documento_id": aporte.evidencia_document_id,
                            "registrado_en": aporte.created_at.isoformat(),
                            "reemplaza_a": aporte.reemplaza_id,
                            "historial_reemplazos": historico_out,
                        }
                    )

                resultado = resultados_por_criterio.get(str(c.id))
                resultado_comision = None
                if resultado is not None:
                    resultados_registrados += 1
                    resultados_por_id = {str(r.id): r for r in resultados}
                    historicos_resultado = []
                    cursor_resultado = resultado
                    while cursor_resultado.reemplaza_id is not None and str(cursor_resultado.reemplaza_id) in resultados_por_id:
                        anterior_resultado = resultados_por_id[str(cursor_resultado.reemplaza_id)]
                        historicos_resultado.append(anterior_resultado)
                        cursor_resultado = anterior_resultado
                    historicos_resultado_ordenados = sorted(historicos_resultado, key=lambda r: r.created_at)
                    miembro_resultado = db.get(GovernmentProcurementCommitteeMember, resultado.member_id)
                    nombre_resultado = resultado.created_by
                    if miembro_resultado is not None:
                        official_resultado = db.get(GovernmentOfficial, miembro_resultado.official_id)
                        if official_resultado is not None:
                            nombre_resultado = official_resultado.nombre
                    resultado_comision = {
                        "id": resultado.id,
                        "puntaje": str(resultado.puntaje) if resultado.puntaje is not None else None,
                        "cumple": resultado.cumple,
                        "observacion": resultado.observacion,
                        "evidencia_documento_id": resultado.evidencia_document_id,
                        "registrado_en": resultado.created_at.isoformat(),
                        "registrado_por": nombre_resultado,
                        "historial_reemplazos": [
                            {
                                "id": h.id,
                                "puntaje": str(h.puntaje) if h.puntaje is not None else None,
                                "cumple": h.cumple,
                                "observacion": h.observacion,
                                "registrado_en": h.created_at.isoformat(),
                            }
                            for h in historicos_resultado_ordenados
                        ],
                    }

                ofertas_resultado.append(
                    {
                        "oferta_id": oid,
                        "oferta": next((o["oferta"] for o in ofertas_out if o["id"] == oid), oid),
                        "criterio_id": c.id,
                        "aspecto": c.aspecto,
                        "criterio": c.nombre,
                        "escala": c.escala,
                        "aportes": aportes_criterio,
                        "resultado_comision": resultado_comision,
                    }
                )

    resultados_requeridos = len(ofertas_abiertas_ids) * len(criterios) if matriz is not None else 0
    progreso = {
        "ofertas_abiertas": len(ofertas_abiertas_ids),
        "criterios": len(criterios) if matriz is not None else 0,
        "resultados_requeridos": resultados_requeridos,
        "resultados_registrados": resultados_registrados,
    }

    if matriz is None:
        siguiente_accion = "Registre la matriz de evaluación"
    elif matriz.estado == "BORRADOR":
        siguiente_accion = "Bloquee la matriz de evaluación"
    elif expediente.recepcion_concluida_en is None:
        siguiente_accion = "Concluya la recepción de ofertas"
    elif not ofertas_abiertas_ids:
        siguiente_accion = "Abra las ofertas recibidas"
    elif expediente.evaluacion_concluida_en is None and any(resultados_faltantes_por_oferta.values()):
        siguiente_accion = "Registre los resultados de la Comisión"
    elif expediente.evaluacion_concluida_en is None:
        siguiente_accion = "Concluya la evaluación"
    else:
        siguiente_accion = "Preparar recomendación"

    return {
        "matriz": (
            {
                "id": matriz.id,
                "estado": matriz.estado,
                "version": matriz.version,
                "transcripcion": matriz.transcripcion,
                "pliego": {
                    "documento_id": matriz.pliego_document_id,
                    "version_id": matriz.pliego_version_id,
                    "huella": matriz.pliego_sha256,
                },
                "criterios": [
                    {
                        "id": c.id,
                        "aspecto": c.aspecto,
                        "orden": c.orden,
                        "nombre": c.nombre,
                        "descripcion": c.descripcion,
                        "escala": c.escala,
                        "puntaje_maximo": str(c.puntaje_maximo) if c.puntaje_maximo is not None else None,
                        "ponderacion": str(c.ponderacion) if c.ponderacion is not None else None,
                    }
                    for c in criterios
                ],
            }
            if matriz
            else None
        ),
        "aperturas": aperturas,
        "ofertas": ofertas_out,
        "miembros": miembros_out,
        "recepcion_concluida_en": expediente.recepcion_concluida_en.isoformat() if expediente.recepcion_concluida_en else None,
        "evaluacion_concluida_en": expediente.evaluacion_concluida_en.isoformat() if expediente.evaluacion_concluida_en else None,
        "siguiente_accion": siguiente_accion,
        "resultados_por_oferta": ofertas_resultado,
        "resultados_faltantes": resultados_faltantes_por_oferta,
        "progreso": progreso,
    }


def obtener_evaluacion(db: Session, ctx: CompanyContext, user: User, expediente_id: str) -> dict:
    expediente = _cargar(db, ctx, expediente_id)
    return _estado_evaluacion(db, ctx, expediente, user)
