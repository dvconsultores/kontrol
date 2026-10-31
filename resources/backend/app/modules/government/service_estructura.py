"""Servicio de dominio de la estructura organizativa por ejercicio (GOV-0 · Estructura organizativa)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.government.models import (
    GovernmentEntity,
    GovernmentStructure,
    GovernmentUnit,
    GovernmentUnitVersion,
)
from app.modules.government.schemas_estructura import DesactivacionIn, EstructuraIn, UnidadCambio, UnidadIn
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio
from app.shared.mixins import utcnow

ORDEN_FALTANTES: tuple[str, ...] = ("UNIDADES", "DOCUMENTO_ACTO", "ENTE_ACTIVO")


def faltantes_para_publicar(unidades_activas: int, documento_vinculado: bool, ente_activo: bool) -> list[str]:
    """Calcula los requisitos pendientes para publicar la estructura."""
    faltantes: list[str] = []
    if unidades_activas == 0:
        faltantes.append("UNIDADES")
    if not documento_vinculado:
        faltantes.append("DOCUMENTO_ACTO")
    if not ente_activo:
        faltantes.append("ENTE_ACTIVO")
    return faltantes


def _motivo_valido(m: str | None) -> bool:
    """Indica si el motivo cumple la longitud exigida."""
    return m is not None and 5 <= len(m) <= 255


def _error_campo(campo: str, mensaje: str) -> KontrolError:
    """Construye un error de validación de campo."""
    return KontrolError(
        code="VALIDATION_ERROR",
        message="Revise la información enviada",
        field_errors={campo: [mensaje]},
        status_code=422,
    )


def _ente(db: Session, ctx: CompanyContext) -> GovernmentEntity:
    """Obtiene el ente del contenedor actual."""
    stmt = select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id)
    ente = db.execute(stmt).scalar_one_or_none()
    if ente is None:
        raise NotFoundError(
            "GOV_ENTITY_NOT_FOUND",
            "Configure primero el ente en Gobierno › Configuración del ente",
        )
    return ente


def _estructura(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    *,
    bloquear: bool,
) -> GovernmentStructure:
    """Obtiene la estructura del ejercicio, con bloqueo opcional."""
    stmt = select(GovernmentStructure).where(
        GovernmentStructure.company_id == ctx.company_id,
        GovernmentStructure.exercise == ejercicio,
    )
    if bloquear:
        stmt = stmt.with_for_update()
    est = db.execute(stmt).scalar_one_or_none()
    if est is None:
        raise NotFoundError("GOV_STRUCTURE_NOT_FOUND", "No hay estructura para ese ejercicio")
    return est


def _unidad(db: Session, est: GovernmentStructure, unidad_id: str) -> GovernmentUnit:
    """Obtiene una unidad de la estructura, sin revelar unidades ajenas."""
    stmt = select(GovernmentUnit).where(
        GovernmentUnit.id == unidad_id,
        GovernmentUnit.structure_id == est.id,
        GovernmentUnit.company_id == est.company_id,
    )
    u = db.execute(stmt).scalar_one_or_none()
    if u is None:
        raise NotFoundError("GOV_UNIT_NOT_FOUND", "La unidad no existe en esta estructura")
    return u


def _unidades(db: Session, est: GovernmentStructure) -> list[GovernmentUnit]:
    """Lista las unidades de la estructura ordenadas por código."""
    stmt = (
        select(GovernmentUnit)
        .where(
            GovernmentUnit.structure_id == est.id,
            GovernmentUnit.company_id == est.company_id,
        )
        .order_by(GovernmentUnit.code.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _niveles(unidades: list[GovernmentUnit]) -> dict[str, int]:
    """Calcula el nivel jerárquico de cada unidad."""
    por_id = {str(u.id): u for u in unidades}
    memo: dict[str, int] = {}

    def nivel(u: GovernmentUnit) -> int:
        clave = str(u.id)
        if clave in memo:
            return memo[clave]
        if u.parent_id is None:
            memo[clave] = 0
            return 0
        superior = por_id.get(u.parent_id)
        if superior is None:
            memo[clave] = 0
            return 0
        memo[clave] = 1 + nivel(superior)
        return memo[clave]

    for u in unidades:
        nivel(u)
    return memo


def _es_descendiente(unidades_por_id: dict[str, GovernmentUnit], candidato_id: str, unidad_id: str) -> bool:
    """Indica si candidato_id es la unidad o una de sus descendientes."""
    actual: str | None = candidato_id
    while actual is not None:
        if actual == unidad_id:
            return True
        u = unidades_por_id.get(actual)
        actual = u.parent_id if u is not None else None
    return False


def _rango(ejercicio: int) -> tuple[date, date]:
    """Devuelve el rango de fechas del ejercicio."""
    return date(ejercicio, 1, 1), date(ejercicio, 12, 31)


def documento_vinculado(db: Session, est: GovernmentStructure) -> bool:
    """Indica si la estructura tiene un documento activo vinculado."""
    stmt = (
        select(DocumentLink.id)
        .join(Document, Document.id == DocumentLink.document_id)
        .where(
            DocumentLink.resource_type == "GovernmentStructure",
            DocumentLink.resource_id == est.id,
            DocumentLink.company_id == est.company_id,
            Document.company_id == est.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _instantanea_unidad(u: GovernmentUnit) -> dict[str, Any]:
    """Devuelve la instantánea serializable de una unidad."""
    return {
        "codigo": u.code,
        "denominacion": u.name,
        "tipo": u.unit_type,
        "unidad_superior_id": u.parent_id,
        "estado": u.status,
        "vigente_desde": u.valid_from.isoformat() if u.valid_from else None,
        "vigente_hasta": u.valid_to.isoformat() if u.valid_to else None,
    }


def _versionar_unidad(db: Session, u: GovernmentUnit, ctx: CompanyContext, motivo: str | None) -> None:
    """Registra una instantánea de la versión actual de la unidad."""
    version = GovernmentUnitVersion(
        unit_id=u.id,
        structure_id=u.structure_id,
        company_id=u.company_id,
        version=u.version,
        status=u.status,
        snapshot=_instantanea_unidad(u),
        reason=motivo,
        actor_id=ctx.user_id,
    )
    db.add(version)
    db.flush()


def _utc(dt: datetime | None) -> datetime | None:
    """Asegura que un datetime tenga zona UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _serializar_valor(v: Any) -> Any:
    """Serializa fechas para auditoría."""
    if isinstance(v, date):
        return v.isoformat()
    return v


