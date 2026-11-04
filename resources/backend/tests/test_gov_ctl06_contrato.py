"""Suite de backend CTL-06 (GOV-CTL-008): contrato."""
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.shared.audit_catalog import catalog
from tests.test_gov_ctl06_hallazgos import (
    H,
    _cuerpo_independiente,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_26_concurrencia_recomendaciones(mundo, gobierno, siembra):
    """GH6-26: dos POST recomendaciones con el mismo If-Match → uno 201 y el otro 409 GOV_FINDING_STALE."""
    cuerpo = _cuerpo_independiente()
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    hallazgo_id = response.json()["id"]

    respuesta_1 = _post(
        mundo,
        f"{H}/{hallazgo_id}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "Recomendación concurrente uno."},
        version=1,
    )
    respuesta_2 = _post(
        mundo,
        f"{H}/{hallazgo_id}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "Recomendación concurrente dos."},
        version=1,
    )

    codigos = sorted([respuesta_1.status_code, respuesta_2.status_code])
    assert codigos == [201, 409]
    for response in (respuesta_1, respuesta_2):
        assert response.status_code in (201, 409), response.text
        if response.status_code == 409:
            assert response.json()["code"] == "GOV_FINDING_STALE"


def test_gh6_27_metodos_no_permitidos(mundo, gobierno, siembra):
    """GH6-27: PATCH, PUT y DELETE sobre H/{id} → 405."""
    detalle = _hallazgo_en_remediacion(mundo, siembra)
    hallazgo_id = detalle["id"]
    headers = mundo.como("ua", mundo.company_a)

    response = mundo.client.patch(f"/api/v1{H}/{hallazgo_id}", headers=headers, json={})
    assert response.status_code == 405, response.text

    response = mundo.client.put(f"/api/v1{H}/{hallazgo_id}", headers=headers, json={})
    assert response.status_code == 405, response.text

    response = mundo.client.delete(f"/api/v1{H}/{hallazgo_id}", headers=headers)
    assert response.status_code == 405, response.text


def test_gh6_28_catalogo_auditoria(mundo, gobierno, siembra):
    """GH6-28: catálogo de las 10 acciones de GovernmentFinding sin red."""
    acciones = [
        "GOV_FINDING_CREATED",
        "GOV_FINDING_RECOMMENDATION_ADDED",
        "GOV_CORRECTIVE_ACTION_ADDED",
        "GOV_FINDING_PLAN_REGISTERED",
        "GOV_FINDING_REMEDIATION_STARTED",
        "GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED",
        "GOV_FINDING_SUBMITTED",
        "GOV_FINDING_VERIFIED",
        "GOV_FINDING_RETURNED",
        "GOV_FINDINGS_EXPORTED",
    ]

    catalogo = catalog()
    for accion in acciones:
        spec = catalogo[(accion, "GovernmentFinding")]
        assert spec.owner_module == "government"
        assert spec.owner_spec == "gov-ctl-06"


def test_gh6_29_ctl04_filtros_y_evento(mundo, gobierno, siembra):
    """GH6-29: CTL-04 incluye CTL-06; el evento GOV_FINDING_CREATED trae ruta y capacidad del objeto."""
    response = mundo.client.get(
        "/api/v1/gobierno/auditoria/filtros",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert response.status_code == 200, response.text
    procesos = response.json()["procesos"]
    assert any(proceso["codigo"] == "CTL-06" for proceso in procesos)

    cuerpo = _cuerpo_independiente()
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    hallazgo_id = response.json()["id"]

    with mundo.factory() as db:
        evento_id = db.scalar(
            select(AuditEvent.id).where(
                AuditEvent.action == "GOV_FINDING_CREATED",
                AuditEvent.entity_type == "GovernmentFinding",
                AuditEvent.entity_id == str(hallazgo_id),
                AuditEvent.company_id == mundo.company_a,
            )
        )
        assert evento_id is not None

    response = mundo.client.get(
        f"/api/v1/gobierno/auditoria/eventos/{evento_id}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert response.status_code == 200, response.text
    detalle = response.json()
    assert detalle["objeto"]["ruta"] == f"/gobierno/hallazgos/{hallazgo_id}"
    assert detalle["objeto"]["capacidad"] == "gobierno_hallazgos:view"
