"""Pruebas HOSTILES (ROJO PRIMERO) de relaciones para inventario, maestros y documentos.

Se fija el contrato de aislamiento entre recursos de distintas empresas/tenants:
un identificador de otra empresa del mismo tenant, de otro tenant o inexistente
debe comportarse exactamente igual: 404 con código específico y sin modificar la
tabla destino. Estas pruebas deben FALLAR con el producto actual (los defectos
existen); una tarea posterior del ciclo 07 corregirá el producto.

Contrato ADR-D0-014: ajeno = inexistente.
"""
from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from hostil_mundo import CasoHostil, ejecutar_caso

pytest_plugins = ("tests.hostil_mundo",)


def _u() -> str:
    return "ISO" + secrets.token_hex(4).upper()


@dataclass(frozen=True)
class Relacion:
    id: str
    metodo: str
    ruta: Callable[[dict], str]
    cuerpo: Callable[[dict, str], dict]
    clave: str | None
    estado: int
    codigo: str
    tabla: str
    actor: str = "a1_op"


def _inv_ok_cuerpo(prep: dict, _x: str) -> dict:
    return {"code": _u(), "method": "AVERAGE", "global_scope": True}


def _inv_prod_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "method": "FIFO", "product_id": x}


def _mov_ok_cuerpo(prep: dict, _x: str) -> dict:
    return {"code": _u(), "name": "x", "direction": "IN", "global_scope": True}


def _transf_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "origin_warehouse_id": prep["w1"],
        "destination_warehouse_id": prep["w2"],
        "lines": [{"product_id": x, "quantity_sent": 1}],
    }


def _transf_propia_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "origin_warehouse_id": prep["w1"],
        "destination_warehouse_id": prep["w2"],
        "lines": [{"product_id": prep["producto"], "quantity_sent": 1}],
    }


def _transf_lote_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "origin_warehouse_id": prep["w1"],
        "destination_warehouse_id": prep["w2"],
        "lines": [{"product_id": prep["producto"], "quantity_sent": 1, "lot_id": x}],
    }


def _transf_serie_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "origin_warehouse_id": prep["w1"],
        "destination_warehouse_id": prep["w2"],
        "lines": [{"product_id": prep["producto"], "quantity_sent": 1, "serial_id": x}],
    }


def _conteo_prod_cuerpo(prep: dict, x: str) -> dict:
    return {"product_id": x, "expected_qty": 1}


def _conteo_lote_cuerpo(prep: dict, x: str) -> dict:
    return {"product_id": prep["producto"], "expected_qty": 1, "lot_id": x}


def _conteo_ubi_cuerpo(prep: dict, x: str) -> dict:
    return {"product_id": prep["producto"], "expected_qty": 1, "location_id": x}


def _cat_cat_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "item_type": "PRODUCT", "category_id": x}


def _cat_cat_propia_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "item_type": "PRODUCT", "category_id": prep["taxonomia"]}


def _cat_uom_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "name": "x",
        "item_type": "PRODUCT",
        "base_unit_id": x,
        "category_id": prep["taxonomia"],
    }


def _cat_perfil_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "name": "x",
        "item_type": "PRODUCT",
        "category_id": prep["taxonomia"],
        "tax_profile_id": x,
    }


def _cat_invperfil_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "name": "x",
        "item_type": "PRODUCT",
        "category_id": prep["taxonomia"],
        "inventory_profile_id": x,
    }


def _cat_serv_cuerpo(prep: dict, x: str) -> dict:
    return {
        "code": _u(),
        "name": "x",
        "item_type": "SERVICE",
        "category_id": prep["taxonomia"],
        "billing_unit_id": x,
    }


def _tax_padre_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "parent_id": x}


def _tax_padre_propia_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "parent_id": prep["taxonomia"]}


def _pres_uom_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "unit_id": x}


def _pres_uom_propia_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "unit_id": prep["unidad"]}


def _pres_fac_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "factor_to_base": "2", "factor_uom_id": x}


def _pres_fac_propia_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "factor_to_base": "2", "factor_uom_id": prep["unidad"]}


def _ver_fac_cuerpo(prep: dict, x: str) -> dict:
    return {"factor_to_base": "3", "factor_uom_id": x}


def _doc_cat_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "category_id": x}


def _doc_cat_propia_cuerpo(prep: dict, x: str) -> dict:
    return {"code": _u(), "name": "x", "category_id": prep["doc_categoria"]}


