from datetime import date

import pytest

from tests.ctl10_ayudantes import (
    MOTIVO,
    C,
    activar,
    anadir_control,
    crear_politica,
    politicas_limpias,  # noqa: F401  # noqa: F401
)
from tests.test_gov_ctl06_hallazgos import (
    _crear_usuario_con_permisos,
    _cuerpo_independiente,
    _post,
)
from tests.tre02_ayudantes import accion, programa_vigente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

ANIO = date.today().year


@pytest.fixture
def bl_sin_permiso(mundo, gobierno):
    _crear_usuario_con_permisos(
        mundo, "bl_sin_permiso", [("gobierno_auditoria", "view")], mundo.company_a
    )
    return "bl_sin_permiso"


def _provocar_bloqueo(mundo, siembra, ejercicio):
    politica = anadir_control(
        mundo,
        crear_politica(mundo, "TRE02_CERRAR_PROGRAMA"),
        "HALLAZGOS_ABIERTOS",
        "ALTO",
    )
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    r = _post(mundo, "/gobierno/hallazgos", "ua", mundo.company_a, _cuerpo_independiente(riesgo="ALTO"))
    assert r.status_code == 201, r.text
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
    return politica, r.json()


def test_bl01_bloqueo_listado(mundo, gobierno, siembra):
    politica, bloqueo = _provocar_bloqueo(mundo, siembra, ANIO + 40)
    r = mundo.client.get(f"/api/v1{C}/bloqueos", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert len(cuerpo["items"]) >= 1
    item = next(i for i in cuerpo["items"] if i["objeto_codigo"] == bloqueo["details"]["objeto_codigo"])
    assert item["politica_codigo"] == politica["codigo"]
    assert item["accion_cierre"] == "TRE02_CERRAR_PROGRAMA"
    assert item["total"] > 0
    assert "usuario" in item
    assert "instante" in item


def test_bl02_filtro_accion_y_fechas(mundo, gobierno, siembra):
    _provocar_bloqueo(mundo, siembra, ANIO + 41)
    r = mundo.client.get(
        f"/api/v1{C}/bloqueos?accion_cierre=TRE02_CERRAR_PROGRAMA",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) >= 1

    r = mundo.client.get(
        f"/api/v1{C}/bloqueos?accion_cierre=ORG02_CERRAR_ESTRUCTURA",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 0

    r = mundo.client.get(
        f"/api/v1{C}/bloqueos?desde=2030-01-01&hasta=2030-01-31",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 0


def test_bl03_paginacion(mundo, gobierno, siembra):
    _provocar_bloqueo(mundo, siembra, ANIO + 42)
    r = mundo.client.get(
        f"/api/v1{C}/bloqueos?pagina=1&tamano=1",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_bl04_otra_empresa_no_lo_ve(mundo, gobierno, siembra):
    _provocar_bloqueo(mundo, siembra, ANIO + 43)
    r = mundo.client.get(f"/api/v1{C}/bloqueos", headers=mundo.como("ub", mundo.company_b))
    assert r.status_code == 200, r.text
    assert all(
        item["objeto_codigo"] != siembra["objeto_codigo"]
        for item in r.json()["items"]
    )


def test_bl05_sin_permiso_403(mundo, gobierno, bl_sin_permiso):
    r = mundo.client.get(
        f"/api/v1{C}/bloqueos",
        headers=mundo.como(bl_sin_permiso, mundo.company_a),
    )
    assert r.status_code == 403, r.text


def test_bl06_cierre_permitido_no_aparece(mundo, gobierno, siembra):
    politica = crear_politica(mundo, "TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "ACTOS_SIN_EFICACIA")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ANIO + 44)
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text
    r = mundo.client.get(f"/api/v1{C}/bloqueos", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, r.text
    assert all(i["objeto_codigo"] != programa["codigo"] for i in r.json()["items"])


def test_bl07_item_trae_politica_id_y_nombre_de_usuario(mundo, gobierno, siembra):
    _provocar_bloqueo(mundo, siembra, ANIO + 45)
    cabeceras = mundo.como("ua", mundo.company_a)
    r = mundo.client.get(f"/api/v1{C}/bloqueos?tamano=1", headers=cabeceras)
    assert r.status_code == 200
    item = r.json()["items"][0]
    r = mundo.client.get(
        f"/api/v1{C}/politicas?estado=VIGENTE&accion_cierre=TRE02_CERRAR_PROGRAMA",
        headers=cabeceras,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert item["politica_id"] == items[0]["id"]
    assert item["usuario"] == "ua"
