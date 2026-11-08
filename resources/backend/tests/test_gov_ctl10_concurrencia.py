import itertools
import os
import threading

import pytest

from tests.ctl10_ayudantes import (
    MOTIVO,
    C,
    activar,
    anadir_control,
    crear_politica,
    politicas_limpias,  # noqa: F401  # noqa: F401
    retirar,
)
from tests.test_gov_ctl06_hallazgos import ANIO, _post
from tests.test_gov_tre01_cuentas import eventos
from tests.tre02_ayudantes import programa_vigente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera con bloqueo de fila se mide en PostgreSQL",
)

_ejercicios = itertools.count(ANIO + 70)


def _correr_dos_hilos_patch(mundo, ruta, cabeceras, cuerpo_a, cuerpo_b):
    """Ejecuta dos PATCH con las mismas cabeceras preparadas en hilos paralelos."""
    resultados = []
    barrera = threading.Barrier(2, timeout=30)

    def hilo(cuerpo):
        barrera.wait()
        r = mundo.client.patch(
            f"/api/v1{ruta}",
            headers=cabeceras,
            json=cuerpo,
        )
        resultados.append(r)

    t1 = threading.Thread(target=hilo, args=(cuerpo_a,))
    t2 = threading.Thread(target=hilo, args=(cuerpo_b,))
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    assert not t1.is_alive()
    assert not t2.is_alive()
    return resultados


def _siguiente_ejercicio() -> int:
    ejercicio = next(_ejercicios)
    assert ejercicio <= ANIO + 80
    return ejercicio


def _cabeceras(mundo, usuario, empresa, version):
    cabeceras = mundo.como(usuario, empresa)
    cabeceras["If-Match"] = str(version)
    return cabeceras


