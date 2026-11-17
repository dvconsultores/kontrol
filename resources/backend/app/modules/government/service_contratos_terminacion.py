"""Terminación, resolución o rescisión del contrato (CNT-07, GOV-CNT-008). LCP arts. 145 y 152–156; RLCP arts. 190–194; LOPA arts. 9 y 73–74. No crea pagos, causado, penalidades ni anulaciones: consume CNT-03, PROC-10, BUD-08, DOC-02 y DOC-04."""

import csv
import hashlib
import io
import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents.service import (
    congelar_vinculo,
    sellar_documento,
    verificar_integridad,
)
from app.modules.government.garantias_reglas import ETIQUETA_ESTADO as ETIQUETA_ESTADO_GARANTIA
from app.modules.government.models import (
    CAUSALES_TERMINACION_CONTRATO,
    FIGURAS_TERMINACION_CONTRATO,
    GovernmentAct,
    GovernmentContract,
    GovernmentContractAmendment,
    GovernmentContractDeliverable,
    GovernmentContractDeliverableSubmission,
    GovernmentContractExecutionAct,
    GovernmentContractMilestone,
    GovernmentContractSupervisorAssignment,
    GovernmentContractTermination,
    GovernmentContractValuation,
    GovernmentNotification,
    GovernmentPosition,
    GovernmentProcurementFile,
)
from app.modules.government.schemas_notificaciones import clave_identificacion
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_contratos import (
    ENTIDAD,
    _auditar,
    _documento_valido,
    _documentos_elegibles,
    _garantias,
    _t,
)
from app.modules.government.service_contratos_ejecucion import _flujo, ejecucion
from app.modules.government.service_contratos_supervision import _etiqueta_acto
from app.modules.government.service_contratos_terminos import terminos_efectivos
from app.modules.government.service_expediente_contractual import (
    _lineas_compromiso,
    _permisos,
    compromisos_trazados,
)
from app.modules.government.service_expedientes import _evento
from app.modules.government.service_identidad import exigir_autoridad_funcional
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.situacion_contractual import (
    ETIQUETA_FIGURA,
    situacion_contractual,
    terminacion_formalizada,
)
from app.shared.audit import record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual

RESCISIONES = ("RESCISION_NO_IMPUTABLE", "RESCISION_IMPUTABLE")
CATALOGO: dict[str, dict[str, Any]] = {
    "RESCISION_NO_IMPUTABLE": {
        "fuente": "LCP art. 152; RLCP arts. 190–191",
        "causales": (
            (
                "INTERES_DEL_CONTRATANTE",
                "Decisión del contratante sin incumplimiento del contratista",
                "LCP art. 152",
            ),
        ),
    },
    "RESOLUCION_MUTUO_ACUERDO": {
        "fuente": "LCP art. 154; RLCP art. 192",
        "causales": (
            (
                "CIRCUNSTANCIAS_ACONSEJABLES",
                "Las circunstancias lo hacen aconsejable",
                "LCP art. 154",
            ),
        ),
    },
    "RESCISION_IMPUTABLE": {
        "fuente": "LCP arts. 155–156; RLCP arts. 193–194",
        "causales": (
            ("LCP_155_1", "Ejecuta los trabajos en desacuerdo con el contrato o de forma que no pueda cumplir en el término", "LCP art. 155, num. 1"),
            ("LCP_155_2", "Disolución o liquidación de la empresa, o atraso o quiebra", "LCP art. 155, num. 2"),
            ("LCP_155_3", "Cede o traspasa el contrato sin autorización escrita", "LCP art. 155, num. 3"),
            ("LCP_155_4", "Incumple el inicio de la ejecución en el plazo", "LCP art. 155, num. 4"),
            ("LCP_155_5", "Comete errores u omisiones sustanciales durante la ejecución", "LCP art. 155, num. 5"),
            ("LCP_155_6", "Incumple sus obligaciones laborales durante la ejecución", "LCP art. 155, num. 6"),
            ("LCP_155_7", "Obtuvo el contrato mediante tráfico de influencias, sobornos o documentos falsos", "LCP art. 155, num. 7"),
            ("LCP_155_8", "Otra falta o incumplimiento de las obligaciones del contrato", "LCP art. 155, num. 8"),
            ("LCP_155_9", "No mantiene al frente de la obra un ingeniero residente", "LCP art. 155, num. 9"),
            ("CLAUSULA_CONTRATO", "Causal establecida en el contrato", "RLCP art. 193"),
        ),
    },
}
REGLA_INDEMNIZACION = {
    "RESCISION_NO_IMPUTABLE": "RLCP art. 191: precio de lo ejecutado, materiales adquiridos e indemnización del 10 % al 5 % de lo no ejecutado según el avance.",
    "RESOLUCION_MUTUO_ACUERDO": "LCP art. 154: no procede indemnización alguna.",
    "RESCISION_IMPUTABLE": "RLCP art. 194: indemnización a favor del contratante en la misma forma y cuantía del art. 191; puede deducirse o ejecutarse la garantía en PROC-10.",
}
EFECTOS = "Esta actuación no crea pagos, causado, penalidades ni anulaciones presupuestarias."
CAMPOS = (
    "figura",
    "causal",
    "causal_referencia",
    "hechos",
    "fundamento",
    "act_id",
    "apertura_act_id",
    "document_id",
    "document_version_id",
    "conclusion_alcance",
    "conclusion_hasta",
)


