"""API de tesorería (006).

Endpoints REST `/treasury/*` con las convenciones heredadas (DOC-03 §14):
errores uniformes, `allowed_actions` en backend, transiciones explícitas,
idempotencia en POST críticos (ejecución de ingresos/egresos).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.treasury import service as treasury_service
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    CashSession,
    Currency,
    FinancialAccount,
    FinancialBank,
    FiscalRule,
    IgftEvent,
    PaymentMethod,
    Reconciliation,
    TreasuryInstrument,
    TreasuryTransfer,
)

router = APIRouter(prefix="/treasury", tags=["tesoreria"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class BankCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    swift: str | None = None
    country: str | None = None


class AccountCreate(BaseModel):
    bank_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    currency: str = "VED"
    iban: str | None = None
    reference: str | None = None


class CashboxCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    currency: str = "VED"
    warehouse_id: str | None = None
    policies: str | None = None


class PaymentMethodCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    kind: str = "OTHER"


class InstrumentCreate(BaseModel):
    method_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    cashbox_id: str | None = None
    account_id: str | None = None


class CurrencyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str | None = None
    symbol: str | None = None
    decimal_places: int = 2


class ExchangeRateCreate(BaseModel):
    currency_id: str
    rate_date: date
    rate: float = Field(gt=0)
    source: str | None = None


class SessionOpen(BaseModel):
    cashbox_id: str
    opened_amount: float = 0.0


class SessionMovementCreate(BaseModel):
    movement_type: str = Field(pattern="^(IN|OUT|ADJUST)$")
    amount: float = Field(gt=0)
    instrument_id: str | None = None
    payment_id: str | None = None
    source: str = "PAYMENT"
    reference: str | None = None
    note: str | None = None


class ArqueoBody(BaseModel):
    counted_amount: float = Field(ge=0)
    notes: str | None = None


class CloseSessionBody(BaseModel):
    difference_approved: bool = False
    approval_note: str | None = None


class BankTransactionCreate(BaseModel):
    account_id: str
    direction: str = Field(pattern="^(IN|OUT)$")
    amount: float = Field(gt=0)
    currency: str = "VED"
    txn_date: date | None = None
    value_date: date | None = None
    reference: str | None = None
    source: str = "ADJUSTMENT"
    commission: float | None = None


class ExecutionBody(BaseModel):
    payment_id: str
    target_type: str = Field(pattern="^(CASHBOX|ACCOUNT)$")
    target_id: str
    idempotency_key: str | None = None


class TransferCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "VED"
    from_cashbox_id: str | None = None
    from_account_id: str | None = None
    to_cashbox_id: str | None = None
    to_account_id: str | None = None
    value_date: date | None = None
    reference: str | None = None


class ReconciliationCreate(BaseModel):
    account_id: str
    statement_date: date | None = None
    statement_ref: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None


class ReconciliationLineCreate(BaseModel):
    bank_transaction_id: str


class ResolveLineBody(BaseModel):
    resolution_type: str = Field(pattern="^(MATCHED|DIFFERENCE|COMMISSION|FX)$")
    system_movement_id: str | None = None
    notes: str | None = None


class TransitionBody(BaseModel):
    target: str


class FiscalRuleCreate(BaseModel):
    rule_code: str = Field(min_length=1, max_length=64)
    name: str | None = None
    rule_type: str = "IGTF"
    version: str = "1.0"
    effective_from: date | None = None
    effective_to: date | None = None
    params: str | None = None


class IgftEvaluateBody(BaseModel):
    event_type: str = Field(pattern="^(PAYMENT|COLLECTION|TRANSFER)$")
    source_document: str | None = None
    amount: float = Field(gt=0)
    currency: str = "VED"
    on_date: date | None = None


# --------------------------------------------------------------------------- #
# Maestros financieros
# --------------------------------------------------------------------------- #
@router.get("/banks")
def list_banks(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(FinancialBank).where(FinancialBank.company_id == ctx.company_id)
                       .order_by(FinancialBank.name)).scalars().all()
    return {"items": [{"id": b.id, "code": b.code, "name": b.name, "swift": b.swift,
                       "country": b.country, "status": b.status} for b in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/banks", dependencies=[Depends(require_write_allowed)])
def create_bank(body: BankCreate, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    bank = treasury_service.create_bank(db, company_id=ctx.company_id, code=body.code, name=body.name,
                                        swift=body.swift, country=body.country, actor=str(actor.id))
    db.commit()
    db.refresh(bank)
    return {"id": bank.id, "code": bank.code, "name": bank.name, "status": bank.status}


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(FinancialAccount).where(FinancialAccount.company_id == ctx.company_id)
                       .order_by(FinancialAccount.name)).scalars().all()
    return {"items": [{"id": a.id, "code": a.code, "name": a.name, "bank_id": a.bank_id,
                       "currency": a.currency, "status": a.status} for a in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/accounts", dependencies=[Depends(require_write_allowed)])
def create_account(body: AccountCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    acc = treasury_service.create_account(db, company_id=ctx.company_id, bank_id=body.bank_id, code=body.code,
                                          name=body.name, currency=body.currency, iban=body.iban,
                                          reference=body.reference, actor=str(actor.id))
    db.commit()
    db.refresh(acc)
    return {"id": acc.id, "code": acc.code, "name": acc.name, "status": acc.status}


@router.get("/cashboxes")
def list_cashboxes(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(Cashbox).where(Cashbox.company_id == ctx.company_id)
                       .order_by(Cashbox.name)).scalars().all()
    return {"items": [{"id": c.id, "code": c.code, "name": c.name, "currency": c.currency,
                       "warehouse_id": c.warehouse_id, "status": c.status} for c in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/cashboxes", dependencies=[Depends(require_write_allowed)])
def create_cashbox(body: CashboxCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    cb = treasury_service.create_cashbox(db, company_id=ctx.company_id, code=body.code, name=body.name,
                                         currency=body.currency, warehouse_id=body.warehouse_id,
                                         policies=body.policies, actor=str(actor.id))
    db.commit()
    db.refresh(cb)
    return {"id": cb.id, "code": cb.code, "name": cb.name, "status": cb.status}


@router.get("/payment-methods")
def list_payment_methods(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(PaymentMethod).where(PaymentMethod.company_id == ctx.company_id)
                       .order_by(PaymentMethod.name)).scalars().all()
    return {"items": [{"id": m.id, "code": m.code, "name": m.name, "kind": m.kind, "status": m.status} for m in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/payment-methods", dependencies=[Depends(require_write_allowed)])
def create_payment_method(body: PaymentMethodCreate, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    m = treasury_service.create_payment_method(db, company_id=ctx.company_id, code=body.code, name=body.name,
                                               kind=body.kind, actor=str(actor.id))
    db.commit()
    db.refresh(m)
    return {"id": m.id, "code": m.code, "name": m.name, "status": m.status}


@router.get("/instruments")
def list_instruments(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TreasuryInstrument).where(TreasuryInstrument.company_id == ctx.company_id)
                       .order_by(TreasuryInstrument.name)).scalars().all()
    return {"items": [{"id": i.id, "code": i.code, "name": i.name, "method_id": i.method_id,
                       "cashbox_id": i.cashbox_id, "account_id": i.account_id, "status": i.status} for i in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/instruments", dependencies=[Depends(require_write_allowed)])
def create_instrument(body: InstrumentCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    i = treasury_service.create_instrument(db, company_id=ctx.company_id, method_id=body.method_id, code=body.code,
                                           name=body.name, cashbox_id=body.cashbox_id, account_id=body.account_id,
                                           actor=str(actor.id))
    db.commit()
    db.refresh(i)
    return {"id": i.id, "code": i.code, "name": i.name, "status": i.status}


@router.get("/currencies")
def list_currencies(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(Currency).where(Currency.company_id == ctx.company_id).order_by(Currency.code)).scalars().all()
    return {"items": [{"id": c.id, "code": c.code, "name": c.name, "symbol": c.symbol,
                       "decimal_places": c.decimal_places, "status": c.status} for c in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/currencies", dependencies=[Depends(require_write_allowed)])
def create_currency(body: CurrencyCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    c = treasury_service.create_currency(db, company_id=ctx.company_id, code=body.code, name=body.name,
                                         symbol=body.symbol, decimal_places=body.decimal_places, actor=str(actor.id))
    db.commit()
    db.refresh(c)
    return {"id": c.id, "code": c.code, "status": c.status}


@router.post("/exchange-rates", dependencies=[Depends(require_write_allowed)])
def set_exchange_rate(body: ExchangeRateCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    r = treasury_service.set_exchange_rate(db, company_id=ctx.company_id, currency_id=body.currency_id,
                                           rate_date=body.rate_date, rate=body.rate, source=body.source,
                                           actor=str(actor.id))
    db.commit()
    db.refresh(r)
    return {"id": r.id, "currency_id": r.currency_id, "rate": r.rate, "rate_date": r.rate_date.isoformat()}


# --------------------------------------------------------------------------- #
# Cajas — sesiones
# --------------------------------------------------------------------------- #
@router.get("/cash-sessions")
def list_sessions(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(CashSession).where(CashSession.company_id == ctx.company_id)
    if status:
        query = query.where(CashSession.status == status)
    items = db.execute(query.order_by(CashSession.opened_at.desc())).scalars().all()
    return {"items": [treasury_service.session_dict(db, s) for s in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/cash-sessions", dependencies=[Depends(require_write_allowed)])
def open_session(body: SessionOpen, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    s = treasury_service.open_session(db, company_id=ctx.company_id, cashbox_id=body.cashbox_id,
                                      opened_amount=body.opened_amount, actor=str(actor.id))
    db.commit()
    db.refresh(s)
    return treasury_service.session_dict(db, s)


@router.get("/cash-sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    return treasury_service.session_dict(db, session)


@router.post("/cash-sessions/{session_id}/movements", dependencies=[Depends(require_write_allowed)])
def add_movement(session_id: str, body: SessionMovementCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    mv = treasury_service.add_session_movement(db, session_id=str(session.id), movement_type=body.movement_type,
                                               amount=body.amount, instrument_id=body.instrument_id,
                                               payment_id=body.payment_id, source=body.source,
                                               reference=body.reference, note=body.note)
    db.commit()
    db.refresh(mv)
    return {"id": mv.id, "movement_type": mv.movement_type, "amount": mv.amount, "reference": mv.reference}


@router.post("/cash-sessions/{session_id}/arqueo", dependencies=[Depends(require_write_allowed)])
def arqueo_session(session_id: str, body: ArqueoBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    treasury_service.arqueo_session(db, session_id=str(session.id), counted_amount=body.counted_amount,
                                    notes=body.notes)
    db.commit()
    db.refresh(session)
    return treasury_service.session_dict(db, session)


@router.post("/cash-sessions/{session_id}/pre-close", dependencies=[Depends(require_write_allowed)])
def pre_close_session(session_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    treasury_service.pre_close_session(db, session_id=str(session.id), actor=str(actor.id))
    db.commit()
    db.refresh(session)
    return treasury_service.session_dict(db, session)


@router.post("/cash-sessions/{session_id}/close", dependencies=[Depends(require_write_allowed)])
def close_session(session_id: str, body: CloseSessionBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    treasury_service.close_session(db, session_id=str(session.id), difference_approved=body.difference_approved,
                                   approval_note=body.approval_note, actor=str(actor.id))
    db.commit()
    db.refresh(session)
    return treasury_service.session_dict(db, session)


@router.post("/cash-sessions/{session_id}/reject", dependencies=[Depends(require_write_allowed)])
def reject_session(session_id: str, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    session = _owned(db, CashSession, session_id, ctx.company_id, "CASH_SESSION_NOT_FOUND", "Sesión de caja no encontrada")
    treasury_service.reject_session(db, session_id=str(session.id), actor=str(actor.id))
    db.commit()
    db.refresh(session)
    return treasury_service.session_dict(db, session)


# --------------------------------------------------------------------------- #
# Bancos — transacciones, ingresos/egresos, transferencias
# --------------------------------------------------------------------------- #
@router.get("/bank-transactions")
def list_bank_transactions(account_id: str | None = None, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(BankTransaction).where(BankTransaction.company_id == ctx.company_id)
    if account_id:
        query = query.where(BankTransaction.account_id == account_id)
    items = db.execute(query.order_by(BankTransaction.txn_date.desc())).scalars().all()
    return {"items": [treasury_service.bank_transaction_dict(bt) for bt in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/bank-transactions", dependencies=[Depends(require_write_allowed)])
def create_bank_transaction(body: BankTransactionCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    bt = treasury_service.create_bank_transaction(db, company_id=ctx.company_id, account_id=body.account_id,
                                                  direction=body.direction, amount=body.amount, currency=body.currency,
                                                  txn_date=body.txn_date, value_date=body.value_date,
                                                  reference=body.reference, source=body.source,
                                                  commission=body.commission, actor=str(actor.id))
    db.commit()
    db.refresh(bt)
    return treasury_service.bank_transaction_dict(bt)


@router.post("/executions/egresos", dependencies=[Depends(require_write_allowed)])
def execute_egreso(body: ExecutionBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    result = treasury_service.execute_payment(db, company_id=ctx.company_id, payment_id=body.payment_id,
                                              target_type=body.target_type, target_id=body.target_id,
                                              actor=str(actor.id), idempotency_key=body.idempotency_key)
    db.commit()
    return {"execution_id": result["id"], "kind": result["kind"], "idempotent": result["idempotent"],
            "amount": result["amount"], "currency": result["currency"]}


@router.post("/executions/ingresos", dependencies=[Depends(require_write_allowed)])
def execute_ingreso(body: ExecutionBody, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    result = treasury_service.execute_collection(db, company_id=ctx.company_id, payment_id=body.payment_id,
                                                 target_type=body.target_type, target_id=body.target_id,
                                                 actor=str(actor.id), idempotency_key=body.idempotency_key)
    db.commit()
    return {"execution_id": result["id"], "kind": result["kind"], "idempotent": result["idempotent"],
            "amount": result["amount"], "currency": result["currency"]}


@router.get("/transfers")
def list_transfers(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TreasuryTransfer).where(TreasuryTransfer.company_id == ctx.company_id)
                       .order_by(TreasuryTransfer.created_at.desc())).scalars().all()
    return {"items": [treasury_service.transfer_dict(t) for t in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/transfers", dependencies=[Depends(require_write_allowed)])
def create_transfer(body: TransferCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    t = treasury_service.create_transfer(db, company_id=ctx.company_id, amount=body.amount, currency=body.currency,
                                         from_cashbox_id=body.from_cashbox_id, from_account_id=body.from_account_id,
                                         to_cashbox_id=body.to_cashbox_id, to_account_id=body.to_account_id,
                                         value_date=body.value_date, reference=body.reference, actor=str(actor.id))
    db.commit()
    db.refresh(t)
    return treasury_service.transfer_dict(t)


# --------------------------------------------------------------------------- #
# Conciliación
# --------------------------------------------------------------------------- #
@router.get("/reconciliations")
def list_reconciliations(status: str | None = None, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(Reconciliation).where(Reconciliation.company_id == ctx.company_id)
    if status:
        query = query.where(Reconciliation.status == status)
    items = db.execute(query.order_by(Reconciliation.created_at.desc())).scalars().all()
    return {"items": [treasury_service.reconciliation_dict(db, r) for r in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/reconciliations", dependencies=[Depends(require_write_allowed)])
def create_reconciliation(body: ReconciliationCreate, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    r = treasury_service.create_reconciliation(db, company_id=ctx.company_id, account_id=body.account_id,
                                               statement_date=body.statement_date, statement_ref=body.statement_ref,
                                               opening_balance=body.opening_balance, closing_balance=body.closing_balance,
                                               actor=str(actor.id))
    db.commit()
    db.refresh(r)
    return treasury_service.reconciliation_dict(db, r)


@router.get("/reconciliations/{reconciliation_id}")
def get_reconciliation(reconciliation_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    r = _owned(db, Reconciliation, reconciliation_id, ctx.company_id, "RECONCILIATION_NOT_FOUND", "Conciliación no encontrada")
    return treasury_service.reconciliation_dict(db, r)


@router.post("/reconciliations/{reconciliation_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_reconciliation_line(reconciliation_id: str, body: ReconciliationLineCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    rec = _owned(db, Reconciliation, reconciliation_id, ctx.company_id, "RECONCILIATION_NOT_FOUND", "Conciliación no encontrada")
    line = treasury_service.add_reconciliation_line(db, reconciliation_id=str(rec.id),
                                                    bank_transaction_id=body.bank_transaction_id)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "bank_transaction_id": line.bank_transaction_id, "status": line.status}


@router.post("/reconciliations/{reconciliation_id}/match", dependencies=[Depends(require_write_allowed)])
def propose_match(reconciliation_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    rec = _owned(db, Reconciliation, reconciliation_id, ctx.company_id, "RECONCILIATION_NOT_FOUND", "Conciliación no encontrada")
    matched = treasury_service.propose_matches(db, reconciliation_id=str(rec.id))
    db.commit()
    return {"matched": len(matched),
            "lines": [{"id": m.id, "bank_transaction_id": m.bank_transaction_id,
                       "system_movement_id": m.system_movement_id, "match_score": m.match_score,
                       "status": m.status} for m in matched]}


@router.post("/reconciliation-lines/{line_id}/resolve", dependencies=[Depends(require_write_allowed)])
def resolve_line(line_id: str, body: ResolveLineBody, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("tesoreria", "approve"))):
    line = treasury_service.resolve_line(db, line_id=line_id, resolution_type=body.resolution_type,
                                         system_movement_id=body.system_movement_id, notes=body.notes,
                                         actor=str(actor.id))
    db.commit()
    db.refresh(line)
    return {"id": line.id, "status": line.status, "resolution": line.resolution, "matched_by": line.matched_by}


@router.post("/reconciliations/{reconciliation_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_reconciliation(reconciliation_id: str, body: TransitionBody, db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("tesoreria", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    rec = _owned(db, Reconciliation, reconciliation_id, ctx.company_id, "RECONCILIATION_NOT_FOUND", "Conciliación no encontrada")
    treasury_service.transition_reconciliation(db, reconciliation_id=str(rec.id), target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(rec)
    return treasury_service.reconciliation_dict(db, rec)


# --------------------------------------------------------------------------- #
# IGTF por regla y evento
# --------------------------------------------------------------------------- #
@router.get("/fiscal-rules")
def list_fiscal_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(FiscalRule).where(FiscalRule.company_id == ctx.company_id)
                       .order_by(FiscalRule.rule_code)).scalars().all()
    return {"items": [{"id": r.id, "rule_code": r.rule_code, "name": r.name, "rule_type": r.rule_type,
                       "version": r.version, "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                       "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                       "params": r.params, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/fiscal-rules", dependencies=[Depends(require_write_allowed)])
def create_fiscal_rule(body: FiscalRuleCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    r = treasury_service.create_fiscal_rule(db, company_id=ctx.company_id, rule_code=body.rule_code, name=body.name,
                                            rule_type=body.rule_type, version=body.version,
                                            effective_from=body.effective_from, effective_to=body.effective_to,
                                            params=body.params, actor=str(actor.id))
    db.commit()
    db.refresh(r)
    return {"id": r.id, "rule_code": r.rule_code, "rule_type": r.rule_type, "version": r.version, "status": r.status}


@router.get("/igft-events")
def list_igft_events(event_type: str | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(IgftEvent).where(IgftEvent.company_id == ctx.company_id)
    if event_type:
        query = query.where(IgftEvent.event_type == event_type)
    items = db.execute(query.order_by(IgftEvent.evaluated_at.desc())).scalars().all()
    return {"items": [treasury_service.igft_event_dict(e) for e in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/igft-events/evaluate", dependencies=[Depends(require_write_allowed)])
def evaluate_igft(body: IgftEvaluateBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("tesoreria", "create")), ctx: CompanyContext = Depends(get_company_context)):
    event = treasury_service.evaluate_igft(db, company_id=ctx.company_id, event_type=body.event_type,
                                           source_document=body.source_document, amount=body.amount,
                                           currency=body.currency, on_date=body.on_date)
    db.commit()
    db.refresh(event)
    return treasury_service.igft_event_dict(event)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
