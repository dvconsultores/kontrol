import os
import threading
from datetime import timedelta

import pytest

from tests.test_gov_ctl01_reglas import HOY, cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import H, _cuerpo_independiente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera con bloqueo de fila se mide en PostgreSQL",
)


def test_sc01_concurrencia_mismo_usuario_mismo_hallazgo(mundo, gobierno, siembra):
    """SC-01: dos peticiones concurrentes sobre el mismo hallazgo producen un 201 y un 409 con código de conflicto."""
    regla = regla_vigente(
        mundo,
        accion_a="CTL06_ACCION",
        accion_b="CTL06_RECOMENDAR",
        bidireccional=True,
    )

    try:
        cabeceras_uab = mundo.como("uab", mundo.company_a)
        r_hallazgo = mundo.client.post(
            f"/api/v1{H}",
            headers=cabeceras_uab,
            json=_cuerpo_independiente(),
        )
        assert r_hallazgo.status_code == 201, r_hallazgo.text
        detalle_hallazgo = r_hallazgo.json()
        id_hallazgo = detalle_hallazgo["id"]
        version_actual = detalle_hallazgo["version"]

        r_recomendacion = mundo.client.post(
            f"/api/v1{H}/{id_hallazgo}/recomendaciones",
            headers={**cabeceras_uab, "If-Match": str(version_actual)},
            json={"texto": "Primera recomendación de uab."},
        )
        assert r_recomendacion.status_code == 201, r_recomendacion.text
        detalle_con_recomendacion = r_recomendacion.json()
        version_actual = detalle_con_recomendacion["version"]
        recomendacion_id = detalle_con_recomendacion["recomendaciones"][0]["id"]

        cabeceras_ua = mundo.como("ua", mundo.company_a)

        respuestas = {}
        barrera = threading.Barrier(2, timeout=30)

        def recomendar():
            barrera.wait()
            respuestas["recomendar"] = mundo.client.post(
                f"/api/v1{H}/{id_hallazgo}/recomendaciones",
                headers={**cabeceras_ua, "If-Match": str(version_actual)},
                json={"texto": "Segunda recomendación en carrera."},
            )

        def accion():
            barrera.wait()
            respuestas["accion"] = mundo.client.post(
                f"/api/v1{H}/{id_hallazgo}/acciones",
                headers={**cabeceras_ua, "If-Match": str(version_actual)},
                json={
                    "recomendacion_id": recomendacion_id,
                    "descripcion": "Acción correctiva en carrera.",
                    "cargo_id": siembra["cargo_vigente"],
                    "fecha_objetivo": (HOY + timedelta(days=30)).isoformat(),
                },
            )

        hilos = [
            threading.Thread(target=recomendar),
            threading.Thread(target=accion),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(60)
        assert not any(hilo.is_alive() for hilo in hilos)

        estados = [respuestas["recomendar"].status_code, respuestas["accion"].status_code]
        assert sorted(estados) == [201, 409], respuestas

        respuesta_conflicto = (
            respuestas["recomendar"]
            if respuestas["recomendar"].status_code == 409
            else respuestas["accion"]
        )
        assert respuesta_conflicto.json().get("code") in {
            "GOV_FINDING_STALE",
            "GOV_SOD_CONFLICT",
        }, respuestas

        r_detalle = mundo.client.get(
            f"/api/v1{H}/{id_hallazgo}",
            headers=cabeceras_uab,
        )
        assert r_detalle.status_code == 200, r_detalle.text
        detalle_final = r_detalle.json()
        num_recomendaciones = len(detalle_final["recomendaciones"])
        num_acciones = len(detalle_final.get("acciones", []))
        assert (num_recomendaciones, num_acciones) in {(2, 0), (1, 1)}, detalle_final

        eventos_hallazgo = eventos(mundo, "GOV_FINDING_RECOMMENDATION_ADDED", id_hallazgo)
        eventos_hallazgo += eventos(
            mundo, "GOV_CORRECTIVE_ACTION_ADDED", id_hallazgo
        )
        assert len(eventos_hallazgo) == 2, eventos_hallazgo
    finally:
        cerrar_regla(mundo, regla)


def test_sc02_secuencial_bloqueo_segregacion(mundo, gobierno, siembra):
    """SC-02: tras registrar una acción, una recomendación secuencial del mismo usuario se bloquea con GOV_SOD_CONFLICT."""
    regla = regla_vigente(
        mundo,
        accion_a="CTL06_ACCION",
        accion_b="CTL06_RECOMENDAR",
        bidireccional=True,
    )

    try:
        cabeceras_uab = mundo.como("uab", mundo.company_a)
        r_hallazgo = mundo.client.post(
            f"/api/v1{H}",
            headers=cabeceras_uab,
            json=_cuerpo_independiente(),
        )
        assert r_hallazgo.status_code == 201, r_hallazgo.text
        detalle_hallazgo = r_hallazgo.json()
        id_hallazgo = detalle_hallazgo["id"]
        version_actual = detalle_hallazgo["version"]

        r_recomendacion = mundo.client.post(
            f"/api/v1{H}/{id_hallazgo}/recomendaciones",
            headers={**cabeceras_uab, "If-Match": str(version_actual)},
            json={"texto": "Primera recomendación de uab."},
        )
        assert r_recomendacion.status_code == 201, r_recomendacion.text
        detalle_con_recomendacion = r_recomendacion.json()
        version_actual = detalle_con_recomendacion["version"]
        recomendacion_id = detalle_con_recomendacion["recomendaciones"][0]["id"]

        cabeceras_ua = mundo.como("ua", mundo.company_a)

        r_accion = mundo.client.post(
            f"/api/v1{H}/{id_hallazgo}/acciones",
            headers={**cabeceras_ua, "If-Match": str(version_actual)},
            json={
                "recomendacion_id": recomendacion_id,
                "descripcion": "Acción correctiva de ua.",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": (HOY + timedelta(days=30)).isoformat(),
            },
        )
        assert r_accion.status_code == 201, r_accion.text
        version_actual = r_accion.json()["version"]

        r_segunda_recomendacion = mundo.client.post(
            f"/api/v1{H}/{id_hallazgo}/recomendaciones",
            headers={**cabeceras_ua, "If-Match": str(version_actual)},
            json={"texto": "Segunda recomendación de ua, bloqueada por segregación."},
        )
        assert r_segunda_recomendacion.status_code == 409, (
            r_segunda_recomendacion.status_code,
            r_segunda_recomendacion.text,
        )
        assert r_segunda_recomendacion.json()["code"] == "GOV_SOD_CONFLICT", (
            r_segunda_recomendacion.text
        )
    finally:
        cerrar_regla(mundo, regla)
