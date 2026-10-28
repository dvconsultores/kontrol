"""Pruebas unitarias del catálogo cerrado de auditoría.

Usan un catálogo sintético construido con `build_catalog` y se pasa a las
funciones mediante `catalog_map`, sin depender de `audit_catalog_entries`.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.shared.audit_catalog import (
    UNCATALOGUED_SCOPE,
    AuditActionSpec,
    AuditContractError,
    build_catalog,
    keys,
    label_of,
    public_actions,
    safe_details,
    scope_of,
    validate_event,
)


def _spec(
    code: str = "CREATE",
    entity_type: str = "invoice",
    *,
    scope: str = "TENANT",
    lifecycle: str = "ACTIVE",
    emission: str = "STATIC",
    emitted_by: str = "",
    tenant_required: bool = True,
    detail_keys: frozenset[str] | None = None,
    label: str = "Crear factura",
) -> AuditActionSpec:
    return AuditActionSpec(
        code=code,
        entity_type=entity_type,
        owner_module="facturacion",
        owner_spec="spec-001",
        scope=scope,
        security_class="FINANCIAL",
        transaction_class="BUSINESS_COMMIT",
        detail_keys=detail_keys
        if detail_keys is not None
        else keys("id", "estado", "permitida"),
        label=label,
        lifecycle=lifecycle,
        emission=emission,
        emitted_by=emitted_by,
        tenant_required=tenant_required,
    )


@pytest.fixture
def catalogo_sintetico() -> dict:
    """Catálogo mínimo reutilizable, con una entrada TENANT y una COMPANY."""
    tenant = _spec()
    company = _spec(
        code="COMPANY_CREATE",
        entity_type="company",
        scope="COMPANY",
        detail_keys=keys("cif", "razon_social"),
        label="Crear empresa",
    )
    return {tenant.key: tenant, company.key: company}


def test_cat01_company_con_empresa_tenant_y_claves_permitidas(
    catalogo_sintetico: dict,
) -> None:
    entrada = validate_event(
        action="COMPANY_CREATE",
        entity_type="company",
        tenant_id="tenant-1",
        company_id="company-1",
        before=None,
        after={"cif": "A123", "razon_social": "Ejemplo"},
        evidence=None,
        catalog_map=catalogo_sintetico,
    )
    assert entrada.key == ("COMPANY_CREATE", "company")


def test_cat02_par_desconocido(catalogo_sintetico: dict) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="BORRAR",
            entity_type="cliente",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after=None,
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_ACTION_UNCATALOGUED"


def test_cat03_entrada_legacy() -> None:
    legacy = _spec(lifecycle="LEGACY")
    catalogo = {legacy.key: legacy}
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after=None,
            evidence=None,
            catalog_map=catalogo,
        )
    assert error.value.code == "AUDIT_ACTION_LEGACY"


def test_cat04_company_sin_empresa(catalogo_sintetico: dict) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="COMPANY_CREATE",
            entity_type="company",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after=None,
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_COMPANY_REQUIRED"


def test_cat05_tenant_con_empresa_y_tenant_sin_empresa(
    catalogo_sintetico: dict,
) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id="company-1",
            before=None,
            after=None,
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_SCOPE_MISMATCH"

    entrada = validate_event(
        action="CREATE",
        entity_type="invoice",
        tenant_id="tenant-1",
        company_id=None,
        before=None,
        after=None,
        evidence=None,
        catalog_map=catalogo_sintetico,
    )
    assert entrada.key == ("CREATE", "invoice")


def test_cat06_tenant_sin_tenant_y_no_requerido(catalogo_sintetico: dict) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id=None,
            company_id=None,
            before=None,
            after=None,
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_TENANT_REQUIRED"

    no_requerido = _spec(tenant_required=False, detail_keys=keys("observacion"))
    catalogo = {no_requerido.key: no_requerido}
    entrada = validate_event(
        action="CREATE",
        entity_type="invoice",
        tenant_id=None,
        company_id=None,
        before=None,
        after={"observacion": "ok"},
        evidence=None,
        catalog_map=catalogo,
    )
    assert entrada.key == ("CREATE", "invoice")


def test_cat07_clave_primer_nivel_no_permitida(catalogo_sintetico: dict) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after={"no_permitida": "x"},
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_DETAIL_KEY_NOT_ALLOWED"


@pytest.mark.parametrize(
    "clave_prohibida",
    [
        "password",
        "token",
        "otp",
        "recovery_codes",
        "signature",
        "file_path",
        "storage_key",
        "original_name",
        "Content",
    ],
)
def test_cat08_claves_prohibidas_anidadas_y_primer_nivel(
    catalogo_sintetico: dict, clave_prohibida: str
) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after={"permitida": {clave_prohibida: "x"}},
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_DETAIL_FORBIDDEN"

    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after={clave_prohibida: "x"},
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_DETAIL_FORBIDDEN"


def test_cat09_valores_binarios_anidados(catalogo_sintetico: dict) -> None:
    for valor in (b"datos", bytearray(b"datos"), memoryview(b"datos")):
        with pytest.raises(AuditContractError) as error:
            validate_event(
                action="CREATE",
                entity_type="invoice",
                tenant_id="tenant-1",
                company_id=None,
                before=None,
                after={"permitida": [valor]},
                evidence=None,
                catalog_map=catalogo_sintetico,
            )
        assert error.value.code == "AUDIT_DETAIL_FORBIDDEN"


def test_cat10_seccion_no_dict(catalogo_sintetico: dict) -> None:
    with pytest.raises(AuditContractError) as error:
        validate_event(
            action="CREATE",
            entity_type="invoice",
            tenant_id="tenant-1",
            company_id=None,
            before=None,
            after="texto",
            evidence=None,
            catalog_map=catalogo_sintetico,
        )
    assert error.value.code == "AUDIT_DETAIL_NOT_OBJECT"


@pytest.mark.parametrize(
    "caso, generador",
    [
        (
            "duplicado",
            lambda: [
                _spec(label="a"),
                _spec(label="b"),
            ],
        ),
        ("scope_invalido", lambda: [_spec(scope="MUNICIPIO")]),
        ("label_vacio", lambda: [_spec(label="   ")]),
        ("detail_prohibido", lambda: [_spec(detail_keys=keys("Token"))]),
        (
            "emision_dynamic_sin_emitter",
            lambda: [_spec(emission="DYNAMIC", emitted_by="")],
        ),
        (
            "company_sin_tenant",
            lambda: [_spec(scope="COMPANY", tenant_required=False)],
        ),
    ],
)
def test_cat11_build_catalog_invalido(
    caso: str, generador: Callable[[], list[AuditActionSpec]]
) -> None:
    entradas = generador()
    with pytest.raises(ValueError):
        build_catalog(entradas)


def test_cat12_safe_details(catalogo_sintetico: dict) -> None:
    resultado = safe_details(
        "CREATE",
        "invoice",
        before={
            "permitida": {"anidada": 1, "token": "secreto"},
            "no_permitida": "x",
            "password": "secreto",
        },
        after={"permitida": b"binario", "estado": "ok"},
        evidence="no es diccionario",
        catalog_map=catalogo_sintetico,
    )

    assert resultado["before"] == {"permitida": {"anidada": 1}}
    assert resultado["after"] == {
        "permitida": "[binario omitido]",
        "estado": "ok",
    }
    assert "evidence" not in resultado

    vacio = safe_details(
        "NO_EXISTE",
        "entidad",
        before={"permitida": "x"},
        after=None,
        evidence=None,
        catalog_map=catalogo_sintetico,
    )
    assert vacio == {}

    eliminada = safe_details(
        "CREATE",
        "invoice",
        before=None,
        after={"no_permitida": "x"},
        evidence=None,
        catalog_map=catalogo_sintetico,
    )
    assert "after" not in eliminada

    conjuntos = safe_details(
        "CREATE",
        "invoice",
        before=None,
        after={"permitida": {("a", b"x")}},
        evidence=None,
        catalog_map=catalogo_sintetico,
    )
    assert conjuntos == {"after": {"permitida": [["a", "[binario omitido]"]]}}


def test_cat13_public_actions_orden_y_claves(catalogo_sintetico: dict) -> None:
    acciones = public_actions(catalog_map=catalogo_sintetico)
    assert acciones == sorted(
        acciones, key=lambda item: (item["code"], item["entity_type"])
    )
    assert len(acciones) == 2
    for accion in acciones:
        assert set(accion.keys()) == {
            "code",
            "entity_type",
            "label",
            "scope",
            "lifecycle",
        }


def test_cat14_scope_of_y_label_of(catalogo_sintetico: dict) -> None:
    assert scope_of("CREATE", "invoice", catalog_map=catalogo_sintetico) == "TENANT"
    assert (
        scope_of("NO_EXISTE", "entidad", catalog_map=catalogo_sintetico)
        == UNCATALOGUED_SCOPE
    )
    assert (
        label_of("CREATE", "invoice", catalog_map=catalogo_sintetico)
        == "Crear factura"
    )
    assert label_of("NO_EXISTE", "entidad", catalog_map=catalogo_sintetico) == "NO_EXISTE"
