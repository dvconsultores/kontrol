from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, BinaryIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import (
    GovernmentAct,
    GovernmentContract,
    GovernmentNotification,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementCommittee,
    GovernmentProcurementDecision,
    GovernmentProcurementFile,
    GovernmentProcurementFileResponsible,
    GovernmentProcurementOffer,
    GovernmentProcurementOpeningOffer,
    GovernmentProcurementRecommendation,
    GovernmentProcurementRecommendationOption,
    GovernmentProcurementRecommendationRejection,
    GovernmentProcurementRecommendationResponsible,
    GovernmentProcurementRecommendationSignatory,
)
from app.modules.government.schemas_notificaciones import clave_identificacion
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_comision_regla import (
    cuenta_voto,
    documentos_faltantes,
    evaluar_decision,
    inhibidos,
    regla_de,
)
from app.modules.government.service_decision_limite import evaluar_limite, limite_del_acto
from app.modules.government.service_evaluacion import _miembros_comision, obtener_evaluacion
from app.modules.government.service_expedientes import _abierto, _auditar, _cargar, _err, _evento, _para_escribir
from app.modules.government.service_identidad import _funcionario_del_actor, _politica_de
from app.modules.government.service_ofertas_montos import resumen_monto
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.service_sod_funciones import verificar_antes_de_asumir_funcion
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio, instante_actual

RESULTADOS_RECOMENDACION = {
    "ADJUDICAR": "Adjudicar",
    "DECLARAR_DESIERTA": "Declarar desierta",
    "TERMINAR": "Terminar el procedimiento",
}

ESTADOS_RECOMENDACION = {
    "EMITIDA": "Emitida",
    "SUSTITUIDA": "Sustituida",
}

CAUSALES_DESIERTA = {
    "LCP113_1": "Ninguna oferta presentada (LCP art. 113.1)",
    "LCP113_2": "Todas las ofertas rechazadas o los oferentes descalificados (LCP art. 113.2)",
    "LCP113_3": "Perjuicio para el contratante si continúa (LCP art. 113.3)",
    "LCP113_4": "Las opciones no mantienen la oferta, no firman, no dan garantías o se les anula (LCP art. 113.4)",
    "LCP113_5": "Otro supuesto previsto en el pliego (LCP art. 113.5)",
}

CAUSALES_RECHAZO = {
    "LCP76_1": "Incumple el Decreto Ley (LCP art. 76.1)",
    "LCP76_2": "Omisiones o desviaciones sustanciales al pliego (LCP art. 76.2)",
    "LCP76_3": "Oferta condicionada o alternativa no permitida (LCP art. 76.3)",
    "LCP76_4": "Varias ofertas del mismo proponente (LCP art. 76.4)",
    "LCP76_5": "Oferentes vinculados entre sí (LCP art. 76.5)",
    "LCP76_6": "Información falsa (LCP art. 76.6)",
    "LCP76_7": "Sin cualidad para representar al oferente (LCP art. 76.7)",
    "LCP76_8": "Sin declaración de responsabilidad social (LCP art. 76.8)",
    "RLCP102_1": "Sin la documentación exigida (RLCP art. 102.1)",
    "RLCP102_2": "Sin las garantías exigidas (RLCP art. 102.2)",
    "RLCP102_3": "Garantías que no se ajustan al pliego (RLCP art. 102.3)",
    "RLCP102_4": "Validez menor a la requerida (RLCP art. 102.4)",
    "RLCP102_5": "Precios irregulares o ilógicos (RLCP art. 102.5)",
    "RLCP102_6": "Otra causal del pliego (RLCP art. 102.6)",
}

RESULTADOS_DECISION = {
    "ADJUDICADA": "Adjudicada",
    "DESIERTA": "Declarada desierta",
    "TERMINADA": "Terminada",
    "NULIDAD": "Nulidad declarada",
}

CAUSALES_NULIDAD = {
    "INFORMACION_FALSA": "Información o documentos falsos (LCP art. 112)",
    "VIOLACION_LEGAL": "Violación de disposiciones legales (LCP art. 112)",
}

