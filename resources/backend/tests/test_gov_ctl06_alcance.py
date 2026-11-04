"""Suite de backend CTL-06 (GOV-CTL-008): alcance."""

from tests.test_gov_ctl06_hallazgos import (
    H,
    _crear_usuario_con_permisos,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_22_alcance_empresa_y_recurso_inexistente(mundo, gobierno, siembra):
    """GH6-22: alcance de empresa sobre detalle y listado; GET con UUID inexistente devuelve 404."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]

    response = mundo.client.get(
        f"/api/v1{H}/{hallazgo_id}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "GOV_FINDING_NOT_FOUND"

    response = mundo.client.get(f"/api/v1{H}", headers=mundo.como("ub", mundo.company_b))
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["items"]]
    assert hallazgo_id not in ids

    response = mundo.client.get(
        "/api/v1/gobierno/hallazgos/00000000-0000-0000-0000-000000000000",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "GOV_FINDING_NOT_FOUND"


def test_gh6_23_permisos_lectura_escritura_y_verificacion(mundo, gobierno, siembra):
    """GH6-23: permisos sobre listado, creación y verificación."""
    _crear_usuario_con_permisos(
        mundo,
        "solo_view_alcance",
        [("gobierno_hallazgos", "view")],
        mundo.company_a,
    )
    _crear_usuario_con_permisos(
        mundo,
        "solo_audit_alcance",
        [("audit", "view")],
        mundo.company_a,
    )

    response = mundo.client.get(
        f"/api/v1{H}",
        headers=mundo.como("solo_view_alcance", mundo.company_a),
    )
    assert response.status_code == 200, response.text

    cuerpo = {
        "titulo": "Hallazgo sin permiso de creación",
        "condicion": "Condición de prueba.",
        "criterio": "Criterio de prueba.",
        "causa": "Causa de prueba.",
        "efecto": "Efecto de prueba.",
        "riesgo": "MEDIO",
        "origen": "INDEPENDIENTE",
        "origen_descripcion": "Origen de prueba.",
    }
    response = mundo.client.post(
        f"/api/v1{H}",
        headers=mundo.como("solo_view_alcance", mundo.company_a),
        json=cuerpo,
    )
    assert response.status_code == 403, response.text

    response = mundo.client.get(
        f"/api/v1{H}",
        headers=mundo.como("solo_audit_alcance", mundo.company_a),
    )
    assert response.status_code == 403, response.text

    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]

    documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {
            "nota": "Avance completo para presentar.",
            "porcentaje": 100,
            "documento_id": documento_id,
        },
        version=detalle["version"],
    )
    assert response.status_code == 201, response.text
    detalle = response.json()

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=detalle["version"],
    )
    assert response.status_code == 200, response.text
    detalle = response.json()

    _crear_usuario_con_permisos(
        mundo,
        "manage_sin_verify_alcance",
        [("gobierno_hallazgos", "view"), ("gobierno_hallazgos", "manage")],
        mundo.company_a,
    )
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/verificar",
        "manage_sin_verify_alcance",
        mundo.company_a,
        {"nota": "Verificación sin permiso verify."},
        version=detalle["version"],
    )
    assert response.status_code == 403, response.text
