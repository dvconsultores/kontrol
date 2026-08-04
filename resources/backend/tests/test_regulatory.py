"""Pruebas de regulación y traslados (008).

Cubre: maestros regulatorios (autoridades, tipos, registros, perfiles,
vehículos, conductores), permisos con ciclo de vida, guías SICA/SIGESAI/SACS
(registro y validación), evaluación por línea de despacho con bloqueo,
contingencias con regla oficial y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Warehouse
from app.modules.regulatory import service as regulatory_service
from app.modules.regulatory.models import PermitInstance, RegulatoryAuthority, RegulatoryEvaluation
from app.modules.sales.models import SalesOrder, Shipment, ShipmentLine


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    init_models()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


COMPANY = "tenant-1"
OTHER = "tenant-2"


def _make_party(db: Session, company: str = COMPANY, code: str = "CLI-1") -> Party:
    party = Party(company_id=company, code=code, name="Cliente SA", person_type="JURIDICA",
                  tax_id=f"J-{abs(hash(code)) % 100000000}-1", roles=["CLIENTE"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_product(db: Session, company: str = COMPANY) -> CatalogItem:
    item = CatalogItem(company_id=company, code="P-001", name="Producto", item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return item


def _make_warehouse(db: Session, company: str = COMPANY) -> Warehouse:
    wh = Warehouse(company_id=company, code="W-1", name="Principal", status="ACTIVE")
    db.add(wh)
    db.flush()
    return wh


def _make_authority(db: Session, company: str = COMPANY) -> None:
    regulatory_service.create_authority(db, company_id=company, code="SICA", name="SICA", validation_method="GUIA")


def _make_shipment(db: Session, company: str = COMPANY) -> Shipment:
    customer = _make_party(db, company)
    product = _make_product(db, company)
    wh = _make_warehouse(db, company)
    order = SalesOrder(company_id=company, customer_id=str(customer.id), code="OV-1", status="APPROVED")
    db.add(order)
    db.flush()
    shipment = Shipment(company_id=company, order_id=str(order.id), origin_warehouse_id=str(wh.id),
                        code=f"SH-{abs(hash(company)) % 1000}", status="DRAFT", validation_status="PENDING")
    db.add(shipment)
    db.flush()
    db.add(ShipmentLine(shipment_id=str(shipment.id), product_id=str(product.id), quantity=10.0))
    db.flush()
    return shipment


class TestMaestros:
    def test_authority_and_permit_type(self, db_session) -> None:
        _make_authority(db_session)
        authority = db_session.execute(select(RegulatoryAuthority)).scalars().first()
        pt = regulatory_service.create_permit_type(db_session, company_id=COMPANY, authority_id=str(authority.id),
                                                   code="SICA-GUIA", name="Guía SICA")
        assert pt.status == "ACTIVE" and pt.authority_id == str(authority.id)

    def test_official_registration(self, db_session) -> None:
        _make_authority(db_session)
        authority = db_session.execute(select(RegulatoryAuthority)).scalars().first()
        r = regulatory_service.create_official_registration(db_session, company_id=COMPANY, authority_id=str(authority.id),
                                                            scope="COMPANY", ref_number="REG-1")
        assert r.ref_number == "REG-1" and r.status == "ACTIVE"

    def test_vehicle_and_driver(self, db_session) -> None:
        party = _make_party(db_session)
        v = regulatory_service.create_vehicle(db_session, company_id=COMPANY, plate="ABC123", vehicle_type="CAMION", capacity=5000.0)
        d = regulatory_service.create_driver(db_session, company_id=COMPANY, party_id=str(party.id), license="L-1")
        assert v.plate == "ABC123" and d.license == "L-1"

    def test_profile_requires_documents(self, db_session) -> None:
        p = regulatory_service.create_profile(db_session, company_id=COMPANY, operation="DESPACHO",
                                              required_documents=["SICA", "SIGESAI"])
        assert "SICA" in (p.required_documents or "") and p.version == "1.0"


class TestPermisosYGuias:
    def _make_permit(self, db_session) -> PermitInstance:
        _make_authority(db_session)
        authority = db_session.execute(select(RegulatoryAuthority)).scalars().first()
        pt = regulatory_service.create_permit_type(db_session, company_id=COMPANY, authority_id=str(authority.id), code="P1", name="Permiso")
        return regulatory_service.create_permit(db_session, company_id=COMPANY, permit_type_id=str(pt.id), number="PER-001")

    def test_permit_cycle(self, db_session) -> None:
        permit = self._make_permit(db_session)
        assert permit.status == "DRAFT" and permit.hash
        for target in ("REGISTERED", "VERIFIED", "APPROVED_FOR_USE", "USED"):
            regulatory_service.transition_permit(db_session, company_id=COMPANY, permit_id=str(permit.id), target=target)
        assert permit.status == "USED"
        with pytest.raises(ConflictError):
            regulatory_service.transition_permit(db_session, company_id=COMPANY, permit_id=str(permit.id), target="USED")

    def test_guia_registered_and_traceable(self, db_session) -> None:
        _make_authority(db_session)
        doc = regulatory_service.register_official_document(db_session, company_id=COMPANY, kind="SICA",
                                                            number="G-2026-001", organism="SICA", verification="OK")
        assert doc.status == "VALID" and doc.hash and doc.verification == "OK"

    def test_invalid_guia_kind(self, db_session) -> None:
        with pytest.raises(KontrolError):
            regulatory_service.register_official_document(db_session, company_id=COMPANY, kind="DESCONOCIDO", number="X")


class TestEvaluacionYBloqueo:
    def test_shipment_blocked_without_guia(self, db_session) -> None:
        shipment = _make_shipment(db_session)
        regulatory_service.create_profile(db_session, company_id=COMPANY, operation="DESPACHO",
                                          required_documents=["SICA"])
        result = regulatory_service.evaluate_shipment(db_session, company_id=COMPANY, shipment_id=str(shipment.id))
        assert result["blocked"] == 1 and result["status"] == "BLOCKED"
        evaluation = db_session.execute(select(RegulatoryEvaluation).where(
            RegulatoryEvaluation.shipment_id == str(shipment.id))).scalars().first()
        assert evaluation.status == "BLOCKED" and "SICA" in (evaluation.blockers or "")

    def test_shipment_cleared_with_guia(self, db_session) -> None:
        shipment = _make_shipment(db_session)
        regulatory_service.create_profile(db_session, company_id=COMPANY, operation="DESPACHO", required_documents=["SICA"])
        _make_authority(db_session)
        regulatory_service.register_official_document(db_session, company_id=COMPANY, kind="SICA", number="G-1",
                                                      expires_at=date.today() + timedelta(days=30))
        result = regulatory_service.evaluate_shipment(db_session, company_id=COMPANY, shipment_id=str(shipment.id))
        assert result["status"] == "CLEARED"

    def test_expired_guia_blocks(self, db_session) -> None:
        shipment = _make_shipment(db_session)
        regulatory_service.create_profile(db_session, company_id=COMPANY, operation="DESPACHO", required_documents=["SICA"])
        _make_authority(db_session)
        regulatory_service.register_official_document(db_session, company_id=COMPANY, kind="SICA", number="G-2",
                                                      expires_at=date.today() - timedelta(days=1))
        result = regulatory_service.evaluate_shipment(db_session, company_id=COMPANY, shipment_id=str(shipment.id))
        assert result["status"] == "BLOCKED"

    def test_override_block(self, db_session) -> None:
        shipment = _make_shipment(db_session)
        regulatory_service.create_profile(db_session, company_id=COMPANY, operation="DESPACHO", required_documents=["SICA"])
        regulatory_service.evaluate_shipment(db_session, company_id=COMPANY, shipment_id=str(shipment.id))
        evaluation = db_session.execute(select(RegulatoryEvaluation).where(
            RegulatoryEvaluation.shipment_id == str(shipment.id))).scalars().first()
        regulatory_service.override_evaluation(db_session, company_id=COMPANY, evaluation_id=str(evaluation.id),
                                               reason="Autorización de gerencia", actor="user-1")
        assert evaluation.status == "OVERRIDDEN" and "user-1" in (evaluation.override or "")


class TestContingenciasYMultiempresa:
    def test_contingency_requires_rule(self, db_session) -> None:
        with pytest.raises(KontrolError):
            regulatory_service.create_contingency(db_session, company_id=COMPANY, rule_ref="", reason="Sin regla")

    def test_contingency_with_rule(self, db_session) -> None:
        c = regulatory_service.create_contingency(db_session, company_id=COMPANY, rule_ref="OFICIAL-2026-01",
                                                  reason="Corte de suministro", actor="user-1")
        assert c.status == "ACTIVE" and c.rule_ref == "OFICIAL-2026-01"
        regulatory_service.end_contingency(db_session, company_id=COMPANY, contingency_id=str(c.id))
        assert c.status == "ENDED"

    def test_approval_request_flow(self, db_session) -> None:
        req = regulatory_service.create_approval_request(db_session, company_id=COMPANY, object_ref="SHIPMENT:1",
                                                         rule_ref="R1", risk="ALTO", amount=1000.0)
        assert req.status == "PENDING"
        regulatory_service.transition_approval_request(db_session, company_id=COMPANY, request_id=str(req.id), target="APPROVED")
        assert req.status == "APPROVED" and req.decision == "APPROVED"

    def test_tenant_isolation(self, db_session) -> None:
        shipment = _make_shipment(db_session, company=COMPANY)
        with pytest.raises(NotFoundError):
            regulatory_service.evaluate_shipment(db_session, company_id=OTHER, shipment_id=str(shipment.id))