RELACIONES: list[Relacion] = [
    Relacion("ISO-INV-01", "POST", lambda p: "/inventory/costing-profiles", _inv_ok_cuerpo, None, 403, "GLOBAL_SCOPE_FORBIDDEN", "costing_profiles"),
    Relacion("ISO-INV-02", "POST", lambda p: "/inventory/costing-profiles", _inv_prod_cuerpo, "product", 404, "PRODUCT_NOT_FOUND", "costing_profiles"),
    Relacion("ISO-INV-03", "POST", lambda p: "/inventory/movement-types", _mov_ok_cuerpo, None, 403, "GLOBAL_SCOPE_FORBIDDEN", "movement_types"),
    Relacion("ISO-INV-04", "POST", lambda p: "/inventory/transfers", _transf_cuerpo, "product", 404, "PRODUCT_NOT_FOUND", "transfers"),
    Relacion("ISO-INV-05", "POST", lambda p: "/inventory/transfers", _transf_lote_cuerpo, "lot", 404, "LOT_NOT_FOUND", "transfers"),
    Relacion("ISO-INV-06", "POST", lambda p: "/inventory/transfers", _transf_serie_cuerpo, "serial", 404, "SERIAL_NOT_FOUND", "transfers"),
    Relacion("ISO-INV-07", "POST", lambda p: f"/inventory/counts/{p['conteo']}/lines", _conteo_prod_cuerpo, "product", 404, "PRODUCT_NOT_FOUND", "stock_count_lines"),
    Relacion("ISO-INV-08", "POST", lambda p: f"/inventory/counts/{p['conteo']}/lines", _conteo_lote_cuerpo, "lot", 404, "LOT_NOT_FOUND", "stock_count_lines"),
    Relacion("ISO-INV-09", "POST", lambda p: f"/inventory/counts/{p['conteo']}/lines", _conteo_ubi_cuerpo, "ubicacion", 404, "LOCATION_NOT_FOUND", "stock_count_lines"),
    Relacion("ISO-MD-01", "POST", lambda p: "/maestros/catalogos/items", _cat_cat_cuerpo, "taxonomy", 404, "CATEGORY_NOT_FOUND", "catalog_items"),
    Relacion("ISO-MD-02", "POST", lambda p: "/maestros/catalogos/items", _cat_uom_cuerpo, "unit", 404, "UOM_NOT_FOUND", "catalog_items"),
    Relacion("ISO-MD-03", "POST", lambda p: "/maestros/catalogos/items", _cat_perfil_cuerpo, "profile", 404, "PROFILE_NOT_FOUND", "catalog_items"),
    Relacion("ISO-MD-04", "POST", lambda p: "/maestros/catalogos/items", _cat_invperfil_cuerpo, "profile", 404, "PROFILE_NOT_FOUND", "catalog_items"),
    Relacion("ISO-MD-05", "POST", lambda p: "/maestros/catalogos/items", _cat_serv_cuerpo, "unit", 404, "UOM_NOT_FOUND", "catalog_items"),
    Relacion("ISO-MD-06", "POST", lambda p: "/maestros/catalogos/taxonomia", _tax_padre_cuerpo, "taxonomy", 404, "TAXONOMY_NODE_NOT_FOUND", "taxonomy_nodes"),
    Relacion("ISO-MD-07", "POST", lambda p: f"/maestros/productos/{p['producto']}/presentaciones", _pres_uom_cuerpo, "unit", 404, "UOM_NOT_FOUND", "presentations"),
    Relacion("ISO-MD-08", "POST", lambda p: f"/maestros/productos/{p['producto']}/presentaciones", _pres_fac_cuerpo, "unit", 404, "UOM_NOT_FOUND", "presentations"),
    Relacion("ISO-MD-09", "POST", lambda p: f"/maestros/presentaciones/{p['presentacion']}/versiones", _ver_fac_cuerpo, "unit", 404, "UOM_NOT_FOUND", "product_presentation_versions"),
    Relacion("ISO-DOC-01", "POST", lambda p: "/documentos/tipos", _doc_cat_cuerpo, "doc_category", 404, "DOCUMENT_CATEGORY_NOT_FOUND", "document_types", "admin_a"),
]


def _referido(mundo, prep: dict, rel: Relacion, origen: str) -> str:
    if origen == "INEXISTENTE":
        return str(uuid.uuid4())
    if rel.clave == "ubicacion":
        return prep["ubicacion"][origen]
    return mundo.recursos[origen][rel.clave]


def _cuerpo_control(rel: Relacion, prep: dict, x: str) -> dict:
    if rel.id == "ISO-INV-01":
        return {"code": _u(), "method": "AVERAGE", "global_scope": False}
    if rel.id == "ISO-INV-03":
        return {"code": _u(), "name": "x", "direction": "IN", "global_scope": False}
    if rel.id == "ISO-INV-04":
        return _transf_propia_cuerpo(prep, x)
    if rel.id == "ISO-MD-01":
        return _cat_cat_propia_cuerpo(prep, x)
    if rel.id == "ISO-MD-06":
        return _tax_padre_propia_cuerpo(prep, x)
    if rel.id == "ISO-MD-07":
        return _pres_uom_propia_cuerpo(prep, x)
    if rel.id == "ISO-MD-08":
        return _pres_fac_propia_cuerpo(prep, x)
    if rel.id == "ISO-DOC-01":
        return _doc_cat_propia_cuerpo(prep, x)
    return rel.cuerpo(prep, x)