def _salida_unidad(u: GovernmentUnit, niveles: dict[str, int]) -> dict[str, Any]:
    """Convierte una unidad al dict de salida de la API."""
    return {
        "id": str(u.id),
        "codigo": u.code,
        "denominacion": u.name,
        "tipo": u.unit_type,
        "unidad_superior_id": u.parent_id,
        "nivel": niveles.get(str(u.id), 0),
        "estado": u.status,
        "vigente_desde": u.valid_from,
        "vigente_hasta": u.valid_to,
        "version": u.version,
    }


def a_salida(db: Session, est: GovernmentStructure) -> dict[str, Any]:
    """Convierte la estructura al dict de salida de la API."""
    unidades = _unidades(db, est)
    niveles = _niveles(unidades)
    activas = sum(1 for u in unidades if u.status == "ACTIVA")
    vinculado = documento_vinculado(db, est)
    ente = db.get(GovernmentEntity, est.entity_id)
    ente_activo = ente is not None and ente.company_id == est.company_id and ente.status == "ACTIVO"
    return {
        "id": str(est.id),
        "ejercicio": est.exercise,
        "estado": est.status,
        "version": est.version,
        "copiada_de": est.copied_from_exercise,
        "faltantes_para_publicar": faltantes_para_publicar(activas, vinculado, ente_activo),
        "documento_vinculado": vinculado,
        "unidades": [_salida_unidad(u, niveles) for u in unidades],
        "publicada_en": _utc(est.published_at),
        "publicada_por": est.published_by,
        "cerrada_en": _utc(est.closed_at),
        "cerrada_por": est.closed_by,
        "creado_en": _utc(est.created_at),
    }


