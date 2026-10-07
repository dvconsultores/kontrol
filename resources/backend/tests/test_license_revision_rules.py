"""REV · Verifica caso por caso la función pura ``resolve_same_period_reissue`` del contrato de licencias.

Cubre las reglas R1..R14 de reemisión en el mismo período: igualdad de artefacto, puente legacy,
revisiones más nuevas, degradaciones, conflictos y validación de revisiones inválidas.
"""

from __future__ import annotations

import pytest

from app.core.license_contract import (
    LEGACY_AFTER_REVISION,
    LEGACY_REISSUE_REQUIRES_REVISION,
    LEGACY_TO_REVISION_BRIDGE,
    NEWER_REVISION,
    REISSUE_REJECTIONS,
    REVISION_CONFLICT,
    REVISION_DOWNGRADE,
    SAME_ARTIFACT,
    LicenseContractError,
    resolve_same_period_reissue,
)


def test_rrev_01_legacy_mismo_hash_es_same_artifact() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=None,
        current_payload_hash="h1",
        incoming_revision=None,
        incoming_payload_hash="h1",
    )
    assert resultado == SAME_ARTIFACT


def test_rrev_02_legacy_hash_distinto_requiere_revision() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=None,
        current_payload_hash="h1",
        incoming_revision=None,
        incoming_payload_hash="h2",
    )
    assert resultado == LEGACY_REISSUE_REQUIRES_REVISION


def test_rrev_03_legacy_sin_huella_requiere_revision() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=None,
        current_payload_hash=None,
        incoming_revision=None,
        incoming_payload_hash="h1",
    )
    assert resultado == LEGACY_REISSUE_REQUIRES_REVISION


@pytest.mark.parametrize("incoming", [1, 7], ids=["incoming_1", "incoming_7"])
def test_rrev_04_legacy_a_revision_es_puente(incoming: int) -> None:
    resultado = resolve_same_period_reissue(
        current_revision=None,
        current_payload_hash=None,
        incoming_revision=incoming,
        incoming_payload_hash="h1",
    )
    assert resultado == LEGACY_TO_REVISION_BRIDGE


def test_rrev_05_revision_actual_con_incoming_legacy() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=3,
        current_payload_hash="h1",
        incoming_revision=None,
        incoming_payload_hash="h2",
    )
    assert resultado == LEGACY_AFTER_REVISION


@pytest.mark.parametrize(
    "current, incoming",
    [(1, 2), (2, 3), (1, 50)],
    ids=["1_a_2", "2_a_3", "1_a_50"],
)
def test_rrev_06_revision_superior_es_newer_revision(current: int, incoming: int) -> None:
    resultado = resolve_same_period_reissue(
        current_revision=current,
        current_payload_hash="h1",
        incoming_revision=incoming,
        incoming_payload_hash="h2",
    )
    assert resultado == NEWER_REVISION


@pytest.mark.parametrize(
    "current, incoming",
    [(3, 2), (3, 1), (50, 1)],
    ids=["3_a_2", "3_a_1", "50_a_1"],
)
def test_rrev_07_revision_inferior_es_downgrade(current: int, incoming: int) -> None:
    resultado = resolve_same_period_reissue(
        current_revision=current,
        current_payload_hash="h1",
        incoming_revision=incoming,
        incoming_payload_hash="h2",
    )
    assert resultado == REVISION_DOWNGRADE


def test_rrev_08_misma_revision_mismo_hash() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=2,
        current_payload_hash="h1",
        incoming_revision=2,
        incoming_payload_hash="h1",
    )
    assert resultado == SAME_ARTIFACT


def test_rrev_09_misma_revision_hash_distinto_es_conflicto() -> None:
    resultado = resolve_same_period_reissue(
        current_revision=2,
        current_payload_hash="h1",
        incoming_revision=2,
        incoming_payload_hash="h2",
    )
    assert resultado == REVISION_CONFLICT


def test_rrev_10_conjunto_de_rechazos() -> None:
    assert REISSUE_REJECTIONS == frozenset(
        {
            LEGACY_REISSUE_REQUIRES_REVISION,
            LEGACY_AFTER_REVISION,
            REVISION_DOWNGRADE,
            REVISION_CONFLICT,
        }
    )
    assert SAME_ARTIFACT not in REISSUE_REJECTIONS
    assert NEWER_REVISION not in REISSUE_REJECTIONS
    assert LEGACY_TO_REVISION_BRIDGE not in REISSUE_REJECTIONS


@pytest.mark.parametrize(
    "current, incoming",
    [(0, None), (None, 0)],
    ids=["current_0", "incoming_0"],
)
def test_rrev_11_revision_cero_es_invalida(current: int | None, incoming: int | None) -> None:
    with pytest.raises(LicenseContractError) as exc:
        resolve_same_period_reissue(
            current_revision=current,
            current_payload_hash="h1",
            incoming_revision=incoming,
            incoming_payload_hash="h1",
        )
    assert exc.value.code == "LICENSE_INVALID_REVISION"


def test_rrev_12_bool_no_es_revision_incoming() -> None:
    with pytest.raises(LicenseContractError) as exc:
        resolve_same_period_reissue(
            current_revision=None,
            current_payload_hash="h1",
            incoming_revision=True,
            incoming_payload_hash="h1",
        )
    assert exc.value.code == "LICENSE_INVALID_REVISION"


def test_rrev_12_bool_no_es_revision_current() -> None:
    with pytest.raises(LicenseContractError) as exc:
        resolve_same_period_reissue(
            current_revision=True,
            current_payload_hash="h1",
            incoming_revision=2,
            incoming_payload_hash="h1",
        )
    assert exc.value.code == "LICENSE_INVALID_REVISION"


def test_rrev_13_revision_negativa_es_invalida() -> None:
    with pytest.raises(LicenseContractError) as exc:
        resolve_same_period_reissue(
            current_revision=None,
            current_payload_hash="h1",
            incoming_revision=-1,
            incoming_payload_hash="h1",
        )
    assert exc.value.code == "LICENSE_INVALID_REVISION"


@pytest.mark.parametrize(
    "current, incoming, current_hash, incoming_hash, esperado",
    [
        (1, 2, "a", "b", NEWER_REVISION),
        (1, 2, "a", "a", NEWER_REVISION),
        (2, 1, "a", "b", REVISION_DOWNGRADE),
        (2, 1, "a", "a", REVISION_DOWNGRADE),
    ],
    ids=["newer_hash_distinto", "newer_hash_igual", "downgrade_hash_distinto", "downgrade_hash_igual"],
)
def test_rrev_14_el_resultado_depende_solo_de_revision(
    current: int,
    incoming: int,
    current_hash: str,
    incoming_hash: str,
    esperado: str,
) -> None:
    resultado = resolve_same_period_reissue(
        current_revision=current,
        current_payload_hash=current_hash,
        incoming_revision=incoming,
        incoming_payload_hash=incoming_hash,
    )
    assert resultado == esperado
