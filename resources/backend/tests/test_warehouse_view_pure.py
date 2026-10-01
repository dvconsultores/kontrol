"""WHV · Lo que el listado dice de un almacén, a partir de sus dependencias (FR-054-E2EFLK-004).

El listado de almacenes calculaba esto con una docena de consultas por fila; ahora lo deriva
de unas cuentas hechas una vez por página, recibidas ya contadas.
Las reglas son las mismas que las del camino por almacén: qué impide borrar, cuándo el
almacén es operativo y qué acciones ofrece.
Estas pruebas no tocan la base de datos: solo la función pura.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.organization import structure as st

TODOS = {
    "organization:view",
    "organization:edit",
    "organization:activate",
    "organization:deactivate",
    "organization:delete",
    "organization:manage_structure",
    "organization:create",
}


def almacen(
    status: str = "ACTIVE",
    regimen: str = "INITIAL",
    tramos: dict[str, bool] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(status=status, structure_regime=regimen, structure_levels=tramos)


def test_whv_01_un_almacen_vacio_se_puede_borrar_y_reestructurar():
    vista = st.warehouse_view(almacen(), {})
    assert vista == {
        "can_delete": True,
        "delete_blocked_by": None,
        "structure_regime": "INITIAL",
        "allowed_actions": [
            "edit",
            "deactivate",
            "manage_structure",
            "add_location",
            "delete",
        ],
    }


def test_whv_02_las_claves_son_exactamente_cuatro():
    assert set(st.warehouse_view(almacen(), {})) == {
        "can_delete",
        "delete_blocked_by",
        "structure_regime",
        "allowed_actions",
    }


def test_whv_03_un_almacen_inactivo_ofrece_activar_no_desactivar():
    acciones = st.warehouse_view(almacen(status="INACTIVE"), {})["allowed_actions"]
    assert "activate" in acciones and "deactivate" not in acciones
    assert acciones[:2] == ["edit", "activate"]


def test_whv_04_los_tramos_declarados_salen_en_orden_canonico():
    tramos = {"rack": True, "zone": True, "aisle": False, "level": True}
    assert st.warehouse_view(almacen(tramos=tramos), {})["allowed_actions"] == [
        "edit",
        "deactivate",
        "manage_structure",
        "add_zone",
        "add_rack",
        "add_level",
        "add_location",
        "delete",
    ]


@pytest.mark.parametrize("clave", ["zone", "aisle", "rack", "level", "locations"])
def test_whv_05_cualquier_nodo_o_ubicacion_vuelve_operativo_el_almacen_y_lo_bloquea(clave):
    vista = st.warehouse_view(almacen(), {clave: 2})
    assert vista["structure_regime"] == st.REGIME_OPERATIONAL
    assert vista["can_delete"] is False
    assert vista["delete_blocked_by"] == {clave: 2}
    assert "manage_structure" not in vista["allowed_actions"] and "delete" not in vista["allowed_actions"]


def test_whv_06_los_movimientos_impiden_borrar_pero_no_son_estructura():
    vista = st.warehouse_view(almacen(), {"movements": 5})
    assert vista["can_delete"] is False and vista["delete_blocked_by"] == {"movements": 5}
    assert vista["structure_regime"] == st.REGIME_INITIAL
    assert vista["allowed_actions"] == ["edit", "deactivate", "manage_structure", "add_location"]


def test_whv_07_el_regimen_operativo_guardado_no_vuelve_atras():
    vista = st.warehouse_view(almacen(regimen="OPERATIONAL"), {})
    assert vista["structure_regime"] == st.REGIME_OPERATIONAL
    assert vista["can_delete"] is True
    assert vista["allowed_actions"] == ["edit", "deactivate", "add_location", "delete"]


def test_whv_08_lo_que_bloquea_se_devuelve_entero_en_su_orden_y_como_copia():
    cuentas = {"zone": 1, "aisle": 2, "locations": 4, "movements": 9}
    original = dict(cuentas)
    vista = st.warehouse_view(almacen(), cuentas)
    assert vista["delete_blocked_by"] == original
    assert list(vista["delete_blocked_by"]) == ["zone", "aisle", "locations", "movements"]
    assert vista["delete_blocked_by"] is not cuentas
    assert cuentas == original


def test_whv_09_sin_permisos_declarados_no_se_recorta_y_con_todos_tampoco():
    assert (
        st.warehouse_view(almacen(tramos={"zone": True}), {}, None)["allowed_actions"]
        == st.warehouse_view(almacen(tramos={"zone": True}), {}, TODOS)["allowed_actions"]
        == ["edit", "deactivate", "manage_structure", "add_zone", "add_location", "delete"]
    )


def test_whv_10_quien_solo_puede_ver_no_recibe_ninguna_accion():
    assert st.warehouse_view(almacen(tramos={"zone": True}), {}, {"organization:view"})["allowed_actions"] == []


@pytest.mark.parametrize(
    "permisos, esperadas",
    [
        ({"organization:edit"}, ["edit"]),
        ({"organization:deactivate"}, ["deactivate"]),
        ({"organization:create"}, ["add_zone", "add_location"]),
        ({"organization:delete"}, ["delete"]),
        ({"organization:manage_structure"}, ["manage_structure"]),
        ({"organization:edit", "organization:create"}, ["edit", "add_zone", "add_location"]),
    ],
)
def test_whv_11_cada_accion_exige_su_permiso(permisos, esperadas):
    assert st.warehouse_view(almacen(tramos={"zone": True}), {}, permisos)["allowed_actions"] == esperadas


def test_whv_12_activar_exige_su_propio_permiso():
    inactivo = almacen(status="INACTIVE")
    assert st.warehouse_view(inactivo, {}, {"organization:activate"})["allowed_actions"] == ["activate"]
    assert st.warehouse_view(inactivo, {}, {"organization:deactivate"})["allowed_actions"] == []


def test_whv_13_el_permiso_de_borrar_no_basta_si_hay_dependencias():
    assert "delete" not in st.warehouse_view(almacen(), {"movements": 1}, TODOS)["allowed_actions"]
    assert "delete" not in st.warehouse_view(almacen(), {"locations": 1}, TODOS)["allowed_actions"]


@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE", "BLOCKED"])
@pytest.mark.parametrize("regimen", ["INITIAL", "OPERATIONAL"])
@pytest.mark.parametrize("cuentas", [{}, {"movements": 3}, {"locations": 1}, {"zone": 1, "movements": 2}, {"level": 7}])
def test_whv_14_las_tres_reglas_se_cumplen_en_cualquier_combinacion(status, regimen, cuentas):
    vista = st.warehouse_view(almacen(status=status, regimen=regimen), dict(cuentas))
    acciones = vista["allowed_actions"]
    assert vista["can_delete"] is (not cuentas)
    assert ("delete" in acciones) is vista["can_delete"]
    assert ("manage_structure" in acciones) is (vista["structure_regime"] == st.REGIME_INITIAL)
    estructura = any(clave != "movements" for clave in cuentas)
    assert vista["structure_regime"] == (
        st.REGIME_OPERATIONAL if regimen == "OPERATIONAL" or estructura else st.REGIME_INITIAL
    )
    assert ("deactivate" in acciones) is (status == "ACTIVE")
    assert ("activate" in acciones) is (status != "ACTIVE")


def test_whv_15_sin_tramos_declarados_o_con_none_no_hay_altas_de_tramo():
    for tramos in (None, {}, {"zone": False, "rack": False}):
        acciones = st.warehouse_view(almacen(tramos=tramos), {})["allowed_actions"]
        assert [a for a in acciones if a.startswith("add_")] == ["add_location"]
