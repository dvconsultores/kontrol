"""API del núcleo fiscal (007).

Endpoints REST `/fiscal/*` con las convenciones heredadas: errores uniformes,
`allowed_actions` en backend, transiciones explícitas e idempotencia en POST
críticos (emisión).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_tenant_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.fiscal import service as fiscal_service
from app.modules.fiscal.models import (
    ControlNumber,
    ControlNumberBatch,
    CreditDebitNote,
    FiscalDocument,
    FiscalNumberSeries,
    FiscalPeriod,
    LegalSource,
    PrintEvent,
    TaxCalculation,
    TaxReturnBatch,
    TaxRuleVersion,
    WithholdingRule,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/fiscal", tags=["fiscal"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class LegalSourceCreate(BaseModel):
    authority: str = Field(min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=32)
    number: str | None = None
    gazette: str | None = None
    publication_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    file_id: str | None = None
    source_hash: str | None = None


class TaxRuleCreate(BaseModel):
    tax_code: str = Field(min_length=1, max_length=64)
    legal_source_id: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    rate: dict | float | None = None
    conditions: dict | None = None
    fiscal_release: str | None = None


class TaxProfileCreate(BaseModel):
    scope: str = Field(pattern="^(COMPANY|PARTY|ITEM)$")
    party_id: str | None = None
    item_id: str | None = None
    classifications: dict | None = None
    validity_from: date | None = None
    validity_to: date | None = None
    source: str | None = None


class TaxCalculateBody(BaseModel):
    tax_code: str
    base: float = Field(ge=0)
    on_date: date | None = None
    document_ref: str | None = None
    line_ref: str | None = None


class NumberSeriesCreate(BaseModel):
    document_type: str = Field(min_length=1, max_length=32)
    prefix: str | None = None
    establishment_id: str | None = None


class ControlBatchCreate(BaseModel):
    range_from: str = Field(min_length=1, max_length=32)
    range_to: str = Field(min_length=1, max_length=32)
    establishment_id: str | None = None
    printer: str | None = None
    received_at: date | None = None


class EmitBody(BaseModel):
    business_document: str = Field(min_length=1, max_length=200)
    series_id: str
    batch_id: str
    idempotency_key: str | None = None


class PrintBody(BaseModel):
    copy_type: str = "ORIGINAL"
    printer: str | None = None
    reason: str | None = None


class NoteCreate(BaseModel):
    original_document: str = Field(min_length=1, max_length=200)
    note_type: str = Field(pattern="^(CREDIT|DEBIT)$")
    cause: str = Field(min_length=3, max_length=255)
    amount: float = Field(gt=0)
    base_amount: float = 0.0
    tax_amount: float = 0.0
    inventory_effect: str | None = None
    financial_effect: str | None = None


class WithholdingRuleCreate(BaseModel):
    tax_type: str = Field(pattern="^(IVA|ISLR)$")
    code: str = Field(min_length=1, max_length=64)
    rate: float = Field(ge=0)
    concept: str | None = None
    conditions: dict | None = None
    minimum: float | None = None
    subtractor: float | None = None


class WithholdingCalcBody(BaseModel):
    party_id: str
    tax_type: str = Field(pattern="^(IVA|ISLR)$")
    code: str
    base: float = Field(ge=0)
    period: str | None = None
    source_event: str | None = None


class WithholdingCertificateBody(BaseModel):
    certificate_ref: str = Field(min_length=1, max_length=200)


class PeriodCreate(BaseModel):
    tax_type: str = Field(min_length=1, max_length=24)
    period_key: str = Field(min_length=1, max_length=12)
    start: date | None = None
    end: date | None = None
    deadlines: dict | None = None


class ReturnBatchCreate(BaseModel):
    tax_type: str = Field(min_length=1, max_length=24)
    period: str = Field(min_length=1, max_length=12)
    files: dict | None = None
    totals: dict | None = None


class TransitionBody(BaseModel):
    target: str


# --------------------------------------------------------------------------- #
# Reglas y perfiles fiscales
# --------------------------------------------------------------------------- #
@router.get("/legal-sources")
def list_legal_sources(db: Session = Depends(get_db), _: User = Depends(require_permission("fiscal", "view"))):
    items = db.execute(select(LegalSource).order_by(LegalSource.created_at.desc())).scalars().all()
    return {"items": [{"id": s.id, "authority": s.authority, "source_type": s.source_type, "number": s.number,
                       "gazette": s.gazette, "status": s.status} for s in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/legal-sources", dependencies=[Depends(require_write_allowed)])
def create_legal_source(body: LegalSourceCreate, db: Session = Depends(get_db),
                        actor: User = Depends(require_tenant_permission("fiscal", "create"))):
    src = fiscal_service.create_legal_source(db, authority=body.authority, source_type=body.source_type,
                                             number=body.number, gazette=body.gazette,
                                             publication_date=body.publication_date,
                                             effective_from=body.effective_from, effective_to=body.effective_to,
                                             file_id=body.file_id, source_hash=body.source_hash, actor=str(actor.id))
    db.commit()
    db.refresh(src)
    return {"id": src.id, "authority": src.authority, "source_type": src.source_type, "status": src.status}


@router.post("/legal-sources/{source_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_legal_source(source_id: str, db: Session = Depends(get_db),
                          actor: User = Depends(require_tenant_permission("fiscal", "approve"))):
    src = fiscal_service.activate_legal_source(db, source_id=source_id, actor=str(actor.id))
    db.commit()
    db.refresh(src)
    return {"id": src.id, "status": src.status}


@router.get("/tax-rule-versions")
def list_tax_rules(tax_code: str | None = None, db: Session = Depends(get_db),
                   _: User = Depends(require_permission("fiscal", "view"))):
    query = select(TaxRuleVersion)
    if tax_code:
        query = query.where(TaxRuleVersion.tax_code == tax_code)
    items = db.execute(query.order_by(TaxRuleVersion.tax_code, TaxRuleVersion.version)).scalars().all()
    return {"items": [{"id": r.id, "tax_code": r.tax_code, "version": r.version,
                       "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                       "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                       "rate": r.rate, "fiscal_release": r.fiscal_release, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/tax-rule-versions", dependencies=[Depends(require_write_allowed)])
def create_tax_rule(body: TaxRuleCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_tenant_permission("fiscal", "create"))):
    rule = fiscal_service.create_tax_rule(db, tax_code=body.tax_code, legal_source_id=body.legal_source_id,
                                          effective_from=body.effective_from, effective_to=body.effective_to,
                                          rate=body.rate, conditions=body.conditions,
                                          fiscal_release=body.fiscal_release, actor=str(actor.id))
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "tax_code": rule.tax_code, "status": rule.status}


@router.post("/tax-rule-versions/{rule_id}/approve", dependencies=[Depends(require_write_allowed)])
def approve_tax_rule(rule_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_tenant_permission("fiscal", "approve"))):
    rule = fiscal_service.approve_tax_rule(db, rule_id=rule_id, approver=str(actor.id))
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "tax_code": rule.tax_code, "status": rule.status}


@router.post("/tax-profiles", dependencies=[Depends(require_write_allowed)])
def create_tax_profile(body: TaxProfileCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    profile = fiscal_service.create_tax_profile(db, company_id=ctx.company_id, scope=body.scope,
                                                party_id=body.party_id, item_id=body.item_id,
                                                classifications=body.classifications,
                                                validity_from=body.validity_from, validity_to=body.validity_to,
                                                source=body.source, actor=str(actor.id))
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "scope": profile.scope, "status": profile.status}


@router.post("/tax-calculations", dependencies=[Depends(require_write_allowed)])
def calculate_tax(body: TaxCalculateBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    calc = fiscal_service.calculate_tax(db, company_id=ctx.company_id, tax_code=body.tax_code, base=body.base,
                                        on_date=body.on_date, document_ref=body.document_ref, line_ref=body.line_ref)
    db.commit()
    db.refresh(calc)
    return {"id": calc.id, "tax_code": body.tax_code, "base": calc.base, "rate": calc.rate,
            "amount": calc.amount, "status": "CALCULATED"}


@router.get("/tax-calculations")
def list_tax_calculations(db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TaxCalculation).where(TaxCalculation.company_id == ctx.company_id)
                       .order_by(TaxCalculation.created_at.desc())).scalars().all()
    return {"items": [{"id": c.id, "document_ref": c.document_ref, "base": c.base, "rate": c.rate,
                       "amount": c.amount} for c in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Numeración y números de control
# --------------------------------------------------------------------------- #
@router.get("/number-series")
def list_number_series(db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(FiscalNumberSeries).where(FiscalNumberSeries.company_id == ctx.company_id)
                       .order_by(FiscalNumberSeries.document_type)).scalars().all()
    return {"items": [{"id": s.id, "establishment_id": s.establishment_id, "document_type": s.document_type,
                       "prefix": s.prefix, "next_number": s.next_number, "validity": s.validity} for s in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/number-series", dependencies=[Depends(require_write_allowed)])
def create_number_series(body: NumberSeriesCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    series = fiscal_service.create_number_series(db, company_id=ctx.company_id, document_type=body.document_type,
                                                 prefix=body.prefix, establishment_id=body.establishment_id,
                                                 actor=str(actor.id))
    db.commit()
    db.refresh(series)
    return {"id": series.id, "document_type": series.document_type, "next_number": series.next_number}


@router.get("/control-batches")
def list_control_batches(db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(ControlNumberBatch).where(ControlNumberBatch.company_id == ctx.company_id)
                       .order_by(ControlNumberBatch.created_at.desc())).scalars().all()
    return {"items": [{"id": b.id, "establishment_id": b.establishment_id, "printer": b.printer,
                       "range_from": b.range_from, "range_to": b.range_to, "status": b.status, "counts": b.counts}
                      for b in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/control-batches", dependencies=[Depends(require_write_allowed)])
def create_control_batch(body: ControlBatchCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    batch = fiscal_service.create_control_batch(db, company_id=ctx.company_id, range_from=body.range_from,
                                                range_to=body.range_to, establishment_id=body.establishment_id,
                                                printer=body.printer, received_at=body.received_at, actor=str(actor.id))
    db.commit()
    db.refresh(batch)
    return {"id": batch.id, "range_from": batch.range_from, "range_to": batch.range_to, "counts": batch.counts}


@router.get("/control-numbers")
def list_control_numbers(batch_id: str | None = None, state: str | None = None, db: Session = Depends(get_db),
                         user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(ControlNumber).where(ControlNumber.company_id == ctx.company_id)
    if batch_id:
        query = query.where(ControlNumber.batch_id == batch_id)
    if state:
        query = query.where(ControlNumber.state == state)
    items = db.execute(query.order_by(ControlNumber.created_at.desc()).limit(500)).scalars().all()
    return {"items": [{"id": c.id, "batch_id": c.batch_id, "value": c.value, "state": c.state,
                       "document_ref": c.document_ref} for c in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Emisión, impresión y notas
# --------------------------------------------------------------------------- #
@router.get("/documents")
def list_documents(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(FiscalDocument).where(FiscalDocument.company_id == ctx.company_id)
    if status:
        query = query.where(FiscalDocument.status == status)
    items = db.execute(query.order_by(FiscalDocument.emitted_at.desc())).scalars().all()
    return {"items": [{"id": d.id, "business_document": d.business_document, "document_type": d.document_type,
                       "series": d.series, "invoice_number": d.invoice_number, "control_number": d.control_number,
                       "fiscal_currency": d.fiscal_currency, "emitted_at": d.emitted_at.isoformat() if d.emitted_at else None,
                       "hash": d.hash, "status": d.status} for d in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    doc = _owned(db, FiscalDocument, document_id, ctx.company_id, "FISCAL_DOCUMENT_NOT_FOUND", "Documento fiscal no encontrado")
    prints = db.execute(select(PrintEvent).where(PrintEvent.fiscal_document_id == document_id)
                        .order_by(PrintEvent.printed_at.desc())).scalars().all()
    return {"id": doc.id, "business_document": doc.business_document, "document_type": doc.document_type,
            "series": doc.series, "invoice_number": doc.invoice_number, "control_number": doc.control_number,
            "fiscal_currency": doc.fiscal_currency, "exchange_rate_snapshot": doc.exchange_rate_snapshot,
            "emitted_at": doc.emitted_at.isoformat() if doc.emitted_at else None, "hash": doc.hash, "status": doc.status,
            "prints": [{"id": p.id, "copy_type": p.copy_type, "printer": p.printer, "user_id": p.user_id,
                        "printed_at": p.printed_at.isoformat() if p.printed_at else None, "reason": p.reason}
                       for p in prints]}


@router.post("/documents/emit", dependencies=[Depends(require_write_allowed)])
def emit_document(body: EmitBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    result = fiscal_service.emit_document(db, company_id=ctx.company_id, business_document=body.business_document,
                                          series_id=body.series_id, batch_id=body.batch_id, actor=str(actor.id))
    db.commit()
    return result


@router.post("/documents/{document_id}/print", dependencies=[Depends(require_write_allowed)])
def register_print(document_id: str, body: PrintBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    doc = _owned(db, FiscalDocument, document_id, ctx.company_id, "FISCAL_DOCUMENT_NOT_FOUND", "Documento fiscal no encontrado")
    event = fiscal_service.register_print(db, company_id=ctx.company_id, fiscal_document_id=str(doc.id),
                                          copy_type=body.copy_type, printer=body.printer, reason=body.reason,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(event)
    return {"id": event.id, "copy_type": event.copy_type, "printed_at": event.printed_at.isoformat() if event.printed_at else None}


@router.post("/credit-debit-notes", dependencies=[Depends(require_write_allowed)])
def create_note(body: NoteCreate, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    note = fiscal_service.create_credit_debit_note(db, company_id=ctx.company_id,
                                                   original_document=body.original_document, note_type=body.note_type,
                                                   cause=body.cause, amount=body.amount, base_amount=body.base_amount,
                                                   tax_amount=body.tax_amount, inventory_effect=body.inventory_effect,
                                                   financial_effect=body.financial_effect, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "original_document": note.original_document, "note_type": note.note_type,
            "amount": note.amount, "limits": note.limits, "status": note.status}


@router.get("/credit-debit-notes")
def list_notes(original_document: str | None = None, db: Session = Depends(get_db),
               user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(CreditDebitNote).where(CreditDebitNote.company_id == ctx.company_id)
    if original_document:
        query = query.where(CreditDebitNote.original_document == original_document)
    items = db.execute(query.order_by(CreditDebitNote.created_at.desc())).scalars().all()
    return {"items": [{"id": n.id, "original_document": n.original_document, "note_type": n.note_type,
                       "cause": n.cause, "amount": n.amount, "status": n.status} for n in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Retenciones
# --------------------------------------------------------------------------- #
@router.get("/withholding-rules")
def list_withholding_rules(tax_type: str | None = None, db: Session = Depends(get_db),
                           user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(WithholdingRule).where(WithholdingRule.company_id == ctx.company_id)
    if tax_type:
        query = query.where(WithholdingRule.tax_type == tax_type)
    items = db.execute(query.order_by(WithholdingRule.code)).scalars().all()
    return {"items": [{"id": r.id, "tax_type": r.tax_type, "code": r.code, "concept": r.concept,
                       "rate": r.rate, "minimum": r.minimum, "subtractor": r.subtractor, "status": r.status}
                      for r in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/withholding-rules", dependencies=[Depends(require_write_allowed)])
def create_withholding_rule(body: WithholdingRuleCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    rule = fiscal_service.create_withholding_rule(db, company_id=ctx.company_id, tax_type=body.tax_type,
                                                  code=body.code, rate=body.rate, concept=body.concept,
                                                  conditions=body.conditions, minimum=body.minimum,
                                                  subtractor=body.subtractor, actor=str(actor.id))
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "tax_type": rule.tax_type, "code": rule.code, "rate": rule.rate, "status": rule.status}


@router.post("/withholdings/calculate", dependencies=[Depends(require_write_allowed)])
def calculate_withholding(body: WithholdingCalcBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    w = fiscal_service.calculate_withholding(db, company_id=ctx.company_id, party_id=body.party_id,
                                             tax_type=body.tax_type, code=body.code, base=body.base,
                                             period=body.period, source_event=body.source_event, actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "tax_type": w.tax_type, "base": w.base, "amount": w.amount, "status": w.status}


@router.post("/withholdings/{withholding_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_withholding(withholding_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("fiscal", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    w = fiscal_service.transition_withholding(db, company_id=ctx.company_id, withholding_id=withholding_id,
                                              target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "status": w.status}


@router.post("/withholdings/{withholding_id}/certificate", dependencies=[Depends(require_write_allowed)])
def issue_certificate(withholding_id: str, body: WithholdingCertificateBody, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    w = fiscal_service.issue_withholding_certificate(db, company_id=ctx.company_id, withholding_id=withholding_id,
                                                     certificate_ref=body.certificate_ref, actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "certificate": w.certificate, "status": w.status}


@router.get("/withholdings")
def list_withholdings(tax_type: str | None = None, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    from app.modules.purchasing.models import Withholding as ApWithholding

    query = select(ApWithholding).where(ApWithholding.company_id == ctx.company_id)
    if tax_type:
        query = query.where(ApWithholding.tax_type == tax_type)
    items = db.execute(query.order_by(ApWithholding.created_at.desc())).scalars().all()
    return {"items": [{"id": w.id, "party_id": w.party_id, "tax_type": w.tax_type, "rule_ref": w.rule_ref,
                       "base": w.base, "amount": w.amount, "period": w.period, "certificate": w.certificate,
                       "status": w.status} for w in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Períodos, declaraciones y libros
# --------------------------------------------------------------------------- #
@router.get("/periods")
def list_periods(tax_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(FiscalPeriod).where(FiscalPeriod.company_id == ctx.company_id)
    if tax_type:
        query = query.where(FiscalPeriod.tax_type == tax_type)
    items = db.execute(query.order_by(FiscalPeriod.period_key.desc())).scalars().all()
    return {"items": [{"id": p.id, "tax_type": p.tax_type, "period_key": p.period_key,
                       "start": p.start.isoformat() if p.start else None, "end": p.end.isoformat() if p.end else None,
                       "status": p.status, "approvals": p.approvals} for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/periods", dependencies=[Depends(require_write_allowed)])
def create_period(body: PeriodCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    period = fiscal_service.create_fiscal_period(db, company_id=ctx.company_id, tax_type=body.tax_type,
                                                 period_key=body.period_key, start=body.start, end=body.end,
                                                 deadlines=body.deadlines, actor=str(actor.id))
    db.commit()
    db.refresh(period)
    return {"id": period.id, "period_key": period.period_key, "status": period.status}


@router.post("/periods/{period_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_period(period_id: str, body: TransitionBody, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("fiscal", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    period = _owned(db, FiscalPeriod, period_id, ctx.company_id, "FISCAL_PERIOD_NOT_FOUND", "Período fiscal no encontrado")
    fiscal_service.transition_period(db, company_id=ctx.company_id, period_id=str(period.id), target=body.target,
                                     actor=str(actor.id))
    db.commit()
    db.refresh(period)
    return {"id": period.id, "period_key": period.period_key, "status": period.status}


@router.post("/tax-return-batches", dependencies=[Depends(require_write_allowed)])
def create_return_batch(body: ReturnBatchCreate, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("fiscal", "create")), ctx: CompanyContext = Depends(get_company_context)):
    batch = fiscal_service.create_tax_return_batch(db, company_id=ctx.company_id, tax_type=body.tax_type,
                                                   period=body.period, files=body.files, totals=body.totals,
                                                   actor=str(actor.id))
    db.commit()
    db.refresh(batch)
    return {"id": batch.id, "tax_type": batch.tax_type, "period": batch.period, "status": batch.status}


@router.get("/tax-return-batches")
def list_return_batches(db: Session = Depends(get_db), user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(TaxReturnBatch).where(TaxReturnBatch.company_id == ctx.company_id)
                       .order_by(TaxReturnBatch.period.desc())).scalars().all()
    return {"items": [{"id": b.id, "tax_type": b.tax_type, "period": b.period, "status": b.status} for b in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/books/{tax_type}")
def get_books(tax_type: str, period: str = "0", db: Session = Depends(get_db),
              user: User = Depends(require_permission("fiscal", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return fiscal_service.books(db, company_id=ctx.company_id, tax_type=tax_type.upper(), period=period)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
