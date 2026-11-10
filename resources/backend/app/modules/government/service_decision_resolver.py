from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, PermissionDeniedError
from app.modules.government.models import (
    GovernmentAct,
    GovernmentProcurementDecision,
    GovernmentProcurementOffer,
    GovernmentProcurementOpeningOffer,
    GovernmentProcurementRecommendation,
    GovernmentProcurementRecommendationOption,
    GovernmentProcurementRecommendationRejection,
    GovernmentProcurementRecommendationSignatory,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_decision import (
    CAUSALES_DESIERTA,
    CAUSALES_NULIDAD,
    RESULTADOS_DECISION,
    _auditar,
    _evento,
    obtener_estado_decision,
)
from app.modules.government.service_expedientes import _abierto, _err, _para_escribir
from app.modules.government.service_identidad import (
    _funcionario_del_actor,
    _politica_de,
    exigir_autoridad_funcional,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio, instante_actual


def _decision_vigente(db: Session, expediente_id: str) -> GovernmentProcurementDecision | None:
    return db.scalar(
        select(GovernmentProcurementDecision)
        .where(
            GovernmentProcurementDecision.file_id == expediente_id,
            GovernmentProcurementDecision.estado == "VIGENTE",
            GovernmentProcurementDecision.resultado != "NULIDAD",
        )
        .order_by(GovernmentProcurementDecision.numero.desc())
        .limit(1)
    )


def _recomendacion_vigente(db: Session, expediente_id: str) -> GovernmentProcurementRecommendation | None:
    return db.scalar(
        select(GovernmentProcurementRecommendation)
        .where(
            GovernmentProcurementRecommendation.file_id == expediente_id,
            GovernmentProcurementRecommendation.estado == "EMITIDA",
        )
        .order_by(GovernmentProcurementRecommendation.numero.desc())
        .limit(1)
    )


def _opciones_de_recomendacion(
    db: Session, recomendacion_id: str
) -> list[GovernmentProcurementRecommendationOption]:
    return list(
        db.scalars(
            select(GovernmentProcurementRecommendationOption)
            .where(GovernmentProcurementRecommendationOption.recommendation_id == recomendacion_id)
            .order_by(GovernmentProcurementRecommendationOption.posicion)
        )
    )


def _ultima_adjudicacion_de_recomendacion(
    db: Session, recomendacion_id: str
) -> GovernmentProcurementDecision | None:
    return db.scalar(
        select(GovernmentProcurementDecision)
        .where(
            GovernmentProcurementDecision.recommendation_id == recomendacion_id,
            GovernmentProcurementDecision.resultado == "ADJUDICADA",
        )
        .order_by(GovernmentProcurementDecision.numero.desc())
        .limit(1)
    )


def _anulada_por_informacion_falsa(
    db: Session, decision_id: str
) -> bool:
    nulidad = db.scalar(
        select(GovernmentProcurementDecision)
        .where(
            GovernmentProcurementDecision.anula_id == decision_id,
            GovernmentProcurementDecision.resultado == "NULIDAD",
            GovernmentProcurementDecision.causal_nulidad == "INFORMACION_FALSA",
        )
        .limit(1)
    )
    return nulidad is not None


def registrar_decision(
    db: Session,
    ctx: CompanyContext,
    user: User,
    expediente_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_DECISION_IF_MATCH_REQUIRED",
            message="Se requiere If-Match con la versión del expediente",
            status_code=428,
        )
    expediente = _para_escribir(db, ctx, expediente_id, version)
    _abierto(expediente)
    if expediente.evaluacion_concluida_en is None:
        raise ConflictError("GOV_DECISION_EVALUATION_PENDING", "La evaluación no ha concluido")

    resultado = cuerpo.get("resultado")
    if resultado not in RESULTADOS_DECISION:
        raise _err("resultado", "Resultado de decisión inválido")

    acto_id = cuerpo.get("acto_id")
    acto = db.get(GovernmentAct, acto_id) if acto_id else None
    if acto is None or acto.company_id != ctx.company_id:
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="El acto no es válido para decidir",
            status_code=422,
            field_errors={"acto_id": ["Acto inexistente o de otro ente"]},
        )
    if acto.status not in ("EMITIDO", "EFICAZ"):
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="El acto no está emitido ni eficaz",
            status_code=422,
            field_errors={"acto_id": ["El acto debe estar EMITIDO o EFICAZ"]},
        )
    if acto.caracter != "PARTICULAR":
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="El acto debe ser de carácter particular",
            status_code=422,
            field_errors={"acto_id": ["El acto debe ser PARTICULAR"]},
        )
    if acto.competencia_accion != "APROBAR" or acto.competencia_materia != "CONTRATACIONES":
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="El acto no tiene competencia para aprobar contrataciones",
            status_code=422,
            field_errors={"acto_id": ["Competencia del acto inválida"]},
        )
    if not _autoridad_valida(
        db, ctx.company_id, str(acto.cargo_id), acto.fecha, "APROBAR", "CONTRATACIONES"
    ):
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="La autoridad del acto no es válida para aprobar contrataciones",
            status_code=422,
            field_errors={"acto_id": ["Autoridad del acto inválida"]},
        )

    acto_en_uso = db.scalar(
        select(GovernmentProcurementDecision)
        .where(GovernmentProcurementDecision.act_id == acto.id)
        .limit(1)
    )
    if acto_en_uso is not None:
        raise ConflictError("GOV_DECISION_ACT_IN_USE", "El acto ya sostiene otra decisión")

    exigir_autoridad_funcional(db, ctx, str(acto.cargo_id), "APROBAR", "CONTRATACIONES")

    politica = _politica_de(db, ctx)
    funcionario_actor = _funcionario_del_actor(db, ctx)
    if politica is not None and politica.exige_identidad:
        vigente_rec = _recomendacion_vigente(db, str(expediente.id))
        if vigente_rec is not None and funcionario_actor is not None:
            firmante_ids = [
                str(s.official_id)
                for s in db.scalars(
                    select(GovernmentProcurementRecommendationSignatory).where(
                        GovernmentProcurementRecommendationSignatory.recommendation_id
                        == vigente_rec.id
                    )
                )
            ]
            if funcionario_actor in firmante_ids:
                raise PermissionDeniedError(
                    code="GOV_DECISION_COMMISSION_SIGNATORY",
                    message="Quien firmó la recomendación no puede decidirla",
                )

    final = _decision_vigente(db, str(expediente.id))
    vigente_rec = _recomendacion_vigente(db, str(expediente.id))

    if resultado in ("ADJUDICADA", "DESIERTA", "TERMINADA"):
        if vigente_rec is None:
            raise ConflictError(
                "GOV_DECISION_RECOMMENDATION_REQUIRED",
                "Decida sobre la recomendación vigente",
            )
        if cuerpo.get("recomendacion_id") != vigente_rec.id:
            raise ConflictError(
                "GOV_DECISION_RECOMMENDATION_REQUIRED",
                "Decida sobre la recomendación vigente",
            )
        if final is not None:
            if resultado in ("ADJUDICADA", "DESIERTA"):
                raise ConflictError(
                    "GOV_DECISION_ALREADY_FINAL",
                    "Ya hay una decisión del procedimiento",
                )
            if final.resultado != "ADJUDICADA":
                raise ConflictError(
                    "GOV_DECISION_ALREADY_FINAL",
                    "Ya hay una decisión del procedimiento",
                )

    posicion: int | None = None
    oferta_id: str | None = None
    causal_desierta: str | None = None
    causal_nulidad: str | None = None
    anula_id: str | None = None

    if resultado == "ADJUDICADA":
        if vigente_rec is None:
            raise ConflictError(
                "GOV_DECISION_RECOMMENDATION_REQUIRED",
                "Decida sobre la recomendación vigente",
            )
        if vigente_rec.resultado_recomendado != "ADJUDICAR":
            raise KontrolError(
                code="GOV_DECISION_OPTION_ORDER",
                message="La recomendación no propone adjudicar",
                status_code=422,
                field_errors={"oferta_id": ["La recomendación no propone adjudicar"]},
            )
        oferta_id = cuerpo.get("oferta_id")
        opciones = _opciones_de_recomendacion(db, str(vigente_rec.id))
        opcion = next((o for o in opciones if str(o.offer_id) == str(oferta_id)), None)
        if opcion is None:
            raise KontrolError(
                code="GOV_DECISION_OPTION_ORDER",
                message="La oferta no es una opción de la recomendación vigente",
                status_code=422,
                field_errors={"oferta_id": ["Oferta no recomendada"]},
            )
        permitida = 1
        ultima = _ultima_adjudicacion_de_recomendacion(db, str(vigente_rec.id))
        if ultima is not None and _anulada_por_informacion_falsa(db, str(ultima.id)):
            permitida = (ultima.posicion or 0) + 1
        if opcion.posicion != permitida:
            raise KontrolError(
                code="GOV_DECISION_OPTION_ORDER",
                message="La opción no respeta el orden de prelación",
                status_code=422,
                field_errors={"oferta_id": ["Debe adjudicarse la opción en el orden permitido"]},
            )
        posicion = opcion.posicion

    elif resultado == "DESIERTA":
        if vigente_rec is None:
            raise ConflictError(
                "GOV_DECISION_RECOMMENDATION_REQUIRED",
                "Decida sobre la recomendación vigente",
            )
        causal_desierta = cuerpo.get("causal_desierta")
        if causal_desierta not in CAUSALES_DESIERTA:
            raise _err("causal_desierta", "Causal de desierta inválida")
        if causal_desierta == "LCP113_2":
            rechazos = list(
                db.scalars(
                    select(GovernmentProcurementRecommendationRejection).where(
                        GovernmentProcurementRecommendationRejection.recommendation_id
                        == vigente_rec.id
                    )
                )
            )
            ofertas_abiertas = list(
                db.scalars(
                    select(GovernmentProcurementOffer)
                    .join(
                        GovernmentProcurementOpeningOffer,
                        GovernmentProcurementOpeningOffer.offer_id == GovernmentProcurementOffer.id,
                    )
                    .where(
                        GovernmentProcurementOffer.company_id == ctx.company_id,
                        GovernmentProcurementOffer.file_id == expediente.id,
                    )
                )
            )
            rechazadas_ids = {str(r.offer_id) for r in rechazos}
            if any(str(o.id) not in rechazadas_ids for o in ofertas_abiertas):
                raise KontrolError(
                    code="GOV_DECISION_OPTION_ORDER",
                    message="LCP113_2 exige que la recomendación rechace todas las ofertas abiertas",
                    status_code=422,
                    field_errors={"causal_desierta": ["No todas las ofertas fueron rechazadas"]},
                )

    elif resultado == "NULIDAD":
        anula_id = cuerpo.get("anula_id")
        objetivo = db.get(GovernmentProcurementDecision, anula_id) if anula_id else None
        if (
            objetivo is None
            or objetivo.file_id != expediente.id
            or objetivo.estado != "VIGENTE"
            or objetivo.resultado == "NULIDAD"
        ):
            raise ConflictError(
                "GOV_DECISION_NOTHING_TO_ANNUL",
                "No hay decisión vigente que anular",
            )
        causal_nulidad = cuerpo.get("causal_nulidad")
        if causal_nulidad not in CAUSALES_NULIDAD:
            raise _err("causal_nulidad", "Causal de nulidad inválida")

    motivacion = cuerpo.get("motivacion")
    if not motivacion or not str(motivacion).strip():
        raise _err("motivacion", "La motivación es obligatoria")

    evaluar_antes_de_actuar(
        db, ctx, "PROC03_RESOLVER", "GovernmentProcurementFile", str(expediente.id)
    )

    max_num = db.scalar(
        select(func.max(GovernmentProcurementDecision.numero)).where(
            GovernmentProcurementDecision.file_id == expediente.id
        )
    )
    numero = (max_num or 0) + 1
    nuevo_id = str(uuid4())
    ahora = instante_actual()

    if resultado == "TERMINADA" and final is not None:
        final.estado = "SUSTITUIDA"
        final.afectada_por_id = nuevo_id
        final.afectada_en = ahora
        db.flush()

    decision = GovernmentProcurementDecision(
        id=nuevo_id,
        company_id=ctx.company_id,
        file_id=expediente.id,
        numero=numero,
        resultado=resultado,
        act_id=acto.id,
        cargo_id=acto.cargo_id,
        recommendation_id=vigente_rec.id if vigente_rec is not None else None,
        offer_id=oferta_id,
        posicion=posicion,
        causal_desierta=causal_desierta,
        causal_nulidad=causal_nulidad,
        anula_id=anula_id,
        motivacion=motivacion,
        decidida_en=ahora,
        decidida_por=str(user.id),
        official_id=funcionario_actor,
        estado="VIGENTE",
    )
    db.add(decision)
    db.flush()

    if resultado == "NULIDAD" and anula_id is not None:
        objetivo = db.get(GovernmentProcurementDecision, anula_id)
        if objetivo is None:
            raise ConflictError(
                "GOV_DECISION_NOTHING_TO_ANNUL",
                "No hay decisión vigente que anular",
            )
        objetivo.estado = "ANULADA"
        objetivo.afectada_por_id = nuevo_id
        objetivo.afectada_en = ahora
        db.flush()

    expediente.version += 1
    db.flush()

    oferta = db.get(GovernmentProcurementOffer, oferta_id) if oferta_id else None
    oferente = oferta.oferente_nombre if oferta else None
    ref = f"DEC-{numero:02d}"
    ref_rec = f"REC-{vigente_rec.numero:02d}" if vigente_rec is not None else None
    acto_etiqueta = f"{acto.tipo} {acto.numero}"

    if resultado == "ADJUDICADA":
        if oferta is None:
            raise ConflictError(
                "GOV_DECISION_OPTION_ORDER",
                "La oferta no es una opción de la recomendación vigente",
            )
        titulo = f"Adjudicación {ref} a O-{oferta.numero:02d} ({oferente})"
        clase = "ADJUDICACION"
    elif resultado == "DESIERTA":
        causal_desierta_etiqueta = (
            CAUSALES_DESIERTA.get(causal_desierta, causal_desierta)
            if causal_desierta
            else causal_desierta
        )
        titulo = f"Declaratoria desierta {ref}: {causal_desierta_etiqueta}"
        clase = "DESIERTA"
    elif resultado == "TERMINADA":
        titulo = f"Terminación del procedimiento {ref}"
        clase = "TERMINACION"
    else:
        objetivo_ref = f"DEC-{objetivo.numero:02d}" if anula_id and objetivo else ""
        causal_nulidad_etiqueta = (
            CAUSALES_NULIDAD.get(causal_nulidad, causal_nulidad)
            if causal_nulidad
            else causal_nulidad
        )
        titulo = f"Nulidad {ref} de {objetivo_ref}: {causal_nulidad_etiqueta}"
        clase = "NULIDAD"

    _evento(
        db,
        ctx,
        expediente,
        clase,
        hoy_de_negocio(),
        titulo,
        act_id=str(acto.id),
        acto_etiqueta=acto_etiqueta,
    )

    if resultado in ("ADJUDICADA", "DESIERTA", "TERMINADA"):
        _auditar(
            db,
            ctx,
            "GOV_PROCUREMENT_DECISION_ISSUED",
            expediente_id=str(expediente.id),
            after={
                "decision": ref,
                "resultado": resultado,
                "oferta": f"O-{oferta.numero:02d}" if oferta else None,
                "causal": causal_desierta,
                "acto": acto.numero,
                "recomendacion": ref_rec,
            },
            motivo=motivacion,
        )
    else:
        _auditar(
            db,
            ctx,
            "GOV_PROCUREMENT_DECISION_NULLIFIED",
            expediente_id=str(expediente.id),
            after={
                "decision": f"DEC-{objetivo.numero:02d}" if anula_id and objetivo else None,
                "resultado": "NULIDAD",
                "causal": causal_nulidad,
                "acto": acto.numero,
            },
            motivo=motivacion,
        )

    return obtener_estado_decision(db, ctx, user, expediente_id)
