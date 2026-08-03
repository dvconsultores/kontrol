"""Pruebas de los servicios fundacionales sobre SQLite en memoria.

Valida modelos, máquina de estados y el asistente de inicialización sin
requerir una base de datos externa.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize, setup_status


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


class TestSetupInitialization:
    def test_initialize_creates_installation_tenant_company_admin(self, db_session) -> None:
        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        result = initialize(db_session, body)

        assert result["ok"] is True
        assert result["installation_id"]
        assert result["tenant_id"]
        assert result["company_id"]
        assert result["admin_user_id"] is not None
        assert result["must_change_password"] is True

        installation = db_session.query(Installation).first()
        # Máquina de estados (DOC-07): PENDING hasta importar licencia válida.
        assert installation.state == "PENDING"
        assert installation.installation_uuid == result["installation_id"]

        tenant = db_session.query(Tenant).first()
        assert tenant.code == "DEMO"

        company = db_session.query(Company).first()
        assert company.rif == "J-12345678-9"

        status = setup_status(db_session)
        assert status.initialized is True

    def test_initialize_is_idempotent(self, db_session) -> None:
        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        initialize(db_session, body)
        from app.core.errors import ConflictError

        with pytest.raises(ConflictError):
            initialize(db_session, body)

    def test_admin_must_change_password_and_audit_exists(self, db_session) -> None:
        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        result = initialize(db_session, body)
        admin = identity_service.get_user(db_session, result["admin_user_id"])
        assert admin.must_change_password is True
        # Auditoría registrada (USER_CREATED)
        events = db_session.query(AuditEvent).filter(AuditEvent.action == "USER_CREATED").all()
        assert len(events) >= 1


class TestLicenseActivation:
    """Transición PENDING → ACTIVE al importar una licencia firmada (FR-001-050)."""

    def test_import_license_activates_installation(self, db_session) -> None:
        import json
        import os

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from app.core.config import get_settings
        from app.modules.setup.api import SetupRequest, initialize

        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        result = initialize(db_session, body)
        assert result["installation_id"]

        # Clave de la autoridad central (el propietario de KONTROL)
        authority_key = Ed25519PrivateKey.generate()
        authority_pub = (
            authority_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        payload = {
            "issuer": "KONTROL Licensing Authority",
            "license_id": "LIC-000999",
            "installation_id": result["installation_id"],
            "customer_id": "CUS-000087",
            "contract_id": "CON-000087",
            "company_tax_id": "J-12345678-9",
            "period_start": "2026-04-01T00:00:00-04:00",
            "period_end": "2027-03-31T23:59:59-04:00",
            "critical_warning_start": "2027-04-21T00:00:00-04:00",
            "read_only_start": "2027-05-01T00:00:00-04:00",
            "entitlements": {"companies": 1, "users": 25, "modules": ["masters"]},
            "minimum_version": "1.0.0",
            "kid": "kontrol-lic-2026-01",
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        signature_hex = authority_key.sign(canonical).hex()

        # Inyectar la clave pública de la autoridad y recalcular settings
        os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = authority_pub
        get_settings.cache_clear()
        try:
            state = licensing_service.import_license(db_session, payload=payload, signature_hex=signature_hex, source="MANUAL")
        finally:
            os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
            get_settings.cache_clear()

        installation = db_session.query(Installation).first()
        assert installation.state == "ACTIVE"
        assert state.mode == "FULL_ACCESS"
        assert state.license_id == "LIC-000999"


class TestAuthFlow:
    def test_login_and_change_password(self, db_session) -> None:
        from app.modules.setup.api import SetupRequest, initialize

        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        initialize(db_session, body)
        tenant = db_session.query(Tenant).first()
        user = identity_service.authenticate(db_session, tenant_id=str(tenant.id), username="admin", password="Kontrol2026Segura!")
        assert user.id is not None
        # Cambio de contraseña obligatorio
        identity_service.change_password(
            db_session,
            user=user,
            current_password="Kontrol2026Segura!",
            new_password="NuevaClave2026!",
        )
        db_session.refresh(user)
        assert user.must_change_password is False

    def test_login_with_wrong_password_locks(self, db_session) -> None:
        from app.modules.setup.api import SetupRequest, initialize

        body = SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="DEMO01",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        )
        initialize(db_session, body)
        tenant = db_session.query(Tenant).first()
        from app.core.errors import KontrolError

        for _ in range(3):
            with pytest.raises(KontrolError):
                identity_service.authenticate(db_session, tenant_id=str(tenant.id), username="admin", password="incorrecta")
