"""Spec 038 · política cambiaria, conversión explícita y reembolso.

Dos decisiones expresas del owner abren este ciclo: el reembolso de un crédito a
favor se soporta, y la política cambiaria es parametrizable con conversión
explícita. La arquitectura funcional §9 dejaba el hueco a propósito —«según
política»— y no había política ninguna.

Lo que estas pruebas defienden, por orden de gravedad: que la tasa **no se
invente**, que el mismo crédito **no se gaste dos veces**, y que cambiar de
moneda sea un hecho con su procedencia y no un número escondido.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.sales import service as sz
from app.modules.sales.models import SalesCreditNote
from app.modules.treasury import service as tz
from app.modules.treasury.models import BankTransaction, TreasuryRateSnapshot

pytest_plugins = ("tests.conftest_multicompany",)


def _cliente(db, company_id, marca):
    from app.modules.master_data.models import Party

    p = Party(company_id=company_id, code=f"CT-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    return str(p.id)


def _cuenta(db, mundo, *, moneda="VED", saldo="0.00", marca=None):
    marca = marca or uuid4().hex[:6]
    banco = tz.create_bank(db, company_id=mundo.company_a, code=f"BK-{marca}",
                           name=f"Banco {marca}", actor="qa")
    cuenta = tz.create_account(db, company_id=mundo.company_a, bank_id=str(banco.id),
                               code=f"AC-{marca}", name=f"Cuenta {marca}", currency=moneda,
                               actor="qa")
    if Decimal(saldo) > 0:
        tz.create_bank_transaction(db, company_id=mundo.company_a, account_id=str(cuenta.id),
                                   direction="IN", amount=Decimal(saldo), currency=moneda,
                                   source="ADJUSTMENT", reference="apertura", actor="qa")
    db.flush()
    return cuenta


def _sin_politica(db, mundo):
    """Retira cualquier política activa: la base del arnés es compartida."""
    from app.modules.treasury.models import TreasuryFxPolicy

    for p in db.execute(select(TreasuryFxPolicy).where(
            TreasuryFxPolicy.company_id == mundo.company_a,
            TreasuryFxPolicy.status == "ACTIVE")).scalars().all():
        p.status = "SUPERSEDED"
    db.flush()


def _politica(db, mundo, *, cross=True, manual=False, refund=True, desde=None):
    # La base del arnés es compartida entre pruebas: si otra dejó una política
    # activa, sería ella la que gobernara y este caso probaría otra cosa.
    _sin_politica(db, mundo)
    p = tz.create_fx_policy(db, company_id=mundo.company_a,
                            policy_code=f"POL-{uuid4().hex[:6]}",
                            functional_currency="VED",
                            effective_from=desde or date(2020, 1, 1),
                            rate_source="BCV", rate_type="OFICIAL",
                            allow_cross_currency=cross, allow_manual_rate=manual,
                            allow_refund=refund,
                            authority_reference="Pendiente de validación legal (D0-07)",
                            actor="qa")
    tz.activate_fx_policy(db, company_id=mundo.company_a, policy_id=str(p.id), actor="qa")
    db.flush()
    return p


def _divisa() -> str:
    """Una divisa distinta por prueba.

    La base del arnés es compartida, y desde la Spec 013 dos observaciones con
    las mismas coordenadas ya no conviven: antes se duplicaban en silencio y el
    desempate lo decidía PostgreSQL. Compartir «USD» entre pruebas dejó de ser
    inocuo el día que el sistema empezó a exigir unicidad.
    """
    return f"D{uuid4().hex[:2].upper()}"


def _tasa(db, mundo, *, codigo="USD", valor="40.00", dia=None):
    cur = tz.create_currency(db, company_id=mundo.company_a, code=codigo, name=codigo,
                             actor="qa")
    tz.set_exchange_rate(db, company_id=mundo.company_a, currency_id=str(cur.id),
                         rate_date=dia or date.today(), rate=Decimal(valor), source="BCV",
                         actor="qa")
    db.flush()
    return cur


def _credito(db, mundo, customer_id, *, amount="100.00", currency="VED", applied="0.00"):
    nota = SalesCreditNote(company_id=mundo.company_a, customer_id=customer_id,
                           number=f"NC-{uuid4().hex[:8]}", amount=Decimal(amount),
                           applied=Decimal(applied), currency=currency, status="POSTED",
                           cause="Devolución de mercancía", issued_at=datetime.now(UTC),
                           refund_reserved=Decimal("0.00"), refunded=Decimal("0.00"))
    db.add(nota)
    db.flush()
    return nota


# =========================================================================== #
# La tasa no se inventa
# =========================================================================== #
def test_sin_tasa_registrada_la_conversion_se_niega(mundo):
    """Devolvía **1,0** cuando no había tasa. Un pago en divisa al cambio uno."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        with pytest.raises(ConflictError) as exc:
            tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                     source_currency=_divisa(), target_currency="VED",
                                     actor="tesorero")
        assert exc.value.code == "RATE_NOT_AVAILABLE"
    finally:
        db.close()


