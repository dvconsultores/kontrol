"""Servicio de dominio de los cargos con competencias y límites de firma/aprobación (GOV-0 · ORG-03)."""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.documents.models import Document, DocumentLink
from app.modules.government.models import (
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.schemas_cargos import (
    CargoCambio,
    CargoIn,
    CompetenciaCambio,
    CompetenciaIn,
    DesactivacionCargoIn,
    RetiroCompetenciaIn,
)
from app.modules.government.service_estructura import (
    _bloqueada_para_escribir,
    _error_campo,
    _estructura,
    _motivo_valido,
    _rango,
    _serializar_valor,
    _utc,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio
from app.shared.mixins import utcnow

ORDEN_FALTANTES_CARGO: tuple[str, ...] = ("ESTRUCTURA_VIGENTE", "COMPETENCIAS", "DOCUMENTO_ACTO")


def faltantes_para_activar(estructura_vigente: bool, competencias: int, documento_vinculado: bool) -> list[str]:
    """Calcula los requisitos pendientes para poner el cargo en vigor."""
    faltantes: list[str] = []
    if not estructura_vigente:
        faltantes.append("ESTRUCTURA_VIGENTE")
    if competencias == 0:
        faltantes.append("COMPETENCIAS")
    if not documento_vinculado:
        faltantes.append("DOCUMENTO_ACTO")
    return faltantes


def _monto_texto(v: Decimal | None) -> str | None:
    """Formatea un monto Decimal para salida."""
    if v is None:
        return None
    return f"{v:.2f}"


def _cargo(db: Session, est: GovernmentStructure, cargo_id: str) -> GovernmentPosition:
    """Obtiene un cargo de la estructura, sin revelar cargos ajenos."""
    stmt = select(GovernmentPosition).where(
        GovernmentPosition.id == cargo_id,
        GovernmentPosition.structure_id == est.id,
        GovernmentPosition.company_id == est.company_id,
    )
    cargo = db.execute(stmt).scalar_one_or_none()
    if cargo is None:
        raise NotFoundError("GOV_POSITION_NOT_FOUND", "El cargo no existe en esta estructura")
    return cargo


def _cargos(db: Session, est: GovernmentStructure) -> list[GovernmentPosition]:
    """Lista los cargos de la estructura ordenados por código."""
    stmt = (
        select(GovernmentPosition)
        .where(
            GovernmentPosition.structure_id == est.id,
            GovernmentPosition.company_id == est.company_id,
        )
        .order_by(GovernmentPosition.code.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _competencias(db: Session, cargo: GovernmentPosition) -> list[GovernmentPositionCompetency]:
    """Lista las competencias del cargo ordenadas por acción y materia."""
    stmt = (
        select(GovernmentPositionCompetency)
        .where(
            GovernmentPositionCompetency.position_id == cargo.id,
            GovernmentPositionCompetency.company_id == cargo.company_id,
        )
        .order_by(
            GovernmentPositionCompetency.action.asc(),
            GovernmentPositionCompetency.subject.asc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def _unidad_de(db: Session, est: GovernmentStructure, unidad_id: str) -> GovernmentUnit | None:
    """Obtiene una unidad de la estructura o None si no existe."""
    stmt = select(GovernmentUnit).where(
        GovernmentUnit.id == unidad_id,
        GovernmentUnit.structure_id == est.id,
        GovernmentUnit.company_id == est.company_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def _unidad_activa(db: Session, est: GovernmentStructure, unidad_id: str) -> GovernmentUnit:
    """Exige una unidad activa de la misma estructura."""
    unidad = _unidad_de(db, est, unidad_id)
    if unidad is None or unidad.status != "ACTIVA":
        raise KontrolError(
            code="GOV_POSITION_INVALID_UNIT",
            message="La unidad debe ser una unidad activa de esta misma estructura",
            status_code=422,
        )
    return unidad


def documento_vinculado_cargo(db: Session, cargo: GovernmentPosition) -> bool:
    """Indica si el cargo tiene un documento activo vinculado."""
    stmt = (
        select(DocumentLink.id)
        .join(Document, Document.id == DocumentLink.document_id)
        .where(
            DocumentLink.resource_type == "GovernmentPosition",
            DocumentLink.resource_id == cargo.id,
            DocumentLink.company_id == cargo.company_id,
            Document.company_id == cargo.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _tiene_vinculos(db: Session, cargo: GovernmentPosition) -> bool:
    """Indica si el cargo tiene algún vínculo documental."""
    stmt = (
        select(DocumentLink.id)
        .where(
            DocumentLink.resource_type == "GovernmentPosition",
            DocumentLink.resource_id == cargo.id,
            DocumentLink.company_id == cargo.company_id,
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _competencia_dict(k: GovernmentPositionCompetency) -> dict[str, Any]:
    """Serializa una competencia para salida."""
    return {
        "accion": k.action,
        "materia": k.subject,
        "tipo_limite": k.limit_type,
        "monto": _monto_texto(k.limit_amount),
        "moneda": k.limit_currency,
        "fundamento": k.basis,
    }


def _instantanea_cargo(db: Session, est: GovernmentStructure, cargo: GovernmentPosition) -> dict[str, Any]:
    """Devuelve la instantánea serializable de un cargo."""
    unidad = _unidad_de(db, est, cargo.unit_id)
    return {
        "codigo": cargo.code,
        "denominacion": cargo.name,
        "unidad_id": cargo.unit_id,
        "unidad_codigo": unidad.code if unidad is not None else None,
        "estado": cargo.status,
        "vigente_desde": cargo.valid_from.isoformat() if cargo.valid_from else None,
        "vigente_hasta": cargo.valid_to.isoformat() if cargo.valid_to else None,
        "competencias": [_competencia_dict(k) for k in _competencias(db, cargo)],
    }


def _versionar_cargo(
    db: Session,
    est: GovernmentStructure,
    cargo: GovernmentPosition,
    ctx: CompanyContext,
    motivo: str | None,
) -> None:
    """Registra una instantánea de la versión actual del cargo."""
    version = GovernmentPositionVersion(
        position_id=cargo.id,
        structure_id=est.id,
        company_id=cargo.company_id,
        version=cargo.version,
        status=cargo.status,
        snapshot=_instantanea_cargo(db, est, cargo),
        reason=motivo,
        actor_id=ctx.user_id,
    )
    db.add(version)
    db.flush()


def _salida_cargo(db: Session, est: GovernmentStructure, cargo: GovernmentPosition) -> dict[str, Any]:
    """Convierte un cargo al dict de salida de la API."""
    competencias = _competencias(db, cargo)
    vinculado = documento_vinculado_cargo(db, cargo)
    if cargo.status == "BORRADOR":
        faltantes = faltantes_para_activar(
            est.status == "VIGENTE",
            len(competencias),
            vinculado,
        )
    else:
        faltantes = []
    unidad = _unidad_de(db, est, cargo.unit_id)
    return {
        "id": str(cargo.id),
        "codigo": cargo.code,
        "denominacion": cargo.name,
        "unidad_id": cargo.unit_id,
        "unidad_codigo": unidad.code if unidad is not None else None,
        "unidad_denominacion": unidad.name if unidad is not None else None,
        "estado": cargo.status,
        "vigente_desde": cargo.valid_from,
        "vigente_hasta": cargo.valid_to,
        "version": cargo.version,
        "competencias": [{"id": str(k.id), **_competencia_dict(k)} for k in competencias],
        "faltantes_para_activar": faltantes,
        "documento_vinculado": vinculado,
        "activado_en": _utc(cargo.activated_at),
        "activado_por": cargo.activated_by,
        "creado_en": _utc(cargo.created_at),
    }


def _exigir_if_match(expected_version: int | None) -> None:
    """Exige la cabecera If-Match con la versión del cargo."""
    if expected_version is None:
        raise KontrolError(
            code="GOV_POSITION_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión del cargo",
            status_code=428,
        )


def cargo_para_escribir(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    expected_version: int | None,
) -> tuple[GovernmentStructure, GovernmentPosition]:
    """Prepara un cargo para escritura con control de concurrencia."""
    _exigir_if_match(expected_version)
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    cargo = _cargo(db, est, cargo_id)
    if expected_version != cargo.version:
        raise ConflictError(
            "GOV_POSITION_STALE",
            "El cargo cambió desde que lo abrió; recárguelo",
            details={"version_actual": cargo.version},
        )
    return est, cargo


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    entity_type: str,
    entity_id: str,
    before: Any,
    after: Any,
    motivo: str | None = None,
) -> None:
    """Registra un evento de auditoría del contexto actual."""
    record_audit(
        db,
        action=accion,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=before,
        after=after,
        reason=motivo,
    )


def _exigir_autoridad(cargo: GovernmentPosition, puede_publicar: bool) -> None:
    """Exige autoridad para cambiar competencias según el estado del cargo."""
    if cargo.status == "INACTIVO":
        raise ConflictError("GOV_POSITION_INVALID_STATE", "Un cargo inactivo no cambia sus competencias")
    if cargo.status == "VIGENTE" and not puede_publicar:
        raise PermissionDeniedError(
            "GOV_POSITION_AUTHORITY_REQUIRED",
            "Cambiar la autoridad de un cargo vigente requiere la capacidad de ponerlo en vigor",
        )


def _exigir_motivo_si_vigente(cargo: GovernmentPosition, motivo: str | None) -> None:
    """Exige motivo cuando el cargo está vigente."""
    if cargo.status == "VIGENTE" and not _motivo_valido(motivo):
        raise KontrolError(
            code="GOV_POSITION_REASON_REQUIRED",
            message="Indique el motivo del cambio (de 5 a 255 caracteres)",
            status_code=422,
        )


def _competencia(
    db: Session,
    cargo: GovernmentPosition,
    competencia_id: str,
) -> GovernmentPositionCompetency:
    """Obtiene una competencia del cargo o falla con 404."""
    stmt = select(GovernmentPositionCompetency).where(
        GovernmentPositionCompetency.id == competencia_id,
        GovernmentPositionCompetency.position_id == cargo.id,
        GovernmentPositionCompetency.company_id == cargo.company_id,
    )
    competencia = db.execute(stmt).scalar_one_or_none()
    if competencia is None:
        raise NotFoundError("GOV_COMPETENCY_NOT_FOUND", "La competencia no existe en este cargo")
    return competencia


def _detalle_competencia(cargo: GovernmentPosition, k: GovernmentPositionCompetency) -> dict[str, Any]:
    """Serializa una competencia con el código del cargo."""
    return {"cargo": cargo.code, **_competencia_dict(k)}


def listar_cargos(db: Session, ctx: CompanyContext, ejercicio: int) -> dict[str, Any]:
    """Lista los cargos de la estructura del ejercicio."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    cargos = _cargos(db, est)
    return {
        "estructura": {"ejercicio": est.exercise, "estado": est.status, "version": est.version},
        "items": [_salida_cargo(db, est, cargo) for cargo in cargos],
        "total": len(cargos),
    }


def crear_cargo(db: Session, ctx: CompanyContext, ejercicio: int, datos: CargoIn) -> dict[str, Any]:
    """Registra un cargo en la estructura del ejercicio."""
    est = _estructura(db, ctx, ejercicio, bloquear=True)
    _bloqueada_para_escribir(est)
    unidad = _unidad_activa(db, est, datos.unidad_id)
    inicio, fin = _rango(ejercicio)

    if datos.vigente_desde is not None:
        if datos.vigente_desde < inicio or datos.vigente_desde > fin:
            raise _error_campo("vigente_desde", "Debe estar dentro del ejercicio")
        if datos.vigente_desde < unidad.valid_from:
            raise _error_campo("vigente_desde", "No puede ser anterior al inicio de vigencia de la unidad")
        vigente_desde = datos.vigente_desde
    else:
        if est.status == "BORRADOR":
            vigente_desde = inicio
        else:
            vigente_desde = min(max(hoy_de_negocio(), inicio), fin)
        vigente_desde = max(vigente_desde, unidad.valid_from)

    repetido = db.execute(
        select(GovernmentPosition.id).where(
            GovernmentPosition.structure_id == est.id,
            GovernmentPosition.company_id == est.company_id,
            GovernmentPosition.code == datos.codigo,
        )
    ).first()
    if repetido is not None:
        raise ConflictError(
            "GOV_POSITION_CODE_DUPLICATE",
            "Ya existe un cargo con ese código en esta estructura",
        )

    cargo = GovernmentPosition(
        structure_id=est.id,
        company_id=ctx.company_id,
        unit_id=unidad.id,
        code=datos.codigo,
        name=datos.denominacion,
        status="BORRADOR",
        valid_from=vigente_desde,
        valid_to=None,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(cargo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_POSITION_CODE_DUPLICATE",
            "Ya existe un cargo con ese código en esta estructura",
        ) from None

    _versionar_cargo(db, est, cargo, ctx, motivo=None)
    _auditar(
        db,
        ctx,
        "GOV_POSITION_CREATED",
        "GovernmentPosition",
        str(cargo.id),
        None,
        {**_instantanea_cargo(db, est, cargo), "ejercicio": ejercicio, "version": 1},
    )
    return _salida_cargo(db, est, cargo)


def obtener_cargo(db: Session, ctx: CompanyContext, ejercicio: int, cargo_id: str) -> dict[str, Any]:
    """Obtiene un cargo de la estructura del ejercicio."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    return _salida_cargo(db, est, _cargo(db, est, cargo_id))


def modificar_cargo(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    cambios: CargoCambio,
    expected_version: int | None,
) -> dict[str, Any]:
    """Modifica un cargo con control de concurrencia."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    if cargo.status == "INACTIVO":
        raise ConflictError("GOV_POSITION_INVALID_STATE", "Un cargo inactivo no se modifica")

    mapeo = {"codigo": "code", "denominacion": "name", "unidad_id": "unit_id", "vigente_desde": "valid_from"}
    nombres_api = {"code": "codigo", "name": "denominacion", "unit_id": "unidad_id", "valid_from": "vigente_desde"}
    campos = {mapeo[k]: getattr(cambios, k) for k in cambios.model_fields_set if k in mapeo}
    cambiados = {k: v for k, v in campos.items() if getattr(cargo, k) != v}
    if not cambiados:
        raise KontrolError(code="GOV_POSITION_NO_CHANGES", message="No hay cambios que guardar", status_code=422)

    if cargo.status == "VIGENTE":
        bloqueados = [nombres_api[k] for k in ("code", "valid_from") if k in cambiados]
        if bloqueados:
            raise KontrolError(
                code="GOV_POSITION_FIELD_LOCKED",
                message="En un cargo vigente el código y el inicio de vigencia no se cambian",
                status_code=422,
                details={"campos": bloqueados},
            )
        if not _motivo_valido(cambios.motivo):
            raise KontrolError(
                code="GOV_POSITION_REASON_REQUIRED",
                message="Indique el motivo del cambio (de 5 a 255 caracteres)",
                status_code=422,
            )

    if "unit_id" in cambiados:
        unidad = _unidad_activa(db, est, cambiados["unit_id"])
    else:
        actual = _unidad_de(db, est, cargo.unit_id)
        if actual is None:
            raise KontrolError(
                code="GOV_POSITION_INVALID_UNIT",
                message="La unidad debe ser una unidad activa de esta misma estructura",
                status_code=422,
            )
        unidad = actual

    inicio, fin = _rango(ejercicio)

    if "valid_from" in cambiados:
        if cambiados["valid_from"] < inicio or cambiados["valid_from"] > fin:
            raise _error_campo("vigente_desde", "Debe estar dentro del ejercicio")
        if cambiados["valid_from"] < unidad.valid_from:
            raise _error_campo("vigente_desde", "No puede ser anterior al inicio de vigencia de la unidad")

    if "unit_id" in cambiados and "valid_from" not in cambiados:
        if cargo.valid_from < unidad.valid_from:
            raise _error_campo("unidad_id", "La unidad empieza después del inicio de vigencia del cargo")

    if "code" in cambiados:
        repetido = db.execute(
            select(GovernmentPosition.id).where(
                GovernmentPosition.structure_id == est.id,
                GovernmentPosition.company_id == est.company_id,
                GovernmentPosition.code == cambiados["code"],
                GovernmentPosition.id != cargo.id,
            )
        ).first()
        if repetido is not None:
            raise ConflictError(
                "GOV_POSITION_CODE_DUPLICATE",
                "Ya existe un cargo con ese código en esta estructura",
            )

    antes = {nombres_api[k]: _serializar_valor(getattr(cargo, k)) for k in cambiados}
    version_anterior = cargo.version
    for k, v in cambiados.items():
        setattr(cargo, k, v)
    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, motivo=cambios.motivo)
    despues = {nombres_api[k]: _serializar_valor(getattr(cargo, k)) for k in cambiados}
    _auditar(
        db,
        ctx,
        "GOV_POSITION_UPDATED",
        "GovernmentPosition",
        str(cargo.id),
        {**antes, "version": version_anterior},
        {**despues, "version": cargo.version},
        motivo=cambios.motivo,
    )
    return _salida_cargo(db, est, cargo)


def eliminar_cargo(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    expected_version: int | None,
) -> None:
    """Elimina un cargo en borrador."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    if cargo.status != "BORRADOR":
        raise ConflictError(
            "GOV_POSITION_INVALID_STATE",
            "Solo se elimina un cargo en borrador; un cargo vigente se desactiva",
        )
    if _tiene_vinculos(db, cargo):
        raise ConflictError("GOV_POSITION_HAS_DOCUMENTS", "Desvincule antes el acto del cargo")

    _auditar(
        db,
        ctx,
        "GOV_POSITION_DELETED",
        "GovernmentPosition",
        str(cargo.id),
        {**_instantanea_cargo(db, est, cargo), "ejercicio": ejercicio, "version": cargo.version},
        None,
    )
    db.execute(
        delete(GovernmentPositionCompetency).where(
            GovernmentPositionCompetency.position_id == cargo.id,
            GovernmentPositionCompetency.company_id == ctx.company_id,
        )
    )
    db.execute(
        delete(GovernmentPositionVersion).where(
            GovernmentPositionVersion.position_id == cargo.id,
            GovernmentPositionVersion.company_id == ctx.company_id,
        )
    )
    db.delete(cargo)
    db.flush()


def activar_cargo(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    expected_version: int | None,
) -> dict[str, Any]:
    """Pone en vigor un cargo en borrador."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    if cargo.status != "BORRADOR":
        raise ConflictError("GOV_POSITION_INVALID_STATE", "Solo se pone en vigor un cargo en borrador")

    faltantes = faltantes_para_activar(
        est.status == "VIGENTE",
        len(_competencias(db, cargo)),
        documento_vinculado_cargo(db, cargo),
    )
    if faltantes:
        raise KontrolError(
            code="GOV_POSITION_INCOMPLETE",
            message="Faltan requisitos para poner el cargo en vigor",
            status_code=422,
            details={"faltantes": faltantes},
        )

    unidad = _unidad_de(db, est, cargo.unit_id)
    if unidad is None or unidad.status != "ACTIVA":
        raise KontrolError(
            code="GOV_POSITION_INVALID_UNIT",
            message="La unidad debe ser una unidad activa de esta misma estructura",
            status_code=422,
        )

    version_anterior = cargo.version
    cargo.status = "VIGENTE"
    cargo.activated_at = utcnow()
    cargo.activated_by = ctx.user_id
    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, motivo=None)
    _auditar(
        db,
        ctx,
        "GOV_POSITION_ACTIVATED",
        "GovernmentPosition",
        str(cargo.id),
        {"estado": "BORRADOR", "version": version_anterior},
        {"estado": "VIGENTE", "version": cargo.version, "ejercicio": ejercicio, "codigo": cargo.code},
    )
    return _salida_cargo(db, est, cargo)


def desactivar_cargo(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    datos: DesactivacionCargoIn,
    expected_version: int | None,
) -> dict[str, Any]:
    """Desactiva un cargo vigente."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    if cargo.status != "VIGENTE":
        raise ConflictError("GOV_POSITION_INVALID_STATE", "Solo se desactiva un cargo vigente")

    inicio, fin = _rango(ejercicio)
    if datos.fecha < inicio or datos.fecha > fin or datos.fecha < cargo.valid_from:
        raise _error_campo("fecha", "La fecha debe estar dentro del ejercicio y no antes del inicio de vigencia del cargo")
    if not _motivo_valido(datos.motivo):
        raise KontrolError(
            code="GOV_POSITION_REASON_REQUIRED",
            message="Indique el motivo del cambio (de 5 a 255 caracteres)",
            status_code=422,
        )

    antes = {**_instantanea_cargo(db, est, cargo), "ejercicio": ejercicio, "version": cargo.version}
    cargo.status = "INACTIVO"
    cargo.valid_to = datos.fecha
    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, datos.motivo)
    _auditar(
        db,
        ctx,
        "GOV_POSITION_DEACTIVATED",
        "GovernmentPosition",
        str(cargo.id),
        antes,
        {**_instantanea_cargo(db, est, cargo), "ejercicio": ejercicio, "version": cargo.version},
        datos.motivo,
    )
    return _salida_cargo(db, est, cargo)


def versiones_cargo(db: Session, ctx: CompanyContext, ejercicio: int, cargo_id: str) -> dict[str, Any]:
    """Lista las versiones históricas de un cargo."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    _cargo(db, est, cargo_id)
    stmt = (
        select(GovernmentPositionVersion)
        .where(
            GovernmentPositionVersion.position_id == cargo_id,
            GovernmentPositionVersion.company_id == ctx.company_id,
        )
        .order_by(GovernmentPositionVersion.version.asc())
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


def exportar_cargos_csv(db: Session, ctx: CompanyContext, ejercicio: int) -> tuple[str, bytes]:
    """Exporta los cargos con sus competencias a CSV."""
    est = _estructura(db, ctx, ejercicio, bloquear=False)
    cargos = _cargos(db, est)

    salida = io.StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(
        [
            "codigo_cargo",
            "denominacion",
            "codigo_unidad",
            "estado",
            "vigente_desde",
            "vigente_hasta",
            "accion",
            "materia",
            "tipo_limite",
            "monto",
            "moneda",
            "fundamento",
        ]
    )
    filas = 0
    for cargo in cargos:
        unidad = _unidad_de(db, est, cargo.unit_id)
        competencias = _competencias(db, cargo)
        base = [
            cargo.code,
            cargo.name,
            unidad.code if unidad is not None else "",
            cargo.status,
            cargo.valid_from.isoformat() if cargo.valid_from else "",
            cargo.valid_to.isoformat() if cargo.valid_to else "",
        ]
        if not competencias:
            writer.writerow([*base, "", "", "", "", "", ""])
            filas += 1
        else:
            for k in competencias:
                writer.writerow(
                    [
                        *base,
                        k.action,
                        k.subject,
                        k.limit_type,
                        _monto_texto(k.limit_amount) or "",
                        k.limit_currency or "",
                        k.basis or "",
                    ]
                )
                filas += 1

    _auditar(
        db,
        ctx,
        "GOV_POSITIONS_EXPORTED",
        "GovernmentStructure",
        str(est.id),
        None,
        {"ejercicio": ejercicio, "filas": filas},
    )
    return f"cargos-{ejercicio}.csv", salida.getvalue().encode("utf-8")


def agregar_competencia(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    datos: CompetenciaIn,
    expected_version: int | None,
    puede_publicar: bool,
) -> dict[str, Any]:
    """Agrega una competencia al cargo."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    _exigir_autoridad(cargo, puede_publicar)
    _exigir_motivo_si_vigente(cargo, datos.motivo)

    duplicada = db.execute(
        select(GovernmentPositionCompetency.id).where(
            GovernmentPositionCompetency.position_id == cargo.id,
            GovernmentPositionCompetency.company_id == cargo.company_id,
            GovernmentPositionCompetency.action == datos.accion,
            GovernmentPositionCompetency.subject == datos.materia,
        )
    ).first()
    if duplicada is not None:
        raise ConflictError(
            "GOV_COMPETENCY_DUPLICATE",
            "El cargo ya tiene esa competencia (acción y materia)",
        )

    competencia = GovernmentPositionCompetency(
        position_id=cargo.id,
        company_id=cargo.company_id,
        action=datos.accion,
        subject=datos.materia,
        limit_type=datos.tipo_limite,
        limit_amount=datos.monto,
        limit_currency=datos.moneda,
        basis=datos.fundamento,
        created_by=ctx.user_id,
    )
    db.add(competencia)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_COMPETENCY_DUPLICATE",
            "El cargo ya tiene esa competencia (acción y materia)",
        ) from None

    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, datos.motivo)
    _auditar(
        db,
        ctx,
        "GOV_COMPETENCY_GRANTED",
        "GovernmentPosition",
        str(cargo.id),
        None,
        {**_detalle_competencia(cargo, competencia), "version": cargo.version},
        motivo=datos.motivo,
    )
    return _salida_cargo(db, est, cargo)


def cambiar_competencia(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    competencia_id: str,
    datos: CompetenciaCambio,
    expected_version: int | None,
    puede_publicar: bool,
) -> dict[str, Any]:
    """Cambia el límite y fundamento de una competencia del cargo."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    _exigir_autoridad(cargo, puede_publicar)
    competencia = _competencia(db, cargo, competencia_id)

    if (
        datos.tipo_limite,
        datos.monto,
        datos.moneda,
        datos.fundamento,
    ) == (
        competencia.limit_type,
        competencia.limit_amount,
        competencia.limit_currency,
        competencia.basis,
    ):
        raise KontrolError(
            code="GOV_COMPETENCY_NO_CHANGES",
            message="No hay cambios que guardar",
            status_code=422,
        )

    _exigir_motivo_si_vigente(cargo, datos.motivo)
    antes = {**_detalle_competencia(cargo, competencia), "version": cargo.version}

    competencia.limit_type = datos.tipo_limite
    competencia.limit_amount = datos.monto
    competencia.limit_currency = datos.moneda
    competencia.basis = datos.fundamento
    db.flush()

    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, datos.motivo)
    _auditar(
        db,
        ctx,
        "GOV_COMPETENCY_CHANGED",
        "GovernmentPosition",
        str(cargo.id),
        antes,
        {**_detalle_competencia(cargo, competencia), "version": cargo.version},
        motivo=datos.motivo,
    )
    return _salida_cargo(db, est, cargo)


def retirar_competencia(
    db: Session,
    ctx: CompanyContext,
    ejercicio: int,
    cargo_id: str,
    competencia_id: str,
    datos: RetiroCompetenciaIn,
    expected_version: int | None,
    puede_publicar: bool,
) -> dict[str, Any]:
    """Retira una competencia del cargo."""
    est, cargo = cargo_para_escribir(db, ctx, ejercicio, cargo_id, expected_version)
    _exigir_autoridad(cargo, puede_publicar)
    competencia = _competencia(db, cargo, competencia_id)
    _exigir_motivo_si_vigente(cargo, datos.motivo)

    if cargo.status == "VIGENTE" and len(_competencias(db, cargo)) == 1:
        raise ConflictError(
            "GOV_COMPETENCY_LAST",
            "Un cargo vigente conserva al menos una competencia; para dejarlo sin autoridad, desactívelo",
        )

    antes = {**_detalle_competencia(cargo, competencia), "version": cargo.version}
    db.delete(competencia)
    db.flush()

    cargo.version += 1
    _versionar_cargo(db, est, cargo, ctx, datos.motivo)
    _auditar(
        db,
        ctx,
        "GOV_COMPETENCY_REVOKED",
        "GovernmentPosition",
        str(cargo.id),
        antes,
        {"cargo": cargo.code, "version": cargo.version},
        motivo=datos.motivo,
    )
    return _salida_cargo(db, est, cargo)
