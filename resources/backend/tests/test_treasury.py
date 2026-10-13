"""Pruebas de tesorería (006).

Cubre: maestros financieros, cajas (apertura/movimientos/arqueo/pre-cierre/
cierre y diferencias), bancos (transacciones, ingresos/egresos idempotentes,
transferencias), conciliación asistida con reglas + resolución manual auditada,
IGTF por regla y evento (≠ IVA), anticipos sin aplicación e imputación,
snapshot de tasa y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.master_data.models import Party
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import OpenItem, Payment
from app.modules.treasury import service as treasury_service
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    CashSession,
    FinancialAccount,
    FinancialBank,
)
from app.shared.clock import hoy_de_negocio
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO, sembrar_empresas


@pytest.fixture()
def db_session(sesion_de_prueba):
    # Las empresas se crean de verdad: con las claves foráneas de N7, guardar
    # bajo una cadena inventada ya no es posible, y tampoco debería haberlo sido.
    sembrar_empresas(sesion_de_prueba)
    sesion_de_prueba.commit()
    return sesion_de_prueba


#: Empresas **reales**, sembradas por `db_session`. Antes eran la cadena
#: «tenant-1», que no era ni empresa ni tenant y solo se aceptaba porque la
#: base no comprobaba nada.
COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS


def _make_party(db: Session, company: str = COMPANY, code: str = "PROV-1") -> Party:
    party = Party(company_id=company, code=code, name="Tercero SA", person_type="JURIDICA",
                  tax_id=f"J-{abs(hash(code)) % 100000000}-1", roles=["PROVEEDOR"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_bank(db: Session, company: str = COMPANY) -> FinancialBank:
    b = treasury_service.create_bank(db, company_id=company, code="BN-1", name="Banco Nacional")
    db.flush()
    return b


def _make_account(db: Session, company: str = COMPANY) -> FinancialAccount:
    bank = _make_bank(db, company)
    a = treasury_service.create_account(db, company_id=company, bank_id=str(bank.id), code="CTA-1",
                                        name="Cuenta Principal", currency="VED")
    db.flush()
    return a


def _make_cashbox(db: Session, company: str = COMPANY) -> Cashbox:
    cb = treasury_service.create_cashbox(db, company_id=company, code="CAJ-1", name="Caja Principal")
    db.flush()
    return cb


def _make_payment(db: Session, company: str = COMPANY, direction: str = "OUT", amount: float = 100.0,
                  status: str = "APPROVED") -> Payment:
    party = _make_party(db, company)
    p = Payment(company_id=company, party_id=str(party.id), direction=direction, currency="VED",
                amount=amount, applied=0.0, status=status)
    db.add(p)
    db.flush()
    return p


def _open_cash_session(db: Session, cashbox: Cashbox, company: str = COMPANY,
                       opened: Decimal = Decimal("0")) -> CashSession:
    s = treasury_service.open_session(db, company_id=company, cashbox_id=str(cashbox.id), opened_amount=opened)
    db.flush()
    return s


class TestMaestrosFinancieros:
    def test_create_bank_account_cashbox(self, db_session) -> None:
        bank = _make_bank(db_session)
        account = treasury_service.create_account(db_session, company_id=COMPANY, bank_id=str(bank.id),
                                                  code="CTA-1", name="Cuenta Principal")
        cashbox = _make_cashbox(db_session)
        assert bank.status == "ACTIVE" and account.bank_id == str(bank.id) and cashbox.currency == "VED"

    def test_method_instrument_currency_rate(self, db_session) -> None:
        method = treasury_service.create_payment_method(db_session, company_id=COMPANY, code="EF", name="Efectivo", kind="CASH")
        instrument = treasury_service.create_instrument(db_session, company_id=COMPANY, method_id=str(method.id),
                                                        code="EF-1", name="Efectivo Bs")
        currency = treasury_service.create_currency(db_session, company_id=COMPANY, code="USD", name="Dólar", symbol="$")
        rate = treasury_service.set_exchange_rate(db_session, company_id=COMPANY, currency_id=str(currency.id),
                                                  rate_date=hoy_de_negocio(), rate=36.5, source="BCV")
        assert instrument.method_id == str(method.id) and rate.rate == 36.5

    def test_currency_isolated(self, db_session) -> None:
        currency = treasury_service.create_currency(db_session, company_id=COMPANY, code="USD")
        with pytest.raises(NotFoundError):
            treasury_service.set_exchange_rate(db_session, company_id=OTHER, currency_id=str(currency.id),
                                               rate_date=hoy_de_negocio(), rate=36.0)


class TestCajas:
    def test_open_session(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=Decimal("500"))
        assert s.status == "OPEN" and s.opened_amount == 500.0

    def test_full_cash_cycle(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=1000.0)
        treasury_service.add_session_movement(db_session, session_id=str(s.id), movement_type="IN", amount=Decimal("200"))
        treasury_service.add_session_movement(db_session, session_id=str(s.id), movement_type="OUT", amount=Decimal("50"))
        treasury_service.arqueo_session(db_session, session_id=str(s.id), counted_amount=Decimal("1150.00"))
        assert s.status == "ARCHED" and s.difference == 0.0
        treasury_service.pre_close_session(db_session, session_id=str(s.id))
        assert s.status == "PRE_CLOSED"
        treasury_service.close_session(db_session, session_id=str(s.id))
        assert s.status == "CLOSED" and s.closed_at is not None

    def test_arqueo_difference_reported(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=1000.0)
        treasury_service.add_session_movement(db_session, session_id=str(s.id), movement_type="IN", amount=Decimal("200"))
        treasury_service.arqueo_session(db_session, session_id=str(s.id), counted_amount=Decimal("1150.00"))
        assert s.counted_amount == 1150.0 and s.expected_amount == 1200.0 and s.difference == -50.0

    def test_close_with_unapproved_difference_rejected(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=1000.0)
        treasury_service.arqueo_session(db_session, session_id=str(s.id), counted_amount=Decimal("950.00"))
        treasury_service.pre_close_session(db_session, session_id=str(s.id))
        with pytest.raises(ConflictError):
            treasury_service.close_session(db_session, session_id=str(s.id), difference_approved=False)
        assert s.status == "PRE_CLOSED"

    def test_close_with_approved_difference(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=1000.0)
        treasury_service.arqueo_session(db_session, session_id=str(s.id), counted_amount=Decimal("950.00"))
        treasury_service.pre_close_session(db_session, session_id=str(s.id))
        treasury_service.close_session(db_session, session_id=str(s.id), difference_approved=True,
                                       approval_note="Faltante autorizado")
        assert s.status == "CLOSED" and s.approval_note == "Faltante autorizado"

    def test_movement_rejected_on_closed_session(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb)
        treasury_service.arqueo_session(db_session, session_id=str(s.id), counted_amount=Decimal("0.00"))
        treasury_service.pre_close_session(db_session, session_id=str(s.id))
        treasury_service.close_session(db_session, session_id=str(s.id))
        with pytest.raises(ConflictError):
            treasury_service.add_session_movement(db_session, session_id=str(s.id), movement_type="IN", amount=Decimal("10"))


class TestBancosYEgresos:
    def test_create_bank_transaction(self, db_session) -> None:
        account = _make_account(db_session)
        bt = treasury_service.create_bank_transaction(db_session, company_id=COMPANY, account_id=str(account.id),
                                                      direction="OUT", amount=100.0, source="ADJUSTMENT")
        assert bt.status == "PENDING" and bt.direction == "OUT" and bt.rate_snapshot == 1.0

    def test_execute_egreso_against_bank_idempotent(self, db_session) -> None:
        account = _make_account(db_session)
        payment = _make_payment(db_session, direction="OUT", amount=100.0)
        result = treasury_service.execute_payment(db_session, company_id=COMPANY, payment_id=str(payment.id),
                                                  target_type="ACCOUNT", target_id=str(account.id),
                                                  idempotency_key="exec-1")
        assert result["kind"] == "bank" and result["idempotent"] is False
        assert payment.status == "POSTED"
        count = db_session.query(BankTransaction).filter(BankTransaction.payment_id == str(payment.id)).count()
        assert count == 1
        # Reintento con la misma clave: idempotente, no duplica
        retry = treasury_service.execute_payment(db_session, company_id=COMPANY, payment_id=str(payment.id),
                                                 target_type="ACCOUNT", target_id=str(account.id),
                                                 idempotency_key="exec-1")
        assert retry["idempotent"] is True
        assert db_session.query(BankTransaction).filter(BankTransaction.payment_id == str(payment.id)).count() == 1

    def test_execute_egreso_against_cashbox(self, db_session) -> None:
        cb = _make_cashbox(db_session)
        s = _open_cash_session(db_session, cb, opened=Decimal("500"))
        payment = _make_payment(db_session, direction="OUT", amount=80.0)
        result = treasury_service.execute_payment(db_session, company_id=COMPANY, payment_id=str(payment.id),
                                                  target_type="CASHBOX", target_id=str(cb.id))
        assert result["kind"] == "cash"
        data = treasury_service.session_dict(db_session, s)
        assert data["expected_amount"] == "420.00" and payment.status == "POSTED"

    def test_execute_collection_requires_approved(self, db_session) -> None:
        account = _make_account(db_session)
        payment = _make_payment(db_session, direction="IN", amount=50.0, status="DRAFT")
        with pytest.raises(ConflictError):
            treasury_service.execute_collection(db_session, company_id=COMPANY, payment_id=str(payment.id),
                                                target_type="ACCOUNT", target_id=str(account.id))

    def test_transfer_between_cashboxes(self, db_session) -> None:
        c1 = _make_cashbox(db_session)
        c2 = treasury_service.create_cashbox(db_session, company_id=COMPANY, code="CAJ-2", name="Caja Secundaria")
        s1 = _open_cash_session(db_session, c1, opened=1000.0)
        s2 = _open_cash_session(db_session, c2, opened=0.0)
        t = treasury_service.create_transfer(db_session, company_id=COMPANY, amount=Decimal("300"),
                                             from_cashbox_id=str(c1.id), to_cashbox_id=str(c2.id))
        assert t.status == "POSTED"
        assert treasury_service.session_dict(db_session, s1)["expected_amount"] == "700.00"
        assert treasury_service.session_dict(db_session, s2)["expected_amount"] == "300.00"

    def test_transfer_between_accounts(self, db_session) -> None:
        a1 = _make_account(db_session)
        a2 = treasury_service.create_account(db_session, company_id=COMPANY, bank_id=str(_make_bank(db_session).id),
                                             code="CTA-2", name="Cuenta Secundaria")
        t = treasury_service.create_transfer(db_session, company_id=COMPANY, amount=Decimal("200"),
                                             from_account_id=str(a1.id), to_account_id=str(a2.id))
        assert t.status == "POSTED"
        txs = db_session.query(BankTransaction).filter(BankTransaction.source == "TRANSFER").count()
        assert txs == 2


class TestConciliacion:
    def test_match_by_rule(self, db_session) -> None:
        account = _make_account(db_session)
        payment = _make_payment(db_session, direction="OUT", amount=100.0)
        treasury_service.execute_payment(db_session, company_id=COMPANY, payment_id=str(payment.id),
                                         target_type="ACCOUNT", target_id=str(account.id))
        bt = db_session.query(BankTransaction).filter(BankTransaction.payment_id == str(payment.id)).first()
        rec = treasury_service.create_reconciliation(db_session, company_id=COMPANY, account_id=str(account.id),
                                                     statement_ref="EXT-1")
        treasury_service.add_reconciliation_line(db_session, reconciliation_id=str(rec.id), bank_transaction_id=str(bt.id))
        matched = treasury_service.propose_matches(db_session, reconciliation_id=str(rec.id))
        assert len(matched) == 1 and matched[0].status == "MATCHED" and matched[0].match_score == 1.0
        assert matched[0].system_movement_id == str(payment.id)

    def test_resolution_manual_audited(self, db_session) -> None:
        account = _make_account(db_session)
        bt = treasury_service.create_bank_transaction(db_session, company_id=COMPANY, account_id=str(account.id),
                                                      direction="IN", amount=50.0, source="ADJUSTMENT")
        rec = treasury_service.create_reconciliation(db_session, company_id=COMPANY, account_id=str(account.id))
        line = treasury_service.add_reconciliation_line(db_session, reconciliation_id=str(rec.id),
                                                        bank_transaction_id=str(bt.id))
        treasury_service.transition_reconciliation(db_session, reconciliation_id=str(rec.id), target="IN_PROGRESS")
        resolved = treasury_service.resolve_line(db_session, company_id=rec.company_id, line_id=str(line.id), resolution_type="DIFFERENCE",
                                                 notes="Comisión bancaria", actor="user-1")
        assert resolved.status == "RESOLVED" and resolved.matched_by == "MANUAL"
        assert "DIFFERENCE" in (resolved.resolution or "") and "user-1" in (resolved.resolution or "")

    def test_reconciliation_approval_flow(self, db_session) -> None:
        account = _make_account(db_session)
        rec = treasury_service.create_reconciliation(db_session, company_id=COMPANY, account_id=str(account.id))
        treasury_service.transition_reconciliation(db_session, reconciliation_id=str(rec.id), target="IN_PROGRESS")
        treasury_service.transition_reconciliation(db_session, reconciliation_id=str(rec.id), target="REVIEW")
        treasury_service.transition_reconciliation(db_session, reconciliation_id=str(rec.id), target="APPROVED",
                                                   actor="auditor-1")
        assert rec.status == "APPROVED" and rec.approved_by == "auditor-1"
        with pytest.raises(ConflictError):
            treasury_service.transition_reconciliation(db_session, reconciliation_id=str(rec.id), target="REVIEW")


class TestIGTF:
    def _make_igft_rule(self, db_session, rate: float = 0.03) -> None:
        treasury_service.create_fiscal_rule(db_session, company_id=COMPANY, rule_code="IGTF-2026",
                                            name="IGTF ventas", rule_type="IGTF", version="1.0",
                                            effective_from=hoy_de_negocio() - timedelta(days=30),
                                            params=f'{{"rate": {rate}}}')

    def test_igft_by_rule_and_event(self, db_session) -> None:
        self._make_igft_rule(db_session)
        event = treasury_service.evaluate_igft(db_session, company_id=COMPANY, event_type="PAYMENT",
                                               source_document="FAC-1", amount=Decimal("100"), currency="VED")
        assert event.igft_amount == 3.0 and event.status == "EVALUATED" and event.rule_id is not None

    def test_igft_not_confused_with_iva(self, db_session) -> None:
        self._make_igft_rule(db_session)
        iva = 16.0  # IVA adicional de una base de 100 al 16%
        event = treasury_service.evaluate_igft(db_session, company_id=COMPANY, event_type="PAYMENT",
                                               amount=Decimal("100"), currency="VED")
        # El IGTF se evalúa por regla y queda separado del IVA (nunca se suman)
        assert event.igft_amount == 3.0
        assert event.igft_amount != iva
        assert event.amount == 100.0  # base sin IVA

    def test_igft_requires_active_rule(self, db_session) -> None:
        with pytest.raises(NotFoundError):
            treasury_service.evaluate_igft(db_session, company_id=COMPANY, event_type="PAYMENT", amount=Decimal("100"))


class TestAnticiposYMultiempresa:
    def test_advance_without_application_then_impute(self, db_session) -> None:
        party = _make_party(db_session)
        adv = ap_service.register_advance(db_session, company_id=COMPANY, party_id=str(party.id), amount=200.0)
        assert adv.available == 200.0 and adv.status == "ACTIVE"  # sin aplicación inicial
        item = OpenItem(company_id=COMPANY, party_id=str(party.id), source_document="FACT-1",
                        item_type="PAYABLE", currency="VED", original=150.0, status="OPEN")
        db_session.add(item)
        db_session.flush()
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="ADVANCE", source_id=str(adv.id),
                                target_open_item_id=str(item.id), amount=150.0)
        assert adv.available == 50.0 and item.status == "CLOSED"

    def test_tenant_isolation_for_cashbox(self, db_session) -> None:
        cb = _make_cashbox(db_session, company=COMPANY)
        with pytest.raises(NotFoundError):
            treasury_service.open_session(db_session, company_id=OTHER, cashbox_id=str(cb.id))

    def test_rate_snapshot_captured(self, db_session) -> None:
        account = treasury_service.create_account(db_session, company_id=COMPANY, bank_id=str(_make_bank(db_session).id),
                                                  code="CTA-USD", name="Cuenta USD", currency="USD")
        currency = treasury_service.create_currency(db_session, company_id=COMPANY, code="USD")
        treasury_service.set_exchange_rate(db_session, company_id=COMPANY, currency_id=str(currency.id),
                                           rate_date=hoy_de_negocio(), rate=36.5)
        bt = treasury_service.create_bank_transaction(db_session, company_id=COMPANY, account_id=str(account.id),
                                                      direction="IN", amount=100.0, currency="USD")
        assert bt.rate_snapshot == 36.5