def test_la_instantanea_guarda_la_procedencia_entera(mundo):
    db = mundo.factory()
    try:
        politica = _politica(db, mundo)
        _tasa(db, mundo, valor="40.00")
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                        source_currency="USD", target_currency="VED",
                                        actor="tesorero")
        db.flush()
        assert Decimal(str(snap.rate)) == Decimal("40.00000000")
        assert snap.rate_source == "BCV"
        assert snap.origin == "REGISTERED"
        assert snap.rate_date == date.today()
        assert snap.policy_version == politica.version
        assert snap.exchange_rate_id is not None, "no dice de qué fila salió"
    finally:
        db.close()


def test_la_tasa_manual_exige_politica_y_motivo(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, manual=False)
        with pytest.raises(ConflictError) as exc:
            tz.capture_rate_snapshot(db, company_id=mundo.company_a, source_currency="USD",
                                     target_currency="VED", manual_rate=Decimal("50"),
                                     manual_reason="acordada", actor="tesorero")
        assert exc.value.code == "MANUAL_RATE_NOT_ALLOWED"
    finally:
        db.close()


def test_una_tasa_de_hoy_no_valora_una_operacion_de_ayer(mundo):
    """Tomaba la más reciente sin mirar la fecha."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        ayer = date.today() - timedelta(days=1)
        cur = _tasa(db, mundo, valor="40.00", dia=ayer)
        tz.set_exchange_rate(db, company_id=mundo.company_a, currency_id=str(cur.id),
                             rate_date=date.today(), rate=Decimal("60.00"), source="BCV",
                             actor="qa")
        db.flush()
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a, source_currency="USD",
                                        target_currency="VED", on_date=ayer, actor="tesorero")
        assert Decimal(str(snap.rate)) == Decimal("40.00000000"), \
            "usó la tasa de hoy para una operación de ayer"
    finally:
        db.close()


# =========================================================================== #
# Cambiar de moneda es un hecho
# =========================================================================== #
def test_la_conversion_deja_dos_movimientos_y_su_instantanea(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        divisa = _divisa()
        _tasa(db, mundo, codigo=divisa, valor="40.00")
        usd = _cuenta(db, mundo, moneda=divisa, saldo="100.00")
        ved = _cuenta(db, mundo, moneda="VED", saldo="0.00")
        conv = tz.convert_currency(db, company_id=mundo.company_a,
                                   source_account_id=str(usd.id),
                                   target_account_id=str(ved.id),
                                   source_amount=Decimal("10.00"), actor="tesorero")
        db.commit()
        assert Decimal(str(conv.source_amount)) == Decimal("10.00")
        assert Decimal(str(conv.target_amount)) == Decimal("400.00")
        assert tz.account_balance(db, company_id=mundo.company_a, account_id=str(usd.id)) == Decimal("90.00")
        assert tz.account_balance(db, company_id=mundo.company_a, account_id=str(ved.id)) == Decimal("400.00")
        # Los dos movimientos apuntan a la misma instantánea.
        movs = db.execute(select(BankTransaction).where(
            BankTransaction.company_id == mundo.company_a,
            BankTransaction.source == "FX")).scalars().all()
        assert len(movs) == 2
        assert {m.rate_snapshot_id for m in movs} == {str(conv.rate_snapshot_id)}
    finally:
        db.close()


def test_sin_politica_no_hay_conversion(mundo):
    db = mundo.factory()
    try:
        _sin_politica(db, mundo)
        divisa = _divisa()
        _tasa(db, mundo, codigo=divisa, valor="40.00")
        usd = _cuenta(db, mundo, moneda=divisa, saldo="100.00")
        ved = _cuenta(db, mundo, moneda="VED")
        with pytest.raises(ConflictError) as exc:
            tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(usd.id),
                                target_account_id=str(ved.id), source_amount=Decimal("10"),
                                actor="tesorero")
        assert exc.value.code == "CROSS_CURRENCY_NOT_ALLOWED"
    finally:
        db.close()


def test_no_se_convierte_sin_fondos(mundo):
    """§71: sin política de descubierto declarada, se bloquea."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        divisa = _divisa()
        _tasa(db, mundo, codigo=divisa, valor="40.00")
        usd = _cuenta(db, mundo, moneda=divisa, saldo="5.00")
        ved = _cuenta(db, mundo, moneda="VED")
        with pytest.raises(ConflictError) as exc:
            tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(usd.id),
                                target_account_id=str(ved.id), source_amount=Decimal("10"),
                                actor="tesorero")
        assert exc.value.code == "INSUFFICIENT_FUNDS"
    finally:
        db.close()


