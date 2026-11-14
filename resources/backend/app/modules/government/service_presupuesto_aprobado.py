"""Servicio de dominio del presupuesto aprobado: ingresos, créditos y cuadre (BUD-05, LOPPM 229, 238-242)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentBudgetCategory,
    GovernmentBudgetClassifier,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetCredit,
    GovernmentBudgetFundingRestriction,
    GovernmentBudgetFundingSource,
    GovernmentBudgetIncomeEstimate,
    GovernmentBudgetTreasuryHoldings,
    GovernmentBudgetYear,
    GovernmentUnit,
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
from app.shared.clock import hoy_de_negocio


def _monto_valido(monto: Any) -> Decimal:
    if not isinstance(monto, Decimal):
        raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "monto")
    exponente = monto.as_tuple().exponent
    if not monto.is_finite() or not isinstance(exponente, int) or monto <= 0 or exponente < -2 or monto >= Decimal("10000000000000000"):
        raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "monto")
    return monto


def _clasificador_del_ejercicio(db: Session, ejercicio: GovernmentBudgetYear) -> GovernmentBudgetClassifier | None:
    return db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id,
            GovernmentBudgetClassifier.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()


def _partidas_del_clasificador(
    db: Session, clasificador: GovernmentBudgetClassifier | None
) -> dict[str, GovernmentBudgetClassifierItem]:
    if clasificador is None:
        return {}
    partidas = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
            GovernmentBudgetClassifierItem.company_id == clasificador.company_id,
        )
    ).scalars().all()
    return {str(partida.id): partida for partida in partidas}


def _ids_con_hijos(partidas: dict[str, GovernmentBudgetClassifierItem]) -> set[str]:
    return {str(partida.parent_id) for partida in partidas.values() if partida.parent_id is not None}


def _validar_categoria(db: Session, ejercicio: GovernmentBudgetYear, categoria_id: str) -> GovernmentBudgetCategory:
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.id == categoria_id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if categoria is None:
        raise _invalida("La categoría no pertenece a este ejercicio", "categoria_id")
    hijas = db.execute(
        select(GovernmentBudgetCategory.id).where(
            GovernmentBudgetCategory.parent_id == categoria.id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ejercicio.company_id,
        ).limit(1)
    ).first()
    if hijas is not None:
        raise _invalida("Solo se imputan categorías del último nivel", "categoria_id")
    return categoria


def _validar_partida(
    db: Session,
    ejercicio: GovernmentBudgetYear,
    partida_id: str,
    tipo: str,
    campo: str = "partida_id",
) -> GovernmentBudgetClassifierItem:
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        raise ConflictError(
            "GOV_BUDGET_CLASSIFIER_MISSING",
            "El ejercicio no tiene clasificador de partidas",
        )
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.id == partida_id,
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
            GovernmentBudgetClassifierItem.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if partida is None:
        raise _invalida("La partida no pertenece al clasificador del ejercicio", campo)
    if partida.tipo != tipo:
        raise _invalida("La partida debe ser de egresos" if tipo == "EGRESO" else "La partida debe ser de recursos", campo)
    hijas = db.execute(
        select(GovernmentBudgetClassifierItem.id).where(
            GovernmentBudgetClassifierItem.parent_id == partida.id,
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
            GovernmentBudgetClassifierItem.company_id == ejercicio.company_id,
        ).limit(1)
    ).first()
    if hijas is not None:
        raise _invalida("Solo se imputan partidas del último nivel", campo)
    return partida


def _validar_fuente(db: Session, ejercicio: GovernmentBudgetYear, fuente_id: str) -> GovernmentBudgetFundingSource:
    fuente = db.execute(
        select(GovernmentBudgetFundingSource).where(
            GovernmentBudgetFundingSource.id == fuente_id,
            GovernmentBudgetFundingSource.year_id == ejercicio.id,
            GovernmentBudgetFundingSource.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if fuente is None:
        raise _invalida("La fuente no pertenece a este ejercicio", "fuente_id")
    return fuente


def _partidas_permitidas_de_fuente(
    db: Session, ejercicio: GovernmentBudgetYear, fuente_id: str
) -> set[str] | None:
    restricciones = db.execute(
        select(GovernmentBudgetFundingRestriction).where(
            GovernmentBudgetFundingRestriction.source_id == fuente_id,
            GovernmentBudgetFundingRestriction.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    permitidas: set[str] = set()
    hay_lista = False
    for restriccion in restricciones:
        if restriccion.partidas:
            hay_lista = True
            permitidas.update(restriccion.partidas)
    return permitidas if hay_lista else None


def _partida_permitida(
    db: Session,
    ejercicio: GovernmentBudgetYear,
    partida_id: str,
    permitidas: set[str] | None,
) -> bool:
    if permitidas is None:
        return True
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        return False
    partidas = _partidas_del_clasificador(db, clasificador)
    actual_id = partida_id
    while actual_id:
        partida = partidas.get(actual_id)
        if partida is None:
            return False
        if partida.codigo in permitidas:
            return True
        actual_id = str(partida.parent_id) if partida.parent_id is not None else ""
    return False


def _categorias_hojas(db: Session, ejercicio: GovernmentBudgetYear) -> list[GovernmentBudgetCategory]:
    categorias = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    ids_con_hijas = {str(categoria.parent_id) for categoria in categorias if categoria.parent_id is not None}
    return [categoria for categoria in categorias if str(categoria.id) not in ids_con_hijas]


def _partidas_hojas(
    db: Session, ejercicio: GovernmentBudgetYear, tipo: str | None = None
) -> list[GovernmentBudgetClassifierItem]:
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        return []
    partidas = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
            GovernmentBudgetClassifierItem.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    ids_con_hijas = {str(partida.parent_id) for partida in partidas if partida.parent_id is not None}
    resultado = [partida for partida in partidas if str(partida.id) not in ids_con_hijas]
    if tipo is not None:
        resultado = [partida for partida in resultado if partida.tipo == tipo]
    return resultado


def _vista(db: Session, ctx: CompanyContext, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    ingresos = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    existencias = db.execute(
        select(GovernmentBudgetTreasuryHoldings).where(
            GovernmentBudgetTreasuryHoldings.year_id == ejercicio.id,
            GovernmentBudgetTreasuryHoldings.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()

    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    partidas = _partidas_del_clasificador(db, clasificador)
    categorias = {
        str(categoria.id): categoria
        for categoria in db.execute(
            select(GovernmentBudgetCategory).where(
                GovernmentBudgetCategory.year_id == ejercicio.id,
                GovernmentBudgetCategory.company_id == ejercicio.company_id,
            )
        ).scalars().all()
    }
    unidades = {
        str(unidad.id): unidad
        for unidad in db.execute(select(GovernmentUnit).where(GovernmentUnit.company_id == ejercicio.company_id)).scalars().all()
    }
    fuentes = {
        str(fuente.id): fuente
        for fuente in db.execute(
            select(GovernmentBudgetFundingSource).where(
                GovernmentBudgetFundingSource.year_id == ejercicio.id,
                GovernmentBudgetFundingSource.company_id == ejercicio.company_id,
            )
        ).scalars().all()
    }

    ingresos_vista: list[dict[str, Any]] = []
    for ingreso in ingresos:
        partida = partidas.get(str(ingreso.item_id))
        if partida is None:
            continue
        ingresos_vista.append(
            {
                "id": str(ingreso.id),
                "partida": {
                    "id": str(partida.id),
                    "codigo": partida.codigo,
                    "denominacion": partida.denominacion,
                },
                "monto": ingreso.monto,
            }
        )
    ingresos_vista.sort(key=lambda item: str(item["partida"]["codigo"]))

    creditos_vista: list[dict[str, Any]] = []
    for credito in creditos:
        partida = partidas.get(str(credito.item_id))
        categoria = categorias.get(str(credito.category_id))
        fuente = fuentes.get(str(credito.source_id))
        if partida is None or categoria is None or fuente is None:
            continue
        unidad = None
        if categoria.unit_id:
            unidad_obj = unidades.get(str(categoria.unit_id))
            if unidad_obj is not None:
                unidad = {"id": str(unidad_obj.id), "codigo": unidad_obj.code, "nombre": unidad_obj.name}
        creditos_vista.append(
            {
                "id": str(credito.id),
                "categoria": {
                    "id": str(categoria.id),
                    "codigo_completo": categoria.codigo_completo,
                    "denominacion": categoria.denominacion,
                },
                "unidad": unidad,
                "partida": {
                    "id": str(partida.id),
                    "codigo": partida.codigo,
                    "denominacion": partida.denominacion,
                },
                "fuente": {
                    "id": str(fuente.id),
                    "codigo": fuente.codigo,
                    "denominacion": fuente.denominacion,
                },
                "monto": credito.monto,
            }
        )
    creditos_vista.sort(
        key=lambda item: (
            str(item["categoria"]["codigo_completo"]),
            str(item["partida"]["codigo"]),
            str(item["fuente"]["codigo"]),
        )
    )

    total_ingresos = sum((ingreso.monto for ingreso in ingresos), Decimal("0.00"))
    total_creditos = sum((credito.monto for credito in creditos), Decimal("0.00"))
    total_existencias = existencias.monto if existencias is not None else Decimal("0.00")
    holgura_tesoro = total_existencias / 2
    disponible = total_ingresos + holgura_tesoro
    diferencia = disponible - total_creditos
    cuadra = 2 * total_creditos <= 2 * total_ingresos + total_existencias

    existencias_vista = None
    if existencias is not None:
        existencias_vista = {
            "monto": existencias.monto,
            "fecha_corte": existencias.fecha_corte,
            "documento_id": existencias.documento_id,
            "documento_sha256": existencias.documento_sha256,
        }

    categorias_opciones: list[dict[str, Any]] = [
        {"id": str(categoria.id), "codigo_completo": categoria.codigo_completo, "denominacion": categoria.denominacion}
        for categoria in _categorias_hojas(db, ejercicio)
    ]
    categorias_opciones.sort(key=lambda item: str(item["codigo_completo"]))

    partidas_egreso: list[dict[str, Any]] = [
        {"id": str(partida.id), "codigo": partida.codigo, "denominacion": partida.denominacion}
        for partida in _partidas_hojas(db, ejercicio, "EGRESO")
    ]
    partidas_egreso.sort(key=lambda item: str(item["codigo"]))
    partidas_recurso: list[dict[str, Any]] = [
        {"id": str(partida.id), "codigo": partida.codigo, "denominacion": partida.denominacion}
        for partida in _partidas_hojas(db, ejercicio, "RECURSO")
    ]
    partidas_recurso.sort(key=lambda item: str(item["codigo"]))

    fuentes_opciones: list[dict[str, Any]] = []
    for fuente in fuentes.values():
        permitidas = _partidas_permitidas_de_fuente(db, ejercicio, str(fuente.id))
        fuentes_opciones.append(
            {
                "id": str(fuente.id),
                "codigo": fuente.codigo,
                "denominacion": fuente.denominacion,
                "partidas_permitidas": sorted(permitidas) if permitidas is not None else None,
            }
        )
    fuentes_opciones.sort(key=lambda item: str(item["codigo"]))

    return {
        "version": ejercicio.version,
        "congelado": ejercicio.estado != "BORRADOR",
        "moneda": ejercicio.moneda_funcional,
        "ingresos": ingresos_vista,
        "creditos": creditos_vista,
        "existencias_tesoro": existencias_vista,
        "totales": {
            "ingresos": total_ingresos,
            "creditos": total_creditos,
            "existencias": total_existencias,
            "holgura_tesoro": holgura_tesoro,
            "disponible": disponible,
            "diferencia": diferencia,
            "cuadra": cuadra,
        },
        "opciones": {
            "categorias": categorias_opciones,
            "partidas_egreso": partidas_egreso,
            "partidas_recurso": partidas_recurso,
            "fuentes": fuentes_opciones,
        },
    }


def vista(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    return _vista(db, ctx, ejercicio)


def crear_ingreso(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    partida = _validar_partida(db, ejercicio, cuerpo["partida_id"], "RECURSO")
    monto = _monto_valido(cuerpo.get("monto"))
    duplicado = db.execute(
        select(GovernmentBudgetIncomeEstimate.id).where(
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
            GovernmentBudgetIncomeEstimate.item_id == partida.id,
        )
    ).first()
    if duplicado is not None:
        raise ConflictError(
            "GOV_BUDGET_INCOME_DUPLICATE",
            "Ya existe una estimación de ingresos para esa partida",
        )
    ingreso = GovernmentBudgetIncomeEstimate(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        created_by=ctx.user_id,
        item_id=str(partida.id),
        monto=monto,
    )
    db.add(ingreso)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "INGRESO_REGISTRADO", {"codigo": partida.codigo, "monto": str(monto)})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_INCOME_ESTIMATE_CREATED",
        {"anio": ejercicio.anio, "codigo": partida.codigo, "monto": str(monto)},
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def modificar_ingreso(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    ingreso_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    ingreso = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.id == ingreso_id,
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if ingreso is None:
        raise NotFoundError("GOV_BUDGET_INCOME_NOT_FOUND", "La estimación de ingresos no existe en este ejercicio")
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(GovernmentBudgetClassifierItem.id == ingreso.item_id)
    ).scalar_one()
    monto_anterior = ingreso.monto
    monto = _monto_valido(cuerpo.get("monto"))
    ingreso.monto = monto
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "INGRESO_MODIFICADO",
        {"codigo": partida.codigo, "monto_anterior": str(monto_anterior), "monto": str(monto)},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_INCOME_ESTIMATE_UPDATED",
        {"anio": ejercicio.anio, "codigo": partida.codigo, "monto": str(monto)},
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def eliminar_ingreso(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    ingreso_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    ingreso = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.id == ingreso_id,
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if ingreso is None:
        raise NotFoundError("GOV_BUDGET_INCOME_NOT_FOUND", "La estimación de ingresos no existe en este ejercicio")
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(GovernmentBudgetClassifierItem.id == ingreso.item_id)
    ).scalar_one()
    monto = ingreso.monto
    db.delete(ingreso)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "INGRESO_ELIMINADO", {"codigo": partida.codigo, "monto": str(monto)})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_INCOME_ESTIMATE_DELETED",
        {"anio": ejercicio.anio, "codigo": partida.codigo, "monto": str(monto)},
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def crear_credito(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    categoria = _validar_categoria(db, ejercicio, cuerpo["categoria_id"])
    partida = _validar_partida(db, ejercicio, cuerpo["partida_id"], "EGRESO")
    fuente = _validar_fuente(db, ejercicio, cuerpo["fuente_id"])
    monto = _monto_valido(cuerpo.get("monto"))

    permitidas = _partidas_permitidas_de_fuente(db, ejercicio, str(fuente.id))
    if permitidas is not None and not _partida_permitida(db, ejercicio, str(partida.id), permitidas):
        mensaje = (
            f"La fuente {fuente.codigo} está restringida a las partidas {', '.join(sorted(permitidas))}: "
            f"la partida {partida.codigo} no está permitida"
        )
        raise KontrolError(
            code="GOV_BUDGET_CREDIT_SOURCE_RESTRICTED",
            message=mensaje,
            field_errors={"partida_id": [mensaje]},
            status_code=422,
        )

    duplicado = db.execute(
        select(GovernmentBudgetCredit.id).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
            GovernmentBudgetCredit.category_id == categoria.id,
            GovernmentBudgetCredit.item_id == partida.id,
            GovernmentBudgetCredit.source_id == fuente.id,
        )
    ).first()
    if duplicado is not None:
        raise ConflictError(
            "GOV_BUDGET_CREDIT_DUPLICATE",
            "Ya existe un crédito para esa categoría, partida y fuente",
        )
    credito = GovernmentBudgetCredit(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        created_by=ctx.user_id,
        category_id=str(categoria.id),
        item_id=str(partida.id),
        source_id=str(fuente.id),
        monto=monto,
    )
    db.add(credito)
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "CREDITO_REGISTRADO",
        {
            "categoria": categoria.codigo_completo,
            "partida": partida.codigo,
            "fuente": fuente.codigo,
            "monto": str(monto),
        },
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CREDIT_CREATED",
        {
            "anio": ejercicio.anio,
            "categoria": categoria.codigo_completo,
            "fuente": fuente.codigo,
            "monto": str(monto),
            "partida": partida.codigo,
        },
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def modificar_credito(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    credito_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    credito = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.id == credito_id,
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if credito is None:
        raise NotFoundError("GOV_BUDGET_CREDIT_NOT_FOUND", "El crédito no existe en este ejercicio")
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(GovernmentBudgetCategory.id == credito.category_id)
    ).scalar_one()
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(GovernmentBudgetClassifierItem.id == credito.item_id)
    ).scalar_one()
    fuente = db.execute(
        select(GovernmentBudgetFundingSource).where(GovernmentBudgetFundingSource.id == credito.source_id)
    ).scalar_one()
    monto_anterior = credito.monto
    monto = _monto_valido(cuerpo.get("monto"))
    credito.monto = monto
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "CREDITO_MODIFICADO",
        {
            "categoria": categoria.codigo_completo,
            "partida": partida.codigo,
            "fuente": fuente.codigo,
            "monto_anterior": str(monto_anterior),
            "monto": str(monto),
        },
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CREDIT_UPDATED",
        {
            "anio": ejercicio.anio,
            "categoria": categoria.codigo_completo,
            "fuente": fuente.codigo,
            "monto": str(monto),
            "partida": partida.codigo,
        },
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def eliminar_credito(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    credito_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    credito = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.id == credito_id,
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if credito is None:
        raise NotFoundError("GOV_BUDGET_CREDIT_NOT_FOUND", "El crédito no existe en este ejercicio")
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(GovernmentBudgetCategory.id == credito.category_id)
    ).scalar_one()
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(GovernmentBudgetClassifierItem.id == credito.item_id)
    ).scalar_one()
    fuente = db.execute(
        select(GovernmentBudgetFundingSource).where(GovernmentBudgetFundingSource.id == credito.source_id)
    ).scalar_one()
    monto = credito.monto
    db.delete(credito)
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "CREDITO_ELIMINADO",
        {
            "categoria": categoria.codigo_completo,
            "partida": partida.codigo,
            "fuente": fuente.codigo,
            "monto": str(monto),
        },
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CREDIT_DELETED",
        {
            "anio": ejercicio.anio,
            "categoria": categoria.codigo_completo,
            "fuente": fuente.codigo,
            "monto": str(monto),
            "partida": partida.codigo,
        },
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def registrar_existencias(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    monto = _monto_valido(cuerpo.get("monto"))
    fecha_corte = cuerpo["fecha_corte"]
    if not isinstance(fecha_corte, date):
        fecha_corte = date.fromisoformat(str(fecha_corte))
    limite_inferior = date(ejercicio.anio - 1, 1, 1)
    if fecha_corte < limite_inferior or fecha_corte > hoy_de_negocio():
        raise _invalida("La fecha de corte debe estar entre el 1 de enero del año anterior y hoy", "fecha_corte")
    documento, sha = _documento_valido(db, ctx, ejercicio, cuerpo["documento_id"], "documento_id")
    existencias = db.execute(
        select(GovernmentBudgetTreasuryHoldings).where(
            GovernmentBudgetTreasuryHoldings.year_id == ejercicio.id,
            GovernmentBudgetTreasuryHoldings.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if existencias is None:
        existencias = GovernmentBudgetTreasuryHoldings(
            year_id=str(ejercicio.id),
            company_id=ctx.company_id,
            created_by=ctx.user_id,
            monto=monto,
            fecha_corte=fecha_corte,
            documento_id=str(documento.id),
            documento_sha256=sha,
        )
        db.add(existencias)
    else:
        existencias.monto = monto
        existencias.fecha_corte = fecha_corte
        existencias.documento_id = str(documento.id)
        existencias.documento_sha256 = sha
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "EXISTENCIAS_REGISTRADAS",
        {"monto": str(monto), "fecha_corte": fecha_corte.isoformat()},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_TREASURY_HOLDINGS_REGISTERED",
        {"anio": ejercicio.anio, "fecha_corte": fecha_corte.isoformat(), "monto": str(monto)},
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def eliminar_existencias(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    existencias = db.execute(
        select(GovernmentBudgetTreasuryHoldings).where(
            GovernmentBudgetTreasuryHoldings.year_id == ejercicio.id,
            GovernmentBudgetTreasuryHoldings.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    if existencias is None:
        raise NotFoundError("GOV_BUDGET_TREASURY_HOLDINGS_NOT_FOUND", "No hay existencias del Tesoro declaradas")
    monto = existencias.monto
    db.delete(existencias)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "EXISTENCIAS_ELIMINADAS", {"monto": str(monto)})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_TREASURY_HOLDINGS_REMOVED",
        {"anio": ejercicio.anio},
    )
    db.flush()
    return _vista(db, ctx, ejercicio)


def _totales_para_verificar(db: Session, ejercicio: GovernmentBudgetYear) -> dict[str, Decimal]:
    ingresos = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    existencias = db.execute(
        select(GovernmentBudgetTreasuryHoldings).where(
            GovernmentBudgetTreasuryHoldings.year_id == ejercicio.id,
            GovernmentBudgetTreasuryHoldings.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    total_ingresos = sum((ingreso.monto for ingreso in ingresos), Decimal("0.00"))
    total_creditos = sum((credito.monto for credito in creditos), Decimal("0.00"))
    total_existencias = existencias.monto if existencias is not None else Decimal("0.00")
    holgura = total_existencias / 2
    disponible = total_ingresos + holgura
    return {
        "ingresos": total_ingresos,
        "creditos": total_creditos,
        "existencias": total_existencias,
        "holgura_tesoro": holgura,
        "disponible": disponible,
        "exceso": total_creditos - disponible,
    }


def verificar_para_fijar(db: Session, ejercicio: GovernmentBudgetYear) -> None:
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    partidas = _partidas_del_clasificador(db, clasificador)
    ids_con_hijos = _ids_con_hijos(partidas)

    categorias = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    categoria_por_id = {str(categoria.id): categoria for categoria in categorias}
    ids_categorias_con_hijas = {str(categoria.parent_id) for categoria in categorias if categoria.parent_id is not None}

    no_imputables: list[str] = []
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    fuentes = {
        str(fuente.id): fuente
        for fuente in db.execute(
            select(GovernmentBudgetFundingSource).where(
                GovernmentBudgetFundingSource.year_id == ejercicio.id,
                GovernmentBudgetFundingSource.company_id == ejercicio.company_id,
            )
        ).scalars().all()
    }
    for credito in creditos:
        categoria = categoria_por_id.get(str(credito.category_id))
        partida = partidas.get(str(credito.item_id))
        if categoria is not None and partida is not None:
            if str(credito.category_id) in ids_categorias_con_hijas or str(credito.item_id) in ids_con_hijos:
                fuente = fuentes.get(str(credito.source_id))
                codigo_fuente = fuente.codigo if fuente is not None else "??"
                no_imputables.append(
                    f"Crédito {categoria.codigo_completo} · {partida.codigo} · {codigo_fuente}"
                )
    ingresos = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    for ingreso in ingresos:
        partida = partidas.get(str(ingreso.item_id))
        if partida is not None and str(ingreso.item_id) in ids_con_hijos:
            no_imputables.append(f"Ingreso {partida.codigo}")

    if no_imputables:
        raise KontrolError(
            code="GOV_BUDGET_NOT_IMPUTABLE",
            message="Hay créditos o ingresos imputados a niveles que ya tienen dependientes",
            details={"no_imputables": no_imputables},
            status_code=422,
        )

    totales = _totales_para_verificar(db, ejercicio)
    if not (2 * totales["creditos"] <= 2 * totales["ingresos"] + totales["existencias"]):
        raise KontrolError(
            code="GOV_BUDGET_UNBALANCED",
            message="Los créditos superan los ingresos estimados más la mitad de las existencias del Tesoro (LOPPM art. 240)",
            details={clave: str(valor) for clave, valor in totales.items()},
            status_code=422,
        )


def fotografia_presupuesto(db: Session, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    ingresos = db.execute(
        select(GovernmentBudgetIncomeEstimate).where(
            GovernmentBudgetIncomeEstimate.year_id == ejercicio.id,
            GovernmentBudgetIncomeEstimate.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
        )
    ).scalars().all()
    existencias = db.execute(
        select(GovernmentBudgetTreasuryHoldings).where(
            GovernmentBudgetTreasuryHoldings.year_id == ejercicio.id,
            GovernmentBudgetTreasuryHoldings.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()

    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    partidas = _partidas_del_clasificador(db, clasificador)
    categorias = {
        str(categoria.id): categoria
        for categoria in db.execute(
            select(GovernmentBudgetCategory).where(
                GovernmentBudgetCategory.year_id == ejercicio.id,
                GovernmentBudgetCategory.company_id == ejercicio.company_id,
            )
        ).scalars().all()
    }
    fuentes = {
        str(fuente.id): fuente
        for fuente in db.execute(
            select(GovernmentBudgetFundingSource).where(
                GovernmentBudgetFundingSource.year_id == ejercicio.id,
                GovernmentBudgetFundingSource.company_id == ejercicio.company_id,
            )
        ).scalars().all()
    }
    unidades = {
        str(unidad.id): unidad
        for unidad in db.execute(select(GovernmentUnit).where(GovernmentUnit.company_id == ejercicio.company_id)).scalars().all()
    }

    ingresos_foto = []
    for ingreso in ingresos:
        partida = partidas.get(str(ingreso.item_id))
        if partida is not None:
            ingresos_foto.append({"partida": partida.codigo, "monto": str(ingreso.monto)})
    ingresos_foto.sort(key=lambda item: item["partida"])

    creditos_foto = []
    for credito in creditos:
        partida = partidas.get(str(credito.item_id))
        categoria = categorias.get(str(credito.category_id))
        fuente = fuentes.get(str(credito.source_id))
        if partida is not None and categoria is not None and fuente is not None:
            unidad = None
            if categoria.unit_id:
                unidad_obj = unidades.get(categoria.unit_id)
                if unidad_obj is not None:
                    unidad = unidad_obj.code
            creditos_foto.append(
                {
                    "categoria": categoria.codigo_completo,
                    "partida": partida.codigo,
                    "fuente": fuente.codigo,
                    "unidad": unidad,
                    "monto": str(credito.monto),
                }
            )
    creditos_foto.sort(key=lambda item: (item["categoria"], item["partida"], item["fuente"]))

    total_ingresos = sum((ingreso.monto for ingreso in ingresos), Decimal("0.00"))
    total_creditos = sum((credito.monto for credito in creditos), Decimal("0.00"))
    total_existencias = existencias.monto if existencias is not None else Decimal("0.00")
    disponible = total_ingresos + total_existencias / 2

    existencias_foto = None
    if existencias is not None:
        existencias_foto = {
            "monto": str(existencias.monto),
            "fecha_corte": existencias.fecha_corte.isoformat(),
            "documento_sha256": existencias.documento_sha256,
        }

    return {
        "ingresos": ingresos_foto,
        "creditos": creditos_foto,
        "existencias_tesoro": existencias_foto,
        "totales": {
            "ingresos": str(total_ingresos),
            "creditos": str(total_creditos),
            "existencias": str(total_existencias),
            "disponible": str(disponible),
        },
    }


def en_uso_categoria(db: Session, categoria_id: str) -> bool:
    return db.execute(
        select(GovernmentBudgetCredit.id).where(GovernmentBudgetCredit.category_id == categoria_id).limit(1)
    ).first() is not None


def en_uso_partida(db: Session, partida_id: str) -> bool:
    if db.execute(
        select(GovernmentBudgetCredit.id).where(GovernmentBudgetCredit.item_id == partida_id).limit(1)
    ).first() is not None:
        return True
    return db.execute(
        select(GovernmentBudgetIncomeEstimate.id).where(GovernmentBudgetIncomeEstimate.item_id == partida_id).limit(1)
    ).first() is not None


def en_uso_fuente(db: Session, fuente_id: str) -> bool:
    return db.execute(
        select(GovernmentBudgetCredit.id).where(GovernmentBudgetCredit.source_id == fuente_id).limit(1)
    ).first() is not None


def verificar_fuente(db: Session, ejercicio: GovernmentBudgetYear, fuente_id: str) -> None:
    permitidas = _partidas_permitidas_de_fuente(db, ejercicio, fuente_id)
    if permitidas is None:
        return
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    partidas = _partidas_del_clasificador(db, clasificador)
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ejercicio.company_id,
            GovernmentBudgetCredit.source_id == fuente_id,
        )
    ).scalars().all()
    fuera = [
        partidas[str(credito.item_id)].codigo
        for credito in creditos
        if str(credito.item_id) in partidas
        and not _partida_permitida(db, ejercicio, str(credito.item_id), permitidas)
    ]
    if fuera:
        lista = ", ".join(sorted(fuera))
        raise ConflictError(
            "GOV_BUDGET_FUNDING_RESTRICTION_CONFLICT",
            f"La restricción deja fuera créditos ya registrados: {lista}",
            details={"creditos": sorted(fuera)},
        )
