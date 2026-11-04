"""Suite de backend CTL-06 (GOV-CTL-008): inmutable."""
import os

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.modules.government.models import GovernmentFindingEvent
from tests.test_gov_ctl06_hallazgos import (
    H,
    _cuerpo_muestra,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_gh6_21_inmutabilidad_postgresql(mundo, gobierno, siembra):
    """GH6-21: UPDATE/DELETE sobre tablas de CTL-06 en PostgreSQL → DBAPIError."""
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")

    detalle = _hallazgo_en_remediacion(mundo, siembra)
    accion_id = detalle["acciones"][0]["id"]

    r = _post(
        mundo,
        f"{H}/{detalle['id']}/acciones/{accion_id}/avances",
        "ua",
        mundo.company_a,
        {"nota": "Avance para probar la inmutabilidad.", "porcentaje": 50},
        version=detalle["version"],
    )
    assert r.status_code == 201, r.text
    detalle = r.json()

    recomendacion_id = detalle["recomendaciones"][0]["id"]
    avance_id = detalle["acciones"][0]["avances"][0]["id"]
    historia_id = detalle["historia"][0]["id"]
    hallazgo_id = detalle["id"]

    sentencias = [
        (
            "UPDATE gov_finding_recommendations SET texto = 'modificado' WHERE id = :id",
            recomendacion_id,
        ),
        (
            "UPDATE gov_corrective_action_progress SET nota = 'modificada' WHERE id = :id",
            avance_id,
        ),
        (
            "UPDATE gov_finding_history SET tipo = 'PLAN' WHERE id = :id",
            historia_id,
        ),
        ("DELETE FROM gov_findings WHERE id = :id", hallazgo_id),
    ]

    for sentencia, id_registro in sentencias:
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(text(sentencia), {"id": id_registro})
                db.commit()
            db.rollback()


def test_gh6_30_partidas_generan_dos_eventos(mundo, gobierno, siembra):
    """GH6-30: alta MUESTRA con 2 partidas → 2 GovernmentFindingEvent del hallazgo en company_a."""
    muestra_id = siembra["muestra_a"]
    partidas = siembra["partidas_a"]

    cuerpo = _cuerpo_muestra(muestra_id, partidas)
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    hallazgo_id = response.json()["id"]

    with mundo.factory() as db:
        total = db.scalar(
            select(func.count()).select_from(GovernmentFindingEvent).where(
                GovernmentFindingEvent.finding_id == hallazgo_id,
                GovernmentFindingEvent.company_id == mundo.company_a,
            )
        )
        assert total == 2