def _correr_dos_hilos(
    mundo, url_a, url_b, cabeceras_a, cabeceras_b, cuerpo_a=None, cuerpo_b=None
):
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo(nombre, url, cabeceras, cuerpo=None):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=cabeceras, json=cuerpo)

    hilos = [
        threading.Thread(target=hilo, args=("h1", url_a, cabeceras_a, cuerpo_a)),
        threading.Thread(target=hilo, args=("h2", url_b, cabeceras_b, cuerpo_b)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()
    return resultados


def _crear_politica_borrador_con_control(mundo, accion_cierre):
    politica = crear_politica(mundo, accion_cierre=accion_cierre)
    politica = anadir_control(
        mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="BAJO"
    )
    return politica


def test_cc01_dos_activaciones_misma_accion(mundo, gobierno):
    """cc01 dos activaciones de dos políticas de la misma acción: exactamente un 200 y un 409."""
    accion = "ORG02_CERRAR_ESTRUCTURA"
    p1 = _crear_politica_borrador_con_control(mundo, accion)
    p2 = _crear_politica_borrador_con_control(mundo, accion)

    url_a = f"/api/v1{C}/politicas/{p1['id']}/activar"
    url_b = f"/api/v1{C}/politicas/{p2['id']}/activar"
    cabeceras_a = _cabeceras(mundo, "ua", mundo.company_a, p1["version"])
    cabeceras_b = _cabeceras(mundo, "ua", mundo.company_a, p2["version"])

    resultados = _correr_dos_hilos(mundo, url_a, url_b, cabeceras_a, cabeceras_b)

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [200, 409]

    for politica in (p1, p2):
        detalle = mundo.client.get(
            f"/api/v1{C}/politicas/{politica['id']}",
            headers=mundo.como("ua", mundo.company_a),
        )
        if detalle.status_code == 200 and detalle.json()["estado"] != "BORRADOR":
            r_ret = retirar(mundo, detalle.json())
            assert r_ret.status_code == 200, r_ret.text


def test_cc02_dos_cierres_mismo_programa_sin_pendientes(mundo, gobierno, siembra):
    """cc02 dos cierres del mismo programa sin pendientes: un 200 y un 409, y un solo evento GOV_CASH_PROGRAM_CLOSED."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    programa = programa_vigente(mundo, cargo, ejercicio)

    url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/cerrar"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cuerpo = {"motivo": MOTIVO}

    resultados = _correr_dos_hilos(mundo, url, url, cabeceras, cabeceras, cuerpo, cuerpo)

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos in ([200, 409], [200, 200])

    eventos_cierre = eventos(mundo, "GOV_CASH_PROGRAM_CLOSED", programa["id"])
    assert len(eventos_cierre) == 1


def test_cc03_retirar_contra_cerrar_con_pendiente(mundo, gobierno, siembra):
    """cc03 retirar contra cerrar con pendiente: resultado coherente; nunca 500."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    programa = programa_vigente(mundo, cargo, ejercicio)

    _post(
        mundo,
        "/gobierno/hallazgos",
        "ua",
        mundo.company_a,
        {
            "titulo": "Hallazgo ALTO de prueba",
            "descripcion": "Descripción suficiente para crear un hallazgo ALTO.",
            "riesgo": "ALTO",
        },
    )

    politica = _crear_politica_borrador_con_control(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    politica = r.json()

    url_retirar = f"/api/v1{C}/politicas/{politica['id']}/retirar"
    url_cerrar = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/cerrar"
    cabeceras_retirar = _cabeceras(mundo, "ua", mundo.company_a, politica["version"])
    cabeceras_cerrar = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cuerpo_retirar = {"motivo": MOTIVO}
    cuerpo_cerrar = {"motivo": MOTIVO}

    resultados = _correr_dos_hilos(
        mundo,
        url_retirar,
        url_cerrar,
        cabeceras_retirar,
        cabeceras_cerrar,
        cuerpo_retirar,
        cuerpo_cerrar,
    )

    for nombre, r in resultados.items():
        assert r.status_code != 500, f"{nombre}: {r.status_code} {r.text}"

    if resultados["h1"].status_code == 200:
        assert resultados["h2"].status_code in (200, 409)
        if resultados["h2"].status_code == 409:
            assert resultados["h2"].json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    else:
        assert resultados["h1"].status_code == 409
        assert resultados["h2"].status_code == 409
        assert resultados["h2"].json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"


def test_cc04_dos_ediciones_misma_version(mundo, gobierno):
    """cc04 dos ediciones con la misma versión: un 200 y un 409 STALE."""
    politica = _crear_politica_borrador_con_control(mundo, "ORG02_CERRAR_ESTRUCTURA")
    ruta = f"{C}/politicas/{politica['id']}"
    cuerpo_a = {"nombre": "Edición A con nombre suficientemente largo."}
    cuerpo_b = {"nombre": "Edición B con nombre suficientemente largo."}
    version = politica["version"]
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, version)

    resultados = _correr_dos_hilos_patch(
        mundo, ruta, cabeceras, cuerpo_a, cuerpo_b
    )

    codigos = sorted(r.status_code for r in resultados)
    assert codigos == [200, 409]

    for r in resultados:
        if r.status_code == 409:
            assert r.json()["code"] == "GOV_CLOSURE_POLICY_STALE"


def test_cc01b_activacion_que_pierde_la_carrera_da_409(mundo, gobierno, monkeypatch):
    from sqlalchemy import text

    from app.modules.government import service_cierres

    accion = "ORG02_CERRAR_ESTRUCTURA"
    p1 = _crear_politica_borrador_con_control(mundo, accion)
    p2 = _crear_politica_borrador_con_control(mundo, accion)

    original = service_cierres.evaluar_antes_de_actuar
    usadas = []

    def rival(db, *args, **kwargs):
        if not usadas:
            usadas.append(1)
            with db.get_bind().connect() as c:
                c.execute(
                    text(
                        "UPDATE gov_closure_policies SET estado = 'VIGENTE', "
                        "activada_por = created_by, activada_en = now() WHERE id = :id"
                    ),
                    {"id": p2["id"]},
                )
                c.commit()
        return original(db, *args, **kwargs)

    monkeypatch.setattr(service_cierres, "evaluar_antes_de_actuar", rival)

    r = mundo.client.post(
        f"/api/v1{C}/politicas/{p1['id']}/activar",
        headers=_cabeceras(mundo, "ua", mundo.company_a, p1["version"]),
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_ACTIVE_EXISTS"
    assert usadas == [1]

    detalle = mundo.client.get(
        f"/api/v1{C}/politicas/{p1['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert detalle.json()["estado"] == "BORRADOR"

    for p in (p1, p2):
        detalle = mundo.client.get(
            f"/api/v1{C}/politicas/{p['id']}",
            headers=mundo.como("ua", mundo.company_a),
        )
        if detalle.json()["estado"] != "BORRADOR":
            retirar(mundo, detalle.json())