def test_convertir_dos_veces_con_la_misma_clave_no_mueve_dos_veces(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        divisa = _divisa()
        _tasa(db, mundo, codigo=divisa, valor="40.00")
        usd = _cuenta(db, mundo, moneda=divisa, saldo="100.00")
        ved = _cuenta(db, mundo, moneda="VED")
        clave = f"conv-{uuid4().hex[:8]}"
        uno = tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(usd.id),
                                  target_account_id=str(ved.id), source_amount=Decimal("10"),
                                  idempotency_key=clave, actor="tesorero")
        dos = tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(usd.id),
                                  target_account_id=str(ved.id), source_amount=Decimal("10"),
                                  idempotency_key=clave, actor="tesorero")
        db.commit()
        assert str(uno.id) == str(dos.id)
        assert tz.account_balance(db, company_id=mundo.company_a, account_id=str(usd.id)) == Decimal("90.00")
    finally:
        db.close()


def test_dos_cuentas_de_la_misma_moneda_no_son_una_conversion(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        a = _cuenta(db, mundo, moneda="VED", saldo="100.00")
        b = _cuenta(db, mundo, moneda="VED")
        with pytest.raises(ConflictError) as exc:
            tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(a.id),
                                target_account_id=str(b.id), source_amount=Decimal("10"),
                                actor="tesorero")
        assert exc.value.code == "SAME_CURRENCY_CONVERSION"
    finally:
        db.close()


