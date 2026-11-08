"""Servicio de consulta de la bitácora institucional de Gobierno."""

from datetime import date
from typing import Any

from sqlalchemy import String, and_, cast, func, or_, select, tuple_
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentOfficial,
    GovernmentUnit,
    GovernmentUserOfficialLink,
)
from app.modules.government.service_auditoria import (
    _detalle_de_evento_para_catalogo,
    _filtro_acciones_gobierno,
    _instante,
    _objeto_desde_evento,
    _pares_gobierno,
    _proceso_de,
    _usuarios_por_ids,
)
from app.modules.identity_access.models import User
from app.shared.audit_catalog import catalog
from app.shared.clock import limites_del_dia_utc

RESULTADOS = (("EXITO", "Éxito"), ("RECHAZO", "Rechazo"), ("DENEGACION", "Denegación"))
_RESULTADO_POR_CLASE = {
    "BUSINESS_COMMIT": "EXITO",
    "REJECTION": "RECHAZO",
    "SECURITY_DENIAL": "DENEGACION",
}
ACCIONES_AUTENTICACION = frozenset(
    {
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "LOGIN_BLOCKED",
        "MFA_CHALLENGE_SUCCEEDED",
        "MFA_CHALLENGE_FAILED",
        "MFA_REAUTH_SUCCEEDED",
        "MFA_REAUTH_FAILED",
        "SESSION_REVOKED",
        "SESSIONS_REVOKED_SECURITY_CHANGE",
    }
)
PROCESO_AUTENTICACION = ("AUTENTICACION", "Autenticación")
ESTADOS_VINCULO = ("ACTIVO", "CERRADO", "REVOCADO")


def _pares_autenticacion() -> tuple[tuple[str, str], ...]:
    return tuple(
        (action, entity_type)
        for (action, entity_type), spec in catalog().items()
        if action in ACCIONES_AUTENTICACION
    )


def _alcance(ctx: CompanyContext) -> Any:
    pares_gobierno = _pares_gobierno()
    pares_autenticacion = _pares_autenticacion()
    return and_(
        AuditEvent.tenant_id == ctx.tenant_id,
        or_(
            and_(
                AuditEvent.company_id == ctx.company_id,
                tuple_(AuditEvent.action, AuditEvent.entity_type).in_(pares_gobierno),
            ),
            and_(
                AuditEvent.company_id.is_(None),
                tuple_(AuditEvent.action, AuditEvent.entity_type).in_(pares_autenticacion),
                AuditEvent.user_id.in_(
                    select(GovernmentUserOfficialLink.user_id).where(
                        GovernmentUserOfficialLink.company_id == ctx.company_id,
                        GovernmentUserOfficialLink.status.in_(ESTADOS_VINCULO),
                    )
                ),
            ),
        ),
    )


def _pares_de_resultado(resultado: str) -> list[tuple[str, str]]:
    clase = next(
        (
            clase
            for clase, codigo in _RESULTADO_POR_CLASE.items()
            if codigo == resultado
        ),
        None,
    )
    if clase is None:
        return []
    pares = list(_pares_gobierno()) + list(_pares_autenticacion())
    return [
        par
        for par in pares
        if catalog().get(par) is not None
        and catalog()[par].transaction_class == clase
    ]


def _resultado_de(event: AuditEvent) -> str:
    spec = catalog().get((event.action, event.entity_type))
    if spec is None:
        return "EXITO"
    return _RESULTADO_POR_CLASE.get(spec.transaction_class, "EXITO")


def _estado_contexto(event: AuditEvent) -> str:
    if event.institutional_context:
        return event.institutional_context.get("estado", "ANTERIOR")
    if (event.action, event.entity_type) in _pares_autenticacion() or event.user_id is None:
        return "NO_APLICA"
    return "ANTERIOR"


def _resumen(event: AuditEvent, usuarios: dict[str, str]) -> dict[str, Any]:
    spec = catalog().get((event.action, event.entity_type))
    if (event.action, event.entity_type) in _pares_autenticacion():
        proceso, proceso_nombre = PROCESO_AUTENTICACION
    else:
        proceso, proceso_nombre = _proceso_de(spec.owner_spec) if spec else ("", "")
    contexto = event.institutional_context or {}
    funcionario = None
    cargos: list[str] = []
    unidades: list[str] = []
    if contexto:
        funcionario = (contexto.get("funcionario") or {}).get("nombre")
        for ocupacion in contexto.get("ocupaciones", []):
            cargo = ocupacion.get("cargo")
            unidad = ocupacion.get("unidad")
            if cargo:
                cargos.append(cargo)
            if unidad and unidad not in unidades:
                unidades.append(unidad)
    return {
        "id": str(event.id),
        "fecha": _instante(event.event_time),
        "resultado": _resultado_de(event),
        "accion": event.action,
        "accion_etiqueta": spec.label if spec else event.action,
        "proceso": proceso,
        "proceso_nombre": proceso_nombre,
        "usuario": usuarios.get(event.user_id) if event.user_id is not None else None,
        "funcionario": funcionario,
        "cargos": cargos,
        "unidades": unidades,
        "estado_contexto": _estado_contexto(event),
        "request_id": event.request_id,
        "motivo": event.reason,
    }


