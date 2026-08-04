"""Servicios de tesorería (006).

Cajas (sesiones, movimientos, arqueo, pre-cierre, cierre y diferencias), bancos
(transacciones, ingresos/egresos, transferencias y depósitos), conciliación
asistida con reglas y resolución manual auditada, e IGTF por regla y evento.

Integración: 006 consume los pagos de 004 (egresos) y los cobros de 005
(ingresos) vía `ap_payments`; no duplica su lógica. La ejecución marca el
pago/cobro como POSTED y genera la transacción de caja o banco (idempotente).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import Payment
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    CashSession,
    CashSessionMovement,
    Currency,
    ExchangeRate,
    FinancialAccount,
    FinancialBank,
    FiscalRule,
    IgftEvent,
    PaymentMethod,
    Reconciliation,
    ReconciliationLine,
    TreasuryInstrument,
    TreasuryTransfer,
)

# --------------------------------------------------------------------------- #
# Máquinas de estado (DOC-02 §10 / DOC-03 §13)
# --------------------------------------------------------------------------- #
CASH_SESSION_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"ARCHED"},
    "ARCHED": {"PRE_CLOSED"},
    "PRE_CLOSED": {"CLOSED", "REJECTED"},
    "CLOSED": set(),
    "REJECTED": set(),
}

RECONCILIATION_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"IN_PROGRESS"},
    "IN_PROGRESS": {"REVIEW"},
    "REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


def _require_cashbox(db: Session, company_id: str, cashbox_id: str) -> Cashbox:
    c = db.get(Cashbox, cashbox_id)
    if not c or c.company_id != company_id:
        raise NotFoundError(code="CASHBOX_NOT_FOUND", message="Caja no encontrada")
    return c


def _require_account(db: Session, company_id: str, account_id: str) -> FinancialAccount:
    a = db.get(FinancialAccount, account_id)
    if not a or a.company_id != company_id:
        raise NotFoundError(code="ACCOUNT_NOT_FOUND", message="Cuenta bancaria no encontrada")
    return a


def _require_session(db: Session, company_id: str, session_id: str) -> CashSession:
    s = db.get(CashSession, session_id)
    if not s or s.company_id != company_id:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    return s


def _require_currency(db: Session, company_id: str, currency_id: str) -> Currency:
    c = db.get(Currency, currency_id)
    if not c or c.company_id != company_id:
        raise NotFoundError(code="CURRENCY_NOT_FOUND", message="Moneda no encontrada")
    return c


def _rate_snapshot(db: Session, company_id: str, currency: str) -> float:
    """Tasa histórica más reciente de la moneda (snapshot por transacción)."""
    if currency in ("VED", "VES"):
        return 1.0
    cur = db.execute(select(Currency).where(
        Currency.company_id == company_id, Currency.code == currency)).scalars().first()
    if not cur:
        return 1.0
    row = db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.company_id == company_id, ExchangeRate.currency_id == str(cur.id))
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    ).scalars().first()
    return row.rate if row else 1.0


def _session_expected(db: Session, session: CashSession) -> float:
    ins = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id, CashSessionMovement.movement_type == "IN")).scalars().all()
    outs = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id, CashSessionMovement.movement_type == "OUT")).scalars().all()
    return round(session.opened_amount + sum(m.amount for m in ins) - sum(m.amount for m in outs), 6)


# --------------------------------------------------------------------------- #
# Maestros financieros
# --------------------------------------------------------------------------- #
def create_bank(db: Session, *, company_id: str, code: str, name: str, swift: str | None = None,
                country: str | None = None, actor: str | None = None) -> FinancialBank:
    company_id = _company(company_id, obj="banco")
    b = FinancialBank(company_id=company_id, code=code, name=name, swift=swift, country=country,
                      status="ACTIVE", created_by=actor)
    db.add(b)
    db.flush()
    return b


def create_account(db: Session, *, company_id: str, bank_id: str, code: str, name: str, currency: str = "VED",
                   iban: str | None = None, reference: str | None = None, actor: str | None = None) -> FinancialAccount:
    company_id = _company(company_id, obj="cuenta")
    bank = db.get(FinancialBank, bank_id)
    if not bank or bank.company_id != company_id:
        raise NotFoundError(code="BANK_NOT_FOUND", message="Banco no encontrado")
    a = FinancialAccount(company_id=company_id, bank_id=bank_id, code=code, name=name, currency=currency,
                         iban=iban, reference=reference, status="ACTIVE", created_by=actor)
    db.add(a)
    db.flush()
    return a


def create_cashbox(db: Session, *, company_id: str, code: str, name: str, currency: str = "VED",
                   warehouse_id: str | None = None, policies: str | None = None, actor: str | None = None) -> Cashbox:
    company_id = _company(company_id, obj="caja")
    c = Cashbox(company_id=company_id, code=code, name=name, currency=currency, warehouse_id=warehouse_id,
                policies=policies, status="ACTIVE", created_by=actor)
    db.add(c)
    db.flush()
    return c


def create_payment_method(db: Session, *, company_id: str, code: str, name: str, kind: str = "OTHER",
                          actor: str | None = None) -> PaymentMethod:
    company_id = _company(company_id, obj="método")
    m = PaymentMethod(company_id=company_id, code=code, name=name, kind=kind, status="ACTIVE", created_by=actor)
    db.add(m)
    db.flush()
    return m


def create_instrument(db: Session, *, company_id: str, method_id: str, code: str, name: str,
                      cashbox_id: str | None = None, account_id: str | None = None,
                      actor: str | None = None) -> TreasuryInstrument:
    company_id = _company(company_id, obj="instrumento")
    method = db.get(PaymentMethod, method_id)
    if not method or method.company_id != company_id:
        raise NotFoundError(code="PAYMENT_METHOD_NOT_FOUND", message="Método de pago no encontrado")
    i = TreasuryInstrument(company_id=company_id, method_id=method_id, code=code, name=name,
                           cashbox_id=cashbox_id, account_id=account_id, status="ACTIVE", created_by=actor)
    db.add(i)
    db.flush()
    return i


def create_currency(db: Session, *, company_id: str, code: str, name: str | None = None, symbol: str | None = None,
                    decimal_places: int = 2, actor: str | None = None) -> Currency:
    company_id = _company(company_id, obj="moneda")
    c = Currency(company_id=company_id, code=code, name=name, symbol=symbol, decimal_places=decimal_places,
                 status="ACTIVE", created_by=actor)
    db.add(c)
    db.flush()
    return c


def set_exchange_rate(db: Session, *, company_id: str, currency_id: str, rate_date: date, rate: float,
                      source: str | None = None, actor: str | None = None) -> ExchangeRate:
    company_id = _company(company_id, obj="tasa")
    _require_currency(db, company_id, currency_id)
    if rate <= 0:
        raise KontrolError(code="INVALID_RATE", message="La tasa debe ser positiva", status_code=422)
    r = ExchangeRate(company_id=company_id, currency_id=currency_id, rate_date=rate_date, rate=rate, source=source,
                     created_by=actor)
    db.add(r)
    db.flush()
    return r


# --------------------------------------------------------------------------- #
# Cajas — sesiones
# --------------------------------------------------------------------------- #
def open_session(db: Session, *, company_id: str, cashbox_id: str, opened_amount: float = 0.0,
                 actor: str | None = None) -> CashSession:
    company_id = _company(company_id, obj="sesión de caja")
    _require_cashbox(db, company_id, cashbox_id)
    s = CashSession(company_id=company_id, cashbox_id=cashbox_id, opened_by=actor,
                    opened_at=date.today(), opened_amount=opened_amount, status="OPEN", created_by=actor)
    db.add(s)
    db.flush()
    return s


def add_session_movement(db: Session, *, session_id: str, movement_type: str, amount: float,
                         instrument_id: str | None = None, payment_id: str | None = None,
                         source: str = "PAYMENT", reference: str | None = None,
                         note: str | None = None) -> CashSessionMovement:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    if session.status not in ("OPEN", "ARCHED"):
        raise ConflictError(code="SESSION_NOT_ACTIVE", message="La sesión de caja no admite movimientos.")
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del movimiento debe ser positivo", status_code=422)
    if movement_type not in ("IN", "OUT", "ADJUST"):
        raise KontrolError(code="INVALID_MOVEMENT_TYPE", message="Tipo de movimiento inválido", status_code=422)
    m = CashSessionMovement(session_id=str(session.id), movement_type=movement_type, amount=amount,
                            instrument_id=instrument_id, payment_id=payment_id, source=source,
                            reference=reference, note=note)
    db.add(m)
    db.flush()
    return m


def arqueo_session(db: Session, *, session_id: str, counted_amount: float,
                   notes: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "ARCHED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    expected = _session_expected(db, session)
    session.counted_amount = counted_amount
    session.expected_amount = expected
    session.difference = round(counted_amount - expected, 6)
    session.status = "ARCHED"
    if notes:
        session.audit = f'{{"arqueo_notes": {notes!r}}}'
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def pre_close_session(db: Session, *, session_id: str, actor: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "PRE_CLOSED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    session.status = "PRE_CLOSED"
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def reject_session(db: Session, *, session_id: str, actor: str | None = None) -> CashSession:
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "REJECTED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    session.status = "REJECTED"
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def close_session(db: Session, *, session_id: str, difference_approved: bool = False,
                  approval_note: str | None = None, actor: str | None = None) -> CashSession:
    """Cierra la caja; rechaza si hay diferencia sin aprobación (FR-006-003)."""
    session = db.get(CashSession, session_id)
    if not session:
        raise NotFoundError(code="CASH_SESSION_NOT_FOUND", message="Sesión de caja no encontrada")
    _assert_transition(session.status, "CLOSED", CASH_SESSION_TRANSITIONS, "la sesión de caja")
    diff = session.difference or 0.0
    if abs(diff) > 1e-6 and not difference_approved:
        raise ConflictError(code="DIFFERENCE_NOT_APPROVED",
                            message="La caja tiene diferencia y debe aprobarse/justificarse para cerrarla.")
    session.status = "CLOSED"
    session.closed_at = date.today()
    session.approval_note = approval_note
    session.audit = f'{{"difference_approved": {str(difference_approved).lower()}, "closed_by": {actor!r}}}'
    session.updated_at = datetime.now(UTC)
    db.flush()
    return session


def session_dict(db: Session, session: CashSession) -> dict:
    movements = db.execute(select(CashSessionMovement).where(
        CashSessionMovement.session_id == session.id).order_by(CashSessionMovement.created_at)).scalars().all()
    expected = _session_expected(db, session)
    return {"id": session.id, "cashbox_id": session.cashbox_id, "opened_by": session.opened_by,
            "opened_at": session.opened_at.isoformat() if session.opened_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "opened_amount": session.opened_amount, "counted_amount": session.counted_amount,
            "expected_amount": expected, "difference": session.difference, "status": session.status,
            "approval_note": session.approval_note,
            "allowed_actions": session_allowed_actions(session),
            "movements": [{"id": m.id, "movement_type": m.movement_type, "payment_id": m.payment_id,
                           "amount": m.amount, "instrument_id": m.instrument_id, "reference": m.reference}
                          for m in movements]}


def session_allowed_actions(session: CashSession) -> dict[str, bool]:
    s = session.status
    return {"view": True, "arqueo": s == "OPEN", "pre_close": s == "ARCHED", "close": s == "PRE_CLOSED",
            "reject": s == "PRE_CLOSED", "movement": s in ("OPEN", "ARCHED")}


# --------------------------------------------------------------------------- #
# Bancos — transacciones, ingresos/egresos, transferencias
# --------------------------------------------------------------------------- #
def create_bank_transaction(db: Session, *, company_id: str, account_id: str, direction: str, amount: float,
                            currency: str = "VED", txn_date: date | None = None, value_date: date | None = None,
                            reference: str | None = None, source: str = "ADJUSTMENT", payment_id: str | None = None,
                            commission: float | None = None, actor: str | None = None) -> BankTransaction:
    company_id = _company(company_id, obj="transacción bancaria")
    _require_account(db, company_id, account_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    bt = BankTransaction(company_id=company_id, account_id=account_id, txn_date=txn_date or date.today(),
                         value_date=value_date or txn_date or date.today(), direction=direction, amount=amount,
                         currency=currency, reference=reference, source=source, payment_id=payment_id,
                         commission=commission, rate_snapshot=_rate_snapshot(db, company_id, currency),
                         status="PENDING", created_by=actor)
    db.add(bt)
    db.flush()
    return bt


def _find_execution(db: Session, payment_id: str) -> dict | None:
    """Busca una ejecución previa (caja o banco) para idempotencia."""
    bt = db.execute(select(BankTransaction).where(BankTransaction.payment_id == payment_id)).scalars().first()
    if bt:
        return {"kind": "bank", "id": str(bt.id)}
    mv = db.execute(select(CashSessionMovement).where(CashSessionMovement.payment_id == payment_id)).scalars().first()
    if mv:
        return {"kind": "cash", "id": str(mv.id)}
    return None


def execute_payment(db: Session, *, company_id: str, payment_id: str, target_type: str, target_id: str,
                    actor: str | None = None, idempotency_key: str | None = None) -> dict:
    """Ejecuta un egreso de 004 (Payment OUT) contra caja o banco (FR-006-020/022).

    Idempotente: reintentar la misma ejecución no duplica transacciones.
    """
    company_id = _company(company_id, obj="egreso")
    payment = db.get(Payment, payment_id)
    if not payment or payment.company_id != company_id or payment.direction != "OUT":
        raise NotFoundError(code="PAYMENT_NOT_FOUND", message="Pago de egreso no encontrado")
    if idempotency_key:
        existing = _find_execution(db, str(payment.id))
        if existing:
            return {"id": existing["id"], "kind": existing["kind"], "idempotent": True,
                    "amount": payment.amount, "currency": payment.currency}
    if payment.status != "APPROVED":
        raise ConflictError(code="PAYMENT_NOT_APPROVED", message="Solo se ejecutan egresos aprobados.")

    if target_type == "CASHBOX":
        _require_cashbox(db, company_id, target_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == target_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja no tiene una sesión abierta para ejecutar el egreso.")
        mv = add_session_movement(db, session_id=str(session.id), movement_type="OUT", amount=payment.amount,
                                  payment_id=str(payment.id), source="PAYMENT", reference=f"EGRESO-{str(payment.id)[:8]}")
        result = {"id": str(mv.id), "kind": "cash", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    elif target_type == "ACCOUNT":
        _require_account(db, company_id, target_id)
        bt = create_bank_transaction(db, company_id=company_id, account_id=target_id, direction="OUT",
                                     amount=payment.amount, currency=payment.currency, source="PAYMENT",
                                     payment_id=str(payment.id), reference=f"EGRESO-{str(payment.id)[:8]}", actor=actor)
        result = {"id": str(bt.id), "kind": "bank", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    else:
        raise KontrolError(code="INVALID_TARGET", message="Destino inválido (CASHBOX/ACCOUNT)", status_code=422)

    ap_service.transition_payment(db, payment=payment, target="POSTED", actor=actor)
    db.flush()
    return result


def execute_collection(db: Session, *, company_id: str, payment_id: str, target_type: str, target_id: str,
                       actor: str | None = None, idempotency_key: str | None = None) -> dict:
    """Ejecuta un ingreso de 005 (Payment IN) contra caja o banco (FR-006-020/022)."""
    company_id = _company(company_id, obj="ingreso")
    payment = db.get(Payment, payment_id)
    if not payment or payment.company_id != company_id or payment.direction != "IN":
        raise NotFoundError(code="COLLECTION_NOT_FOUND", message="Cobro de ingreso no encontrado")
    if idempotency_key:
        existing = _find_execution(db, str(payment.id))
        if existing:
            return {"id": existing["id"], "kind": existing["kind"], "idempotent": True,
                    "amount": payment.amount, "currency": payment.currency}
    if payment.status != "APPROVED":
        raise ConflictError(code="COLLECTION_NOT_APPROVED", message="Solo se ejecutan ingresos aprobados.")

    if target_type == "CASHBOX":
        _require_cashbox(db, company_id, target_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == target_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja no tiene una sesión abierta para ejecutar el ingreso.")
        mv = add_session_movement(db, session_id=str(session.id), movement_type="IN", amount=payment.amount,
                                  payment_id=str(payment.id), source="COLLECTION", reference=f"INGRESO-{str(payment.id)[:8]}")
        result = {"id": str(mv.id), "kind": "cash", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    elif target_type == "ACCOUNT":
        _require_account(db, company_id, target_id)
        bt = create_bank_transaction(db, company_id=company_id, account_id=target_id, direction="IN",
                                     amount=payment.amount, currency=payment.currency, source="COLLECTION",
                                     payment_id=str(payment.id), reference=f"INGRESO-{str(payment.id)[:8]}", actor=actor)
        result = {"id": str(bt.id), "kind": "bank", "idempotent": False, "amount": payment.amount,
                  "currency": payment.currency}
    else:
        raise KontrolError(code="INVALID_TARGET", message="Destino inválido (CASHBOX/ACCOUNT)", status_code=422)

    ap_service.transition_payment(db, payment=payment, target="POSTED", actor=actor)
    db.flush()
    return result


def create_transfer(db: Session, *, company_id: str, amount: float, currency: str = "VED",
                    from_cashbox_id: str | None = None, from_account_id: str | None = None,
                    to_cashbox_id: str | None = None, to_account_id: str | None = None,
                    value_date: date | None = None, reference: str | None = None,
                    actor: str | None = None) -> TreasuryTransfer:
    """Transferencia entre cajas/cuentas y depósitos (FR-006-023).

    Registra la transferencia y las transacciones de banco/movimientos de caja
    de origen y destino. Requiere sesión abierta cuando participa una caja.
    """
    company_id = _company(company_id, obj="transferencia")
    if not (from_cashbox_id or from_account_id) or not (to_cashbox_id or to_account_id):
        raise KontrolError(code="INVALID_TRANSFER", message="Se requieren origen y destino válidos", status_code=422)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    t = TreasuryTransfer(company_id=company_id, from_cashbox_id=from_cashbox_id, from_account_id=from_account_id,
                         to_cashbox_id=to_cashbox_id, to_account_id=to_account_id, amount=amount,
                         currency=currency, value_date=value_date or date.today(), reference=reference,
                         status="PENDING", created_by=actor)
    db.add(t)
    db.flush()

    ref = reference or f"TRANSFER-{str(t.id)[:8]}"
    if from_account_id:
        create_bank_transaction(db, company_id=company_id, account_id=from_account_id, direction="OUT",
                                amount=amount, currency=currency, value_date=value_date, reference=ref,
                                source="TRANSFER", actor=actor)
    if to_account_id:
        create_bank_transaction(db, company_id=company_id, account_id=to_account_id, direction="IN",
                                amount=amount, currency=currency, value_date=value_date, reference=ref,
                                source="TRANSFER", actor=actor)
    if from_cashbox_id:
        _require_cashbox(db, company_id, from_cashbox_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == from_cashbox_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja de origen no tiene sesión abierta.")
        add_session_movement(db, session_id=str(session.id), movement_type="OUT", amount=amount,
                             source="TRANSFER", reference=ref)
    if to_cashbox_id:
        _require_cashbox(db, company_id, to_cashbox_id)
        session = db.execute(select(CashSession).where(
            CashSession.company_id == company_id, CashSession.cashbox_id == to_cashbox_id,
            CashSession.status.in_(["OPEN", "ARCHED"])).order_by(CashSession.opened_at.desc())).scalars().first()
        if not session:
            raise ConflictError(code="NO_OPEN_SESSION", message="La caja de destino no tiene sesión abierta.")
        add_session_movement(db, session_id=str(session.id), movement_type="IN", amount=amount,
                             source="TRANSFER", reference=ref)
    t.status = "POSTED"
    db.flush()
    return t


def bank_transaction_dict(bt: BankTransaction) -> dict:
    return {"id": bt.id, "account_id": bt.account_id, "txn_date": bt.txn_date.isoformat() if bt.txn_date else None,
            "value_date": bt.value_date.isoformat() if bt.value_date else None, "direction": bt.direction,
            "amount": bt.amount, "currency": bt.currency, "reference": bt.reference, "source": bt.source,
            "payment_id": bt.payment_id, "commission": bt.commission, "status": bt.status}


def transfer_dict(t: TreasuryTransfer) -> dict:
    return {"id": t.id, "from_cashbox_id": t.from_cashbox_id, "from_account_id": t.from_account_id,
            "to_cashbox_id": t.to_cashbox_id, "to_account_id": t.to_account_id, "amount": t.amount,
            "currency": t.currency, "value_date": t.value_date.isoformat() if t.value_date else None,
            "reference": t.reference, "status": t.status}


# --------------------------------------------------------------------------- #
# Conciliación (FR-006-030/031)
# --------------------------------------------------------------------------- #
def create_reconciliation(db: Session, *, company_id: str, account_id: str, statement_date: date | None = None,
                          statement_ref: str | None = None, opening_balance: float | None = None,
                          closing_balance: float | None = None, actor: str | None = None) -> Reconciliation:
    company_id = _company(company_id, obj="conciliación")
    _require_account(db, company_id, account_id)
    r = Reconciliation(company_id=company_id, account_id=account_id, statement_date=statement_date,
                       statement_ref=statement_ref, opening_balance=opening_balance,
                       closing_balance=closing_balance, status="DRAFT", created_by=actor)
    db.add(r)
    db.flush()
    return r


def add_reconciliation_line(db: Session, *, reconciliation_id: str, bank_transaction_id: str) -> ReconciliationLine:
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    if rec.status not in ("DRAFT", "IN_PROGRESS"):
        raise ConflictError(code="RECONCILIATION_LOCKED", message="La conciliación no admite nuevas líneas.")
    bt = db.get(BankTransaction, bank_transaction_id)
    if not bt:
        raise NotFoundError(code="BANK_TRANSACTION_NOT_FOUND", message="Transacción bancaria no encontrada")
    line = ReconciliationLine(reconciliation_id=str(rec.id), bank_transaction_id=str(bt.id), status="UNMATCHED")
    db.add(line)
    db.flush()
    return line


def propose_matches(db: Session, *, reconciliation_id: str) -> list[ReconciliationLine]:
    """Propone emparejamientos por reglas (match score) — FR-006-030.

    Reglas: referencia+importe (1.0), importe+fecha valor (0.8), importe (0.6).
    Los movimientos del sistema candidatos son pagos/cobros de 004/005.
    """
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    lines = db.execute(select(ReconciliationLine).where(
        ReconciliationLine.reconciliation_id == reconciliation_id,
        ReconciliationLine.status == "UNMATCHED")).scalars().all()
    matched = []
    for line in lines:
        bt = db.get(BankTransaction, line.bank_transaction_id) if line.bank_transaction_id else None
        if not bt:
            continue
        candidates = db.execute(select(Payment).where(
            Payment.company_id == rec.company_id, Payment.amount == bt.amount)).scalars().all()
        best = None
        best_score = 0.0
        for p in candidates:
            if p.status not in ("APPROVED", "POSTED"):
                continue
            score = 0.6
            if bt.reference and p.id and bt.reference == f"{'EGRESO' if p.direction == 'OUT' else 'INGRESO'}-{str(p.id)[:8]}":
                score = 1.0
            elif p.date and bt.value_date and p.date == bt.value_date:
                score = 0.8
            if score > best_score:
                best, best_score = p, score
        if best and best_score >= 0.8:
            line.system_movement_id = str(best.id)
            line.system_movement_type = "PAYMENT"
            line.match_score = best_score
            line.matched_by = "RULE"
            line.status = "MATCHED"
            matched.append(line)
    db.flush()
    return matched


def resolve_line(db: Session, *, line_id: str, resolution_type: str, system_movement_id: str | None = None,
                 notes: str | None = None, actor: str | None = None) -> ReconciliationLine:
    """Resolución manual auditada de una línea de conciliación — FR-006-030.

    `resolution_type`: MATCHED / DIFFERENCE / COMMISSION / FX.
    La resolución queda auditada sin alterar el IVA original (FR-006-032).
    """
    line = db.get(ReconciliationLine, line_id)
    if not line:
        raise NotFoundError(code="RECONCILIATION_LINE_NOT_FOUND", message="Línea de conciliación no encontrada")
    rec = db.get(Reconciliation, line.reconciliation_id)
    if rec and rec.status not in ("IN_PROGRESS", "REVIEW"):
        raise ConflictError(code="RECONCILIATION_LOCKED", message="La conciliación no admite resoluciones.")
    if resolution_type not in ("MATCHED", "DIFFERENCE", "COMMISSION", "FX"):
        raise KontrolError(code="INVALID_RESOLUTION", message="Tipo de resolución inválido", status_code=422)
    if system_movement_id:
        line.system_movement_id = system_movement_id
        line.system_movement_type = "PAYMENT"
    line.matched_by = "MANUAL"
    line.match_score = 1.0
    line.status = "RESOLVED"
    line.resolution = f'{{"type": {resolution_type!r}, "resolved_by": {actor!r}}}'
    line.notes = notes
    db.flush()
    return line


def transition_reconciliation(db: Session, *, reconciliation_id: str, target: str,
                              actor: str | None = None) -> Reconciliation:
    rec = db.get(Reconciliation, reconciliation_id)
    if not rec:
        raise NotFoundError(code="RECONCILIATION_NOT_FOUND", message="Conciliación no encontrada")
    _assert_transition(rec.status, target, RECONCILIATION_TRANSITIONS, "la conciliación")
    rec.status = target
    rec.updated_at = datetime.now(UTC)
    if target == "APPROVED":
        rec.approved_by = actor
        rec.approved_at = date.today()
    db.flush()
    return rec


def reconciliation_dict(db: Session, rec: Reconciliation) -> dict:
    lines = db.execute(select(ReconciliationLine).where(
        ReconciliationLine.reconciliation_id == rec.id).order_by(ReconciliationLine.created_at)).scalars().all()
    return {"id": rec.id, "account_id": rec.account_id,
            "statement_date": rec.statement_date.isoformat() if rec.statement_date else None,
            "statement_ref": rec.statement_ref, "opening_balance": rec.opening_balance,
            "closing_balance": rec.closing_balance, "status": rec.status, "approved_by": rec.approved_by,
            "approved_at": rec.approved_at.isoformat() if rec.approved_at else None,
            "allowed_actions": reconciliation_allowed_actions(rec),
            "lines": [{"id": line.id, "bank_transaction_id": line.bank_transaction_id,
                       "system_movement_id": line.system_movement_id, "system_movement_type": line.system_movement_type,
                       "match_score": line.match_score, "matched_by": line.matched_by, "status": line.status,
                       "resolution": line.resolution, "notes": line.notes} for line in lines]}


def reconciliation_allowed_actions(rec: Reconciliation) -> dict[str, bool]:
    s = rec.status
    return {"view": True, "in_progress": s == "DRAFT", "review": s == "IN_PROGRESS",
            "approve": s == "REVIEW", "reject": s == "REVIEW", "match": s in ("DRAFT", "IN_PROGRESS")}


# --------------------------------------------------------------------------- #
# IGTF por regla y evento (FR-006-040/041)
# --------------------------------------------------------------------------- #
def create_fiscal_rule(db: Session, *, company_id: str, rule_code: str, name: str | None = None,
                       rule_type: str = "IGTF", version: str = "1.0", effective_from: date | None = None,
                       effective_to: date | None = None, params: str | None = None,
                       actor: str | None = None) -> FiscalRule:
    company_id = _company(company_id, obj="regla fiscal")
    r = FiscalRule(company_id=company_id, rule_code=rule_code, name=name, rule_type=rule_type, version=version,
                   effective_from=effective_from, effective_to=effective_to, params=params,
                   status="ACTIVE", created_by=actor)
    db.add(r)
    db.flush()
    return r


def _active_rule(db: Session, company_id: str, rule_type: str, on_date: date) -> FiscalRule | None:
    today = on_date or date.today()
    return db.execute(select(FiscalRule).where(
        FiscalRule.company_id == company_id, FiscalRule.rule_type == rule_type, FiscalRule.status == "ACTIVE",
        (FiscalRule.effective_from.is_(None)) | (FiscalRule.effective_from <= today),
        (FiscalRule.effective_to.is_(None)) | (FiscalRule.effective_to >= today),
    ).order_by(FiscalRule.created_at.desc())).scalars().first()


def evaluate_igft(db: Session, *, company_id: str, event_type: str, source_document: str | None = None,
                  amount: float, currency: str = "VED", on_date: date | None = None) -> IgftEvent:
    """Evalúa IGTF por regla y evento; no confundir con IVA adicional (FR-006-040)."""
    company_id = _company(company_id, obj="evento IGTF")
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto debe ser positivo", status_code=422)
    rule = _active_rule(db, company_id, "IGTF", on_date or date.today())
    if rule is None:
        raise NotFoundError(code="NO_IGTF_RULE", message="No hay una regla IGTF vigente.")
    import json

    params = json.loads(rule.params or "{}")
    rate = float(params.get("rate", 0.0))
    snapshot = _rate_snapshot(db, company_id, currency)
    igft_amount = round(amount * rate * snapshot, 2) if currency not in ("VED", "VES") else round(amount * rate, 2)
    event = IgftEvent(company_id=company_id, event_type=event_type, source_document=source_document, amount=amount,
                      currency=currency, rate_snapshot=snapshot, igft_amount=igft_amount, rule_id=str(rule.id),
                      evaluated_at=on_date or date.today(), status="EVALUATED")
    db.add(event)
    db.flush()
    return event


def igft_event_dict(e: IgftEvent) -> dict:
    return {"id": e.id, "event_type": e.event_type, "source_document": e.source_document, "amount": e.amount,
            "currency": e.currency, "rate_snapshot": e.rate_snapshot, "igft_amount": e.igft_amount,
            "rule_id": e.rule_id, "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            "status": e.status}