# =========================================================================== #
# El reembolso: el mismo crédito no se gasta dos veces
# =========================================================================== #
def test_solicitar_reserva_el_credito_y_lo_quita_de_lo_aplicable(mundo):
    """§11: reservar 60 de 100 deja 40 disponibles para aplicar."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r1")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        refund = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                                    amount=Decimal("60.00"), reason="El cliente lo pidió",
                                    account_id=str(cuenta.id), actor="cobranza")
        db.commit()
        assert refund.status == "REQUESTED"
        assert Decimal(str(nota.refund_reserved)) == Decimal("60.00")
        assert tz.refundable_credit(db, nota) == Decimal("40.00")
    finally:
        db.close()


def test_lo_reservado_no_puede_aplicarse_a_una_cuenta_por_cobrar(mundo):
    """El P0 del doble gasto: reservado y aplicable son excluyentes."""
    db = mundo.factory()
    try:
        from datetime import date as _date

        from app.modules.purchasing.models import OpenItem
        from app.modules.sales import service as sales

        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r2")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                          amount=Decimal("60.00"), reason="Devolución solicitada",
                          account_id=str(cuenta.id), actor="cobranza")
        db.flush()

        doc = OpenItem(company_id=mundo.company_a, party_id=x,
                       source_document=f"SALES_INVOICE:{uuid4()}", item_type="RECEIVABLE",
                       currency="VED", original=Decimal("100.00"), applied=Decimal("0.00"),
                       due_date=_date.today(), status="OPEN")
        db.add(doc)
        db.flush()
        # Quedan 40 aplicables: pedir 60 tiene que fallar.
        with pytest.raises(ConflictError) as exc:
            sales.apply_credit_note(db, note=nota, target_open_item_id=str(doc.id),
                                    amount=Decimal("60.00"), actor="cobranza")
        assert exc.value.code == "APPLICATION_EXCEEDS_SOURCE"
        # Y 40 sí se puede.
        sales.apply_credit_note(db, note=nota, target_open_item_id=str(doc.id),
                                amount=Decimal("40.00"), actor="cobranza")
        db.commit()
        assert Decimal(str(nota.applied)) == Decimal("40.00")
        assert tz.refundable_credit(db, nota) == Decimal("0.00")
    finally:
        db.close()


def test_denegar_libera_la_reserva(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r3")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        refund = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                                    amount=Decimal("60.00"), reason="Petición",
                                    account_id=str(cuenta.id), actor="cobranza")
        db.flush()
        with pytest.raises(KontrolError) as exc:
            tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                             approved=False, actor="jefe")
        assert exc.value.code == "REFUND_REJECTION_REASON_REQUIRED"
        tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                         approved=False, reason="No procede", actor="jefe")
        db.commit()
        assert refund.status == "REJECTED"
        assert Decimal(str(nota.refund_reserved)) == Decimal("0.00")
        assert tz.refundable_credit(db, nota) == Decimal("100.00")
    finally:
        db.close()


def test_ejecutar_saca_el_dinero_y_consume_el_credito(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r4")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        refund = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                                    amount=Decimal("60.00"), reason="Petición",
                                    account_id=str(cuenta.id), actor="cobranza")
        tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                         approved=True, actor="jefe")
        tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                         actor="tesorero")
        db.commit()
        assert refund.status == "SETTLED" and refund.movement_id
        assert tz.account_balance(db, company_id=mundo.company_a,
                                  account_id=str(cuenta.id)) == Decimal("440.00")
        assert Decimal(str(nota.refund_reserved)) == Decimal("0.00")
        assert Decimal(str(nota.refunded)) == Decimal("60.00")
        # Lo devuelto no vuelve a estar disponible.
        assert tz.refundable_credit(db, nota) == Decimal("40.00")
    finally:
        db.close()


def test_no_se_ejecuta_sin_aprobar(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r5")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        refund = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                                    amount=Decimal("10.00"), reason="Petición",
                                    account_id=str(cuenta.id), actor="cobranza")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                             actor="tesorero")
        assert exc.value.code == "REFUND_NOT_APPROVED"
    finally:
        db.close()


def test_ejecutar_dos_veces_no_saca_el_dinero_dos_veces(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r6")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        refund = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                                    amount=Decimal("30.00"), reason="Petición",
                                    account_id=str(cuenta.id), actor="cobranza")
        tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(refund.id),
                         approved=True, actor="jefe")
        tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(refund.id), actor="t")
        tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(refund.id), actor="t")
        db.commit()
        assert tz.account_balance(db, company_id=mundo.company_a,
                                  account_id=str(cuenta.id)) == Decimal("470.00")
        assert Decimal(str(nota.refunded)) == Decimal("30.00")
    finally:
        db.close()


def test_no_se_devuelve_mas_credito_del_que_queda(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r7")
        nota = _credito(db, mundo, x, amount="100.00", applied="80.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        with pytest.raises(ConflictError) as exc:
            tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                              amount=Decimal("30.00"), reason="Petición",
                              account_id=str(cuenta.id), actor="cobranza")
        assert exc.value.code == "REFUND_EXCEEDS_CREDIT"
    finally:
        db.close()


def test_sin_politica_que_lo_permita_no_hay_reembolso(mundo):
    db = mundo.factory()
    try:
        _sin_politica(db, mundo)
        _politica(db, mundo, refund=False)
        x = _cliente(db, mundo.company_a, "r8")
        nota = _credito(db, mundo, x, amount="100.00")
        with pytest.raises(ConflictError) as exc:
            tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                              amount=Decimal("10.00"), reason="Petición", actor="cobranza")
        assert exc.value.code == "REFUND_NOT_ALLOWED"
    finally:
        db.close()


def test_no_se_devuelve_desde_una_cuenta_de_otra_moneda(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "r9")
        nota = _credito(db, mundo, x, amount="100.00", currency="VED")
        cuenta = _cuenta(db, mundo, moneda="USD", saldo="500.00")
        with pytest.raises(ConflictError) as exc:
            tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                              amount=Decimal("10.00"), reason="Petición",
                              account_id=str(cuenta.id), actor="cobranza")
        assert exc.value.code == "REFUND_CURRENCY_MISMATCH"
    finally:
        db.close()


def test_no_se_devuelve_un_credito_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "ra")
        nota = _credito(db, mundo, x, amount="100.00")
        db.commit()
        with pytest.raises(NotFoundError):
            tz.request_refund(db, company_id=mundo.company_b, credit_note_id=str(nota.id),
                              amount=Decimal("10.00"), reason="Desde otra empresa", actor="x")
    finally:
        db.close()


# =========================================================================== #
# El dinero, exacto
# =========================================================================== #
def test_el_arqueo_no_arrastra_error_binario(mundo):
    """`round(float(a) - float(b), 6)`: misma familia que `KQA-100`."""
    db = mundo.factory()
    try:
        caja = tz.create_cashbox(db, company_id=mundo.company_a, code=f"CJ-{uuid4().hex[:6]}",
                                 name="Caja", currency="VED", actor="qa")
        ses = tz.open_session(db, company_id=mundo.company_a, cashbox_id=str(caja.id),
                              opened_amount=Decimal("0.30"), actor="cajero")
        tz.add_session_movement(db, session_id=str(ses.id), movement_type="IN",
                                amount=Decimal("0.10"), source="ADJUSTMENT")
        tz.add_session_movement(db, session_id=str(ses.id), movement_type="IN",
                                amount=Decimal("0.20"), source="ADJUSTMENT")
        db.flush()
        tz.arqueo_session(db, session_id=str(ses.id), counted_amount=Decimal("0.60"),
                          actor="cajero")
        db.commit()
        assert Decimal(str(ses.difference)) == Decimal("0.00"), \
            "el arqueo arrastró error de coma flotante"
    finally:
        db.close()


def test_el_saldo_de_la_cuenta_sale_de_los_movimientos(mundo):
    db = mundo.factory()
    try:
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="0.30")
        tz.create_bank_transaction(db, company_id=mundo.company_a, account_id=str(cuenta.id),
                                   direction="OUT", amount=Decimal("0.10"), currency="VED",
                                   source="ADJUSTMENT", actor="qa")
        tz.create_bank_transaction(db, company_id=mundo.company_a, account_id=str(cuenta.id),
                                   direction="OUT", amount=Decimal("0.20"), currency="VED",
                                   source="ADJUSTMENT", actor="qa")
        db.commit()
        assert tz.account_balance(db, company_id=mundo.company_a,
                                  account_id=str(cuenta.id)) == Decimal("0.00")
    finally:
        db.close()


def test_la_posicion_de_caja_no_mezcla_monedas(mundo):
    """Mostrar un equivalente exigiría una conversión que nadie hizo."""
    db = mundo.factory()
    try:
        antes = {x["currency"]: Decimal(x["balance"])
                 for x in tz.cash_position(db, company_id=mundo.company_a)["by_currency"]}
        _cuenta(db, mundo, moneda="VED", saldo="100.00")
        _cuenta(db, mundo, moneda="USD", saldo="50.00")
        db.commit()
        pos = tz.cash_position(db, company_id=mundo.company_a)
        monedas = {x["currency"]: Decimal(x["balance"]) for x in pos["by_currency"]}
        assert monedas["VED"] - antes.get("VED", Decimal(0)) == Decimal("100.00")
        assert monedas["USD"] - antes.get("USD", Decimal(0)) == Decimal("50.00")
        # Las monedas no se suman entre sí: mostrar un equivalente exigiría una
        # conversión que nadie ha hecho.
        assert "total" not in pos, "sumó monedas distintas en un solo número"
    finally:
        db.close()


def test_la_politica_anterior_no_se_borra_al_activar_otra(mundo):
    db = mundo.factory()
    try:
        primera = _politica(db, mundo, desde=date(2020, 1, 1))
        segunda = tz.create_fx_policy(db, company_id=mundo.company_a,
                                      policy_code=primera.policy_code,
                                      functional_currency="VED",
                                      effective_from=date(2026, 1, 1), actor="qa")
        tz.activate_fx_policy(db, company_id=mundo.company_a, policy_id=str(segunda.id),
                              actor="qa")
        db.commit()
        assert primera.status == "SUPERSEDED", "la política anterior se borró"
        assert primera.effective_to == date(2026, 1, 1)
        assert segunda.version == primera.version + 1
    finally:
        db.close()


def test_la_instantanea_sobrevive_al_cambio_de_tasa(mundo):
    """Una tasa futura no cambia una operación pasada."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        divisa = _divisa()
        cur = _tasa(db, mundo, codigo=divisa, valor="40.00")
        usd = _cuenta(db, mundo, moneda=divisa, saldo="100.00")
        ved = _cuenta(db, mundo, moneda="VED")
        conv = tz.convert_currency(db, company_id=mundo.company_a, source_account_id=str(usd.id),
                                   target_account_id=str(ved.id), source_amount=Decimal("10"),
                                   actor="tesorero")
        db.commit()
        tz.set_exchange_rate(db, company_id=mundo.company_a, currency_id=str(cur.id),
                             rate_date=date.today() + timedelta(days=1), rate=Decimal("80.00"),
                             source="BCV", actor="qa")
        db.commit()
        snap = db.get(TreasuryRateSnapshot, str(conv.rate_snapshot_id))
        assert Decimal(str(snap.rate)) == Decimal("40.00000000")
        assert Decimal(str(conv.target_amount)) == Decimal("400.00")
    finally:
        db.close()


