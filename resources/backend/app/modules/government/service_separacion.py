from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, accessible_company_ids
from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentRoleCategory
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_bitacora import _alcance
from app.modules.government.service_identidad import (
    CATEGORIAS_IDENTIDAD,
    _politica_de,
    contexto_institucional,
)
from app.modules.identity_access.authority import (
    ADMIN_ROLE_CODE,
    FUNCTIONAL_ROLE_CODE,
    SECURITY_ADMIN_CAPABILITIES,
    TECHNICAL_CAPABILITIES,
    capabilities_in_company,
    role_capabilities,
)
from app.modules.identity_access.models import Role, User, UserRole
from app.shared.clock import hoy_de_negocio

_MENSAJES: dict[str, str] = {
    "AUTHORITY_CEILING_EXCEEDED": "No puede conceder ni gestionar una autoridad que usted no tiene.",
    "SELF_ESCALATION_FORBIDDEN": "No puede ampliar su propia autoridad.",
    "CROSS_SCOPE_DELEGATION_FORBIDDEN": "No puede conceder autoridad fuera de las empresas en las que la tiene.",
    "TARGET_OUT_OF_SCOPE": "Esa asignación está fuera de las empresas en las que usted tiene autoridad.",
    "LAST_SECURITY_ADMIN_REQUIRED": "La operación dejaría a la empresa sin ningún administrador de seguridad.",
    "COMPANY_SCOPE_FORBIDDEN": "No tiene esa autoridad en esta empresa.",
    "GOV_IDENTITY_LINK_REQUIRED": "Su cuenta no tiene un vínculo institucional vigente en este ente",
    "GOV_FUNCTIONAL_AUTHORITY_REQUIRED": "Su funcionario no ejerce hoy ese cargo con esa competencia",
}

_MOTIVOS: dict[str, str] = {
    "SIN_VINCULO": "Sin vínculo institucional vigente",
    "CUENTA_INACTIVA": "Cuenta inactiva",
    "FUNCIONARIO_INACTIVO": "Funcionario inactivo",
    "SIN_OCUPACION": "No ejerce ningún cargo hoy",
}

_ACCIONES_DENEGACION = {
    "AUTHORITY_DELEGATION_DENIED",
    "LAST_ADMIN_OPERATION_DENIED",
    "COMPANY_SCOPE_DENIED",
    "GOV_IDENTITY_GUARD_BLOCKED",
}


def _etiqueta_categoria(codigo: str) -> str:
    for valor, etiqueta, _descripcion in CATEGORIAS_IDENTIDAD:
        if valor == codigo:
            return etiqueta
    return codigo


def _rol_protegido(
    db: Session, codigo: str, capacidades_permitidas: frozenset[str], invertir: bool
) -> dict[str, Any] | None:
    rol = db.scalar(
        select(Role).where(
            Role.code == codigo,
            Role.protected.is_(True),
            Role.company_id.is_(None),
        )
    )
    if rol is None:
        return None
    capacidades = role_capabilities(db, str(rol.id))
    if invertir:
        fuera = sorted(capacidades & capacidades_permitidas)
    else:
        fuera = sorted(capacidades - capacidades_permitidas)
    return {
        "codigo": rol.code,
        "nombre": rol.name,
        "capacidades": len(capacidades),
        "fuera_de_lugar": fuera,
    }


def _integridad(db: Session) -> dict[str, Any]:
    admin = _rol_protegido(db, ADMIN_ROLE_CODE, TECHNICAL_CAPABILITIES, invertir=False)
    funcional = _rol_protegido(
        db, FUNCTIONAL_ROLE_CODE, TECHNICAL_CAPABILITIES, invertir=True
    )
    integra = (admin is None or not admin["fuera_de_lugar"]) and (
        funcional is None or not funcional["fuera_de_lugar"]
    )
    return {"integra": integra, "admin": admin, "funcional": funcional}


def _exigencia(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    politica = _politica_de(db, ctx)
    activa = bool(politica and politica.exige_identidad)
    version = politica.version if politica else 0
    if activa:
        efecto = (
            "Las acciones que exigen cargo comprueban el vínculo institucional, "
            "la ocupación y la competencia del usuario."
        )
    else:
        efecto = (
            "Las acciones protegidas no comprueban el cargo del usuario: basta el "
            "permiso funcional y el acto competente (OD-ORG06-09)."
        )
    return {"activa": activa, "version": version, "efecto": efecto}


def _origenes(
    db: Session, asignaciones: Sequence[UserRole], tenant_id: str | None
) -> dict[str, dict[str, Any]]:
    ids = [str(asignacion.id) for asignacion in asignaciones]
    if not ids:
        return {}
    eventos = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.action == "ROLE_ASSIGNED",
            AuditEvent.entity_id.in_(ids),
            AuditEvent.tenant_id == tenant_id,
        )
        .order_by(AuditEvent.event_time.desc())
    ).all()
    por_asignacion: dict[str, dict[str, Any]] = {}
    for evento in eventos:
        clave = str(evento.entity_id)
        if clave not in por_asignacion:
            por_asignacion[clave] = {
                "fuente": "ASIGNACION",
                "actor": evento.user_id,
                "fecha": _instante(evento.event_time),
            }
            if evento.source == "SETUP":
                por_asignacion[clave]["fuente"] = "INSTALACION"
                por_asignacion[clave]["actor"] = None
    actores = [valor["actor"] for valor in por_asignacion.values() if valor["actor"]]
    usernames = _usuarios_por_ids(db, actores, tenant_id)
    for valor in por_asignacion.values():
        if valor["actor"]:
            valor["actor"] = usernames.get(valor["actor"])
    return por_asignacion


