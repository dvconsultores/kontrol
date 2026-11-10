"""Pruebas del catálogo de auditoría para copia, restauración y RPO."""

import pytest

from app.shared.audit_catalog import CATALOG_VERSION, catalog


def test_catb_01_catalog_version() -> None:
    """CATB-01: la versión del catálogo es la esperada."""
    assert CATALOG_VERSION == "2026-11-08.1"


@pytest.mark.parametrize(
    ("code", "entity_type", "detail_keys"),
    [
        (
            "INSTALLATION_BACKUP_CREATED",
            "Installation",
            frozenset({"backup_id", "consistency_mode", "objects"}),
        ),
        (
            "INSTALLATION_RESTORED",
            "Installation",
            frozenset({"backup_created_at", "backup_id", "sessions_revoked"}),
        ),
        (
            "INSTALLATION_BACKUP_VERIFIED",
            "Installation",
            frozenset({"backup_id", "objects"}),
        ),
        (
            "INSTALLATION_BACKUP_VERIFY_FAILED",
            "Installation",
            frozenset({"backup_id", "error_code"}),
        ),
        (
            "INSTALLATION_BACKUP_FAILED",
            "Installation",
            frozenset({"backup_id", "error_code", "origin"}),
        ),
        (
            "INSTALLATION_BACKUP_PURGED",
            "Installation",
            frozenset({"backup_id"}),
        ),
        (
            "INSTALLATION_BACKUP_DESTINATION_UNAVAILABLE",
            "Installation",
            frozenset({"destination_label", "error_code"}),
        ),
        (
            "INSTALLATION_BACKUP_CONFIG_CHANGED",
            "Installation",
            frozenset({
                "configured_rpo_minutes",
                "destination_label",
                "retention_days",
                "retention_min_copies",
                "safety_margin_minutes",
                "schedule_interval_minutes",
                "scheduler_enabled",
            }),
        ),
        (
            "INSTALLATION_RPO_STATE_CHANGED",
            "Installation",
            frozenset({"from_state", "to_state"}),
        ),
    ],
)
def test_catb_02_entries(
    code: str,
    entity_type: str,
    detail_keys: frozenset[str],
) -> None:
    """CATB-02: las entradas existen con los atributos esperados."""
    entries = catalog()
    key = (code, entity_type)
    assert key in entries
    spec = entries[key]
    assert spec.code == code
    assert spec.entity_type == entity_type
    assert spec.scope == "TENANT"
    assert spec.security_class == "SECURITY"
    assert spec.transaction_class == "BUSINESS_COMMIT"
    assert spec.owner_module == "ops"
    assert spec.owner_spec == "001"
    assert spec.lifecycle == "ACTIVE"
    assert spec.emission == "STATIC"
    assert spec.tenant_required is True
    assert spec.detail_keys == detail_keys


def test_catb_03_catalog_size() -> None:
    """CATB-03: el catálogo tiene exactamente 453 entradas."""
    assert len(catalog()) == 453
