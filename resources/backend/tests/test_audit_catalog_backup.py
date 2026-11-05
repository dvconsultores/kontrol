"""Pruebas del catálogo de auditoría para copia y restauración verificadas."""

import pytest

from app.shared.audit_catalog import CATALOG_VERSION, catalog


def test_catb_01_catalog_version() -> None:
    """CATB-01: la versión del catálogo es la esperada."""
    assert CATALOG_VERSION == "2026-10-28.2"


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
    """CATB-03: el catálogo tiene exactamente 303 entradas."""
    assert len(catalog()) == 303
