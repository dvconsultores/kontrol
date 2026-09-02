"""Arquitectura de la captura temprana — Spec 029, `P23`.

Falla en construcción. Existe para que un refactor futuro no pueda devolver la
línea de venta a `unit_price` a secas: la deuda que la Spec 029 cerró tardó dos
Specs en cerrarse y no debe reabrirse en una tarde.
"""

from __future__ import annotations

import ast
import pathlib

from sqlalchemy import Float, Numeric

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope, scope_authority

init_models()

#: Las líneas comerciales que resuelven precio automáticamente.
LINEAS_COMERCIALES = ("sales_quote_lines", "sales_order_lines")

#: El contrato de evidencia de la Spec 012 §11, más lo que 029 añadió para
#: poder distinguir un precio manual de uno resuelto.
EVIDENCIA = (
    "price_source_version_id",
    "price_source_item_id",
    "pricing_source",
    "resolved_unit_price",
    "manual_reason",
    "discount_policy_id",
    "discount_policy_version",
    "discount_approval_request_id",
    "payment_term_snapshot",
)


def test_toda_linea_comercial_conserva_su_evidencia():
    """`P23`: si el precio se resuelve, su origen se guarda."""
    faltan = []
    for tabla in LINEAS_COMERCIALES:
        cols = set(Base.metadata.tables[tabla].columns.keys())
        for campo in EVIDENCIA:
            if campo not in cols:
                faltan.append(f"{tabla}.{campo}")
    assert faltan == [], (
        "líneas comerciales sin evidencia de origen:\n  " + "\n  ".join(faltan)
        + "\n\nUn precio sin origen no se puede reconstruir, y no porque el dato se "
          "pierda: es que nunca se captura.")


def test_el_origen_apunta_a_la_version_no_a_la_lista():
    """La lista cambia; la versión es lo que produjo **ese** precio."""
    malos = []
    for tabla in LINEAS_COMERCIALES:
        col = Base.metadata.tables[tabla].c["price_source_version_id"]
        destinos = {f.column.table.name for f in col.foreign_keys}
        if destinos != {"price_list_versions"}:
            malos.append(f"{tabla}: {destinos or 'sin clave foránea'}")
    assert malos == [], "\n  ".join(["el origen no referencia la versión:", *malos])


def test_la_evidencia_admite_nulos():
    """Las líneas anteriores no reciben un origen inventado.

    Rellenar la clave foránea con una versión actual solo para que no quede nula
    sería falsificar evidencia histórica, que es peor que no tenerla.
    """
    obligatorias = []
    for tabla in LINEAS_COMERCIALES:
        for campo in EVIDENCIA:
            if not Base.metadata.tables[tabla].c[campo].nullable:
                obligatorias.append(f"{tabla}.{campo}")
    assert obligatorias == [], f"evidencia obligatoria que impediría el legado: {obligatorias}"


def test_el_precio_de_la_linea_no_trunca_el_del_maestro():
    """El maestro guarda cuatro decimales; la línea tenía dos.

    Copiar un precio de la lista lo redondeaba en silencio, y entonces el origen
    apuntaba a una versión cuyo precio no coincidía con el de la línea.
    """
    maestro = Base.metadata.tables["price_list_items"].c["unit_price"].type
    for tabla in LINEAS_COMERCIALES:
        linea = Base.metadata.tables[tabla].c["unit_price"].type
        assert isinstance(linea, Numeric) and linea.scale >= maestro.scale, (
            f"{tabla}.unit_price tiene escala {linea.scale} y el maestro {maestro.scale}")


def test_ningun_importe_de_venta_es_de_coma_flotante():
    flotantes = []
    for tabla in LINEAS_COMERCIALES + ("sales_quotes", "sales_orders"):
        for col in Base.metadata.tables[tabla].columns:
            if isinstance(col.type, Float) and not isinstance(col.type, Numeric):
                flotantes.append(f"{tabla}.{col.name}")
    assert flotantes == [], f"importes en coma flotante: {flotantes}"


def test_las_lineas_derivan_su_empresa_y_no_la_duplican():
    for tabla, ruta in (("sales_quote_lines", "quote_id → sales_quotes"),
                        ("sales_order_lines", "order_id → sales_orders")):
        modelo = next(m.class_ for m in Base.registry.mappers
                      if m.class_.__tablename__ == tabla)
        assert declared_scope(modelo) is Scope.COMPANY
        assert scope_authority(modelo) == ruta, f"{tabla}: ruta «{scope_authority(modelo)}»"
        assert "company_id" not in Base.metadata.tables[tabla].c, (
            f"{tabla} lleva `company_id` redundante")


def test_ventas_no_crea_un_segundo_resolutor_de_precio():
    """Hay una autoridad de precio y vive en la Spec 012.

    Se busca por estructura, no por comentario: cualquier función del módulo de
    ventas cuyo nombre prometa resolver un precio sería una segunda autoridad.
    """
    fuente = pathlib.Path(__file__).resolve().parents[1] / "app" / "modules" / "sales"
    culpables = []
    for archivo in fuente.glob("*.py"):
        arbol = ast.parse(archivo.read_text())
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name in (
                    "resolve_price", "resolver_precio", "calcular_precio", "price_for"):
                culpables.append(f"{archivo.name}::{nodo.name}")
    assert culpables == [], (
        f"segundo resolutor de precio en ventas: {culpables}. "
        "La autoridad es `commercial.resolver_precio`")


def test_la_conversion_no_vuelve_a_resolver():
    """La conversión copia la evidencia; no la recalcula.

    Se comprueba sobre el AST: si `convertir_en_pedido` llamara al resolutor,
    el precio del pedido podría diferir del que aceptó el cliente.
    """
    servicio = pathlib.Path(__file__).resolve().parents[1] / "app" / "modules" / "sales" / "service.py"
    arbol = ast.parse(servicio.read_text())
    fn = next(n for n in ast.walk(arbol)
              if isinstance(n, ast.FunctionDef) and n.name == "convertir_en_pedido")
    llamadas = [n.func.attr for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "resolver_precio" not in llamadas and "_origen_comercial" not in [
        n.func.id for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)], (
        "la conversión vuelve a resolver el precio: el cliente aceptó otro")
