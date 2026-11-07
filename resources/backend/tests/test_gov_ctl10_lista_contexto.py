from datetime import date
from itertools import count

from sqlalchemy import text

from app.shared.clock import hoy_de_negocio
from tests.ctl10_ayudantes import (
    MOTIVO,
    acto_emitido,
    politica_vigente,
    politicas_limpias,  # noqa: F401
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _cuerpo_independiente, _post
from tests.tre02_ayudantes import accion, programa_vigente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

ANIO = hoy_de_negocio().year
_futuros = count(ANIO + 80)
L = "/api/v1/gobierno/hallazgos"


def _hallazgo(mundo, riesgo):
    r = _post(mundo, "/gobierno/hallazgos", "ua", mundo.company_a, _cuerpo_independiente(riesgo=riesgo))
    assert r.status_code == 201
    return r.json()


def _ids(mundo, consulta, usuario="ua", empresa=None):
    empresa = empresa or mundo.company_a
    separador = "&" if "?" in consulta else "?"
    url = f"{L}{consulta}{separador}por_pagina=200"
    r = mundo.client.get(url, headers=mundo.como(usuario, empresa))
    assert r.status_code == 200, r.text
    payload = r.json()
    return {item["id"] for item in payload["items"]}, payload["total"]


def _bloqueo(mundo, siembra):
    programa = programa_vigente(mundo, siembra["cargo_vigente"], next(_futuros))
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409
    payload = r.json()
    assert payload["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    return payload["details"]


def test_lc01_ruta_lista_de_hallazgos_lleva_contexto(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "HALLAZGOS_ABIERTOS", riesgo_minimo="MEDIO")
    _hallazgo(mundo, "ALTO")
    details = _bloqueo(mundo, siembra)
    assert details["controles"][0]["ruta_lista"] == "/gobierno/hallazgos?abiertos=true&riesgo_minimo=MEDIO"


def test_lc02_ruta_lista_de_actos_lleva_contexto(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "ACTOS_SIN_EFICACIA")
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    acto_emitido(mundo, siembra, date(ejercicio, 6, 1))
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409
    details = r.json()["details"]
    assert details["controles"][0]["ruta_lista"] == f"/gobierno/actos?anio={ejercicio}&estado=EMITIDO"


def test_lc03_poblacion_del_filtro(mundo, gobierno, siembra):
    alto = _hallazgo(mundo, "ALTO")
    medio = _hallazgo(mundo, "MEDIO")
    bajo = _hallazgo(mundo, "BAJO")
    alto_cerrado = _hallazgo(mundo, "ALTO")
    with mundo.factory() as db:
        db.execute(text("UPDATE gov_findings SET estado='CERRADO' WHERE id = :i"), {"i": alto_cerrado["id"]})
        db.commit()
    ids, _ = _ids(mundo, "?abiertos=true&riesgo_minimo=MEDIO")
    assert alto["id"] in ids
    assert medio["id"] in ids
    assert bajo["id"] not in ids
    assert alto_cerrado["id"] not in ids


def test_lc04_total_de_la_lista_igual_a_pendientes(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "HALLAZGOS_ABIERTOS", riesgo_minimo="MEDIO")
    _hallazgo(mundo, "ALTO")
    _hallazgo(mundo, "BAJO")
    details = _bloqueo(mundo, siembra)
    _, total = _ids(mundo, "?abiertos=true&riesgo_minimo=MEDIO")
    assert total == details["controles"][0]["pendientes"]


def test_lc05_sin_filtro_la_lista_no_cambia(mundo, gobierno, siembra):
    bajo = _hallazgo(mundo, "BAJO")
    alto_cerrado = _hallazgo(mundo, "ALTO")
    with mundo.factory() as db:
        db.execute(text("UPDATE gov_findings SET estado='CERRADO' WHERE id = :i"), {"i": alto_cerrado["id"]})
        db.commit()
    ids, _ = _ids(mundo, "?")
    assert bajo["id"] in ids
    assert alto_cerrado["id"] in ids


def test_lc06_otra_empresa_no_ve(mundo, gobierno, siembra):
    propio = _hallazgo(mundo, "ALTO")
    ids, _ = _ids(mundo, "?abiertos=true&riesgo_minimo=BAJO", "ub", mundo.company_b)
    assert propio["id"] not in ids


def test_lc07_riesgo_minimo_invalido(mundo, gobierno, siembra):
    r = mundo.client.get(f"{L}?riesgo_minimo=OTRO", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 422, r.text


def test_lc08_exportar_respeta_el_filtro(mundo, gobierno, siembra):
    alto = _hallazgo(mundo, "ALTO")
    bajo = _hallazgo(mundo, "BAJO")
    r = mundo.client.get(f"{L}/exportar?abiertos=true&riesgo_minimo=ALTO", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, r.text
    assert alto["codigo"] in r.text
    assert bajo["codigo"] not in r.text


def test_lc09_sin_permiso_403(mundo, gobierno, siembra):
    _crear_usuario_con_permisos(mundo, "lc_sin", [("gobierno_auditoria", "view")], mundo.company_a)
    r = mundo.client.get(f"{L}?abiertos=true&riesgo_minimo=ALTO", headers=mundo.como("lc_sin", mundo.company_a))
    assert r.status_code == 403, r.text


def test_lc10_mas_de_cinco_pendientes(mundo, gobierno, siembra):
    politica_vigente(mundo, "TRE02_CERRAR_PROGRAMA", "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    for _ in range(6):
        _hallazgo(mundo, "ALTO")
    details = _bloqueo(mundo, siembra)
    control = details["controles"][0]
    assert len(control["muestra"]) == 5
    assert control["pendientes"] >= 6
    assert details["total"] == control["pendientes"]
    _, total = _ids(mundo, "?abiertos=true&riesgo_minimo=ALTO")
    assert total == control["pendientes"]