ESTADOS_DECISION = {
    "VIGENTE": "Vigente",
    "ANULADA": "Anulada",
    "SUSTITUIDA": "Sustituida",
}


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _text(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _contrato_de_decision(db: Session, ctx: CompanyContext, decision_id: str) -> dict[str, Any] | None:
    contrato = db.scalar(
        select(GovernmentContract).where(
            GovernmentContract.company_id == ctx.company_id,
            GovernmentContract.decision_id == decision_id,
        )
    )
    if contrato is None:
        return None
    return {
        "id": contrato.id,
        "identificacion": contrato.codigo or f"Borrador · {contrato.expediente_numero} · {contrato.decision_referencia}",
        "estado": contrato.estado,
    }


def _parte_decision(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile) -> dict[str, Any]:
    decisiones = (
        db.query(GovernmentProcurementDecision)
        .filter(GovernmentProcurementDecision.file_id == expediente.id)
        .order_by(GovernmentProcurementDecision.numero.desc())
        .all()
    )
    decision_vigente = next(
        (d for d in decisiones if d.estado == "VIGENTE" and d.resultado != "NULIDAD"), None
    )

    decisiones_payload = []
    for d in decisiones:
        acto = db.get(GovernmentAct, d.act_id)
        cargo = db.get(GovernmentPosition, d.cargo_id)
        recomendacion = db.get(GovernmentProcurementRecommendation, d.recommendation_id) if d.recommendation_id else None
        oferta = db.get(GovernmentProcurementOffer, d.offer_id) if d.offer_id else None
        anula = db.get(GovernmentProcurementDecision, d.anula_id) if d.anula_id else None
        afectada_por = db.get(GovernmentProcurementDecision, d.afectada_por_id) if d.afectada_por_id else None
        usuario = db.get(User, d.decidida_por) if d.decidida_por else None
        decisiones_payload.append(
            {
                "id": d.id,
                "referencia": f"DEC-{d.numero:02d}",
                "resultado": d.resultado,
                "resultado_etiqueta": RESULTADOS_DECISION.get(d.resultado, d.resultado),
                "estado": d.estado,
                "estado_etiqueta": ESTADOS_DECISION.get(d.estado, d.estado),
                "recomendacion": f"REC-{recomendacion.numero:02d}" if recomendacion else None,
                "oferta": f"O-{oferta.numero:02d}" if oferta else None,
                "oferente": oferta.oferente_nombre if oferta else None,
                "posicion": d.posicion,
                "causal": d.causal_desierta or d.causal_nulidad,
                "causal_etiqueta": (
                    CAUSALES_DESIERTA.get(d.causal_desierta)
                    if d.causal_desierta
                    else CAUSALES_NULIDAD.get(d.causal_nulidad)
                    if d.causal_nulidad
                    else None
                ),
                "anula": f"DEC-{anula.numero:02d}" if anula else None,
                "afectada_por": f"DEC-{afectada_por.numero:02d}" if afectada_por else None,
                "acto": {
                    "id": acto.id,
                    "tipo": acto.tipo,
                    "numero": acto.numero,
                    "fecha": acto.fecha,
                    "status": acto.status,
                } if acto else None,
                "cargo": cargo.name if cargo else None,
                "motivacion": d.motivacion,
                "decidida_en": d.decidida_en,
                "decidida_por": usuario.username if usuario else None,
                "conversion": d.conversion_autoridad,
            }
        )

    actos_elegibles = []
    actos = (
        db.query(GovernmentAct)
        .filter(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status.in_(("EMITIDO", "EFICAZ")),
            GovernmentAct.caracter == "PARTICULAR",
            GovernmentAct.competencia_accion == "APROBAR",
            GovernmentAct.competencia_materia == "CONTRATACIONES",
        )
        .all()
    )
    actos_con_decision = {d.act_id for d in decisiones}
    ofertas_expediente = list(
        db.scalars(
            select(GovernmentProcurementOffer)
            .where(
                GovernmentProcurementOffer.company_id == ctx.company_id,
                GovernmentProcurementOffer.file_id == expediente.id,
            )
            .order_by(GovernmentProcurementOffer.numero)
        )
    )
    for acto in actos:
        if acto.id in actos_con_decision:
            continue
        actos_elegibles.append(
            {
                "id": acto.id,
                "tipo": acto.tipo,
                "numero": acto.numero,
                "fecha": acto.fecha,
                "asunto": acto.asunto,
                "limite": limite_del_acto(db, ctx, acto),
                "control_monto": [evaluar_limite(db, ctx, acto, oferta) for oferta in ofertas_expediente],
            }
        )

    notificaciones = []
    acto_eficaz = False
    if decision_vigente:
        acto_vigente = db.get(GovernmentAct, decision_vigente.act_id)
        acto_eficaz = bool(acto_vigente and acto_vigente.status == "EFICAZ")
        ofertas = (
            db.query(GovernmentProcurementOffer)
            .filter(GovernmentProcurementOffer.file_id == expediente.id)
            .all()
        )
        notis = (
            db.query(GovernmentNotification)
            .filter(
                GovernmentNotification.act_id == decision_vigente.act_id,
                GovernmentNotification.status != "ANULADA",
            )
            .all()
        )
        notis_por_clave = {n.identificacion_clave: n for n in notis}
        for oferta in ofertas:
            clave = clave_identificacion(oferta.oferente_documento)
            noti = notis_por_clave.get(clave)
            notificaciones.append(
                {
                    "offer_id": oferta.id,
                    "oferta": f"O-{oferta.numero:02d}",
                    "oferente": oferta.oferente_nombre,
                    "documento": oferta.oferente_documento,
                    "estado": noti.status if noti else "SIN_NOTIFICACION",
                    "estado_etiqueta": (
                        {"PENDIENTE": "Pendiente", "NOTIFICADA": "Notificada"}.get(noti.status)
                        if noti
                        else "Sin notificación"
                    ),
                    "fecha_notificacion": noti.fecha_notificacion if noti else None,
                    "medio": noti.medio_notificacion if noti else None,
                }
            )

    decision_vigente_payload = None
    if decision_vigente:
        recomendacion = (
            db.get(GovernmentProcurementRecommendation, decision_vigente.recommendation_id)
            if decision_vigente.recommendation_id
            else None
        )
        oferta_decision = (
            db.get(GovernmentProcurementOffer, decision_vigente.offer_id)
            if decision_vigente.offer_id
            else None
        )
        anula_decision = (
            db.get(GovernmentProcurementDecision, decision_vigente.anula_id)
            if decision_vigente.anula_id
            else None
        )
        afectada_por_decision = (
            db.get(GovernmentProcurementDecision, decision_vigente.afectada_por_id)
            if decision_vigente.afectada_por_id
            else None
        )
        acto_decision = db.get(GovernmentAct, decision_vigente.act_id)
        cargo_decision = db.get(GovernmentPosition, decision_vigente.cargo_id)
        usuario_decision = (
            db.get(User, decision_vigente.decidida_por)
            if decision_vigente.decidida_por
            else None
        )
        decision_vigente_payload = {
            "id": decision_vigente.id,
            "referencia": f"DEC-{decision_vigente.numero:02d}",
            "contrato": _contrato_de_decision(db, ctx, str(decision_vigente.id)),
            "resultado": decision_vigente.resultado,
            "resultado_etiqueta": RESULTADOS_DECISION.get(
                decision_vigente.resultado, decision_vigente.resultado
            ),
            "estado": decision_vigente.estado,
            "estado_etiqueta": ESTADOS_DECISION.get(decision_vigente.estado, decision_vigente.estado),
            "recomendacion": (
                f"REC-{recomendacion.numero:02d}" if recomendacion else None
            ),
            "oferta": (
                f"O-{oferta_decision.numero:02d}" if oferta_decision else None
            ),
            "oferente": (
                oferta_decision.oferente_nombre if oferta_decision else None
            ),
            "posicion": decision_vigente.posicion,
            "causal": decision_vigente.causal_desierta or decision_vigente.causal_nulidad,
            "causal_etiqueta": (
                CAUSALES_DESIERTA.get(decision_vigente.causal_desierta)
                if decision_vigente.causal_desierta
                else CAUSALES_NULIDAD.get(decision_vigente.causal_nulidad)
                if decision_vigente.causal_nulidad
                else None
            ),
            "anula": (
                f"DEC-{anula_decision.numero:02d}" if anula_decision else None
            ),
            "afectada_por": (
                f"DEC-{afectada_por_decision.numero:02d}" if afectada_por_decision else None
            ),
            "acto": {
                "id": acto_decision.id if acto_decision else None,
                "tipo": acto_decision.tipo if acto_decision else None,
                "numero": acto_decision.numero if acto_decision else None,
                "fecha": acto_decision.fecha if acto_decision else None,
                "status": acto_decision.status if acto_decision else None,
            },
            "cargo": cargo_decision.name if cargo_decision else None,
            "motivacion": decision_vigente.motivacion,
            "decidida_en": decision_vigente.decidida_en,
            "decidida_por": (
                usuario_decision.username if usuario_decision else None
            ),
        }

    return {
        "decision_vigente": decision_vigente_payload,
        "decisiones": decisiones_payload,
        "resultado": decision_vigente.resultado if decision_vigente else None,
        "actos_elegibles": actos_elegibles,
        "notificaciones": notificaciones,
        "acto_eficaz": acto_eficaz,
    }


def _serializar_recomendacion(
    db: Session,
    ctx: CompanyContext,
    recomendacion: GovernmentProcurementRecommendation,
) -> dict[str, Any]:
    firmantes = (
        db.query(GovernmentProcurementRecommendationSignatory)
        .filter(
            GovernmentProcurementRecommendationSignatory.company_id == ctx.company_id,
            GovernmentProcurementRecommendationSignatory.recommendation_id == recomendacion.id,
        )
        .order_by(GovernmentProcurementRecommendationSignatory.created_at)
        .all()
    )
    responsables = (
        db.query(GovernmentProcurementRecommendationResponsible)
        .filter(
            GovernmentProcurementRecommendationResponsible.company_id == ctx.company_id,
            GovernmentProcurementRecommendationResponsible.recommendation_id == recomendacion.id,
        )
        .order_by(GovernmentProcurementRecommendationResponsible.created_at)
        .all()
    )
    opciones = (
        db.query(GovernmentProcurementRecommendationOption)
        .filter(
            GovernmentProcurementRecommendationOption.company_id == ctx.company_id,
            GovernmentProcurementRecommendationOption.recommendation_id == recomendacion.id,
        )
        .order_by(GovernmentProcurementRecommendationOption.posicion)
        .all()
    )
    rechazos = (
        db.query(GovernmentProcurementRecommendationRejection)
        .filter(
            GovernmentProcurementRecommendationRejection.company_id == ctx.company_id,
            GovernmentProcurementRecommendationRejection.recommendation_id == recomendacion.id,
        )
        .all()
    )

    ofertas = {
        str(o.id): o
        for o in db.query(GovernmentProcurementOffer)
        .filter(GovernmentProcurementOffer.company_id == ctx.company_id)
        .all()
    }
    oficiales = {
        str(o.id): o
        for o in db.query(GovernmentOfficial)
        .filter(GovernmentOfficial.company_id == ctx.company_id)
        .all()
    }
    usuarios = _usuarios_por_ids(db, [recomendacion.emitida_por], ctx.tenant_id)
    emitida_por = usuarios.get(recomendacion.emitida_por, recomendacion.emitida_por)

    sustituye_ref = None
    if recomendacion.sustituye_id:
        anterior = db.get(GovernmentProcurementRecommendation, recomendacion.sustituye_id)
        if anterior:
            sustituye_ref = f"REC-{anterior.numero:02d}"

    def oferta_label(offer_id: str) -> str:
        oferta = ofertas.get(str(offer_id))
        return f"O-{oferta.numero:02d}" if oferta else "O-??"

    def oferente_label(offer_id: str) -> str:
        oferta = ofertas.get(str(offer_id))
        return oferta.oferente_nombre if oferta else ""

    return {
        "id": recomendacion.id,
        "referencia": f"REC-{recomendacion.numero:02d}",
        "estado": recomendacion.estado,
        "estado_etiqueta": ESTADOS_RECOMENDACION.get(recomendacion.estado, recomendacion.estado),
        "resultado_recomendado": recomendacion.resultado_recomendado,
        "resultado_etiqueta": RESULTADOS_RECOMENDACION.get(
            recomendacion.resultado_recomendado, recomendacion.resultado_recomendado
        ),
        "causal_desierta": recomendacion.causal_desierta,
        "causal_etiqueta": CAUSALES_DESIERTA.get(recomendacion.causal_desierta)
        if recomendacion.causal_desierta
        else None,
        "motivacion": recomendacion.motivacion,
        "examen_legal": recomendacion.examen_legal,
        "examen_financiero": recomendacion.examen_financiero,
        "examen_tecnico": recomendacion.examen_tecnico,
        "resultado_matriz": recomendacion.resultado_matriz,
        "medidas_promocion": recomendacion.medidas_promocion,
        "modo": recomendacion.modo,
        "regla": recomendacion.regla,
        "firmantes": [
            {
                "member_id": f.member_id,
                "oficial": (
                    oficiales[str(f.official_id)].nombre
                    if str(f.official_id) in oficiales
                    else ""
                ),
                "funcion": f.funcion,
                "condicion": f.condicion,
                "cuenta_voto": f.cuenta_voto,
            }
            for f in firmantes
        ],
        "responsables": [
            {
                "responsible_id": resp.responsible_id,
                "oficial": (
                    oficiales[str(resp.official_id)].nombre
                    if str(resp.official_id) in oficiales
                    else ""
                ),
                "rol": resp.rol,
            }
            for resp in responsables
        ],
        "opciones": [
            {
                "posicion": o.posicion,
                "offer_id": o.offer_id,
                "oferta": oferta_label(o.offer_id),
                "oferente": oferente_label(o.offer_id),
            }
            for o in opciones
        ],
        "rechazos": [
            {
                "offer_id": r.offer_id,
                "oferta": oferta_label(r.offer_id),
                "oferente": oferente_label(r.offer_id),
                "causal": r.causal,
                "causal_etiqueta": CAUSALES_RECHAZO.get(r.causal, r.causal),
                "motivacion": r.motivacion,
            }
            for r in rechazos
        ],
        "matriz_version": recomendacion.matrix_version,
        "evaluacion_concluida_en": recomendacion.evaluacion_concluida_en.isoformat()
        if recomendacion.evaluacion_concluida_en
        else None,
        "emitida_en": recomendacion.emitida_en.isoformat() if recomendacion.emitida_en else None,
        "emitida_por": emitida_por,
        "sustituye": sustituye_ref,
        "motivo_sustitucion": recomendacion.motivo_sustitucion,
        "sustituida_en": recomendacion.sustituida_en.isoformat() if recomendacion.sustituida_en else None,
        "informe": {
            "nombre": recomendacion.informe_nombre,
            "sha256": recomendacion.informe_sha256,
            "tamano": recomendacion.informe_tamano,
        },
    }


def obtener_estado_decision(
    db: Session, ctx: CompanyContext, user: User, expediente_id: str
) -> dict[str, Any]:
    expediente = _cargar(db, ctx, expediente_id)

    verificar_antes_de_asumir_funcion(db, ctx, expediente, "EVALUADOR", user_ids=[ctx.user_id])
    evaluacion = obtener_evaluacion(db, ctx, user, expediente_id)
    evaluacion_concluida_en = evaluacion.get("evaluacion_concluida_en")

    comision = None
    regla_estado = None
    if expediente.committee_id:
        c = db.get(GovernmentProcurementCommittee, expediente.committee_id)
        if c and c.company_id == ctx.company_id:
            comision = {"id": c.id, "nombre": c.nombre}

    miembros_raw = _miembros_comision(db, ctx.company_id, expediente.committee_id) if expediente.committee_id else []
    oficiales = {
        str(o.id): o
        for o in db.query(GovernmentOfficial)
        .filter(GovernmentOfficial.company_id == ctx.company_id)
        .all()
    }
    if expediente.committee_id:
        miembros_raw = _miembros_comision(db, ctx.company_id, expediente.committee_id)
        inh = inhibidos(db, ctx.company_id, expediente.committee_id, str(expediente.id))
        oficiales = {
            str(o.id): o
            for o in db.query(GovernmentOfficial)
            .filter(GovernmentOfficial.company_id == ctx.company_id)
            .all()
        }
        c = db.get(GovernmentProcurementCommittee, expediente.committee_id)
        if c and c.company_id == ctx.company_id:
            regla = regla_de(db, c)
            d = evaluar_decision(regla, miembros_raw, [], [], inh)
            q = d["quorum"]
            regla_estado = {
                "etiqueta": regla.get("etiqueta"),
                "quorum_tipo_etiqueta": q.get("tipo_etiqueta"),
                "decision_tipo_etiqueta": d.get("tipo_etiqueta"),
                "decision_base": d.get("base"),
                "miembros_con_voto": q.get("miembros_con_voto"),
                "quorum_requerido": q.get("quorum_requerido"),
                "presidente_dirimente": regla.get("presidente_dirimente"),
            }
        presidente_vota = bool(regla.get("presidente_vota", True)) if regla else True

        miembros = [
            {
                "id": m.id,
                "oficial": (
                    oficiales[str(m.official_id)].nombre
                    if str(m.official_id) in oficiales
                    else ""
                ),
                "funcion": m.funcion,
                "condicion": m.condicion,
                "cuenta_voto": m.funcion == "MIEMBRO" and m.condicion == "PRINCIPAL" and (presidente_vota or not m.preside),
                "inhibido": m.id in inh,
                "preside": m.preside,
            }
            for m in miembros_raw
        ]
    else:
        inh = set()
        miembros = []

    responsables = []
    if not expediente.committee_id and expediente.comision_no_aplica_motivo:
        responsables_rows = (
            db.query(GovernmentProcurementFileResponsible)
            .filter(
                GovernmentProcurementFileResponsible.company_id == ctx.company_id,
                GovernmentProcurementFileResponsible.file_id == expediente.id,
                GovernmentProcurementFileResponsible.fin_efectivo.is_(None),
                GovernmentProcurementFileResponsible.rol.in_(["RESPONSABLE", "SUSTANCIACION"]),
            )
            .all()
        )
        responsables = [
            {
                "id": resp.official_id,
                "oficial": (
                    oficiales[str(resp.official_id)].nombre
                    if str(resp.official_id) in oficiales
                    else ""
                ),
                "rol": resp.rol,
            }
            for resp in responsables_rows
        ]

    recomendaciones = (
        db.query(GovernmentProcurementRecommendation)
        .filter(
            GovernmentProcurementRecommendation.company_id == ctx.company_id,
            GovernmentProcurementRecommendation.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementRecommendation.numero.desc())
        .all()
    )
    vigente = next((r for r in recomendaciones if r.estado == "EMITIDA"), None)

    ofertas_abiertas = (
        db.query(GovernmentProcurementOffer)
        .join(
            GovernmentProcurementOpeningOffer,
            GovernmentProcurementOpeningOffer.offer_id == GovernmentProcurementOffer.id,
        )
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOffer.numero)
        .all()
    )
    rechazadas_ids = set()
    if vigente:
        rechazadas_ids = {
            r.offer_id
            for r in db.query(GovernmentProcurementRecommendationRejection)
            .filter(
                GovernmentProcurementRecommendationRejection.company_id == ctx.company_id,
                GovernmentProcurementRecommendationRejection.recommendation_id == vigente.id,
            )
            .all()
        }

    ofertas: list[dict[str, Any]] = []
    for o in ofertas_abiertas:
        resumen = resumen_monto(db, ctx, o, abierta=True)
        ofertas.append(
            {
                "id": o.id,
                "oferta": f"O-{o.numero:02d}",
                "oferente": o.oferente_nombre,
                "documento": o.oferente_documento,
                "rechazada": o.id in rechazadas_ids,
                "monto": resumen["monto"],
                "monto_estado_etiqueta": resumen["monto_estado_etiqueta"],
            }
        )

    if evaluacion_concluida_en is None:
        siguiente_accion = "Concluir la evaluación (PROC-07)"
    elif vigente is None:
        siguiente_accion = "Preparar recomendación"
    else:
        parte_decision = _parte_decision(db, ctx, expediente)
        decision_vigente = parte_decision["decision_vigente"]
        if decision_vigente and not parte_decision["acto_eficaz"]:
            siguiente_accion = "Notificar a los oferentes"
        elif decision_vigente and parte_decision["acto_eficaz"]:
            if decision_vigente["resultado"] == "ADJUDICADA":
                siguiente_accion = "Resultado notificado: adjudicación (contrato en CNT-01)"
            else:
                siguiente_accion = f"Procedimiento concluido: {decision_vigente['resultado_etiqueta']}"
        else:
            siguiente_accion = "Decidir el resultado"

    catalogos = {
        "resultados_recomendacion": [
            {"codigo": k, "etiqueta": v} for k, v in RESULTADOS_RECOMENDACION.items()
        ],
        "causales_desierta": [{"codigo": k, "etiqueta": v} for k, v in CAUSALES_DESIERTA.items()],
        "causales_rechazo": [{"codigo": k, "etiqueta": v} for k, v in CAUSALES_RECHAZO.items()],
        "resultados_decision": [{"codigo": k, "etiqueta": v} for k, v in RESULTADOS_DECISION.items()],
        "causales_nulidad": [{"codigo": k, "etiqueta": v} for k, v in CAUSALES_NULIDAD.items()],
    }

    resultado = {
        "expediente": {
            "id": expediente.id,
            "numero": expediente.numero,
            "objeto": expediente.objeto,
            "version": expediente.version,
        },
        "evaluacion_concluida_en": evaluacion_concluida_en,
        "comision": comision,
        "comision_no_aplica_motivo": expediente.comision_no_aplica_motivo,
        "modo": (
            "COMISION"
            if expediente.committee_id
            else "UNIDAD_CONTRATANTE"
            if expediente.comision_no_aplica_motivo
            else None
        ),
        "regla": regla_estado,
        "miembros": miembros,
        "responsables": responsables,
        "ofertas": ofertas,
        "recomendacion_vigente": _serializar_recomendacion(db, ctx, vigente) if vigente else None,
        "recomendaciones": [_serializar_recomendacion(db, ctx, r) for r in recomendaciones],
        "siguiente_accion": siguiente_accion,
        "catalogos": catalogos,
    }
    resultado.update(_parte_decision(db, ctx, expediente))
    return resultado


