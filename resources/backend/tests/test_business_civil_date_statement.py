"""Pruebas de fecha de negocio de Caracas en el estado de cuenta."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.purchasing.models import OpenItem
from app.modules.sales import service as sales
from app.modules.sales.models import SalesCreditNote
from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)


def _cliente(db, company_id, marca):
    from app.modules.master_data.models import Party

    p = Party(company_id=company_id, code=f"CR-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    return str(p.id)


def _documento(db, company_id, party_id, *, original="100.00", currency="VED"):
    item = OpenItem(company_id=company_id, party_id=party_id,
                    source_document=f"SALES_INVOICE:{uuid4()}", item_type="RECEIVABLE",
                    currency=currency, original=Decimal(original), applied=Decimal("0.00"),
                    due_date=hoy_de_negocio(), status="OPEN")
    db.add(item)
    db.flush()
    return item


def _credito(db, company_id, customer_id, *, amount="100.00", currency="VED"):
    nota = SalesCreditNote(company_id=company_id, customer_id=customer_id,
                           number=f"NC-{uuid4().hex[:8]}", amount=Decimal(amount),
                           applied=Decimal("0.00"), currency=currency, status="POSTED",
                           cause="Devolución de mercancía", issued_at=datetime.now(UTC))
    db.add(nota)
    db.flush()
    return nota


def test_la_fecha_del_estado_de_cuenta_es_la_de_caracas(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, f"bd{uuid4().hex[:6]}")
        doc = _documento(db, mundo.company_a, x)
        doc.created_at = datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        nota = _credito(db, mundo.company_a, x)
        nota.issued_at = datetime(2026, 10, 28, 3, 40, tzinfo=UTC)
        db.flush()

        estado = sales.customer_statement(db, company_id=mundo.company_a, customer_id=x)

        fechas = {e["type"]: e["date"] for e in estado["entries"]}
        assert fechas["DOCUMENT"] == "2026-10-27"
        assert fechas["CREDIT_NOTE"] == "2026-10-27"
    finally:
        db.close()


def test_dentro_del_mismo_dia_manda_el_instante(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, f"bd{uuid4().hex[:6]}")
        doc = _documento(db, mundo.company_a, x)
        doc.created_at = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)
        nota = _credito(db, mundo.company_a, x)
        nota.issued_at = datetime(2026, 10, 27, 13, 0, tzinfo=UTC)
        db.flush()

        estado = sales.customer_statement(db, company_id=mundo.company_a, customer_id=x)

        assert [e["type"] for e in estado["entries"]] == ["CREDIT_NOTE", "DOCUMENT"]
    finally:
        db.close()


def test_ninguna_fecha_del_estado_lleva_hora(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, f"bd{uuid4().hex[:6]}")
        doc = _documento(db, mundo.company_a, x)
        doc.created_at = datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        nota = _credito(db, mundo.company_a, x)
        nota.issued_at = datetime(2026, 10, 28, 3, 40, tzinfo=UTC)
        db.flush()

        estado = sales.customer_statement(db, company_id=mundo.company_a, customer_id=x)

        assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) for e in estado["entries"] if e["date"] is not None)
    finally:
        db.close()
