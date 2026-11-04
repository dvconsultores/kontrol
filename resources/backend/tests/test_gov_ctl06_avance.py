"""Suite de backend CTL-06 (GOV-CTL-008): avance."""
from datetime import timedelta

from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import (
    H,
    _hallazgo_con_recomendacion,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_14_avance_en_plan_de_accion_y_ejecucion(mundo, gobierno, siembra):
    """GH6-14: avance en PLAN_DE_ACCION → 409; tras ejecucion → 200 EN_REMEDIACION."""
    detalle = _hallazgo_con_recomendacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    recomendacion_id = detalle["recomendaciones"][0]["id"]
    version = detalle["version"]

    fecha_objetivo = (hoy_de_negocio() + timedelta(days=20)).strftime("%Y-%m-%d")
    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones",
        "ua",
        mundo.company_a,
        {
            "recomendacion_id": recomendacion_id,
            "descripcion": "Acción para completar el plan correctivo.",
            "cargo_id": siembra["cargo_vigente"],
            "fecha_objetivo": fecha_objetivo,
        },
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    version = detalle["version"]
    accion_id = detalle["acciones"][0]["id"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/plan",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    version = detalle["version"]
    assert detalle["estado"] == "PLAN_DE_ACCION"

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance prematuro.", "porcentaje": 10},
        version=version,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "GOV_FINDING_INVALID_STATE"

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/ejecucion",
        "ua",
        mundo.company_a,
        {},
        version=version,
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["estado"] == "EN_REMEDIACION"
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance ya en remediación.", "porcentaje": 10},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    assert detalle["estado"] == "EN_REMEDIACION"


def test_gh6_15_avance_50_y_30_regresivo(mundo, gobierno, siembra):
    """GH6-15: avance 50 → acción EN_CURSO y porcentaje 50; avance 30 → 422 GOV_FINDING_PROGRESS_INVALID."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    accion_id = detalle["acciones"][0]["id"]
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance inicial al 50%.", "porcentaje": 50},
        version=version,
    )
    assert response.status_code == 201, response.text
    detalle = response.json()
    assert detalle["acciones"][0]["estado"] == "EN_CURSO"
    assert detalle["acciones"][0]["avances"][-1]["porcentaje"] == 50
    version = detalle["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance regresivo al 30%.", "porcentaje": 30},
        version=version,
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "GOV_FINDING_PROGRESS_INVALID"
