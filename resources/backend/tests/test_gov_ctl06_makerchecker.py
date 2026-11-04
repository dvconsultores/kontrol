"""Suite de backend CTL-06 (GOV-CTL-008): maker-checker, separando avances y presentación."""
from tests.test_gov_ctl06_hallazgos import (
    H,
    _crear_usuario_con_permisos,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_31_presentador_no_puede_verificar(mundo, gobierno, siembra):
    """GH6-31: «ua» registra el avance y «uab» presenta; quien presentó no puede verificar."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance del 100 % con evidencia.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "uab",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "uab",
        mundo.company_a,
        {"nota": "Verificación con conflicto de maker-checker."},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_SELF_VERIFICATION"


def test_gh6_32_autor_de_avance_no_puede_verificar(mundo, gobierno, siembra):
    """GH6-32: «ua» registra el avance y «uab» presenta; el autor del avance no puede verificar; un tercero sí."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance del 100 % con evidencia.", "porcentaje": 100, "documento_id": documento_id},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "uab",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "ua",
        mundo.company_a,
        {"nota": "Verificación con conflicto de maker-checker."},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_SELF_VERIFICATION"

    _crear_usuario_con_permisos(
        mundo,
        "verificador_mc",
        [("gobierno_hallazgos", "view"), ("gobierno_hallazgos", "verify")],
        mundo.company_a,
    )

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "verificador_mc",
        mundo.company_a,
        {"nota": "Evidencia validada por un verificador independiente."},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["estado"] == "CERRADO"