# =========================================================================== #
# La API: la empresa la manda el contexto
# =========================================================================== #
def test_la_api_recorre_el_reembolso_entero(mundo):
    """Solicitar, aprobar y ejecutar, con el estado real en cada respuesta."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "api1")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        db.commit()
        nota_id, cuenta_id = str(nota.id), str(cuenta.id)
    finally:
        db.close()

    r = mundo.post("/treasury/refunds", "admin", mundo.company_a,
                   {"credit_note_id": nota_id, "amount": "60.00",
                    "reason": "El cliente lo pidió", "account_id": cuenta_id})
    assert r.status_code == 200, r.text
    refund_id = r.json()["id"]
    assert r.json()["status"] == "REQUESTED"

    r = mundo.post(f"/treasury/refunds/{refund_id}/decide", "admin", mundo.company_a,
                   {"approved": True})
    assert r.status_code == 200 and r.json()["status"] == "APPROVED"

    r = mundo.post(f"/treasury/refunds/{refund_id}/settle", "admin", mundo.company_a, {})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SETTLED" and r.json()["movement_id"]

    saldo = mundo.get(f"/treasury/accounts/{cuenta_id}/balance", "admin", mundo.company_a).json()
    assert Decimal(saldo["balance"]) == Decimal("440.00")


def test_la_api_no_devuelve_un_credito_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "api2")
        nota = _credito(db, mundo, x, amount="50.00")
        db.commit()
        nota_id = str(nota.id)
    finally:
        db.close()
    r = mundo.post("/treasury/refunds", "admin", mundo.company_b,
                   {"credit_note_id": nota_id, "amount": "10.00", "reason": "Desde otra empresa"})
    assert r.status_code == 404, r.text


def test_la_api_niega_la_conversion_sin_tasa(mundo):
    """No hay tasa por defecto: negarse es la respuesta correcta.

    La moneda existe en el catálogo y nadie le registró tasa; es el caso
    hostil exacto. El código va marcado porque la base es compartida y
    otras pruebas sí cotizan el dólar.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        codigo = f"Q{uuid4().hex[:2].upper()}"
        tz.create_currency(db, company_id=mundo.company_a, code=codigo, name=codigo, actor="qa")
        muda = _cuenta(db, mundo, moneda=codigo, saldo="100.00")
        ved = _cuenta(db, mundo, moneda="VED")
        db.commit()
        usd_id, ved_id = str(muda.id), str(ved.id)
    finally:
        db.close()
    r = mundo.post("/treasury/fx-conversions", "admin", mundo.company_a,
                   {"source_account_id": usd_id, "target_account_id": ved_id,
                    "source_amount": "10.00"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RATE_NOT_AVAILABLE"


def test_la_api_expone_la_posicion_sin_mezclar_monedas(mundo):
    db = mundo.factory()
    try:
        _cuenta(db, mundo, moneda="VED", saldo="10.00")
        db.commit()
    finally:
        db.close()
    r = mundo.get("/treasury/cash-position", "admin", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert "by_currency" in cuerpo and "accounts" in cuerpo
    assert "total" not in cuerpo


def test_la_api_activa_una_politica_y_sustituye_la_anterior(mundo):
    marca = uuid4().hex[:6]
    r = mundo.post("/treasury/fx-policies", "admin", mundo.company_a,
                   {"policy_code": f"API-{marca}", "functional_currency": "VED",
                    "effective_from": "2020-01-01", "allow_cross_currency": True,
                    "allow_refund": True,
                    "authority_reference": "Pendiente de validación legal (D0-07)"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DRAFT", "la política nació activa sin aprobarse"
    pid = r.json()["id"]
    r = mundo.post(f"/treasury/fx-policies/{pid}/activate", "admin", mundo.company_a, {})
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"


def test_el_credito_reservado_deja_de_ofrecerse_como_disponible(mundo):
    """Delta al dueño (Spec 037): reservar para reembolso no es tener.

    El desplegable de «aplicar crédito» leía `amount - applied` y no veía la
    reserva. Enseñaba cien cuando quedaban cuarenta: el mismo dinero contado
    dos veces, y una aplicación que el servicio rechaza después.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "res1")
        nota = _credito(db, mundo, x, amount="100.00")
        db.flush()
        antes = sz.customer_credits(db, company_id=mundo.company_a, customer_id=x)
        fila = next(c for c in antes if c["id"] == str(nota.id))
        assert Decimal(fila["available"]) == Decimal("100.00")

        tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                          amount=Decimal("60.00"), reason="El cliente lo pidió",
                          actor="tesorero")
        db.flush()

        despues = sz.customer_credits(db, company_id=mundo.company_a, customer_id=x)
        fila = next(c for c in despues if c["id"] == str(nota.id))
        assert Decimal(fila["available"]) == Decimal("40.00"), "ofrece crédito ya reservado"
        assert Decimal(fila["refund_reserved"]) == Decimal("60.00")

        # El estado de cuenta separa las dos cifras. Imputable bajó a cuarenta;
        # el saldo **no se movió**, porque reservar no paga: los sesenta se
        # siguen debiendo, solo que en efectivo.
        estado = sz.customer_balance(db, company_id=mundo.company_a, customer_id=x)
        assert Decimal(estado["credit_available"]) == Decimal("40.00")
        assert Decimal(estado["credit_refund_reserved"]) == Decimal("60.00")
        saldo_reservado = Decimal(estado["balance"])
        assert saldo_reservado == Decimal(estado["outstanding"]) - Decimal("100.00")
    finally:
        db.close()


def test_el_saldo_solo_se_mueve_cuando_el_dinero_sale(mundo):
    """Ejecutar el reembolso sí paga la deuda; reservarla no."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "res2")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="500.00")
        db.flush()
        inicial = Decimal(sz.customer_balance(db, company_id=mundo.company_a,
                                              customer_id=x)["balance"])

        r = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                              amount=Decimal("60.00"), reason="El cliente lo pidió",
                              account_id=str(cuenta.id), actor="tesorero")
        db.flush()
        tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(r.id),
                         approved=True, actor="jefe")
        db.flush()
        assert Decimal(sz.customer_balance(db, company_id=mundo.company_a,
                                           customer_id=x)["balance"]) == inicial, \
            "aprobar no paga: el saldo no puede moverse todavía"

        tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(r.id), actor="jefe")
        db.flush()
        final = sz.customer_balance(db, company_id=mundo.company_a, customer_id=x)
        assert Decimal(final["balance"]) == inicial + Decimal("60.00"), \
            "el dinero salió del banco y la deuda sigue contada"
        assert Decimal(final["credit_refunded"]) == Decimal("60.00")
        assert Decimal(final["credit_available"]) == Decimal("40.00")
    finally:
        db.close()


def test_no_se_ejecuta_un_reembolso_sin_fondos(mundo):
    """«No negative cash by accident»: la cuenta no se descubre para pagar.

    La comprobación va en la ejecución, no en la solicitud: entre pedir y pagar
    puede pasar cualquier cosa con el saldo, y es en el momento de sacar el
    dinero cuando hay que mirar.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        x = _cliente(db, mundo.company_a, "rf")
        nota = _credito(db, mundo, x, amount="100.00")
        cuenta = _cuenta(db, mundo, moneda="VED", saldo="10.00")
        r = tz.request_refund(db, company_id=mundo.company_a, credit_note_id=str(nota.id),
                              amount=Decimal("60.00"), reason="Petición del cliente",
                              account_id=str(cuenta.id), actor="cobranza")
        db.flush()
        tz.decide_refund(db, company_id=mundo.company_a, refund_id=str(r.id),
                         approved=True, actor="jefe")
        db.flush()

        with pytest.raises(ConflictError) as exc:
            tz.settle_refund(db, company_id=mundo.company_a, refund_id=str(r.id), actor="jefe")
        assert exc.value.code == "INSUFFICIENT_FUNDS"

        # Y nada se movió: ni el banco, ni la reserva, ni el estado.
        assert tz.account_balance(db, company_id=mundo.company_a,
                                  account_id=str(cuenta.id)) == Decimal("10.00")
        assert Decimal(str(nota.refund_reserved)) == Decimal("60.00")
        assert Decimal(str(nota.refunded)) == Decimal("0.00")
        assert r.status == "APPROVED"
    finally:
        db.close()


def test_el_credito_de_otra_empresa_no_existe_aunque_la_politica_prohiba(mundo):
    """El orden de las comprobaciones también es una respuesta.

    Si la política se mira primero, una empresa que pregunta por el crédito de
    otra recibe «no está permitido devolver» —y con eso aprende que el crédito
    existe—. La pertenencia se comprueba antes: para quien no es su dueño, ese
    crédito no existe. Es la misma lección que dejó `create_shipment` en la 035.
    """
    db = mundo.factory()
    try:
        _sin_politica(db, mundo)
        # Política de la empresa B que **prohíbe** devolver: si se mirase antes
        # que la pertenencia, éste sería el error que saldría.
        tz.activate_fx_policy(
            db, company_id=mundo.company_b,
            policy_id=str(tz.create_fx_policy(
                db, company_id=mundo.company_b, policy_code=f"NOB-{uuid4().hex[:6]}",
                functional_currency="VED", effective_from=date(2020, 1, 1),
                allow_cross_currency=True, allow_refund=False, actor="qa").id),
            actor="qa")
        x = _cliente(db, mundo.company_a, "rg")
        nota = _credito(db, mundo, x, amount="100.00")
        db.commit()

        with pytest.raises(NotFoundError):
            tz.request_refund(db, company_id=mundo.company_b, credit_note_id=str(nota.id),
                              amount=Decimal("10.00"), reason="Desde otra empresa",
                              actor="x")
    finally:
        db.close()