def _inv(campo: str, motivo: str, mensaje: str) -> KontrolError:
    return KontrolError(
        "GOV_CONTRACT_TERMINATION_INVALID",
        "Datos de la terminación inválidos",
        field_errors={campo: [mensaje]},
        details={"campo": campo, "motivo": motivo},
        status_code=422,
    )


def _contrato(db: Session, ctx: CompanyContext, contrato_id: str, bloquear: bool) -> GovernmentContract:
    consulta = select(GovernmentContract).where(
        GovernmentContract.id == contrato_id,
        GovernmentContract.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    contrato = db.execute(consulta).scalar_one_or_none()
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    return contrato


def _formalizado(c: GovernmentContract) -> None:
    if c.estado != "FORMALIZADO":
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_NOT_FORMALIZED",
            "Solo un contrato u orden formalizado admite terminación, resolución o rescisión",
        )


def _borrador(db: Session, c: GovernmentContract, bloquear: bool) -> GovernmentContractTermination | None:
    consulta = select(GovernmentContractTermination).where(
        GovernmentContractTermination.company_id == c.company_id,
        GovernmentContractTermination.contract_id == c.id,
        GovernmentContractTermination.estado == "BORRADOR",
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.execute(consulta).scalar_one_or_none()


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    version: int | None,
) -> tuple[GovernmentContract, GovernmentContractTermination]:
    if version is None:
        raise KontrolError(
            "GOV_CONTRACT_TERMINATION_IF_MATCH_REQUIRED",
            "Se requiere la versión del borrador",
            status_code=428,
        )
    c = _contrato(db, ctx, contrato_id, bloquear=True)
    _formalizado(c)
    t = _borrador(db, c, bloquear=True)
    if t is None:
        raise NotFoundError("GOV_CONTRACT_TERMINATION_NOT_FOUND", "No hay un borrador de terminación")
    if t.version != version:
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_STALE",
            "El borrador fue cambiado por otro usuario",
            details={"version_actual": t.version},
        )
    return c, t


