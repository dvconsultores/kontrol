"""REV Â· El claim `revision` del paquete firmado (Spec 004 Â· Autoridad Central Fase 1, FR-010-281..282).

Ausente es legacy; presente debe ser un entero â¥ 1 (ni booleano, ni cadena, ni decimal, ni null).
Viaja dentro de los bytes canÃ³nicos; su existencia no cambia un byte de los paquetes legacy. Payloads
sintÃ©ticos."""
from __future__ import annotations

import json

import pytest

from app.core.license_contract import (
    LicenseContractError,
    canonical_bytes,
    parse_license_payload,
    parse_revision,
)

LEGACY = {
    "issuer": "QA",
    "license_id": "LIC-SINTETICA",
    "installation_id": "KTL-XX-SINTETICA",
    "customer_id": "C",
    "contract_id": "K",
    "company_tax_id": "J-0",
    "period_start": "2027-04-01T00:00:00-04:00",
    "period_end": "2028-03-31T23:59:59-04:00",
    "critical_warning_start": "2028-04-21T00:00:00-04:00",
    "read_only_start": "2028-05-01T00:00:00-04:00",
    "entitlements": {"companies": 3},
    "minimum_version": "1.0.0",
    "kid": "kontrol-lic-2026-01",
}


def test_rev_01_sin_clave_es_legacy() -> None:
    assert parse_revision(LEGACY) is None
    assert parse_license_payload(LEGACY).revision is None


@pytest.mark.parametrize("n", [1, 2, 7, 10_000])
def test_rev_02_entero_positivo_se_acepta(n: int) -> None:
    assert parse_revision({**LEGACY, "revision": n}) == n
    assert parse_license_payload({**LEGACY, "revision": n}).revision == n


@pytest.mark.parametrize("invalid", [0, -1, 1.0, True, False, "1", None, [1], {"n": 1}])
def test_rev_03_valores_invalidos_se_rechazan(invalid: object) -> None:
    with pytest.raises(LicenseContractError) as excinfo:
        parse_revision({**LEGACY, "revision": invalid})
    assert excinfo.value.code == "LICENSE_INVALID_REVISION"

    with pytest.raises(LicenseContractError) as excinfo:
        parse_license_payload({**LEGACY, "revision": invalid})
    assert excinfo.value.code == "LICENSE_INVALID_REVISION"


def test_rev_04_null_explicito_no_es_legacy() -> None:
    with pytest.raises(LicenseContractError) as excinfo:
        parse_revision({**LEGACY, "revision": None})
    assert excinfo.value.code == "LICENSE_INVALID_REVISION"


def test_rev_05_la_revision_viaja_dentro_de_los_bytes_canonicos() -> None:
    assert b'"revision": 1' in canonical_bytes({**LEGACY, "revision": 1})
    assert b'"revision"' not in canonical_bytes(LEGACY)


def test_rev_06_los_bytes_legacy_no_cambian_por_existir_el_claim() -> None:
    assert canonical_bytes(LEGACY) == json.dumps(LEGACY, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert canonical_bytes(LEGACY) != canonical_bytes({**LEGACY, "revision": None})


def test_rev_07_el_resto_del_paquete_no_cambia_por_la_revision() -> None:
    d = parse_license_payload({**LEGACY, "revision": 3})
    assert d.license_id == "LIC-SINTETICA"
    assert d.kid == "kontrol-lic-2026-01"
    assert d.entitlements == {"companies": 3}
    assert d.period_start.year == 2027
