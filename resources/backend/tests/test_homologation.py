"""Pruebas de homologación y liberación (011).

Cubren: registro/sometimiento/evaluación del acto de homologación con
segregación y acto formal, regla de "homologado", versiones con changelog y
gates, liberación gateada (homologación + licencia) y timeline.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import make_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.homologation import service as homologation_service
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
    """Activa una licencia firmada (FULL_ACCESS) para el gate de liberación."""
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
    installation = db.query(Installation).first()
    assert installation is not None
    payload = {
        "issuer": "KONTROL Licensing Authority",
        "license_id": "LIC-011000",
        "installation_id": installation.installation_uuid,
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

    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = authority_pub
    get_settings.cache_clear()
    try:
        from app.modules.licensing import service as licensing_service

        licensing_service.import_license(db, payload=payload, signature_hex=signature_hex, source="MANUAL")
    finally:
        # El ancla se queda configurada: el vigente se reverifica contra ella (LICENCIA-ESTADO-SIN-REVERIFICAR).
        get_settings.cache_clear()


def _create_record(db: Session, actor: str = "admin", *, evidence: bool = True, formal_act: bool = True) -> dict:
    return homologation_service.create_record(
        db,
        fiscal_version="2026-1.0",
        modality="E_FACTURA",
        formal_act_ref="ACT-2026-001" if formal_act else None,
        evidence_sha256="a" * 64 if evidence else None,
        notes="Acto inicial",
        actor=actor,
    )


def _approved_record(db: Session, actor: str = "admin", evaluator: str = "fiscal-1") -> dict:
    record = _create_record(db, actor=actor)
    homologation_service.submit_record(db, record_id=record["id"], actor=actor)
    return homologation_service.evaluate_record(
        db, record_id=record["id"], decision="APPROVED", formal_act_ref="ACT-2026-001", notes="OK", actor=evaluator
    )


def _gates() -> dict:
    return {
        "tests": {"passed": True, "checked_by": "qa", "checked_at": "2026-08-04"},
        "security": {"passed": True, "checked_by": "sec", "checked_at": "2026-08-04"},
        "backup": {"passed": True, "checked_by": "ops", "checked_at": "2026-08-04"},
    }


class TestHomologacion:
    def test_create_and_submit(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session)
        assert record["status"] == "DRAFT"

        submitted = homologation_service.submit_record(db_session, record_id=record["id"], actor="admin")
        assert submitted["status"] == "SUBMITTED"

    def test_submit_requires_evidence(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session, evidence=False)
        with pytest.raises(KontrolError) as exc:
            homologation_service.submit_record(db_session, record_id=record["id"], actor="admin")
        assert exc.value.code == "HOMOLOGATION_INCOMPLETE"

    def test_approve_with_segregation(self, db_session) -> None:
        _setup(db_session)
        approved = _approved_record(db_session)
        assert approved["status"] == "APPROVED"
        assert approved["homologated"] is True
        assert approved["evaluated_by"] == "fiscal-1"

    def test_segregation_blocks_self_approval(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session, actor="admin")
        homologation_service.submit_record(db_session, record_id=record["id"], actor="admin")
        with pytest.raises(ConflictError) as exc:
            homologation_service.evaluate_record(
                db_session, record_id=record["id"], decision="APPROVED", formal_act_ref="ACT-2026-001", notes="", actor="admin"
            )
        assert exc.value.code == "SEGREGATION_VIOLATION"

    def test_approve_requires_formal_act(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session, formal_act=False)
        homologation_service.submit_record(db_session, record_id=record["id"], actor="admin")
        with pytest.raises(KontrolError) as exc:
            homologation_service.evaluate_record(
                db_session, record_id=record["id"], decision="APPROVED", formal_act_ref=None, notes="", actor="fiscal-1"
            )
        assert exc.value.code == "FORMAL_ACT_REQUIRED"

    def test_not_homologated_without_formal_act(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session)
        # Aprobado sin acto formal no es posible por regla; un DRAFT tampoco es homologado.
        assert record["homologated"] is False
        assert record["status"] == "DRAFT"

    def test_events_recorded(self, db_session) -> None:
        _setup(db_session)
        record = _create_record(db_session)
        homologation_service.submit_record(db_session, record_id=record["id"], actor="admin")
        detail = homologation_service.get_record(db_session, record["id"])
        types = [e["event_type"] for e in detail["events"]]
        assert "HOMOLOGATION_CREATED" in types
        assert "HOMOLOGATION_SUBMITTED" in types

    def test_record_not_found(self, db_session) -> None:
        _setup(db_session)
        with pytest.raises(NotFoundError):
            homologation_service.get_record(db_session, "no-existe")


class TestLiberacion:
    def test_create_and_promote(self, db_session) -> None:
        _setup(db_session)
        release = homologation_service.create_release(
            db_session, version="1.1.0", changelog={"summary": "Nuevo módulo"}, gates=_gates(), notes="", actor="admin"
        )
        assert release["status"] == "DRAFT"

        promoted = homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")
        assert promoted["status"] == "CANDIDATE"

    def test_promote_requires_gates(self, db_session) -> None:
        _setup(db_session)
        release = homologation_service.create_release(
            db_session, version="1.2.0", changelog={}, gates={}, notes="", actor="admin"
        )
        with pytest.raises(KontrolError) as exc:
            homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")
        assert exc.value.code == "GATES_MISSING"

    def test_invalid_version_rejected(self, db_session) -> None:
        _setup(db_session)
        with pytest.raises(KontrolError) as exc:
            homologation_service.create_release(db_session, version="abc", changelog={}, gates={}, notes="", actor="admin")
        assert exc.value.code == "INVALID_VERSION"

    def test_duplicate_version_rejected(self, db_session) -> None:
        _setup(db_session)
        homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates={}, notes="", actor="admin")
        with pytest.raises(ConflictError):
            homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates={}, notes="", actor="admin")

    def test_release_blocked_without_homologation(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        release = homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")

        result = homologation_service.release_version(db_session, release_id=release["id"], homologation_id=None, notes="", actor="admin")
        assert result["status"] == "BLOCKED"
        assert "HOMOLOGATION_NOT_DOCUMENTED" in result["blocked_reasons"]["reasons"]

    def test_release_blocked_without_license(self, db_session) -> None:
        _setup(db_session)
        approved = _approved_record(db_session)
        # Sin licencia activa, el modo no es FULL_ACCESS.
        release = homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")

        result = homologation_service.release_version(
            db_session, release_id=release["id"], homologation_id=approved["id"], notes="", actor="admin"
        )
        assert result["status"] == "BLOCKED"
        assert "LICENSE_NOT_VALID" in result["blocked_reasons"]["reasons"]

    def test_release_success_with_all_gates(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        approved = _approved_record(db_session)
        release = homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")

        result = homologation_service.release_version(
            db_session, release_id=release["id"], homologation_id=approved["id"], notes="", actor="admin"
        )
        assert result["status"] == "RELEASED"
        assert result["homologation_id"] == approved["id"]
        assert result["released_by"] == "admin"

    def test_older_release_blocked(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        approved = _approved_record(db_session)

        newer = homologation_service.create_release(db_session, version="1.2.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=newer["id"], actor="admin")
        first = homologation_service.release_version(
            db_session, release_id=newer["id"], homologation_id=approved["id"], notes="", actor="admin"
        )
        assert first["status"] == "RELEASED"

        older = homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=older["id"], actor="admin")
        second = homologation_service.release_version(
            db_session, release_id=older["id"], homologation_id=approved["id"], notes="", actor="admin"
        )
        assert second["status"] == "BLOCKED"
        assert "RELEASE_OLDER_THAN_APPLIED" in second["blocked_reasons"]["reasons"]

    def test_timeline(self, db_session) -> None:
        _setup(db_session)
        _activate_license(db_session)
        approved = _approved_record(db_session)
        release = homologation_service.create_release(db_session, version="1.1.0", changelog={}, gates=_gates(), notes="", actor="admin")
        homologation_service.promote_release(db_session, release_id=release["id"], actor="admin")
        homologation_service.release_version(db_session, release_id=release["id"], homologation_id=approved["id"], notes="", actor="admin")

        timeline = homologation_service.timeline(db_session)
        types = {e["event_type"] for e in timeline}
        assert "HOMOLOGATION_CREATED" in types
        assert "HOMOLOGATION_SUBMITTED" in types
        assert "HOMOLOGATION_APPROVED" in types
        assert "RELEASE_CREATED" in types
        assert "RELEASE_RELEASED" in types
