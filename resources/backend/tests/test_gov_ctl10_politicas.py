import itertools
import os
from datetime import timedelta

import pytest

from app.shared.clock import hoy_de_negocio
from tests.ctl10_ayudantes import (
    C,
    activar,
    anadir_control,
    crear_politica,
    politica_vigente,
    politicas_limpias,  # noqa: F401
    post_control,
    post_politica,
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post
from tests.test_gov_tre01_cuentas import eventos
from tests.tre02_ayudantes import cerrar_regla, regla_sod_vigente, sin_if_match

HOY = hoy_de_negocio()
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

HOY = hoy_de_negocio()
ANIO = HOY.year
PROGRAMAS = itertools.count(ANIO + 40)

VALIDOS = {
    "nombre": "Política válida",
    "accion_cierre": "ORG02_CERRAR_ESTRUCTURA",
    "fundamento": "Fundamento válido con más de diez caracteres.",
}


def test_pp01_catalogo(mundo, gobierno):
    """PP-01: el catálogo devuelve dos acciones y dos tipos."""
    r = mundo.get(f"{C}/catalogo", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert {a["codigo"] for a in cuerpo["acciones"]} == {
        "ORG02_CERRAR_ESTRUCTURA",
        "TRE02_CERRAR_PROGRAMA",
    }
    assert {t["codigo"] for t in cuerpo["tipos"]} == {
        "HALLAZGOS_ABIERTOS",
        "ACTOS_SIN_EFICACIA",
    }


def test_pp02_alta_politica(mundo, gobierno):
    """PP-02: alta 201 con código PC-001, BORRADOR, versión 1, historia CREADA y auditoría."""
    r = post_politica(mundo)
    assert r.status_code == 201, r.text
    politica = r.json()
    assert politica["codigo"] == "PC-001", politica
    assert politica["estado"] == "BORRADOR", politica
    assert politica["version"] == 1, politica
    assert [h["evento"] for h in politica["historia"]] == ["CREADA"], politica

    audit = eventos(mundo, "GOV_CLOSURE_POLICY_CREATED", politica["id"])
    assert len(audit) == 1, politica


def test_pp03_codigo_correlativo_por_empresa(mundo, gobierno):
    """PP-03: el código correlativo es por empresa; cada empresa lleva su propio consecutivo."""
    politica_a1 = crear_politica(mundo, usuario="ua", empresa=mundo.company_a)
    numero_a1 = int(politica_a1["codigo"].split("-")[-1])

    politica_b1 = crear_politica(mundo, usuario="ub", empresa=mundo.company_b)
    numero_b1 = int(politica_b1["codigo"].split("-")[-1])

    politica_a2 = crear_politica(
        mundo,
        usuario="ua",
        empresa=mundo.company_a,
        nombre="Segunda politica",
    )
    numero_a2 = int(politica_a2["codigo"].split("-")[-1])
    assert numero_a2 == numero_a1 + 1, politica_a2

    politica_b2 = crear_politica(
        mundo,
        usuario="ub",
        empresa=mundo.company_b,
        nombre="Segunda politica",
    )
    numero_b2 = int(politica_b2["codigo"].split("-")[-1])
    assert numero_b2 == numero_b1 + 1, politica_b2


@pytest.mark.parametrize(
    "cambios,campo",
    [
        ({"nombre": "AB"}, "nombre"),
        ({"fundamento": "corto"}, "fundamento"),
        ({"accion_cierre": "ACCION_INVALIDA"}, "accion_cierre"),
        ({"vigente_hasta": (HOY - timedelta(days=1)).isoformat()}, "_"),
    ],
)
def test_pp04_validaciones_422(mundo, gobierno, cambios, campo):
    """PP-04: entradas inválidas devuelven 422 VALIDATION_ERROR con el campo señalado."""
    r = post_politica(mundo, **cambios)
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR", r.text
    assert campo in cuerpo["field_errors"], cuerpo


def test_pp04_campo_extra_company_id_rechazado(mundo, gobierno):
    """PP-04: company_id enviado por el cliente se rechaza con 422 VALIDATION_ERROR."""
    r = _post(
        mundo,
        f"{C}/politicas",
        "ua",
        mundo.company_a,
        {
            "nombre": f"Política extra {os.urandom(4).hex()}",
            "accion_cierre": "ORG02_CERRAR_ESTRUCTURA",
            "fundamento": "Fundamento válido con más de diez caracteres.",
            "vigente_desde": HOY.isoformat(),
            "company_id": mundo.company_b,
        },
    )
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR", cuerpo
    assert "company_id" in cuerpo["field_errors"], cuerpo


def test_pp05_validaciones_de_controles(mundo, gobierno):
    """PP-05: validaciones de controles según el tipo."""
    politica = crear_politica(mundo)

    r = post_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo=None)
    assert r.status_code == 422, r.text

    r = post_control(mundo, politica, "ACTOS_SIN_EFICACIA", riesgo_minimo="ALTO")
    assert r.status_code == 422, r.text

    r = post_control(mundo, politica, "ACTOS_SIN_EFICACIA")
    assert r.status_code == 201, r.text
    politica = r.json()

    r = post_control(
        mundo,
        politica,
        "ACTOS_SIN_EFICACIA",
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID", r.text

    r = post_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    assert r.status_code == 201, r.text
    politica = r.json()

    r = post_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID", r.text


def test_pp05_tipo_fuera_de_catalogo(mundo, gobierno):
    """PP-05: tipo de control fuera de catálogo devuelve 422 VALIDATION_ERROR."""
    politica = crear_politica(mundo)
    r = post_control(mundo, politica, "TIPO_INVALIDO")
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR", cuerpo
    assert "tipo" in cuerpo["field_errors"], cuerpo


def test_pp06_activar_sin_controles(mundo, gobierno):
    """PP-06: activar sin controles devuelve 422 y la política sigue BORRADOR."""
    politica = crear_politica(mundo)
    r = activar(mundo, politica)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID", r.text

    detalle = mundo.get(f"{C}/politicas/{politica['id']}", "ua", mundo.company_a).json()
    assert detalle["estado"] == "BORRADOR", detalle


def test_pp07_activar_politica(mundo, gobierno):
    """PP-07: activar cambia a VIGENTE, registra activación, historia y auditoría."""
    politica = crear_politica(mundo, accion_cierre="TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    r = activar(mundo, politica)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "VIGENTE", cuerpo
    assert cuerpo["activada_por"] == "ua", cuerpo
    assert cuerpo["activada_en"] is not None, cuerpo
    assert cuerpo["version"] == politica["version"] + 1, cuerpo
    assert [h["evento"] for h in cuerpo["historia"]][-1] == "ACTIVADA", cuerpo

    audit = eventos(mundo, "GOV_CLOSURE_POLICY_ACTIVATED", politica["id"])
    assert len(audit) == 1, politica


def test_pp08_if_match_obligatorio(mundo, gobierno):
    """PP-08: activar sin If-Match devuelve 428; versión vieja devuelve 409 STALE."""
    politica = crear_politica(mundo, accion_cierre="TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")

    r = sin_if_match(mundo, f"{C}/politicas/{politica['id']}/activar", {})
    assert r.status_code == 428, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_IF_MATCH_REQUIRED", r.text

    r = activar(mundo, politica, version=politica["version"] - 1)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_STALE", r.text


def test_pp09_segunda_vigente_por_accion(mundo, gobierno):
    """PP-09: segunda VIGENTE en la misma acción da ACTIVE_EXISTS; otra acción activa."""
    politica_vigente(mundo, "ORG02_CERRAR_ESTRUCTURA", "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")

    politica = crear_politica(mundo, accion_cierre="ORG02_CERRAR_ESTRUCTURA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    r = activar(mundo, politica)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_ACTIVE_EXISTS", r.text

    otra = crear_politica(mundo, accion_cierre="TRE02_CERRAR_PROGRAMA")
    otra = anadir_control(mundo, otra, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    r = activar(mundo, otra)
    assert r.status_code == 200, r.text


def test_pp10_vigente_inmutable_por_api(mundo, gobierno):
    """PP-10: una política VIGENTE no se edita ni admite controles."""
    politica = politica_vigente(mundo, "ORG02_CERRAR_ESTRUCTURA", "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")

    r = mundo.client.patch(
        f"/api/v1{C}/politicas/{politica['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(politica["version"])},
        json={"fundamento": "Intento de edición de política vigente."},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE", r.text

    r = post_control(mundo, politica, "ACTOS_SIN_EFICACIA")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE", r.text


def test_pp11_permisos(mundo, gobierno):
    """PP-11: view no crea, manage no activa, sin permiso no lista."""
    _crear_usuario_con_permisos(
        mundo,
        "cierre_consulta",
        [("gobierno_cierre", "view")],
        mundo.company_a,
    )
    _crear_usuario_con_permisos(
        mundo,
        "cierre_gestor",
        [("gobierno_cierre", "view"), ("gobierno_cierre", "manage")],
        mundo.company_a,
    )
    _crear_usuario_con_permisos(
        mundo,
        "sin_cierre",
        [("gobierno_hallazgos", "view")],
        mundo.company_a,
    )

    r = mundo.get(f"{C}/politicas", "cierre_consulta", mundo.company_a)
    assert r.status_code == 200, r.text

    r = post_politica(mundo, usuario="cierre_consulta")
    assert r.status_code == 403, r.text

    politica = crear_politica(mundo, usuario="cierre_gestor", accion_cierre="TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO", usuario="cierre_gestor")
    r = activar(mundo, politica, usuario="cierre_gestor")
    assert r.status_code == 403, r.text

    r = mundo.get(f"{C}/politicas", "sin_cierre", mundo.company_a)
    assert r.status_code == 403, r.text


def test_pp12_alcance_por_empresa(mundo, gobierno):
    """PP-12: otra empresa no ve la política y recibe 404 en detalle y activar."""
    politica = crear_politica(mundo, usuario="ua", empresa=mundo.company_a)

    r = mundo.get(f"{C}/politicas/{politica['id']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_NOT_FOUND", r.text

    r = activar(mundo, politica, usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404, r.text

    r = mundo.get(f"{C}/politicas", "ub", mundo.company_b)
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert politica["id"] not in ids, r.text


def test_pp13_guarda_sod_activar(mundo, gobierno):
    """PP-13: la guarda SoD bloquea activar cuando CTL10_REGISTRAR y CTL10_ACTIVAR coinciden."""
    regla = regla_sod_vigente(
        mundo,
        "CTL10_REGISTRAR",
        "CTL10_ACTIVAR",
        "Regla SoD CTL-10",
        proceso="CTL-10",
    )
    politica = crear_politica(mundo, usuario="ua", accion_cierre="TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO", usuario="ua")
    r = activar(mundo, politica, usuario="ua")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_CONFLICT", r.text

    detalle = mundo.get(f"{C}/politicas/{politica['id']}", "ua", mundo.company_a).json()
    assert detalle["estado"] == "BORRADOR", detalle
    cerrar_regla(mundo, regla)


def test_pp14_historia_en_orden(mundo, gobierno):
    """PP-14: la historia conserva CREADA, CONTROL_ANADIDO y ACTIVADA en orden."""
    politica = crear_politica(mundo, usuario="ua", accion_cierre="TRE02_CERRAR_PROGRAMA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO", usuario="ua")
    r = activar(mundo, politica, usuario="ua")
    assert r.status_code == 200, r.text
    assert [h["evento"] for h in r.json()["historia"]] == [
        "CREADA",
        "CONTROL_ANADIDO",
        "ACTIVADA",
    ], r.text
    assert all(h["usuario"] == "ua" for h in r.json()["historia"]), r.text


def test_pp15_lista_paginada_y_filtrada(mundo, gobierno):
    """PP-15: la lista pagina, filtra por estado y acción y devuelve resumen."""
    politica_vigente(mundo, "ORG02_CERRAR_ESTRUCTURA", "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    crear_politica(mundo, accion_cierre="TRE02_CERRAR_PROGRAMA")

    r = mundo.get(
        f"{C}/politicas?estado=VIGENTE&accion_cierre=ORG02_CERRAR_ESTRUCTURA&pagina=1&tamano=10",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert all(item["estado"] == "VIGENTE" for item in cuerpo["items"]), cuerpo
    assert all(item["accion_cierre"] == "ORG02_CERRAR_ESTRUCTURA" for item in cuerpo["items"]), cuerpo
    assert "resumen" in cuerpo, cuerpo


def test_pp16_politica_futura_y_vencida(mundo, gobierno):
    """PP-16: futura y vencida se pueden activar; efectiva_hoy es false."""
    futura = crear_politica(
        mundo,
        accion_cierre="TRE02_CERRAR_PROGRAMA",
        vigente_desde=(HOY + timedelta(days=30)).isoformat(),
    )
    futura = anadir_control(mundo, futura, "HALLAZGOS_ABIERTOS", riesgo_minimo="ALTO")
    r = activar(mundo, futura)
    assert r.status_code == 200, r.text
    assert r.json()["efectiva_hoy"] is False, r.text

    vencida = crear_politica(
        mundo,
        accion_cierre="ORG02_CERRAR_ESTRUCTURA",
        vigente_desde=(HOY - timedelta(days=30)).isoformat(),
        vigente_hasta=(HOY - timedelta(days=1)).isoformat(),
    )
    vencida = anadir_control(mundo, vencida, "ACTOS_SIN_EFICACIA")
    r = activar(mundo, vencida)
    assert r.status_code == 200, r.text
    assert r.json()["efectiva_hoy"] is False, r.text
