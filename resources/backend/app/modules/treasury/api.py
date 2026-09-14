"""API de tesorería (006).

Endpoints REST `/treasury/*` con las convenciones heredadas (DOC-03 §14):
errores uniformes, `allowed_actions` en backend, transiciones explícitas,
idempotencia en POST críticos (ejecución de ingresos/egresos).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.treasury import rates
from app.modules.treasury import service as treasury_service
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    CashSession,
    Currency,
    ExchangeRate,
    ExchangeRateImportBatch,
    ExchangeRatePolicy,
    ExchangeRateSource,
    FinancialAccount,
    FinancialBank,
    FiscalRule,
    IgftEvent,
    PaymentMethod,
    Reconciliation,
    TreasuryFxConversion,
    TreasuryFxPolicy,
    TreasuryInstrument,
    TreasuryRefund,
    TreasuryTransfer,
)
from app.shared.money import texto_de_salida, texto_decimal

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
    #: `Decimal`, no `float`. La columna siempre fue exacta y la anotación del
    #: borde era la que mentía: familia `KQA-100`.
    rate: Decimal = Field(gt=0)
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


# Spec 038 · FLOAT-038-A — el importe del movimiento bancario es texto decimal
# exacto al entrar y al salir (OQ-FLOAT-038-A-01), y lo que no cabe en su columna
# se rechaza sin redondear (OQ-FLOAT-038-A-02). La escala y la precisión se leen
# de la columna: no hay un `2` ni un `18` escritos aquí.
ImporteBancario = texto_decimal(BankTransaction.__table__.c.amount.type, positivo=True)
#: La comisión no tenía regla de signo y este delta no inventa una.
ComisionBancaria = texto_decimal(BankTransaction.__table__.c.commission.type, positivo=False)
ImporteBancarioSalida = texto_de_salida(BankTransaction.__table__.c.amount.type)


class BankTransactionCreate(BaseModel):
    account_id: str
    direction: str = Field(pattern="^(IN|OUT)$")
    amount: ImporteBancario
    currency: str = "VED"
    txn_date: date | None = None
    value_date: date | None = None
    reference: str | None = None
    source: str = "ADJUSTMENT"
    commission: ComisionBancaria | None = None


class BankTransactionOut(BaseModel):
    id: str
    account_id: str
    txn_date: str | None
    value_date: str | None
    direction: str
    amount: ImporteBancarioSalida
    currency: str
    reference: str | None
    source: str
    payment_id: str | None
    commission: ImporteBancarioSalida | None
    status: str


class BankTransactionPage(BaseModel):
    items: list[BankTransactionOut]
    total: int
    page: int
    page_size: int


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
                                    notes=body.notes, actor=str(actor.id))
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
@router.get("/bank-transactions", response_model=BankTransactionPage)
def list_bank_transactions(account_id: str | None = None, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(BankTransaction).where(BankTransaction.company_id == ctx.company_id)
    if account_id:
        query = query.where(BankTransaction.account_id == account_id)
    items = db.execute(query.order_by(BankTransaction.txn_date.desc())).scalars().all()
    return {"items": [treasury_service.bank_transaction_dict(bt) for bt in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.post("/bank-transactions", response_model=BankTransactionOut, dependencies=[Depends(require_write_allowed)])
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
                 actor: User = Depends(require_permission("tesoreria", "approve")),
                 ctx: CompanyContext = Depends(get_company_context)):
    line = treasury_service.resolve_line(db, company_id=ctx.company_id, line_id=line_id,
                                         resolution_type=body.resolution_type,
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


# --------------------------------------------------------------------------- #
# Spec 038 · política cambiaria, conversión explícita y reembolso
#
# Dos decisiones expresas del owner: el reembolso de un crédito a favor se
# soporta —explícito, aprobado, ejecutado desde tesorería— y la política
# cambiaria es parametrizable con conversión explícita.
#
# Ninguna regla legal venezolana se escribe aquí: la política se configura, se
# versiona y guarda de qué autoridad viene. `D0-07` sigue abierto.
# --------------------------------------------------------------------------- #
class FxPolicyBody(BaseModel):
    policy_code: str = Field(min_length=1, max_length=64)
    functional_currency: str = Field(min_length=1, max_length=8)
    effective_from: date
    effective_date_basis: str = "SETTLEMENT"
    rate_source: str | None = None
    rate_type: str | None = None
    allow_cross_currency: bool = False
    allow_manual_rate: bool = False
    allow_refund: bool = False
    authority_reference: str | None = None


class FxConversionBody(BaseModel):
    source_account_id: str
    target_account_id: str
    source_amount: Decimal = Field(gt=0)
    on_date: date | None = None
    manual_rate: Decimal | None = Field(default=None, gt=0)
    manual_reason: str | None = None
    idempotency_key: str | None = None


class RefundRequestBody(BaseModel):
    credit_note_id: str
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)
    account_id: str | None = None
    payment_method_id: str | None = None
    beneficiary_reference: str | None = None
    idempotency_key: str | None = None


class RefundDecisionBody(BaseModel):
    approved: bool
    reason: str | None = None


class RefundSettleBody(BaseModel):
    account_id: str | None = None


@router.get("/fx-policies")
def list_fx_policies(db: Session = Depends(get_db),
                     user: User = Depends(require_permission("tesoreria", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TreasuryFxPolicy).where(
        TreasuryFxPolicy.company_id == ctx.company_id)
        .order_by(TreasuryFxPolicy.policy_code, TreasuryFxPolicy.version.desc())).scalars().all()
    return {"items": [{"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
                       "functional_currency": p.functional_currency,
                       "effective_date_basis": p.effective_date_basis,
                       "rate_source": p.rate_source, "rate_type": p.rate_type,
                       "allow_cross_currency": p.allow_cross_currency,
                       "allow_manual_rate": p.allow_manual_rate,
                       "allow_refund": p.allow_refund,
                       "authority_reference": p.authority_reference,
                       "effective_from": p.effective_from.isoformat(),
                       "effective_to": p.effective_to.isoformat() if p.effective_to else None,
                       "status": p.status} for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/fx-policies", dependencies=[Depends(require_write_allowed)])
def create_fx_policy(body: FxPolicyBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("tesoreria", "create")),
                     ctx: CompanyContext = Depends(get_company_context)):
    """Crea una versión de política. Nace en borrador: activarla es otro acto."""
    p = treasury_service.create_fx_policy(
        db, company_id=ctx.company_id, policy_code=body.policy_code,
        functional_currency=body.functional_currency, effective_from=body.effective_from,
        effective_date_basis=body.effective_date_basis, rate_source=body.rate_source,
        rate_type=body.rate_type, allow_cross_currency=body.allow_cross_currency,
        allow_manual_rate=body.allow_manual_rate, allow_refund=body.allow_refund,
        authority_reference=body.authority_reference, actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
            "status": p.status}


@router.post("/fx-policies/{policy_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_fx_policy(policy_id: str, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("tesoreria", "approve")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Activa la versión y **sustituye** la anterior, sin borrarla."""
    p = treasury_service.activate_fx_policy(db, company_id=ctx.company_id, policy_id=policy_id,
                                            actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
            "status": p.status,
            "effective_from": p.effective_from.isoformat()}


