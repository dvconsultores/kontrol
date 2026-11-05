import os
import threading

import pytest

from tests.test_gov_tre01_cuentas import (
    crear_banco,
    cuenta_lista,
    cuenta_vigente,
    cuerpo_cuenta,
    eventos,
    numero_de,
    segundo_cargo,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera con bloqueo de fila se mide en PostgreSQL",
)


def test_cc01_dos_activaciones(mundo, gobierno, siembra):
    cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
    url = f"/api/v1/gobierno/tesoreria/cuentas/{cuenta['id']}/activar"
    version = cuenta["version"]
    headers = {**mundo.como("ua", mundo.company_a), "If-Match": str(version)}
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def activar_hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=headers)

    hilos = [
        threading.Thread(target=activar_hilo, args=("h1",)),
        threading.Thread(target=activar_hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [200, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] in (
        "GOV_BANK_ACCOUNT_STALE",
        "GOV_BANK_ACCOUNT_INVALID_STATE",
    )

    eventos_activacion = eventos(mundo, "GOV_BANK_ACCOUNT_ACTIVATED", cuenta["id"])
    assert len(eventos_activacion) == 1

    detalle = mundo.get(
        f"/gobierno/tesoreria/cuentas/{cuenta['id']}",
        usuario="ua",
        empresa=mundo.company_a,
    ).json()
    historia_activada = [h for h in detalle["historia"] if h["tipo"] == "ACTIVADA"]
    assert len(historia_activada) == 1


def test_cc02_misma_cuenta_dos_veces(mundo, gobierno):
    banco = crear_banco(mundo)
    cuerpo = cuerpo_cuenta(banco)
    url = "/api/v1/gobierno/tesoreria/cuentas"
    headers = mundo.como("ua", mundo.company_a)
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def crear_hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=headers, json=cuerpo)

    hilos = [
        threading.Thread(target=crear_hilo, args=("h1",)),
        threading.Thread(target=crear_hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [201, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] in ("GOV_BANK_ACCOUNT_DUPLICATE", "GOV_BANK_ACCOUNT_CONFLICT")


def test_cc03_dos_altas_mismo_cargo(mundo, gobierno, siembra):
    cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
    cargo2 = segundo_cargo(mundo, siembra["cargo_vigente"])
    url = f"/api/v1/gobierno/tesoreria/cuentas/{cuenta['id']}/autorizados"
    cuerpo = {
        "cargo_id": cargo2,
        "acto_id": cuenta["acto"]["id"],
        "vigente_desde": cuenta["vigente_desde"],
    }
    headers = {
        **mundo.como("ua", mundo.company_a),
        "If-Match": str(cuenta["version"]),
    }
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def autorizar_hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=headers, json=cuerpo)

    hilos = [
        threading.Thread(target=autorizar_hilo, args=("h1",)),
        threading.Thread(target=autorizar_hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [201, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] in (
        "GOV_BANK_ACCOUNT_STALE",
        "GOV_BANK_AUTHORIZATION_DUPLICATE",
    )

    detalle = mundo.get(
        f"/gobierno/tesoreria/cuentas/{cuenta['id']}",
        usuario="ua",
        empresa=mundo.company_a,
    ).json()
    autorizados_vigentes = [a for a in detalle["autorizados"] if a["en_vigor"]]
    assert len([a for a in autorizados_vigentes if a["cargo_id"] == cargo2]) == 1


def test_cc04_inactivar_contra_autorizar(mundo, gobierno, siembra):
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    cargo2 = segundo_cargo(mundo, siembra["cargo_vigente"])
    cuenta_id = cuenta["id"]
    version = cuenta["version"]
    headers_inactivar = {
        **mundo.como("ua", mundo.company_a),
        "If-Match": str(version),
    }
    headers_autorizar = {
        **mundo.como("ua", mundo.company_a),
        "If-Match": str(version),
    }
    cuerpo_inactivar = {"motivo": "Motivo de inactivación con longitud suficiente"}
    cuerpo_autorizar = {
        "cargo_id": cargo2,
        "acto_id": cuenta["acto"]["id"],
        "vigente_desde": cuenta["vigente_desde"],
    }
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def inactivar_hilo():
        barrera.wait()
        resultados["inactivar"] = mundo.client.post(
            f"/api/v1/gobierno/tesoreria/cuentas/{cuenta_id}/inactivar",
            headers=headers_inactivar,
            json=cuerpo_inactivar,
        )

    def autorizar_hilo():
        barrera.wait()
        resultados["autorizar"] = mundo.client.post(
            f"/api/v1/gobierno/tesoreria/cuentas/{cuenta_id}/autorizados",
            headers=headers_autorizar,
            json=cuerpo_autorizar,
        )

    hilos = [
        threading.Thread(target=inactivar_hilo),
        threading.Thread(target=autorizar_hilo),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    assert resultados["inactivar"].status_code in (200, 409)
    assert resultados["autorizar"].status_code in (201, 409)
    assert sorted(r.status_code == 409 for r in resultados.values()) == [False, True]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] == "GOV_BANK_ACCOUNT_STALE"

    detalle = mundo.get(
        f"/gobierno/tesoreria/cuentas/{cuenta_id}",
        usuario="ua",
        empresa=mundo.company_a,
    ).json()

    ganador = next(nombre for nombre, r in resultados.items() if r.status_code != 409)
    if ganador == "inactivar":
        assert detalle["estado"] == "INACTIVA"
        assert not any(a["en_vigor"] and a["cargo_id"] == cargo2 for a in detalle["autorizados"])
    else:
        assert detalle["estado"] == "VIGENTE"
        assert any(a["en_vigor"] and a["cargo_id"] == cargo2 for a in detalle["autorizados"])


def test_cc05_dos_ceses_misma_autorizacion(mundo, gobierno, siembra):
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    autorizacion = next(a for a in cuenta["autorizados"] if a["en_vigor"])
    url = (
        f"/api/v1/gobierno/tesoreria/cuentas/{cuenta['id']}"
        f"/autorizados/{autorizacion['id']}/fin"
    )
    headers = {
        **mundo.como("ua", mundo.company_a),
        "If-Match": str(cuenta["version"]),
    }
    cuerpo = {
        "acto_id": cuenta["acto"]["id"],
        "vigente_hasta": cuenta["vigente_desde"],
        "motivo": "Motivo de fin de autorización con longitud suficiente",
    }
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def fin_hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=headers, json=cuerpo)

    hilos = [
        threading.Thread(target=fin_hilo, args=("h1",)),
        threading.Thread(target=fin_hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [200, 409]

    detalle = mundo.get(
        f"/gobierno/tesoreria/cuentas/{cuenta['id']}",
        usuario="ua",
        empresa=mundo.company_a,
    ).json()
    historia_fin = [h for h in detalle["historia"] if h["tipo"] == "AUTORIZADO_FIN"]
    assert len(historia_fin) == 1


def test_cc06_codigo_en_carrera(mundo, gobierno):
    banco = crear_banco(mundo)
    url = "/api/v1/gobierno/tesoreria/cuentas"
    headers = mundo.como("ua", mundo.company_a)
    cuerpo1 = cuerpo_cuenta(banco, numero=numero_de(banco))
    cuerpo2 = cuerpo_cuenta(banco, numero=numero_de(banco))
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def crear_hilo(nombre, cuerpo):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=headers, json=cuerpo)

    hilos = [
        threading.Thread(target=crear_hilo, args=("h1", cuerpo1)),
        threading.Thread(target=crear_hilo, args=("h2", cuerpo2)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert all(codigo in (201, 409) for codigo in codigos)

    for r in resultados.values():
        if r.status_code == 409:
            assert r.json()["code"] in (
                "GOV_BANK_ACCOUNT_DUPLICATE",
                "GOV_BANK_ACCOUNT_CONFLICT",
            )

    cuentas_creadas = [r.json()["codigo"] for r in resultados.values() if r.status_code == 201]
    assert len(cuentas_creadas) == len(set(cuentas_creadas))


def test_cc07_repeticion(mundo, gobierno, siembra):
    def escenario():
        cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
        url = f"/api/v1/gobierno/tesoreria/cuentas/{cuenta['id']}/activar"
        version = cuenta["version"]
        headers = {**mundo.como("ua", mundo.company_a), "If-Match": str(version)}
        resultados = {}
        barrera = threading.Barrier(2, timeout=30)

        def activar_hilo(nombre):
            barrera.wait()
            resultados[nombre] = mundo.client.post(url, headers=headers)

        hilos = [
            threading.Thread(target=activar_hilo, args=("h1",)),
            threading.Thread(target=activar_hilo, args=("h2",)),
        ]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)
            assert not h.is_alive()

        codigos = sorted(r.status_code for r in resultados.values())
        assert codigos == [200, 409]

        error_409 = next(r for r in resultados.values() if r.status_code == 409)
        assert error_409.json()["code"] in (
            "GOV_BANK_ACCOUNT_STALE",
            "GOV_BANK_ACCOUNT_INVALID_STATE",
        )

        eventos_activacion = eventos(mundo, "GOV_BANK_ACCOUNT_ACTIVATED", cuenta["id"])
        assert len(eventos_activacion) == 1

        detalle = mundo.get(
            f"/gobierno/tesoreria/cuentas/{cuenta['id']}",
            usuario="ua",
            empresa=mundo.company_a,
        ).json()
        historia_activada = [h for h in detalle["historia"] if h["tipo"] == "ACTIVADA"]
        assert len(historia_activada) == 1

    for _ in range(5):
        escenario()