def _bloqueada_para_escribir(est: GovernmentStructure) -> None:
    """Lanza error si la estructura está cerrada."""
    if est.status == "CERRADA":
        raise ConflictError(
            "GOV_STRUCTURE_CLOSED",
            "La estructura de un ejercicio cerrado es de solo lectura",
        )


def listar(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Lista las estructuras del contenedor."""
    _ente(db, ctx)
    stmt = (
        select(GovernmentStructure)
        .where(GovernmentStructure.company_id == ctx.company_id)
        .order_by(GovernmentStructure.exercise.asc())
    )
    estructuras = db.execute(stmt).scalars().all()
    items: list[dict[str, Any]] = []
    for est in estructuras:
        unidades = _unidades(db, est)
        activas = sum(1 for u in unidades if u.status == "ACTIVA")
        items.append(
            {
                "ejercicio": est.exercise,
                "estado": est.status,
                "version": est.version,
                "unidades_activas": activas,
                "publicada_en": _utc(est.published_at),
                "cerrada_en": _utc(est.closed_at),
            }
        )
    return {"items": items, "total": len(items)}


def abrir(db: Session, ctx: CompanyContext, datos: EstructuraIn) -> dict[str, Any]:
    """Abre la estructura de un ejercicio, copiando opcionalmente de otro."""
    ente = _ente(db, ctx)
    existente = db.execute(
        select(GovernmentStructure.id).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == datos.ejercicio,
        )
    ).first()
    if existente is not None:
        raise ConflictError("GOV_STRUCTURE_ALREADY_EXISTS", "Ya existe la estructura de ese ejercicio")

    origen: GovernmentStructure | None = None
    if datos.copiar_de is not None:
        if datos.copiar_de == datos.ejercicio:
            raise KontrolError(
                code="GOV_STRUCTURE_COPY_SOURCE_INVALID",
                message="Solo se copia la estructura vigente o cerrada de otro ejercicio",
                status_code=422,
            )
        origen = db.execute(
            select(GovernmentStructure).where(
                GovernmentStructure.company_id == ctx.company_id,
                GovernmentStructure.exercise == datos.copiar_de,
            )
        ).scalar_one_or_none()
        if origen is None or origen.status not in ("VIGENTE", "CERRADA"):
            raise KontrolError(
                code="GOV_STRUCTURE_COPY_SOURCE_INVALID",
                message="Solo se copia la estructura vigente o cerrada de otro ejercicio",
                status_code=422,
            )

    est = GovernmentStructure(
        company_id=ctx.company_id,
        entity_id=ente.id,
        exercise=datos.ejercicio,
        status="BORRADOR",
        version=1,
        copied_from_exercise=datos.copiar_de,
        created_by=ctx.user_id,
    )
    db.add(est)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_STRUCTURE_ALREADY_EXISTS", "Ya existe la estructura de ese ejercicio") from None

    unidades_copiadas = 0
    if origen is not None:
        origen_unidades = _unidades(db, origen)
        niveles_origen = _niveles(origen_unidades)
        ordenadas = sorted(origen_unidades, key=lambda u: niveles_origen.get(str(u.id), 0))
        nuevos: dict[str, GovernmentUnit] = {}
        for u in ordenadas:
            if u.status != "ACTIVA":
                continue
            nueva = GovernmentUnit(
                structure_id=est.id,
                company_id=ctx.company_id,
                code=u.code,
                name=u.name,
                unit_type=u.unit_type,
                parent_id=nuevos[u.parent_id].id if u.parent_id is not None else None,
                status="ACTIVA",
                valid_from=date(datos.ejercicio, 1, 1),
                valid_to=None,
                version=1,
                created_by=ctx.user_id,
            )
            db.add(nueva)
            db.flush()
            nuevos[str(u.id)] = nueva
            _versionar_unidad(db, nueva, ctx, motivo=f"Copia del ejercicio {datos.copiar_de}")
            unidades_copiadas += 1

    record_audit(
        db,
        action="GOV_STRUCTURE_CREATED",
        entity_type="GovernmentStructure",
        entity_id=str(est.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=None,
        after={
            "ejercicio": est.exercise,
            "estado": est.status,
            "version": est.version,
            "copiada_de": est.copied_from_exercise,
            "unidades_copiadas": unidades_copiadas,
        },
    )
    return a_salida(db, est)


def obtener(db: Session, ctx: CompanyContext, ejercicio: int) -> dict[str, Any]:
    """Obtiene la estructura de un ejercicio."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    return a_salida(db, est)


def crear_unidad(db: Session, ctx: CompanyContext, ejercicio: int, datos: UnidadIn) -> dict[str, Any]:
    """Crea una unidad en la estructura."""
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    motivo = datos.motivo
    if est.status == "VIGENTE" and not _motivo_valido(motivo):
        raise KontrolError(
            code="GOV_UNIT_REASON_REQUIRED",
            message="Indique el motivo del cambio (de 5 a 255 caracteres)",
            status_code=422,
        )

    inicio, fin = _rango(ejercicio)
    if datos.vigente_desde is not None:
        vigente_desde = datos.vigente_desde
    elif est.status == "BORRADOR":
        vigente_desde = inicio
    else:
        hoy = hoy_de_negocio()
        vigente_desde = min(max(hoy, inicio), fin)
    if vigente_desde < inicio or vigente_desde > fin:
        raise _error_campo("vigente_desde", "Debe estar dentro del ejercicio")

    if datos.unidad_superior_id is not None:
        superior = db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == datos.unidad_superior_id,
                GovernmentUnit.structure_id == est.id,
                GovernmentUnit.company_id == est.company_id,
            )
        ).scalar_one_or_none()
        if superior is None or superior.status != "ACTIVA":
            raise KontrolError(
                code="GOV_UNIT_INVALID_PARENT",
                message="La unidad superior debe ser una unidad activa de esta misma estructura",
                status_code=422,
            )

    repetido = db.execute(
        select(GovernmentUnit.id).where(
            GovernmentUnit.structure_id == est.id,
            GovernmentUnit.company_id == est.company_id,
            GovernmentUnit.code == datos.codigo,
        )
    ).first()
    if repetido is not None:
        raise ConflictError(
            "GOV_UNIT_CODE_DUPLICATE",
            "Ya existe una unidad con ese código en esta estructura",
        )

    u = GovernmentUnit(
        structure_id=est.id,
        company_id=ctx.company_id,
        code=datos.codigo,
        name=datos.denominacion,
        unit_type=datos.tipo,
        parent_id=datos.unidad_superior_id,
        status="ACTIVA",
        valid_from=vigente_desde,
        valid_to=None,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(u)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_UNIT_CODE_DUPLICATE",
            "Ya existe una unidad con ese código en esta estructura",
        ) from None
    _versionar_unidad(db, u, ctx, motivo)
    record_audit(
        db,
        action="GOV_UNIT_CREATED",
        entity_type="GovernmentUnit",
        entity_id=str(u.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=None,
        after={**_instantanea_unidad(u), "ejercicio": ejercicio, "version": u.version},
        reason=motivo,
    )
    unidades = _unidades(db, est)
    niveles = _niveles(unidades)
    return _salida_unidad(u, niveles)


def modificar_unidad(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    unidad_id: str,
    cambios: UnidadCambio,
    expected_version: int | None,
) -> dict[str, Any]:
    """Modifica una unidad con control de concurrencia."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_UNIT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la unidad",
            status_code=428,
        )
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    u = _unidad(db, est, unidad_id)
    if expected_version != u.version:
        raise ConflictError(
            "GOV_UNIT_STALE",
            "La unidad cambió desde que la abrió; recárguela",
            details={"version_actual": u.version},
        )
    if u.status == "INACTIVA":
        raise ConflictError("GOV_UNIT_INVALID_STATE", "Una unidad inactiva no se modifica")

    mapeo = {
        "codigo": "code",
        "denominacion": "name",
        "tipo": "unit_type",
        "unidad_superior_id": "parent_id",
        "vigente_desde": "valid_from",
    }
    campos = {mapeo[k]: getattr(cambios, k) for k in cambios.model_fields_set if k in mapeo}
    motivo = cambios.motivo
    cambiados = {k: v for k, v in campos.items() if getattr(u, k) != v}
    if not cambiados:
        raise KontrolError(code="GOV_UNIT_NO_CHANGES", message="No hay cambios que guardar", status_code=422)

    if est.status == "VIGENTE":
        bloqueados = [k for k in ("code", "valid_from") if k in cambiados]
        if bloqueados:
            raise KontrolError(
                code="GOV_UNIT_FIELD_LOCKED",
                message="En una estructura vigente el código y el inicio de vigencia no se cambian",
                status_code=422,
                details={"campos": bloqueados},
            )
        if not _motivo_valido(motivo):
            raise KontrolError(
                code="GOV_UNIT_REASON_REQUIRED",
                message="Indique el motivo del cambio (de 5 a 255 caracteres)",
                status_code=422,
            )

    if "parent_id" in cambiados and cambiados["parent_id"] is not None:
        nuevo_superior = cambiados["parent_id"]
        unidades = _unidades(db, est)
        por_id = {str(x.id): x for x in unidades}
        if nuevo_superior == str(u.id) or _es_descendiente(por_id, nuevo_superior, str(u.id)):
            raise KontrolError(
                code="GOV_UNIT_HIERARCHY_CYCLE",
                message="Una unidad no puede depender de sí misma ni de una de sus subordinadas",
                status_code=422,
            )
        superior = por_id.get(nuevo_superior)
        if superior is None or superior.status != "ACTIVA":
            raise KontrolError(
                code="GOV_UNIT_INVALID_PARENT",
                message="La unidad superior debe ser una unidad activa de esta misma estructura",
                status_code=422,
            )

    if "valid_from" in cambiados:
        inicio, fin = _rango(ejercicio)
        if cambiados["valid_from"] < inicio or cambiados["valid_from"] > fin:
            raise _error_campo("vigente_desde", "Debe estar dentro del ejercicio")

    if "code" in cambiados:
        repetido = db.execute(
            select(GovernmentUnit.id).where(
                GovernmentUnit.structure_id == est.id,
                GovernmentUnit.company_id == est.company_id,
                GovernmentUnit.code == cambiados["code"],
                GovernmentUnit.id != u.id,
            )
        ).first()
        if repetido is not None:
            raise ConflictError(
                "GOV_UNIT_CODE_DUPLICATE",
                "Ya existe una unidad con ese código en esta estructura",
            )

    nombres_api = {
        "code": "codigo",
        "name": "denominacion",
        "unit_type": "tipo",
        "parent_id": "unidad_superior_id",
        "valid_from": "vigente_desde",
    }
    antes = {nombres_api[k]: _serializar_valor(getattr(u, k)) for k in cambiados}
    for k, v in cambiados.items():
        setattr(u, k, v)
    u.version += 1
    _versionar_unidad(db, u, ctx, motivo)
    despues = {nombres_api[k]: _serializar_valor(getattr(u, k)) for k in cambiados}
    record_audit(
        db,
        action="GOV_UNIT_UPDATED",
        entity_type="GovernmentUnit",
        entity_id=str(u.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={**antes, "version": u.version - 1},
        after={**despues, "version": u.version},
        reason=motivo,
    )
    unidades = _unidades(db, est)
    niveles = _niveles(unidades)
    return _salida_unidad(u, niveles)


def desactivar_unidad(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    unidad_id: str,
    datos: DesactivacionIn,
    expected_version: int | None,
) -> dict[str, Any]:
    """Desactiva una unidad de una estructura vigente."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_UNIT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la unidad",
            status_code=428,
        )
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    if est.status != "VIGENTE":
        raise ConflictError(
            "GOV_STRUCTURE_INVALID_STATE",
            "Solo se desactivan unidades de una estructura vigente; en borrador, elimínela",
        )
    u = _unidad(db, est, unidad_id)
    if expected_version != u.version:
        raise ConflictError(
            "GOV_UNIT_STALE",
            "La unidad cambió desde que la abrió; recárguela",
            details={"version_actual": u.version},
        )
    if u.status == "INACTIVA":
        raise ConflictError("GOV_UNIT_INVALID_STATE", "La unidad ya está inactiva")

    hija_activa = db.execute(
        select(GovernmentUnit.id).where(
            GovernmentUnit.structure_id == est.id,
            GovernmentUnit.company_id == est.company_id,
            GovernmentUnit.parent_id == u.id,
            GovernmentUnit.status == "ACTIVA",
        )
    ).first()
    if hija_activa is not None:
        raise ConflictError(
            "GOV_UNIT_HAS_ACTIVE_CHILDREN",
            "Desactive o mueva antes sus unidades subordinadas",
        )

    inicio, fin = _rango(ejercicio)
    if datos.fecha < inicio or datos.fecha > fin or datos.fecha < u.valid_from:
        raise _error_campo("fecha", "La fecha debe estar dentro del ejercicio y no antes del inicio de vigencia")
    if not _motivo_valido(datos.motivo):
        raise KontrolError(
            code="GOV_UNIT_REASON_REQUIRED",
            message="Indique el motivo del cambio (de 5 a 255 caracteres)",
            status_code=422,
        )

    antes = {**_instantanea_unidad(u), "ejercicio": ejercicio, "version": u.version}
    u.status = "INACTIVA"
    u.valid_to = datos.fecha
    u.version += 1
    _versionar_unidad(db, u, ctx, datos.motivo)
    record_audit(
        db,
        action="GOV_UNIT_DEACTIVATED",
        entity_type="GovernmentUnit",
        entity_id=str(u.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=antes,
        after={**_instantanea_unidad(u), "ejercicio": ejercicio, "version": u.version},
        reason=datos.motivo,
    )
    unidades = _unidades(db, est)
    niveles = _niveles(unidades)
    return _salida_unidad(u, niveles)


def eliminar_unidad(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    unidad_id: str,
    expected_version: int | None,
) -> None:
    """Elimina una unidad de una estructura en borrador."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_UNIT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la unidad",
            status_code=428,
        )
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    if est.status != "BORRADOR":
        raise ConflictError(
            "GOV_STRUCTURE_INVALID_STATE",
            "En una estructura vigente las unidades no se eliminan: desactívelas",
        )
    u = _unidad(db, est, unidad_id)
    if expected_version != u.version:
        raise ConflictError(
            "GOV_UNIT_STALE",
            "La unidad cambió desde que la abrió; recárguela",
            details={"version_actual": u.version},
        )

    hija = db.execute(
        select(GovernmentUnit.id).where(
            GovernmentUnit.structure_id == est.id,
            GovernmentUnit.company_id == est.company_id,
            GovernmentUnit.parent_id == u.id,
        )
    ).first()
    if hija is not None:
        raise ConflictError(
            "GOV_UNIT_HAS_CHILDREN",
            "Elimine o mueva antes sus unidades subordinadas",
        )

    record_audit(
        db,
        action="GOV_UNIT_DELETED",
        entity_type="GovernmentUnit",
        entity_id=str(u.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={**_instantanea_unidad(u), "ejercicio": ejercicio, "version": u.version},
        after=None,
    )
    db.execute(
        delete(GovernmentUnitVersion).where(
            GovernmentUnitVersion.unit_id == u.id,
            GovernmentUnitVersion.company_id == ctx.company_id,
        )
    )
    db.delete(u)
    db.flush()


def versiones_unidad(db: Session, ctx: CompanyContext, ejercicio: int, unidad_id: str) -> dict[str, Any]:
    """Lista las versiones históricas de una unidad."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    _unidad(db, est, unidad_id)
    stmt = (
        select(GovernmentUnitVersion)
        .where(
            GovernmentUnitVersion.unit_id == unidad_id,
            GovernmentUnitVersion.company_id == ctx.company_id,
        )
        .order_by(GovernmentUnitVersion.version.asc())
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


def publicar(db: Session, ctx: CompanyContext, ejercicio: int, expected_version: int | None) -> dict[str, Any]:
    """Pone en vigor una estructura en borrador."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_STRUCTURE_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la estructura",
            status_code=428,
        )
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    if expected_version != est.version:
        raise ConflictError(
            "GOV_STRUCTURE_STALE",
            "La estructura cambió desde que la abrió; recárguela",
            details={"version_actual": est.version},
        )
    if est.status != "BORRADOR":
        raise ConflictError(
            "GOV_STRUCTURE_INVALID_STATE",
            "Solo se pone en vigor una estructura en borrador",
        )

    unidades = _unidades(db, est)
    activas = sum(1 for u in unidades if u.status == "ACTIVA")
    vinculado = documento_vinculado(db, est)
    ente = _ente(db, ctx)
    faltantes = faltantes_para_publicar(activas, vinculado, ente.status == "ACTIVO")
    if faltantes:
        raise KontrolError(
            code="GOV_STRUCTURE_INCOMPLETE",
            message="Faltan requisitos para poner la estructura en vigor",
            status_code=422,
            details={"faltantes": faltantes},
        )

    version_anterior = est.version
    est.status = "VIGENTE"
    est.published_at = utcnow()
    est.published_by = ctx.user_id
    est.version += 1
    record_audit(
        db,
        action="GOV_STRUCTURE_PUBLISHED",
        entity_type="GovernmentStructure",
        entity_id=str(est.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={"estado": "BORRADOR", "version": version_anterior},
        after={"estado": "VIGENTE", "version": est.version, "ejercicio": ejercicio},
    )
    return a_salida(db, est)


def cerrar(db: Session, ctx: CompanyContext, ejercicio: int, expected_version: int | None) -> dict[str, Any]:
    """Cierra una estructura vigente."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_STRUCTURE_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la estructura",
            status_code=428,
        )
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    if expected_version != est.version:
        raise ConflictError(
            "GOV_STRUCTURE_STALE",
            "La estructura cambió desde que la abrió; recárguela",
            details={"version_actual": est.version},
        )
    if est.status != "VIGENTE":
        raise ConflictError("GOV_STRUCTURE_INVALID_STATE", "Solo se cierra una estructura vigente")
    if ejercicio >= hoy_de_negocio().year:
        raise KontrolError(
            code="GOV_STRUCTURE_EXERCISE_NOT_ENDED",
            message="El ejercicio aún no ha terminado: se cierra a partir del 1 de enero siguiente",
            status_code=422,
        )

    version_anterior = est.version
    est.status = "CERRADA"
    est.closed_at = utcnow()
    est.closed_by = ctx.user_id
    est.version += 1
    record_audit(
        db,
        action="GOV_STRUCTURE_CLOSED",
        entity_type="GovernmentStructure",
        entity_id=str(est.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before={"estado": "VIGENTE", "version": version_anterior},
        after={"estado": "CERRADA", "version": est.version, "ejercicio": ejercicio},
    )
    return a_salida(db, est)


def exportar_csv(db: Session, ctx: CompanyContext, ejercicio: int) -> tuple[str, bytes]:
    """Exporta la estructura a CSV."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    unidades = _unidades(db, est)
    niveles = _niveles(unidades)
    por_id = {str(u.id): u for u in unidades}

    salida = io.StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(
        ["codigo", "denominacion", "tipo", "codigo_superior", "nivel", "estado", "vigente_desde", "vigente_hasta"]
    )
    for u in unidades:
        superior = por_id.get(u.parent_id) if u.parent_id is not None else None
        writer.writerow(
            [
                u.code,
                u.name,
                u.unit_type,
                superior.code if superior is not None else "",
                niveles.get(str(u.id), 0),
                u.status,
                u.valid_from.isoformat() if u.valid_from else "",
                u.valid_to.isoformat() if u.valid_to else "",
            ]
        )

    record_audit(
        db,
        action="GOV_STRUCTURE_EXPORTED",
        entity_type="GovernmentStructure",
        entity_id=str(est.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=None,
        after={"ejercicio": ejercicio, "filas": len(unidades)},
    )
    return f"estructura-{ejercicio}.csv", salida.getvalue().encode("utf-8")
