"""Catálogo, consultas y escrituras de reglas de segregación de funciones (SoD)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentSoDRule, GovernmentSoDRuleHistory, GovernmentUserOfficialLink
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.identity_access.models import User
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, limites_del_dia_utc

ENTIDAD_REGLA = "GovernmentSoDRule"
CONFLICTO_ACCION = "GOV_SOD_CONFLICT_BLOCKED"

CATALOGO_SOD: dict[str, dict[str, Any]] = {
    "DOC-02": {
        "nombre": "Actos administrativos",
        "objeto": "GovernmentAct",
        "objeto_nombre": "acto",
        "acciones": {
            "DOC02_REGISTRAR": ("Registrar el acto", "GOV_ACT_CREATED", True),
            "DOC02_EDITAR": ("Editar el borrador del acto", "GOV_ACT_UPDATED", False),
            "DOC02_EMITIR": ("Emitir el acto", "GOV_ACT_ISSUED", False),
            "DOC02_EFICACIA": ("Registrar la eficacia del acto", "GOV_ACT_EFFECTIVENESS_RECORDED", False),
            "DOC02_CORREGIR": ("Corregir el acto", "GOV_ACT_CORRECTED", False),
            "DOC02_REVOCAR": ("Revocar el acto", "GOV_ACT_REVOKED", False),
            "DOC02_ANULAR": ("Anular el acto", "GOV_ACT_NULLIFIED", False),
        },
    },
    "CTL-06": {
        "nombre": "Hallazgos y acciones correctivas",
        "objeto": "GovernmentFinding",
        "objeto_nombre": "hallazgo",
        "acciones": {
            "CTL06_REGISTRAR": ("Registrar el hallazgo", "GOV_FINDING_CREATED", True),
            "CTL06_RECOMENDAR": ("Añadir una recomendación", "GOV_FINDING_RECOMMENDATION_ADDED", False),
            "CTL06_ACCION": ("Añadir una acción correctiva", "GOV_CORRECTIVE_ACTION_ADDED", False),
            "CTL06_PLAN": ("Registrar el plan de acción", "GOV_FINDING_PLAN_REGISTERED", False),
            "CTL06_EJECUCION": ("Iniciar la ejecución", "GOV_FINDING_REMEDIATION_STARTED", False),
            "CTL06_AVANCE": ("Registrar un avance", "GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED", False),
            "CTL06_PRESENTAR": ("Presentar a verificación", "GOV_FINDING_SUBMITTED", False),
            "CTL06_VERIFICAR": ("Verificar y cerrar", "GOV_FINDING_VERIFIED", False),
            "CTL06_DEVOLVER": ("Devolver a remediación", "GOV_FINDING_RETURNED", False),
        },
    },
    "TRE-01": {
        "nombre": "Cuentas bancarias públicas",
        "objeto": "GovernmentBankAccount",
        "objeto_nombre": "cuenta",
        "acciones": {
            "TRE01_REGISTRAR": ("Registrar la cuenta", "GOV_BANK_ACCOUNT_CREATED", True),
            "TRE01_ACTIVAR": ("Activar la cuenta", "GOV_BANK_ACCOUNT_ACTIVATED", False),
            "TRE01_AUTORIZAR": ("Autorizar un cargo", "GOV_BANK_AUTHORIZATION_ADDED", False),
            "TRE01_FIN_AUTORIZACION": ("Terminar una autorización", "GOV_BANK_AUTHORIZATION_ENDED", False),
            "TRE01_INACTIVAR": ("Inactivar la cuenta", "GOV_BANK_ACCOUNT_DEACTIVATED", False),
            "TRE01_CERRAR": ("Cerrar la cuenta", "GOV_BANK_ACCOUNT_CLOSED", False),
        },
    },
    "TRE-02": {
        "nombre": "Programación financiera",
        "objeto": "GovernmentCashProgram",
        "objeto_nombre": "programa",
        "acciones": {
            "TRE02_REGISTRAR": ("Registrar el programa", "GOV_CASH_PROGRAM_CREATED", True),
            "TRE02_ACTIVAR": ("Activar el programa", "GOV_CASH_PROGRAM_ACTIVATED", False),
            "TRE02_REPROGRAMAR": ("Reprogramar", "GOV_CASH_PROGRAM_REVISED", False),
            "TRE02_CERRAR": ("Cerrar el programa", "GOV_CASH_PROGRAM_CLOSED", False),
        },
    },
    "CTL-10": {
        "nombre": "Controles de cierre",
        "objeto": "GovernmentClosurePolicy",
        "objeto_nombre": "política",
        "acciones": {
            "CTL10_REGISTRAR": ("Registrar la política", "GOV_CLOSURE_POLICY_CREATED", True),
            "CTL10_ACTIVAR": ("Activar la política", "GOV_CLOSURE_POLICY_ACTIVATED", False),
            "CTL10_RETIRAR": ("Retirar la política", "GOV_CLOSURE_POLICY_RETIRED", False),
        },
    },
    "ORG-04": {
        "nombre": "Ocupación de cargos",
        "objeto": "GovernmentAssignment",
        "objeto_nombre": "asignación",
        "acciones": {
            "ORG04_REGISTRAR": ("Registrar la asignación", "GOV_ASSIGNMENT_CREATED", True),
            "ORG04_ACTIVAR": ("Activar la asignación", "GOV_ASSIGNMENT_ACTIVATED", False),
            "ORG04_REVOCAR": ("Revocar la asignación", "GOV_ASSIGNMENT_REVOKED", False),
            "ORG04_FINALIZAR": ("Finalizar la asignación", "GOV_ASSIGNMENT_FINISHED", False),
        },
    },
    "ORG-06": {
        "nombre": "Identidad institucional",
        "objeto": "GovernmentUserOfficialLink",
        "objeto_nombre": "vínculo",
        "acciones": {
            "ORG06_REGISTRAR": ("Registrar el vínculo", "GOV_IDENTITY_LINK_CREATED", True),
            "ORG06_ACTIVAR": ("Activar el vínculo", "GOV_IDENTITY_LINK_ACTIVATED", False),
            "ORG06_CERRAR": ("Cerrar el vínculo", "GOV_IDENTITY_LINK_CLOSED", False),
            "ORG06_REVOCAR": ("Revocar el vínculo", "GOV_IDENTITY_LINK_REVOKED", False),
            "ORG06_CAT_OPERATIVO": ("Categoría operativa", "", False),
            "ORG06_CAT_APROBADOR": ("Categoría aprobadora", "", False),
            "ORG06_CAT_CONTROL_INTERNO": ("Categoría de control interno", "", False),
            "ORG06_CAT_AUDITORIA": ("Categoría de auditoría", "", False),
            "ORG06_CAT_ADMINISTRACION_TECNICA": ("Categoría de administración técnica", "", False),
        },
    },
    "PROC-02": {
        "nombre": "Comisiones de contrataciones",
        "objeto": "GovernmentProcurementCommittee",
        "objeto_nombre": "comisión",
        "acciones": {
            "PROC02_REGISTRAR": ("Registrar la comisión", "GOV_COMMITTEE_CREATED", True),
            "PROC02_ACTIVAR": ("Activar la comisión", "GOV_COMMITTEE_ACTIVATED", False),
            "PROC02_CERRAR": ("Cerrar la comisión", "GOV_COMMITTEE_CLOSED", False),
        },
    },
    "PROC-03": {
        "nombre": "Expedientes de contratación",
        "objeto": "GovernmentProcurementFile",
        "objeto_nombre": "expediente",
        "acciones": {
            "PROC03_REGISTRAR": ("Registrar el expediente", "GOV_PROCUREMENT_FILE_CREATED", True),
            "PROC03_DECIDIR": ("Registrar una decisión", "GOV_PROCUREMENT_FILE_DECISION_RECORDED", False),
            "PROC03_RECIBIR": ("Recibir una oferta", "GOV_PROCUREMENT_OFFER_RECEIVED", False),
            "PROC03_ABRIR": ("Abrir ofertas", "GOV_PROCUREMENT_OFFERS_OPENED", False),
            "PROC03_EVALUAR": ("Registrar un resultado de evaluación", "GOV_PROCUREMENT_EVAL_RESULT_RECORDED", False),
            "PROC03_CERRAR": ("Cerrar el expediente", "GOV_PROCUREMENT_FILE_CLOSED", False),
        },
    },
}


def _proceso_de_accion(accion: str) -> str | None:
    for proceso, catalogo_proceso in CATALOGO_SOD.items():
        if accion in catalogo_proceso["acciones"]:
            return proceso
    return None


def etiqueta_de(accion: str | None) -> str | None:
    if accion is None:
        return None
    proceso = _proceso_de_accion(accion)
    if proceso is None:
        return None
    return CATALOGO_SOD[proceso]["acciones"][accion][0]


def catalogo() -> dict[str, Any]:
    return {
        "procesos": [
            {
                "proceso": proceso,
                "nombre": catalogo_proceso["nombre"],
                "objeto": catalogo_proceso["objeto"],
                "acciones": [
                    {"codigo": codigo, "etiqueta": tupla[0], "crea_objeto": tupla[2]}
                    for codigo, tupla in catalogo_proceso["acciones"].items()
                ],
            }
            for proceso, catalogo_proceso in CATALOGO_SOD.items()
        ]
    }


def _invalida(mensaje: str) -> KontrolError:
    return KontrolError(code="GOV_SOD_RULE_INVALID", message=mensaje, status_code=422)


def _validar_par(proceso: str, accion_a: str, accion_b: str, bidireccional: bool) -> None:
    acciones = CATALOGO_SOD[proceso]["acciones"]
    if accion_a not in acciones or accion_b not in acciones:
        raise _invalida("Las acciones deben pertenecer al catálogo del proceso")
    if accion_a == accion_b:
        raise _invalida("La acción A y la acción B deben ser distintas")
    if not bidireccional and acciones[accion_b][2]:
        raise _invalida("Una acción que crea el objeto no puede ser la acción B de una regla en un solo sentido")
    if proceso == "ORG-06":
        if not accion_a.startswith("ORG06_CAT_") or not accion_b.startswith("ORG06_CAT_"):
            raise _invalida("Las acciones de ORG-06 deben ser categorías ORG06_CAT_*")
        if accion_a.removeprefix("ORG06_CAT_") == accion_b.removeprefix("ORG06_CAT_"):
            raise _invalida("Las categorías A y B deben ser distintas")


def _regla_de_empresa(db: Session, ctx: CompanyContext, regla_id: str, bloquear: bool = False) -> GovernmentSoDRule:
    consulta = select(GovernmentSoDRule).where(
        GovernmentSoDRule.id == regla_id,
        GovernmentSoDRule.tenant_id == ctx.tenant_id,
        GovernmentSoDRule.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    regla = db.execute(consulta).scalar_one_or_none()
    if regla is None:
        raise NotFoundError("GOV_SOD_RULE_NOT_FOUND", "La regla no existe en este ente")
    return regla


def _para_escribir(db: Session, ctx: CompanyContext, regla_id: str, version: int | None) -> GovernmentSoDRule:
    if version is None:
        raise KontrolError(
            code="GOV_SOD_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la regla",
            status_code=428,
        )
    regla = _regla_de_empresa(db, ctx, regla_id, bloquear=True)
    if regla.version != version:
        raise ConflictError(
            "GOV_SOD_RULE_STALE",
            "La regla cambió desde que la abrió; recárguela",
            details={"version_actual": regla.version},
        )
    return regla


def _exigir_estado(regla: GovernmentSoDRule, estado: str) -> None:
    if regla.estado != estado:
        raise ConflictError("GOV_SOD_RULE_INVALID_STATE", f"La regla debe estar en estado {estado}")


def en_vigor(regla: GovernmentSoDRule, hoy: date | None = None) -> bool:
    hoy = hoy or hoy_de_negocio()
    return (
        regla.estado == "VIGENTE"
        and regla.vigente_desde <= hoy
        and (regla.vigente_hasta is None or hoy <= regla.vigente_hasta)
    )


def _historia(db: Session, ctx: CompanyContext, regla: GovernmentSoDRule, tipo: str, detalle: dict | None) -> None:
    db.add(
        GovernmentSoDRuleHistory(
            rule_id=str(regla.id),
            company_id=ctx.company_id,
            tipo=tipo,
            detalle=detalle,
            created_by=ctx.user_id,
        )
    )


def _auditar(db: Session, ctx: CompanyContext, regla: GovernmentSoDRule, accion: str, after: dict) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD_REGLA,
        entity_id=str(regla.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _conflictos_de_regla(db: Session, ctx: CompanyContext, regla_id: str) -> int:
    total = db.execute(
        select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == CONFLICTO_ACCION,
            AuditEvent.company_id == ctx.company_id,
            AuditEvent.entity_id == regla_id,
        )
    ).scalar_one_or_none()
    return total if total is not None else 0


def _resumen(regla: GovernmentSoDRule, hoy: date) -> dict:
    return {
        "id": str(regla.id),
        "codigo": regla.codigo,
        "nombre": regla.nombre,
        "proceso": regla.proceso,
        "accion_a": regla.accion_a,
        "accion_a_etiqueta": etiqueta_de(regla.accion_a) or regla.accion_a,
        "accion_b": regla.accion_b,
        "accion_b_etiqueta": etiqueta_de(regla.accion_b) or regla.accion_b,
        "bidireccional": regla.bidireccional,
        "alcance": regla.alcance,
        "modo": regla.modo,
        "vigente_desde": regla.vigente_desde,
        "vigente_hasta": regla.vigente_hasta,
        "estado": regla.estado,
        "en_vigor": en_vigor(regla, hoy),
        "version": regla.version,
    }


def detalle(db: Session, ctx: CompanyContext, regla_id: str) -> dict:
    regla = _regla_de_empresa(db, ctx, regla_id)
    historia = (
        db.execute(
            select(GovernmentSoDRuleHistory)
            .where(
                GovernmentSoDRuleHistory.rule_id == regla.id,
                GovernmentSoDRuleHistory.company_id == ctx.company_id,
            )
            .order_by(GovernmentSoDRuleHistory.created_at, GovernmentSoDRuleHistory.id)
        )
        .scalars()
        .all()
    )
    ids_usuarios = [regla.created_by, regla.activada_por, regla.cerrada_por] + [h.created_by for h in historia]
    usuarios = _usuarios_por_ids(db, ids_usuarios, ctx.tenant_id)

    def _nombre(usuario_id: Any) -> str | None:
        return usuarios.get(str(usuario_id)) if usuario_id is not None else None

    return {
        **_resumen(regla, hoy_de_negocio()),
        "descripcion": regla.descripcion,
        "creada_por": _nombre(regla.created_by),
        "creada_en": _instante(regla.created_at),
        "activada_por": _nombre(regla.activada_por),
        "activada_en": _instante(regla.activada_en) if regla.activada_en is not None else None,
        "cerrada_por": _nombre(regla.cerrada_por),
        "cerrada_en": _instante(regla.cerrada_en) if regla.cerrada_en is not None else None,
        "motivo_cierre": regla.motivo_cierre,
        "conflictos": _conflictos_de_regla(db, ctx, regla_id),
        "historia": [
            {
                "tipo": h.tipo,
                "detalle": h.detalle,
                "registrado_por": _nombre(h.created_by),
                "registrado_en": _instante(h.created_at),
            }
            for h in historia
        ],
    }


def listar(db: Session, ctx: CompanyContext, estado: str | None, proceso: str | None) -> dict:
    condiciones = [
        GovernmentSoDRule.tenant_id == ctx.tenant_id,
        GovernmentSoDRule.company_id == ctx.company_id,
    ]
    if estado is not None:
        condiciones.append(GovernmentSoDRule.estado == estado)
    if proceso is not None:
        condiciones.append(GovernmentSoDRule.proceso == proceso)
    reglas = (
        db.execute(select(GovernmentSoDRule).where(*condiciones).order_by(GovernmentSoDRule.codigo.desc()))
        .scalars()
        .all()
    )
    hoy = hoy_de_negocio()
    conteos = (
        db.execute(
            select(GovernmentSoDRule.estado, func.count())
            .where(
                GovernmentSoDRule.tenant_id == ctx.tenant_id,
                GovernmentSoDRule.company_id == ctx.company_id,
            )
            .group_by(GovernmentSoDRule.estado)
        )
        .all()
    )
    conteos_por_estado = {estado_contado: total for estado_contado, total in conteos}
    inicio_30, _ = limites_del_dia_utc(hoy - timedelta(days=29))
    conflictos_30 = db.execute(
        select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == CONFLICTO_ACCION,
            AuditEvent.company_id == ctx.company_id,
            AuditEvent.event_time >= inicio_30,
        )
    ).scalar_one_or_none()
    return {
        "items": [_resumen(regla, hoy) for regla in reglas],
        "resumen": {
            "borradores": conteos_por_estado.get("BORRADOR", 0),
            "vigentes": conteos_por_estado.get("VIGENTE", 0),
            "cerradas": conteos_por_estado.get("CERRADA", 0),
            "conflictos_30_dias": conflictos_30 if conflictos_30 is not None else 0,
        },
    }


def _siguiente_codigo(db: Session, ctx: CompanyContext) -> str:
    prefijo = f"SOD-{hoy_de_negocio().year}-"
    n = db.execute(
        select(func.count())
        .select_from(GovernmentSoDRule)
        .where(
            GovernmentSoDRule.tenant_id == ctx.tenant_id,
            GovernmentSoDRule.company_id == ctx.company_id,
            GovernmentSoDRule.codigo.like(f"{prefijo}%"),
        )
    ).scalar_one_or_none()
    return f"{prefijo}{(n or 0) + 1:04d}"


def crear(db: Session, ctx: CompanyContext, datos: Any) -> GovernmentSoDRule:
    _validar_par(datos.proceso, datos.accion_a, datos.accion_b, datos.bidireccional)
    if datos.vigente_desde < hoy_de_negocio():
        raise _invalida("La vigencia no puede empezar antes de hoy")
    regla = GovernmentSoDRule(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=_siguiente_codigo(db, ctx),
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        proceso=datos.proceso,
        accion_a=datos.accion_a,
        accion_b=datos.accion_b,
        bidireccional=datos.bidireccional,
        alcance="MISMO_OBJETO",
        modo="BLOQUEAR",
        vigente_desde=datos.vigente_desde,
        vigente_hasta=datos.vigente_hasta,
        estado="BORRADOR",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(regla)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_SOD_RULE_CONFLICT", "Otra regla se registró al mismo tiempo; vuelva a intentarlo") from None
    _historia(db, ctx, regla, "CREADA", None)
    _auditar(
        db,
        ctx,
        regla,
        "GOV_SOD_RULE_CREATED",
        {"codigo": regla.codigo, "proceso": regla.proceso, "accion_a": regla.accion_a, "accion_b": regla.accion_b, "bidireccional": regla.bidireccional},
    )
    db.flush()
    return regla


def editar(db: Session, ctx: CompanyContext, regla_id: str, version: int | None, cambios: Any) -> GovernmentSoDRule:
    regla = _para_escribir(db, ctx, regla_id, version)
    _exigir_estado(regla, "BORRADOR")
    valores = cambios.model_dump(exclude_unset=True)
    nuevos = {
        "nombre": valores.get("nombre", regla.nombre),
        "descripcion": valores.get("descripcion", regla.descripcion),
        "accion_a": valores.get("accion_a", regla.accion_a),
        "accion_b": valores.get("accion_b", regla.accion_b),
        "bidireccional": valores.get("bidireccional", regla.bidireccional),
        "vigente_desde": valores.get("vigente_desde", regla.vigente_desde),
        "vigente_hasta": valores.get("vigente_hasta", regla.vigente_hasta),
    }
    _validar_par(regla.proceso, nuevos["accion_a"], nuevos["accion_b"], nuevos["bidireccional"])
    if "vigente_desde" in valores and nuevos["vigente_desde"] < hoy_de_negocio():
        raise _invalida("La vigencia no puede empezar antes de hoy")
    if nuevos["vigente_hasta"] and nuevos["vigente_hasta"] < nuevos["vigente_desde"]:
        raise _invalida("La vigencia final no puede ser anterior a la inicial")
    cambiados = sorted(c for c, v in nuevos.items() if v != getattr(regla, c))
    for campo, valor in nuevos.items():
        setattr(regla, campo, valor)
    regla.version += 1
    _historia(db, ctx, regla, "EDITADA", {"campos": cambiados})
    _auditar(db, ctx, regla, "GOV_SOD_RULE_UPDATED", {"codigo": regla.codigo, "campos": cambiados})
    db.flush()
    return regla


def _duplicada(db: Session, ctx: CompanyContext, regla: GovernmentSoDRule) -> bool:
    otras = (
        db.execute(
            select(GovernmentSoDRule).where(
                GovernmentSoDRule.id != regla.id,
                GovernmentSoDRule.tenant_id == ctx.tenant_id,
                GovernmentSoDRule.company_id == ctx.company_id,
                GovernmentSoDRule.proceso == regla.proceso,
                GovernmentSoDRule.estado == "VIGENTE",
            )
        )
        .scalars()
        .all()
    )
    for otra in otras:
        mismo_par = (otra.accion_a == regla.accion_a and otra.accion_b == regla.accion_b)
        par_invertido = (otra.accion_a == regla.accion_b and otra.accion_b == regla.accion_a)
        if mismo_par or (par_invertido and (regla.bidireccional or otra.bidireccional)):
            return True
    return False


def activar(db: Session, ctx: CompanyContext, regla_id: str, version: int | None) -> GovernmentSoDRule:
    regla = _para_escribir(db, ctx, regla_id, version)
    _exigir_estado(regla, "BORRADOR")
    if regla.vigente_hasta and regla.vigente_hasta < hoy_de_negocio():
        raise _invalida("La regla ya habría vencido; ajuste su vigencia")
    if _duplicada(db, ctx, regla):
        raise ConflictError("GOV_SOD_RULE_DUPLICATE", "Ya hay una regla vigente con esas dos acciones en este proceso")
    regla.estado = "VIGENTE"
    regla.activada_por = ctx.user_id
    regla.activada_en = datetime.now(UTC)
    regla.version += 1
    detalle_auditoria = {
        "vigente_desde": regla.vigente_desde.isoformat(),
        "vigente_hasta": regla.vigente_hasta.isoformat() if regla.vigente_hasta else None,
    }
    _historia(db, ctx, regla, "ACTIVADA", detalle_auditoria)
    _auditar(db, ctx, regla, "GOV_SOD_RULE_ACTIVATED", {"codigo": regla.codigo, **detalle_auditoria})
    db.flush()
    return regla


def cerrar(db: Session, ctx: CompanyContext, regla_id: str, version: int | None, datos: Any) -> GovernmentSoDRule:
    regla = _para_escribir(db, ctx, regla_id, version)
    _exigir_estado(regla, "VIGENTE")
    regla.estado = "CERRADA"
    regla.cerrada_por = ctx.user_id
    regla.cerrada_en = datetime.now(UTC)
    regla.motivo_cierre = datos.motivo
    regla.version += 1
    _historia(db, ctx, regla, "CERRADA", {"motivo": datos.motivo})
    _auditar(db, ctx, regla, "GOV_SOD_RULE_CLOSED", {"codigo": regla.codigo, "motivo": datos.motivo})
    db.flush()
    return regla


def usuarios_equivalentes(db: Session, ctx: CompanyContext, user_id: str) -> set[str]:
    if not user_id:
        return set()
    resultado = {user_id}
    vinculos = db.execute(
        select(GovernmentUserOfficialLink).where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.status.in_(["ACTIVO", "CERRADO", "REVOCADO"]),
        )
    ).scalars().all()
    por_usuario: dict[str, set[str]] = {}
    por_funcionario: dict[str, set[str]] = {}
    for vinculo in vinculos:
        user_id_str = str(vinculo.user_id)
        official_id_str = str(vinculo.official_id)
        por_usuario.setdefault(user_id_str, set()).add(official_id_str)
        por_funcionario.setdefault(official_id_str, set()).add(user_id_str)
    pendientes = {user_id}
    while pendientes:
        actual = pendientes.pop()
        for official_id in por_usuario.get(actual, set()):
            for otro_usuario in por_funcionario.get(official_id, set()):
                if otro_usuario not in resultado:
                    resultado.add(otro_usuario)
                    pendientes.add(otro_usuario)
    return resultado


def funcionarios_de_actor(db: Session, ctx: CompanyContext, user_id: str) -> set[str]:
    """Devuelve los official_id de los enlaces activos/cerrados/revocados del actor."""
    if not user_id:
        return set()
    user_ids = usuarios_equivalentes(db, ctx, user_id)
    if not user_ids:
        return set()
    enlaces = (
        db.query(GovernmentUserOfficialLink.official_id)
        .filter(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.user_id.in_(user_ids),
            GovernmentUserOfficialLink.status.in_(("ACTIVO", "CERRADO", "REVOCADO")),
        )
        .all()
    )
    return {str(enlace.official_id) for enlace in enlaces}


def conflictos_de_categorias(
    db: Session, ctx: CompanyContext, categorias: set[str], fecha: date
) -> list[dict[str, Any]]:
    if not categorias:
        return []
    reglas = db.execute(
        select(GovernmentSoDRule).where(
            GovernmentSoDRule.tenant_id == ctx.tenant_id,
            GovernmentSoDRule.company_id == ctx.company_id,
            GovernmentSoDRule.proceso == "ORG-06",
            GovernmentSoDRule.estado == "VIGENTE",
            GovernmentSoDRule.vigente_desde <= fecha,
            (
                (GovernmentSoDRule.vigente_hasta.is_(None))
                | (GovernmentSoDRule.vigente_hasta >= fecha)
            ),
        )
    ).scalars().all()
    conflictos: list[dict[str, Any]] = []
    for regla in reglas:
        categoria_a = regla.accion_a.removeprefix("ORG06_CAT_")
        categoria_b = regla.accion_b.removeprefix("ORG06_CAT_")
        if categoria_a in categorias and categoria_b in categorias:
            conflictos.append(
                {
                    "regla_id": str(regla.id),
                    "regla_codigo": regla.codigo,
                    "regla_nombre": regla.nombre,
                    "regla_version": regla.version,
                    "categoria_a": categoria_a,
                    "categoria_b": categoria_b,
                }
            )
    return conflictos


def evaluar_antes_de_actuar(db: Session, ctx: CompanyContext, accion: str, objeto_tipo: str, objeto_id: str) -> None:
    """Guarda preventiva de segregación de funciones (CTL-01, spec §4.2).

    Se llama justo antes de la mutación de negocio, con la fila del objeto ya bloqueada por el servicio que la invoca
    (`SELECT … FOR UPDATE`): dos acciones del mismo objeto se serializan y la segunda ve el evento de la primera.
    Si una regla vigente lo prohíbe, deshace la transacción, audita el intento (REJECTION) y responde 409 GOV_SOD_CONFLICT.
    Nunca concede autoridad: solo puede impedir.
    """
    proceso = _proceso_de_accion(accion)
    if proceso is None:
        return

    actores = usuarios_equivalentes(db, ctx, ctx.user_id)
    hoy = hoy_de_negocio()
    reglas = select(GovernmentSoDRule).where(
        GovernmentSoDRule.tenant_id == ctx.tenant_id,
        GovernmentSoDRule.company_id == ctx.company_id,
        GovernmentSoDRule.proceso == proceso,
        GovernmentSoDRule.estado == "VIGENTE",
        GovernmentSoDRule.vigente_desde <= hoy,
        or_(GovernmentSoDRule.vigente_hasta.is_(None), GovernmentSoDRule.vigente_hasta >= hoy),
        or_(
            GovernmentSoDRule.accion_b == accion,
            and_(GovernmentSoDRule.bidireccional.is_(True), GovernmentSoDRule.accion_a == accion),
        ),
    ).order_by(GovernmentSoDRule.codigo)

    for regla in db.scalars(reglas):
        previa = regla.accion_a if regla.accion_b == accion else regla.accion_b
        evento_previa = CATALOGO_SOD[proceso]["acciones"][previa][1]
        evento = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.company_id == ctx.company_id,
                AuditEvent.user_id.in_(actores),
                AuditEvent.entity_type == objeto_tipo,
                AuditEvent.entity_id == objeto_id,
                AuditEvent.action == evento_previa,
            )
            .order_by(AuditEvent.event_time.desc())
            .limit(1)
        )
        if evento is None:
            continue

        objeto_nombre = CATALOGO_SOD[proceso]["objeto_nombre"]
        etiqueta_previa = etiqueta_de(previa) or previa
        etiqueta = etiqueta_de(accion) or accion
        detalles = {
            "regla_codigo": regla.codigo,
            "regla_nombre": regla.nombre,
            "accion": accion,
            "accion_etiqueta": etiqueta,
            "accion_previa": previa,
            "accion_previa_etiqueta": etiqueta_previa,
            "objeto_tipo": objeto_tipo,
            "objeto_id": objeto_id,
            "previa_en": _instante(evento.event_time).isoformat(),
        }
        regla_id, regla_codigo, regla_version = str(regla.id), regla.codigo, regla.version
        record_audit_after_rollback(
            db,
            action=CONFLICTO_ACCION,
            entity_type=ENTIDAD_REGLA,
            entity_id=regla_id,
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={
                "regla_codigo": regla_codigo,
                "regla_version": regla_version,
                "proceso": proceso,
                "accion": accion,
                "accion_previa": previa,
                "objeto_tipo": objeto_tipo,
                "objeto_id": objeto_id,
                "evento_previo_id": str(evento.id),
            },
        )
        raise ConflictError(
            "GOV_SOD_CONFLICT",
            f"Operación bloqueada por segregación de funciones: usted ya realizó «{etiqueta_previa}» sobre este {objeto_nombre} "
            f"(regla {regla_codigo} · {detalles['regla_nombre']}). Esta acción debe realizarla otro usuario.",
            details=detalles,
        )


def conflictos(
    db: Session,
    ctx: CompanyContext,
    regla_id: str | None,
    proceso: str | None,
    accion: str | None,
    usuario: str | None,
    desde: date | None,
    hasta: date | None,
    pagina: int,
    por_pagina: int,
) -> dict[str, Any]:
    """Intentos bloqueados por segregación de funciones en la empresa activa (spec §4.3)."""
    condiciones = [
        AuditEvent.tenant_id == ctx.tenant_id,
        AuditEvent.company_id == ctx.company_id,
        AuditEvent.action == CONFLICTO_ACCION,
        AuditEvent.entity_type == ENTIDAD_REGLA,
    ]
    if regla_id:
        condiciones.append(AuditEvent.entity_id == regla_id)
    if usuario:
        u = db.scalar(select(User).where(User.tenant_id == ctx.tenant_id, User.username == usuario))
        if u is None:
            return {"items": [], "total": 0, "pagina": pagina, "por_pagina": por_pagina}
        condiciones.append(AuditEvent.user_id == str(u.id))
    if desde:
        inicio, _ = limites_del_dia_utc(desde)
        condiciones.append(AuditEvent.event_time >= inicio)
    if hasta:
        _, fin = limites_del_dia_utc(hasta)
        condiciones.append(AuditEvent.event_time < fin)

    eventos = db.scalars(
        select(AuditEvent)
        .where(*condiciones)
        .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
        .limit(5000)
    ).all()

    filtrados = [
        e
        for e in eventos
        if (not proceso or (e.after or {}).get("proceso") == proceso)
        and (not accion or (e.after or {}).get("accion") == accion)
    ]
    total = len(filtrados)
    pagina_ev = filtrados[(pagina - 1) * por_pagina : pagina * por_pagina]

    usuarios = _usuarios_por_ids(db, [e.user_id for e in pagina_ev], ctx.tenant_id)

    ids_reglas = [e.entity_id for e in pagina_ev]
    nombres: dict[str, str] = {}
    if ids_reglas:
        reglas = db.scalars(
            select(GovernmentSoDRule).where(
                GovernmentSoDRule.id.in_(ids_reglas),
                GovernmentSoDRule.company_id == ctx.company_id,
            )
        ).all()
        nombres = {str(r.id): r.nombre for r in reglas}

    items = []
    for e in pagina_ev:
        a = e.after or {}
        items.append(
            {
                "id": str(e.id),
                "fecha": _instante(e.event_time),
                "usuario": usuarios.get(str(e.user_id)) if e.user_id else None,
                "regla_id": e.entity_id,
                "regla_codigo": a.get("regla_codigo"),
                "regla_nombre": nombres.get(str(e.entity_id)),
                "proceso": a.get("proceso"),
                "accion": a.get("accion"),
                "accion_etiqueta": etiqueta_de(a.get("accion")),
                "accion_previa": a.get("accion_previa"),
                "accion_previa_etiqueta": etiqueta_de(a.get("accion_previa")),
                "objeto_tipo": a.get("objeto_tipo"),
                "objeto_id": a.get("objeto_id"),
            }
        )

    return {"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina}