def _categorias_por_rol(
    db: Session, ctx: CompanyContext, roles_ids: Sequence[str]
) -> dict[str, list[str]]:
    if not roles_ids:
        return {}
    hoy = hoy_de_negocio()
    filas = db.execute(
        select(GovernmentRoleCategory.role_id, GovernmentRoleCategory.categoria)
        .where(
            GovernmentRoleCategory.company_id == ctx.company_id,
            GovernmentRoleCategory.role_id.in_(list(roles_ids)),
            GovernmentRoleCategory.status == "ACTIVA",
            GovernmentRoleCategory.desde <= hoy,
            (GovernmentRoleCategory.hasta.is_(None))
            | (GovernmentRoleCategory.hasta >= hoy),
        )
        .order_by(GovernmentRoleCategory.categoria)
    ).all()
    resultado: dict[str, list[str]] = {}
    for role_id, categoria in filas:
        resultado.setdefault(str(role_id), []).append(_etiqueta_categoria(categoria))
    return resultado


def _roles_administrador(
    db: Session,
    ctx: CompanyContext,
    usuario: User,
    asignaciones: Sequence[UserRole],
    origenes: dict[str, dict[str, Any]],
    categorias_por_rol: dict[str, list[str]],
    cache_capacidades: dict[str, set[str]],
) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for asignacion in asignaciones:
        rol = db.get(Role, asignacion.role_id)
        if rol is None or rol.status != "ACTIVE":
            continue
        capacidades = cache_capacidades.get(str(rol.id))
        if capacidades is None:
            capacidades = role_capabilities(db, str(rol.id))
            cache_capacidades[str(rol.id)] = capacidades
        tipo = (
            "TECNICO"
            if capacidades.issubset(TECHNICAL_CAPABILITIES)
            else "FUNCIONAL"
        )
        alcance = "TODAS" if asignacion.company_id is None else "ENTE"
        origen = origenes.get(
            str(asignacion.id),
            {"fuente": "NO_REGISTRADO", "actor": None, "fecha": None},
        )
        roles.append(
            {
                "codigo": rol.code,
                "nombre": rol.name,
                "protegido": bool(rol.protected),
                "tipo": tipo,
                "alcance": alcance,
                "capacidades": len(capacidades),
                "categorias": categorias_por_rol.get(str(rol.id), []),
                "origen": origen,
            }
        )
    roles.sort(key=lambda item: (item["tipo"] != "TECNICO", item["codigo"]))
    return roles


def _identidad(db: Session, ctx: CompanyContext, usuario: User) -> dict[str, Any]:
    contexto = contexto_institucional(db, ctx, str(usuario.id), None)
    vinculo = contexto.get("vinculo")
    funcionario = contexto.get("funcionario")
    ocupaciones = []
    for ocupacion in contexto.get("ocupaciones", []):
        if not ocupacion.get("ejerce"):
            continue
        ocupaciones.append(
            {
                "cargo": ocupacion["cargo"],
                "cargo_codigo": ocupacion["cargo_codigo"],
                "figura_etiqueta": ocupacion["figura_etiqueta"],
                "unidad": ocupacion["unidad"],
                "competencias": [
                    {"accion": item["accion"], "materia": item["materia"]}
                    for item in ocupacion.get("autoridad", [])
                ],
            }
        )
    motivo = contexto.get("motivo_sin_autoridad")
    return {
        "vinculo_codigo": vinculo["codigo"] if vinculo else None,
        "funcionario": funcionario["nombre"] if funcionario else None,
        "ocupaciones": ocupaciones,
        "tiene_autoridad": bool(contexto.get("tiene_autoridad")),
        "motivo": motivo,
        "motivo_etiqueta": _MOTIVOS.get(motivo) if motivo else None,
    }


def _separacion(roles: list[dict[str, Any]], identidad: dict[str, Any]) -> dict[str, str]:
    tiene_funcional = any(rol["tipo"] == "FUNCIONAL" for rol in roles)
    if not tiene_funcional:
        return {
            "separacion": "SOLO_TECNICO",
            "separacion_etiqueta": "Solo técnico",
            "separacion_detalle": (
                "Administra la plataforma; no tiene permisos de negocio en este ente."
            ),
        }
    if identidad["tiene_autoridad"]:
        return {
            "separacion": "TECNICO_Y_FUNCIONAL_CON_AUTORIDAD",
            "separacion_etiqueta": "Técnico y funcional, con autoridad institucional",
            "separacion_detalle": (
                "Sus permisos de negocio se concedieron por separado y ejerce un cargo."
            ),
        }
    return {
        "separacion": "TECNICO_Y_FUNCIONAL_SIN_AUTORIDAD",
        "separacion_etiqueta": "Técnico y funcional, sin autoridad institucional",
        "separacion_detalle": (
            "Tiene permisos de negocio concedidos por separado, pero no ejerce ningún "
            "cargo: no puede emitir actos que exigen cargo cuando la exigencia de "
            "identidad está activa."
        ),
    }