def _codigos_de_accion() -> set[str]:
    return {item["codigo"] for item in _filtro_acciones_gobierno()} | {action for action, _ in _pares_autenticacion()}


def filtros(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    acciones = list(_filtro_acciones_gobierno())
    for action, entity_type in _pares_autenticacion():
        spec = catalog()[(action, entity_type)]
        acciones.append(
            {
                "codigo": action,
                "entidad": entity_type,
                "etiqueta": spec.label,
                "proceso": "AUTENTICACION",
            }
        )
    funcionarios_db = (
        db.execute(
            select(GovernmentOfficial)
            .where(GovernmentOfficial.company_id == ctx.company_id)
            .order_by(GovernmentOfficial.nombre)
        )
        .scalars()
        .all()
    )
    unidades_db = (
        db.execute(
            select(GovernmentUnit)
            .where(GovernmentUnit.company_id == ctx.company_id)
            .order_by(GovernmentUnit.name)
        )
        .scalars()
        .all()
    )
    return {
        "resultados": [
            {"codigo": codigo, "etiqueta": etiqueta} for codigo, etiqueta in RESULTADOS
        ],
        "acciones": acciones,
        "funcionarios": [
            {"id": str(oficial.id), "nombre": oficial.nombre}
            for oficial in funcionarios_db
        ],
        "unidades": [
            {"id": str(unidad.id), "nombre": unidad.name} for unidad in unidades_db
        ],
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    *,
    desde: date | None,
    hasta: date | None,
    accion: str | None,
    usuario: str | None,
    funcionario_id: str | None,
    unidad_id: str | None,
    request_id: str | None,
    resultado: str | None,
    pagina: int,
    por_pagina: int,
) -> dict[str, Any]:
    condiciones = [_alcance(ctx)]
    if desde and hasta and desde > hasta:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha inicial no puede ser posterior a la fecha final",
            field_errors={
                "desde": ["La fecha inicial no puede ser posterior a la fecha final"]
            },
            status_code=422,
        )
    if desde:
        condiciones.append(AuditEvent.event_time >= limites_del_dia_utc(desde)[0])
    if hasta:
        condiciones.append(AuditEvent.event_time < limites_del_dia_utc(hasta)[1])
    if accion:
        if accion not in _codigos_de_accion():
            raise KontrolError(
                code="GOV_BITACORA_INVALID_FILTER",
                message="La acción indicada no pertenece a la bitácora de Gobierno",
                field_errors={
                    "accion": ["La acción indicada no pertenece a la bitácora de Gobierno"]
                },
                status_code=422,
            )
        condiciones.append(AuditEvent.action == accion)
    if usuario:
        condiciones.append(
            AuditEvent.user_id.in_(
                select(User.id).where(
                    User.tenant_id == ctx.tenant_id,
                    User.username == usuario,
                )
            )
        )
    if funcionario_id:
        condiciones.append(
            cast(AuditEvent.institutional_context, String).like(f"%{funcionario_id}%")
        )
    if unidad_id:
        condiciones.append(
            cast(AuditEvent.institutional_context, String).like(f"%{unidad_id}%")
        )
    if request_id:
        condiciones.append(AuditEvent.request_id == request_id)
    if resultado:
        pares = _pares_de_resultado(resultado)
        condiciones.append(
            tuple_(AuditEvent.action, AuditEvent.entity_type).in_(pares)
        )
    total = db.execute(select(func.count()).select_from(AuditEvent).where(*condiciones)).scalar_one()
    eventos = (
        db.execute(
            select(AuditEvent)
            .where(*condiciones)
            .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        .scalars()
        .all()
    )
    user_ids = [event.user_id for event in eventos if event.user_id is not None]
    usuarios = _usuarios_por_ids(db, user_ids, ctx.tenant_id)
    return {
        "items": [_resumen(event, usuarios) for event in eventos],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def detalle(db: Session, ctx: CompanyContext, evento_id: str) -> dict[str, Any]:
    event = db.execute(
        select(AuditEvent).where(AuditEvent.id == evento_id, _alcance(ctx))
    ).scalar_one_or_none()
    if event is None:
        raise NotFoundError(
            code="GOV_BITACORA_EVENT_NOT_FOUND",
            message="El evento no existe en la bitácora de este ente",
        )
    usuarios = _usuarios_por_ids(
        db, [event.user_id] if event.user_id is not None else [], ctx.tenant_id
    )
    resumen = _resumen(event, usuarios)
    detalle_data, _ = _detalle_de_evento_para_catalogo(event)
    objeto = _objeto_desde_evento(db, event, ctx)
    resumen.update(
        {
            "entidad": event.entity_type,
            "entidad_id": event.entity_id,
            "sesion_id": event.session_id,
            "ip": event.ip,
            "detalle": detalle_data,
            "objeto": objeto.model_dump() if objeto is not None else None,
            "contexto": event.institutional_context,
        }
    )
    return resumen
