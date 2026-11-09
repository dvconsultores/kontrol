from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.imports import service
from app.modules.imports.models import (
    ImportCostAllocation,
    ImportCostApplication,
    ImportExpense,
    ImportFile,
)
from app.modules.inventory.models import CostLayer
from app.modules.inventory.service import effective_unit_cost, layer_value
from app.modules.master_data import party_service
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Warehouse
from app.modules.purchasing.models import GoodsReceipt, SupplierInvoice
from app.modules.treasury.models import Currency, TreasuryRateSnapshot
from app.modules.treasury.rates import moneda_funcional, moneda_por_codigo
from app.modules.treasury.service import capture_rate_snapshot

ADMITTED_FILE_STATUSES = ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED")
ADMITTED_INVOICE_STATUSES = ("VALIDATED", "MATCHED", "EXCEPTION", "APPROVED", "POSTED", "PARTIALLY_PAID", "PAID")
EXPENSE_KINDS = ("DIRECT_IMPORT_EXPENSE", "LINKED_SUPPLIER_INVOICE")


def _money(value: Decimal | None) -> str:
    if value is None:
        return "0.00"
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN), "f")


def _dec(value: Any) -> Decimal:
    """Coerción a `Decimal` en la frontera del servicio.

    Las columnas monetarias están anotadas `float` sobre `NUMERIC`; en
    ejecución SQLAlchemy devuelve `Decimal`. Forzamos `Decimal` sin tocar
    los modelos para que la aritmética sea exacta y mypy quede conforme.
    """
    if value is None:
        return Decimal(0)
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _require_file_state(file: ImportFile) -> None:
    if file.status not in ADMITTED_FILE_STATUSES:
        raise ConflictError(
            code="IMPORT_INVALID_STATE",
            message="El expediente no admite gastos en su estado actual.",
        )


def _party_for_file(db: Session, file: ImportFile, party_id: str) -> Party:
    party = db.scalar(
        select(Party).where(
            Party.id == party_id,
            Party.company_id == file.company_id,
        )
    )
    if party is None:
        raise NotFoundError(
            code="IMPORT_EXPENSE_PARTY_NOT_FOUND",
            message="Tercero no encontrado en la empresa del expediente.",
        )
    return party


def _invoice_for_expense(db: Session, file: ImportFile, invoice_id: str) -> SupplierInvoice:
    invoice = db.scalar(
        select(SupplierInvoice)
        .where(
            SupplierInvoice.id == invoice_id,
            SupplierInvoice.company_id == file.company_id,
        )
        .with_for_update()
    )
    if invoice is None:
        raise NotFoundError(
            code="IMPORT_EXPENSE_INVOICE_NOT_FOUND",
            message="Factura de proveedor no encontrada.",
        )
    if invoice.status not in ADMITTED_INVOICE_STATUSES:
        raise ConflictError(
            code="IMPORT_EXPENSE_INVOICE_INVALID_STATE",
            message="La factura no está en un estado que admita gastos vinculados.",
        )
    return invoice


def _assigned_to_invoice(db: Session, company_id: str, invoice_id: str) -> Decimal:
    rows = db.scalars(
        select(ImportExpense.amount).where(
            ImportExpense.company_id == company_id,
            ImportExpense.supplier_invoice_id == invoice_id,
            ImportExpense.status == "REGISTERED",
        )
    ).all()
    return sum(rows, Decimal("0"))