@pytest.fixture(scope="module")
def prep(mundo_hostil):
    from app.modules.inventory.models import StockCount
    from app.modules.master_data.models import CatalogItem
    from app.modules.organization.models import Warehouse, WarehouseLocation

    a1 = mundo_hostil.empresas["A1"]
    w1_id = mundo_hostil.recursos["A1"]["warehouse"]
    u = _u()

    with mundo_hostil.factory() as db:
        w2 = Warehouse(company_id=a1, code=u, name="W2")
        db.add(w2)
        db.flush()

        conteo = StockCount(company_id=a1, warehouse_id=w1_id, code=_u())
        db.add(conteo)
        db.flush()

        ubicacion: dict[str, str] = {}
        for emp in ("A1", "A2", "B1"):
            loc = WarehouseLocation(
                company_id=mundo_hostil.empresas[emp],
                warehouse_id=mundo_hostil.recursos[emp]["warehouse"],
                code=_u(),
            )
            db.add(loc)
            db.flush()
            ubicacion[emp] = str(loc.id)

        producto = db.get(CatalogItem, mundo_hostil.recursos["A1"]["product"])
        producto.base_unit_id = mundo_hostil.recursos["A1"]["unit"]
        db.flush()
        db.commit()

        p = {
            "w1": w1_id,
            "w2": str(w2.id),
            "conteo": str(conteo.id),
            "ubicacion": ubicacion,
            "producto": mundo_hostil.recursos["A1"]["product"],
            "unidad": mundo_hostil.recursos["A1"]["unit"],
            "taxonomia": mundo_hostil.recursos["A1"]["taxonomy"],
            "doc_categoria": mundo_hostil.recursos["A1"]["doc_category"],
        }

    r = mundo_hostil.pedir(
        "a1_op",
        "POST",
        f"/maestros/productos/{p['producto']}/presentaciones",
        empresa=a1,
        json={"code": "PRA1" + secrets.token_hex(2).upper(), "name": "Pres A1"},
    )
    assert r.status_code in (200, 201), r.text
    p["presentacion"] = str(r.json()["id"])
    return p


@pytest.mark.parametrize("origen", ["A2", "B1", "INEXISTENTE"])
@pytest.mark.parametrize("rel", [r for r in RELACIONES if r.clave], ids=lambda r: r.id)
def test_relacion_ajena_se_rechaza(mundo_hostil, prep, rel, origen):
    x = _referido(mundo_hostil, prep, rel, origen)
    ejecutar_caso(
        mundo_hostil,
        CasoHostil(
            nombre=f"{rel.id}-{origen}",
            actor=rel.actor,
            metodo=rel.metodo,
            ruta=rel.ruta(prep),
            empresa_activa=mundo_hostil.empresas["A1"],
            json=rel.cuerpo(prep, x),
            estado=rel.estado,
            codigo=rel.codigo,
            tablas_inmutables=[rel.tabla],
        ),
    )


@pytest.mark.parametrize("rel", [r for r in RELACIONES if not r.clave], ids=lambda r: r.id)
def test_escritura_global_se_rechaza(mundo_hostil, prep, rel):
    ejecutar_caso(
        mundo_hostil,
        CasoHostil(
            nombre=rel.id,
            actor=rel.actor,
            metodo=rel.metodo,
            ruta=rel.ruta(prep),
            empresa_activa=mundo_hostil.empresas["A1"],
            json=rel.cuerpo(prep, ""),
            estado=rel.estado,
            codigo=rel.codigo,
            tablas_inmutables=[rel.tabla],
        ),
    )


@pytest.mark.parametrize("rel", RELACIONES, ids=lambda r: r.id)
def test_control_relacion_propia_se_acepta(mundo_hostil, prep, rel):
    if rel.clave is None:
        x = ""
    elif rel.clave == "ubicacion":
        x = prep["ubicacion"]["A1"]
    else:
        x = mundo_hostil.recursos["A1"][rel.clave]

    r = mundo_hostil.pedir(
        rel.actor,
        rel.metodo,
        rel.ruta(prep),
        empresa=mundo_hostil.empresas["A1"],
        json=_cuerpo_control(rel, prep, x),
    )
    assert r.status_code in (200, 201), f"{rel.id}: {r.status_code} {r.text}"
