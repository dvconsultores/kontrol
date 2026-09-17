"""Spec 028 · delta dirigido: el saldo es `Decimal` exacto, no `float`.

`ADR-D0-001` registra `KQA-100` como defecto CRÍTICO —«`Decimal + float`… que
SQLite no reveló y que rompió factura, pago, cobro»— y la Spec 011 lo corrigió
en las cantidades. El motor de saldos nunca lo recibió: `open_item_balance`
devolvía `round(float(a) - float(b), 6)`, y ese `6` no era una política sino el
margen que hacía falta para que el error binario no se viera.

Estas pruebas existen para que no vuelva. Cada una está escrita con cifras que
**no son representables en binario**: con `float` fallan, con `Decimal` no.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.purchasing import service as ap
from app.modules.purchasing.models import OpenItem
from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)


def _documento(db, company_id, party_id, *, original, applied="0.00", tipo="RECEIVABLE"):
    item = OpenItem(company_id=company_id, party_id=party_id,
                    source_document=f"TEST:{original}-{applied}", item_type=tipo,
                    currency="VED", original=Decimal(original), applied=Decimal(applied),
                    due_date=hoy_de_negocio(), status="OPEN")
    db.add(item)
    db.flush()
    return item


def _cliente(db, company_id, marca):
    from app.modules.master_data.models import Party

    p = Party(company_id=company_id, code=f"CM-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    return str(p.id)


# --------------------------------------------------------------------------- #
# La exactitud que `float` no tiene
# --------------------------------------------------------------------------- #
def test_el_saldo_es_decimal_y_no_float(mundo):
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t1")
        item = _documento(db, mundo.company_a, cli, original="100.00")
        saldo = ap.open_item_balance(item)
        assert isinstance(saldo, Decimal), "el saldo volvió a ser coma flotante"
        assert not isinstance(saldo, float)
    finally:
        db.close()


def test_tres_aplicaciones_de_un_tercio_cierran_el_documento_exactamente(mundo):
    """El caso que `float` no puede pasar.

    `0.10 + 0.20 == 0.30` es falso en binario. Tres aplicaciones de `33.33`
    sobre `99.99` tienen que dejar el documento en cero **exacto** y cerrado;
    con `float` el residuo obligaba a un margen de `1e-6` para disimularlo.
    """
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t2")
        item = _documento(db, mundo.company_a, cli, original="99.99")
        pago = ap.register_payment(db, company_id=mundo.company_a, party_id=cli,
                                   amount=Decimal("99.99"), direction="IN", actor="qa")
        pago.status = "CONFIRMED"
        db.flush()
        for _ in range(3):
            ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                            source_id=str(pago.id), target_open_item_id=str(item.id),
                            amount=Decimal("33.33"), actor="qa")
        db.flush()
        assert ap.open_item_balance(item) == Decimal("0.00")
        assert item.status == "CLOSED", "el documento no cerró por un residuo binario"
    finally:
        db.close()


def test_la_suma_de_centimos_no_arrastra_error(mundo):
    """Diez céntimos y veinte céntimos son treinta céntimos."""
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t3")
        item = _documento(db, mundo.company_a, cli, original="0.30")
        pago = ap.register_payment(db, company_id=mundo.company_a, party_id=cli,
                                   amount=Decimal("0.30"), direction="IN", actor="qa")
        pago.status = "CONFIRMED"
        db.flush()
        ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                        source_id=str(pago.id), target_open_item_id=str(item.id),
                        amount=Decimal("0.10"), actor="qa")
        ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                        source_id=str(pago.id), target_open_item_id=str(item.id),
                        amount=Decimal("0.20"), actor="qa")
        db.flush()
        assert ap.open_item_balance(item) == Decimal("0")
        assert item.status == "CLOSED"
    finally:
        db.close()


def test_no_se_aplica_por_encima_del_saldo_ni_por_un_centimo(mundo):
    """El margen de `1e-6` dejaba pasar céntimos de más."""
    db = mundo.factory()
    try:
        from app.core.errors import ConflictError

        cli = _cliente(db, mundo.company_a, "t4")
        item = _documento(db, mundo.company_a, cli, original="10.00", applied="9.99")
        pago = ap.register_payment(db, company_id=mundo.company_a, party_id=cli,
                                   amount=Decimal("5.00"), direction="IN", actor="qa")
        pago.status = "CONFIRMED"
        db.flush()
        assert ap.open_item_balance(item) == Decimal("0.01")
        with pytest.raises(ConflictError) as exc:
            ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                            source_id=str(pago.id), target_open_item_id=str(item.id),
                            amount=Decimal("0.02"), actor="qa")
        assert exc.value.code == "APPLICATION_EXCEEDS_BALANCE"
    finally:
        db.close()


def test_el_saldo_sobrevive_a_la_ida_y_vuelta_a_la_base(mundo):
    """Lo que Python calcula y lo que PostgreSQL guarda dicen lo mismo."""
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t5")
        item = _documento(db, mundo.company_a, cli, original="1234.56", applied="1234.55")
        db.commit()
        db.expire_all()
        recargado = db.get(OpenItem, str(item.id))
        assert ap.open_item_balance(recargado) == Decimal("0.01")
    finally:
        db.close()


def test_el_aging_suma_en_decimal(mundo):
    """El aging suma dinero: si suma en `float`, arrastra el error."""
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t6")
        for _ in range(3):
            _documento(db, mundo.company_a, cli, original="0.10")
        db.flush()
        resultado = ap.aging(db, company_id=mundo.company_a, party_id=cli,
                             item_type="RECEIVABLE")
        assert Decimal(str(resultado["total"])) == Decimal("0.30"), \
            "el aging arrastró error binario"
    finally:
        db.close()


def test_la_fuente_tambien_se_mide_en_decimal(mundo):
    """Lo que queda por aplicar de un pago es exacto."""
    db = mundo.factory()
    try:
        cli = _cliente(db, mundo.company_a, "t7")
        item = _documento(db, mundo.company_a, cli, original="100.00")
        pago = ap.register_payment(db, company_id=mundo.company_a, party_id=cli,
                                   amount=Decimal("0.30"), direction="IN", actor="qa")
        pago.status = "CONFIRMED"
        db.flush()
        ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                        source_id=str(pago.id), target_open_item_id=str(item.id),
                        amount=Decimal("0.10"), actor="qa")
        ap.apply_source(db, company_id=mundo.company_a, source_type="PAYMENT",
                        source_id=str(pago.id), target_open_item_id=str(item.id),
                        amount=Decimal("0.20"), actor="qa")
        db.flush()
        assert ap._source_available(db, source_type="PAYMENT", source_id=str(pago.id)) == Decimal("0")
    finally:
        db.close()
