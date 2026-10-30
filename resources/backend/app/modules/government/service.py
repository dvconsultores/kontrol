"""Servicio de dominio del ente de Gobierno (GOV-0 · Configurar el ente)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.government.models import GovernmentEntity, GovernmentEntityVersion
from app.modules.government.schemas import EnteCambio, EnteIn
from app.shared.audit import record_audit
from app.shared.mixins import utcnow

CAMPOS: tuple[str, ...] = (
    "denominacion",
    "siglas",
    "rif",
    "nivel_territorial",
    "forma_organizativa",
    "organo_adscripcion",
    "entidad_federal",
    "municipio",
    "acto_tipo",
    "acto_numero",
    "acto_fecha",
    "acto_publicacion",
)

ORDEN_FALTANTES: tuple[str, ...] = (
    "DENOMINACION",
    "NIVEL_TERRITORIAL",
    "FORMA_ORGANIZATIVA",
    "ORGANO_ADSCRIPCION",
    "ENTIDAD_FEDERAL",
    "MUNICIPIO",
    "ACTO_TIPO",
    "ACTO_NUMERO",
    "ACTO_FECHA",
    "ACTO_PUBLICACION",
    "DOCUMENTO_ACTO",
)


def _falta(v: Any) -> bool:
    """Indica si un valor está ausente o vacío."""
    return v is None or (isinstance(v, str) and not v.strip())


def faltantes_para_activar(datos: dict[str, Any], documento_vinculado: bool) -> list[str]:
    """Calcula los requisitos pendientes para activar el ente."""
    faltantes: list[str] = []
    if _falta(datos.get("denominacion")):
        faltantes.append("DENOMINACION")
    nivel = datos.get("nivel_territorial")
    if _falta(nivel):
        faltantes.append("NIVEL_TERRITORIAL")
    forma = datos.get("forma_organizativa")
    if _falta(forma):
        faltantes.append("FORMA_ORGANIZATIVA")
    if not _falta(forma) and forma != "ADMINISTRACION_CENTRAL" and _falta(datos.get("organo_adscripcion")):
        faltantes.append("ORGANO_ADSCRIPCION")
    if nivel in ("ESTADAL", "MUNICIPAL") and _falta(datos.get("entidad_federal")):
        faltantes.append("ENTIDAD_FEDERAL")
    if nivel == "MUNICIPAL" and _falta(datos.get("municipio")):
        faltantes.append("MUNICIPIO")
    if _falta(datos.get("acto_tipo")):
        faltantes.append("ACTO_TIPO")
    if _falta(datos.get("acto_numero")):
        faltantes.append("ACTO_NUMERO")
    if _falta(datos.get("acto_fecha")):
        faltantes.append("ACTO_FECHA")
    if _falta(datos.get("acto_publicacion")):
        faltantes.append("ACTO_PUBLICACION")
    if not documento_vinculado:
        faltantes.append("DOCUMENTO_ACTO")
    return faltantes


def _instantanea(ente: GovernmentEntity) -> dict[str, Any]:
    """Devuelve los 12 campos del ente como dict serializable."""
    return {
        "denominacion": ente.denominacion,
        "siglas": ente.siglas,
        "rif": ente.rif,
        "nivel_territorial": ente.nivel_territorial,
        "forma_organizativa": ente.forma_organizativa,
        "organo_adscripcion": ente.organo_adscripcion,
        "entidad_federal": ente.entidad_federal,
        "municipio": ente.municipio,
        "acto_tipo": ente.acto_tipo,
        "acto_numero": ente.acto_numero,
        "acto_fecha": ente.acto_fecha.isoformat() if ente.acto_fecha else None,
        "acto_publicacion": ente.acto_publicacion,
    }


def _utc(dt: datetime | None) -> datetime | None:
    """Asegura que un datetime tenga zona UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def documento_vinculado(db: Session, ente: GovernmentEntity) -> bool:
    """Indica si el ente tiene un documento activo vinculado."""
    stmt = (
        select(DocumentLink.id)
        .join(Document, Document.id == DocumentLink.document_id)
        .where(
            DocumentLink.resource_type == "GovernmentEntity",
            DocumentLink.resource_id == ente.id,
            DocumentLink.company_id == ente.company_id,
            Document.company_id == ente.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def a_salida(db: Session, ente: GovernmentEntity) -> dict[str, Any]:
    """Convierte el ente al dict de salida de la API."""
    instantanea = _instantanea(ente)
    vinculado = documento_vinculado(db, ente)
    return {
        "id": str(ente.id),
        **instantanea,
        "acto_fecha": ente.acto_fecha,
        "estado": ente.status,
        "version": ente.version,
        "faltantes_para_activar": faltantes_para_activar(instantanea, vinculado),
        "documento_vinculado": vinculado,
        "activado_en": _utc(ente.activated_at),
        "activado_por": ente.activated_by,
        "creado_en": _utc(ente.created_at),
        "actualizado_en": _utc(ente.updated_at),
    }


def _buscar(db: Session, ctx: CompanyContext, *, bloquear: bool) -> GovernmentEntity | None:
    """Busca el ente del contenedor, con bloqueo opcional."""
    stmt = select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id)
    if bloquear:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def _versionar(db: Session, ente: GovernmentEntity, ctx: CompanyContext, motivo: str | None) -> None:
    """Registra una instantánea de la versión actual del ente."""
    version = GovernmentEntityVersion(
        entity_id=ente.id,
        company_id=ente.company_id,
        version=ente.version,
        status=ente.status,
        snapshot=_instantanea(ente),
        reason=motivo,
        actor_id=ctx.user_id,
    )
    db.add(version)
    db.flush()


def obtener(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Obtiene el ente del contenedor actual."""
    ente = _buscar(db, ctx, bloquear=False)
    if ente is None:
        raise NotFoundError("GOV_ENTITY_NOT_FOUND", "El ente no está configurado en este contenedor")
    return a_salida(db, ente)


def crear(db: Session, ctx: CompanyContext, datos: EnteIn) -> dict[str, Any]:
    """Crea el ente del contenedor actual."""
    if _buscar(db, ctx, bloquear=False) is not None:
        raise ConflictError("GOV_ENTITY_ALREADY_EXISTS", "Ya hay un ente configurado en este contenedor")
    ente = GovernmentEntity(
        company_id=ctx.company_id,
        created_by=ctx.user_id,
        status="BORRADOR",
        version=1,
        **datos.model_dump(),
    )
    db.add(ente)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_ENTITY_ALREADY_EXISTS", "Ya hay un ente configurado en este contenedor") from None
    _versionar(db, ente, ctx, motivo=None)
    record_audit(
        db,
        action="GOV_ENTITY_CREATED",
        entity_type="GovernmentEntity",
        entity_id=str(ente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=None,
        after={**_instantanea(ente), "estado": ente.status, "version": ente.version},
    )
    return a_salida(db, ente)


def _serializar_campo(v: Any) -> Any:
    """Serializa un valor para auditoría."""
    if isinstance(v, date) and not isinstance(v, datetime):
        return v.isoformat()
    return v


def modificar(db: Session, ctx: CompanyContext, cambios: EnteCambio, expected_version: int | None) -> dict[str, Any]:
    """Aplica cambios parciales al ente con control de concurrencia."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_ENTITY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    ente = _buscar(db, ctx, bloquear=True)
    if ente is None:
        raise NotFoundError("GOV_ENTITY_NOT_FOUND", "El ente no está configurado en este contenedor")
    if expected_version != ente.version:
        raise ConflictError(
            "GOV_ENTITY_STALE",
            "El ente cambió desde que lo abrió; recárguelo",
            details={"version_actual": ente.version},
        )
    campos = {k: getattr(cambios, k) for k in cambios.model_fields_set if k != "motivo"}
    motivo = cambios.motivo
    cambiados = {k: v for k, v in campos.items() if getattr(ente, k) != v}
    if not cambiados:
        raise KontrolError(code="GOV_ENTITY_NO_CHANGES", message="No hay cambios que guardar", status_code=422)
    if ente.status == "ACTIVO":
        if motivo is None or len(motivo) < 5:
            raise KontrolError(
                code="GOV_ENTITY_REASON_REQUIRED",
                message="Indique el motivo de la modificación (de 5 a 255 caracteres)",
                status_code=422,
            )
        instantanea_futura = _instantanea(ente)
        for k, v in cambiados.items():
            instantanea_futura[k] = _serializar_campo(v)
        faltantes = faltantes_para_activar(instantanea_futura, documento_vinculado(db, ente))
        if faltantes:
            raise KontrolError(
                code="GOV_ENTITY_INCOMPLETE",
                message="El ente activo no puede quedar incompleto",
                status_code=422,
                details={"faltantes": faltantes},
            )
    antes = {k: _serializar_campo(getattr(ente, k)) for k in cambiados}
    for k, v in cambiados.items():
        setattr(ente, k, v)
    ente.version += 1
    _versionar(db, ente, ctx, motivo)
    despues = {k: _serializar_campo(getattr(ente, k)) for k in cambiados}
    record_audit(
        db,
        action="GOV_ENTITY_UPDATED",
        entity_type="GovernmentEntity",
        entity_id=str(ente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={**antes, "version": ente.version - 1},
        after={**despues, "version": ente.version},
        reason=motivo,
    )
    return a_salida(db, ente)


def activar(db: Session, ctx: CompanyContext, expected_version: int | None) -> dict[str, Any]:
    """Activa el ente si está completo y en borrador."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_ENTITY_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    ente = _buscar(db, ctx, bloquear=True)
    if ente is None:
        raise NotFoundError("GOV_ENTITY_NOT_FOUND", "El ente no está configurado en este contenedor")
    if expected_version != ente.version:
        raise ConflictError(
            "GOV_ENTITY_STALE",
            "El ente cambió desde que lo abrió; recárguelo",
            details={"version_actual": ente.version},
        )
    if ente.status != "BORRADOR":
        raise ConflictError("GOV_ENTITY_INVALID_STATE", "El ente ya está activo")
    faltantes = faltantes_para_activar(_instantanea(ente), documento_vinculado(db, ente))
    if faltantes:
        raise KontrolError(
            code="GOV_ENTITY_INCOMPLETE",
            message="Faltan datos o el documento del acto para activar el ente",
            status_code=422,
            details={"faltantes": faltantes},
        )
    ente.status = "ACTIVO"
    ente.activated_at = utcnow()
    ente.activated_by = ctx.user_id
    ente.version += 1
    _versionar(db, ente, ctx, motivo=None)
    record_audit(
        db,
        action="GOV_ENTITY_ACTIVATED",
        entity_type="GovernmentEntity",
        entity_id=str(ente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={"estado": "BORRADOR", "version": ente.version - 1},
        after={"estado": "ACTIVO", "version": ente.version},
    )
    return a_salida(db, ente)


def versiones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Lista las versiones históricas del ente."""
    ente = _buscar(db, ctx, bloquear=False)
    if ente is None:
        raise NotFoundError("GOV_ENTITY_NOT_FOUND", "El ente no está configurado en este contenedor")
    stmt = (
        select(GovernmentEntityVersion)
        .where(
            GovernmentEntityVersion.entity_id == ente.id,
            GovernmentEntityVersion.company_id == ctx.company_id,
        )
        .order_by(GovernmentEntityVersion.version.asc())
    )
    filas = db.execute(stmt).scalars().all()
    items = [
        {
            "version": f.version,
            "estado": f.status,
            "motivo": f.reason,
            "actor_id": f.actor_id,
            "creado_en": _utc(f.created_at),
            "datos": f.snapshot,
        }
        for f in filas
    ]
    return {"items": items, "total": len(items)}
