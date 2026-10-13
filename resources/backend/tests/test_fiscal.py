"""Pruebas del núcleo fiscal (007).

Cubre: reglas fiscales versionadas (fuente legal, vigencia sin solape),
numeración/correlativos y números de control con asignación atómica, emisión
fiscal con hash e idempotencia, impresión auditada, notas con límites al saldo
ajustable, retenciones (reglas + ciclo vía 004), períodos/declaraciones, libros
reconstruibles y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.fiscal import service as fiscal_service
from app.modules.fiscal.models import ControlNumber, FiscalDocument, TaxRuleVersion
from app.modules.master_data.models import Party
from app.modules.sales.models import SalesInvoice
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


def _make_party(db: Session, company: str = COMPANY, code: str = "CLI-1") -> Party:
    party = Party(company_id=company, code=code, name="Cliente SA", person_type="JURIDICA",
                  tax_id=f"J-{abs(hash(code)) % 100000000}-1", roles=["CLIENTE"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_invoice(db: Session, company: str = COMPANY, total: float = 1000.0) -> SalesInvoice:
    party = _make_party(db, company)
    inv = SalesInvoice(company_id=company, customer_id=str(party.id), base_fiscal_currency="VED",
                       base_fiscal=total, tax_total=0.0, total=total, status="EMITTED")
    db.add(inv)
    db.flush()
    return inv


def _make_iva_rule(db: Session, tax_code: str = "IVA_GENERAL", rate_pct: float = 16.0):
    fiscal_service.create_legal_source(db, authority="SENIAT", source_type="GACETA",
                                       number="42.000", gazette="42.000", effective_from=date(2026, 1, 1))
    rule = fiscal_service.create_tax_rule(db, tax_code=tax_code, effective_from=date(2026, 1, 1),
                                          rate={"percent": rate_pct})
    fiscal_service.approve_tax_rule(db, rule_id=str(rule.id), approver="user-1")
    return rule


def _make_series_and_batch(db: Session, company: str = COMPANY):
    series = fiscal_service.create_number_series(db, company_id=company, document_type="INVOICE", prefix="FV")
    batch = fiscal_service.create_control_batch(db, company_id=company, range_from="1001", range_to="1005",
                                                printer="IMP-1")
    return series, batch


class TestReglasFiscales:
    def test_legal_source_and_tax_rule_approval(self, db_session) -> None:
        _make_iva_rule(db_session)
        rules = db_session.execute(select(TaxRuleVersion)).scalars().all()
        assert len(rules) == 1 and rules[0].status == "ACTIVE"

    def test_tax_rule_overlap_rejected(self, db_session) -> None:
        _make_iva_rule(db_session)
        with pytest.raises(ConflictError):
            fiscal_service.create_tax_rule(db_session, tax_code="IVA_GENERAL", effective_from=date(2026, 6, 1),
                                           rate={"percent": 16.0})

    def test_tax_profile_by_party(self, db_session) -> None:
        party = _make_party(db_session)
        profile = fiscal_service.create_tax_profile(db_session, company_id=COMPANY, scope="PARTY",
                                                    party_id=str(party.id), classifications={"iva": "GRAVADO"})
        assert profile.scope == "PARTY" and profile.status == "ACTIVE"

    def test_calculate_tax_snapshot(self, db_session) -> None:
        _make_iva_rule(db_session)
        calc = fiscal_service.calculate_tax(db_session, company_id=COMPANY, tax_code="IVA_GENERAL",
                                            base=100.0, document_ref="INVOICE:x")
        assert calc.amount == 16.0 and calc.base == 100.0 and calc.rate == 16.0
        assert (calc.snapshot or {}).get("tax_code") == "IVA_GENERAL"


class TestNumeracionYControl:
    def test_reserve_number_sequential(self, db_session) -> None:
        series, _ = _make_series_and_batch(db_session)
        first = fiscal_service.reserve_number(db_session, company_id=COMPANY, series_id=str(series.id))
        second = fiscal_service.reserve_number(db_session, company_id=COMPANY, series_id=str(series.id))
        assert first == "FV0000001" and second == "FV0000002"
        assert series.next_number == 3 and series.lock_version == 2

    def test_control_batch_and_assignment(self, db_session) -> None:
        _, batch = _make_series_and_batch(db_session)
        control = fiscal_service.assign_control(db_session, company_id=COMPANY, batch_id=str(batch.id))
        assert control.state == "RESERVED" and control.value == "1001"
        # el siguiente asignado es distinto (no se comparte)
        next_control = fiscal_service.assign_control(db_session, company_id=COMPANY, batch_id=str(batch.id))
        assert next_control.value != control.value

    def test_control_batch_exhausted(self, db_session) -> None:
        _, batch = _make_series_and_batch(db_session)
        for _ in range(5):
            fiscal_service.assign_control(db_session, company_id=COMPANY, batch_id=str(batch.id))
        with pytest.raises(ConflictError):
            fiscal_service.assign_control(db_session, company_id=COMPANY, batch_id=str(batch.id))

    def test_use_control_requires_reserved(self, db_session) -> None:
        _, batch = _make_series_and_batch(db_session)
        control = fiscal_service.assign_control(db_session, company_id=COMPANY, batch_id=str(batch.id))
        fiscal_service.use_control(db_session, control_id=str(control.id), document_ref="INVOICE:1")
        assert control.state == "USED"
        with pytest.raises(ConflictError):
            fiscal_service.use_control(db_session, control_id=str(control.id), document_ref="INVOICE:2")


class TestEmisionEImpresion:
    def test_emit_atomic_and_idempotent(self, db_session) -> None:
        invoice = _make_invoice(db_session)
        series, batch = _make_series_and_batch(db_session)
        result = fiscal_service.emit_document(db_session, company_id=COMPANY,
                                              business_document=f"INVOICE:{invoice.id}",
                                              series_id=str(series.id), batch_id=str(batch.id), actor="user-1")
        assert result["idempotent"] is False and result["invoice_number"] == "FV0000001"
        assert result["control_number"] == "1001" and result["hash"]
        # Reintento: idempotente, no consume otro correlativo ni control
        retry = fiscal_service.emit_document(db_session, company_id=COMPANY,
                                             business_document=f"INVOICE:{invoice.id}",
                                             series_id=str(series.id), batch_id=str(batch.id))
        assert retry["idempotent"] is True and retry["invoice_number"] == "FV0000001"
        docs = db_session.execute(select(FiscalDocument)).scalars().all()
        assert len(docs) == 1

    def test_emit_consumes_control(self, db_session) -> None:
        invoice = _make_invoice(db_session)
        series, batch = _make_series_and_batch(db_session)
        fiscal_service.emit_document(db_session, company_id=COMPANY, business_document=f"INVOICE:{invoice.id}",
                                     series_id=str(series.id), batch_id=str(batch.id))
        controls = db_session.execute(select(ControlNumber)).scalars().all()
        assert [c.state for c in controls].count("USED") == 1

    def test_print_event_audited(self, db_session) -> None:
        invoice = _make_invoice(db_session)
        series, batch = _make_series_and_batch(db_session)
        emitted = fiscal_service.emit_document(db_session, company_id=COMPANY,
                                               business_document=f"INVOICE:{invoice.id}",
                                               series_id=str(series.id), batch_id=str(batch.id))
        event = fiscal_service.register_print(db_session, company_id=COMPANY,
                                              fiscal_document_id=emitted["id"],
                                              copy_type="COPY", reason="Copia para archivo", actor="user-2")
        assert event.reason == "Copia para archivo" and event.user_id == "user-2" and event.hash


class TestNotasFiscales:
    def test_credit_note_within_adjustable(self, db_session) -> None:
        invoice = _make_invoice(db_session, total=1000.0)
        note = fiscal_service.create_credit_debit_note(db_session, company_id=COMPANY,
                                                       original_document=f"INVOICE:{invoice.id}",
                                                       note_type="CREDIT", cause="Devolución", amount=300.0)
        assert note.amount == 300.0 and (note.limits or {}).get("original_total") == 1000.0

    def test_credit_note_exceeds_adjustable(self, db_session) -> None:
        invoice = _make_invoice(db_session, total=1000.0)
        fiscal_service.create_credit_debit_note(db_session, company_id=COMPANY,
                                                original_document=f"INVOICE:{invoice.id}",
                                                note_type="CREDIT", cause="Primera", amount=700.0)
        with pytest.raises(ConflictError):
            fiscal_service.create_credit_debit_note(db_session, company_id=COMPANY,
                                                    original_document=f"INVOICE:{invoice.id}",
                                                    note_type="CREDIT", cause="Segunda", amount=400.0)

    def test_note_requires_invoice_reference(self, db_session) -> None:
        with pytest.raises(KontrolError):
            fiscal_service.create_credit_debit_note(db_session, company_id=COMPANY,
                                                    original_document="FACTURA-1", note_type="CREDIT",
                                                    cause="Sin referencia", amount=10.0)


class TestRetenciones:
    def _make_rule(self, db_session, rate: float = 3.0) -> None:
        fiscal_service.create_withholding_rule(db_session, company_id=COMPANY, tax_type="IVA", code="RT-IVA",
                                               rate=rate, concept="Retención IVA 3%")

    def test_calculate_withholding_creates_004(self, db_session) -> None:
        party = _make_party(db_session)
        self._make_rule(db_session)
        w = fiscal_service.calculate_withholding(db_session, company_id=COMPANY, party_id=str(party.id),
                                                 tax_type="IVA", code="RT-IVA", base=1000.0, period="2026-01")
        assert w.status == "CALCULADA" and w.amount == 30.0 and w.rule_ref == "RT-IVA"

    def test_withholding_cycle_and_certificate(self, db_session) -> None:
        party = _make_party(db_session)
        self._make_rule(db_session)
        w = fiscal_service.calculate_withholding(db_session, company_id=COMPANY, party_id=str(party.id),
                                                 tax_type="IVA", code="RT-IVA", base=1000.0)
        fiscal_service.transition_withholding(db_session, company_id=COMPANY, withholding_id=str(w.id), target="PRACTICADA")
        fiscal_service.issue_withholding_certificate(db_session, company_id=COMPANY, withholding_id=str(w.id),
                                                     certificate_ref="COMP-2026-0001")
        assert w.status == "EMITIDA" and w.certificate == "COMP-2026-0001"

    def test_withholding_rule_not_found(self, db_session) -> None:
        party = _make_party(db_session)
        with pytest.raises(NotFoundError):
            fiscal_service.calculate_withholding(db_session, company_id=COMPANY, party_id=str(party.id),
                                                 tax_type="ISLR", code="NO-EXISTE", base=1000.0)


class TestPeriodosLibrosYMultiempresa:
    def test_fiscal_period_flow(self, db_session) -> None:
        period = fiscal_service.create_fiscal_period(db_session, company_id=COMPANY, tax_type="IVA",
                                                     period_key="2026-01", start=date(2026, 1, 1), end=date(2026, 1, 31))
        assert period.status == "OPEN"
        fiscal_service.transition_period(db_session, company_id=COMPANY, period_id=str(period.id), target="CLOSED", actor="aud-1")
        assert period.status == "CLOSED"
        fiscal_service.transition_period(db_session, company_id=COMPANY, period_id=str(period.id), target="REOPENED", actor="aud-1")
        assert period.status == "REOPENED" and "REOPENED" in (period.approvals or {})

    def test_tax_return_batch(self, db_session) -> None:
        batch = fiscal_service.create_tax_return_batch(db_session, company_id=COMPANY, tax_type="IVA",
                                                       period="2026-01", totals={"base": 1000.0, "tax": 160.0})
        assert batch.status == "DRAFT" and (batch.totals or {}).get("tax") == 160.0

    def test_books_ventas_reconstructed(self, db_session) -> None:
        invoice = _make_invoice(db_session, total=500.0)
        series, batch = _make_series_and_batch(db_session)
        fiscal_service.emit_document(db_session, company_id=COMPANY, business_document=f"INVOICE:{invoice.id}",
                                     series_id=str(series.id), batch_id=str(batch.id))
        book = fiscal_service.books(db_session, company_id=COMPANY, tax_type="VENTAS", period="2026-01")
        assert book["count"] == 1 and book["total"] == 500.0

    def test_tenant_isolation_for_emission(self, db_session) -> None:
        invoice = _make_invoice(db_session, company=COMPANY)
        series, batch = _make_series_and_batch(db_session, company=COMPANY)
        with pytest.raises(NotFoundError):
            fiscal_service.emit_document(db_session, company_id=OTHER, business_document=f"INVOICE:{invoice.id}",
                                         series_id=str(series.id), batch_id=str(batch.id))
