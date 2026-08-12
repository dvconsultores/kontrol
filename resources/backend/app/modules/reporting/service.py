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
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import KontrolError, NotFoundError
from app.modules.purchasing import service as ap_service
from app.modules.reporting.models import ReportExport, ReportJob
from app.shared import audit as audit_service


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


def _exports_dir() -> Path:
    """Directorio de archivos de exportación bajo KONTROL_STORAGE_PATH."""
    d = Path(get_settings().storage_path) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def _render_pdf(report_key: str, period: str, rows: list[dict]) -> bytes:
    """Genera un PDF real con ReportLab (platypus): encabezado + tabla (KAUD-002)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), rightMargin=15 * mm,
                            leftMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"KONTROL — Reporte: {report_key}", styles["Title"]),
             Paragraph(f"Período: {period or '—'} · Generado: {datetime.now(UTC).isoformat()}", styles["Normal"]),
             Spacer(1, 6 * mm)]
    if rows:
        headers = list(rows[0].keys())
        data = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("Sin datos para el reporte.", styles["Normal"]))
    doc.build(story)
    return buf.getvalue()


def create_export(db: Session, *, company_id: str, report_key: str, fmt: str = "CSV",
                  filters: dict | None = None, actor: str | None = None) -> ReportExport:
    """Exporta un reporte de forma **auditada** con archivo real (FR-009-020, KAUD-002).

    Genera el contenido (CSV/PDF), lo persiste bajo `KONTROL_STORAGE_PATH/exports/`
    y registra el evento de auditoría de la exportación.
    """
    company_id = _company(company_id, obj="exportación")
    if fmt not in ("CSV", "PDF"):
        raise KontrolError(code="INVALID_FORMAT", message="Formato inválido (CSV/PDF)", status_code=422)
    data = report(db, company_id=company_id, key=report_key, period=(filters or {}).get("period", ""))
    rows = [dict(r) for r in (data.get("rows") or [])]
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_ref = f"report-{report_key}-{stamp}.{fmt.lower()}"

    content = _to_csv(rows).encode("utf-8") if fmt == "CSV" else _render_pdf(report_key, (filters or {}).get("period", ""), rows)
    target = _exports_dir() / file_ref
    target.write_bytes(content)

    export = ReportExport(company_id=company_id, report_key=report_key, format=fmt,
                          filters=json.dumps(filters or {}), file_ref=file_ref, exported_by=actor,
                          exported_at=datetime.now(UTC), status="DONE", created_by=actor)
    db.add(export)
    db.flush()
    audit_service.record_audit(db, action="REPORT_EXPORTED", entity_type="ReportExport",
                               entity_id=str(export.id), company_id=company_id, user_id=actor,
                               source="API", after={"report_key": report_key, "format": fmt, "file_ref": file_ref})
    return export


def get_export_file(db: Session, *, export_id: str, company_id: str) -> tuple[str, bytes]:
    """Devuelve (filename, content) de una exportación del propio tenant (KAUD-002)."""
    export = db.get(ReportExport, export_id)
    if not export or export.company_id != company_id:
        raise NotFoundError(code="EXPORT_NOT_FOUND", message="Exportación no encontrada")
    if not export.file_ref:
        raise NotFoundError(code="EXPORT_FILE_MISSING", message="La exportación no tiene archivo asociado")
    path = _exports_dir() / export.file_ref
    if not path.exists():
        raise NotFoundError(code="EXPORT_FILE_MISSING", message="El archivo de la exportación no existe")
    return path.name, path.read_bytes()


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
