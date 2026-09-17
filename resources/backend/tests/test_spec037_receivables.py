"""Spec 037 · cuentas por cobrar: aislamiento, rastro y reverso.

Lo que estas pruebas defienden es la fórmula de la arquitectura funcional §9
—«Saldo = documentos + débitos − cobros − retenciones − créditos»— y las tres
cosas que el camino de CxC no hacía: comprobar el cliente, dejar la fila de la
aplicación y poder revertirla sin borrar nada.

El primer caso es el grave: hasta este ciclo, el crédito de un cliente podía
aplicarse al documento de otro dentro de la misma empresa.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.purchasing import service as ap
from app.modules.purchasing.models import Application, OpenItem
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


def _aplicaciones(db, company_id, note_id):
    return list(db.execute(select(Application).where(
        Application.company_id == company_id,
        Application.source_id == str(note_id))).scalars().all())


# =========================================================================== #
# P0 · el crédito es del cliente que lo tiene
# =========================================================================== #
def test_el_credito_de_un_cliente_no_se_aplica_al_documento_de_otro(mundo):
    """El defecto grave: la misma empresa no basta.

    Hasta este ciclo se comprobaba `company_id` y nada más, así que el crédito
    del cliente X podía pagar la factura del cliente Y.
    """
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x1")
        y = _cliente(db, mundo.company_a, "y1")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        ajeno = _documento(db, mundo.company_a, y, original="100.00")
        db.flush()

        with pytest.raises(ConflictError) as exc:
            sales.apply_credit_note(db, note=nota, target_open_item_id=str(ajeno.id),
                                    amount=Decimal("100.00"), actor="cobranza")
        assert exc.value.code == "CREDIT_CUSTOMER_MISMATCH"

        # Y no se movió nada: ni el documento, ni el crédito, ni el libro.
        assert ap.open_item_balance(ajeno) == Decimal("100.00")
        assert _dec_applied(nota) == Decimal("0.00")
        assert _aplicaciones(db, mundo.company_a, nota.id) == []
    finally:
        db.close()


def _dec_applied(nota) -> Decimal:
    return Decimal(str(nota.applied))


def test_el_credito_se_aplica_al_documento_de_su_propio_cliente(mundo):
    """El camino feliz, con su fila de aplicación."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x2")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()

        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("60.00"), actor="cobranza")
        db.flush()
        assert ap.open_item_balance(propio) == Decimal("40.00")
        assert _dec_applied(nota) == Decimal("60.00")
        assert propio.status == "OPEN"

        apps = _aplicaciones(db, mundo.company_a, nota.id)
        assert len(apps) == 1, "la aplicación no dejó rastro"
        a = apps[0]
        assert a.source_type == "CREDIT" and a.status == "APPLIED"
        assert Decimal(str(a.amount)) == Decimal("60.00")
        assert a.currency == "VED" and Decimal(str(a.rate)) == Decimal(1)
        assert a.date is not None
    finally:
        db.close()


def test_no_se_aplica_un_credito_en_otra_moneda(mundo):
    """Sin política de diferencia cambiaria, aplicar entre monedas es inventar."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x3")
        nota = _credito(db, mundo.company_a, x, amount="100.00", currency="USD")
        propio = _documento(db, mundo.company_a, x, original="100.00", currency="VED")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                    amount=Decimal("50.00"), actor="cobranza")
        assert exc.value.code == "CREDIT_CURRENCY_MISMATCH"
        assert _aplicaciones(db, mundo.company_a, nota.id) == []
    finally:
        db.close()


def test_no_se_aplica_mas_credito_del_que_queda(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x4")
        nota = _credito(db, mundo.company_a, x, amount="50.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("50.00"), actor="cobranza")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                    amount=Decimal("0.01"), actor="cobranza")
        assert exc.value.code == "APPLICATION_EXCEEDS_SOURCE"
    finally:
        db.close()


def test_un_credito_se_reparte_entre_varios_documentos_del_mismo_cliente(mundo):
    """CxC «soporta parcial, múltiple»."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x5")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        uno = _documento(db, mundo.company_a, x, original="60.00")
        dos = _documento(db, mundo.company_a, x, original="60.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(uno.id),
                                amount=Decimal("60.00"), actor="cobranza")
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(dos.id),
                                amount=Decimal("40.00"), actor="cobranza")
        db.flush()
        assert uno.status == "CLOSED"
        assert ap.open_item_balance(dos) == Decimal("20.00")
        assert _dec_applied(nota) == Decimal("100.00")
        assert len(_aplicaciones(db, mundo.company_a, nota.id)) == 2
    finally:
        db.close()


