"""Suite de backend CTL-06 (GOV-CTL-008): listado."""
import os
from datetime import timedelta

import pytest
from sqlalchemy import select, text

from app.modules.audit.models import AuditEvent
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import (
    H,
    _cuerpo_independiente,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_24_listado_y_resumen(mundo, gobierno, siembra):
    """GH6-24: filtrar estado=CERRADO devuelve solo cerrados; riesgo=ALTO solo ALTO; acción vencida se refleja en resumen y detalle."""
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")

    # Crear un hallazgo en remediación para poder poner una acción vencida por SQL.
    detalle_alto = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_alto_id = detalle_alto["id"]
    accion_alto_id = detalle_alto["acciones"][0]["id"]

    # Cerrar otro hallazgo para verificar el filtro estado=CERRADO.
    detalle_cerrado = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_cerrado_id = detalle_cerrado["id"]
    accion_cerrado_id = detalle_cerrado["acciones"][0]["id"]
    version_cerrado = detalle_cerrado["version"]

    doc_cerrado = _doc_vinculado(mundo, mundo.company_a, accion_cerrado_id)
    response = _post(
        mundo,
        f"{H}/{hallazgo_cerrado_id}/acciones/{accion_cerrado_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance completo para cerrar.", "porcentaje": 100, "documento_id": doc_cerrado},
        version=version_cerrado,
    )
    assert response.status_code == 201, response.text
    detalle_cerrado = response.json()
    version_cerrado = detalle_cerrado["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_cerrado_id}/presentar",
        "ua",
        mundo.company_a,
        {},
        version=version_cerrado,
    )
    assert response.status_code == 200, response.text
    detalle_cerrado = response.json()
    version_cerrado = detalle_cerrado["version"]

    response = _post(
        mundo,
        f"{H}/{hallazgo_cerrado_id}/verificar",
        "uab",
        mundo.company_a,
        {"nota": "Verificación satisfactoria del cierre."},
        version=version_cerrado,
    )
    assert response.status_code == 200, response.text

    # Poner la fecha objetivo de la acción del hallazgo ALTO en ayer.
    ayer = (hoy_de_negocio() - timedelta(days=1)).strftime("%Y-%m-%d")
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_corrective_actions SET fecha_objetivo = :fecha WHERE id = :id"),
            {"fecha": ayer, "id": accion_alto_id},
        )
        db.commit()

    # Listado con estado=CERRADO: solo debe aparecer el hallazgo cerrado.
    response = mundo.get(f"{H}?estado=CERRADO", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    datos = response.json()
    assert "items" in datos
    items_cerrados = datos["items"]
    assert len(items_cerrados) >= 1
    ids_cerrados = {item["id"] for item in items_cerrados}
    assert hallazgo_cerrado_id in ids_cerrados
    assert hallazgo_alto_id not in ids_cerrados
    for item in items_cerrados:
        assert item["estado"] == "CERRADO"

    # Listado con riesgo=ALTO: debe incluir solo hallazgos con riesgo ALTO.
    cuerpo_alto = _cuerpo_independiente(riesgo="ALTO", titulo="Hallazgo de riesgo ALTO para listado")
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo_alto)
    assert response.status_code == 201, response.text
    hallazgo_riesgo_alto_id = response.json()["id"]

    response = mundo.get(f"{H}?riesgo=ALTO", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    items_alto = response.json()["items"]
    assert len(items_alto) >= 1
    ids_alto = {item["id"] for item in items_alto}
    assert hallazgo_riesgo_alto_id in ids_alto
    for item in items_alto:
        assert item["riesgo"] == "ALTO"

    # Resumen: debe reflejar la acción vencida y el cerrado.
    response = mundo.get(f"{H}", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    resumen = response.json()["resumen"]
    assert resumen["acciones_vencidas"] >= 1
    assert resumen["cerrados"] >= 1

    # vencidas=true debe incluir el hallazgo ALTO con la acción vencida.
    response = mundo.get(f"{H}?vencidas=true", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    items_vencidas = response.json()["items"]
    ids_vencidas = {item["id"] for item in items_vencidas}
    assert hallazgo_alto_id in ids_vencidas

    # El detalle de ese hallazgo debe marcar la acción como vencida.
    response = mundo.get(f"{H}/{hallazgo_alto_id}", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert any(accion.get("vencida") is True for accion in detalle["acciones"])


def test_gh6_25_exportar(mundo, gobierno, siembra):
    """GH6-25: exportar CSV con cabecera exacta, al menos una fila y auditoría GOV_FINDINGS_EXPORTED."""
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")

    # Crear un hallazgo en remediación para garantizar al menos una fila exportable.
    _hallazgo_en_remediacion(mundo, siembra)

    response = mundo.get(f"{H}/exportar", "ua", mundo.company_a)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "plan-acciones-" in response.headers.get("content-disposition", "")

    texto = response.text
    lineas = texto.splitlines()
    assert len(lineas) >= 2
    cabecera_esperada = (
        "codigo,titulo,riesgo,estado,recomendacion,accion,"
        "cargo_codigo,cargo_denominacion,unidad,fecha_objetivo,"
        "porcentaje,estado_accion,vencida"
    )
    assert lineas[0] == cabecera_esperada

    # Verificar auditoría GOV_FINDINGS_EXPORTED de company_a.
    with mundo.factory() as db:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_FINDINGS_EXPORTED",
                AuditEvent.company_id == mundo.company_a,
            )
        )
        assert evento is not None
        assert evento.entity_type == "GovernmentFinding"
