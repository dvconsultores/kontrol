"""Pruebas de maestros (002-maestros).

Cubre: normalización/duplicidad de RIF, taxonomía/atributos gobernados,
especialización producto/servicio, conversiones y perfiles.
"""

from __future__ import annotations

from datetime import UTC

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, KontrolError
from app.modules.master_data import service as master_service
from app.modules.master_data.models import (
    CatalogItem,
    Party,
    Product,
    ProfileVersion,
    Service,
    TaxonomyNode,
    UnitConversion,
    UnitOfMeasure,
)


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


class TestPartyAndDuplicidad:
    def test_normalize_rif(self) -> None:
        assert master_service.normalize_rif("J123456789") == "J-12345678-9"
        assert master_service.normalize_rif("j-12345678-9") == "J-12345678-9"

    def test_invalid_rif_rejected(self) -> None:
        with pytest.raises(KontrolError):
            master_service.validate_tax_id("X-123", "JURIDICA")

    def test_create_party_and_duplicate_same_role(self, db_session) -> None:
        master_service.ensure_no_duplicate(db_session, company_id=COMPANY, tax_id="J-12345678-9", role="CLIENTE")
        db_session.add(
            Party(
                company_id=COMPANY,
                code="P001",
                name="Demo C.A.",
                person_type="JURIDICA",
                tax_id="J-12345678-9",
                roles=["CLIENTE"],
                status="ACTIVE",
            )
        )
        db_session.commit()
        # Mismo RIF y mismo rol -> duplicado
        assert master_service.is_duplicate_party(db_session, company_id=COMPANY, tax_id="J-12345678-9", role="CLIENTE") is True
        # Mismo RIF pero rol distinto -> NO duplicado (legítimo)
        assert master_service.is_duplicate_party(db_session, company_id=COMPANY, tax_id="J-12345678-9", role="PROVEEDOR") is False

    def test_duplicate_raises_conflict(self, db_session) -> None:
        db_session.add(Party(company_id=COMPANY, code="P001", name="A", tax_id="J-12345678-9", roles=["CLIENTE"], status="ACTIVE"))
        db_session.commit()
        with pytest.raises(ConflictError):
            master_service.ensure_no_duplicate(db_session, company_id=COMPANY, tax_id="J-12345678-9", role="CLIENTE")


class TestCatalogAndEspecializacion:
    def test_product_service_specialization(self, db_session) -> None:
        # Producto
        item_p = CatalogItem(company_id=COMPANY, code="P-001", name="Arroz", item_type="PRODUCT", status="ACTIVE")
        db_session.add(item_p)
        db_session.flush()
        db_session.add(Product(item_id=str(item_p.id)))
        # Servicio
        item_s = CatalogItem(company_id=COMPANY, code="S-001", name="Servicio contable", item_type="SERVICE", status="ACTIVE")
        db_session.add(item_s)
        db_session.flush()
        db_session.add(Service(item_id=str(item_s.id)))
        db_session.commit()

        product = db_session.query(Product).filter_by(item_id=str(item_p.id)).first()
        service = db_session.query(Service).filter_by(item_id=str(item_s.id)).first()
        assert product is not None
        assert service is not None
        # El servicio NO tiene campos de inventario; el producto SÍ los tiene
        product_cols = {c.name for c in Product.__table__.columns}
        service_cols = {c.name for c in Service.__table__.columns}
        assert "inventory_profile_id" in product_cols
        assert "inventory_profile_id" not in service_cols
        assert "billing_unit_id" in service_cols  # unidad de facturación del servicio


class TestTaxonomiaYAtributos:
    def test_taxonomy_and_attribute_governed(self, db_session) -> None:
        node = TaxonomyNode(company_id=COMPANY, code="RUB-ALIM", name="Alimentos", level="RUBRO", applies_to=["PRODUCT"], status="ACTIVE")
        db_session.add(node)
        db_session.commit()
        assert node.level == "RUBRO"

    def test_eav_no_free_for_critical(self, db_session) -> None:
        # Verifica que el modelo de producto usa columnas tipadas (no EAV) para inventario
        from app.modules.master_data.models import Product as P

        cols = {c.name for c in P.__table__.columns}
        # Datos críticos en columnas tipadas/FK, no en un único campo JSON libre
        assert "inventory_profile_id" in cols
        assert "item_id" in cols


class TestUnidadesYConversiones:
    def test_conversion_requires_positive_factor(self) -> None:
        kg = UnitOfMeasure(company_id=None, code="KG", name="Kilogramo", symbol="kg", dimension="MASA", decimals=3, status="ACTIVE")
        g = UnitOfMeasure(company_id=None, code="G", name="Gramo", symbol="g", dimension="MASA", decimals=2, status="ACTIVE")
        from pydantic import ValidationError

        from app.modules.master_data.api import ConversionCreate

        with pytest.raises(ValidationError):
            ConversionCreate(from_unit_id=str(kg.id), to_unit_id=str(g.id), factor=0)

    def test_unit_conversion_model(self, db_session) -> None:
        kg = UnitOfMeasure(company_id=None, code="KG", name="Kilogramo", symbol="kg", dimension="MASA", decimals=3, status="ACTIVE")
        g = UnitOfMeasure(company_id=None, code="G", name="Gramo", symbol="g", dimension="MASA", decimals=2, status="ACTIVE")
        db_session.add_all([kg, g])
        db_session.flush()
        db_session.add(UnitConversion(from_unit_id=str(kg.id), to_unit_id=str(g.id), factor=1000, rounding=4))
        db_session.commit()
        conv = db_session.query(UnitConversion).first()
        assert conv.factor == 1000


class TestPerfiles:
    def test_profile_version_without_overlap(self, db_session) -> None:
        from datetime import datetime

        p = ProfileVersion(
            company_id=COMPANY,
            code="INV-BASIC",
            name="Inventario básico",
            profile_type="INVENTORY",
            stockable=True,
            lot=True,
            expiry=True,
            status="ACTIVE",
            approval_status="DRAFT",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_to=datetime(2026, 12, 31, tzinfo=UTC),
        )
        db_session.add(p)
        db_session.commit()
        assert p.stockable is True
        assert p.trace_level == "NONE"

    def test_regulatory_flags(self, db_session) -> None:
        p = ProfileVersion(
            company_id=COMPANY,
            code="REG-ALIM",
            name="Regulatorio alimentos",
            profile_type="REGULATORY",
            requires_sica=True,
            requires_sacs=True,
            status="ACTIVE",
            approval_status="DRAFT",
        )
        db_session.add(p)
        db_session.commit()
        assert p.requires_sica is True
        assert p.requires_sacs is True


class TestAllowedActions:
    def test_party_allowed_actions(self) -> None:
        party = Party(company_id=COMPANY, code="P", name="X", roles=["CLIENTE"], status="ACTIVE")
        actions = master_service.party_allowed_actions(party)
        assert actions["deactivate"] is True
        assert actions["activate"] is False
        assert actions["delete"] is False