def _administradores(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    usuarios = db.scalars(
        select(User).where(User.tenant_id == ctx.tenant_id)
    ).all()

    administradores_ids: list[str] = []
    for usuario in usuarios:
        capacidades = capabilities_in_company(db, usuario, ctx.company_id)
        if capacidades & SECURITY_ADMIN_CAPABILITIES:
            administradores_ids.append(str(usuario.id))

    if not administradores_ids:
        return []

    asignaciones = db.scalars(
        select(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id.in_(administradores_ids),
            Role.status == "ACTIVE",
            (UserRole.company_id.is_(None))
            | (UserRole.company_id == ctx.company_id),
        )
    ).all()

    roles_ids = [str(asignacion.role_id) for asignacion in asignaciones]
    origenes = _origenes(db, asignaciones, ctx.tenant_id)
    categorias_por_rol = _categorias_por_rol(db, ctx, roles_ids)
    cache_capacidades: dict[str, set[str]] = {}

    asignaciones_por_usuario: dict[str, list[UserRole]] = {}
    for asignacion in asignaciones:
        asignaciones_por_usuario.setdefault(str(asignacion.user_id), []).append(
            asignacion
        )

    administradores: list[dict[str, Any]] = []
    for usuario in usuarios:
        if str(usuario.id) not in administradores_ids:
            continue
        asignaciones_usuario = asignaciones_por_usuario.get(str(usuario.id), [])
        roles = _roles_administrador(
            db,
            ctx,
            usuario,
            asignaciones_usuario,
            origenes,
            categorias_por_rol,
            cache_capacidades,
        )
        identidad = _identidad(db, ctx, usuario)
        separacion = _separacion(roles, identidad)
        administradores.append(
            {
                "usuario": usuario.username,
                "estado": usuario.status,
                **separacion,
                "roles": roles,
                "identidad": identidad,
            }
        )
    administradores.sort(key=lambda item: item["usuario"])
    return administradores


def _etiqueta_denegacion(codigo: str | None) -> str:
    if codigo in _MENSAJES:
        return _MENSAJES[codigo]
    return "Operación denegada"


def _denegaciones(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    eventos = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == ctx.tenant_id,
            AuditEvent.action.in_(_ACCIONES_DENEGACION),
        )
        .order_by(AuditEvent.event_time.desc())
        .limit(500)
    ).all()

    usuarios_tenant = db.scalars(
        select(User).where(User.tenant_id == ctx.tenant_id)
    ).all()
    usuarios_con_acceso = {
        str(usuario.id)
        for usuario in usuarios_tenant
        if str(ctx.company_id) in accessible_company_ids(db, usuario)
    }

    seleccionados: list[AuditEvent] = []
    for evento in eventos:
        if str(evento.company_id) == str(ctx.company_id):
            seleccionados.append(evento)
        elif evento.company_id is None and evento.user_id in usuarios_con_acceso:
            evidence = evento.evidence or {}
            if evidence.get("company_id") in (None, str(ctx.company_id)):
                seleccionados.append(evento)
        if len(seleccionados) >= 50:
            break

    ids = [str(evento.id) for evento in seleccionados]
    en_bitacora_ids: set[str] = set()
    if ids:
        filas = db.scalars(
            select(AuditEvent.id).where(
                AuditEvent.id.in_(ids),
                _alcance(ctx),
            )
        ).all()
        en_bitacora_ids = {str(fila) for fila in filas}

    actores = [evento.user_id for evento in seleccionados if evento.user_id]
    usernames = _usuarios_por_ids(db, actores, ctx.tenant_id)

    resultado: list[dict[str, Any]] = []
    for evento in seleccionados:
        evidence = evento.evidence or {}
        codigo = evento.reason
        if codigo is None and evento.action == "GOV_IDENTITY_GUARD_BLOCKED":
            codigo = (evento.after or {}).get("operacion")
        resultado.append(
            {
                "id": str(evento.id),
                "fecha": _instante(evento.event_time),
                "usuario": usernames.get(evento.user_id) if evento.user_id else None,
                "accion": evento.action,
                "codigo": codigo,
                "codigo_etiqueta": _etiqueta_denegacion(codigo),
                "rol": evidence.get("role_code"),
                "capacidades_excedidas": evidence.get("capabilities_excedidas") or [],
                "en_bitacora": str(evento.id) in en_bitacora_ids,
            }
        )
    return resultado


def separacion(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    return {
        "ente": ctx.company.legal_name,
        "integridad": _integridad(db),
        "exigencia_identidad": _exigencia(db, ctx),
        "administradores": _administradores(db, ctx),
        "denegaciones": _denegaciones(db, ctx),
    }