def register_expense(
    db: Session,
    *,
    file: ImportFile,
    kind: str,
    concept: str,
    expense_date: date | None,
    amount: Decimal,
    currency: str | None,
    reference: str | None,
    supplier_id: str | None,
    supplier_invoice_id: str | None,
    import_document_id: str | None,
    actor_id: str,
    tenant_id: str,
) -> ImportExpense:
    _require_file_state(file)
    if kind not in EXPENSE_KINDS:
        raise KontrolError(
            code="IMPORT_EXPENSE_KIND_INVALID",
            message="Tipo de gasto de importación inválido.",
            status_code=422,
        )
    if not concept or not concept.strip():
        raise KontrolError(
            code="IMPORT_EXPENSE_CONCEPT_REQUIRED",
            message="El concepto del gasto es obligatorio.",
            status_code=422,
        )

    if kind == "DIRECT_IMPORT_EXPENSE":
        if supplier_invoice_id is not None:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="Un gasto directo no admite factura vinculada.",
                status_code=422,
                details={"field": "supplier_invoice_id"},
            )
        if not supplier_id:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="El tercero es obligatorio.",
                status_code=422,
                details={"field": "supplier_id"},
            )
        if not reference or not reference.strip():
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La referencia es obligatoria.",
                status_code=422,
                details={"field": "reference"},
            )
        if not currency:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La moneda es obligatoria.",
                status_code=422,
                details={"field": "currency"},
            )
        if expense_date is None:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La fecha del gasto es obligatoria.",
                status_code=422,
                details={"field": "expense_date"},
            )
        expense_party = _party_for_file(db, file, str(supplier_id))
        invoice_id_for_expense: str | None = None
        expense_currency = currency
        expense_reference = reference.strip()
        expense_supplier_id = str(expense_party.id)
    else:
        if not supplier_invoice_id:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La factura vinculada es obligatoria.",
                status_code=422,
                details={"field": "supplier_invoice_id"},
            )
        invoice = _invoice_for_expense(db, file, str(supplier_invoice_id))
        if invoice.issue_date is None and expense_date is None:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La fecha del gasto es obligatoria.",
                status_code=422,
                details={"field": "expense_date"},
            )
        if currency and currency != invoice.currency:
            raise KontrolError(
                code="IMPORT_EXPENSE_CURRENCY_MISMATCH",
                message="La moneda no coincide con la factura vinculada.",
                status_code=422,
            )
        invoice_id_for_expense = str(invoice.id)
        expense_currency = invoice.currency
        expense_reference = invoice.invoice_number
        expense_supplier_id = invoice.supplier_id
        expense_party = _party_for_file(db, file, expense_supplier_id)
        assigned = _assigned_to_invoice(db, file.company_id, invoice_id_for_expense)
        if assigned + amount > _dec(invoice.total):
            available = _dec(invoice.total) - assigned
            raise ConflictError(
                code="IMPORT_EXPENSE_EXCEEDS_INVOICE",
                message="El gasto excede el disponible de la factura.",
                details={"available": _money(available)},
            )

    if expense_date is None:
        invoice_linked = db.scalar(
            select(SupplierInvoice).where(SupplierInvoice.id == invoice_id_for_expense)
        )
        if invoice_linked is not None and invoice_linked.issue_date is not None:
            expense_date = invoice_linked.issue_date
        else:
            raise KontrolError(
                code="IMPORT_EXPENSE_FIELD_REQUIRED",
                message="La fecha del gasto es obligatoria.",
                status_code=422,
                details={"field": "expense_date"},
            )

    functional_currency = moneda_funcional(db, file.company_id)
    if expense_currency != functional_currency:
        if moneda_por_codigo(db, file.company_id, expense_currency) is None:
            raise KontrolError(
                code="IMPORT_EXPENSE_CURRENCY_UNKNOWN",
                message="La moneda del gasto no existe en la empresa.",
                status_code=422,
            )

    document = None
    if import_document_id is not None:
        document = service._get_document(db, file.company_id, file, str(import_document_id))

    snapshot = capture_rate_snapshot(
        db,
        company_id=file.company_id,
        source_currency=expense_currency,
        target_currency=functional_currency,
        on_date=expense_date,
        actor=actor_id,
    )

    rate_value = snapshot.rate
    functional_amount = (amount * rate_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    expense = ImportExpense(
        company_id=file.company_id,
        file_id=file.id,
        kind=kind,
        supplier_id=expense_supplier_id,
        supplier_invoice_id=invoice_id_for_expense,
        reference=expense_reference,
        concept=concept.strip(),
        expense_date=expense_date,
        currency=expense_currency,
        amount=amount,
        functional_currency=functional_currency,
        functional_amount=functional_amount,
        rate_snapshot_id=snapshot.id,
        import_document_id=document.id if document else None,
        status="REGISTERED",
        created_by=actor_id,
        version=1,
    )
    db.add(expense)
    db.flush()

    service._audit(
        db,
        action="IMPORT_EXPENSE_REGISTERED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "amount": _money(expense.amount),
            "concept": expense.concept,
            "currency": expense.currency,
            "expense_date": expense.expense_date.isoformat(),
            "expense_id": str(expense.id),
            "functional_amount": _money(expense.functional_amount),
            "kind": expense.kind,
            "reference": expense.reference,
            "status": expense.status,
        },
    )
    party_service.bump(file)
    return expense


