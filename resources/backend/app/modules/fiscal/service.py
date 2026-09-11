"""Servicios del núcleo fiscal (007).

Reglas fiscales versionadas, numeración/correlativos y números de control con
asignación atómica, emisión fiscal inalterable (FiscalDocument + hash),
impresión auditada (PrintEvent), notas con límites al saldo ajustable,
retenciones (reglas propias; instancias reutilizan 004 `ap_withholdings`),
períodos/declaraciones y libros reconstruibles desde documentos y eventos.

Invariantes (DOC-01 §5, DOC-02 §11, DOC-03 §12):
- Emisión consume correlativo y control en transacción atómica.
- Numeración/control no editables; hash de integridad.
- Notas limitan al saldo ajustable del original.
- Libros reconstruibles, nunca tablas editables.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
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
    TaxProfile,
    TaxReturnBatch,
    TaxRuleVersion,
    WithholdingRule,
)
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import SupplierInvoice
from app.modules.purchasing.models import Withholding as ApWithholding
from app.shared import audit as audit_service


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Registra un evento de auditoría de negocio (KAUD-001 → FR-009-022)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _rule_rate(rule: TaxRuleVersion) -> float:
    rate = rule.rate
    if isinstance(rate, dict):
        return float(rate.get("percent", rate.get("rate", 0.0)) or 0.0)
    return float(rate or 0.0)


# --------------------------------------------------------------------------- #
# Reglas fiscales
# --------------------------------------------------------------------------- #
def create_legal_source(db: Session, *, authority: str, source_type: str, number: str | None = None,
                        gazette: str | None = None, publication_date: date | None = None,
                        effective_from: date | None = None, effective_to: date | None = None,
                        file_id: str | None = None, source_hash: str | None = None,
                        actor: str | None = None) -> LegalSource:
    src = LegalSource(authority=authority, source_type=source_type, number=number, gazette=gazette,
                      publication_date=publication_date, effective_from=effective_from, effective_to=effective_to,
                      file_id=file_id, source_hash=source_hash, status="LEGAL_VALIDATION_REQUIRED", created_by=actor)
    db.add(src)
    db.flush()
    return src


def activate_legal_source(db: Session, *, source_id: str, actor: str | None = None) -> LegalSource:
    src = db.get(LegalSource, source_id)
    if not src:
        raise NotFoundError(code="LEGAL_SOURCE_NOT_FOUND", message="Fuente legal no encontrada")
    src.status = "ACTIVE"
    src.updated_at = datetime.now(UTC)
    db.flush()
    return src


def create_tax_rule(db: Session, *, tax_code: str, legal_source_id: str | None = None,
                    effective_from: date | None = None, effective_to: date | None = None,
                    rate: dict | float | None = None, conditions: dict | None = None,
                    fiscal_release: str | None = None, actor: str | None = None) -> TaxRuleVersion:
    """Crea una versión de regla tributaria (FR-007-001); no solapa versiones activas (DOC-03 §12)."""
    if effective_from:
        overlapping = db.execute(select(TaxRuleVersion).where(
            TaxRuleVersion.tax_code == tax_code, TaxRuleVersion.status == "ACTIVE",
            (TaxRuleVersion.effective_to.is_(None)) | (TaxRuleVersion.effective_to >= effective_from),
        )).scalars().first()
        if overlapping:
            raise ConflictError(code="RULE_OVERLAP", message="Ya existe una versión activa de la regla en esa vigencia.")
    rule = TaxRuleVersion(tax_code=tax_code, legal_source_id=legal_source_id, effective_from=effective_from,
                          effective_to=effective_to, rate=rate, conditions=conditions, approval={},
                          fiscal_release=fiscal_release, status="DRAFT", created_by=actor)
    db.add(rule)
    db.flush()
    return rule


def approve_tax_rule(db: Session, *, rule_id: str, approver: str | None = None) -> TaxRuleVersion:
    rule = db.get(TaxRuleVersion, rule_id)
    if not rule:
        raise NotFoundError(code="TAX_RULE_NOT_FOUND", message="Regla fiscal no encontrada")
    _assert_transition(rule.status, "ACTIVE", {"DRAFT": {"ACTIVE"}, "ACTIVE": set(), "INACTIVE": {"ACTIVE"}}, "la regla fiscal")
    rule.status = "ACTIVE"
    rule.approval = {"approved_by": approver, "approved_at": datetime.now(UTC).isoformat()}
    rule.updated_at = datetime.now(UTC)
    db.flush()
    return rule


def _active_tax_rule(db: Session, tax_code: str, on_date: date) -> TaxRuleVersion:
    on = on_date or date.today()
    rule = db.execute(select(TaxRuleVersion).where(
        TaxRuleVersion.tax_code == tax_code, TaxRuleVersion.status == "ACTIVE",
        (TaxRuleVersion.effective_from.is_(None)) | (TaxRuleVersion.effective_from <= on),
        (TaxRuleVersion.effective_to.is_(None)) | (TaxRuleVersion.effective_to >= on),
    ).order_by(TaxRuleVersion.created_at.desc())).scalars().first()
    if not rule:
        raise NotFoundError(code="NO_ACTIVE_TAX_RULE", message=f"No hay una regla fiscal activa para {tax_code}.")
    return rule


def create_tax_profile(db: Session, *, company_id: str, scope: str, party_id: str | None = None,
                       item_id: str | None = None, classifications: dict | None = None,
                       validity_from: date | None = None, validity_to: date | None = None,
                       source: str | None = None, actor: str | None = None) -> TaxProfile:
    company_id = _company(company_id, obj="perfil fiscal")
    profile = TaxProfile(company_id=company_id, scope=scope, party_id=party_id, item_id=item_id,
                         classifications=classifications, validity_from=validity_from, validity_to=validity_to,
                         source=source, status="ACTIVE", created_by=actor)
    db.add(profile)
    db.flush()
    return profile


def calculate_tax(db: Session, *, company_id: str, tax_code: str, base: float,
                  on_date: date | None = None, document_ref: str | None = None,
                  line_ref: str | None = None) -> TaxCalculation:
    """Calcula un impuesto con la regla activa y conserva snapshot (FR-007-004)."""
    company_id = _company(company_id, obj="cálculo fiscal")
    if base < 0:
        raise KontrolError(code="INVALID_BASE", message="La base no puede ser negativa", status_code=422)
    rule = _active_tax_rule(db, tax_code, on_date or date.today())
    rate = _rule_rate(rule)
    amount = round(base * rate / 100.0, 2) if rate > 1 else round(base * rate, 2)
    calc = TaxCalculation(company_id=company_id, document_ref=document_ref, line_ref=line_ref,
                          rule_version_id=str(rule.id), base=base, rate=rate, amount=amount, rounding=2.0,
                          snapshot={"tax_code": tax_code, "fiscal_release": rule.fiscal_release,
                                    "status": rule.status})
    db.add(calc)
    db.flush()
    return calc


# --------------------------------------------------------------------------- #
# Numeración y números de control (asignación atómica)
# --------------------------------------------------------------------------- #
def create_number_series(db: Session, *, company_id: str, document_type: str, prefix: str | None = None,
                         establishment_id: str | None = None, validity: dict | None = None,
                         actor: str | None = None) -> FiscalNumberSeries:
    company_id = _company(company_id, obj="serie fiscal")
    series = FiscalNumberSeries(company_id=company_id, establishment_id=establishment_id, document_type=document_type,
                                prefix=prefix, next_number=1, lock_version=0, validity=validity or {"status": "ACTIVE"},
                                created_by=actor)
    db.add(series)
    db.flush()
    return series


def reserve_number(db: Session, *, company_id: str, series_id: str) -> str:
    """Reserva atómica del siguiente correlativo (FR-007-010)."""
    company_id = _company(company_id, obj="correlativo")
    series = db.get(FiscalNumberSeries, series_id)
    if not series or series.company_id != company_id:
        raise NotFoundError(code="NUMBER_SERIES_NOT_FOUND", message="Serie de numeración no encontrada")
    if (series.validity or {}).get("status") not in (None, "ACTIVE"):
        raise ConflictError(code="SERIES_INACTIVE", message="La serie de numeración no está activa.")
    number = series.next_number
    series.next_number = series.next_number + 1
    series.lock_version = series.lock_version + 1
    series.updated_at = datetime.now(UTC)
    db.flush()
    return f"{series.prefix or ''}{number:07d}"


def create_control_batch(db: Session, *, company_id: str, range_from: str, range_to: str,
                         establishment_id: str | None = None, printer: str | None = None,
                         received_at: date | None = None, actor: str | None = None) -> ControlNumberBatch:
    """Crea un lote de imprenta y materializa los números de control (FR-007-011)."""
    company_id = _company(company_id, obj="lote de control")
    batch = ControlNumberBatch(company_id=company_id, establishment_id=establishment_id, printer=printer,
                               range_from=range_from, range_to=range_to, received_at=received_at,
                               status="AVAILABLE", counts={"generated": 0}, created_by=actor)
    db.add(batch)
    db.flush()
    try:
        start = int(range_from)
        end = int(range_to)
    except ValueError:
        raise KontrolError(code="INVALID_RANGE", message="El rango debe ser numérico", status_code=422) from None
    if start > end or end - start > 100000:
        raise KontrolError(code="INVALID_RANGE", message="Rango de control inválido o excesivo", status_code=422)
    count = 0
    for value in range(start, end + 1):
        db.add(ControlNumber(company_id=company_id, batch_id=str(batch.id), value=str(value), state="AVAILABLE"))
        count += 1
    batch.counts = {"generated": count}
    db.flush()
    return batch


def assign_control(db: Session, *, company_id: str, batch_id: str) -> ControlNumber:
    """Asigna (reserva) un número de control disponible (FR-007-012)."""
    company_id = _company(company_id, obj="número de control")
    batch = db.get(ControlNumberBatch, batch_id)
    if not batch or batch.company_id != company_id:
        raise NotFoundError(code="CONTROL_BATCH_NOT_FOUND", message="Lote de control no encontrado")
    control = db.execute(select(ControlNumber).where(
        ControlNumber.batch_id == batch_id, ControlNumber.state == "AVAILABLE")
        .order_by(ControlNumber.created_at).limit(1)).scalars().first()
    if not control:
        raise ConflictError(code="NO_CONTROL_AVAILABLE", message="No hay números de control disponibles en el lote.")
    control.state = "RESERVED"
    control.updated_at = datetime.now(UTC)
    db.flush()
    return control


def use_control(db: Session, *, control_id: str, document_ref: str) -> ControlNumber:
    control = db.get(ControlNumber, control_id)
    if not control:
        raise NotFoundError(code="CONTROL_NOT_FOUND", message="Número de control no encontrado")
    if control.state != "RESERVED":
        raise ConflictError(code="CONTROL_NOT_RESERVED", message="El número de control debe estar reservado para usarse.")
    control.state = "USED"
    control.document_ref = document_ref
    control.used_at = datetime.now(UTC)
    control.updated_at = datetime.now(UTC)
    db.flush()
    return control


# --------------------------------------------------------------------------- #
# Emisión fiscal (transacción atómica) e impresión
# --------------------------------------------------------------------------- #
def _resolve_invoice(db: Session, company_id: str, invoice_id: str):
    from app.modules.sales.models import SalesInvoice

    sales = db.get(SalesInvoice, invoice_id)
    if sales and sales.company_id == company_id:
        return sales
    supplier = db.get(SupplierInvoice, invoice_id)
    if supplier and supplier.company_id == company_id:
        return supplier
    raise NotFoundError(code="INVOICE_NOT_FOUND", message="La factura a emitir no fue encontrada")


def _canonical_hash(*parts: object) -> str:
    payload = "|".join(str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


#: Lo que este motor sabe emitir. Es el mismo trío que `FiscalDocument`
#: declaraba en su comentario desde el principio.
EMITTABLE_DOCUMENT_TYPES: frozenset[str] = frozenset({"INVOICE", "CREDIT_NOTE", "DEBIT_NOTE"})


def _resolve_note_currency(db: Session, company_id: str, tipo: str, note_id: str) -> str:
    """La moneda de la nota, leída de la nota y acotada por empresa."""
    from app.modules.sales.models import SalesCreditNote, SalesDebitNote

    modelo = SalesCreditNote if tipo == "CREDIT_NOTE" else SalesDebitNote
    nota = db.get(modelo, note_id)
    if nota is None or str(nota.company_id) != str(company_id):
        raise NotFoundError(code="NOTE_NOT_FOUND", message="Nota no encontrada")
    return nota.currency or "VED"


def emit_document(db: Session, *, company_id: str, business_document: str, series_id: str,
                  batch_id: str, actor: str | None = None) -> dict:
    """Emite un documento fiscal: consume correlativo y control en transacción atómica (FR-007-020).

    Idempotente: si el documento ya fue emitido, devuelve el existente.
    """
    company_id = _company(company_id, obj="emisión fiscal")
    existing = db.execute(select(FiscalDocument).where(
        FiscalDocument.company_id == company_id, FiscalDocument.business_document == business_document)
        .order_by(FiscalDocument.created_at)).scalars().first()
    if existing:
        return {"id": str(existing.id), "business_document": business_document, "idempotent": True,
                "invoice_number": existing.invoice_number, "control_number": existing.control_number,
                "hash": existing.hash, "status": existing.status}

    # Delta dirigido de la Spec 036. El modelo declaraba desde el principio
    # «INVOICE / CREDIT_NOTE / DEBIT_NOTE» y este motor solo sabía emitir el
    # primero: el tipo estaba escrito a mano más abajo. La norma exige que la
    # nota de crédito y la de débito tengan «consecutivo propio» y «número de
    # control», y sin esto la 036 habría tenido que numerar por su cuenta, que
    # es exactamente lo que la Spec 042 existe para impedir.
    tipo = business_document.split(":", 1)[0]
    if tipo not in EMITTABLE_DOCUMENT_TYPES or ":" not in business_document:
        raise KontrolError(
            code="INVALID_BUSINESS_DOCUMENT",
            message="El documento debe ser {tipo}:{id} con tipo emitible.",
            details={"allowed": sorted(EMITTABLE_DOCUMENT_TYPES)}, status_code=422)
    referencia_id = business_document.split(":", 1)[1]
    fiscal_currency_default = "VED"
    if tipo == "INVOICE":
        invoice = _resolve_invoice(db, company_id, referencia_id)
        fiscal_currency_default = getattr(invoice, "base_fiscal_currency", "VED") or "VED"
    else:
        fiscal_currency_default = _resolve_note_currency(db, company_id, tipo, referencia_id)

    serie_previa = db.get(FiscalNumberSeries, series_id)
    if serie_previa is not None and serie_previa.document_type != tipo:
        raise KontrolError(
            code="SERIES_DOCUMENT_TYPE_MISMATCH",
            message="La serie no corresponde al tipo de documento que se emite.",
            details={"series_document_type": serie_previa.document_type, "document_type": tipo},
            status_code=422)
    number = reserve_number(db, company_id=company_id, series_id=series_id)
    control = assign_control(db, company_id=company_id, batch_id=batch_id)
    use_control(db, control_id=str(control.id), document_ref=business_document)
    series = db.get(FiscalNumberSeries, series_id)
    series_prefix = series.prefix if series else None

    fiscal_currency = fiscal_currency_default
    emitted_at = datetime.now(UTC)
    doc = FiscalDocument(company_id=company_id, business_document=business_document,
                         document_type=tipo, fiscal_mode="DIGITAL", series=series_prefix,
                         invoice_number=number, control_number=control.value, fiscal_currency=fiscal_currency,
                         exchange_rate_snapshot=1.0, emitted_at=emitted_at, status="EMITTED",
                         created_by=actor)
    doc.hash = _canonical_hash(company_id, business_document, series_prefix, number, control.value,
                               fiscal_currency, emitted_at.isoformat())
    db.add(doc)
    db.flush()
    _audit(db, action="FISCAL_DOCUMENT_EMITTED", entity_type="FiscalDocument", entity_id=str(doc.id),
           company_id=company_id, actor=actor,
           after={"invoice_number": number, "control_number": control.value, "hash": doc.hash})
    return {"id": str(doc.id), "business_document": business_document, "idempotent": False,
            "invoice_number": number, "control_number": control.value, "hash": doc.hash, "status": doc.status}


def register_print(db: Session, *, company_id: str, fiscal_document_id: str, copy_type: str = "ORIGINAL",
                   printer: str | None = None, reason: str | None = None, actor: str | None = None) -> PrintEvent:
    """Registra impresión/reimpresión con motivo y usuario (FR-007-022)."""
    company_id = _company(company_id, obj="impresión fiscal")
    doc = db.get(FiscalDocument, fiscal_document_id)
    if not doc or doc.company_id != company_id:
        raise NotFoundError(code="FISCAL_DOCUMENT_NOT_FOUND", message="Documento fiscal no encontrado")
    event = PrintEvent(company_id=company_id, fiscal_document_id=fiscal_document_id, copy_type=copy_type,
                       printer=printer, user_id=actor, printed_at=datetime.now(UTC), reason=reason)
    printed_at = event.printed_at or datetime.now(UTC)
    event.hash = _canonical_hash(company_id, fiscal_document_id, copy_type, printer, printed_at.isoformat(), reason)
    db.add(event)
    db.flush()
    _audit(db, action="FISCAL_DOCUMENT_PRINTED", entity_type="PrintEvent", entity_id=str(event.id),
           company_id=company_id, actor=actor,
           after={"fiscal_document_id": fiscal_document_id, "copy_type": copy_type})
    return event


def create_credit_debit_note(db: Session, *, company_id: str, original_document: str, note_type: str, cause: str,
                             amount: float, base_amount: float = 0.0, tax_amount: float = 0.0,
                             inventory_effect: str | None = None, financial_effect: str | None = None,
                             actor: str | None = None) -> CreditDebitNote:
    """Nota fiscal con límite al saldo ajustable del original (FR-007-030/031)."""
    company_id = _company(company_id, obj="nota fiscal")
    if note_type not in ("CREDIT", "DEBIT"):
        raise KontrolError(code="INVALID_NOTE_TYPE", message="Tipo de nota inválido", status_code=422)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto de la nota debe ser positivo", status_code=422)
    if not original_document.startswith("INVOICE:"):
        raise KontrolError(code="INVALID_ORIGINAL", message="La nota debe referenciar INVOICE:{id}", status_code=422)
    invoice_id = original_document.split(":", 1)[1]
    invoice = _resolve_invoice(db, company_id, invoice_id)

    invoice_total = float(getattr(invoice, "total", 0.0) or 0.0)
    prior_used = 0.0
    for note in db.execute(select(CreditDebitNote).where(
            CreditDebitNote.company_id == company_id, CreditDebitNote.original_document == original_document,
            CreditDebitNote.note_type == "CREDIT")).scalars().all():
        prior_used += float(note.amount or 0)
    adjustable = round(invoice_total - prior_used, 6)
    if note_type == "CREDIT" and amount > adjustable:
        raise ConflictError(code="NOTE_EXCEEDS_ADJUSTABLE",
                            message=f"La nota excede el saldo ajustable de la factura ({adjustable}).")

    note = CreditDebitNote(company_id=company_id, original_document=original_document, note_type=note_type,
                           cause=cause, amount=amount, base_amount=base_amount, tax_amount=tax_amount,
                           limits={"original_total": invoice_total, "prior_used": prior_used, "adjustable": adjustable},
                           inventory_effect=inventory_effect, financial_effect=financial_effect,
                           status="EMITTED", created_by=actor)
    db.add(note)
    db.flush()
    _audit(db, action="FISCAL_NOTE_EMITTED", entity_type="CreditDebitNote", entity_id=str(note.id),
           company_id=company_id, actor=actor,
           after={"note_type": note_type, "original_document": original_document, "amount": float(amount)})
    return note


# --------------------------------------------------------------------------- #
# Retenciones (reglas en 007; instancias en 004)
# --------------------------------------------------------------------------- #
def create_withholding_rule(db: Session, *, company_id: str, tax_type: str, code: str, rate: float,
                            concept: str | None = None, conditions: dict | None = None,
                            minimum: float | None = None, subtractor: float | None = None,
                            validity: dict | None = None, actor: str | None = None) -> WithholdingRule:
    company_id = _company(company_id, obj="regla de retención")
    rule = WithholdingRule(company_id=company_id, tax_type=tax_type, concept=concept, code=code,
                           conditions=conditions, base=0.0, rate=rate, minimum=minimum, subtractor=subtractor,
                           validity=validity or {}, status="ACTIVE", created_by=actor)
    db.add(rule)
    db.flush()
    return rule


def _active_withholding_rule(db: Session, company_id: str, tax_type: str, code: str) -> WithholdingRule:
    rule = db.execute(select(WithholdingRule).where(
        WithholdingRule.company_id == company_id, WithholdingRule.tax_type == tax_type,
        WithholdingRule.code == code, WithholdingRule.status == "ACTIVE")
        .order_by(WithholdingRule.created_at.desc())).scalars().first()
    if not rule:
        raise NotFoundError(code="NO_WITHHOLDING_RULE", message="Regla de retención no encontrada")
    return rule


def calculate_withholding(db: Session, *, company_id: str, party_id: str, tax_type: str, code: str,
                          base: float, period: str | None = None, source_event: str | None = None,
                          actor: str | None = None) -> ApWithholding:
    """Calcula una retención con la regla activa y la crea en 004 (CALCULADA)."""
    company_id = _company(company_id, obj="retención")
    rule = _active_withholding_rule(db, company_id, tax_type, code)
    rate = float(rule.rate)
    amount = round(float(base) * rate / 100.0, 2) if rate > 1 else round(float(base) * rate, 2)
    if rule.minimum is not None and amount < float(rule.minimum):
        amount = 0.0
    if rule.subtractor is not None:
        amount = round(max(amount - float(rule.subtractor), 0.0), 2)
    return ap_service.create_withholding(db, company_id=company_id, party_id=party_id, tax_type=tax_type,
                                         rule_ref=code, base=base, rate_ref=str(rule.rate), amount=amount,
                                         period=period, source_event=source_event, actor=actor)


def transition_withholding(db: Session, *, company_id: str, withholding_id: str, target: str,
                           actor: str | None = None) -> ApWithholding:
    w = db.get(ApWithholding, withholding_id)
    if not w or w.company_id != company_id:
        raise NotFoundError(code="WITHHOLDING_NOT_FOUND", message="Retención no encontrada")
    return ap_service.transition_withholding(db, withholding=w, target=target)


def issue_withholding_certificate(db: Session, *, company_id: str, withholding_id: str,
                                  certificate_ref: str, actor: str | None = None) -> ApWithholding:
    w = db.get(ApWithholding, withholding_id)
    if not w or w.company_id != company_id:
        raise NotFoundError(code="WITHHOLDING_NOT_FOUND", message="Retención no encontrada")
    w.certificate = certificate_ref
    w.updated_at = datetime.now(UTC)
    db.flush()
    return ap_service.transition_withholding(db, withholding=w, target="EMITIDA")


# --------------------------------------------------------------------------- #
# Períodos, declaraciones y libros reconstruibles
# --------------------------------------------------------------------------- #
def create_fiscal_period(db: Session, *, company_id: str, tax_type: str, period_key: str,
                         start: date | None = None, end: date | None = None, deadlines: dict | None = None,
                         actor: str | None = None) -> FiscalPeriod:
    company_id = _company(company_id, obj="período fiscal")
    period = FiscalPeriod(company_id=company_id, tax_type=tax_type, period_key=period_key, start=start, end=end,
                          deadlines=deadlines, status="OPEN", approvals={}, created_by=actor)
    db.add(period)
    db.flush()
    return period


PERIOD_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"CLOSED"},
    "CLOSED": {"REOPENED"},
    "REOPENED": {"CLOSED"},
}


def transition_period(db: Session, *, company_id: str, period_id: str, target: str,
                      actor: str | None = None) -> FiscalPeriod:
    period = db.get(FiscalPeriod, period_id)
    if not period or period.company_id != company_id:
        raise NotFoundError(code="FISCAL_PERIOD_NOT_FOUND", message="Período fiscal no encontrado")
    _assert_transition(period.status, target, PERIOD_TRANSITIONS, "el período fiscal")
    period.status = target
    period.approvals = {**(period.approvals or {}), target: {"by": actor, "at": datetime.now(UTC).isoformat()}}
    period.updated_at = datetime.now(UTC)
    db.flush()
    return period


def create_tax_return_batch(db: Session, *, company_id: str, tax_type: str, period: str,
                            files: dict | None = None, totals: dict | None = None,
                            actor: str | None = None) -> TaxReturnBatch:
    company_id = _company(company_id, obj="declaración fiscal")
    batch = TaxReturnBatch(company_id=company_id, tax_type=tax_type, period=period, files=files,
                           totals=totals, status="DRAFT", created_by=actor)
    db.add(batch)
    db.flush()
    return batch


def books(db: Session, *, company_id: str, tax_type: str, period: str) -> dict:
    """Libro reconstruible desde documentos y eventos (FR-007-050). Nunca tabla editable."""
    company_id = _company(company_id, obj="libro fiscal")
    from app.modules.treasury.models import IgftEvent

    rows: list[dict] = []
    total_amount = 0.0
    if tax_type == "VENTAS":
        docs = db.execute(select(FiscalDocument).where(
            FiscalDocument.company_id == company_id, FiscalDocument.document_type == "INVOICE")).scalars().all()
        for doc in docs:
            amount = 0.0
            if doc.business_document.startswith("INVOICE:"):
                invoice = _resolve_invoice(db, company_id, doc.business_document.split(":", 1)[1])
                amount = float(getattr(invoice, "total", 0.0) or 0.0)
            total_amount += amount
            rows.append({"document": doc.business_document, "series": doc.series, "number": doc.invoice_number,
                         "control": doc.control_number, "currency": doc.fiscal_currency,
                         "rate": doc.exchange_rate_snapshot, "total": amount,
                         "bolivares": round(amount * float(doc.exchange_rate_snapshot or 1.0), 6),
                         "emitted_at": doc.emitted_at.isoformat() if doc.emitted_at else None})
    elif tax_type == "COMPRAS":
        invoices = db.execute(select(SupplierInvoice).where(SupplierInvoice.company_id == company_id)).scalars().all()
        for inv in invoices:
            total_amount += float(inv.total or 0.0)
            rows.append({"document": inv.invoice_number, "supplier_id": inv.supplier_id,
                         "control": inv.control_number, "total": inv.total, "status": inv.status})
    elif tax_type == "RETENCIONES":
        withholdings = db.execute(select(ApWithholding).where(ApWithholding.company_id == company_id)).scalars().all()
        for w in withholdings:
            total_amount += float(w.amount or 0)
            rows.append({"id": str(w.id), "tax_type": w.tax_type, "base": w.base, "rate_ref": w.rate_ref,
                         "amount": w.amount, "period": w.period, "status": w.status})
    elif tax_type == "IGTF":
        events = db.execute(select(IgftEvent).where(IgftEvent.company_id == company_id)).scalars().all()
        for e in events:
            total_amount += float(e.igft_amount or 0.0)
            rows.append({"event_type": e.event_type, "source": e.source_document, "amount": e.amount,
                         "igft_amount": e.igft_amount, "currency": e.currency,
                         "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None})
    else:
        raise NotFoundError(code="UNKNOWN_BOOK", message="Tipo de libro fiscal no soportado")
    return {"tax_type": tax_type, "period": period, "count": len(rows), "total": round(total_amount, 6), "rows": rows}