def _acto(db: Session, ctx: CompanyContext, acto_id: str | None) -> GovernmentAct | None:
    if not acto_id:
        return None
    return db.execute(
        select(GovernmentAct).where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()


def _acto_publico(db: Session, acto: GovernmentAct) -> dict[str, Any]:
    cargo = db.get(GovernmentPosition, acto.cargo_id)
    return {
        "id": acto.id,
        "etiqueta": _etiqueta_acto(acto),
        "tipo": acto.tipo,
        "numero": acto.numero,
        "fecha": acto.fecha.isoformat(),
        "estado": acto.status,
        "fecha_eficacia": acto.fecha_eficacia.isoformat() if acto.fecha_eficacia else None,
        "emisor_cargo": cargo.name if cargo else "",
        "funcionario": acto.funcionario,
        "enlace": f"/gobierno/actos/{acto.id}",
    }


def _acto_valido(db: Session, acto: GovernmentAct) -> bool:
    return (
        acto.caracter == "PARTICULAR"
        and acto.status == "EFICAZ"
        and acto.fecha_eficacia is not None
        and acto.competencia_accion == "APROBAR"
        and acto.competencia_materia == "CONTRATACIONES"
    )


def _autoridad(db: Session, acto: GovernmentAct) -> bool:
    return _autoridad_valida(
        db,
        acto.company_id,
        str(acto.cargo_id),
        acto.fecha,
        "APROBAR",
        "CONTRATACIONES",
    )


def _notificaciones(db: Session, ctx: CompanyContext, c: GovernmentContract, acto_id: str | None) -> list[dict[str, Any]]:
    if not acto_id:
        return []
    notificaciones = db.scalars(
        select(GovernmentNotification).where(
            GovernmentNotification.company_id == ctx.company_id,
            GovernmentNotification.act_id == acto_id,
            GovernmentNotification.status != "ANULADA",
        )
    ).all()
    return [
        {
            "id": n.id,
            "destinatario": n.nombre,
            "identificacion": n.identificacion,
            "estado": n.status,
            "fecha_notificacion": n.fecha_notificacion.isoformat() if n.fecha_notificacion else None,
            "es_contratista": n.identificacion_clave == clave_identificacion(c.contratista_documento),
            "enlace": f"/gobierno/notificaciones/{n.id}",
        }
        for n in notificaciones
    ]


def _garantias_vista(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    return [
        {
            "referencia": g["referencia"],
            "tipo_etiqueta": g["tipo_etiqueta"],
            "emisor": g["emisor"],
            "monto": g["monto"],
            "moneda": g["moneda"],
            "estado": g["estado"],
            "estado_etiqueta": ETIQUETA_ESTADO_GARANTIA.get(g["estado"], g["estado"]),
            "vigente": g["estado"] == "REGISTRADA",
            "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
        }
        for g in _garantias(db, c)
    ]


def _hechos_posteriores(db: Session, c: GovernmentContract, limite: date) -> list[dict[str, str]]:
    hechos: list[dict[str, str]] = []
    ejecuciones = db.scalars(
        select(GovernmentContractExecutionAct).where(
            GovernmentContractExecutionAct.contract_id == c.id,
            GovernmentContractExecutionAct.tipo.in_(("INICIO", "TERMINACION")),
            GovernmentContractExecutionAct.fecha > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-03", "tipo": e.tipo, "fecha": e.fecha.isoformat()} for e in ejecuciones)
    hitos = db.scalars(
        select(GovernmentContractMilestone).where(
            GovernmentContractMilestone.contract_id == c.id,
            GovernmentContractMilestone.estado == "VIGENTE",
            GovernmentContractMilestone.fecha_prevista > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-03", "tipo": "HITO", "fecha": h.fecha_prevista.isoformat()} for h in hitos)
    entregables = db.scalars(
        select(GovernmentContractDeliverable).where(
            GovernmentContractDeliverable.contract_id == c.id,
            GovernmentContractDeliverable.estado == "VIGENTE",
            GovernmentContractDeliverable.fecha_vencimiento > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-03", "tipo": "ENTREGABLE", "fecha": e.fecha_vencimiento.isoformat()} for e in entregables)
    entregas = db.scalars(
        select(GovernmentContractDeliverableSubmission).where(
            GovernmentContractDeliverableSubmission.contract_id == c.id,
            GovernmentContractDeliverableSubmission.fecha_entrega > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-03", "tipo": "ENTREGA", "fecha": s.fecha_entrega.isoformat()} for s in entregas)
    valuaciones = db.scalars(
        select(GovernmentContractValuation).where(
            GovernmentContractValuation.contract_id == c.id,
            GovernmentContractValuation.estado != "ANULADA",
            GovernmentContractValuation.periodo_hasta > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-03", "tipo": "VALUACION", "fecha": v.periodo_hasta.isoformat()} for v in valuaciones)
    modificaciones = db.scalars(
        select(GovernmentContractAmendment).where(
            GovernmentContractAmendment.contract_id == c.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
            GovernmentContractAmendment.vigente_desde > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-02", "tipo": "MODIFICACION", "fecha": m.vigente_desde.isoformat() if m.vigente_desde else ""} for m in modificaciones)
    designaciones = db.scalars(
        select(GovernmentContractSupervisorAssignment).where(
            GovernmentContractSupervisorAssignment.contract_id == c.id,
            GovernmentContractSupervisorAssignment.desde > limite,
        )
    ).all()
    hechos.extend({"proceso": "CNT-04", "tipo": "DESIGNACION", "fecha": d.desde.isoformat()} for d in designaciones)
    return hechos


def _consecuencias(db: Session, ctx: CompanyContext, c: GovernmentContract, figura: str | None, fecha_corte: date) -> dict[str, Any]:
    ej = ejecucion(db, ctx, str(c.id))
    r = ej["resumen"]
    term = terminos_efectivos(db, c, fecha_corte)
    monto = term["monto"]
    conformado = Decimal(r["valuado_conformado"])
    recepciones_validas = [x for x in ej["recepciones"] if x["estado"] != "ANULADA"]
    compromisos = [
        {
            "codigo": comp.codigo,
            "estado": comp.estado,
            "total": _t(sum((linea.monto for linea in _lineas_compromiso(db, comp)), Decimal("0"))),
            "moneda": comp.moneda,
            "enlace": f"/gobierno/presupuesto/ejercicios/{comp.year_id}",
        }
        for comp in compromisos_trazados(db, c)
    ]
    if figura is None:
        indemnizacion = None
    elif figura == "RESOLUCION_MUTUO_ACUERDO":
        indemnizacion = {
            "regla": REGLA_INDEMNIZACION[figura],
            "estado": "NO_PROCEDE",
            "mensaje": "No procede indemnización.",
        }
    else:
        indemnizacion = {
            "regla": REGLA_INDEMNIZACION[figura],
            "estado": "CONSECUENCIA_PENDIENTE_CNT06",
            "mensaje": "La cuantía no se calcula aquí: corresponde a CNT-06 (penalidades, retenciones e indemnizaciones).",
        }
    return {
        "fecha_corte": fecha_corte.isoformat(),
        "moneda": term["moneda"],
        "monto_vigente": _t(monto),
        "valuado_conformado": r["valuado_conformado"],
        "valuado_presentado": r["valuado_presentado"],
        "saldo_no_ejecutado": _t(monto - conformado),
        "saldo_por_valuar_cnt03": r["saldo"],
        "facturado_conforme": r["facturado"],
        "recepciones": {
            "total": len(recepciones_validas),
            "definitiva": any(x["tipo"] == "DEFINITIVA" for x in recepciones_validas),
        },
        "estado_ejecucion": r["estado_ejecucion"],
        "estado_ejecucion_etiqueta": r["estado_etiqueta"],
        "hitos": {"total": r["hitos_total"], "cumplidos": r["hitos_cumplidos"]},
        "compromisos": compromisos,
        "indemnizacion": indemnizacion,
        "efectos": EFECTOS,
    }


def _requisitos(db: Session, ctx: CompanyContext, c: GovernmentContract, t: GovernmentContractTermination) -> list[dict[str, Any]]:
    requisitos: list[dict[str, Any]] = []

    figura_ok = t.figura in FIGURAS_TERMINACION_CONTRATO
    requisitos.append({"codigo": "FIGURA", "cumplido": figura_ok, "mensaje": "Cumplido" if figura_ok else "Seleccione una figura jurídica de terminación válida."})

    causal_ok = t.causal in [x[0] for x in CATALOGO.get(t.figura, {}).get("causales", ())]
    if t.causal == "LCP_155_9":
        expediente = db.get(GovernmentProcurementFile, c.file_id)
        causal_ok = causal_ok and expediente is not None and _flujo(expediente) == "OBRAS"
        mensaje_causal = "Cumplido" if causal_ok else "La causal LCP_155_9 solo aplica a contratos de obras."
    elif t.causal == "CLAUSULA_CONTRATO":
        causal_ok = causal_ok and bool(t.causal_referencia and t.causal_referencia.strip())
        mensaje_causal = "Cumplido" if causal_ok else "Indique la cláusula contractual que se invoca."
    else:
        mensaje_causal = "Cumplido" if causal_ok else "Seleccione una causal válida para la figura jurídica."
    requisitos.append({"codigo": "CAUSAL", "cumplido": causal_ok, "mensaje": mensaje_causal})

    textos_ok = (
        t.hechos is not None
        and t.fundamento is not None
        and 20 <= len(t.hechos.strip()) <= 4000
        and 20 <= len(t.fundamento.strip()) <= 4000
    )
    requisitos.append(
        {
            "codigo": "MOTIVACION",
            "cumplido": textos_ok,
            "mensaje": "Cumplido" if textos_ok else "Los hechos y el fundamento deben tener entre 20 y 4000 caracteres.",
        }
    )

    acto = _acto(db, ctx, t.act_id) if t.act_id else None
    acto_ok = (
        acto is not None
        and _acto_valido(db, acto)
        and c.fecha_formalizacion is not None
        and acto.fecha >= c.fecha_formalizacion
        and bool(acto.hechos and acto.hechos.strip())
        and bool(acto.fundamentos and acto.fundamentos.strip())
    )
    requisitos.append(
        {
            "codigo": "ACTO_EFICAZ",
            "cumplido": acto_ok,
            "mensaje": "Cumplido" if acto_ok else "El acto decisorio debe ser particular, eficaz, posterior a la formalización y estar motivado.",
        }
    )

    aut_ok = acto is not None and _autoridad(db, acto)
    requisitos.append(
        {
            "codigo": "AUTORIDAD",
            "cumplido": aut_ok,
            "mensaje": "Cumplido" if aut_ok else "El cargo que emitió el acto debe tener competencia de Aprobar sobre Contrataciones en su fecha.",
        }
    )

    notificaciones = _notificaciones(db, ctx, c, str(acto.id)) if acto else []
    notif_contratista = any(n["es_contratista"] and n["estado"] == "NOTIFICADA" for n in notificaciones)
    requisitos.append(
        {
            "codigo": "NOTIFICACION_CONTRATISTA",
            "cumplido": notif_contratista,
            "mensaje": "Cumplido" if notif_contratista else "Notifique el acto al contratista.",
        }
    )

    garantias_vigentes = [g for g in _garantias_vista(db, c) if g["vigente"]]
    if t.figura in RESCISIONES and garantias_vigentes:
        notif_garantes = any(not n["es_contratista"] and n["estado"] == "NOTIFICADA" for n in notificaciones)
        requisitos.append(
            {
                "codigo": "NOTIFICACION_GARANTES",
                "cumplido": notif_garantes,
                "mensaje": "Cumplido" if notif_garantes else "Notifique el acto a los garantes.",
            }
        )

    if t.figura == "RESCISION_IMPUTABLE":
        ap = _acto(db, ctx, t.apertura_act_id) if t.apertura_act_id else None
        apertura_ok = (
            ap is not None
            and acto is not None
            and ap.id != t.act_id
            and _acto_valido(db, ap)
            and _autoridad(db, ap)
            and ap.fecha_eficacia is not None
            and ap.fecha_eficacia < acto.fecha
        )
        requisitos.append(
            {
                "codigo": "APERTURA",
                "cumplido": apertura_ok,
                "mensaje": "Cumplido" if apertura_ok else "La rescisión imputable requiere un acto de apertura válido, distinto y anterior al decisorio.",
            }
        )

    if t.figura == "RESOLUCION_MUTUO_ACUERDO":
        r = _documento_valido(db, ctx, c, t.document_id)
        doc_ok = (
            r is not None
            and str(r[1].id) == t.document_version_id
            and r[1].sha256 == t.documento_sha256
            and verificar_integridad(db, r[1])
        )
        mensaje_doc = "Cumplido" if doc_ok else "Vincule el acuerdo firmado al expediente con integridad verificada."
        requisitos.append({"codigo": "DOCUMENTO_ACUERDO", "cumplido": doc_ok, "mensaje": mensaje_doc})

    if t.conclusion_hasta:
        conclusion_ok = (
            t.figura in RESCISIONES
            and t.conclusion_alcance is not None
            and 10 <= len(t.conclusion_alcance.strip()) <= 1000
            and (acto is None or (acto.fecha_eficacia is not None and t.conclusion_hasta > acto.fecha_eficacia))
        )
        requisitos.append(
            {
                "codigo": "CONCLUSION",
                "cumplido": conclusion_ok,
                "mensaje": "Cumplido" if conclusion_ok else "La conclusión autorizada exige una rescisión, alcance entre 10 y 1000 caracteres y fecha posterior a la eficacia del acto.",
            }
        )

    if acto and acto.fecha_eficacia:
        limite = t.conclusion_hasta or acto.fecha_eficacia
        hechos = _hechos_posteriores(db, c, limite)
        requisitos.append(
            {
                "codigo": "SIN_HECHOS_POSTERIORES",
                "cumplido": not hechos,
                "mensaje": "Cumplido" if not hechos else "Existen hechos posteriores a la fecha de extinción.",
            }
        )
    else:
        requisitos.append(
            {
                "codigo": "SIN_HECHOS_POSTERIORES",
                "cumplido": True,
                "mensaje": "Se comprueba al vincular el acto",
            }
        )

    return requisitos


def _terminacion_publica(db: Session, t: GovernmentContractTermination) -> dict[str, Any]:
    causal_etiqueta = None
    for figura in CATALOGO.get(t.figura, {}).get("causales", ()):
        if figura[0] == t.causal:
            causal_etiqueta = figura[1]
            break
    acto = db.get(GovernmentAct, t.act_id) if t.act_id else None
    apertura = db.get(GovernmentAct, t.apertura_act_id) if t.apertura_act_id else None
    return {
        "id": t.id,
        "codigo": t.codigo,
        "estado": t.estado,
        "version": t.version,
        "figura": t.figura,
        "figura_etiqueta": ETIQUETA_FIGURA.get(t.figura),
        "causal": t.causal,
        "causal_etiqueta": causal_etiqueta,
        "causal_referencia": t.causal_referencia,
        "hechos": t.hechos,
        "fundamento": t.fundamento,
        "acto": _acto_publico(db, acto) if acto else None,
        "apertura": _acto_publico(db, apertura) if apertura else None,
        "documento": {
            "id": t.document_id,
            "version_id": t.document_version_id,
            "titulo": t.documento_titulo,
            "sha256": t.documento_sha256,
        }
        if t.document_id
        else None,
        "conclusion": {
            "alcance": t.conclusion_alcance,
            "hasta": t.conclusion_hasta.isoformat(),
        }
        if t.conclusion_hasta
        else None,
        "fecha_acto": t.fecha_acto.isoformat() if t.fecha_acto else None,
        "fecha_eficacia": t.fecha_eficacia.isoformat() if t.fecha_eficacia else None,
        "formalizado_en": t.formalizado_en.isoformat() if t.formalizado_en else None,
        "formalizado_por": t.formalizado_por,
        "huella": t.huella,
    }


def _aplicar(db: Session, ctx: CompanyContext, c: GovernmentContract, t: GovernmentContractTermination, cuerpo: dict[str, Any]) -> None:
    for campo in CAMPOS:
        if campo not in cuerpo:
            continue
        valor = cuerpo[campo]
        if campo == "figura":
            if valor not in FIGURAS_TERMINACION_CONTRATO:
                raise _inv("figura", "FIGURA", "Figura jurídica no válida")
            if t.figura != valor:
                t.figura = valor
                t.causal = None
                t.causal_referencia = None
        elif campo == "causal":
            if valor is not None and valor not in CAUSALES_TERMINACION_CONTRATO:
                raise _inv("causal", "CAUSAL", "Causal no válida")
            t.causal = valor
        elif campo in ("causal_referencia", "hechos", "fundamento", "conclusion_alcance"):
            limite = {"causal_referencia": 200, "hechos": 4000, "fundamento": 4000, "conclusion_alcance": 1000}[campo]
            texto = valor.strip() if valor is not None else None
            if texto == "":
                texto = None
            if texto is not None and len(texto) > limite:
                raise _inv(campo, "MOTIVACION", "Texto demasiado largo")
            setattr(t, campo, texto)
        elif campo in ("act_id", "apertura_act_id"):
            if valor is not None and _acto(db, ctx, valor) is None:
                raise _inv(campo, "ACTO_EFICAZ", "Acto administrativo no encontrado")
            setattr(t, campo, valor)
        elif campo == "document_id":
            if valor is None:
                t.document_id = None
                t.document_version_id = None
                t.documento_sha256 = None
                t.documento_titulo = None
            else:
                r = _documento_valido(db, ctx, c, valor)
                if r is None:
                    raise _inv("document_id", "DOCUMENTO_ACUERDO", "El documento debe estar vinculado al expediente y disponible")
                doc, version_doc, _link = r
                t.document_id = valor
                t.document_version_id = str(version_doc.id)
                t.documento_sha256 = version_doc.sha256
                t.documento_titulo = doc.title
        elif campo == "conclusion_hasta":
            if valor is None:
                t.conclusion_hasta = None
            else:
                try:
                    t.conclusion_hasta = date.fromisoformat(str(valor))
                except (TypeError, ValueError):
                    raise _inv("conclusion_hasta", "CONCLUSION", "Fecha no válida") from None
        elif campo == "document_version_id":
            continue


def crear_borrador(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    c = _contrato(db, ctx, contrato_id, bloquear=True)
    _formalizado(c)
    if terminacion_formalizada(db, ctx.company_id, str(c.id)) is not None:
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_ALREADY_EXISTS",
            "El contrato ya tiene una terminación formalizada",
        )
    if _borrador(db, c, False) is not None:
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_DRAFT_EXISTS",
            "Ya hay un borrador de terminación en curso",
        )
    if cuerpo.get("figura") is None:
        raise _inv("figura", "FIGURA", "Figura jurídica no válida")
    evaluar_antes_de_actuar(db, ctx, "PROC03_TERMINACION_PREPARAR", ENTIDAD, str(c.file_id))
    t = GovernmentContractTermination(
        company_id=ctx.company_id,
        contract_id=str(c.id),
        file_id=str(c.file_id),
        estado="BORRADOR",
        figura=cuerpo["figura"],
        created_by=ctx.user_id,
    )
    _aplicar(db, ctx, c, t, cuerpo)
    db.add(t)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_contract_terminations_borrador"):
            raise ConflictError(
                "GOV_CONTRACT_TERMINATION_DRAFT_EXISTS",
                "Ya hay un borrador de terminación en curso",
            ) from error
        raise
    _auditar(db, ctx, "GOV_CONTRACT_TERMINATION_DRAFT_CREATED", str(c.file_id), {"contrato": c.codigo, "figura": t.figura})
    return vista(db, ctx, contrato_id)


def actualizar_borrador(db: Session, ctx: CompanyContext, contrato_id: str, version: int | None, cuerpo: dict[str, Any]) -> dict[str, Any]:
    c, t = _para_escribir(db, ctx, contrato_id, version)
    _aplicar(db, ctx, c, t, cuerpo)
    t.version += 1
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_TERMINATION_DRAFT_UPDATED",
        str(c.file_id),
        {"contrato": c.codigo, "figura": t.figura, "causal": t.causal},
    )
    return vista(db, ctx, contrato_id)


def descartar_borrador(db: Session, ctx: CompanyContext, contrato_id: str, version: int | None) -> None:
    c, t = _para_escribir(db, ctx, contrato_id, version)
    figura = t.figura
    db.delete(t)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_TERMINATION_DRAFT_DISCARDED",
        str(c.file_id),
        {"contrato": c.codigo, "figura": figura},
    )


def formalizar(db: Session, ctx: CompanyContext, user: Any, contrato_id: str, version: int | None) -> dict[str, Any]:
    c, t = _para_escribir(db, ctx, contrato_id, version)
    if terminacion_formalizada(db, ctx.company_id, str(c.id)) is not None:
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_ALREADY_EXISTS",
            "El contrato ya tiene una terminación formalizada",
        )
    reqs = _requisitos(db, ctx, c, t)
    acto = _acto(db, ctx, t.act_id) if t.act_id else None
    ap = _acto(db, ctx, t.apertura_act_id) if t.apertura_act_id else None
    dict_reqs = {req["codigo"]: req for req in reqs}
    if acto is not None and (not dict_reqs["AUTORIDAD"]["cumplido"] or (ap is not None and not _autoridad(db, ap))):
        record_audit_after_rollback(
            db,
            action="GOV_CONTRACT_TERMINATION_BLOCKED",
            entity_type=ENTIDAD,
            entity_id=str(c.file_id),
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={"contrato": c.codigo, "figura": t.figura, "causal": "AUTORIDAD", "acto": _etiqueta_acto(acto)},
        )
        raise _inv(
            "act_id",
            "AUTORIDAD",
            "El cargo que emitió el acto no tenía la competencia Aprobar sobre Contrataciones en su fecha",
        )
    if acto is not None and acto.fecha_eficacia is not None and not dict_reqs["SIN_HECHOS_POSTERIORES"]["cumplido"]:
        limite = t.conclusion_hasta or acto.fecha_eficacia
        raise ConflictError(
            "GOV_CONTRACT_TERMINATION_LATER_FACTS",
            "Ya hay hechos registrados con fecha posterior a la extinción",
            details={"hechos": _hechos_posteriores(db, c, limite)},
        )
    mapa_campos = {
        "FIGURA": "figura",
        "CAUSAL": "causal",
        "MOTIVACION": "hechos",
        "ACTO_EFICAZ": "act_id",
        "NOTIFICACION_CONTRATISTA": "act_id",
        "APERTURA": "apertura_act_id",
        "DOCUMENTO_ACUERDO": "document_id",
        "CONCLUSION": "conclusion_hasta",
    }
    if t.figura in RESCISIONES:
        mapa_campos["NOTIFICACION_GARANTES"] = "act_id"
    for req in reqs:
        if not req["cumplido"]:
            campo = mapa_campos.get(req["codigo"], "hechos")
            raise _inv(campo, req["codigo"], req["mensaje"])
    if acto is None:
        raise _inv("act_id", "ACTO_EFICAZ", "El acto decisorio es obligatorio")
    fecha_eficacia = acto.fecha_eficacia
    if fecha_eficacia is None:
        raise _inv("act_id", "ACTO_EFICAZ", "El acto decisorio debe estar eficaz")
    exigir_autoridad_funcional(db, ctx, str(acto.cargo_id), "APROBAR", "CONTRATACIONES")
    evaluar_antes_de_actuar(db, ctx, "PROC03_TERMINACION_FORMALIZAR", ENTIDAD, str(c.file_id))
    expediente = db.execute(
        select(GovernmentProcurementFile)
        .where(
            GovernmentProcurementFile.id == c.file_id,
            GovernmentProcurementFile.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one()
    hoy = hoy_de_negocio()
    codigo = f"{c.codigo}/TER"
    consecuencias = _consecuencias(db, ctx, c, t.figura, fecha_eficacia)
    snapshot = {
        "codigo": codigo,
        "contrato": {"codigo": c.codigo, "huella": c.huella},
        "figura": t.figura,
        "causal": t.causal,
        "causal_referencia": t.causal_referencia,
        "hechos": t.hechos,
        "fundamento": t.fundamento,
        "acto": _acto_publico(db, acto),
        "apertura": _acto_publico(db, ap) if ap else None,
        "documento": (
            {"titulo": t.documento_titulo, "sha256": t.documento_sha256}
            if t.document_id
            else None
        ),
        "conclusion": (
            {"alcance": t.conclusion_alcance, "hasta": t.conclusion_hasta.isoformat()}
            if t.conclusion_hasta
            else None
        ),
        "fecha_acto": acto.fecha.isoformat(),
        "fecha_eficacia": fecha_eficacia.isoformat(),
        "notificaciones": _notificaciones(db, ctx, c, str(acto.id)),
        "consecuencias": consecuencias,
        "requisitos": reqs,
        "fecha_registro": hoy.isoformat(),
    }
    huella = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    t.estado = "FORMALIZADA"
    t.codigo = codigo
    t.fecha_acto = acto.fecha
    t.fecha_eficacia = fecha_eficacia
    t.formalizado_en = instante_actual()
    t.formalizado_por = ctx.user_id
    t.snapshot = snapshot
    t.huella = huella
    t.version += 1
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_contract_terminations_formalizada"):
            raise ConflictError(
                "GOV_CONTRACT_TERMINATION_ALREADY_EXISTS",
                "El contrato ya tiene una terminación formalizada",
            ) from error
        raise
    if t.figura == "RESOLUCION_MUTUO_ACUERDO" and t.document_id:
        r = _documento_valido(db, ctx, c, t.document_id)
        if r is None:
            raise _inv("document_id", "DOCUMENTO_ACUERDO", "El acuerdo cambió o ya no está disponible: vuelva a vincularlo")
        doc, version_doc, link = r
        sellar_documento(
            db,
            document=doc,
            resource_type="GovernmentContractTermination",
            resource_id=str(t.id),
            actor_id=ctx.user_id,
            motivo=f"Acuerdo de resolución {codigo} formalizado (CNT-07)",
        )
        congelar_vinculo(db, link=link, version_id=str(version_doc.id), actor=user)
        db.flush()
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "CONTRATO",
        fecha_eficacia,
        f"{ETIQUETA_FIGURA[t.figura]} {codigo} formalizada",
        detalle=f"Acto {_etiqueta_acto(acto)} · eficaz desde {fecha_eficacia:%d/%m/%Y}",
    )
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_TERMINATION_FORMALIZED",
        str(c.file_id),
        {
            "contrato": c.codigo,
            "terminacion": codigo,
            "codigo": codigo,
            "figura": t.figura,
            "causal": t.causal,
            "acto": _etiqueta_acto(acto),
            "apertura": _etiqueta_acto(ap) if ap else None,
            "fecha_eficacia": fecha_eficacia.isoformat(),
            "huella": huella,
        },
    )
    return vista(db, ctx, contrato_id)


def reporte_csv(
    db: Session,
    ctx: CompanyContext,
    figura: str | None,
    desde: date | None,
    hasta: date | None,
) -> tuple[str, bytes]:
    consulta = select(GovernmentContractTermination).where(
        GovernmentContractTermination.company_id == ctx.company_id,
        GovernmentContractTermination.estado == "FORMALIZADA",
    )
    if figura is not None:
        consulta = consulta.where(GovernmentContractTermination.figura == figura)
    if desde is not None:
        consulta = consulta.where(GovernmentContractTermination.fecha_eficacia >= desde)
    if hasta is not None:
        consulta = consulta.where(GovernmentContractTermination.fecha_eficacia <= hasta)
    filas = db.scalars(
        consulta.order_by(
            GovernmentContractTermination.fecha_eficacia.desc(),
            GovernmentContractTermination.codigo,
        )
    ).all()
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(
        [
            "codigo_terminacion",
            "codigo_contrato",
            "contratista",
            "documento_contratista",
            "figura",
            "causal",
            "causal_referencia",
            "fecha_acto",
            "fecha_eficacia",
            "acto",
            "conclusion_hasta",
            "monto_vigente",
            "valuado_conformado",
            "saldo_no_ejecutado",
            "moneda",
            "formalizado_en",
        ]
    )
    for t in filas:
        c = db.get(GovernmentContract, t.contract_id)
        snapshot = t.snapshot or {}
        consecuencias = snapshot.get("consecuencias") or {}
        escritor.writerow(
            [
                t.codigo,
                c.codigo if c else None,
                c.contratista_nombre if c else None,
                c.contratista_documento if c else None,
                t.figura,
                t.causal,
                t.causal_referencia,
                t.fecha_acto.isoformat() if t.fecha_acto else "",
                t.fecha_eficacia.isoformat() if t.fecha_eficacia else "",
                (snapshot.get("acto") or {}).get("etiqueta", ""),
                t.conclusion_hasta.isoformat() if t.conclusion_hasta else "",
                consecuencias.get("monto_vigente", ""),
                consecuencias.get("valuado_conformado", ""),
                consecuencias.get("saldo_no_ejecutado", ""),
                consecuencias.get("moneda", ""),
                t.formalizado_en.isoformat() if t.formalizado_en else "",
            ]
        )
    return "terminaciones-contractuales.csv", salida.getvalue().encode("utf-8")


def vista(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    c = _contrato(db, ctx, contrato_id, False)
    _formalizado(c)
    hoy = hoy_de_negocio()
    formalizada = terminacion_formalizada(db, ctx.company_id, str(c.id))
    borrador = _borrador(db, c, False) if c.estado == "FORMALIZADO" else None
    actual = formalizada or borrador
    acto_principal = actual.act_id if actual and actual.act_id else None
    expediente = db.get(GovernmentProcurementFile, c.file_id)
    compromisos = compromisos_trazados(db, c)
    garantias = _garantias_vista(db, c)
    corte = formalizada.fecha_eficacia if formalizada and formalizada.fecha_eficacia else hoy
    obligaciones: list[dict[str, str]] = []
    if actual and actual.figura in RESCISIONES:
        obligaciones.append(
            {
                "codigo": "EVALUACION_DESEMPENO_SNC",
                "mensaje": "Remita la evaluación de desempeño del contratista al Servicio Nacional de Contrataciones.",
                "fuente": "LCP art. 51",
            }
        )
    if actual and actual.figura == "RESCISION_IMPUTABLE":
        obligaciones.append(
            {
                "codigo": "PUBLICACION_SNC",
                "mensaje": "Publique la notificación de la rescisión en la página web del Servicio Nacional de Contrataciones.",
                "fuente": "LCP art. 8",
            }
        )
    if any(comp.estado == "VIGENTE" for comp in compromisos):
        obligaciones.append(
            {
                "codigo": "REVISAR_COMPROMISO_BUD08",
                "mensaje": "Revise el compromiso presupuestario en BUD-08: la anulación, si procede, se hace allí.",
                "fuente": "BUD-08",
            }
        )
    if any(g["vigente"] for g in garantias):
        obligaciones.append(
            {
                "codigo": "REVISAR_GARANTIAS_PROC10",
                "mensaje": "Revise las garantías en PROC-10: su liberación o ejecución, si procede, se hace allí.",
                "fuente": "LCP arts. 152 y 156; RLCP art. 194",
            }
        )
    actos = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.caracter == "PARTICULAR",
            GovernmentAct.status.in_(("EMITIDO", "EFICAZ")),
            GovernmentAct.competencia_accion == "APROBAR",
            GovernmentAct.competencia_materia == "CONTRATACIONES",
        )
        .order_by(GovernmentAct.fecha.desc())
    ).all()
    opciones_actos = []
    for acto in actos:
        if not _autoridad(db, acto):
            continue
        cargo = db.get(GovernmentPosition, acto.cargo_id)
        opciones_actos.append(
            {
                "id": acto.id,
                "etiqueta": _etiqueta_acto(acto),
                "estado": acto.status,
                "fecha": acto.fecha.isoformat(),
                "fecha_eficacia": acto.fecha_eficacia.isoformat() if acto.fecha_eficacia else None,
                "emisor_cargo": cargo.name if cargo else "",
            }
        )
    catalogo_figuras = []
    for figura in FIGURAS_TERMINACION_CONTRATO:
        catalogo_figuras.append(
            {
                "codigo": figura,
                "etiqueta": ETIQUETA_FIGURA[figura],
                "fuente": CATALOGO[figura]["fuente"],
                "causales": [{"codigo": x[0], "etiqueta": x[1], "fuente": x[2]} for x in CATALOGO[figura]["causales"]],
            }
        )
    return {
        "contrato": {
            "id": c.id,
            "codigo": c.codigo,
            "contratista": {"nombre": c.contratista_nombre, "documento": c.contratista_documento},
            "objeto": c.objeto,
            "tipo_contratacion": _flujo(expediente) if expediente is not None else "BIENES_SERVICIOS",
            "fecha_formalizacion": c.fecha_formalizacion.isoformat() if c.fecha_formalizacion else None,
            "enlace": f"/gobierno/contratos/{c.id}",
        },
        "situacion": situacion_contractual(db, ctx.company_id, str(c.id), hoy),
        "catalogo": {"figuras": catalogo_figuras},
        "borrador": _terminacion_publica(db, borrador) if borrador else None,
        "formalizada": _terminacion_publica(db, formalizada) if formalizada else None,
        "requisitos": _requisitos(db, ctx, c, borrador) if borrador else [],
        "opciones": {"actos": opciones_actos, "documentos": _documentos_elegibles(db, ctx, c)},
        "notificaciones": _notificaciones(db, ctx, c, acto_principal),
        "consecuencias": _consecuencias(db, ctx, c, actual.figura if actual else None, corte),
        "garantias": garantias,
        "obligaciones": obligaciones,
        "permisos": {
            "terminar": "gobierno_contratos:terminate" in _permisos(db, ctx)
            and c.estado == "FORMALIZADO"
            and formalizada is None
        },
    }