def void_expense(
    db: Session,
    *,
    file: ImportFile,
    expense_id: str,
    version: int,
    reason: str,
    actor_id: str,
    tenant_id: str,
) -> ImportExpense:
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
            message="El gasto no se puede anular en su estado actual.",
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
            message="El gasto tiene una aplicación vigente. Reviértala antes de anularlo.",
        )
    if not reason or not reason.strip():
        raise KontrolError(
            code="IMPORT_EXPENSE_REASON_REQUIRED",
            message="El motivo de anulación es obligatorio.",
            status_code=422,
        )

    before = {
        "amount": _money(expense.amount),
        "concept": expense.concept,
        "currency": expense.currency,
        "expense_date": expense.expense_date.isoformat(),
        "expense_id": str(expense.id),
        "functional_amount": _money(expense.functional_amount),
        "kind": expense.kind,
        "reference": expense.reference,
        "status": expense.status,
    }
    expense.status = "VOIDED"
    expense.void_reason = reason.strip()
    expense.voided_at = datetime.now(UTC)
    expense.voided_by = actor_id
    after = {
        **before,
        "status": expense.status,
    }

    service._audit(
        db,
        action="IMPORT_EXPENSE_VOIDED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    party_service.bump(expense)
    party_service.bump(file)
    return expense


def invoice_candidates(
    db: Session,
    *,
    file: ImportFile,
    q: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    invoices = db.scalars(
        select(SupplierInvoice).where(
            SupplierInvoice.company_id == file.company_id,
            SupplierInvoice.status.in_(ADMITTED_INVOICE_STATUSES),
        )
    ).all()

    candidates: list[dict[str, Any]] = []
    for invoice in invoices:
        if q and q.lower() not in invoice.invoice_number.lower():
            continue
        assigned = _assigned_to_invoice(db, file.company_id, str(invoice.id))
        available = _dec(invoice.total) - assigned
        if available <= 0:
            continue
        supplier = db.get(Party, invoice.supplier_id)
        candidates.append(
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "supplier_name": supplier.name if supplier else None,
                "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
                "currency": invoice.currency,
                "total": _money(_dec(invoice.total)),
                "tax_total": _money(_dec(invoice.tax_total)),
                "assigned": _money(assigned),
                "available": _money(available),
                "status": invoice.status,
            }
        )

    total = len(candidates)
    start = (page - 1) * page_size
    items = candidates[start : start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _tracking_expense_username(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    return user.username if user is not None else None


def _expense_application_detail(db: Session, expense: ImportExpense) -> tuple[dict, list[dict]]:
    applications = db.scalars(
        select(ImportCostApplication)
        .where(
            ImportCostApplication.expense_id == expense.id,
            ImportCostApplication.company_id == expense.company_id,
        )
        .order_by(ImportCostApplication.applied_at.desc(), ImportCostApplication.created_at.desc())
    ).all()

    applied_exists = any(application.status == "APPLIED" for application in applications)
    allowed_actions = {
        "void": expense.status == "REGISTERED" and not applied_exists,
        "classify": expense.status == "REGISTERED" and not applied_exists,
        "apply": expense.status == "REGISTERED"
        and expense.capitalization == "CAPITALIZABLE"
        and not applied_exists,
    }

    application_payloads = []
    for application in applications:
        allocations = db.scalars(
            select(ImportCostAllocation).where(
                ImportCostAllocation.application_id == application.id
            )
        ).all()

        can_reverse = application.status == "APPLIED" and all(
            (layer := db.get(CostLayer, allocation.layer_id)) is not None
            and _dec(layer.quantity_remaining) >= _dec(layer.quantity_in)
            for allocation in allocations
        )

        application_payloads.append(
            {
                "id": str(application.id),
                "version": application.version,
                "status": application.status,
                "criterion": application.criterion,
                "valuation_currency": application.valuation_currency,
                "valuation_amount": _money(application.valuation_amount),
                "applied_at": application.applied_at.isoformat() if application.applied_at else None,
                "applied_by_name": _tracking_expense_username(db, application.applied_by),
                "reversed_at": application.reversed_at.isoformat() if application.reversed_at else None,
                "reversed_by_name": _tracking_expense_username(db, application.reversed_by),
                "reversal_reason": application.reversal_reason,
                "can_reverse": can_reverse,
                "allocations": [
                    {
                        "product_code": db.scalar(
                            select(CatalogItem.code).where(CatalogItem.id == allocation.product_id)
                        )
                        if allocation.product_id
                        else None,
                        "product_name": db.scalar(
                            select(CatalogItem.name).where(CatalogItem.id == allocation.product_id)
                        )
                        if allocation.product_id
                        else None,
                        "allocated_amount": _money(allocation.allocated_amount),
                        "before_landed_cost": _money(allocation.before_landed_cost),
                        "after_landed_cost": _money(allocation.after_landed_cost),
                        "before_unit_cost": format(
                            allocation.before_unit_cost.quantize(Decimal("0.000001")), "f"
                        ),
                        "after_unit_cost": format(
                            allocation.after_unit_cost.quantize(Decimal("0.000001")), "f"
                        ),
                    }
                    for allocation in sorted(
                        allocations, key=lambda row: row.created_at or row.id
                    )
                ],
            }
        )
    return allowed_actions, application_payloads


def costs_detail(db: Session, file: ImportFile) -> dict[str, Any]:
    functional_currency = moneda_funcional(db, file.company_id)

    currencies = db.execute(
        select(Currency.code)
        .where(
            Currency.company_id == file.company_id,
            Currency.status == "ACTIVE",
        )
        .order_by(Currency.code)
    ).scalars().all()
    if functional_currency not in currencies:
        currencies = sorted([*currencies, functional_currency])

    receipt_refs = []
    receipts_by_ref: dict[str, GoodsReceipt] = {}
    if file.order_id:
        receipts = db.scalars(
            select(GoodsReceipt).where(
                GoodsReceipt.order_id == file.order_id,
                GoodsReceipt.company_id == file.company_id,
            )
        ).all()
        receipt_refs = [f"RECEIPT:{receipt.id}" for receipt in receipts]
        receipts_by_ref = {f"RECEIPT:{receipt.id}": receipt for receipt in receipts}

    layers = []
    goods_totals: dict[str, Decimal] = {}
    inventory_totals: dict[str, Decimal] = {}
    if receipt_refs:
        layers_rows = db.scalars(
            select(CostLayer).where(
                CostLayer.company_id == file.company_id,
                CostLayer.receipt_ref.in_(receipt_refs),
            )
        ).all()
        for layer in layers_rows:
            warehouse = db.get(Warehouse, layer.warehouse_id)
            catalog_item = db.get(CatalogItem, layer.product_id)
            receipt = receipts_by_ref.get(layer.receipt_ref) if layer.receipt_ref else None
            layers.append(
                {
                    "layer_id": str(layer.id),
                    "receipt_code": receipt.code if receipt else None,
                    "product_code": catalog_item.code if catalog_item else None,
                    "product_name": catalog_item.name if catalog_item else None,
                    "warehouse_name": warehouse.name if warehouse else None,
                    "quantity_in": format(layer.quantity_in.normalize(), "f"),
                    "quantity_remaining": format(layer.quantity_remaining.normalize(), "f"),
                    "unit_cost": _money(_dec(layer.unit_cost)),
                    "currency": layer.currency,
                    "landed_cost": _money(_dec(layer.landed_cost)),
                    "effective_unit_cost": format(
                        effective_unit_cost(layer).quantize(Decimal("0.000001")), "f"
                    ),
                    "value": _money(layer_value(layer)),
                    "partially_consumed": layer.quantity_remaining < layer.quantity_in,
                }
            )
            key = layer.currency
            goods_totals[key] = goods_totals.get(key, Decimal("0")) + (
                layer.quantity_in * _dec(layer.unit_cost)
            )
            inventory_totals[key] = inventory_totals.get(key, Decimal("0")) + layer_value(layer)

    expenses_rows = db.scalars(
        select(ImportExpense)
        .where(
            ImportExpense.file_id == file.id,
            ImportExpense.company_id == file.company_id,
        )
        .order_by(ImportExpense.expense_date, ImportExpense.created_at)
    ).all()
    expenses_detail = []
    for expense in expenses_rows:
        allowed_actions, applications = _expense_application_detail(db, expense)
        snapshot = db.scalar(
            select(TreasuryRateSnapshot).where(TreasuryRateSnapshot.id == expense.rate_snapshot_id)
        )
        document = None
        if expense.import_document_id:
            import_service_document = service._get_document(db, file.company_id, file, expense.import_document_id)
            if import_service_document is not None:
                document = {
                    "id": str(import_service_document.id),
                    "name": import_service_document.name,
                    "status": import_service_document.status,
                }
        supplier = db.get(Party, expense.supplier_id)
        invoice = None
        if expense.supplier_invoice_id:
            linked_invoice = db.get(SupplierInvoice, expense.supplier_invoice_id)
            if linked_invoice is not None:
                invoice = linked_invoice.invoice_number
        expenses_detail.append(
            {
                "id": str(expense.id),
                "kind": expense.kind,
                "concept": expense.concept,
                "reference": expense.reference,
                "supplier_name": supplier.name if supplier else None,
                "invoice_number": invoice,
                "expense_date": expense.expense_date.isoformat(),
                "currency": expense.currency,
                "amount": _money(expense.amount),
                "functional_amount": _money(expense.functional_amount),
                "status": expense.status,
                "void_reason": expense.void_reason,
                "capitalization": expense.capitalization,
                "version": expense.version,
                "username": _tracking_expense_username(db, expense.created_by),
                "created_at": expense.created_at.isoformat() if expense.created_at else None,
                "rate": {
                    "value": format(snapshot.rate, "f").rstrip("0").rstrip(".") if snapshot else "0.00",
                    "source": snapshot.rate_source if snapshot else None,
                    "type": snapshot.rate_type if snapshot else None,
                    "date": snapshot.rate_date.isoformat() if snapshot and snapshot.rate_date else None,
                    "origin": snapshot.origin if snapshot else None,
                    "derivation": snapshot.derivation if snapshot else None,
                    "identity": snapshot.rate_source == "SAME_CURRENCY_IDENTITY" if snapshot else False,
                },
                "document": document,
                "allowed_actions": allowed_actions,
                "applications": applications,
            }
        )

    registered = [expense for expense in expenses_rows if expense.status == "REGISTERED"]
    totals_by_currency: dict[str, Decimal] = {}
    for expense in registered:
        key = expense.currency
        totals_by_currency[key] = totals_by_currency.get(key, Decimal("0")) + expense.amount
    totals = {
        "count": len(registered),
        "functional_total": _money(sum((e.functional_amount for e in registered), Decimal("0"))),
        "by_currency": [
            {"currency": key, "amount": _money(value)}
            for key, value in sorted(totals_by_currency.items())
        ],
    }

    return {
        "functional_currency": functional_currency,
        "can_register": file.status in ADMITTED_FILE_STATUSES,
        "currencies": list(currencies),
        "expenses": expenses_detail,
        "totals": totals,
        "layers": layers,
        "goods_totals": [
            {"currency": key, "amount": _money(value)}
            for key, value in sorted(goods_totals.items())
        ],
        "inventory_totals": [
            {"currency": key, "amount": _money(value)}
            for key, value in sorted(inventory_totals.items())
        ],
    }