def _render_informe(snapshot: dict[str, Any], referencia: str, emitida_en: datetime) -> bytes:
    styles = {
        "title": ParagraphStyle(name="TitleStyle", fontName="Helvetica-Bold", fontSize=13, leading=16),
        "label": ParagraphStyle(name="LabelStyle", fontName="Helvetica-Bold", fontSize=7, leading=9),
        "value": ParagraphStyle(name="ValueStyle", fontName="Helvetica", fontSize=7, leading=9),
        "h2": ParagraphStyle(
            name="Heading2",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceBefore=10,
            spaceAfter=4,
        ),
    }

    def styled(value: str | None, style: str = "value") -> Paragraph:
        return Paragraph(_text(value or ""), styles[style])

    def pair_table(rows: list[tuple[str, Any]]) -> Table:
        data = [[styled(k, "label"), styled(str(v) if v is not None else "")] for k, v in rows]
        table = Table(data, colWidths=[45 * mm, 125 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Informe de recomendación {referencia}",
    )
    story: list[Any] = [Paragraph(f"Informe de recomendación {referencia}", styles["title"]), Spacer(1, 6 * mm)]

    expediente = snapshot.get("expediente", {})
    story.append(pair_table([
        ("Expediente", f"{expediente.get('numero', '')} - {expediente.get('objeto', '')}"),
        ("Comisión", snapshot.get("comision", "")),
        ("Fecha", emitida_en.isoformat()),
    ]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Firmantes", styles["h2"]))
    firmantes = snapshot.get("firmantes", [])
    if firmantes:
        data = [[styled("Oficial", "label"), styled("Función", "label"), styled("Condición", "label")]]
        for f in firmantes:
            data.append([styled(f.get("oficial", "")), styled(f.get("funcion", "")), styled(f.get("condicion", ""))])
        table = Table(data, colWidths=[80 * mm, 45 * mm, 45 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
    else:
        story.append(styled("Sin firmantes"))

    story.append(Paragraph("Ofertas evaluadas", styles["h2"]))
    ofertas = snapshot.get("ofertas", [])
    if ofertas:
        data = [[styled("Oferta", "label"), styled("Oferente", "label"), styled("Resultados", "label")]]
        for oferta in ofertas:
            resultados = oferta.get("resultados", [])
            texto_resultados = "; ".join(
                f"{r.get('aspecto', '')} - {r.get('criterio', '')}: {r.get('valor', '')}"
                for r in resultados
            )
            data.append([
                styled(oferta.get("oferta", "")),
                styled(oferta.get("oferente", "")),
                styled(texto_resultados),
            ])
        table = Table(data, colWidths=[30 * mm, 60 * mm, 80 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
    else:
        story.append(styled("Sin ofertas evaluadas"))

    story.append(Paragraph("Rechazos", styles["h2"]))
    rechazos = snapshot.get("rechazos", [])
    if rechazos:
        for r in rechazos:
            story.append(
                styled(
                    f"{r.get('oferta', '')} - {r.get('causal_etiqueta', '')}: {r.get('motivacion', '')}"
                )
            )
    else:
        story.append(styled("Sin rechazos"))

    story.append(Paragraph("Examen legal", styles["h2"]))
    story.append(styled(snapshot.get("examen_legal", "")))
    story.append(Paragraph("Examen financiero", styles["h2"]))
    story.append(styled(snapshot.get("examen_financiero", "")))
    story.append(Paragraph("Examen técnico", styles["h2"]))
    story.append(styled(snapshot.get("examen_tecnico", "")))

    if snapshot.get("medidas_promocion"):
        story.append(Paragraph("Medidas de promoción", styles["h2"]))
        story.append(styled(snapshot.get("medidas_promocion", "")))

    story.append(Paragraph("Resultado de la matriz", styles["h2"]))
    story.append(styled(snapshot.get("resultado_matriz", "")))
    story.append(Paragraph("Motivación", styles["h2"]))
    story.append(styled(snapshot.get("motivacion", "")))

    story.append(Paragraph("Resultado recomendado", styles["h2"]))
    story.append(styled(snapshot.get("resultado_etiqueta", "")))
    if snapshot.get("causal_etiqueta"):
        story.append(styled(snapshot.get("causal_etiqueta", "")))

    opciones = snapshot.get("opciones", [])
    if opciones:
        story.append(Paragraph("Opciones", styles["h2"]))
        for o in opciones:
            story.append(styled(f"{o.get('posicion', '')} - {o.get('oferta', '')} - {o.get('oferente', '')}"))

    story.append(Paragraph("Evaluación concluida", styles["h2"]))
    story.append(styled(snapshot.get("evaluacion_concluida_en", "")))

    doc.build(story)
    return buffer.getvalue()


def emitir_recomendacion(
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

    evaluacion = obtener_evaluacion(db, ctx, user, expediente_id)
    evaluacion_concluida_en = evaluacion.get("evaluacion_concluida_en")
    if evaluacion_concluida_en is None:
        raise ConflictError("GOV_DECISION_EVALUATION_PENDING", "La evaluación no está concluida")

    decision_vigente = db.scalar(
        select(GovernmentProcurementDecision).where(
            GovernmentProcurementDecision.company_id == ctx.company_id,
            GovernmentProcurementDecision.file_id == expediente.id,
            GovernmentProcurementDecision.estado == "VIGENTE",
            GovernmentProcurementDecision.resultado != "NULIDAD",
        )
    )
    if decision_vigente is not None:
        raise ConflictError(
            "GOV_RECOMMENDATION_LOCKED_BY_DECISION", "Ya hay una decisión del procedimiento"
        )

    vigente = db.scalar(
        select(GovernmentProcurementRecommendation).where(
            GovernmentProcurementRecommendation.company_id == ctx.company_id,
            GovernmentProcurementRecommendation.file_id == expediente.id,
            GovernmentProcurementRecommendation.estado == "EMITIDA",
        )
    )
    sustituye_id = cuerpo.get("sustituye_id")
    if vigente is not None and sustituye_id != vigente.id:
        raise ConflictError(
            "GOV_RECOMMENDATION_ALREADY_ISSUED",
            "Ya hay una recomendación emitida; indique cuál sustituye",
        )
    if vigente is None and sustituye_id:
        raise ConflictError(
            "GOV_RECOMMENDATION_ALREADY_ISSUED",
            "Ya hay una recomendación emitida; indique cuál sustituye",
        )
    if sustituye_id:
        motivo_sustitucion = (cuerpo.get("motivo_sustitucion") or "").strip()
        if not motivo_sustitucion:
            raise _err("motivo_sustitucion", "El motivo de sustitución es obligatorio")

    if expediente.committee_id is None and not expediente.comision_no_aplica_motivo:
        raise _err("comision", "El expediente no tiene comisión vinculada ni declaró que no interviene")

    politica = _politica_de(db, ctx)
    oficial_actor_id = _funcionario_del_actor(db, ctx)

    firmante_ids = cuerpo.get("firmante_ids") or []
    asistente_ids = cuerpo.get("asistente_ids") or []
    responsable_ids = cuerpo.get("responsable_ids") or []
    miembros: list[Any] = []
    regla: dict[str, Any] | None = None
    d: dict[str, Any] | None = None
    inh: set[str] = set()

    if expediente.committee_id:
        c = db.get(GovernmentProcurementCommittee, expediente.committee_id)
        if c is None or c.company_id != ctx.company_id:
            raise _err("comision", "La comisión vinculada no existe en la empresa")
        regla = regla_de(db, c)
        if not regla.get("aplica_recomendacion", True):
            raise _err("comision", "La política de la comisión no la habilita para recomendar")

        if politica and politica.exige_identidad:
            if oficial_actor_id is None:
                raise PermissionDeniedError(
                    code="GOV_DECISION_IDENTITY_REQUIRED",
                    message="La cuenta debe estar vinculada a un funcionario",
                )
            miembros = _miembros_comision(db, ctx.company_id, expediente.committee_id)
            if oficial_actor_id not in {m.official_id for m in miembros}:
                raise PermissionDeniedError(
                    code="GOV_DECISION_NOT_COMMISSION_MEMBER",
                    message="Solo un miembro de la comisión registra su recomendación",
                )

        miembros = _miembros_comision(db, ctx.company_id, expediente.committee_id)
        if not firmante_ids:
            raise _err("firmantes", "Debe indicar al menos un firmante")
        miembros_ids = {m.id for m in miembros}
        for fid in firmante_ids:
            if fid not in miembros_ids:
                raise _err("firmantes", "Firmante no pertenece a la comisión")

        inh = inhibidos(db, ctx.company_id, expediente.committee_id, str(expediente.id))
        for mid in set(firmante_ids) | set(asistente_ids):
            miembro = next((m for m in miembros if m.id == mid), None)
            if miembro and mid in inh:
                oficial = db.get(GovernmentOfficial, miembro.official_id)
                nombre = oficial.nombre if oficial else str(miembro.official_id)
                raise _err("firmantes", f"{nombre} tiene una inhibición aceptada en este expediente; actúa su suplente")

        presentes = asistente_ids or firmante_ids
        for fid in firmante_ids:
            if fid not in presentes:
                raise _err("asistentes", "Todo firmante debe figurar entre los asistentes")
        for aid in presentes:
            if aid not in miembros_ids:
                raise _err("asistentes", "Asistente no pertenece a la comisión")

        d = evaluar_decision(regla, miembros, presentes, firmante_ids, inh)
        q = d["quorum"]
        if not q["hay_quorum"]:
            mensaje = f"Sin quórum: se requieren {q['quorum_requerido']} de {q['miembros_con_voto']} miembros con voto ({q['tipo_etiqueta']})"
            raise KontrolError(
                code="GOV_RECOMMENDATION_QUORUM",
                message=mensaje,
                status_code=422,
                field_errors={"firmantes": [mensaje]},
            )
        if not d["aprobada"]:
            mensaje = f"Sin mayoría: se requieren {d['requerido']} votos a favor de {d['base']} ({d['tipo_etiqueta']}); hay {d['votos_a_favor']}"
            raise KontrolError(
                code="GOV_RECOMMENDATION_MAJORITY",
                message=mensaje,
                status_code=422,
                field_errors={"firmantes": [mensaje]},
            )

        faltan = documentos_faltantes(
            db, ctx.company_id, regla, "RECOMENDACION", "GovernmentProcurementFile", str(expediente.id)
        )
        if faltan:
            raise _err("documentos", "; ".join(faltan))
    else:
        if not responsable_ids:
            raise _err("responsables", "Indique los responsables del expediente que firman la recomendación")
        responsables_rows = (
            db.query(GovernmentProcurementFileResponsible)
            .filter(
                GovernmentProcurementFileResponsible.company_id == ctx.company_id,
                GovernmentProcurementFileResponsible.file_id == expediente.id,
                GovernmentProcurementFileResponsible.fin_efectivo.is_(None),
                GovernmentProcurementFileResponsible.rol.in_(["RESPONSABLE", "SUSTANCIACION"]),
            )
            .all()
        )
        responsables_por_id = {r.id: r for r in responsables_rows}
        responsables_validos: list[GovernmentProcurementFileResponsible] = []
        for rid in responsable_ids:
            encontrado = responsables_por_id.get(rid)
            if encontrado is None:
                raise _err("responsables", "El responsable no es un responsable vigente del expediente")
            responsables_validos.append(encontrado)

        if politica and politica.exige_identidad:
            if oficial_actor_id is None:
                raise PermissionDeniedError(
                    code="GOV_DECISION_IDENTITY_REQUIRED",
                    message="La cuenta debe estar vinculada a un funcionario",
                )
            if oficial_actor_id not in {r.official_id for r in responsables_validos}:
                raise PermissionDeniedError(
                    code="GOV_DECISION_NOT_RESPONSIBLE",
                    message="Solo un responsable del expediente registra la recomendación",
                )

        verificar_antes_de_asumir_funcion(
            db,
            ctx,
            expediente,
            "EVALUADOR",
            user_ids=[ctx.user_id],
            official_ids=[r.official_id for r in responsables_validos],
        )

    ofertas_abiertas = (
        db.query(GovernmentProcurementOffer)
        .join(
            GovernmentProcurementOpeningOffer,
            GovernmentProcurementOpeningOffer.offer_id == GovernmentProcurementOffer.id,
        )
        .filter(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
        .order_by(GovernmentProcurementOffer.numero)
        .all()
    )
    ofertas_abiertas_ids = {o.id for o in ofertas_abiertas}

    rechazos_in = cuerpo.get("rechazos") or []
    rechazos_ids: set[str] = set()
    for r in rechazos_in:
        offer_id = r.get("offer_id")
        if offer_id not in ofertas_abiertas_ids:
            raise _err("rechazos", "Oferta no válida para rechazo")
        if offer_id in rechazos_ids:
            raise _err("rechazos", "Oferta repetida en rechazos")
        rechazos_ids.add(offer_id)
        causal = r.get("causal")
        if causal not in CAUSALES_RECHAZO:
            raise _err("rechazos", "Causal de rechazo no válida")
        motivacion = (r.get("motivacion") or "").strip()
        if not motivacion:
            raise _err("rechazos", "La motivación del rechazo es obligatoria")

    resultado = cuerpo.get("resultado_recomendado")
    if resultado not in RESULTADOS_RECOMENDACION:
        raise _err("resultado_recomendado", "Resultado no válido")

    opciones_in = cuerpo.get("opciones") or []
    causal_desierta = cuerpo.get("causal_desierta")

    if resultado == "ADJUDICAR":
        if not opciones_in:
            raise _err("opciones", "Debe indicar al menos una opción")
        posiciones = [o.get("posicion") for o in opciones_in]
        if posiciones != list(range(1, len(posiciones) + 1)):
            raise _err("opciones", "Las posiciones deben ser consecutivas desde 1")
        if len(posiciones) > 3:
            raise _err("opciones", "Máximo tres opciones")
        opciones_ofertas: set[str] = set()
        for o in opciones_in:
            offer_id = o.get("offer_id")
            if offer_id not in ofertas_abiertas_ids:
                raise _err("opciones", "Oferta no válida para opción")
            if offer_id in rechazos_ids:
                raise _err("opciones", "Una oferta rechazada no puede ser opción")
            if offer_id in opciones_ofertas:
                raise _err("opciones", "Oferta repetida en opciones")
            opciones_ofertas.add(offer_id)
        if causal_desierta is not None:
            raise _err("causal_desierta", "No aplica causal de desierta al adjudicar")
    else:
        if opciones_in:
            raise _err("opciones", "Las opciones solo aplican al resultado Adjudicar")
        if resultado == "DECLARAR_DESIERTA":
            if causal_desierta not in CAUSALES_DESIERTA:
                raise _err("causal_desierta", "Causal de desierta obligatoria y válida")
            if causal_desierta == "LCP113_2":
                if rechazos_ids != ofertas_abiertas_ids:
                    raise _err("rechazos", "LCP113_2 exige rechazar todas las ofertas abiertas")
            if causal_desierta == "LCP113_1":
                if ofertas_abiertas_ids:
                    raise _err("causal_desierta", "LCP113_1 exige que no haya ofertas abiertas")
        else:
            if causal_desierta is not None:
                raise _err("causal_desierta", "La causal de desierta no aplica a este resultado")

    textos = {
        "motivacion": cuerpo.get("motivacion"),
        "examen_legal": cuerpo.get("examen_legal"),
        "examen_financiero": cuerpo.get("examen_financiero"),
        "examen_tecnico": cuerpo.get("examen_tecnico"),
        "resultado_matriz": cuerpo.get("resultado_matriz"),
    }
    for campo, valor in textos.items():
        if not valor or not str(valor).strip():
            raise _err(campo, "Texto obligatorio")

    evaluar_antes_de_actuar(db, ctx, "PROC03_RECOMENDAR", "GovernmentProcurementFile", str(expediente.id))

    comision_nombre = ""
    if expediente.committee_id:
        c = db.get(GovernmentProcurementCommittee, expediente.committee_id)
        if c:
            comision_nombre = c.nombre

    oficiales = {
        str(o.id): o
        for o in db.query(GovernmentOfficial)
        .filter(GovernmentOfficial.company_id == ctx.company_id)
        .all()
    }
    firmantes_snapshot = []
    if expediente.committee_id:
        for fid in firmante_ids:
            miembro = next((m for m in miembros if m.id == fid), None)
            if miembro:
                oficial = oficiales.get(str(miembro.official_id))
                firmantes_snapshot.append(
                    {
                        "oficial": oficial.nombre if oficial else "",
                        "funcion": miembro.funcion,
                        "condicion": miembro.condicion,
                    }
                )
    else:
        responsables_oficiales = [
            {
                "oficial": oficiales[str(resp.official_id)].nombre
                if str(resp.official_id) in oficiales
                else "",
                "funcion": "RESPONSABLE",
                "condicion": resp.rol,
            }
            for resp in responsables_validos
        ]
        firmantes_snapshot = responsables_oficiales
        comision_nombre = f"Sin comisión: {expediente.comision_no_aplica_motivo}"

    ofertas_snapshot = []
    for oferta in ofertas_abiertas:
        resultados = []
        for rpo in evaluacion.get("resultados_por_oferta", []):
            if rpo.get("oferta_id") == oferta.id:
                rc = rpo.get("resultado_comision")
                if rc:
                    valor = rc.get("puntaje") if rc.get("puntaje") is not None else rc.get("cumple")
                    resultados.append(
                        {
                            "aspecto": rpo.get("aspecto", ""),
                            "criterio": rpo.get("criterio", ""),
                            "valor": valor,
                        }
                    )
        ofertas_snapshot.append(
            {
                "oferta": f"O-{oferta.numero:02d}",
                "oferente": oferta.oferente_nombre,
                "resultados": resultados,
            }
        )

    rechazos_snapshot = []
    for r in rechazos_in:
        oferta_rechazo: GovernmentProcurementOffer | None = next(
            (o for o in ofertas_abiertas if str(o.id) == str(r.get("offer_id"))), None
        )
        rechazos_snapshot.append(
            {
                "offer_id": r.get("offer_id"),
                "oferta": f"O-{oferta_rechazo.numero:02d}" if oferta_rechazo else "O-??",
                "oferente": oferta_rechazo.oferente_nombre if oferta_rechazo else "",
                "causal": r.get("causal"),
                "causal_etiqueta": CAUSALES_RECHAZO.get(r.get("causal"), r.get("causal")),
                "motivacion": r.get("motivacion"),
            }
        )

    opciones_snapshot = []
    for o in opciones_in:
        oferta_opcion: GovernmentProcurementOffer | None = next(
            (x for x in ofertas_abiertas if str(x.id) == str(o.get("offer_id"))), None
        )
        opciones_snapshot.append(
            {
                "posicion": o.get("posicion"),
                "offer_id": o.get("offer_id"),
                "oferta": f"O-{oferta_opcion.numero:02d}" if oferta_opcion else "O-??",
                "oferente": oferta_opcion.oferente_nombre if oferta_opcion else "",
            }
        )

    snapshot: dict[str, Any] = {
        "expediente": {"numero": expediente.numero, "objeto": expediente.objeto},
        "comision": comision_nombre,
        "firmantes": firmantes_snapshot,
        "matriz": evaluacion.get("matriz"),
        "ofertas": ofertas_snapshot,
        "rechazos": rechazos_snapshot,
        "opciones": opciones_snapshot,
        "resultado": resultado,
        "resultado_etiqueta": RESULTADOS_RECOMENDACION.get(resultado, resultado),
        "causal_desierta": causal_desierta,
        "causal_etiqueta": CAUSALES_DESIERTA.get(causal_desierta) if causal_desierta else None,
        "motivacion": cuerpo.get("motivacion"),
        "examen_legal": cuerpo.get("examen_legal"),
        "examen_financiero": cuerpo.get("examen_financiero"),
        "examen_tecnico": cuerpo.get("examen_tecnico"),
        "resultado_matriz": cuerpo.get("resultado_matriz"),
        "medidas_promocion": cuerpo.get("medidas_promocion"),
        "evaluacion_concluida_en": evaluacion_concluida_en,
    }

    max_numero = db.scalar(
        select(func.max(GovernmentProcurementRecommendation.numero)).where(
            GovernmentProcurementRecommendation.company_id == ctx.company_id,
            GovernmentProcurementRecommendation.file_id == expediente.id,
        )
    )
    numero = (max_numero or 0) + 1
    referencia = f"REC-{numero:02d}"

    ahora = instante_actual()
    if vigente is not None and sustituye_id == vigente.id:
        vigente.estado = "SUSTITUIDA"
        vigente.sustituida_en = ahora
        db.flush()

    pdf_bytes = _render_informe(snapshot, referencia, ahora)
    storage = get_storage()
    storage_key = generate_storage_key(ctx.company_id)
    size, sha = storage.put(storage_key, io.BytesIO(pdf_bytes))
    if sha != hashlib.sha256(pdf_bytes).hexdigest() or size != len(pdf_bytes):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )
    if not storage.verify(storage_key, sha):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )

    saneado = re.sub(r"[^A-Za-z0-9-]", "", str(expediente.numero))
    informe_nombre = f"informe-recomendacion-{referencia}-{saneado}.pdf"

    regla_guardada: dict[str, Any] | None = None
    if expediente.committee_id and regla is not None and d is not None:
        regla_guardada = {
            "modo": "COMISION",
            "etiqueta": regla.get("etiqueta"),
            "quorum": regla.get("quorum"),
            "decision": regla.get("decision"),
            "politica_codigo": regla.get("politica_codigo"),
            "politica_version": regla.get("politica_version"),
            "votos_a_favor": d.get("votos_a_favor"),
            "requerido": d.get("requerido"),
            "base": d.get("base"),
            "dirimente_usado": d.get("dirimente_usado"),
        }
    else:
        regla_guardada = {
            "modo": "UNIDAD_CONTRATANTE",
            "motivo": expediente.comision_no_aplica_motivo,
        }

    recomendacion = GovernmentProcurementRecommendation(
        company_id=ctx.company_id,
        file_id=expediente.id,
        committee_id=expediente.committee_id,
        modo="COMISION" if expediente.committee_id else "UNIDAD_CONTRATANTE",
        regla=regla_guardada,
        numero=numero,
        estado="EMITIDA",
        resultado_recomendado=resultado,
        causal_desierta=causal_desierta,
        motivacion=cuerpo.get("motivacion"),
        examen_legal=cuerpo.get("examen_legal"),
        examen_financiero=cuerpo.get("examen_financiero"),
        examen_tecnico=cuerpo.get("examen_tecnico"),
        resultado_matriz=cuerpo.get("resultado_matriz"),
        medidas_promocion=cuerpo.get("medidas_promocion"),
        matrix_id=evaluacion["matriz"]["id"] if evaluacion.get("matriz") else "",
        matrix_version=evaluacion["matriz"]["version"] if evaluacion.get("matriz") else 0,
        evaluacion_concluida_en=datetime.fromisoformat(evaluacion_concluida_en)
        if evaluacion_concluida_en
        else ahora,
        snapshot=snapshot,
        informe_storage_key=storage_key,
        informe_sha256=sha,
        informe_tamano=size,
        informe_nombre=informe_nombre,
        emitida_en=ahora,
        emitida_por=str(user.id),
        official_id=oficial_actor_id,
        sustituye_id=sustituye_id,
        motivo_sustitucion=cuerpo.get("motivo_sustitucion") if sustituye_id else None,
        sustituida_en=None,
        created_by=ctx.user_id,
    )
    db.add(recomendacion)
    db.flush()

    if expediente.committee_id and d is not None:
        votantes = set(d["quorum"].get("votantes_presentes", []))
        presidente_vota = bool(regla.get("presidente_vota")) if regla else False
        for fid in firmante_ids:
            miembro = next((m for m in miembros if m.id == fid), None)
            if miembro:
                voto = cuenta_voto(
                    miembro,
                    presentes=set(presentes),
                    inh=inh,
                    votantes_presentes=votantes,
                    presidente_vota=presidente_vota,
                )
                db.add(
                    GovernmentProcurementRecommendationSignatory(
                        company_id=ctx.company_id,
                        recommendation_id=recomendacion.id,
                        member_id=miembro.id,
                        official_id=miembro.official_id,
                        funcion=miembro.funcion,
                        condicion=miembro.condicion,
                        cuenta_voto=voto,
                        created_by=ctx.user_id,
                    )
                )
    else:
        for resp in responsables_validos:
            db.add(
                GovernmentProcurementRecommendationResponsible(
                    company_id=ctx.company_id,
                    recommendation_id=recomendacion.id,
                    responsible_id=resp.id,
                    official_id=resp.official_id,
                    rol=resp.rol,
                    created_by=str(user.id),
                )
            )

    for o in opciones_in:
        db.add(
            GovernmentProcurementRecommendationOption(
                company_id=ctx.company_id,
                recommendation_id=recomendacion.id,
                offer_id=o.get("offer_id"),
                posicion=o.get("posicion"),
                created_by=ctx.user_id,
            )
        )

    for r in rechazos_in:
        db.add(
            GovernmentProcurementRecommendationRejection(
                company_id=ctx.company_id,
                recommendation_id=recomendacion.id,
                offer_id=r.get("offer_id"),
                causal=r.get("causal"),
                motivacion=r.get("motivacion"),
                created_by=ctx.user_id,
            )
        )

    expediente.version += 1
    db.flush()

    titulo = f"Recomendación {referencia}: {RESULTADOS_RECOMENDACION.get(resultado, resultado)}"
    if resultado == "ADJUDICAR" and opciones_snapshot:
        titulo += f" · primera opción {opciones_snapshot[0].get('oferta', '')}"
    _evento(db, ctx, expediente, "RECOMENDACION", hoy_de_negocio(), titulo)

    for r in rechazos_snapshot:
        _evento(
            db,
            ctx,
            expediente,
            "RECHAZO_OFERTA",
            hoy_de_negocio(),
            f"Oferta {r.get('oferta', '')} rechazada: {r.get('causal_etiqueta', '')}",
        )

    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_RECOMMENDATION_ISSUED",
        expediente_id=str(expediente.id),
        after={
            "recomendacion": referencia,
            "resultado": resultado,
            "opciones": [o.get("oferta") for o in opciones_snapshot],
            "rechazos": [r.get("oferta") for r in rechazos_snapshot],
            "firmantes": len(firmante_ids) if expediente.committee_id else len(responsables_validos),
            "modo": "COMISION" if expediente.committee_id else "UNIDAD_CONTRATANTE",
            "sustituye": f"REC-{vigente.numero:02d}" if vigente and sustituye_id else None,
        },
    )
    if vigente is not None and sustituye_id == vigente.id:
        _auditar(
            db,
            ctx,
            "GOV_PROCUREMENT_RECOMMENDATION_SUPERSEDED",
            expediente_id=str(expediente.id),
            after={
                "recomendacion": f"REC-{vigente.numero:02d}",
                "sustituye": referencia,
            },
            motivo=cuerpo.get("motivo_sustitucion"),
        )

    return obtener_estado_decision(db, ctx, user, expediente_id)


def abrir_informe(
    db: Session,
    ctx: CompanyContext,
    user: User,
    expediente_id: str,
    recomendacion_id: str,
) -> tuple[str, BinaryIO, int]:
    expediente = _cargar(db, ctx, expediente_id)
    recomendacion = db.scalar(
        select(GovernmentProcurementRecommendation).where(
            GovernmentProcurementRecommendation.id == recomendacion_id,
            GovernmentProcurementRecommendation.company_id == ctx.company_id,
            GovernmentProcurementRecommendation.file_id == expediente.id,
        )
    )
    if recomendacion is None:
        raise NotFoundError("GOV_RECOMMENDATION_NOT_FOUND", "Recomendación no encontrada")

    storage = get_storage()
    if not storage.verify(recomendacion.informe_storage_key, recomendacion.informe_sha256):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )
    stream = storage.open(recomendacion.informe_storage_key)
    return recomendacion.informe_nombre, stream, recomendacion.informe_tamano
