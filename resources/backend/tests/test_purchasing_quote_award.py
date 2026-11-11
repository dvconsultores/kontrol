"""Pruebas de adjudicación y conversión de cotizaciones de compra."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from conftest import seed_org_chain
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import PurchaseOrderLine, SupplierQuote
from app.shared.clock import hoy_de_negocio
from tests.test_purchasing import COMPANY, OTHER, _make_party, _make_product


@pytest.fixture()
def db_session(sesion_de_prueba):
    seed_org_chain(sesion_de_prueba, COMPANY, OTHER)
    return sesion_de_prueba


def _make_quote(db: Session, *, company: str = COMPANY, code: str = "COT-1",
                validity_until=None, currency: str = "VED", supplier=None,
                terms: str | None = None) -> SupplierQuote:
    if supplier is None:
        supplier = _make_party(db, company=company)
    quote = ap_service.create_quote(db, company_id=company, code=code, supplier_id=str(supplier.id),
                                    validity_until=validity_until, currency=currency, terms=terms)
    db.flush()
    return quote


class TestComparacionCotizaciones:
    def test_compare_quotes_orders_by_currency_price_delivery(self, db_session) -> None:
        product = _make_product(db_session)
        supplier1 = _make_party(db_session, code="SUP-1", name="Proveedor 1")
        supplier2 = _make_party(db_session, code="SUP-2", name="Proveedor 2")
        supplier3 = _make_party(db_session, code="SUP-3", name="Proveedor 3")
        other_supplier = _make_party(db_session, company=OTHER, code="SUP-OTHER", name="Otro")

        quote1 = _make_quote(db_session, code="COT-1", supplier=supplier1)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote1.id),
                                  product_id=str(product.id), quantity=5, unit_price=10,
                                  discount=1.0, delivery_days=7)
        quote2 = _make_quote(db_session, code="COT-2", supplier=supplier2)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote2.id),
                                  product_id=str(product.id), quantity=5, unit_price=8.50,
                                  discount=0.5, delivery_days=3)
        quote3 = _make_quote(db_session, code="COT-3", currency="USD", supplier=supplier3)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote3.id),
                                  product_id=str(product.id), quantity=1, unit_price=20,
                                  discount=0.0, delivery_days=None)
        other_quote = _make_quote(db_session, company=OTHER, code="COT-OTHER", supplier=other_supplier)
        ap_service.add_quote_line(db_session, company_id=OTHER, quote_id=str(other_quote.id),
                                  product_id=str(_make_product(db_session, company=OTHER, code="P-OTHER").id),
                                  quantity=1, unit_price=1)

        result = ap_service.compare_quotes(db_session, company_id=COMPANY, product_id=str(product.id))
        assert result["product_id"] == str(product.id)
        assert [item["currency"] for item in result["items"]] == ["USD", "VED", "VED"]
        assert [item["quote_code"] for item in result["items"][1:]] == ["COT-2", "COT-1"]
        assert Decimal(str(result["items"][0]["line_amount"])) == Decimal("20.00")
        assert Decimal(str(result["items"][1]["line_amount"])) == Decimal("42.50")
        assert Decimal(str(result["items"][2]["line_amount"])) == Decimal("50.00")
        assert result["items"][1]["discount"] == "0.50"
        assert result["items"][2]["discount"] == "1.00"
        assert all(item["quote_id"] != str(other_quote.id) for item in result["items"])


class TestAdjudicacionCotizacion:
    def test_award_ok(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-OK")
        quote = _make_quote(db_session, code="COT-AWARD", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)

        awarded = ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                         reason="Mejor precio", actor="user-1")
        assert awarded.status == "AWARDED"
        assert awarded.awarded_by == "user-1"
        assert awarded.award_reason == "Mejor precio"
        assert awarded.awarded_at is not None

        result = ap_service.compare_quotes(db_session, company_id=COMPANY, product_id=str(product.id))
        assert result["items"][0]["can_award"] is False

    def test_award_negatives(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-NEG")

        # Razón en blanco
        quote = _make_quote(db_session, code="COT-BLANK", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        with pytest.raises(KontrolError) as exc:
            ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="   ")
        assert exc.value.code == "REASON_REQUIRED"

        # Cotización vencida
        yesterday = hoy_de_negocio() - timedelta(days=1)
        expired = _make_quote(db_session, code="COT-EXPIRED", supplier=supplier, validity_until=yesterday)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(expired.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        with pytest.raises(ConflictError) as exc:
            ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(expired.id), reason="Razón")
        assert exc.value.code == "QUOTE_EXPIRED"

        # Cotización sin líneas
        empty = _make_quote(db_session, code="COT-EMPTY", supplier=supplier)
        with pytest.raises(ConflictError) as exc:
            ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(empty.id), reason="Razón")
        assert exc.value.code == "QUOTE_EMPTY"

        # Doble adjudicación
        quote = _make_quote(db_session, code="COT-TWICE", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Primera")
        with pytest.raises(ConflictError) as exc:
            ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Segunda")
        assert exc.value.code == "QUOTE_ALREADY_AWARDED"

        # Otra empresa
        other_product = _make_product(db_session, company=OTHER, code="P-OTHER-2")
        other_supplier = _make_party(db_session, company=OTHER, code="SUP-OTHER-2")
        other_quote = _make_quote(db_session, company=OTHER, code="COT-OTHER-2", supplier=other_supplier)
        ap_service.add_quote_line(db_session, company_id=OTHER, quote_id=str(other_quote.id),
                                  product_id=str(other_product.id), quantity=1, unit_price=10)
        with pytest.raises(NotFoundError):
            ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(other_quote.id), reason="Razón")


class TestOrdenDesdeCotizacion:
    def test_order_from_quote(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-ORDER")
        quote = _make_quote(db_session, code="COT-TOCONVERT", supplier=supplier, terms="Pago 30 días")
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=5, unit_price=10.25,
                                  discount=1.5, delivery_days=7)
        ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Mejor oferta")

        order, created = ap_service.order_from_quote(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                                     code="OC-FROM-QUOTE", actor="user-1")
        assert created is True
        assert order.status == "DRAFT"
        assert order.supplier_id == str(supplier.id)
        assert order.currency == "VED"
        assert order.terms == "Pago 30 días"
        assert order.quote_id == str(quote.id)

        lines = db_session.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == order.id)
        ).scalars().all()
        assert len(lines) == 1
        assert Decimal(str(lines[0].quantity_ordered)) == Decimal("5")
        assert Decimal(str(lines[0].unit_price)) == Decimal("10.25")
        assert Decimal(str(lines[0].discount)) == Decimal("1.50")
        assert lines[0].tax_ref is None

        db_session.refresh(quote)
        assert quote.status == "CONVERTED"

        same_order, created_again = ap_service.order_from_quote(db_session, company_id=COMPANY,
                                                                quote_id=str(quote.id), code="OC-DUP")
        assert created_again is False
        assert same_order.id == order.id

    def test_order_requires_awarded(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-NOT-AWARDED")
        quote = _make_quote(db_session, code="COT-NOT-AWARDED", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)

        with pytest.raises(ConflictError) as exc:
            ap_service.order_from_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), code="OC-X")
        assert exc.value.code == "QUOTE_NOT_AWARDED"

    def test_generated_po_follows_normal_flow(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-FLOW")
        quote = _make_quote(db_session, code="COT-FLOW", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Razón")
        order, _ = ap_service.order_from_quote(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                               code="OC-FLOW")
        ap_service.transition_order(db_session, order=order, target="SUBMITTED")
        ap_service.transition_order(db_session, order=order, target="APPROVED")
        assert order.status == "APPROVED"

    def test_order_copies_terms(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-TERMS")
        quote = _make_quote(db_session, code="COT-TERMS", supplier=supplier, terms="Entrega en 48h")
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Razón")
        order, _ = ap_service.order_from_quote(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                               code="OC-TERMS")
        assert order.terms == "Entrega en 48h"

    def test_quote_dict_shows_order_and_supplier(self, db_session) -> None:
        product = _make_product(db_session)
        supplier = _make_party(db_session, code="SUP-DICT", name="Proveedor Dict")
        quote = _make_quote(db_session, code="COT-DICT", supplier=supplier)
        ap_service.add_quote_line(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                  product_id=str(product.id), quantity=1, unit_price=10)
        ap_service.award_quote(db_session, company_id=COMPANY, quote_id=str(quote.id), reason="Razón")
        order, _ = ap_service.order_from_quote(db_session, company_id=COMPANY, quote_id=str(quote.id),
                                               code="OC-DICT")

        data = ap_service.quote_dict(db_session, quote)
        assert data["order_id"] == str(order.id)
        assert data["supplier_name"] == "Proveedor Dict"
