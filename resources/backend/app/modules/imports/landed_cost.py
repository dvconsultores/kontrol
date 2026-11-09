"""Clasificación, reparto, vista previa y aplicación de gastos de importación."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from fractions import Fraction
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.imports import service
from app.modules.imports.models import (
    ImportCostAllocation,
    ImportCostApplication,
    ImportExpense,
    ImportFile,
)
from app.modules.inventory.models import CostLayer, InventoryMovement
from app.modules.inventory.service import effective_unit_cost
from app.modules.master_data.models import CatalogItem
from app.modules.master_data.party_service import bump
from app.modules.master_data.uom import base_unit_of
from app.modules.purchasing.models import GoodsReceipt
from app.modules.treasury.models import TreasuryRateSnapshot
from app.modules.treasury.service import capture_rate_snapshot, resolucion_de_tasa

CAPITALIZABLE = "CAPITALIZABLE"
NOT_CAPITALIZABLE = "NOT_CAPITALIZABLE"
UNDETERMINED = "UNDETERMINED"
CAPITALIZATIONS = (CAPITALIZABLE, NOT_CAPITALIZABLE, UNDETERMINED)

VALUE = "VALUE"
QUANTITY = "QUANTITY"
MANUAL = "MANUAL"
CRITERIA = (VALUE, QUANTITY, MANUAL)

TWO_PLACES = Decimal("0.01")
SIX_PLACES = Decimal("0.000001")


@dataclass(frozen=True)
class AllocationResult:
    layers: list[CostLayer]
    valuation_amount: Decimal
    valuation_currency: str
    lines: list[dict[str, Any]]
    blocks: list[dict[str, Any]]
    can_apply: bool
    token: str
    criterion_source: str
    response: dict[str, Any]


def _dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        return Decimal(value)
    return Decimal(str(value))


def distribuir(
    importe: Decimal,
    bases: list[tuple[str, Decimal]],
) -> list[tuple[str, Decimal, Decimal, Decimal, Decimal]]:
    """Reparte importe entre claves por fracción mayor, en céntimos exactos.

    Devuelve (clave, exacto, redondeado, ajuste, asignado) en el orden dado.
    """
    importe = _dec(importe)
    total_cents = int((importe / TWO_PLACES).to_integral_value())
    if not bases:
        return []

    entradas = [(clave, _dec(base)) for clave, base in bases]
    total = sum((base for _, base in entradas), Decimal("0"))
    if total <= 0:
        raise KontrolError(
            code="IMPORT_COST_BASE_ZERO",
            message="La base de reparto es cero.",
            status_code=422,
        )

    fracciones: list[tuple[str, Fraction, Decimal, int]] = []
    for clave, base in entradas:
        cociente = Fraction(total_cents) * Fraction(base) / Fraction(total)
        truncado = cociente.numerator // cociente.denominator
        fraccion_descartada = cociente - truncado
        fracciones.append((clave, fraccion_descartada, Decimal(cociente.numerator) / Decimal(cociente.denominator), truncado))

    suma_truncados = sum(f[3] for f in fracciones)
    residuo_cents = total_cents - suma_truncados

    orden = sorted(enumerate(fracciones), key=lambda t: (-t[1][1], t[0]))
    ajustes = [0] * len(fracciones)
    idx = 0
    while residuo_cents > 0:
        ajustes[orden[idx][0]] += 1
        idx += 1
        residuo_cents -= 1

    resultado: list[tuple[str, Decimal, Decimal, Decimal, Decimal]] = []
    for pos, (clave, _frac, exacto, truncado) in enumerate(fracciones):
        ajuste_cents = ajustes[pos]
        ajuste = Decimal(ajuste_cents) * TWO_PLACES
        redondeado = Decimal(truncado) * TWO_PLACES
        asignado = redondeado + ajuste
        resultado.append((clave, exacto / HUNDRED_CENTS, redondeado, ajuste, asignado))
    return resultado


HUNDRED_CENTS = Decimal("100")


def _layers_of_file(
    db: Session, *, file: ImportFile, lock: bool = False
) -> list[CostLayer]:
    if not file.order_id:
        return []
    receipts = db.scalars(
        select(GoodsReceipt).where(
            GoodsReceipt.order_id == file.order_id,
            GoodsReceipt.company_id == file.company_id,
        )
    ).all()
    receipt_refs = [f"RECEIPT:{receipt.id}" for receipt in receipts]
    if not receipt_refs:
        return []
    query = (
        select(CostLayer)
        .where(CostLayer.company_id == file.company_id)
        .where(CostLayer.receipt_ref.in_(receipt_refs))
        .order_by(CostLayer.created_at, CostLayer.id)
    )
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query))


def _layer_currency_validation(layers: list[CostLayer]) -> str:
    currencies = {layer.currency for layer in layers}
    if len(currencies) > 1:
        raise ConflictError(
            code="IMPORT_COST_LAYER_CURRENCY_MIXED",
            message="Las capas del expediente usan monedas distintas.",
        )
    return next(iter(currencies))


def _valuation_amount(
    db: Session,
    *,
    expense: ImportExpense,
    layer_currency: str,
) -> tuple[Decimal, Decimal, str | None, str]:
    if expense.currency == layer_currency:
        return expense.amount, Decimal("1"), "IDENTITY", expense.rate_snapshot_id
    if expense.functional_currency == layer_currency:
        snapshot = db.get(TreasuryRateSnapshot, expense.rate_snapshot_id)
        if snapshot is None:
            raise ConflictError(
                code="RATE_NOT_AVAILABLE",
                message="No hay tasa disponible para valorar el gasto.",
            )
        return expense.functional_amount, snapshot.rate, snapshot.rate_source, str(snapshot.id)

    tasa = resolucion_de_tasa(
        db,
        expense.company_id,
        expense.currency,
        layer_currency,
        expense.expense_date,
    )
    if tasa is None:
        raise ConflictError(
            code="RATE_NOT_AVAILABLE",
            message="No hay tasa disponible para valorar el gasto.",
        )

    amount = (expense.amount * tasa.rate).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
    return amount, tasa.rate, "RESOLVED", expense.rate_snapshot_id


def _layer_base_value(layer: CostLayer) -> Decimal:
    return _dec(layer.quantity_in) * _dec(layer.unit_cost)


def _layer_base_quantity(db: Session, *, layer: CostLayer) -> Decimal:
    movement = db.scalar(
        select(InventoryMovement)
        .where(InventoryMovement.company_id == layer.company_id)
        .where(InventoryMovement.product_id == layer.product_id)
        .where(InventoryMovement.warehouse_id == layer.warehouse_id)
        .where(InventoryMovement.document_ref == layer.receipt_ref)
        .where(InventoryMovement.quantity == layer.quantity_in)
        .order_by(InventoryMovement.created_at)
        .limit(1)
    )
    if movement is None:
        raise ConflictError(
            code="IMPORT_COST_QUANTITY_BASE_UNKNOWN",
            message="No se encontró la cantidad base de la capa.",
        )
    if movement.base_quantity is None or movement.quantity is None or _dec(movement.quantity) == 0:
        raise ConflictError(
            code="IMPORT_COST_QUANTITY_BASE_UNKNOWN",
            message="No se encontró la cantidad base de la capa.",
        )
    return _dec(layer.quantity_in) * _dec(movement.base_quantity) / _dec(movement.quantity)


def _is_layer_consumed(layer: CostLayer) -> bool:
    return _dec(layer.quantity_remaining) < _dec(layer.quantity_in)


def _participacion(base: Decimal, total_base: Decimal) -> Decimal:
    participacion = Fraction(base) / Fraction(total_base)
    return Decimal(participacion.numerator) / Decimal(participacion.denominator)


def classify_expense(
    db: Session,
    *,
    file: ImportFile,
    expense_id: str,
    version: int,
    capitalization: str,
    actor_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    expense = db.scalar(
        select(ImportExpense).where(
            ImportExpense.id == expense_id,
            ImportExpense.file_id == file.id,
            ImportExpense.company_id == file.company_id,
        )
    )
    if expense is None:
        raise NotFoundError(
            code="IMPORT_EXPENSE_NOT_FOUND",
            message="Gasto de importación no encontrado.",
        )
    if expense.version != version:
        raise ConflictError(
            code="IMPORT_EXPENSE_STALE",
            message="La versión del gasto no coincide.",
        )
    if expense.status != "REGISTERED":
        raise ConflictError(
            code="IMPORT_EXPENSE_INVALID_STATE",
            message="El gasto no se puede clasificar en su estado actual.",
        )
    if capitalization not in CAPITALIZATIONS:
        raise KontrolError(
            code="IMPORT_EXPENSE_CAPITALIZATION_INVALID",
            message="La clasificación del gasto no es válida.",
            status_code=422,
        )
    applied = db.scalar(
        select(ImportCostApplication.id).where(
            ImportCostApplication.expense_id == expense.id,
            ImportCostApplication.status == "APPLIED",
        )
    )
    if applied is not None:
        raise ConflictError(
            code="IMPORT_EXPENSE_APPLIED",
            message="El gasto tiene una aplicación vigente y no se puede clasificar.",
        )

    before = {
        "capitalization": expense.capitalization,
    }
    expense.capitalization = capitalization
    after = {
        "capitalization": expense.capitalization,
    }

    service._audit(
        db,
        action="IMPORT_EXPENSE_CLASSIFIED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    bump(expense)
    bump(file)

    return {
        "id": str(expense.id),
        "capitalization": expense.capitalization,
        "version": expense.version,
    }


def compute_allocation(
    db: Session,
    *,
    file: ImportFile,
    expense: ImportExpense,
    criterion: str,
    manual_amounts: dict[str, str] | None,
    lock: bool = False,
) -> AllocationResult:
    layers = _layers_of_file(db, file=file, lock=lock)
    if not layers:
        raise ConflictError(
            code="IMPORT_COST_NO_LAYERS",
            message="El expediente no tiene capas de costo.",
        )

    layer_currency = _layer_currency_validation(layers)

    valuation_amount, rate_value, rate_source, rate_snapshot_id = _valuation_amount(
        db, expense=expense, layer_currency=layer_currency
    )
    rate_date = expense.expense_date.isoformat()
    rate_identity = rate_source == "SAME_CURRENCY_IDENTITY"

    blocks: list[dict[str, Any]] = []
    can_apply = True

    if expense.capitalization != CAPITALIZABLE:
        blocks.append(
            {
                "code": "IMPORT_COST_NOT_CAPITALIZABLE",
                "message": "El gasto no está clasificado como capitalizable.",
            }
        )
        can_apply = False

    consumed_layers = [layer for layer in layers if _is_layer_consumed(layer)]
    if consumed_layers:
        blocks.append(
            {
                "code": "IMPORT_COST_LAYER_CONSUMED",
                "message": "El inventario ya se consumió y el costo no puede aplicarse de forma retroactiva.",
            }
        )
        can_apply = False

    applied = db.scalar(
        select(ImportCostApplication.id).where(
            ImportCostApplication.expense_id == expense.id,
            ImportCostApplication.status == "APPLIED",
        )
    )
    if applied is not None:
        blocks.append(
            {
                "code": "IMPORT_COST_ALREADY_APPLIED",
                "message": "El gasto ya tiene una aplicación vigente.",
            }
        )
        can_apply = False

    criterio_source_label = {
        VALUE: "COST_LAYER_RECEIVED_VALUE",
        QUANTITY: "COST_LAYER_BASE_QUANTITY",
        MANUAL: "USER_MANUAL_AMOUNTS",
    }[criterion]
    base_label = {
        VALUE: "Valor recibido",
        QUANTITY: "Cantidad base",
        MANUAL: "Importe manual",
    }[criterion]

    if criterion == VALUE:
        bases = [(str(layer.id), _layer_base_value(layer)) for layer in layers]
    elif criterion == QUANTITY:
        bases = []
        uoms: set[str] = set()
        for layer in layers:
            product = db.get(CatalogItem, layer.product_id)
            if product is None:
                raise ConflictError(
                    code="IMPORT_COST_QUANTITY_BASE_UNKNOWN",
                    message="No se encontró el producto de la capa.",
                )
            uom = base_unit_of(db, str(product.id))
            if uom is None:
                raise ConflictError(
                    code="IMPORT_COST_QUANTITY_BASE_UNKNOWN",
                    message="No se encontró la unidad base del producto.",
                )
            uoms.add(str(uom.id))
            bases.append((str(layer.id), _layer_base_quantity(db, layer=layer)))
        if len(uoms) > 1:
            raise ConflictError(
                code="IMPORT_COST_QUANTITY_NOT_COMPARABLE",
                message="Los productos usan unidades base distintas.",
            )
    elif criterion == MANUAL:
        manual = manual_amounts or {}
        bases = []
        total_manual = Decimal("0")
        for layer in layers:
            raw = manual.get(str(layer.id))
            if raw is None:
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_LAYER_INVALID",
                    message="Hay una capa sin importe manual.",
                    status_code=422,
                )
            try:
                amount = Decimal(str(raw))
            except (InvalidOperation, ValueError):
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_AMOUNT_INVALID",
                    message="El importe manual no es válido.",
                    status_code=422,
                ) from None
            if not amount.is_finite():
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_AMOUNT_INVALID",
                    message="El importe manual no puede ser NaN o infinito.",
                    status_code=422,
                )
            if amount < 0:
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_AMOUNT_INVALID",
                    message="El importe manual no puede ser negativo.",
                    status_code=422,
                )
            if amount != amount.quantize(TWO_PLACES):
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_AMOUNT_INVALID",
                    message="El importe manual no puede tener más de dos decimales.",
                    status_code=422,
                )
            bases.append((str(layer.id), amount))
            total_manual += amount
        for layer_id in manual:
            if layer_id not in {str(layer.id) for layer in layers}:
                raise KontrolError(
                    code="IMPORT_COST_MANUAL_LAYER_INVALID",
                    message="Una capa manual no pertenece al expediente.",
                    status_code=422,
                )
        if total_manual != valuation_amount:
            difference = valuation_amount - total_manual
            blocks.append(
                {
                    "code": "IMPORT_COST_MANUAL_UNBALANCED",
                    "message": "Los importes manuales no suman el importe de valoración.",
                    "difference": format(difference, "f"),
                }
            )
            can_apply = False
    else:  # pragma: no cover - ya validado
        raise KontrolError(code="IMPORT_COST_CRITERION_INVALID", message="Criterio inválido.", status_code=422)

    total_base = sum((base for _, base in bases), Decimal("0"))
    if total_base <= 0 and not (criterion == MANUAL and not can_apply):
        raise KontrolError(
            code="IMPORT_COST_BASE_ZERO",
            message="La base de reparto es cero.",
            status_code=422,
        )

    raw_lines: list[dict[str, Any]] = []
    distributed_total = Decimal("0")
    base_by_id = dict(bases)

    if criterion == MANUAL:
        reparto_by_id: dict[str, tuple[Decimal, Decimal, Decimal, Decimal]] = {}
        for layer_id, amount in bases:
            reparto_by_id[layer_id] = (amount, amount, Decimal("0"), amount)
    else:
        repartos = distribuir(valuation_amount, bases)
        reparto_by_id = {clave: (exacto, redondeado, ajuste, asignado) for clave, exacto, redondeado, ajuste, asignado in repartos}

    for layer in layers:
        layer_id = str(layer.id)
        if layer_id not in reparto_by_id:
            exacto = Decimal("0")
            asignado = Decimal("0")
            redondeado = Decimal("0")
            ajuste = Decimal("0")
        else:
            exacto, redondeado, ajuste, asignado = reparto_by_id[layer_id]
        base = base_by_id[layer_id]
        participation = _participacion(base, total_base) if total_base > 0 else Decimal("0")

        before = _dec(layer.landed_cost)
        after = before + asignado
        before_unit = effective_unit_cost(layer, landed_cost=before)
        after_unit = effective_unit_cost(layer, landed_cost=after)

        raw_lines.append(
            {
                "layer": layer_id,
                "base": base,
                "participation": participation,
                "exact": exacto,
                "rounded": redondeado,
                "adjustment": ajuste,
                "allocated": asignado,
                "before_landed": before,
                "after_landed": after,
                "before_unit": before_unit,
                "after_unit": after_unit,
            }
        )
        distributed_total += asignado

    difference = valuation_amount - distributed_total

    snapshot = db.get(TreasuryRateSnapshot, expense.rate_snapshot_id)
    origin_rate_value = snapshot.rate if snapshot else Decimal("0")

    token = _preview_token(
        expense=expense,
        layers=layers,
        criterion=criterion,
        manual_amounts=manual_amounts,
        valuation_amount=valuation_amount,
    )

    lineas: list[dict[str, Any]] = []
    receipts_by_ref: dict[str, GoodsReceipt] = {}
    if file.order_id:
        receipts = db.scalars(
            select(GoodsReceipt).where(
                GoodsReceipt.order_id == file.order_id,
                GoodsReceipt.company_id == file.company_id,
            )
        ).all()
        receipts_by_ref = {f"RECEIPT:{receipt.id}": receipt for receipt in receipts}

    for line in raw_lines:
        layer_id = str(line["layer"])
        layer = next(layer for layer in layers if str(layer.id) == layer_id)
        product = db.get(CatalogItem, layer.product_id)
        product_code = product.code if product else None
        product_name = product.name if product else None
        receipt = receipts_by_ref.get(layer.receipt_ref or "")
        receipt_code = receipt.code if receipt else None
        exacto = line["exact"]
        asignado = line["allocated"]
        redondeado = line["rounded"]
        ajuste = line["adjustment"]
        base = line["base"]
        participation = line["participation"]
        before = line["before_landed"]
        after = line["after_landed"]
        before_unit = line["before_unit"]
        after_unit = line["after_unit"]

        lineas.append(
            {
                "layer_id": layer_id,
                "product_code": product_code,
                "product_name": product_name,
                "receipt_code": receipt_code,
                "base": format(base.quantize(SIX_PLACES), "f"),
                "base_label": base_label,
                "participation": format(participation.quantize(SIX_PLACES), "f"),
                "exact_share": format(exacto.quantize(SIX_PLACES), "f"),
                "allocated_amount": format(asignado.quantize(TWO_PLACES), "f"),
                "residual_adjustment": format(ajuste.quantize(TWO_PLACES), "f"),
                "unit_cost": format(_dec(layer.unit_cost).quantize(SIX_PLACES), "f"),
                "before_landed_cost": format(before.quantize(TWO_PLACES), "f"),
                "before_unit_cost": format(before_unit.quantize(SIX_PLACES), "f"),
                "after_landed_cost": format(after.quantize(TWO_PLACES), "f"),
                "after_unit_cost": format(after_unit.quantize(SIX_PLACES), "f"),
                "consumed": _is_layer_consumed(layer),
            }
        )

    response = {
        "expense": {
            "id": str(expense.id),
            "concept": expense.concept,
            "reference": expense.reference,
            "capitalization": expense.capitalization,
            "version": expense.version,
            "currency": expense.currency,
            "amount": format(expense.amount, "f"),
            "rate_value": format(origin_rate_value, "f").rstrip("0").rstrip("."),
            "rate_date": rate_date,
            "rate_identity": rate_identity,
        },
        "criterion": criterion,
        "criterion_source_label": criterio_source_label,
        "valuation_currency": layer_currency,
        "valuation_amount": format(valuation_amount, "f"),
        "distributed_total": format(distributed_total.quantize(TWO_PLACES), "f"),
        "difference": format(difference.quantize(TWO_PLACES), "f"),
        "lines": lineas,
        "can_apply": can_apply,
        "blocks": blocks,
        "preview_token": token,
    }
    return AllocationResult(
        layers=layers,
        valuation_amount=valuation_amount,
        valuation_currency=layer_currency,
        lines=raw_lines,
        blocks=blocks,
        can_apply=can_apply,
        token=token,
        criterion_source=criterio_source_label,
        response=response,
    )


def preview_allocation(
    db: Session,
    *,
    file: ImportFile,
    expense_id: str,
    criterion: str,
    manual_amounts: dict[str, str] | None = None,
) -> dict[str, Any]:
    if criterion not in CRITERIA:
        raise KontrolError(
            code="IMPORT_COST_CRITERION_INVALID",
            message="El criterio de reparto no es válido.",
            status_code=422,
        )

    expense = db.scalar(
        select(ImportExpense).where(
            ImportExpense.id == expense_id,
            ImportExpense.file_id == file.id,
            ImportExpense.company_id == file.company_id,
        )
    )
    if expense is None:
        raise NotFoundError(
            code="IMPORT_EXPENSE_NOT_FOUND",
            message="Gasto de importación no encontrado.",
        )
    if expense.status != "REGISTERED":
        raise ConflictError(
            code="IMPORT_EXPENSE_INVALID_STATE",
            message="El gasto no se puede previsualizar en su estado actual.",
        )

    result = compute_allocation(
        db,
        file=file,
        expense=expense,
        criterion=criterion,
        manual_amounts=manual_amounts,
    )
    return result.response


APPLICATION_BLOCK_PRIORITY = (
    "IMPORT_COST_ALREADY_APPLIED",
    "IMPORT_COST_NOT_CAPITALIZABLE",
    "IMPORT_COST_LAYER_CONSUMED",
    "IMPORT_COST_MANUAL_UNBALANCED",
)


def apply_allocation(
    db: Session,
    *,
    file: ImportFile,
    expense_id: str,
    criterion: str,
    manual_amounts: dict[str, str] | None,
    preview_token: str,
    actor_id: str,
    tenant_id: str,
) -> ImportCostApplication:
    if criterion not in CRITERIA:
        raise KontrolError(
            code="IMPORT_COST_CRITERION_INVALID",
            message="El criterio de reparto no es válido.",
            status_code=422,
        )

    expense = db.scalar(
        select(ImportExpense)
        .where(
            ImportExpense.id == expense_id,
            ImportExpense.file_id == file.id,
            ImportExpense.company_id == file.company_id,
        )
        .with_for_update()
    )
    if expense is None:
        raise NotFoundError(
            code="IMPORT_EXPENSE_NOT_FOUND",
            message="Gasto de importación no encontrado.",
        )
    if expense.status != "REGISTERED":
        raise ConflictError(
            code="IMPORT_EXPENSE_INVALID_STATE",
            message="El gasto no se puede aplicar en su estado actual.",
        )

    result = compute_allocation(
        db,
        file=file,
        expense=expense,
        criterion=criterion,
        manual_amounts=manual_amounts,
        lock=True,
    )

    if result.blocks:
        by_code = {block["code"]: block for block in result.blocks}
        block = next(
            (by_code[code] for code in APPLICATION_BLOCK_PRIORITY if code in by_code),
            result.blocks[0],
        )
        raise ConflictError(code=block["code"], message=block["message"])

    if result.token != preview_token:
        raise ConflictError(
            code="IMPORT_COST_PREVIEW_STALE",
            message="Los datos cambiaron desde la vista previa. Genérela de nuevo.",
        )

    valuation_rate_snapshot_id: str | None = None
    if expense.currency == result.valuation_currency:
        valuation_rate_snapshot_id = None
    elif expense.functional_currency == result.valuation_currency:
        valuation_rate_snapshot_id = expense.rate_snapshot_id
    else:
        snapshot = capture_rate_snapshot(
            db,
            company_id=expense.company_id,
            source_currency=expense.currency,
            target_currency=result.valuation_currency,
            on_date=expense.expense_date,
            actor=actor_id,
        )
        valuation_rate_snapshot_id = str(snapshot.id)

    valuation_snapshot = db.get(TreasuryRateSnapshot, expense.rate_snapshot_id)
    origin_rate_value = valuation_snapshot.rate if valuation_snapshot else Decimal("0")

    application = ImportCostApplication(
        company_id=expense.company_id,
        file_id=file.id,
        expense_id=expense.id,
        criterion=criterion,
        criterion_source=result.criterion_source,
        status="APPLIED",
        origin_currency=expense.currency,
        origin_amount=expense.amount,
        origin_rate_snapshot_id=expense.rate_snapshot_id,
        origin_rate_value=origin_rate_value,
        valuation_currency=result.valuation_currency,
        valuation_amount=result.valuation_amount,
        valuation_rate_snapshot_id=valuation_rate_snapshot_id,
        applied_at=datetime.now(UTC),
        applied_by=actor_id,
        version=1,
        created_by=actor_id,
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            code="IMPORT_COST_ALREADY_APPLIED",
            message="El gasto ya tiene una aplicación vigente.",
        ) from None

    layer_by_id = {str(layer.id): layer for layer in result.layers}
    for line in result.lines:
        layer = layer_by_id[str(line["layer"])]
        db.add(
            ImportCostAllocation(
                company_id=expense.company_id,
                application_id=application.id,
                layer_id=layer.id,
                product_id=layer.product_id,
                allocation_base=line["base"],
                participation=line["participation"],
                exact_share=line["exact"],
                rounded_share=line["rounded"],
                residual_adjustment=line["adjustment"],
                allocated_amount=line["allocated"],
                currency=result.valuation_currency,
                before_landed_cost=line["before_landed"],
                after_landed_cost=line["after_landed"],
                before_unit_cost=line["before_unit"],
                after_unit_cost=line["after_unit"],
                created_by=actor_id,
            )
        )
        layer.landed_cost = _dec(layer.landed_cost) + line["allocated"]

    service._audit(
        db,
        action="IMPORT_COST_APPLIED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "application_id": str(application.id),
            "expense_id": str(expense.id),
            "criterion": criterion,
            "valuation_amount": format(result.valuation_amount, "f"),
            "valuation_currency": result.valuation_currency,
            "lines": len(result.lines),
            "status": "APPLIED",
        },
    )
    bump(expense)
    bump(file)
    return application


def reverse_application(
    db: Session,
    *,
    file: ImportFile,
    application_id: str,
    version: int,
    reason: str,
    actor_id: str,
    tenant_id: str,
) -> ImportCostApplication:
    application = db.scalar(
        select(ImportCostApplication)
        .where(
            ImportCostApplication.id == application_id,
            ImportCostApplication.file_id == file.id,
            ImportCostApplication.company_id == file.company_id,
        )
        .with_for_update()
    )
    if application is None:
        raise NotFoundError(
            code="IMPORT_COST_APPLICATION_NOT_FOUND",
            message="Aplicación de gasto no encontrada.",
        )
    if application.version != version:
        raise ConflictError(
            code="IMPORT_COST_APPLICATION_STALE",
            message="La versión de la aplicación no coincide.",
        )
    if application.status != "APPLIED":
        raise ConflictError(
            code="IMPORT_COST_APPLICATION_INVALID_STATE",
            message="La aplicación no se puede revertir en su estado actual.",
        )
    if not reason or not reason.strip():
        raise KontrolError(
            code="IMPORT_COST_REVERSAL_REASON_REQUIRED",
            message="El motivo de reversión es obligatorio.",
            status_code=422,
        )

    allocations = db.scalars(
        select(ImportCostAllocation)
        .where(ImportCostAllocation.application_id == application.id)
        .with_for_update()
    ).all()
    layers_by_id = {
        str(row.id): row
        for row in db.execute(
            select(CostLayer).where(
                CostLayer.id.in_([row.layer_id for row in allocations]),
                CostLayer.company_id == file.company_id,
            )
        )
        .scalars()
        .all()
    }
    for allocation in allocations:
        layer = layers_by_id[str(allocation.layer_id)]
        if _dec(layer.quantity_remaining) < _dec(layer.quantity_in):
            raise ConflictError(
                code="IMPORT_COST_REVERSAL_BLOCKED",
                message="El inventario ya se consumió y la aplicación no se puede revertir.",
            )
        layer.landed_cost = _dec(layer.landed_cost) - _dec(allocation.allocated_amount)  # type: ignore[assignment]

    application.status = "REVERSED"
    application.reversed_at = datetime.now(UTC)
    application.reversed_by = actor_id
    application.reversal_reason = reason.strip()
    application.version += 1

    service._audit(
        db,
        action="IMPORT_COST_REVERSED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "application_id": str(application.id),
            "status": application.status,
            "version": application.version,
        },
    )
    bump(file)
    return application


def _preview_token(
    *,
    expense: ImportExpense,
    layers: list[CostLayer],
    criterion: str,
    manual_amounts: dict[str, str] | None,
    valuation_amount: Decimal,
) -> str:
    material = [
        str(expense.id),
        str(expense.version),
        str(expense.capitalization),
        format(expense.amount, "f"),
        criterion,
        format(valuation_amount, "f"),
    ]
    for layer in sorted(layers, key=lambda layer: str(layer.id)):
        material.extend(
            [
                str(layer.id),
                format(_dec(layer.quantity_remaining), "f"),
                format(_dec(layer.landed_cost), "f"),
                format(_dec(layer.unit_cost), "f"),
            ]
        )
    if manual_amounts:
        for layer_id in sorted(manual_amounts):
            material.extend([layer_id, manual_amounts[layer_id]])
    return hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()
