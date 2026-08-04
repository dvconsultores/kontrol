"""Servicios de reportes y auditoría (009).

Dashboard (indicadores y vencimientos), reportes ejecutivos/operativos/
financieros/fiscales/regulatorios (solo lectura sobre 003-008), exportación
auditada (CSV/PDF), trabajos asíncronos y timeline de auditoría (reutiliza
`AuditEvent` de 001).

Invariantes (DOC-01 §1/§5): reconstrucción desde eventos; exportaciones
auditadas; 009 no duplica la lógica de 003-008.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import KontrolError, NotFoundError
from app.modules.purchasing import service as ap_service
from app.modules.reporting.models import ReportExport, ReportJob


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard(db: Session, *, company_id: str) -> dict:
    """Indicadores agregados y vencimientos por módulo (FR-009-001/002)."""
    from app.modules.fiscal.models import FiscalDocument, FiscalPeriod
    from app.modules.purchasing.models import SupplierInvoice
    from app.modules.regulatory.models import PermitInstance, RegulatoryEvaluation
    from app.modules.sales.models import SalesInvoice
    from app.modules.treasury.models import BankTransaction

    company_id = _company(company_id, obj="dashboard")

    def _sum(model, *statuses):
        q = select(func.coalesce(func.sum(model.total), 0.0)).where(model.company_id == company_id)
        if statuses:
            q = q.where(model.status.in_(statuses))
        return float(db.execute(q).scalar() or 0.0)

    sales_total = _sum(SalesInvoice, "EMITTED", "DELIVERED", "PARTIALLY_PAID", "PAID")
    purchases_total = _sum(SupplierInvoice, "POSTED", "PARTIALLY_PAID", "PAID")
    bank_total = float(db.execute(select(func.coalesce(func.sum(BankTransaction.amount), 0.0)).where(
        BankTransaction.company_id == company_id)).scalar() or 0.0)
    emitted = db.execute(select(func.count()).select_from(FiscalDocument).where(
        FiscalDocument.company_id == company_id)).scalar() or 0
    blocked = db.execute(select(func.count()).select_from(RegulatoryEvaluation).where(
        RegulatoryEvaluation.company_id == company_id, RegulatoryEvaluation.status == "BLOCKED")).scalar() or 0
    cxc = ap_service.aging(db, company_id=company_id, item_type="RECEIVABLE")
    cxp = ap_service.aging(db, company_id=company_id, item_type="PAYABLE")

    # Vencimientos
    from app.modules.purchasing.models import OpenItem

    today = date.today()
    due_items = db.execute(select(func.count()).select_from(OpenItem).where(
        OpenItem.company_id == company_id, OpenItem.status == "OPEN",
        OpenItem.due_date.isnot(None), OpenItem.due_date < today)).scalar() or 0
    open_periods = db.execute(select(func.count()).select_from(FiscalPeriod).where(
        FiscalPeriod.company_id == company_id, FiscalPeriod.status == "OPEN")).scalar() or 0
    active_permits = db.execute(select(func.count()).select_from(PermitInstance).where(
        PermitInstance.company_id == company_id,
        PermitInstance.status.in_(["APPROVED_FOR_USE", "USED"]))).scalar() or 0

    return {
        "indicators": {
            "ventas": round(sales_total, 2),
            "compras": round(purchases_total, 2),
            "tesoreria_banco": round(bank_total, 2),
            "cxc": round(cxc["total"], 2),
            "cxp": round(cxp["total"], 2),
            "documentos_fiscales": emitted,
            "despachos_bloqueados": blocked,
        },
        "vencimientos": {
            "open_items_vencidos": due_items,
            "periodos_fiscales_abiertos": open_periods,
            "permisos_activos": active_permits,
        },
    }


# --------------------------------------------------------------------------- #
# Reportes (solo lectura sobre 003-008)
# --------------------------------------------------------------------------- #
def report(db: Session, *, company_id: str, key: str, period: str = "") -> dict:
    company_id = _company(company_id, obj="reporte")
    if key == "executive_ventas":
        return _executive_ventas(db, company_id, period)
    if key == "operational_inventario":
        return _operational_inventario(db, company_id)
    if key == "financial_aging":
        return _financial_aging(db, company_id)
    if key.startswith("fiscal_libros_"):
        tax_type = key.split("_", 2)[2].upper()
        from app.modules.fiscal import service as fiscal_service

        return fiscal_service.books(db, company_id=company_id, tax_type=tax_type, period=period or "0")
    if key == "regulatory_evaluaciones":
        return _regulatory(db, company_id)
    raise NotFoundError(code="REPORT_NOT_FOUND", message="Reporte no encontrado")


def _executive_ventas(db: Session, company_id: str, period: str) -> dict:
    from app.modules.sales.models import SalesInvoice

    rows = db.execute(select(SalesInvoice).where(
        SalesInvoice.company_id == company_id,
        SalesInvoice.status.in_(["EMITTED", "DELIVERED", "PARTIALLY_PAID", "PAID"]))).scalars().all()
    total = sum(float(i.total or 0.0) for i in rows)
    base = sum(float(i.base_fiscal or 0.0) for i in rows)
    tax = sum(float(i.tax_total or 0.0) for i in rows)
    return {"report_key": "executive_ventas", "period": period, "count": len(rows),
            "total": round(total, 2), "base": round(base, 2), "tax": round(tax, 2),
            "rows": [{"id": str(i.id), "invoice_number": i.invoice_number, "customer_id": i.customer_id,
                      "base_fiscal": i.base_fiscal, "tax_total": i.tax_total, "total": i.total, "status": i.status}
                     for i in rows]}


def _operational_inventario(db: Session, company_id: str) -> dict:
    from app.modules.inventory.models import InventoryBalance, InventoryMovement

    balances = db.execute(select(InventoryBalance).where(InventoryBalance.company_id == company_id)).scalars().all()
    movements = db.execute(select(func.count()).select_from(InventoryMovement).where(
        InventoryMovement.company_id == company_id)).scalar() or 0
    total_qty = sum(float(b.qty_on_hand or 0.0) for b in balances)
    return {"report_key": "operational_inventario", "count": len(balances), "movements": movements,
            "qty_on_hand": round(total_qty, 4),
            "rows": [{"id": str(b.id), "product_id": b.product_id, "warehouse_id": b.warehouse_id,
                      "qty_on_hand": b.qty_on_hand, "qty_available": b.qty_available, "state": b.state}
                     for b in balances]}


def _financial_aging(db: Session, company_id: str) -> dict:
    cxc = ap_service.aging(db, company_id=company_id, item_type="RECEIVABLE")
    cxp = ap_service.aging(db, company_id=company_id, item_type="PAYABLE")
    return {"report_key": "financial_aging", "cxc": cxc, "cxp": cxp}


def _regulatory(db: Session, company_id: str) -> dict:
    from app.modules.regulatory.models import PermitInstance, RegulatoryEvaluation

    evaluations = db.execute(select(RegulatoryEvaluation).where(RegulatoryEvaluation.company_id == company_id)).scalars().all()
    permits = db.execute(select(func.count()).select_from(PermitInstance).where(
        PermitInstance.company_id == company_id)).scalar() or 0
    return {"report_key": "regulatory_evaluaciones", "count": len(evaluations), "permits": permits,
            "rows": [{"id": str(e.id), "shipment_id": e.shipment_id, "status": e.status, "blockers": e.blockers}
                     for e in evaluations]}


# --------------------------------------------------------------------------- #
# Exportación auditada (P5)
# --------------------------------------------------------------------------- #
def _to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


def create_export(db: Session, *, company_id: str, report_key: str, fmt: str = "CSV",
                  filters: dict | None = None, actor: str | None = None) -> ReportExport:
    """Exporta un reporte de forma **auditada** (FR-009-020)."""
    company_id = _company(company_id, obj="exportación")
    if fmt not in ("CSV", "PDF"):
        raise KontrolError(code="INVALID_FORMAT", message="Formato inválido (CSV/PDF)", status_code=422)
    data = report(db, company_id=company_id, key=report_key, period=(filters or {}).get("period", ""))
    rows = [dict(r) for r in (data.get("rows") or [])]
    file_ref = None
    if fmt == "CSV":
        _to_csv(rows)  # contenido generado; se registra metadata auditada (P5)
        file_ref = f"report-{report_key}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.csv"
    else:
        file_ref = f"report-{report_key}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.pdf"
    export = ReportExport(company_id=company_id, report_key=report_key, format=fmt,
                          filters=json.dumps(filters or {}), file_ref=file_ref, exported_by=actor,
                          exported_at=datetime.now(UTC), status="DONE", created_by=actor)
    db.add(export)
    db.flush()
    return export


# --------------------------------------------------------------------------- #
# Trabajos asíncronos
# --------------------------------------------------------------------------- #
def create_job(db: Session, *, company_id: str, report_key: str, params: dict | None = None,
               actor: str | None = None) -> ReportJob:
    company_id = _company(company_id, obj="trabajo de reporte")
    job = ReportJob(company_id=company_id, report_key=report_key, params=json.dumps(params or {}),
                    status="PENDING", created_by=actor)
    db.add(job)
    db.flush()
    return job


def run_job(db: Session, *, company_id: str, job_id: str) -> ReportJob:
    job = db.get(ReportJob, job_id)
    if not job or job.company_id != company_id:
        raise NotFoundError(code="JOB_NOT_FOUND", message="Trabajo no encontrado")
    job.status = "RUNNING"
    job.started_at = datetime.now(UTC)
    db.flush()
    try:
        params = json.loads(job.params or "{}")
        report(db, company_id=company_id, key=job.report_key, period=params.get("period", ""))
        job.result_ref = f"{job.report_key}-{str(job.id)[:8]}.out"
        job.status = "DONE"
    except Exception as exc:  # noqa: BLE001
        job.status = "FAILED"
        job.error = str(exc)
    job.finished_at = datetime.now(UTC)
    db.flush()
    return job


# --------------------------------------------------------------------------- #
# Auditoría (reutiliza AuditEvent de 001)
# --------------------------------------------------------------------------- #
def audit_timeline(db: Session, *, company_id: str, entity_type: str | None = None,
                   action: str | None = None, user_id: str | None = None) -> list[dict]:
    from app.modules.audit.models import AuditEvent

    query = select(AuditEvent).where(AuditEvent.company_id == company_id)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if action:
        query = query.where(AuditEvent.action == action)
    if user_id:
        query = query.where(AuditEvent.user_id == user_id)
    items = db.execute(query.order_by(AuditEvent.event_time.desc()).limit(200)).scalars().all()
    return [{"id": str(e.id), "action": e.action, "entity_type": e.entity_type, "entity_id": e.entity_id,
             "user_id": e.user_id, "source": e.source, "reason": e.reason,
             "event_time": e.event_time.isoformat() if e.event_time else None} for e in items]