@router.post("/fx-conversions", dependencies=[Depends(require_write_allowed)])
def create_fx_conversion(body: FxConversionBody, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("tesoreria", "create")),
                         ctx: CompanyContext = Depends(get_company_context)):
    """Cambia dinero de moneda: dos movimientos y una instantánea de tasa."""
    conv = treasury_service.convert_currency(
        db, company_id=ctx.company_id, source_account_id=body.source_account_id,
        target_account_id=body.target_account_id, source_amount=body.source_amount,
        on_date=body.on_date, manual_rate=body.manual_rate, manual_reason=body.manual_reason,
        idempotency_key=body.idempotency_key, actor=str(actor.id))
    db.commit()
    db.refresh(conv)
    return treasury_service.fx_conversion_dict(db, conv)


@router.get("/fx-conversions")
def list_fx_conversions(db: Session = Depends(get_db),
                        user: User = Depends(require_permission("tesoreria", "view")),
                        ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TreasuryFxConversion).where(
        TreasuryFxConversion.company_id == ctx.company_id)
        .order_by(TreasuryFxConversion.created_at.desc())).scalars().all()
    return {"items": [treasury_service.fx_conversion_dict(db, c) for c in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/refunds")
def list_refunds(status: str | None = None, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("tesoreria", "view")),
                 ctx: CompanyContext = Depends(get_company_context)):
    consulta = select(TreasuryRefund).where(TreasuryRefund.company_id == ctx.company_id)
    if status:
        consulta = consulta.where(TreasuryRefund.status == status)
    items = db.execute(consulta.order_by(TreasuryRefund.created_at.desc())).scalars().all()
    return {"items": [treasury_service.refund_dict(r) for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/refunds/{refund_id}")
def get_refund(refund_id: str, db: Session = Depends(get_db),
               user: User = Depends(require_permission("tesoreria", "view")),
               ctx: CompanyContext = Depends(get_company_context)):
    refund = treasury_service._require_refund(db, ctx.company_id, refund_id)
    return treasury_service.refund_dict(refund)


@router.post("/refunds", dependencies=[Depends(require_write_allowed)])
def request_refund(body: RefundRequestBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("tesoreria", "create")),
                   ctx: CompanyContext = Depends(get_company_context)):
    """Solicita la devolución y **reserva** el crédito: desde aquí no se aplica."""
    refund = treasury_service.request_refund(
        db, company_id=ctx.company_id, credit_note_id=body.credit_note_id,
        amount=body.amount, reason=body.reason, account_id=body.account_id,
        payment_method_id=body.payment_method_id,
        beneficiary_reference=body.beneficiary_reference,
        idempotency_key=body.idempotency_key, actor=str(actor.id))
    db.commit()
    db.refresh(refund)
    return treasury_service.refund_dict(refund)


@router.post("/refunds/{refund_id}/decide", dependencies=[Depends(require_write_allowed)])
def decide_refund(refund_id: str, body: RefundDecisionBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("tesoreria", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """Aprueba o deniega. Denegar libera la reserva: el crédito vuelve."""
    refund = treasury_service.decide_refund(db, company_id=ctx.company_id, refund_id=refund_id,
                                            approved=body.approved, reason=body.reason,
                                            actor=str(actor.id))
    db.commit()
    db.refresh(refund)
    return treasury_service.refund_dict(refund)


@router.post("/refunds/{refund_id}/settle", dependencies=[Depends(require_write_allowed)])
def settle_refund(refund_id: str, body: RefundSettleBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("tesoreria", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """Ejecuta el pago: sale el dinero y la reserva se convierte en devuelto."""
    refund = treasury_service.settle_refund(db, company_id=ctx.company_id, refund_id=refund_id,
                                            account_id=body.account_id, actor=str(actor.id))
    db.commit()
    db.refresh(refund)
    return treasury_service.refund_dict(refund)


@router.get("/cash-position")
def cash_position(db: Session = Depends(get_db),
                  user: User = Depends(require_permission("tesoreria", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """La posición real por cuenta y por moneda. **No convierte nada.**"""
    return treasury_service.cash_position(db, company_id=ctx.company_id)


@router.get("/accounts/{account_id}/balance")
def account_balance(account_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("tesoreria", "view")),
                    ctx: CompanyContext = Depends(get_company_context)):
    """El saldo calculado desde los movimientos, no un campo guardado."""
    saldo = treasury_service.account_balance(db, company_id=ctx.company_id, account_id=account_id)
    return {"account_id": account_id, "balance": str(saldo)}


# --------------------------------------------------------------------------- #
# Spec 013 · maestros financieros
#
# La autoridad de la tasa: monedas, fuentes, política de resolución,
# observaciones con par explícito, importación y consulta.
#
# Ninguna regla legal venezolana se escribe aquí y no se llama a ninguna web: la
# ingesta externa es de la Spec 048, que entrega observaciones ya normalizadas.
# --------------------------------------------------------------------------- #
class RateSourceBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    source_type: str = "MANUAL"
    authority_reference: str | None = None
    provider_code: str | None = None
    allows_manual: bool = True
    priority: int = 100
    effective_from: date | None = None


class RateSourceStatusBody(BaseModel):
    status: str = Field(pattern="^(ACTIVE|DISABLED)$")


class RatePolicyBody(BaseModel):
    policy_code: str = Field(min_length=1, max_length=64)
    effective_from: date
    allow_inversion: bool = False
    allow_triangulation: bool = False
    triangulation_currency: str | None = None
    max_age_days: int | None = Field(default=None, ge=0)
    carry_forward: bool = True
    require_rate_approval: bool = False
    rate_scale: int = Field(default=6, ge=0, le=12)
    authority_reference: str | None = None


class RateObservationBody(BaseModel):
    base_currency: str = Field(min_length=1, max_length=8)
    quote_currency: str = Field(min_length=1, max_length=8)
    #: `Decimal`, no `float`. La tasa es dinero y el borde también cuenta.
    rate: Decimal = Field(gt=0)
    effective_at: datetime
    source_id: str | None = None
    rate_type: str = "REFERENCE"
    published_at: datetime | None = None
    reason: str | None = None
    source_reference: str | None = None
    authority_reference: str | None = None


class RateCorrectionBody(BaseModel):
    rate: Decimal = Field(gt=0)
    reason: str = Field(min_length=3, max_length=1000)


class RateImportBody(BaseModel):
    source_id: str
    rate_type: str = "REFERENCE"
    filename: str | None = None
    #: El contenido del CSV. La subida de fichero la hace el navegador; aquí
    #: llega su texto, que es lo que se valida y de lo que sale el hash.
    content: str = Field(min_length=1)


def _fuente_dict(f) -> dict:
    return {"id": str(f.id), "code": f.code, "name": f.name, "source_type": f.source_type,
            "authority_reference": f.authority_reference, "provider_code": f.provider_code,
            "allows_manual": f.allows_manual, "priority": f.priority, "status": f.status,
            "effective_from": f.effective_from.isoformat() if f.effective_from else None,
            "effective_to": f.effective_to.isoformat() if f.effective_to else None,
            "last_sync_at": f.last_sync_at.isoformat() if f.last_sync_at else None,
            "last_success_at": f.last_success_at.isoformat() if f.last_success_at else None,
            "last_error": f.last_error}


def _observacion_dict(db: Session, o) -> dict:
    base = db.get(Currency, str(o.base_currency_id)) if o.base_currency_id else None
    quote = db.get(Currency, str(o.quote_currency_id)) if o.quote_currency_id else None
    fuente = db.get(ExchangeRateSource, str(o.source_id)) if o.source_id else None
    return {"id": str(o.id), "base_currency": base.code if base else None,
            "quote_currency": quote.code if quote else None, "rate": str(o.rate),
            "rate_type": o.rate_type, "status": o.status, "version": o.version,
            "source_id": str(o.source_id) if o.source_id else None,
            "source_code": fuente.code if fuente else o.source,
            "effective_at": o.effective_at.isoformat() if o.effective_at else None,
            "published_at": o.published_at.isoformat() if o.published_at else None,
            "observed_at": o.observed_at.isoformat() if o.observed_at else None,
            "supersedes_id": str(o.supersedes_id) if o.supersedes_id else None,
            "import_batch_id": str(o.import_batch_id) if o.import_batch_id else None,
            "provider_observation_id": o.provider_observation_id,
            "source_reference": o.source_reference, "reason": o.reason,
            "entered_by": o.entered_by, "approved_by": o.approved_by}


@router.get("/rate-sources")
def list_rate_sources(db: Session = Depends(get_db),
                      user: User = Depends(require_permission("tesoreria", "view")),
                      ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(ExchangeRateSource).where(
        ExchangeRateSource.company_id == ctx.company_id)
        .order_by(ExchangeRateSource.priority, ExchangeRateSource.code)).scalars().all()
    return {"items": [_fuente_dict(f) for f in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/rate-sources", dependencies=[Depends(require_write_allowed)])
def create_rate_source(body: RateSourceBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("tesoreria", "create")),
                       ctx: CompanyContext = Depends(get_company_context)):
    f = rates.create_source(db, company_id=ctx.company_id, code=body.code, name=body.name,
                            source_type=body.source_type,
                            authority_reference=body.authority_reference,
                            provider_code=body.provider_code, allows_manual=body.allows_manual,
                            priority=body.priority, effective_from=body.effective_from,
                            actor=str(actor.id))
    db.commit()
    db.refresh(f)
    return _fuente_dict(f)


@router.post("/rate-sources/{source_id}/status", dependencies=[Depends(require_write_allowed)])
def set_rate_source_status(source_id: str, body: RateSourceStatusBody,
                           db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("tesoreria", "approve")),
                           ctx: CompanyContext = Depends(get_company_context)):
    """Desactivar una fuente no borra su historia: deja de producir tasas nuevas."""
    f = rates.set_source_status(db, company_id=ctx.company_id, source_id=source_id,
                                status=body.status, actor=str(actor.id))
    db.commit()
    db.refresh(f)
    return _fuente_dict(f)


@router.get("/rate-policies")
def list_rate_policies(db: Session = Depends(get_db),
                       user: User = Depends(require_permission("tesoreria", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(ExchangeRatePolicy).where(
        ExchangeRatePolicy.company_id == ctx.company_id)
        .order_by(ExchangeRatePolicy.policy_code,
                  ExchangeRatePolicy.version.desc())).scalars().all()
    return {"items": [{"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
                       "allow_inversion": p.allow_inversion,
                       "allow_triangulation": p.allow_triangulation,
                       "triangulation_currency": p.triangulation_currency,
                       "max_age_days": p.max_age_days, "carry_forward": p.carry_forward,
                       "require_rate_approval": p.require_rate_approval,
                       "rate_scale": p.rate_scale,
                       "authority_reference": p.authority_reference,
                       "status": p.status,
                       "effective_from": p.effective_from.isoformat(),
                       "effective_to": p.effective_to.isoformat() if p.effective_to else None}
                      for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/rate-policies", dependencies=[Depends(require_write_allowed)])
def create_rate_policy(body: RatePolicyBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("tesoreria", "create")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Crea una versión de política de resolución. Nace en borrador."""
    p = rates.create_policy(db, company_id=ctx.company_id, policy_code=body.policy_code,
                            effective_from=body.effective_from,
                            allow_inversion=body.allow_inversion,
                            allow_triangulation=body.allow_triangulation,
                            triangulation_currency=body.triangulation_currency,
                            max_age_days=body.max_age_days, carry_forward=body.carry_forward,
                            require_rate_approval=body.require_rate_approval,
                            rate_scale=body.rate_scale,
                            authority_reference=body.authority_reference, actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
            "status": p.status}


@router.post("/rate-policies/{policy_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_rate_policy(policy_id: str, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("tesoreria", "approve")),
                         ctx: CompanyContext = Depends(get_company_context)):
    p = rates.activate_policy(db, company_id=ctx.company_id, policy_id=policy_id,
                              actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": str(p.id), "policy_code": p.policy_code, "version": p.version,
            "status": p.status}


@router.get("/exchange-rates/observations")
def list_rate_observations(base_currency: str | None = None, quote_currency: str | None = None,
                           source_id: str | None = None, status: str | None = None,
                           date_from: date | None = None, date_to: date | None = None,
                           page: int = 1, page_size: int = 50,
                           db: Session = Depends(get_db),
                           user: User = Depends(require_permission("tesoreria", "view")),
                           ctx: CompanyContext = Depends(get_company_context)):
    """El histórico, paginado con `page`/`page_size`, que es el contrato real."""
    tam = max(1, min(page_size, 100))
    consulta = select(ExchangeRate).where(ExchangeRate.company_id == ctx.company_id)
    if base_currency:
        cur = rates.moneda_por_codigo(db, ctx.company_id, base_currency.upper())
        consulta = consulta.where(ExchangeRate.base_currency_id == (str(cur.id) if cur else None))
    if quote_currency:
        cur = rates.moneda_por_codigo(db, ctx.company_id, quote_currency.upper())
        consulta = consulta.where(ExchangeRate.quote_currency_id == (str(cur.id) if cur else None))
    if source_id:
        consulta = consulta.where(ExchangeRate.source_id == source_id)
    if status:
        consulta = consulta.where(ExchangeRate.status == status)
    if date_from:
        consulta = consulta.where(ExchangeRate.rate_date >= date_from)
    if date_to:
        consulta = consulta.where(ExchangeRate.rate_date <= date_to)
    total = db.execute(select(func.count()).select_from(consulta.subquery())).scalar() or 0
    filas = db.execute(
        consulta.order_by(ExchangeRate.effective_at.desc().nullslast(), ExchangeRate.id)
        .limit(tam).offset((max(page, 1) - 1) * tam)).scalars().all()
    return {"items": [_observacion_dict(db, o) for o in filas],
            "total": total, "page": max(page, 1), "page_size": tam}


@router.post("/exchange-rates/observations", dependencies=[Depends(require_write_allowed)])
def create_rate_observation(body: RateObservationBody, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("tesoreria", "create")),
                            ctx: CompanyContext = Depends(get_company_context)):
    """Registra una cotización. **1 base = `rate` quote.**"""
    o = rates.register_rate(db, company_id=ctx.company_id,
                            base_code=body.base_currency.upper(),
                            quote_code=body.quote_currency.upper(), rate=body.rate,
                            effective_at=body.effective_at, source_id=body.source_id,
                            rate_type=body.rate_type, published_at=body.published_at,
                            reason=body.reason, source_reference=body.source_reference,
                            authority_reference=body.authority_reference, actor=str(actor.id))
    db.commit()
    db.refresh(o)
    return _observacion_dict(db, o)


@router.post("/exchange-rates/observations/{observation_id}/correct",
             dependencies=[Depends(require_write_allowed)])
def correct_rate_observation(observation_id: str, body: RateCorrectionBody,
                             db: Session = Depends(get_db),
                             actor: User = Depends(require_permission("tesoreria", "create")),
                             ctx: CompanyContext = Depends(get_company_context)):
    """Una corrección **sucede** a la anterior; la original se conserva."""
    o = rates.correct_rate(db, company_id=ctx.company_id, observation_id=observation_id,
                           rate=body.rate, reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(o)
    return _observacion_dict(db, o)


@router.post("/exchange-rates/observations/{observation_id}/approve",
             dependencies=[Depends(require_write_allowed)])
def approve_rate_observation(observation_id: str, db: Session = Depends(get_db),
                             actor: User = Depends(require_permission("tesoreria", "approve")),
                             ctx: CompanyContext = Depends(get_company_context)):
    o = rates.approve_rate(db, company_id=ctx.company_id, observation_id=observation_id,
                           actor=str(actor.id))
    db.commit()
    db.refresh(o)
    return _observacion_dict(db, o)


@router.get("/exchange-rates/resolve")
def resolve_exchange_rate(base_currency: str, quote_currency: str,
                          effective_at: datetime | None = None, rate_type: str | None = None,
                          source_code: str | None = None, db: Session = Depends(get_db),
                          user: User = Depends(require_permission("tesoreria", "view")),
                          ctx: CompanyContext = Depends(get_company_context)):
    """La tasa que gobierna una operación, con su procedencia.

    Nunca devuelve un número pelado: si no hay tasa, devuelve el error de
    dominio, porque entre monedas distintas «no la hay» y «vale uno» no son lo
    mismo.
    """
    r = rates.resolve_rate(db, company_id=ctx.company_id,
                           base_code=base_currency.upper(), quote_code=quote_currency.upper(),
                           effective_at=effective_at, rate_type=rate_type,
                           source_code=source_code)
    return {"base_currency": r.base_code, "quote_currency": r.quote_code, "rate": str(r.rate),
            "meaning": f"1 {r.base_code} = {r.rate} {r.quote_code}",
            "observation_id": r.observation_id, "source_code": r.source_code,
            "rate_type": r.rate_type,
            "effective_at": r.effective_at.isoformat() if r.effective_at else None,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "observed_at": r.observed_at.isoformat() if r.observed_at else None,
            "version": r.version, "status": r.status, "identity": r.identity,
            "derived": r.derived, "derived_from": list(r.derived_from)}


@router.get("/exchange-rates/import-batches")
def list_import_batches(db: Session = Depends(get_db),
                        user: User = Depends(require_permission("tesoreria", "view")),
                        ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(ExchangeRateImportBatch).where(
        ExchangeRateImportBatch.company_id == ctx.company_id)
        .order_by(ExchangeRateImportBatch.created_at.desc())).scalars().all()
    return {"items": [{"id": str(b.id), "filename": b.filename, "status": b.status,
                       "rows": b.row_count, "imported": b.imported_count,
                       "rejected": b.rejected_count,
                       "source_id": str(b.source_id), "rate_type": b.rate_type,
                       "created_at": b.created_at.isoformat() if b.created_at else None}
                      for b in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/exchange-rates/import", dependencies=[Depends(require_write_allowed)])
def import_exchange_rates(body: RateImportBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("tesoreria", "create")),
                          ctx: CompanyContext = Depends(get_company_context)):
    """Carga masiva. Ninguna fila inválida se descarta en silencio."""
    resultado = rates.import_rates(db, company_id=ctx.company_id, contenido=body.content,
                                   source_id=body.source_id, rate_type=body.rate_type,
                                   filename=body.filename, actor=str(actor.id))
    db.commit()
    return resultado
