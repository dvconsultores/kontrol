import itertools

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.shared.clock import hoy_de_negocio
from tests.ctl10_ayudantes import (
    C,
    activar,
    anadir_control,
    crear_politica,
    politicas_limpias,  # noqa: F401  # noqa: F401
    post_politica,
    retirar,
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _cuerpo_independiente, _post
from tests.tre02_ayudantes import accion, delete_con_version, patch_con_version, programa_vigente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

ANIO = hoy_de_negocio().year
_futuros = itertools.count(ANIO + 60)


@pytest.fixture
def sg_solo_view(mundo, gobierno):
    _crear_usuario_con_permisos(
        mundo, "sg_solo_view", [("gobierno_cierre", "view")], mundo.company_a
    )
    return "sg_solo_view"


def _crear_politica_vigente(mundo, accion_cierre="ORG02_CERRAR_ESTRUCTURA"):
    politica = crear_politica(mundo, accion_cierre=accion_cierre)
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="BAJO")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    return r.json()


def test_sg01_usuario_solo_view(mundo, gobierno, sg_solo_view):
    """sg01 usuario solo view: lista y detalle 200; POST, PATCH, DELETE y activar 403."""
    politica = _crear_politica_vigente(mundo)

    r = mundo.client.get(f"/api/v1{C}/politicas", headers=mundo.como("sg_solo_view", mundo.company_a))
    assert r.status_code == 200, r.text
    assert "items" in r.json()

    r = mundo.client.get(
        f"/api/v1{C}/politicas/{politica['id']}", headers=mundo.como("sg_solo_view", mundo.company_a)
    )
    assert r.status_code == 200, r.text

    r = post_politica(mundo, usuario="sg_solo_view")
    assert r.status_code == 403, r.text

    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Cambio no permitido"},
        politica["version"],
        usuario="sg_solo_view",
        empresa=mundo.company_a,
    )
    assert r.status_code == 403, r.text

    r = delete_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}/controles/{politica['controles'][0]['id']}",
        politica["version"],
        usuario="sg_solo_view",
        empresa=mundo.company_a,
    )
    assert r.status_code == 403, r.text

    r = activar(mundo, politica, usuario="sg_solo_view")
    assert r.status_code == 403, r.text

    r = retirar(mundo, politica, usuario="sg_solo_view")
    assert r.status_code == 403, r.text


def test_sg02_admin_tecnico_sin_funcional_completo(mundo, gobierno):
    """sg02 ADMIN tecnico sin FUNCIONAL_COMPLETO no ve /gobierno/cierres/politicas: 403."""
    _crear_usuario_con_permisos(
        mundo, "admin_tecnico", [("organization", "view")], mundo.company_a
    )
    r = mundo.client.get(
        f"/api/v1{C}/politicas", headers=mundo.como("admin_tecnico", mundo.company_a)
    )
    assert r.status_code == 403, r.text


def test_sg03_empresa_ajena(mundo, gobierno):
    """sg03 empresa ajena: GET, PATCH, activar y retirar de una politica de company_a por ub en company_b dan 404, y su lista no la contiene."""
    politica = _crear_politica_vigente(mundo)

    r = mundo.client.get(
        f"/api/v1{C}/politicas/{politica['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r.status_code == 404, r.text

    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Cambio ajeno"},
        politica["version"],
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text

    r = activar(mundo, politica, usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404, r.text

    r = retirar(mundo, politica, usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404, r.text

    r = mundo.client.get(
        f"/api/v1{C}/politicas", headers=mundo.como("ub", mundo.company_b)
    )
    assert r.status_code == 200, r.text
    ids = [p["id"] for p in r.json()["items"]]
    assert politica["id"] not in ids


def test_sg04_uuid_inexistente(mundo, gobierno):
    """sg04 UUID inexistente 404."""
    r = mundo.client.get(
        f"/api/v1{C}/politicas/00000000-0000-0000-0000-000000000000",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 404, r.text


def test_sg05_company_id_en_cuerpo(mundo, gobierno):
    """sg05 company_id en el cuerpo 422."""
    cuerpo = {
        "nombre": "Política con company_id",
        "accion_cierre": "ORG02_CERRAR_ESTRUCTURA",
        "fundamento": "Fundamento de control interno con longitud mayor a diez caracteres.",
        "vigente_desde": "2025-01-01",
        "company_id": str(mundo.company_a),
    }
    r = _post(mundo, f"{C}/politicas", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 422, r.text


def test_sg06_tipo_manipulado_por_sql_otro(mundo, gobierno):
    """sg06 tipo manipulado por SQL a OTRO no es posible (DBAPIError)."""
    politica = _crear_politica_vigente(mundo)
    with pytest.raises(DBAPIError):
        with mundo.factory() as session:
            session.execute(
                text(
                    "UPDATE government_closure_control SET tipo = 'OTRO' WHERE id = :id"
                ),
                {"id": politica["controles"][0]["id"]},
            )


def test_sg07_controles_passed_extra_en_cierre_programa(mundo, gobierno, siembra):
    """sg07 el cliente no puede saltar la guarda: cierre de programa con pendiente enviando cuerpo con controles_passed: true: 422 por campo extra, y sin ese campo 409."""
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)

    politica = anadir_control(
        mundo,
        crear_politica(mundo, accion_cierre="TRE02_CERRAR_PROGRAMA"),
        "HALLAZGOS_ABIERTOS",
        "ALTO",
    )
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text

    r = _post(mundo, "/gobierno/hallazgos", "ua", mundo.company_a, _cuerpo_independiente(riesgo="ALTO"))
    assert r.status_code == 201, r.text

    r = _post(
        mundo,
        f"/gobierno/tesoreria/programas/{programa['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Motivo de cierre válido.", "controles_passed": True},
        version=programa["version"],
    )
    assert r.status_code == 422, r.text

    r = accion(mundo, programa, "cerrar", {"motivo": "Motivo de cierre válido."})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"


def _programa_con_hallazgo_pendiente(mundo, siembra):
    ejercicio = next(_futuros)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    politica = anadir_control(mundo, crear_politica(mundo, "TRE02_CERRAR_PROGRAMA"), "HALLAZGOS_ABIERTOS", "ALTO")
    r = activar(mundo, politica)
    assert r.status_code == 200
    r = _post(mundo, "/gobierno/hallazgos", "ua", mundo.company_a, _cuerpo_independiente(riesgo="ALTO"))
    assert r.status_code == 201
    return programa


def test_sg08_cierre_programa_con_hallazgos_abiertos(mundo, gobierno, siembra):
    programa = _programa_con_hallazgo_pendiente(mundo, siembra)
    r = accion(mundo, programa, "cerrar", {"motivo": "Motivo de cierre válido."})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_MATERIAL_CLOSE_BLOCKED"
