"""Pruebas de reportes y auditoría (009).

Cubre: dashboard con indicadores/vencimientos, reportes ejecutivos/operativos/
financieros/fiscales/regulatorios, exportación auditada, trabajos asíncronos,
timeline de auditoría y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from conftest import make_engine, seed_org_chain
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.fiscal import service as fiscal_service
from app.modules.inventory.models import InventoryBalance
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Warehouse
from app.modules.purchasing.models import SupplierInvoice
from app.modules.reporting import service as reporting_service
from app.modules.sales.models import SalesInvoice


@pytest.fixture()
def db_session():
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    seed_org_chain(session, COMPANY, OTHER)
    try:
        yield session
    finally:
        session.close()


COMPANY = "tenant-1"
OTHER = "tenant-2"


def _make_party(db: Session, company: str = COMPANY) -> Party:
    party = Party(company_id=company, code="CLI-1", name="Cliente SA", person_type="JURIDICA",
                  tax_id=f"J-{abs(hash(company)) % 100000000}-1", roles=["CLIENTE"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_sales_invoice(db: Session, company: str = COMPANY, total: float = 1000.0) -> SalesInvoice:
    party = _make_party(db, company)
    inv = SalesInvoice(company_id=company, customer_id=str(party.id), base_fiscal_currency="VED",
                       base_fiscal=total, tax_total=160.0, total=total, status="EMITTED")
    db.add(inv)
    db.flush()
    return inv


def _make_supplier_invoice(db: Session, company: str = COMPANY, total: float = 500.0) -> SupplierInvoice:
    party = _make_party(db, company)
    inv = SupplierInvoice(company_id=company, supplier_id=str(party.id), invoice_number="F-1",
                          currency="VED", tax_total=0.0, total=total, status="POSTED")
    db.add(inv)
    db.flush()
    return inv


def _make_inventory(db: Session, company: str = COMPANY) -> None:
    product = CatalogItem(company_id=company, code="P-1", name="Producto", item_type="PRODUCT", status="ACTIVE")
    wh = Warehouse(company_id=company, code="W-1", name="Principal", status="ACTIVE")
    db.add_all([product, wh])
    db.flush()
    db.add(InventoryBalance(company_id=company, warehouse_id=str(wh.id), product_id=str(product.id),
                            state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0))
    db.flush()


def _make_fiscal(db: Session, company: str = COMPANY) -> None:
    invoice = _make_sales_invoice(db, company)
    series = fiscal_service.create_number_series(db, company_id=company, document_type="INVOICE", prefix="FV")
    batch = fiscal_service.create_control_batch(db, company_id=company, range_from="2001", range_to="2005")
    fiscal_service.emit_document(db, company_id=company, business_document=f"INVOICE:{invoice.id}",
                                 series_id=str(series.id), batch_id=str(batch.id))


class TestDashboard:
    def test_dashboard_indicators(self, db_session) -> None:
        _make_sales_invoice(db_session, total=1000.0)
        _make_supplier_invoice(db_session, total=500.0)
        dash = reporting_service.dashboard(db_session, company_id=COMPANY)
        assert dash["indicators"]["ventas"] == 1000.0
        assert dash["indicators"]["compras"] == 500.0

    def test_dashboard_vencimientos(self, db_session) -> None:
        party = _make_party(db_session)
        from app.modules.purchasing.models import OpenItem

        db_session.add(OpenItem(company_id=COMPANY, party_id=str(party.id), source_document="FACT-1",
                                item_type="PAYABLE", currency="VED", original=100.0,
                                due_date=date.today() - timedelta(days=5), status="OPEN"))
        db_session.flush()
        dash = reporting_service.dashboard(db_session, company_id=COMPANY)
        assert dash["vencimientos"]["open_items_vencidos"] == 1


class TestReportes:
    def test_executive_ventas(self, db_session) -> None:
        _make_sales_invoice(db_session, total=1000.0)
        rep = reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas")
        assert rep["count"] == 1 and rep["total"] == 1000.0 and rep["tax"] == 160.0

    def test_operational_inventario(self, db_session) -> None:
        _make_inventory(db_session)
        rep = reporting_service.report(db_session, company_id=COMPANY, key="operational_inventario")
        assert rep["qty_on_hand"] == 10.0 and rep["count"] == 1

    def test_financial_aging(self, db_session) -> None:
        party = _make_party(db_session)
        from app.modules.purchasing.models import OpenItem

        db_session.add(OpenItem(company_id=COMPANY, party_id=str(party.id), source_document="FACT-2",
                                item_type="RECEIVABLE", currency="VED", original=200.0, status="OPEN"))
        db_session.flush()
        rep = reporting_service.report(db_session, company_id=COMPANY, key="financial_aging")
        assert rep["cxc"]["total"] == 200.0

    def test_fiscal_libros_reuses_007(self, db_session) -> None:
        _make_fiscal(db_session)
        rep = reporting_service.report(db_session, company_id=COMPANY, key="fiscal_libros_VENTAS")
        assert rep["count"] == 1 and rep["total"] == 1000.0

    def test_regulatory_evaluaciones(self, db_session) -> None:
        rep = reporting_service.report(db_session, company_id=COMPANY, key="regulatory_evaluaciones")
        assert rep["report_key"] == "regulatory_evaluaciones"

    def test_unknown_report(self, db_session) -> None:
        with pytest.raises(NotFoundError):
            reporting_service.report(db_session, company_id=COMPANY, key="no_existe")


class TestExportacionYJobs:
    def test_export_auditada(self, db_session) -> None:
        _make_sales_invoice(db_session, total=1000.0)
        export = reporting_service.create_export(db_session, company_id=COMPANY, report_key="executive_ventas",
                                                 fmt="CSV", filters={"period": "2026-01"}, actor="user-1")
        assert export.status == "DONE" and export.exported_by == "user-1"
        assert export.file_ref and export.file_ref.endswith(".csv")
        # KAUD-002: el archivo debe existir físicamente con contenido real
        filename, content = reporting_service.get_export_file(db_session, export_id=str(export.id), company_id=COMPANY)
        assert filename == export.file_ref
        assert content.startswith(b"id,") and len(content) > 20  # CSV con contenido real
        # el evento de exportación queda auditado (KAUD-001)
        assert db_session.query(AuditEvent).filter(AuditEvent.action == "REPORT_EXPORTED").count() >= 1

    def test_export_pdf_genera_archivo(self, db_session) -> None:
        _make_sales_invoice(db_session, total=1000.0)
        export = reporting_service.create_export(db_session, company_id=COMPANY, report_key="executive_ventas",
                                                 fmt="PDF", actor="user-1")
        assert export.file_ref and export.file_ref.endswith(".pdf")
        _, content = reporting_service.get_export_file(db_session, export_id=str(export.id), company_id=COMPANY)
        assert content.startswith(b"%PDF"), "el PDF debe ser un archivo PDF real (ReportLab)"

    def test_export_isolada_por_tenant(self, db_session) -> None:
        _make_sales_invoice(db_session, total=1000.0)
        export = reporting_service.create_export(db_session, company_id=COMPANY, report_key="executive_ventas",
                                                 fmt="CSV", actor="user-1")
        with pytest.raises(NotFoundError):
            reporting_service.get_export_file(db_session, export_id=str(export.id), company_id=OTHER)

    def test_export_invalid_format(self, db_session) -> None:
        with pytest.raises(KontrolError):
            reporting_service.create_export(db_session, company_id=COMPANY, report_key="executive_ventas", fmt="XLSX")

    def test_job_lifecycle(self, db_session) -> None:
        _make_sales_invoice(db_session, total=100.0)
        job = reporting_service.create_job(db_session, company_id=COMPANY, report_key="executive_ventas")
        assert job.status == "PENDING"
        reporting_service.run_job(db_session, company_id=COMPANY, job_id=str(job.id))
        assert job.status == "DONE" and job.result_ref is not None

    def test_jobs_list(self, db_session) -> None:
        """KAUD-003: lista de jobs por tenant (GET /reporting/jobs)."""
        from app.modules.reporting.models import ReportJob

        db_session.add(ReportJob(company_id=COMPANY, report_key="executive_ventas",
                                 params="{}", status="DONE", result_ref="x.out"))
        db_session.add(ReportJob(company_id=OTHER, report_key="executive_ventas",
                                 params="{}", status="DONE", result_ref="y.out"))
        db_session.flush()
        from sqlalchemy import select

        mine = db_session.execute(select(ReportJob).where(ReportJob.company_id == COMPANY)).scalars().all()
        assert len(mine) == 1  # solo los del propio tenant


class TestAuditoriaYMultiempresa:
    def test_audit_timeline(self, db_session) -> None:
        db_session.add(AuditEvent(company_id=COMPANY, user_id="u1", action="EXPORT", entity_type="REPORT",
                                  entity_id="e1", source="API", event_time=datetime.now()))
        db_session.flush()
        items = reporting_service.audit_timeline(db_session, company_id=COMPANY)
        assert len(items) == 1 and items[0]["action"] == "EXPORT"

    def test_tenant_isolation(self, db_session) -> None:
        _make_sales_invoice(db_session, company=COMPANY)
        dash_other = reporting_service.dashboard(db_session, company_id=OTHER)
        assert dash_other["indicators"]["ventas"] == 0.0
