"""Pruebas hostiles (rojo atribuible) de relaciones de compras y ventas.

Ajeno = inexistente para el actor, conforme a ADR-D0-014.
"""

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from hostil_mundo import CasoHostil, ejecutar_caso

from app.modules.purchasing.models import (
    PurchaseRequisition,
    SupplierInvoice,
    SupplierQuote,
)
from app.modules.sales.models import SalesInvoice

pytest_plugins = ("tests.hostil_mundo",)


@dataclass(frozen=True)
class Relacion:
    id: str
    metodo: str
    ruta: Callable[[dict], str]
    cuerpo: Callable[[dict, str], dict]
    clave: str
    estado: int
    codigo: str
    tabla: str
    actor: str = "a1_op"


RELACIONES: list[Relacion] = [
    Relacion(
        "ISO-COM-01",
        "POST",
        lambda p: f"/purchasing/supplier-invoices/{p['fa']}/lines",
        lambda p, x: {"product_id": x, "quantity": 1, "unit_price": 1},
        "product",
        404,
        "PRODUCT_NOT_FOUND",
        "supplier_invoice_lines",
    ),
    Relacion(
        "ISO-COM-02",
        "POST",
        lambda p: f"/purchasing/supplier-invoices/{p['fa']}/lines",
        lambda p, x: {
            "product_id": p["PA"],
            "quantity": 1,
            "unit_price": 1,
            "order_line_id": x,
        },
        "po_line",
        404,
        "ORDER_LINE_NOT_FOUND",
        "supplier_invoice_lines",
    ),
    Relacion(
        "ISO-COM-03",
        "POST",
        lambda p: f"/purchasing/supplier-invoices/{p['fa']}/lines",
        lambda p, x: {
            "product_id": p["PA"],
            "quantity": 1,
            "unit_price": 1,
            "receipt_line_id": x,
        },
        "receipt_line",
        404,
        "RECEIPT_LINE_NOT_FOUND",
        "supplier_invoice_lines",
    ),
    Relacion(
        "ISO-COM-04",
        "POST",
        lambda p: f"/purchasing/orders/{p['purchase_order']}/lines",
        lambda p, x: {"product_id": x, "quantity_ordered": 1, "unit_price": 1},
        "product",
        404,
        "PRODUCT_NOT_FOUND",
        "purchase_order_lines",
    ),
    Relacion(
        "ISO-COM-05",
        "POST",
        lambda p: f"/purchasing/requisitions/{p['req']}/lines",
        lambda p, x: {"product_id": x, "quantity": 1},
        "product",
        404,
        "PRODUCT_NOT_FOUND",
        "purchase_requisition_lines",
    ),
    Relacion(
        "ISO-COM-06",
        "POST",
        lambda p: f"/purchasing/requisitions/{p['req']}/lines",
        lambda p, x: {"product_id": p["PA"], "quantity": 1, "unit_id": x},
        "unit",
        404,
        "UOM_NOT_FOUND",
        "purchase_requisition_lines",
    ),
    Relacion(
        "ISO-COM-07",
        "POST",
        lambda p: f"/purchasing/quotes/{p['cot']}/lines",
        lambda p, x: {"product_id": x, "quantity": 1, "unit_price": 1},
        "product",
        404,
        "PRODUCT_NOT_FOUND",
        "supplier_quote_lines",
    ),
    Relacion(
        "ISO-VEN-01",
        "POST",
        lambda p: f"/sales/invoices/{p['fv']}/lines",
        lambda p, x: {"product_id": x, "quantity": 1, "unit_price": 1},
        "product",
        404,
        "ITEM_NOT_FOUND",
        "sales_invoice_lines",
    ),
]


@pytest.fixture(scope="module")
def prep(mundo_hostil):
    """Prepara facturas, requisiciones, cotizaciones y facturas de venta."""
    recursos = mundo_hostil.recursos
    resultado: dict[str, str] = {"PA": recursos["A1"]["product"]}
    resultado["purchase_order"] = recursos["A1"]["purchase_order"]
    con = mundo_hostil.empresas

    with mundo_hostil.factory() as db:
        u = "ISO" + secrets.token_hex(4).upper()
        fa = SupplierInvoice(
            company_id=con["A1"],
            supplier_id=recursos["A1"]["party"],
            invoice_number=u,
        )
        db.add(fa)
        fa_a2 = SupplierInvoice(
            company_id=con["A2"],
            supplier_id=recursos["A2"]["party"],
            invoice_number=u + "2",
        )
        db.add(fa_a2)
        fa_b1 = SupplierInvoice(
            company_id=con["B1"],
            supplier_id=recursos["B1"]["party"],
            invoice_number=u + "B",
        )
        db.add(fa_b1)
        req = PurchaseRequisition(company_id=con["A1"], code=u + "R")
        db.add(req)
        cot = SupplierQuote(
            company_id=con["A1"],
            supplier_id=recursos["A1"]["party"],
            code=u + "C",
        )
        db.add(cot)
        fv = SalesInvoice(
            company_id=con["A1"],
            customer_id=recursos["A1"]["party"],
        )
        db.add(fv)
        db.flush()
        resultado["fa"] = str(fa.id)
        resultado["fa_A2"] = str(fa_a2.id)
        resultado["fa_B1"] = str(fa_b1.id)
        resultado["req"] = str(req.id)
        resultado["cot"] = str(cot.id)
        resultado["fv"] = str(fv.id)
        db.commit()

    return resultado


@pytest.mark.parametrize("rel", RELACIONES)
@pytest.mark.parametrize("origen", ["A2", "B1", "INEXISTENTE"])
def test_relacion_ajena_se_rechaza(mundo_hostil, prep, rel, origen):
    """Las relaciones de líneas apuntando a recursos ajenos o inexistentes se rechazan."""
    recursos = mundo_hostil.recursos
    if origen == "INEXISTENTE":
        x = str(uuid.uuid4())
    else:
        x = recursos[origen][rel.clave]

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


@pytest.mark.parametrize("origen", ["A2", "B1", "INEXISTENTE"])
def test_factura_compra_ajena_se_rechaza(mundo_hostil, prep, origen):
    """Una factura de compra ajena o inexistente no admite líneas (ISO-COM-08)."""
    if origen == "INEXISTENTE":
        factura = str(uuid.uuid4())
    else:
        factura = prep[f"fa_{origen}"]

    ejecutar_caso(
        mundo_hostil,
        CasoHostil(
            nombre=f"ISO-COM-08-{origen}",
            actor="a1_op",
            metodo="POST",
            ruta=f"/purchasing/supplier-invoices/{factura}/lines",
            empresa_activa=mundo_hostil.empresas["A1"],
            json={"product_id": prep["PA"], "quantity": 1, "unit_price": 1},
            estado=404,
            codigo="INVOICE_NOT_FOUND",
            tablas_inmutables=["supplier_invoice_lines"],
        ),
    )


@pytest.mark.parametrize("rel", RELACIONES)
def test_control_relacion_propia_se_acepta(mundo_hostil, prep, rel):
    """Las relaciones propias del actor en A1 se aceptan (control)."""
    x = mundo_hostil.recursos["A1"][rel.clave]
    r = mundo_hostil.pedir(
        rel.actor,
        rel.metodo,
        rel.ruta(prep),
        empresa=mundo_hostil.empresas["A1"],
        json=rel.cuerpo(prep, x),
    )
    assert r.status_code in (200, 201), f"{rel.id}: {r.status_code} {r.text}"
