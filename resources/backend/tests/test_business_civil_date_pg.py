"""Pruebas de que la fecha de negocio no depende de la zona de sesión de PostgreSQL."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text

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


def test_el_motor_de_la_aplicacion_fija_la_sesion_en_utc(monkeypatch):
    import app.core.database as base_de_datos

    capturado = {}
    monkeypatch.setattr(
        base_de_datos,
        "create_engine",
        lambda url, **kw: capturado.update(url=url, **kw) or object(),
    )
    monkeypatch.setattr(base_de_datos, "_engine", None)
    monkeypatch.setattr(
        base_de_datos,
        "get_settings",
        lambda: SimpleNamespace(db_url="postgresql+psycopg2://usuario@servidor/base"),
    )

    base_de_datos.get_engine()

    assert capturado["connect_args"] == {"options": "-c timezone=UTC"}


def test_sqlite_no_recibe_opciones_de_sesion(monkeypatch):
    import app.core.database as base_de_datos

    capturado = {}
    monkeypatch.setattr(
        base_de_datos,
        "create_engine",
        lambda url, **kw: capturado.update(url=url, **kw) or object(),
    )
    monkeypatch.setattr(base_de_datos, "_engine", None)
    monkeypatch.setattr(
        base_de_datos,
        "get_settings",
        lambda: SimpleNamespace(db_url="sqlite+pysqlite:///:memory:"),
    )

    base_de_datos.get_engine()

    assert "connect_args" not in capturado


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la zona de sesión solo existe en PostgreSQL",
)
@pytest.mark.parametrize("zona", ["UTC", "America/Caracas", "Asia/Tokyo"])
def test_la_fecha_del_estado_de_cuenta_no_depende_de_la_zona_de_sesion(mundo, zona):
    db = mundo.factory()
    try:
        # SET LOCAL limita el cambio a la transacción de la prueba: al cerrar la
        # sesión se deshace y la conexión vuelve al pool sin la zona cambiada.
        db.execute(text(f"SET LOCAL TIME ZONE '{zona}'"))
        assert db.execute(text("SHOW TimeZone")).scalar() == zona

        x = _cliente(db, mundo.company_a, f"bd{uuid4().hex[:6]}")
        doc = _documento(db, mundo.company_a, x)
        doc.created_at = datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        nota = _credito(db, mundo.company_a, x)
        nota.issued_at = datetime(2026, 10, 28, 3, 40, tzinfo=UTC)
        db.flush()
        db.expire_all()

        estado = sales.customer_statement(db, company_id=mundo.company_a, customer_id=x)

        fechas = {e["type"]: e["date"] for e in estado["entries"]}
        assert fechas["DOCUMENT"] == "2026-10-27"
        assert fechas["CREDIT_NOTE"] == "2026-10-27"
    finally:
        db.close()


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la zona de sesión solo existe en PostgreSQL",
)
@pytest.mark.parametrize("zona", ["UTC", "America/Caracas", "Asia/Tokyo"])
def test_el_instante_leido_es_el_mismo_con_cualquier_zona_de_sesion(mundo, zona):
    db = mundo.factory()
    try:
        # SET LOCAL limita el cambio a la transacción de la prueba: al cerrar la
        # sesión se deshace y la conexión vuelve al pool sin la zona cambiada.
        db.execute(text(f"SET LOCAL TIME ZONE '{zona}'"))

        x = _cliente(db, mundo.company_a, f"bd{uuid4().hex[:6]}")
        doc = _documento(db, mundo.company_a, x)
        doc.created_at = datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        db.flush()
        db.expire(doc)

        assert doc.created_at.astimezone(UTC) == datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
    finally:
        db.close()