# =========================================================================== #
# El reverso no borra
# =========================================================================== #
def test_el_reverso_no_borra_la_aplicacion_original(mundo):
    """«Los reversos no eliminan; crean evento inverso y reapertura controlada»."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x6")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("60.00"), actor="cobranza")
        db.flush()
        original = _aplicaciones(db, mundo.company_a, nota.id)[0]

        inverso = sales.reverse_credit_application(
            db, company_id=mundo.company_a, application_id=str(original.id),
            reason="El cliente reclamó que no correspondía", actor="jefe")
        db.flush()

        # La original sigue ahí, marcada, no borrada.
        assert db.get(Application, str(original.id)) is not None
        assert original.status == "REVERSED"
        # Y existe su inverso, por el importe contrario.
        assert Decimal(str(inverso.amount)) == Decimal("-60.00")
        assert inverso.status == "REVERSAL"
        # Reapertura controlada: el documento vuelve a tener saldo.
        assert ap.open_item_balance(propio) == Decimal("100.00")
        assert propio.status == "OPEN"
        assert _dec_applied(nota) == Decimal("0.00")
        assert len(_aplicaciones(db, mundo.company_a, nota.id)) == 2
    finally:
        db.close()


def test_una_aplicacion_no_se_revierte_dos_veces(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x7")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("60.00"), actor="cobranza")
        db.flush()
        original = _aplicaciones(db, mundo.company_a, nota.id)[0]
        sales.reverse_credit_application(db, company_id=mundo.company_a,
                                         application_id=str(original.id),
                                         reason="Primera vez", actor="jefe")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            sales.reverse_credit_application(db, company_id=mundo.company_a,
                                             application_id=str(original.id),
                                             reason="Segunda vez", actor="jefe")
        assert exc.value.code == "APPLICATION_ALREADY_REVERSED"
        assert ap.open_item_balance(propio) == Decimal("100.00"), "se reabrió dos veces"
    finally:
        db.close()


def test_revertir_exige_motivo(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x8")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("10.00"), actor="cobranza")
        db.flush()
        original = _aplicaciones(db, mundo.company_a, nota.id)[0]
        with pytest.raises(KontrolError) as exc:
            sales.reverse_credit_application(db, company_id=mundo.company_a,
                                             application_id=str(original.id),
                                             reason="   ", actor="jefe")
        assert exc.value.code == "REVERSAL_REASON_REQUIRED"
    finally:
        db.close()


def test_no_se_revierte_una_aplicacion_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "x9")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(propio.id),
                                amount=Decimal("10.00"), actor="cobranza")
        db.flush()
        original = _aplicaciones(db, mundo.company_a, nota.id)[0]
        with pytest.raises(NotFoundError):
            sales.reverse_credit_application(db, company_id=mundo.company_b,
                                             application_id=str(original.id),
                                             reason="Desde otra empresa", actor="intruso")
    finally:
        db.close()


# =========================================================================== #
# El saldo del cliente: la fórmula de la arquitectura funcional §9
# =========================================================================== #
def test_el_saldo_del_cliente_resta_los_creditos_sin_aplicar(mundo):
    """«Saldo = documentos + débitos − cobros − retenciones − créditos».

    Un crédito que todavía no se ha imputado a ningún documento **ya** resta del
    saldo del cliente: eso es lo que significa tener saldo a favor.
    """
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "xa")
        _documento(db, mundo.company_a, x, original="100.00")
        nota = _credito(db, mundo.company_a, x, amount="120.00")
        db.commit()
        estado = sales.customer_balance(db, company_id=mundo.company_a, customer_id=x)
        assert Decimal(estado["documents"]) == Decimal("100.00")
        assert Decimal(estado["credits"]) == Decimal("120.00")
        # 100 − 120 = −20: el cliente tiene veinte a favor.
        assert Decimal(estado["balance"]) == Decimal("-20.00")
        assert Decimal(estado["credit_available"]) == Decimal("120.00")
        assert nota is not None
    finally:
        db.close()


def test_aplicar_el_credito_no_lo_resta_dos_veces(mundo):
    """P0 del doble conteo: el crédito resta una vez, no dos.

    Al aplicarlo, el documento baja **y** el crédito disponible baja. El saldo
    neto del cliente no puede moverse por el hecho de imputarlo: imputar no
    crea ni destruye dinero.
    """
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "xb")
        doc = _documento(db, mundo.company_a, x, original="100.00")
        nota = _credito(db, mundo.company_a, x, amount="30.00")
        db.commit()
        antes = sales.customer_balance(db, company_id=mundo.company_a, customer_id=x)
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(doc.id),
                                amount=Decimal("30.00"), actor="cobranza")
        db.commit()
        despues = sales.customer_balance(db, company_id=mundo.company_a, customer_id=x)
        assert Decimal(antes["balance"]) == Decimal("70.00")
        assert Decimal(despues["balance"]) == Decimal("70.00"), \
            "imputar el crédito movió el saldo neto: se restó dos veces"
        assert Decimal(despues["credit_available"]) == Decimal("0.00")
    finally:
        db.close()


def test_el_estado_de_cuenta_reconstruye_la_cronologia(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "xc")
        doc = _documento(db, mundo.company_a, x, original="100.00")
        nota = _credito(db, mundo.company_a, x, amount="40.00")
        db.flush()
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(doc.id),
                                amount=Decimal("40.00"), actor="cobranza")
        db.commit()
        estado = sales.customer_statement(db, company_id=mundo.company_a, customer_id=x)
        tipos = [x["type"] for x in estado["entries"]]
        assert "DOCUMENT" in tipos and "CREDIT_NOTE" in tipos and "APPLICATION" in tipos
        assert Decimal(estado["balance"]) == Decimal("60.00")
    finally:
        db.close()


def test_el_saldo_del_cliente_no_cruza_empresas(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "xd")
        _documento(db, mundo.company_a, x, original="100.00")
        db.commit()
        ajeno = sales.customer_balance(db, company_id=mundo.company_b, customer_id=x)
        assert Decimal(ajeno["balance"]) == Decimal("0")
    finally:
        db.close()


# =========================================================================== #
# La API: la empresa la manda el contexto y el cliente se comprueba siempre
# =========================================================================== #
def test_la_api_bloquea_la_aplicacion_entre_clientes(mundo):
    """El P0 por HTTP: error de dominio, no 500, y sin efecto económico."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api1")
        y = _cliente(db, mundo.company_a, "api2")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        ajeno = _documento(db, mundo.company_a, y, original="100.00")
        db.commit()
        nota_id, ajeno_id = str(nota.id), str(ajeno.id)
    finally:
        db.close()

    r = mundo.post(f"/sales/cxc/creditos/{nota_id}/aplicar", "admin", mundo.company_a, {"target_open_item_id": ajeno_id, "amount": "100.00"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "CREDIT_CUSTOMER_MISMATCH"

    db = mundo.factory()
    try:
        assert ap.open_item_balance(db.get(OpenItem, ajeno_id)) == Decimal("100.00")
        assert _aplicaciones(db, mundo.company_a, nota_id) == []
    finally:
        db.close()


def test_la_api_aplica_y_devuelve_el_estado_real(mundo):
    """No vale «éxito»: la respuesta dice cómo quedó el dominio."""
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api3")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.commit()
        nota_id, propio_id = str(nota.id), str(propio.id)
    finally:
        db.close()

    r = mundo.post(f"/sales/cxc/creditos/{nota_id}/aplicar", "admin", mundo.company_a, {"target_open_item_id": propio_id, "amount": "60.00"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert Decimal(cuerpo["target_outstanding"]) == Decimal("40.00")
    assert Decimal(cuerpo["credit_remaining"]) == Decimal("40.00")
    assert cuerpo["target_status"] == "OPEN"

    apps = mundo.get(f"/sales/cxc/documentos/{propio_id}/aplicaciones", "admin", mundo.company_a).json()
    assert len(apps["items"]) == 1 and apps["items"][0]["source_type"] == "CREDIT"


def test_la_api_no_aplica_un_credito_de_otra_empresa(mundo):  # noqa: D103
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api4")
        nota = _credito(db, mundo.company_a, x, amount="50.00")
        propio = _documento(db, mundo.company_a, x, original="50.00")
        db.commit()
        nota_id, propio_id = str(nota.id), str(propio.id)
    finally:
        db.close()

    r = mundo.post(f"/sales/cxc/creditos/{nota_id}/aplicar", "admin", mundo.company_b, {"target_open_item_id": propio_id, "amount": "10.00"})
    assert r.status_code == 404, r.text


def test_la_api_revierte_sin_borrar(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api5")
        nota = _credito(db, mundo.company_a, x, amount="100.00")
        propio = _documento(db, mundo.company_a, x, original="100.00")
        db.commit()
        nota_id, propio_id = str(nota.id), str(propio.id)
    finally:
        db.close()

    mundo.post(f"/sales/cxc/creditos/{nota_id}/aplicar", "admin", mundo.company_a, {"target_open_item_id": propio_id, "amount": "60.00"})
    apps = mundo.get(f"/sales/cxc/documentos/{propio_id}/aplicaciones", "admin", mundo.company_a).json()
    original = apps["items"][0]["id"]

    r = mundo.post(f"/sales/cxc/aplicaciones/{original}/revertir", "admin", mundo.company_a, {"reason": "No correspondía"})
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["amount"]) == Decimal("-60.00")

    despues = mundo.get(f"/sales/cxc/documentos/{propio_id}/aplicaciones", "admin", mundo.company_a).json()
    estados = sorted(x["status"] for x in despues["items"])
    assert estados == ["REVERSAL", "REVERSED"], "el reverso borró la aplicación original"

    # Y no se puede revertir dos veces.
    otra = mundo.post(f"/sales/cxc/aplicaciones/{original}/revertir", "admin", mundo.company_a, {"reason": "Otra vez"})
    assert otra.status_code == 409
    assert otra.json()["code"] == "APPLICATION_ALREADY_REVERSED"


def test_la_api_no_crea_cobros_ni_movimientos_de_tesoreria(mundo):
    """Aplicar un crédito no es cobrar: no entra dinero."""
    from app.modules.purchasing.models import Payment

    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api6")
        nota = _credito(db, mundo.company_a, x, amount="40.00")
        propio = _documento(db, mundo.company_a, x, original="40.00")
        db.commit()
        nota_id, propio_id = str(nota.id), str(propio.id)
        pagos_antes = len(db.execute(select(Payment).where(
            Payment.company_id == mundo.company_a)).scalars().all())
    finally:
        db.close()

    mundo.post(f"/sales/cxc/creditos/{nota_id}/aplicar", "admin", mundo.company_a, {"target_open_item_id": propio_id, "amount": "40.00"})

    db = mundo.factory()
    try:
        pagos = db.execute(select(Payment).where(
            Payment.company_id == mundo.company_a)).scalars().all()
        assert len(pagos) == pagos_antes, "aplicar un crédito creó un cobro"
    finally:
        db.close()


def test_la_api_expone_el_saldo_y_la_cronologia(mundo):
    db = mundo.factory()
    try:
        x = _cliente(db, mundo.company_a, "api7")
        _documento(db, mundo.company_a, x, original="100.00")
        _credito(db, mundo.company_a, x, amount="30.00")
        db.commit()
        cid = x
    finally:
        db.close()

    saldo = mundo.get(f"/sales/cxc/clientes/{cid}/saldo", "admin", mundo.company_a).json()
    assert Decimal(saldo["balance"]) == Decimal("70.00")
    estado = mundo.get(f"/sales/cxc/clientes/{cid}/estado-de-cuenta", "admin", mundo.company_a).json()
    assert len(estado["entries"]) == 2
    creditos = mundo.get(f"/sales/cxc/clientes/{cid}/creditos", "admin", mundo.company_a).json()
    assert len(creditos["items"]) == 1
    assert Decimal(creditos["items"][0]["available"]) == Decimal("30.00")
