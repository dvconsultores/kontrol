"""Pruebas de licenciamiento central (010).

Cubren: configuración del servidor central, sincronización (contrato v1)
con idempotencia y tolerancia a fallo, entitlements por módulo, tolerancia
offline (reloj confiable), renovación con comprobante y transiciones de modo.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_engine
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEvent, LicenseState
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize


@pytest.fixture()
def db_session():
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _setup(db: Session) -> str:
    body = SetupRequest(
        tenant_code="DEMO",
        tenant_name="Empresa Demo",
        company_code="DEMO01",
        company_legal_name="Demo C.A.",
        company_rif="J-12345678-9",
        admin_username="admin",
        admin_password="Kontrol2026Segura!",
    )
    return initialize(db, body)["installation_id"]


def _activate_license(db: Session) -> None:
    """Activa una licencia firmada (FR-001-050) para tener un LicenseState."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from app.core.config import get_settings

    authority_key = Ed25519PrivateKey.generate()
    authority_pub = (
        authority_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    installation = db.execute(select_installation()).scalars().first()
    assert installation is not None
    payload = {
        "issuer": "KONTROL Licensing Authority",
        "license_id": "LIC-010000",
        "installation_id": installation.installation_uuid,
        "customer_id": "CUS-000087",
        "contract_id": "CON-000087",
        "company_tax_id": "J-12345678-9",
        "period_start": "2026-04-01T00:00:00-04:00",
        "period_end": "2027-03-31T23:59:59-04:00",
        "critical_warning_start": "2027-04-21T00:00:00-04:00",
        "read_only_start": "2027-05-01T00:00:00-04:00",
        "entitlements": {"companies": 1, "users": 25, "modules": ["ventas", "compras"]},
        "minimum_version": "1.0.0",
        "kid": "kontrol-lic-2026-01",
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    signature_hex = authority_key.sign(canonical).hex()

    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = authority_pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=signature_hex, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()


def select_installation():
    from sqlalchemy import select

    return select(Installation).limit(1)


def _configure_central(db: Session) -> dict:
    return licensing_service.upsert_central_config(
        db,
        server_url="https://central.kontrol.example",
        public_key=None,
        sync_policy={"mode": "MANUAL"},
        grace_days=7,
        enabled=True,
        actor="admin",
    )


def _fake_sync_client(response: dict | None = None, error: Exception | None = None):
    default = {
        "version": "1.0",
        "status": "FULL_ACCESS",
        "server_time": "2026-08-04T12:00:00+00:00",
        "expires_at": "2026-12-31T23:59:59+00:00",
        "entitlements": {
            "ventas": True,
            "compras": True,
            "inventario": True,
            "tesoreria": True,
            "fiscal": True,
            "regulatorio": True,
            "reportes": True,
        },
    }

    def client(payload: dict, server_url: str) -> dict:
        if error is not None:
            raise error
        return response if response is not None else default

    return client


class TestConfiguracionCentral:
    def test_upsert_and_get_config(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        config = _configure_central(db_session)
        assert config["server_url"] == "https://central.kontrol.example"
        assert config["grace_days"] == 7
        assert config["enabled"] is True

        fetched = licensing_service.get_central_config(db_session)
        assert fetched is not None
        assert fetched["server_url"] == config["server_url"]

    def test_sync_without_config_raises(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        with pytest.raises(KontrolError) as exc:
            licensing_service.sync_license(db_session, sync_client=_fake_sync_client())
        assert exc.value.code == "CENTRAL_NOT_CONFIGURED"


class TestSincronizacion:
    def test_sync_success_records_run_snapshot_and_event(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)

        result = licensing_service.sync_license(db_session, sync_client=_fake_sync_client(), actor="admin")

        assert result["status"] == "SUCCESS"
        assert result["idempotent"] is False

        runs = licensing_service.list_sync_runs(db_session)
        assert len(runs) == 1
        assert runs[0]["status"] == "SUCCESS"

        installation = db_session.execute(select_installation()).scalars().first()
        assert installation is not None
        state = db_session.execute(
            select_state(installation.installation_uuid)
        ).scalars().first()
        assert state is not None
        assert state.last_reliable_date.replace(tzinfo=UTC) == datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
        assert state.mode == "FULL_ACCESS"
        assert "ventas" in (state.entitlements or {}).get("modules", [])

        snapshots = licensing_service.list_entitlement_snapshots(db_session)
        assert len(snapshots) == 1
        assert snapshots[0]["modules"]["ventas"] is True

        events = db_session.execute(select(LicenseEvent)).scalars().all()
        assert any(e.event_type == "LICENSE_SYNCED" for e in events)

    def test_sync_is_idempotent_same_day(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)

        first = licensing_service.sync_license(db_session, sync_client=_fake_sync_client())
        second = licensing_service.sync_license(db_session, sync_client=_fake_sync_client())

        assert first["idempotent"] is False
        assert second["idempotent"] is True
        assert len(licensing_service.list_sync_runs(db_session)) == 1

    def test_sync_failure_records_failed_run(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)

        with pytest.raises(KontrolError) as exc:
            licensing_service.sync_license(
                db_session,
                sync_client=_fake_sync_client(error=ConnectionError("servidor caído")),
                actor="admin",
            )
        assert exc.value.code == "CENTRAL_UNREACHABLE"
        assert exc.value.status_code == 503

        runs = licensing_service.list_sync_runs(db_session)
        assert len(runs) == 1
        assert runs[0]["status"] == "FAILED"


class TestEntitlements:
    def test_current_entitlements_matrix(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)
        licensing_service.sync_license(db_session, sync_client=_fake_sync_client())

        matrix = licensing_service.current_entitlements(db_session)
        assert matrix["modules"]["ventas"] is True
        assert matrix["modules"]["reportes"] is True
        assert licensing_service.module_entitled(db_session, "ventas") is True

    def test_module_not_entitled_denied_by_default(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)
        response = {
            "version": "1.0",
            "status": "FULL_ACCESS",
            "server_time": "2026-08-04T12:00:00+00:00",
            "expires_at": "2026-12-31T23:59:59+00:00",
            "entitlements": {"ventas": True, "reportes": False},
        }
        licensing_service.sync_license(db_session, sync_client=_fake_sync_client(response=response))

        assert licensing_service.module_entitled(db_session, "ventas") is True
        assert licensing_service.module_entitled(db_session, "reportes") is False


class TestOffline:
    def test_within_grace_valid(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)
        installation = db_session.execute(select_installation()).scalars().first()
        assert installation is not None
        state = db_session.execute(select_state(installation.installation_uuid)).scalars().first()
        assert state is not None
        state.last_reliable_date = datetime.now(UTC) - timedelta(days=2)
        db_session.commit()

        offline = licensing_service.verify_offline(db_session)
        assert offline["offline_valid"] is True
        assert offline["reason"] == "WITHIN_GRACE"
        assert offline["grace_days_left"] >= 1

    def test_grace_expired_invalid(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        _configure_central(db_session)
        installation = db_session.execute(select_installation()).scalars().first()
        assert installation is not None
        state = db_session.execute(select_state(installation.installation_uuid)).scalars().first()
        assert state is not None
        state.last_reliable_date = datetime.now(UTC) - timedelta(days=30)
        db_session.commit()

        offline = licensing_service.verify_offline(db_session)
        assert offline["offline_valid"] is False
        assert offline["reason"] == "GRACE_EXPIRED"


class TestRenovacionCentral:
    def test_renewal_workflow(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        req = licensing_service.create_renewal_request(
            db_session, payment_proof_ref="COMP-2026-01", notes="Pago anual", user_id="admin"
        )
        assert req.status == "REPORTED"

        verified = licensing_service.transition_renewal(db_session, request_id=str(req.id), target="VERIFIED", actor="provider")
        assert verified["status"] == "VERIFIED"

        issued = licensing_service.transition_renewal(db_session, request_id=str(req.id), target="ISSUED", actor="provider")
        assert issued["status"] == "ISSUED"

        with pytest.raises(ConflictError):
            licensing_service.transition_renewal(db_session, request_id=str(req.id), target="REJECTED", actor="provider")

    def test_renewal_not_found(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        with pytest.raises(NotFoundError):
            licensing_service.transition_renewal(db_session, request_id="no-existe", target="VERIFIED", actor="admin")

    def test_list_renewal_requests(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        licensing_service.create_renewal_request(db_session, payment_proof_ref="COMP-X", notes="", user_id="admin")
        requests = licensing_service.list_renewal_requests(db_session)
        assert len(requests) == 1
        assert requests[0]["status"] == "REPORTED"


class TestModos:
    def test_mode_transition_valid(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        result = licensing_service.transition_mode(db_session, target="READ_ONLY", actor="admin")
        assert result["to"] == "READ_ONLY"

        events = db_session.execute(select(LicenseEvent)).scalars().all()
        assert any(e.event_type == "LICENSE_MODE_CHANGED" for e in events)

    def test_mode_transition_invalid_blocks(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        licensing_service.transition_mode(db_session, target="READ_ONLY", actor="admin")
        # READ_ONLY es terminal: no se puede volver a FULL_ACCESS manualmente
        with pytest.raises(ConflictError):
            licensing_service.transition_mode(db_session, target="FULL_ACCESS", actor="admin")

    def test_mode_transition_invalid_target(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        with pytest.raises(KontrolError):
            licensing_service.transition_mode(db_session, target="BOGUS", actor="admin")


def select_state(installation_id: str):
    from sqlalchemy import select

    return select(LicenseState).where(LicenseState.installation_id == installation_id)
