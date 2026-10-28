"""Pruebas de período civil de Caracas para reportes (009 + 001 + 007).

Cubre el filtrado del período «AAAA-MM» en el reporte gerencial de ventas,
la validación de período para todo reporte y la declaración explícita de que
los libros fiscales no filtran por período (bloqueo normativo).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from conftest import seed_org_chain
from sqlalchemy.orm import Session

from app.core.errors import KontrolError
from app.modules.fiscal import service as fiscal_service
from app.modules.master_data.models import Party
from app.modules.reporting import service as reporting_service
from app.modules.sales.models import SalesInvoice
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO


@pytest.fixture()
def db_session(sesion_de_prueba):
    seed_org_chain(sesion_de_prueba, COMPANY, OTHER)
    return sesion_de_prueba


COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS


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


def _make_fiscal(db: Session, company: str = COMPANY) -> None:
    invoice = _make_sales_invoice(db, company)
    series = fiscal_service.create_number_series(db, company_id=company, document_type="INVOICE", prefix="FV")
    batch = fiscal_service.create_control_batch(db, company_id=company, range_from="2001", range_to="2005")
    fiscal_service.emit_document(db, company_id=company, business_document=f"INVOICE:{invoice.id}",
                                 series_id=str(series.id), batch_id=str(batch.id))


def _factura_emitida(db: Session, party: Party, issued_at: datetime, total: float) -> SalesInvoice:
    inv = SalesInvoice(company_id=party.company_id, customer_id=str(party.id), base_fiscal_currency="VED",
                       base_fiscal=total, tax_total=160.0, total=total, status="EMITTED",
                       issued_at=issued_at)
    db.add(inv)
    db.flush()
    return inv


def test_el_periodo_es_el_mes_de_caracas(db_session):
    party = _make_party(db_session)
    _factura_emitida(db_session, party, datetime(2026, 11, 1, 3, 59, tzinfo=UTC), 100)
    _factura_emitida(db_session, party, datetime(2026, 11, 1, 4, 0, tzinfo=UTC), 200)
    _factura_emitida(db_session, party, datetime(2026, 10, 1, 4, 0, tzinfo=UTC), 400)

    resultado_octubre = reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas", period="2026-10")
    assert resultado_octubre["count"] == 2
    assert resultado_octubre["total"] == 500.0
    assert resultado_octubre["period_applied"] is True

    resultado_noviembre = reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas", period="2026-11")
    assert resultado_noviembre["count"] == 1
    assert resultado_noviembre["total"] == 200.0


def test_sin_periodo_no_se_filtra(db_session):
    party = _make_party(db_session)
    _factura_emitida(db_session, party, datetime(2026, 11, 1, 3, 59, tzinfo=UTC), 100)
    _factura_emitida(db_session, party, datetime(2026, 11, 1, 4, 0, tzinfo=UTC), 200)
    _factura_emitida(db_session, party, datetime(2026, 10, 1, 4, 0, tzinfo=UTC), 400)

    resultado_vacio = reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas", period="")
    assert resultado_vacio["count"] == 3
    assert resultado_vacio["period_applied"] is False

    resultado_cero = reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas", period="0")
    assert resultado_cero["count"] == 3
    assert resultado_cero["period_applied"] is False


def test_un_periodo_invalido_es_422(db_session):
    with pytest.raises(KontrolError) as exc_info:
        reporting_service.report(db_session, company_id=COMPANY, key="executive_ventas", period="2026-13")
    assert exc_info.value.code == "INVALID_PERIOD"
    assert exc_info.value.status_code == 422

    with pytest.raises(KontrolError) as exc_info:
        reporting_service.report(db_session, company_id=COMPANY, key="fiscal_libros_VENTAS", period="octubre")
    assert exc_info.value.code == "INVALID_PERIOD"
    assert exc_info.value.status_code == 422


def test_los_libros_fiscales_declaran_que_no_filtran(db_session):
    _make_fiscal(db_session)
    resultado = reporting_service.report(db_session, company_id=COMPANY, key="fiscal_libros_VENTAS", period="2026-10")
    assert resultado["period_applied"] is False
    assert resultado["period_rule"] == "LEGAL_VALIDATION_REQUIRED"
    assert resultado["count"] == 1


def test_los_reportes_sin_periodo_declaran_period_applied(db_session):
    resultado = reporting_service.report(db_session, company_id=COMPANY, key="operational_inventario")
    assert resultado["period_applied"] is False
