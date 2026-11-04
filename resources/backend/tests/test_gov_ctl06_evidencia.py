"""Suite de backend CTL-06 (GOV-CTL-008): evidencia."""
from tests.test_gov_ctl06_hallazgos import (
    H,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_16_evidencia_requerida_invalida_y_valida(mundo, gobierno, siembra):
    """GH6-16: avance 100 sin documento → 422 GOV_FINDING_EVIDENCE_REQUIRED; documento vinculado a otra acción → 422 GOV_FINDING_EVIDENCE_INVALID; documento válido → 201, acción COMPLETADA y documento listado."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    # 1. Sin documento: 422 GOV_FINDING_EVIDENCE_REQUIRED
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance final sin evidencia.", "porcentaje": 100},
        version=version,
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "GOV_FINDING_EVIDENCE_REQUIRED"

    # 2. Documento vinculado a OTRA acción: 422 GOV_FINDING_EVIDENCE_INVALID
    otro = _hallazgo_en_remediacion(mundo, siembra)
    otro_accion_id = otro["acciones"][0]["id"]
    doc_otra_accion = _doc_vinculado(mundo, mundo.company_a, otro_accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {
            "nota": "Avance final con documento de otra acción.",
            "porcentaje": 100,
            "documento_id": doc_otra_accion,
        },
        version=version,
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "GOV_FINDING_EVIDENCE_INVALID"

    # 3. Documento vinculado a la acción: 201, acción COMPLETADA y documento listado
    doc_accion = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {
            "nota": "Avance final con evidencia válida.",
            "porcentaje": 100,
            "documento_id": doc_accion,
        },
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    assert detalle["acciones"][0]["estado"] == "COMPLETADA"
    assert doc_accion in detalle["acciones"][0]["documentos"]


def test_gh6_17_presentar_acciones_incompletas_y_evidencia_presentada(mundo, gobierno, siembra):
    """GH6-17: presentar con acción al 50 → 409 GOV_FINDING_ACTIONS_INCOMPLETE; acción completada → 200 EVIDENCIA_PRESENTADA y presentado_por "ua"."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    # Avance al 50 (no requiere documento)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance parcial al 50%.", "porcentaje": 50},
        version=version,
    )
    assert response.status_code == 201, response.text
    version = response.json()["version"]

    # Presentar con acción al 50 → 409 GOV_FINDING_ACTIONS_INCOMPLETE
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_ACTIONS_INCOMPLETE"

    # Completar la acción con documento válido
    doc_accion = _doc_vinculado(mundo, mundo.company_a, accion_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {
            "nota": "Avance final al 100%.",
            "porcentaje": 100,
            "documento_id": doc_accion,
        },
        version=version,
    )
    assert response.status_code == 201, response.text
    version = response.json()["version"]

    # Presentar con acción completada → 200 EVIDENCIA_PRESENTADA
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["estado"] == "EVIDENCIA_PRESENTADA"
    assert detalle["presentado_por"] == "ua"
