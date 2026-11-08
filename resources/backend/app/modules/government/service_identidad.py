"""Servicio de vínculos de identidad gubernamental."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from typing import Any, NoReturn

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, accessible_company_ids
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentEntity,
    GovernmentIdentityPolicy,
    GovernmentIdentityPolicyHistory,
    GovernmentOfficial,
    GovernmentRoleCategory,
    GovernmentRoleCategoryHistory,
    GovernmentUserOfficialLink,
    GovernmentUserOfficialLinkHistory,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_ocupacion import (
    _funcionario_de_empresa,
    enmascarar_documento,
    ocupaciones_de_funcionario,
)
from app.modules.government.service_sod import (
    conflictos_de_categorias,
    evaluar_antes_de_actuar,
    usuarios_equivalentes,
)
from app.modules.identity_access.models import Role, User, UserRole
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, limites_del_dia_utc

ENTIDAD_VINCULO = "GovernmentUserOfficialLink"

CATEGORIAS_IDENTIDAD = [
    ("OPERATIVO", "Operativo", "Categoría operativa"),
    ("APROBADOR", "Aprobador", "Categoría aprobadora"),
    ("CONTROL_INTERNO", "Control interno", "Categoría de control interno"),
    ("AUDITORIA", "Auditoría", "Categoría de auditoría"),
    (
        "ADMINISTRACION_TECNICA",
        "Administración técnica",
        "Categoría de administración técnica",
    ),
]

ESTADOS_VINCULO = ["BORRADOR", "ACTIVO", "CERRADO", "REVOCADO", "DESCARTADO"]
SITUACIONES_VINCULO = [
    "BORRADOR",
    "DESCARTADA",
    "FUTURA",
    "VIGENTE",
    "VENCIDA",
    "CERRADA",
    "REVOCADA",
]


def catalogo() -> dict:
    return {
        "categorias": [
            {"codigo": c[0], "etiqueta": c[1], "descripcion": c[2]}
            for c in CATEGORIAS_IDENTIDAD
        ],
        "situaciones": SITUACIONES_VINCULO,
        "estados": ESTADOS_VINCULO,
    }


def _cuenta_del_ente(db: Session, ctx: CompanyContext, user_id: str) -> User:
    usuario = db.scalar(
        select(User).where(
            User.id == user_id,
            User.tenant_id == ctx.tenant_id,
        )
    )
    if not usuario:
        raise NotFoundError(
            "GOV_IDENTITY_USER_NOT_FOUND", "La cuenta no existe en este ente"
        )
    if ctx.company_id not in accessible_company_ids(db, usuario):
        raise NotFoundError(
            "GOV_IDENTITY_USER_NOT_FOUND", "La cuenta no existe en este ente"
        )
    return usuario


def _siguiente_codigo_vinculo(db: Session, ctx: CompanyContext) -> str:
    total = (
        db.scalar(
            select(func.count(GovernmentUserOfficialLink.id)).where(
                GovernmentUserOfficialLink.company_id == ctx.company_id
            )
        )
        or 0
    )
    return f"VIN-{total + 1:05d}"


def _historia(
    db: Session,
    ctx: CompanyContext,
    vinculo: GovernmentUserOfficialLink,
    tipo: str,
    detalle: dict[str, Any],
) -> None:
    db.add(
        GovernmentUserOfficialLinkHistory(
            link_id=vinculo.id,
            tipo=tipo,
            detalle=detalle,
            company_id=ctx.company_id,
            created_by=ctx.user_id,
        )
    )


def _estado_vinculo(v: GovernmentUserOfficialLink) -> dict[str, Any]:
    return {
        "codigo": v.codigo,
        "user_id": str(v.user_id),
        "funcionario_id": str(v.official_id),
        "desde": v.desde.isoformat() if v.desde else None,
        "hasta": v.hasta.isoformat() if v.hasta else None,
        "fin_efectivo": v.fin_efectivo.isoformat() if v.fin_efectivo else None,
        "estado": v.status,
        "motivo": v.motivo,
        "motivo_fin": v.motivo_fin,
        "soporte": v.soporte,
    }


def _funcionario_del_actor(db: Session, ctx: CompanyContext) -> str | None:
    hoy = hoy_de_negocio()
    vinculo = db.scalar(
        select(GovernmentUserOfficialLink).where(
            GovernmentUserOfficialLink.user_id == ctx.user_id,
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.status == "ACTIVO",
            GovernmentUserOfficialLink.desde <= hoy,
            (
                (GovernmentUserOfficialLink.hasta.is_(None))
                | (GovernmentUserOfficialLink.hasta >= hoy)
            ),
            (
                (GovernmentUserOfficialLink.fin_efectivo.is_(None))
                | (GovernmentUserOfficialLink.fin_efectivo >= hoy)
            ),
        )
    )
    if not vinculo:
        return None
    return str(vinculo.official_id)


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    entidad_id: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    motivo: str | None = None,
    entidad: str = ENTIDAD_VINCULO,
) -> None:
    if after is not None:
        after = dict(after)
        after["actor_institucional"] = _funcionario_del_actor(db, ctx)
    record_audit(
        db,
        action=accion,
        entity_type=entidad,
        entity_id=entidad_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=before,
        after=after,
        reason=motivo,
    )


def _para_escribir(
    db: Session, ctx: CompanyContext, vinculo_id: str, version: int | None
) -> GovernmentUserOfficialLink:
    if version is None:
        raise KontrolError(
            code="GOV_IDENTITY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    vinculo = db.scalar(
        select(GovernmentUserOfficialLink)
        .where(
            GovernmentUserOfficialLink.id == vinculo_id,
            GovernmentUserOfficialLink.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not vinculo:
        raise NotFoundError("GOV_IDENTITY_LINK_NOT_FOUND", "El vínculo no existe")
    if vinculo.version != version:
        raise ConflictError(
            "GOV_IDENTITY_STALE",
            "El vínculo cambió desde que lo abrió; recárguelo",
            details={"version_actual": vinculo.version},
        )
    return vinculo


def _exigir_estado(vinculo: GovernmentUserOfficialLink, estado: str) -> None:
    if vinculo.status != estado:
        raise ConflictError(
            "GOV_IDENTITY_INVALID_STATE",
            f"El vínculo debe estar en estado {estado}",
        )


def _exige_no_autovinculo(
    db: Session, ctx: CompanyContext, user_id: str, official_id: str
) -> None:
    cuentas = set(
        db.execute(
            select(GovernmentUserOfficialLink.user_id).where(
                GovernmentUserOfficialLink.official_id == official_id,
                GovernmentUserOfficialLink.company_id == ctx.company_id,
                GovernmentUserOfficialLink.status.in_(
                    ["ACTIVO", "CERRADO", "REVOCADO"]
                ),
            )
        )
        .scalars()
        .all()
    )
    if ctx.user_id in cuentas or user_id == ctx.user_id:
        raise KontrolError(
            code="GOV_IDENTITY_SELF_LINK",
            message="Quien actúa es la cuenta o el funcionario del vínculo",
            status_code=403,
        )


def _bloquear_identidad(db: Session, ctx: CompanyContext) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            select(
                func.pg_advisory_xact_lock(
                    7006001, func.hashtext(str(ctx.company_id))
                )
            )
        )


def situacion_vinculo(v: GovernmentUserOfficialLink, fecha: date) -> str:
    if v.status == "BORRADOR":
        return "BORRADOR"
    if v.status == "DESCARTADO":
        return "DESCARTADA"
    if v.desde and fecha < v.desde:
        return "FUTURA"
    if v.fin_efectivo and fecha > v.fin_efectivo:
        if v.status == "CERRADO":
            return "CERRADA"
        if v.status == "REVOCADO":
            return "REVOCADA"
    if v.hasta and fecha > v.hasta:
        return "VENCIDA"
    return "VIGENTE"


def roles_de_usuario(
    db: Session, ctx: CompanyContext, user_id: str, fecha: date
) -> list[dict]:
    hoy = hoy_de_negocio()
    if fecha >= hoy:
        user_roles = db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                (UserRole.company_id.is_(None))
                | (UserRole.company_id == ctx.company_id),
            )
        ).scalars().all()
        role_ids = [ur.role_id for ur in user_roles]
    else:
        inicio, fin = limites_del_dia_utc(fecha)
        eventos = db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action.in_(["ROLE_ASSIGNED", "ROLE_REMOVED"]),
                AuditEvent.event_time < fin,
                AuditEvent.tenant_id == ctx.tenant_id,
            )
            .order_by(AuditEvent.event_time)
        ).scalars().all()
        role_ids_set: set[str] = set()
        for evento in eventos:
            after = evento.after or {}
            if after.get("user_id") != user_id:
                continue
            company_id = after.get("company_id")
            if company_id is not None and str(company_id) != str(ctx.company_id):
                continue
            role_id = after.get("role_id")
            if not role_id:
                continue
            if evento.action == "ROLE_ASSIGNED":
                role_ids_set.add(str(role_id))
            elif evento.action == "ROLE_REMOVED":
                role_ids_set.discard(str(role_id))
        role_ids = list(role_ids_set)
    if not role_ids:
        return []
    roles = db.execute(
        select(Role).where(Role.id.in_(role_ids), Role.status == "ACTIVE")
    ).scalars().all()
    return [{"id": str(r.id), "codigo": r.code, "nombre": r.name} for r in roles]


def categorias_de_usuario(
    db: Session, ctx: CompanyContext, user_id: str, fecha: date
) -> set[str]:
    roles = roles_de_usuario(db, ctx, user_id, fecha)
    role_ids = [r["id"] for r in roles]
    if not role_ids:
        return set()
    categorias = db.execute(
        select(GovernmentRoleCategory).where(
            GovernmentRoleCategory.company_id == ctx.company_id,
            GovernmentRoleCategory.role_id.in_(role_ids),
            GovernmentRoleCategory.desde <= fecha,
            (
                (GovernmentRoleCategory.hasta.is_(None))
                | (GovernmentRoleCategory.hasta >= fecha)
            ),
            GovernmentRoleCategory.status.in_(["ACTIVA", "RETIRADA"]),
        )
    ).scalars().all()
    return {c.categoria for c in categorias}


def opciones(db: Session, ctx: CompanyContext) -> dict:
    usuarios = db.execute(
        select(User).where(User.tenant_id == ctx.tenant_id)
    ).scalars().all()
    cuentas = []
    for u in usuarios:
        if ctx.company_id in accessible_company_ids(db, u):
            vinculado = (
                db.scalar(
                    select(GovernmentUserOfficialLink.id).where(
                        GovernmentUserOfficialLink.user_id == u.id,
                        GovernmentUserOfficialLink.company_id == ctx.company_id,
                        GovernmentUserOfficialLink.status == "ACTIVO",
                    )
                )
                is not None
            )
            cuentas.append(
                {
                    "id": str(u.id),
                    "usuario": u.username,
                    "estado": u.status,
                    "vinculada": vinculado,
                }
            )
    funcionarios_rows = db.execute(
        select(GovernmentOfficial).where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
    ).scalars().all()
    funcionarios = []
    for f in funcionarios_rows:
        vinculado = (
            db.scalar(
                select(GovernmentUserOfficialLink.id).where(
                    GovernmentUserOfficialLink.official_id == f.id,
                    GovernmentUserOfficialLink.company_id == ctx.company_id,
                    GovernmentUserOfficialLink.status == "ACTIVO",
                )
            )
            is not None
        )
        funcionarios.append(
            {
                "id": str(f.id),
                "codigo": f.codigo,
                "nombre": f.nombre,
                "documento": enmascarar_documento(
                    f.tipo_documento, f.numero_documento
                ),
                "vinculado": vinculado,
            }
        )
    return {"cuentas": cuentas, "funcionarios": funcionarios}


def crear(
    db: Session, ctx: CompanyContext, datos: Any
) -> GovernmentUserOfficialLink:
    _cuenta_del_ente(db, ctx, str(datos.user_id))
    _funcionario_de_empresa(db, ctx, str(datos.official_id))
    _exige_no_autovinculo(db, ctx, str(datos.user_id), str(datos.official_id))

    vinculo = GovernmentUserOfficialLink(
        company_id=ctx.company_id,
        codigo=_siguiente_codigo_vinculo(db, ctx),
        user_id=datos.user_id,
        official_id=datos.official_id,
        desde=datos.desde,
        hasta=datos.hasta,
        status="BORRADOR",
        motivo=datos.motivo,
        soporte=datos.soporte,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(vinculo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_IDENTITY_OVERLAP",
            "Ya existe un vínculo incompatible",
        ) from None
    estado = _estado_vinculo(vinculo)
    _historia(db, ctx, vinculo, "CREADO", {"despues": estado})
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_LINK_CREATED",
        str(vinculo.id),
        None,
        estado,
    )
    return vinculo


def editar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> GovernmentUserOfficialLink:
    vinculo = _para_escribir(db, ctx, id, version)
    _exigir_estado(vinculo, "BORRADOR")
    _cuenta_del_ente(db, ctx, str(datos.user_id))
    _funcionario_de_empresa(db, ctx, str(datos.official_id))
    _exige_no_autovinculo(db, ctx, str(datos.user_id), str(datos.official_id))

    antes = _estado_vinculo(vinculo)
    vinculo.user_id = datos.user_id
    vinculo.official_id = datos.official_id
    vinculo.desde = datos.desde
    vinculo.hasta = datos.hasta
    vinculo.motivo = datos.motivo
    vinculo.soporte = datos.soporte
    vinculo.version += 1
    db.flush()
    despues = _estado_vinculo(vinculo)
    _historia(db, ctx, vinculo, "EDITADO", {"antes": antes, "despues": despues})
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_LINK_UPDATED",
        str(vinculo.id),
        antes,
        despues,
    )
    return vinculo


def descartar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> GovernmentUserOfficialLink:
    vinculo = _para_escribir(db, ctx, id, version)
    _exigir_estado(vinculo, "BORRADOR")
    antes = _estado_vinculo(vinculo)
    vinculo.status = "DESCARTADO"
    vinculo.motivo_fin = datos.motivo
    vinculo.version += 1
    db.flush()
    despues = _estado_vinculo(vinculo)
    _historia(db, ctx, vinculo, "DESCARTADO", {"antes": antes, "despues": despues})
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_LINK_DISCARDED",
        str(vinculo.id),
        antes,
        despues,
    )
    return vinculo


def activar(
    db: Session, ctx: CompanyContext, id: str, version: int | None
) -> GovernmentUserOfficialLink:
    vinculo = _para_escribir(db, ctx, id, version)
    _exigir_estado(vinculo, "BORRADOR")
    _bloquear_identidad(db, ctx)

    if vinculo.created_by in usuarios_equivalentes(db, ctx, ctx.user_id):
        raise KontrolError(
            code="GOV_IDENTITY_SELF_ACTIVATION",
            message="El actor efectivo registró el vínculo",
            status_code=403,
        )

    _exige_no_autovinculo(db, ctx, str(vinculo.user_id), str(vinculo.official_id))

    usuario = _cuenta_del_ente(db, ctx, str(vinculo.user_id))
    if usuario.status != "ACTIVE":
        raise KontrolError(
            code="GOV_IDENTITY_USER_INACTIVE",
            message="La cuenta no está activa",
            status_code=422,
        )

    funcionario = _funcionario_de_empresa(db, ctx, str(vinculo.official_id))
    if funcionario.estado != "ACTIVO":
        raise KontrolError(
            code="GOV_IDENTITY_OFFICIAL_INACTIVE",
            message="El funcionario no está activo",
            status_code=422,
        )

    fin = vinculo.hasta
    condiciones_solape = [
        GovernmentUserOfficialLink.company_id == ctx.company_id,
        GovernmentUserOfficialLink.status == "ACTIVO",
        GovernmentUserOfficialLink.id != vinculo.id,
        (
            (GovernmentUserOfficialLink.user_id == vinculo.user_id)
            | (GovernmentUserOfficialLink.official_id == vinculo.official_id)
        ),
        (
            (
                func.coalesce(
                    GovernmentUserOfficialLink.fin_efectivo,
                    GovernmentUserOfficialLink.hasta,
                ).is_(None)
            )
            | (
                func.coalesce(
                    GovernmentUserOfficialLink.fin_efectivo,
                    GovernmentUserOfficialLink.hasta,
                )
                >= vinculo.desde
            )
        ),
    ]
    if fin is not None:
        condiciones_solape.append(GovernmentUserOfficialLink.desde <= fin)
    solape = db.scalar(
        select(GovernmentUserOfficialLink).where(*condiciones_solape)
    )
    if solape:
        raise ConflictError(
            "GOV_IDENTITY_OVERLAP",
            "Ya hay un vínculo activo para la cuenta o el funcionario",
        )

    categorias = categorias_de_usuario(db, ctx, str(vinculo.user_id), hoy_de_negocio())
    _bloquear_si_conflicto(db, ctx, categorias, hoy_de_negocio(), ENTIDAD_VINCULO, str(vinculo.id))

    evaluar_antes_de_actuar(db, ctx, "ORG06_ACTIVAR", ENTIDAD_VINCULO, str(vinculo.id))

    antes = _estado_vinculo(vinculo)
    vinculo.status = "ACTIVO"
    vinculo.activated_at = datetime.now(UTC)
    vinculo.activated_by = ctx.user_id
    vinculo.version += 1
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_IDENTITY_OVERLAP",
            "Ya hay un vínculo activo que se solapa",
        ) from None
    despues = _estado_vinculo(vinculo)
    _historia(db, ctx, vinculo, "ACTIVADO", {"antes": antes, "despues": despues})
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_LINK_ACTIVATED",
        str(vinculo.id),
        antes,
        despues,
    )
    return vinculo


def _cerrar_o_revocar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
    accion: str,
    estado: str,
    historico_tipo: str,
) -> GovernmentUserOfficialLink:
    vinculo = _para_escribir(db, ctx, id, version)
    _exigir_estado(vinculo, "ACTIVO")
    if datos.fecha < vinculo.desde or (
        vinculo.hasta and datos.fecha > vinculo.hasta
    ):
        raise KontrolError(
            code="GOV_IDENTITY_INVALID",
            message="La fecha debe estar dentro de la vigencia del vínculo",
            status_code=422,
        )
    evaluar_antes_de_actuar(db, ctx, accion, ENTIDAD_VINCULO, str(vinculo.id))
    antes = _estado_vinculo(vinculo)
    vinculo.status = estado
    vinculo.fin_efectivo = datos.fecha
    vinculo.motivo_fin = datos.motivo
    vinculo.ended_at = datetime.now(UTC)
    vinculo.ended_by = ctx.user_id
    vinculo.version += 1
    db.flush()
    despues = _estado_vinculo(vinculo)
    _historia(db, ctx, vinculo, historico_tipo, {"antes": antes, "despues": despues})
    _auditar(
        db,
        ctx,
        {"CERRADO": "GOV_IDENTITY_LINK_CLOSED", "REVOCADO": "GOV_IDENTITY_LINK_REVOKED"}[estado],
        str(vinculo.id),
        antes,
        despues,
    )
    return vinculo


def cerrar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> GovernmentUserOfficialLink:
    return _cerrar_o_revocar(
        db, ctx, id, version, datos, "ORG06_CERRAR", "CERRADO", "CERRADO"
    )


def revocar(
    db: Session,
    ctx: CompanyContext,
    id: str,
    version: int | None,
    datos: Any,
) -> GovernmentUserOfficialLink:
    return _cerrar_o_revocar(
        db, ctx, id, version, datos, "ORG06_REVOCAR", "REVOCADO", "REVOCADO"
    )


def _consulta_vinculos(
    ctx: CompanyContext,
    estado: str | None,
    usuario_id: str | None,
    funcionario_id: str | None,
):
    query = select(GovernmentUserOfficialLink).where(
        GovernmentUserOfficialLink.company_id == ctx.company_id
    )
    if estado:
        query = query.where(GovernmentUserOfficialLink.status == estado)
    if usuario_id:
        query = query.where(GovernmentUserOfficialLink.user_id == usuario_id)
    if funcionario_id:
        query = query.where(GovernmentUserOfficialLink.official_id == funcionario_id)
    return query


def _ref_cuenta(db: Session, user_id: str | None) -> dict:
    if not user_id:
        return {"id": "", "usuario": "", "estado": ""}
    usuario = db.scalar(select(User).where(User.id == user_id))
    if not usuario:
        return {"id": str(user_id), "usuario": "", "estado": ""}
    return {
        "id": str(usuario.id),
        "usuario": usuario.username,
        "estado": usuario.status,
    }


def _ref_funcionario(
    db: Session, ctx: CompanyContext, official_id: str | None
) -> dict:
    if not official_id:
        return {"id": "", "codigo": "", "nombre": "", "documento": ""}
    funcionario = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == official_id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    if not funcionario:
        return {
            "id": str(official_id),
            "codigo": "",
            "nombre": "",
            "documento": "",
        }
    return {
        "id": str(funcionario.id),
        "codigo": funcionario.codigo,
        "nombre": funcionario.nombre,
        "documento": enmascarar_documento(
            funcionario.tipo_documento, funcionario.numero_documento
        ),
    }


def _resumen(
    db: Session, ctx: CompanyContext, v: GovernmentUserOfficialLink, fecha: date
) -> dict:
    return {
        "id": str(v.id),
        "codigo": v.codigo,
        "cuenta": _ref_cuenta(db, v.user_id),
        "funcionario": _ref_funcionario(db, ctx, v.official_id),
        "desde": v.desde.isoformat() if v.desde else None,
        "hasta": v.hasta.isoformat() if v.hasta else None,
        "fin_efectivo": v.fin_efectivo.isoformat() if v.fin_efectivo else None,
        "status": v.status,
        "situacion": situacion_vinculo(v, fecha),
        "version": v.version,
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    usuario_id: str | None,
    funcionario_id: str | None,
    fecha: date | None,
    pagina: int,
    por_pagina: int,
) -> dict:
    if fecha is None:
        fecha = hoy_de_negocio()
    query = _consulta_vinculos(ctx, estado, usuario_id, funcionario_id)
    query = query.order_by(
        GovernmentUserOfficialLink.desde.desc(), GovernmentUserOfficialLink.codigo
    )
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    offset = (pagina - 1) * por_pagina
    rows = db.execute(query.offset(offset).limit(por_pagina)).scalars().all()
    items = [_resumen(db, ctx, v, fecha) for v in rows]
    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "fecha": fecha,
    }


def _celda(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    if texto and texto[0] in "=+-@\t\r":
        return "'" + texto
    return texto


def exportar_csv(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    usuario_id: str | None,
    funcionario_id: str | None,
    fecha: date | None,
) -> tuple[str, bytes]:
    if fecha is None:
        fecha = hoy_de_negocio()
    query = _consulta_vinculos(ctx, estado, usuario_id, funcionario_id)
    query = query.order_by(
        GovernmentUserOfficialLink.desde.desc(), GovernmentUserOfficialLink.codigo
    )
    rows = db.execute(query).scalars().all()
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "Código",
            "Cuenta",
            "Funcionario",
            "Documento",
            "Desde",
            "Hasta",
            "Situación",
        ]
    )
    for v in rows:
        resumen = _resumen(db, ctx, v, fecha)
        cuenta_ref = resumen.get("cuenta") or {}
        funcionario_ref = resumen.get("funcionario") or {}
        writer.writerow(
            [
                _celda(resumen.get("codigo")),
                _celda(cuenta_ref.get("usuario")),
                _celda(funcionario_ref.get("nombre")),
                _celda(funcionario_ref.get("documento")),
                _celda(resumen.get("desde")),
                _celda(resumen.get("hasta")),
                _celda(resumen.get("situacion")),
            ]
        )
    total = len(rows)
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_LINKS_EXPORTED",
        None,
        None,
        {
            "total": total,
            "filtros": {
                "estado": estado,
                "usuario_id": usuario_id,
                "funcionario_id": funcionario_id,
            },
            "fecha": fecha.isoformat(),
        },
    )
    content = output.getvalue().encode("utf-8")
    nombre = f"identidad-{fecha.isoformat()}.csv"
    return nombre, content


def resumen(
    db: Session, ctx: CompanyContext, v: GovernmentUserOfficialLink, fecha: date
) -> dict:
    return _resumen(db, ctx, v, fecha)


def detalle_base(db: Session, ctx: CompanyContext, id: str, fecha: date) -> dict:
    vinculo = db.scalar(
        select(GovernmentUserOfficialLink).where(
            GovernmentUserOfficialLink.id == id,
            GovernmentUserOfficialLink.company_id == ctx.company_id,
        )
    )
    if not vinculo:
        raise NotFoundError("GOV_IDENTITY_LINK_NOT_FOUND", "El vínculo no existe")
    base = _resumen(db, ctx, vinculo, fecha)
    usuarios_ids = [
        uid for uid in [vinculo.created_by, vinculo.activated_by, vinculo.ended_by] if uid
    ]
    usuarios = _usuarios_por_ids(db, usuarios_ids, ctx.tenant_id)
    historia_rows = db.execute(
        select(GovernmentUserOfficialLinkHistory)
        .where(GovernmentUserOfficialLinkHistory.link_id == vinculo.id)
        .order_by(GovernmentUserOfficialLinkHistory.created_at)
    ).scalars().all()
    historia = [
        {
            "id": str(h.id),
            "tipo": h.tipo,
            "detalle": h.detalle,
            "actor": usuarios.get(str(h.created_by)),
            "creado_en": _instante(h.created_at),
        }
        for h in historia_rows
    ]
    base.update(
        {
            "motivo": vinculo.motivo,
            "soporte": vinculo.soporte,
            "motivo_fin": vinculo.motivo_fin,
            "registrado_por": usuarios.get(str(vinculo.created_by))
            if vinculo.created_by
            else None,
            "activado_por": usuarios.get(str(vinculo.activated_by))
            if vinculo.activated_by
            else None,
            "activado_en": _instante(vinculo.activated_at)
            if vinculo.activated_at
            else None,
            "terminado_por": usuarios.get(str(vinculo.ended_by))
            if vinculo.ended_by
            else None,
            "terminado_en": _instante(vinculo.ended_at)
            if vinculo.ended_at
            else None,
            "historia": historia,
        }
    )
    return base


def contexto_institucional(db: Session, ctx: CompanyContext, user_id: str, fecha: date | None) -> dict:
    hoy = hoy_de_negocio()
    fecha = fecha or hoy
    es_historica = fecha < hoy

    usuario = _cuenta_del_ente(db, ctx, user_id)
    cuenta = {"id": user_id, "usuario": usuario.username, "estado": usuario.status}

    ente = db.scalar(
        select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id)
    )
    ente_info = (
        {"id": str(ente.id), "nombre": ente.denominacion}
        if ente
        else {"id": str(ctx.company_id), "nombre": ctx.company.legal_name}
    )

    vinculos = db.scalars(
        select(GovernmentUserOfficialLink)
        .where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.user_id == user_id,
            GovernmentUserOfficialLink.status.in_(["ACTIVO", "CERRADO", "REVOCADO"]),
        )
        .order_by(GovernmentUserOfficialLink.desde)
    ).all()
    vinculo = next(
        (v for v in vinculos if situacion_vinculo(v, fecha) == "VIGENTE"),
        None,
    )

    roles = roles_de_usuario(db, ctx, user_id, fecha)
    categorias = sorted(categorias_de_usuario(db, ctx, user_id, fecha))
    conflictos = [
        {
            "regla_codigo": c.get("regla_codigo"),
            "regla_nombre": c.get("regla_nombre"),
            "categoria_a": c.get("categoria_a"),
            "categoria_b": c.get("categoria_b"),
        }
        for c in conflictos_de_categorias(db, ctx, set(categorias), fecha)
    ]

    if not vinculo:
        return {
            "fecha": fecha.isoformat(),
            "es_historica": es_historica,
            "ente": ente_info,
            "cuenta": cuenta,
            "vinculo": None,
            "funcionario": None,
            "ocupaciones": [],
            "unidades": [],
            "roles": roles,
            "categorias": categorias,
            "conflictos": conflictos,
            "tiene_autoridad": False,
            "motivo_sin_autoridad": "SIN_VINCULO",
        }

    funcionario = _ref_funcionario(db, ctx, vinculo.official_id)
    ocupaciones = ocupaciones_de_funcionario(db, ctx, str(vinculo.official_id), fecha)
    ocupaciones_mapeadas = [
        {
            "asignacion_id": d["id"],
            "codigo": d["codigo"],
            "figura": d["figura"],
            "figura_etiqueta": d["figura_etiqueta"],
            "cargo_id": d["cargo"]["id"],
            "cargo": d["cargo"]["nombre"],
            "cargo_codigo": d["cargo"]["codigo"],
            "unidad_id": d["cargo"]["unidad_id"],
            "unidad": d["cargo"]["unidad"],
            "ejercicio": d["cargo"]["ejercicio"],
            "ejerce": d["ejerce"],
            "situacion": d["situacion"],
            "desde": d["desde"],
            "hasta": d["fin_efectivo"] or d["hasta"],
            "autoridad": d["autoridad"],
            "avocaciones": len(d["avocaciones"]),
        }
        for d in ocupaciones
    ]

    unidades = []
    for ocupacion in ocupaciones_mapeadas:
        unidad = {"id": ocupacion["unidad_id"], "nombre": ocupacion["unidad"]}
        if unidad not in unidades:
            unidades.append(unidad)

    motivo = None
    if not es_historica and usuario.status != "ACTIVE":
        motivo = "CUENTA_INACTIVA"
    elif not es_historica and _funcionario_de_empresa(db, ctx, str(vinculo.official_id)).estado != "ACTIVO":
        motivo = "FUNCIONARIO_INACTIVO"
    elif not any(ocupacion["ejerce"] for ocupacion in ocupaciones_mapeadas):
        motivo = "SIN_OCUPACION"

    return {
        "fecha": fecha.isoformat(),
        "es_historica": es_historica,
        "ente": ente_info,
        "cuenta": cuenta,
        "vinculo": {
            "id": str(vinculo.id),
            "codigo": vinculo.codigo,
            "situacion": situacion_vinculo(vinculo, fecha),
        },
        "funcionario": funcionario,
        "ocupaciones": ocupaciones_mapeadas,
        "unidades": unidades,
        "roles": roles,
        "categorias": categorias,
        "conflictos": conflictos,
        "tiene_autoridad": motivo is None,
        "motivo_sin_autoridad": motivo,
    }


def mi_contexto(db: Session, ctx: CompanyContext, fecha: date | None) -> dict:
    return contexto_institucional(db, ctx, str(ctx.user_id), fecha)


def detalle(db: Session, ctx: CompanyContext, id: str, fecha: date | None) -> dict:
    base = detalle_base(db, ctx, id, fecha or hoy_de_negocio())
    base["contexto"] = contexto_institucional(db, ctx, base["cuenta"]["id"], fecha)
    return base


ENTIDAD_CATEGORIA = "GovernmentRoleCategory"
ENTIDAD_POLITICA = "GovernmentIdentityPolicy"


def _bloquear_si_conflicto(
    db: Session,
    ctx: CompanyContext,
    categorias: set[str],
    fecha: date,
    objeto_tipo: str,
    objeto_id: str,
) -> None:
    conflictos = conflictos_de_categorias(db, ctx, categorias, fecha)
    if not conflictos:
        return

    regla_id = conflictos[0]["regla_id"]
    categoria_a = conflictos[0].get("categoria_a", "")
    categoria_b = conflictos[0].get("categoria_b", "")
    tenant_id = ctx.tenant_id
    company_id = ctx.company_id
    user_id = ctx.user_id
    record_audit_after_rollback(
        db,
        action="GOV_SOD_CONFLICT_BLOCKED",
        entity_type="GovernmentSoDRule",
        entity_id=regla_id,
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        after={
            "regla_codigo": conflictos[0].get("regla_codigo"),
            "regla_version": conflictos[0].get("regla_version"),
            "proceso": "ORG-06",
            "accion": "ORG06_CAT_" + categoria_a,
            "accion_previa": "ORG06_CAT_" + categoria_b,
            "objeto_tipo": objeto_tipo,
            "objeto_id": objeto_id,
            "evento_previo_id": None,
        },
    )
    raise ConflictError(
        "GOV_SOD_CONFLICT",
        "Las categorías de la cuenta generan un conflicto de separación de funciones",
        details={"conflictos": conflictos},
    )


def _rol_del_ente(db: Session, ctx: CompanyContext, role_id: str) -> Role:
    rol = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.status == "ACTIVE",
            (Role.tenant_id == ctx.tenant_id) | (Role.tenant_id.is_(None)),
            (Role.company_id.is_(None)) | (Role.company_id == ctx.company_id),
        )
    )
    if rol is None:
        raise NotFoundError("GOV_ROLE_NOT_FOUND", "El rol no existe en este ente")
    return rol


def _salida_categoria(c: GovernmentRoleCategory, rol: Role) -> dict:
    etiqueta = ""
    for codigo, label, _desc in CATEGORIAS_IDENTIDAD:
        if codigo == c.categoria:
            etiqueta = label
            break
    return {
        "id": str(c.id),
        "role_id": str(c.role_id),
        "rol_codigo": rol.code,
        "rol_nombre": rol.name,
        "categoria": c.categoria,
        "categoria_etiqueta": etiqueta,
        "desde": c.desde,
        "hasta": c.hasta,
        "status": c.status,
        "motivo": c.motivo,
        "version": c.version,
    }


def listar_categorias(db: Session, ctx: CompanyContext) -> dict:
    categorias = db.scalars(
        select(GovernmentRoleCategory)
        .where(GovernmentRoleCategory.company_id == ctx.company_id)
        .order_by(GovernmentRoleCategory.desde)
    ).all()
    roles = db.scalars(
        select(Role)
        .where(
            Role.status == "ACTIVE",
            (Role.tenant_id == ctx.tenant_id) | (Role.tenant_id.is_(None)),
            (Role.company_id.is_(None)) | (Role.company_id == ctx.company_id),
        )
        .order_by(Role.code)
    ).all()
    roles_por_id = {str(r.id): r for r in roles}
    items = [
        _salida_categoria(c, roles_por_id[str(c.role_id)])
        for c in categorias
        if str(c.role_id) in roles_por_id
    ]
    return {
        "items": items,
        "roles": [{"id": str(r.id), "codigo": r.code, "nombre": r.name} for r in roles],
    }


def crear_categoria(db: Session, ctx: CompanyContext, datos: Any) -> dict:
    _bloquear_identidad(db, ctx)
    rol = _rol_del_ente(db, ctx, datos.role_id)
    hoy = hoy_de_negocio()

    existente = db.scalar(
        select(GovernmentRoleCategory).where(
            GovernmentRoleCategory.company_id == ctx.company_id,
            GovernmentRoleCategory.role_id == datos.role_id,
            GovernmentRoleCategory.categoria == datos.categoria,
            GovernmentRoleCategory.status == "ACTIVA",
        )
    )
    if existente is not None:
        raise ConflictError("GOV_ROLE_CATEGORY_DUPLICATE", "El rol ya tiene esa categoría")

    vinculos = db.scalars(
        select(GovernmentUserOfficialLink).where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.status == "ACTIVO",
        )
    ).all()
    for v in vinculos:
        if situacion_vinculo(v, hoy) != "VIGENTE":
            continue
        tiene_rol = db.scalar(
            select(UserRole.id).where(
                UserRole.user_id == v.user_id,
                UserRole.role_id == rol.id,
                (UserRole.company_id.is_(None)) | (UserRole.company_id == ctx.company_id),
            )
        )
        if tiene_rol is None:
            continue
        categorias = categorias_de_usuario(db, ctx, str(v.user_id), hoy)
        categorias.add(datos.categoria)
        _bloquear_si_conflicto(db, ctx, categorias, hoy, ENTIDAD_VINCULO, str(v.id))

    c = GovernmentRoleCategory(
        company_id=ctx.company_id,
        role_id=datos.role_id,
        categoria=datos.categoria,
        desde=datos.desde,
        hasta=None,
        status="ACTIVA",
        motivo=datos.motivo,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_ROLE_CATEGORY_DUPLICATE", "El rol ya tiene esa categoría") from None

    estado = {
        "role_id": c.role_id,
        "categoria": c.categoria,
        "desde": c.desde.isoformat() if isinstance(c.desde, date) else str(c.desde),
        "hasta": None,
        "status": c.status,
        "motivo": c.motivo,
    }
    db.add(
        GovernmentRoleCategoryHistory(
            category_id=c.id,
            company_id=ctx.company_id,
            tipo="AGREGADA",
            detalle={"despues": estado},
            created_by=ctx.user_id,
        )
    )
    _auditar(
        db,
        ctx,
        "GOV_ROLE_CATEGORY_ADDED",
        str(c.id),
        None,
        estado,
        datos.motivo,
        entidad=ENTIDAD_CATEGORIA,
    )
    return _salida_categoria(c, rol)


def retirar_categoria(
    db: Session, ctx: CompanyContext, id: str, datos: Any, version: int | None
) -> dict:
    if version is None:
        raise KontrolError(
            code="GOV_IDENTITY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )

    c = db.scalar(
        select(GovernmentRoleCategory)
        .where(
            GovernmentRoleCategory.id == id,
            GovernmentRoleCategory.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if c is None:
        raise NotFoundError("GOV_ROLE_CATEGORY_NOT_FOUND", "La categoría no existe")

    if c.version != version:
        raise ConflictError(
            "GOV_IDENTITY_STALE",
            "La categoría cambió desde que la abrió; recárguela",
            details={"version_actual": c.version},
        )

    if c.status != "ACTIVA":
        raise ConflictError(
            "GOV_IDENTITY_INVALID_STATE",
            "La categoría debe estar en estado ACTIVA",
        )

    if datos.fecha < c.desde:
        raise KontrolError(
            code="GOV_IDENTITY_INVALID",
            message="La fecha de retiro no puede ser anterior al inicio",
            field_errors={"fecha": ["La fecha de retiro no puede ser anterior al inicio"]},
            status_code=422,
        )

    rol = _rol_del_ente(db, ctx, c.role_id)
    antes = {
        "role_id": c.role_id,
        "categoria": c.categoria,
        "desde": c.desde.isoformat() if isinstance(c.desde, date) else str(c.desde),
        "hasta": c.hasta.isoformat() if isinstance(c.hasta, date) else c.hasta,
        "status": c.status,
        "motivo": c.motivo,
    }

    c.status = "RETIRADA"
    c.hasta = datos.fecha
    c.version += 1

    despues = {
        "role_id": c.role_id,
        "categoria": c.categoria,
        "desde": c.desde.isoformat() if isinstance(c.desde, date) else str(c.desde),
        "hasta": c.hasta.isoformat() if isinstance(c.hasta, date) else c.hasta,
        "status": c.status,
        "motivo": c.motivo,
    }

    db.add(
        GovernmentRoleCategoryHistory(
            category_id=c.id,
            company_id=ctx.company_id,
            tipo="RETIRADA",
            detalle={"antes": antes, "despues": despues},
            created_by=ctx.user_id,
        )
    )
    _auditar(
        db,
        ctx,
        "GOV_ROLE_CATEGORY_RETIRED",
        str(c.id),
        antes,
        despues,
        datos.motivo,
        entidad=ENTIDAD_CATEGORIA,
    )
    return _salida_categoria(c, rol)


def conflictos(db: Session, ctx: CompanyContext) -> dict:
    hoy = hoy_de_negocio()
    vinculos = db.scalars(
        select(GovernmentUserOfficialLink).where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.status == "ACTIVO",
        )
    ).all()
    items = []
    for v in vinculos:
        if situacion_vinculo(v, hoy) != "VIGENTE":
            continue
        categorias = categorias_de_usuario(db, ctx, str(v.user_id), hoy)
        lista = conflictos_de_categorias(db, ctx, categorias, hoy)
        if not lista:
            continue
        items.append(
            {
                "vinculo_id": v.id,
                "codigo": v.codigo,
                "cuenta": _ref_cuenta(db, v.user_id),
                "funcionario": _ref_funcionario(db, ctx, v.official_id),
                "conflictos": [
                    {
                        "regla_codigo": conflicto.get("regla_codigo"),
                        "regla_nombre": conflicto.get("regla_nombre"),
                        "categoria_a": conflicto.get("categoria_a"),
                        "categoria_b": conflicto.get("categoria_b"),
                    }
                    for conflicto in lista
                ],
            }
        )
    return {"items": items}


def _politica_de(
    db: Session, ctx: CompanyContext, bloquear: bool = False
) -> GovernmentIdentityPolicy | None:
    query = select(GovernmentIdentityPolicy).where(
        GovernmentIdentityPolicy.company_id == ctx.company_id
    )
    if bloquear:
        query = query.with_for_update()
    return db.scalar(query)


def politica(db: Session, ctx: CompanyContext) -> dict:
    p = _politica_de(db, ctx)
    if p is None:
        return {"exige_identidad": False, "version": 0, "motivo": None, "historia": []}

    historias = db.scalars(
        select(GovernmentIdentityPolicyHistory)
        .where(GovernmentIdentityPolicyHistory.policy_id == p.id)
        .order_by(GovernmentIdentityPolicyHistory.created_at)
    ).all()
    ids_actor = list({h.created_by for h in historias if h.created_by})
    usuarios = _usuarios_por_ids(db, ids_actor, ctx.tenant_id) if ids_actor else {}

    historia = []
    for h in historias:
        actor = usuarios.get(h.created_by) if h.created_by else None
        historia.append(
            {
                "id": h.id,
                "tipo": h.tipo,
                "detalle": h.detalle,
                "actor": actor,
                "creado_en": _instante(h.created_at),
            }
        )

    return {
        "exige_identidad": p.exige_identidad,
        "version": p.version,
        "motivo": p.motivo,
        "historia": historia,
    }


def cambiar_politica(
    db: Session, ctx: CompanyContext, datos: Any, version: int | None
) -> dict:
    if version is None:
        raise KontrolError(
            code="GOV_IDENTITY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )

    p = _politica_de(db, ctx, bloquear=True)
    if p is None and version != 0:
        raise ConflictError(
            "GOV_IDENTITY_STALE",
            "La política cambió desde que la abrió; recárguela",
        )
    if p is not None and p.version != version:
        raise ConflictError(
            "GOV_IDENTITY_STALE",
            "La política cambió desde que la abrió; recárguela",
        )

    before = {"exige_identidad": p.exige_identidad} if p is not None else None

    if p is None:
        p = GovernmentIdentityPolicy(
            company_id=ctx.company_id,
            exige_identidad=datos.exige_identidad,
            motivo=datos.motivo,
            version=1,
            created_by=ctx.user_id,
        )
        db.add(p)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError(
                "GOV_IDENTITY_STALE",
                "La política cambió desde que la abrió; recárguela",
            ) from None
    else:
        p.exige_identidad = datos.exige_identidad
        p.motivo = datos.motivo
        p.version += 1

    after = {"exige_identidad": p.exige_identidad, "motivo": p.motivo}
    db.add(
        GovernmentIdentityPolicyHistory(
            policy_id=p.id,
            company_id=ctx.company_id,
            tipo="CAMBIADA",
            detalle={"antes": before, "despues": after},
            created_by=ctx.user_id,
        )
    )
    _auditar(
        db,
        ctx,
        "GOV_IDENTITY_POLICY_CHANGED",
        str(p.id),
        before,
        after,
        datos.motivo,
        entidad=ENTIDAD_POLITICA,
    )
    return politica(db, ctx)


def exigir_autoridad_funcional(
    db: Session, ctx: CompanyContext, cargo_id: str, accion: str, materia: str
) -> None:
    p = _politica_de(db, ctx)
    if p is None or not p.exige_identidad:
        return

    contexto = contexto_institucional(db, ctx, str(ctx.user_id), None)
    vinculo = contexto["vinculo"]

    if vinculo is None:
        _bloquear_guarda(
            db,
            ctx,
            str(p.id),
            "GOV_IDENTITY_LINK_REQUIRED",
            "Su cuenta no tiene un vínculo institucional vigente en este ente",
            accion,
        )

    tiene_competencia = False
    for ocupacion in contexto.get("ocupaciones", []):
        if not ocupacion.get("ejerce") or ocupacion.get("cargo_id") != str(cargo_id):
            continue
        for autoridad in ocupacion.get("autoridad", []):
            if autoridad.get("accion") == accion and autoridad.get("materia") == materia:
                tiene_competencia = True
                break
        if tiene_competencia:
            break

    if not tiene_competencia or contexto.get("tiene_autoridad") is False:
        _bloquear_guarda(
            db,
            ctx,
            str(p.id),
            "GOV_FUNCTIONAL_AUTHORITY_REQUIRED",
            "Su funcionario no ejerce hoy ese cargo con esa competencia",
            accion,
        )

    _bloquear_si_conflicto(
        db,
        ctx,
        set(contexto.get("categorias", [])),
        hoy_de_negocio(),
        ENTIDAD_VINCULO,
        str(vinculo["id"]),
    )


def _bloquear_guarda(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    codigo: str,
    mensaje: str,
    accion: str,
) -> NoReturn:
    tenant_id = ctx.tenant_id
    company_id = ctx.company_id
    user_id = ctx.user_id
    record_audit_after_rollback(
        db,
        action="GOV_IDENTITY_GUARD_BLOCKED",
        entity_type=ENTIDAD_POLITICA,
        entity_id=politica_id,
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        after={"operacion": codigo, "accion": accion},
    )
    raise KontrolError(code=codigo, message=mensaje, status_code=403)
