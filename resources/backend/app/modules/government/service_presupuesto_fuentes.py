"""Servicio de dominio de fuentes de financiamiento (BUD-04)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, NotFoundError
from app.modules.government.models import (
    GovernmentBudgetClassifier,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetFundingRestriction,
    GovernmentBudgetFundingSource,
    GovernmentBudgetYear,
)
from app.modules.government.service_presupuesto import (
    _auditar,
    _documento_valido,
    _ejercicio_de_empresa,
    _exigir_borrador,
    _historia,
    _invalida,
    _para_escribir,
)


def _fuente_no_encontrada() -> NotFoundError:
    return NotFoundError(
        "GOV_BUDGET_FUNDING_SOURCE_NOT_FOUND",
        "La fuente de financiamiento no existe en este ejercicio",
    )


def _restriccion_no_encontrada() -> NotFoundError:
    return NotFoundError(
        "GOV_BUDGET_FUNDING_RESTRICTION_NOT_FOUND",
        "La restricción no existe en esta fuente",
    )


def _obtener_fuente(db: Session, exercise_id: str, company_id: str, fuente_id: str) -> GovernmentBudgetFundingSource:
    fuente = db.execute(
        select(GovernmentBudgetFundingSource).where(
            GovernmentBudgetFundingSource.id == fuente_id,
            GovernmentBudgetFundingSource.year_id == exercise_id,
            GovernmentBudgetFundingSource.company_id == company_id,
        )
    ).scalar_one_or_none()
    if fuente is None:
        raise _fuente_no_encontrada()
    return fuente


def _normalizar_partidas(
    db: Session,
    ejercicio: GovernmentBudgetYear,
    ctx: CompanyContext,
    partidas: list[str],
) -> list[str]:
    if not partidas:
        return []
    clasificador = db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id,
            GovernmentBudgetClassifier.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if clasificador is None:
        raise ConflictError(
            "GOV_BUDGET_CLASSIFIER_MISSING",
            "El ejercicio no tiene clasificador de partidas",
        )
    items = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
            GovernmentBudgetClassifierItem.tipo == "EGRESO",
        )
    ).scalars().all()
    codigos_egreso = {item.codigo for item in items}
    normalizadas = sorted(set(partidas))
    for codigo in normalizadas:
        if codigo not in codigos_egreso:
            raise _invalida(
                f"La partida {codigo} no es una partida de egresos del clasificador",
                "partidas",
            )
    return normalizadas


def _vista_fuentes(db: Session, ctx: CompanyContext, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    fuentes = db.execute(
        select(GovernmentBudgetFundingSource)
        .where(
            GovernmentBudgetFundingSource.year_id == ejercicio.id,
            GovernmentBudgetFundingSource.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetFundingSource.codigo)
    ).scalars().all()

    source_ids = [f.id for f in fuentes]
    restricciones: list[GovernmentBudgetFundingRestriction] = []
    if source_ids:
        restricciones = list(
            db.execute(
                select(GovernmentBudgetFundingRestriction).where(
                    GovernmentBudgetFundingRestriction.source_id.in_(source_ids),
                    GovernmentBudgetFundingRestriction.company_id == ctx.company_id,
                )
            ).scalars().all()
        )
    restricciones_por_fuente: dict[str, list[GovernmentBudgetFundingRestriction]] = {}
    for restriccion in restricciones:
        restricciones_por_fuente.setdefault(str(restriccion.source_id), []).append(restriccion)

    items = []
    for fuente in fuentes:
        items.append(
            {
                "id": str(fuente.id),
                "codigo": fuente.codigo,
                "denominacion": fuente.denominacion,
                "procedencia": fuente.procedencia,
                "documento_id": fuente.documento_id,
                "documento_sha256": fuente.documento_sha256,
                "vigente_desde": fuente.vigente_desde.isoformat(),
                "vigente_hasta": fuente.vigente_hasta.isoformat() if fuente.vigente_hasta else None,
                "restricciones": [
                    {
                        "id": str(r.id),
                        "descripcion": r.descripcion,
                        "fundamento": r.fundamento,
                        "partidas": r.partidas,
                    }
                    for r in restricciones_por_fuente.get(str(fuente.id), [])
                ],
            }
        )
    return {
        "version": ejercicio.version,
        "congelado": ejercicio.estado != "BORRADOR",
        "items": items,
    }


def vista_fuentes(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    return _vista_fuentes(db, ctx, ejercicio)


def _validar_fechas(
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    vigente_desde: date | None,
    vigente_hasta: date | None,
) -> tuple[date, date | None]:
    if vigente_desde is None:
        vigente_desde = date(ejercicio.anio, 1, 1)
    if vigente_desde.year != ejercicio.anio:
        raise _invalida("La fecha de inicio debe estar dentro del ejercicio", "vigente_desde")
    if vigente_hasta is not None and vigente_hasta.year != ejercicio.anio:
        raise _invalida("La fecha de fin debe estar dentro del ejercicio", "vigente_hasta")
    if vigente_hasta is not None and vigente_hasta < vigente_desde:
        raise _invalida("La fecha de fin no puede ser anterior a la de inicio", "vigente_hasta")
    return vigente_desde, vigente_hasta


def _preparar_documento(
    db: Session,
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    documento_id: str | None,
    campo: str = "documento_id",
) -> tuple[str | None, str | None]:
    if documento_id is None:
        return None, None
    documento, sha256 = _documento_valido(db, ctx, ejercicio, documento_id, campo)
    return str(documento.id), sha256


def _cambiar_ejercicio(ejercicio: GovernmentBudgetYear) -> None:
    ejercicio.version += 1


def crear_fuente(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)

    codigo = cuerpo["codigo"]
    existente = db.execute(
        select(GovernmentBudgetFundingSource.id).where(
            GovernmentBudgetFundingSource.year_id == ejercicio.id,
            GovernmentBudgetFundingSource.company_id == ctx.company_id,
            GovernmentBudgetFundingSource.codigo == codigo,
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise _invalida("Ya existe una fuente con ese código", "codigo")

    vigente_desde, vigente_hasta = _validar_fechas(
        ctx, ejercicio, cuerpo.get("vigente_desde"), cuerpo.get("vigente_hasta")
    )
    documento_id, documento_sha256 = _preparar_documento(
        db, ctx, ejercicio, cuerpo.get("documento_id")
    )

    fuente = GovernmentBudgetFundingSource(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        created_by=ctx.user_id,
        codigo=codigo,
        denominacion=cuerpo["denominacion"],
        procedencia=cuerpo["procedencia"],
        documento_id=documento_id,
        documento_sha256=documento_sha256,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
    )
    db.add(fuente)
    _cambiar_ejercicio(ejercicio)
    db.flush()
    _historia(db, ctx, ejercicio, "FUENTE_CREADA", {"codigo": fuente.codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_FUNDING_SOURCE_CREATED",
        {"anio": ejercicio.anio, "codigo": fuente.codigo},
    )
    db.flush()
    return _vista_fuentes(db, ctx, ejercicio)


def modificar_fuente(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    fuente_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    fuente = _obtener_fuente(db, str(ejercicio.id), ctx.company_id, fuente_id)

    vigente_desde, vigente_hasta = _validar_fechas(
        ctx, ejercicio, cuerpo.get("vigente_desde"), cuerpo.get("vigente_hasta")
    )
    documento_id, documento_sha256 = _preparar_documento(
        db, ctx, ejercicio, cuerpo.get("documento_id")
    )

    fuente.denominacion = cuerpo["denominacion"]
    fuente.procedencia = cuerpo["procedencia"]
    fuente.documento_id = documento_id
    fuente.documento_sha256 = documento_sha256
    fuente.vigente_desde = vigente_desde
    fuente.vigente_hasta = vigente_hasta
    _cambiar_ejercicio(ejercicio)
    db.flush()
    _historia(db, ctx, ejercicio, "FUENTE_MODIFICADA", {"codigo": fuente.codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_FUNDING_SOURCE_UPDATED",
        {"anio": ejercicio.anio, "codigo": fuente.codigo},
    )
    db.flush()
    return _vista_fuentes(db, ctx, ejercicio)


def eliminar_fuente(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    fuente_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    fuente = _obtener_fuente(db, str(ejercicio.id), ctx.company_id, fuente_id)

    db.execute(
        delete(GovernmentBudgetFundingRestriction).where(
            GovernmentBudgetFundingRestriction.source_id == fuente.id,
            GovernmentBudgetFundingRestriction.company_id == ctx.company_id,
        )
    )
    db.flush()
    db.delete(fuente)
    _cambiar_ejercicio(ejercicio)
    db.flush()
    _historia(db, ctx, ejercicio, "FUENTE_ELIMINADA", {"codigo": fuente.codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_FUNDING_SOURCE_DELETED",
        {"anio": ejercicio.anio, "codigo": fuente.codigo},
    )
    db.flush()
    return _vista_fuentes(db, ctx, ejercicio)


def agregar_restriccion(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    fuente_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    fuente = _obtener_fuente(db, str(ejercicio.id), ctx.company_id, fuente_id)

    partidas = _normalizar_partidas(db, ejercicio, ctx, cuerpo.get("partidas", []))
    restriccion = GovernmentBudgetFundingRestriction(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        created_by=ctx.user_id,
        source_id=str(fuente.id),
        descripcion=cuerpo["descripcion"],
        fundamento=cuerpo["fundamento"],
        partidas=partidas,
    )
    db.add(restriccion)
    _cambiar_ejercicio(ejercicio)
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "RESTRICCION_AGREGADA",
        {"codigo": fuente.codigo, "partidas": partidas},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_FUNDING_RESTRICTION_ADDED",
        {"anio": ejercicio.anio, "codigo": fuente.codigo, "partidas": partidas},
    )
    db.flush()
    return _vista_fuentes(db, ctx, ejercicio)


def eliminar_restriccion(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    fuente_id: str,
    restriccion_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    fuente = _obtener_fuente(db, str(ejercicio.id), ctx.company_id, fuente_id)

    restriccion = db.execute(
        select(GovernmentBudgetFundingRestriction).where(
            GovernmentBudgetFundingRestriction.id == restriccion_id,
            GovernmentBudgetFundingRestriction.source_id == fuente.id,
            GovernmentBudgetFundingRestriction.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if restriccion is None:
        raise _restriccion_no_encontrada()

    db.delete(restriccion)
    _cambiar_ejercicio(ejercicio)
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "RESTRICCION_ELIMINADA",
        {"codigo": fuente.codigo, "partidas": restriccion.partidas},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_FUNDING_RESTRICTION_REMOVED",
        {"anio": ejercicio.anio, "codigo": fuente.codigo, "partidas": restriccion.partidas},
    )
    db.flush()
    return _vista_fuentes(db, ctx, ejercicio)


def fotografia_fuentes(db: Session, ejercicio: GovernmentBudgetYear) -> list[dict[str, Any]]:
    fuentes = db.execute(
        select(GovernmentBudgetFundingSource)
        .where(
            GovernmentBudgetFundingSource.year_id == ejercicio.id,
            GovernmentBudgetFundingSource.company_id == ejercicio.company_id,
        )
        .order_by(GovernmentBudgetFundingSource.codigo)
    ).scalars().all()

    source_ids = [f.id for f in fuentes]
    restricciones: list[GovernmentBudgetFundingRestriction] = []
    if source_ids:
        restricciones = list(
            db.execute(
                select(GovernmentBudgetFundingRestriction).where(
                    GovernmentBudgetFundingRestriction.source_id.in_(source_ids),
                    GovernmentBudgetFundingRestriction.company_id == ejercicio.company_id,
                )
            ).scalars().all()
        )
    restricciones_por_fuente: dict[str, list[GovernmentBudgetFundingRestriction]] = {}
    for restriccion in restricciones:
        restricciones_por_fuente.setdefault(str(restriccion.source_id), []).append(restriccion)

    resultado = []
    for fuente in fuentes:
        resultado.append(
            {
                "codigo": fuente.codigo,
                "denominacion": fuente.denominacion,
                "procedencia": fuente.procedencia,
                "documento_sha256": fuente.documento_sha256,
                "vigente_desde": fuente.vigente_desde.isoformat(),
                "vigente_hasta": fuente.vigente_hasta.isoformat() if fuente.vigente_hasta else None,
                "restricciones": [
                    {
                        "descripcion": r.descripcion,
                        "fundamento": r.fundamento,
                        "partidas": r.partidas,
                    }
                    for r in restricciones_por_fuente.get(str(fuente.id), [])
                ],
            }
        )
    return resultado
