"""Cotización y pedido con origen comercial — Spec 029.

La Spec 012 construyó la autoridad de precio y nadie la llamaba: `unit_price`
era un número que alguien tecleó. `P23` dice por qué eso importa — **el dato no
se pierde, es que nunca se captura**, y ninguna migración posterior lo repara.

Estas pruebas comprueban que ahora se captura, que sobrevive a que el maestro
cambie, y que viaja intacto de la cotización al pedido.
"""

from __future__ import annotations

from datetime import date, timedelta

pytest_plugins = ("tests.conftest_multicompany",)

BLOQUEO = (403, 404)
HOY = date.today()


# --------------------------------------------------------------------------- #
# Mundo comercial mínimo: lista activa con un precio
# --------------------------------------------------------------------------- #
def _cliente(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})


def _articulo(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Artículo {code}", "item_type": "PRODUCT"})


def _lista_con_precio(mundo, usuario, empresa, marca, articulo, precio):
    """Deja una versión ACTIVE con un precio para ese artículo."""
    moneda = mundo.crear("/treasury/currencies", usuario, empresa,
                         {"code": f"{marca[:3]}", "name": "Moneda", "symbol": "$"})
    lista = mundo.crear("/comercial/listas-precio", usuario, empresa,
                        {"code": f"L-{marca}", "name": f"Lista {marca}", "currency_id": moneda})
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones", usuario, empresa,
                   {"valid_from": str(HOY - timedelta(days=1))})
    assert r.status_code == 201, r.text
    version = r.json()["id"]
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items",
                   usuario, empresa, {"item_id": articulo, "unit_price": precio})
    assert r.status_code == 201, r.text
    item = r.json()["id"]
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
                   usuario, empresa, {"target": "ACTIVE"})
    assert r.status_code == 200, r.text
    return {"lista": lista, "version": version, "item": item, "moneda": moneda}


def _cotizacion(mundo, usuario, empresa, code, cliente):
    return mundo.crear("/sales/quotes", usuario, empresa,
                       {"code": code, "customer_id": cliente, "currency": "VED"})


# --------------------------------------------------------------------------- #
# P23 — la captura del origen
# --------------------------------------------------------------------------- #
def test_una_linea_sin_precio_lo_resuelve_y_guarda_su_origen(mundo):
    """El caso que esta Spec existe para cerrar."""
    art = _articulo(mundo, "ua", mundo.company_a, "P23-ART")
    maestro = _lista_con_precio(mundo, "ua", mundo.company_a, "P23", art, "125.4000")
    cli = _cliente(mundo, "ua", mundo.company_a, "P23-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "P23-COT", cli)

    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 3})
    assert r.status_code == 200, r.text
    linea = r.json()
    assert linea["unit_price"] == "125.4000", "no tomó el precio de la lista"
    assert linea["pricing_source"] == "RESOLVED"
    assert linea["price_source_version_id"] == maestro["version"], (
        "guardó el precio y no la versión que lo produjo")
    assert linea["price_source_item_id"] == maestro["item"]


def test_sin_lista_aplicable_no_se_inventa_un_precio(mundo):
    """Un cero es un precio. La ausencia de precio no lo es."""
    art = _articulo(mundo, "ua", mundo.company_a, "SINL-ART")
    cli = _cliente(mundo, "ua", mundo.company_a, "SINL-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "SINL-COT", cli)
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1})
    assert r.status_code == 422, f"inventó un precio sin lista: {r.text}"
    assert r.json()["code"] == "PRICE_NOT_RESOLVED"


def test_un_precio_sin_lista_se_marca_como_sin_origen(mundo):
    """Escribir un precio cuando no hay lista **no** es una desviación.

    No hay de qué desviarse. Exigir un motivo aquí sería pedir que se justifique
    una diferencia contra un precio que no existe, y dejaría el sistema
    inservible el primer día: los catálogos comerciales nacen vacíos por `P8`.

    Se registra lo que es —un precio sin origen— con el tercer valor del enum
    que la Spec 012 declaró justo para esto.
    """
    art = _articulo(mundo, "ua", mundo.company_a, "LEG-ART")
    cli = _cliente(mundo, "ua", mundo.company_a, "LEG-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "LEG-COT", cli)
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1, "unit_price": 42})
    assert r.status_code == 200, f"rechazó un precio donde no hay lista: {r.text}"
    linea = r.json()
    assert linea["pricing_source"] == "LEGACY_FREETEXT"
    assert linea["resolved_unit_price"] is None
    assert linea["manual_reason"] is None


def test_un_precio_manual_exige_motivo_y_conserva_el_resuelto(mundo):
    """Con lista, desviarse **sí** necesita explicación.

    Y sin el resuelto al lado, un precio manual y uno automático no se
    distinguen después.
    """
    art = _articulo(mundo, "ua", mundo.company_a, "MAN-ART")
    _lista_con_precio(mundo, "ua", mundo.company_a, "MAN", art, "100.0000")
    cli = _cliente(mundo, "ua", mundo.company_a, "MAN-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "MAN-COT", cli)

    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1, "unit_price": 80})
    assert r.status_code == 422, f"aceptó un precio manual sin motivo: {r.text}"
    assert r.json()["code"] == "MANUAL_PRICE_REASON_REQUIRED"

    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1, "unit_price": 80,
                    "manual_reason": "Acuerdo puntual con el cliente"})
    assert r.status_code == 200, r.text
    linea = r.json()
    assert linea["pricing_source"] == "MANUAL_JUSTIFIED"
    assert linea["unit_price"] == "80.0000"
    assert linea["resolved_unit_price"] == "100.0000", "perdió lo que dijo el resolutor"
    assert linea["manual_reason"]


def test_el_descuento_registra_su_politica(mundo):
    art = _articulo(mundo, "ua", mundo.company_a, "DTO-ART")
    _lista_con_precio(mundo, "ua", mundo.company_a, "DTO", art, "50.0000")
    assert mundo.post("/comercial/politicas-descuento", "ua", mundo.company_a,
                      {"code": "V-LIN", "name": "Línea", "scope": "LINE",
                       "max_percent": "20.0"}).status_code == 201
    cli = _cliente(mundo, "ua", mundo.company_a, "DTO-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "DTO-COT", cli)

    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1, "discount": 10})
    assert r.status_code == 200, r.text
    assert r.json()["discount_policy_id"], "no registró qué política autorizó el descuento"
    assert r.json()["discount_policy_version"] == 1

    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1, "discount": 40})
    assert r.status_code == 422, "aceptó un descuento sobre el máximo"
    assert r.json()["code"] == "DISCOUNT_ABOVE_LIMIT"


# --------------------------------------------------------------------------- #
# Invariancia histórica
# --------------------------------------------------------------------------- #
def test_una_cotizacion_no_se_recalcula_cuando_cambia_la_lista(mundo):
    """El corazón de `P23`.

    Se crea la línea con V1 a 100, se supera V1 con V2 a 120, y la cotización
    debe seguir diciendo 100 **y** apuntando a V1. Recalcularla cambiaría lo que
    se le ofreció al cliente.
    """
    art = _articulo(mundo, "ua", mundo.company_a, "HIST-ART")
    maestro = _lista_con_precio(mundo, "ua", mundo.company_a, "HIS", art, "100.0000")
    cli = _cliente(mundo, "ua", mundo.company_a, "HIST-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "HIST-COT", cli)
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1})
    assert r.status_code == 200, r.text
    v1 = maestro["version"]

    # V1 se supera y nace V2, vigente desde hoy, a otro precio.
    assert mundo.post(
        f"/comercial/listas-precio/{maestro['lista']}/versiones/{v1}/transicion",
        "ua", mundo.company_a, {"target": "SUPERSEDED"}).status_code == 200
    r = mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones",
                   "ua", mundo.company_a, {"valid_from": str(HOY)})
    v2 = r.json()["id"]
    mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones/{v2}/items",
               "ua", mundo.company_a, {"item_id": art, "unit_price": "120.0000"})
    assert mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones/{v2}/transicion",
                      "ua", mundo.company_a, {"target": "ACTIVE"}).status_code == 200

    detalle = mundo.get(f"/sales/quotes/{cot}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    linea = detalle.json()["lines"][0]
    assert linea["unit_price"] == "100.0000", "la cotización se recalculó con la lista nueva"
    assert linea["price_source_version_id"] == v1, "perdió el rastro de la versión original"


def test_el_historico_sobrevive_al_archivado_de_su_version(mundo):
    """Archivar la versión no borra la evidencia: la versión no se borra nunca."""
    art = _articulo(mundo, "ua", mundo.company_a, "ARCH-ART")
    maestro = _lista_con_precio(mundo, "ua", mundo.company_a, "ARC", art, "77.0000")
    cli = _cliente(mundo, "ua", mundo.company_a, "ARCH-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "ARCH-COT", cli)
    mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
               {"product_id": art, "quantity": 1})
    assert mundo.post(
        f"/comercial/listas-precio/{maestro['lista']}/versiones/{maestro['version']}/transicion",
        "ua", mundo.company_a, {"target": "ARCHIVED"}).status_code == 200

    detalle = mundo.get(f"/sales/quotes/{cot}", "ua", mundo.company_a).json()
    assert detalle["lines"][0]["unit_price"] == "77.0000"
    assert detalle["lines"][0]["price_source_version_id"] == maestro["version"]


# --------------------------------------------------------------------------- #
# Ciclo de vida y conversión
# --------------------------------------------------------------------------- #
def _cotizacion_lista(mundo, marca, precio="10.0000"):
    art = _articulo(mundo, "ua", mundo.company_a, f"{marca}-ART")
    maestro = _lista_con_precio(mundo, "ua", mundo.company_a, marca, art, precio)
    cli = _cliente(mundo, "ua", mundo.company_a, f"{marca}-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, f"{marca}-COT", cli)
    assert mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                      {"product_id": art, "quantity": 2}).status_code == 200
    return cot, maestro, art


def test_una_cotizacion_enviada_no_admite_lineas(mundo):
    """Enviada, su contenido es lo que el cliente vio."""
    cot, _, art = _cotizacion_lista(mundo, "ENV")
    assert mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a,
                      {"target": "SENT"}).status_code == 200
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art, "quantity": 1})
    assert r.status_code == 409, f"una cotización enviada admitió una línea: {r.status_code}"


def test_solo_se_convierte_una_cotizacion_aceptada(mundo):
    cot, _, _ = _cotizacion_lista(mundo, "ACE")
    r = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    assert r.status_code == 409, "convirtió un borrador"
    assert mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a,
                      {"target": "SENT"}).status_code == 200
    assert mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a,
                      {"target": "ACCEPTED"}).status_code == 200
    r = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    assert r.status_code == 201, r.text


def test_una_cotizacion_vencida_no_se_convierte(mundo):
    art = _articulo(mundo, "ua", mundo.company_a, "VEN-ART")
    _lista_con_precio(mundo, "ua", mundo.company_a, "VEN", art, "9.0000")
    cli = _cliente(mundo, "ua", mundo.company_a, "VEN-CLI")
    cot = mundo.crear("/sales/quotes", "ua", mundo.company_a,
                      {"code": "VEN-COT", "customer_id": cli, "currency": "VED",
                       "validity_until": str(HOY - timedelta(days=1))})
    assert mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                      {"product_id": art, "quantity": 1}).status_code == 200
    r = mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    assert r.status_code == 409, f"envió una cotización vencida: {r.status_code}"
    assert r.json()["code"] == "SALES_QUOTE_EXPIRED"


def test_la_conversion_lleva_la_evidencia_al_pedido(mundo):
    """Lo que se pactó viaja entero. Es el punto de la conversión."""
    cot, maestro, _ = _cotizacion_lista(mundo, "EVI", "33.0000")
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "ACCEPTED"})
    r = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    assert r.status_code == 201, r.text
    pedido = r.json()["id"]

    detalle = mundo.get(f"/sales/orders/{pedido}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    lineas = detalle.json().get("lines") or []
    assert lineas, f"el pedido nació sin líneas: {detalle.json()}"
    assert str(lineas[0].get("unit_price")) == "33.0000"


def test_convertir_dos_veces_no_crea_dos_pedidos(mundo):
    """Un doble clic no es dos pedidos."""
    cot, _, _ = _cotizacion_lista(mundo, "IDE")
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "ACCEPTED"})
    primera = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    segunda = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    assert primera.status_code == 201 and primera.json()["created"] is True
    assert segunda.status_code == 200 and segunda.json()["created"] is False
    assert primera.json()["id"] == segunda.json()["id"], "creó un segundo pedido"


def test_la_conversion_no_reprecia_en_silencio(mundo):
    """Entre la cotización y el pedido puede nacer otra versión.

    El cliente aceptó la anterior. Volver a resolver cambiaría lo pactado sin
    que nadie lo pidiera.
    """
    cot, maestro, art = _cotizacion_lista(mundo, "REP", "60.0000")
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "ACCEPTED"})

    mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones/{maestro['version']}/transicion",
               "ua", mundo.company_a, {"target": "SUPERSEDED"})
    r = mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones",
                   "ua", mundo.company_a, {"valid_from": str(HOY)})
    v2 = r.json()["id"]
    mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones/{v2}/items",
               "ua", mundo.company_a, {"item_id": art, "unit_price": "999.0000"})
    mundo.post(f"/comercial/listas-precio/{maestro['lista']}/versiones/{v2}/transicion",
               "ua", mundo.company_a, {"target": "ACTIVE"})

    pedido = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {}).json()["id"]
    lineas = mundo.get(f"/sales/orders/{pedido}", "ua", mundo.company_a).json().get("lines") or []
    assert str(lineas[0]["unit_price"]) == "60.0000", "reprecio en silencio al convertir"


# --------------------------------------------------------------------------- #
# Multiempresa
# --------------------------------------------------------------------------- #
def test_la_cotizacion_de_otra_empresa_no_se_lee_ni_se_convierte(mundo):
    art = _articulo(mundo, "ub", mundo.company_b, "MC-ART")
    _lista_con_precio(mundo, "ub", mundo.company_b, "MCB", art, "5.0000")
    cli = _cliente(mundo, "ub", mundo.company_b, "MC-CLI")
    cot_b = _cotizacion(mundo, "ub", mundo.company_b, "MC-COT", cli)

    assert mundo.get(f"/sales/quotes/{cot_b}", "ua", mundo.company_a).status_code in BLOQUEO
    r = mundo.post(f"/sales/quotes/{cot_b}/transition", "ua", mundo.company_a, {"target": "SENT"})
    assert r.status_code in BLOQUEO, f"A movió la cotización de B: {r.status_code}"
    r = mundo.post(f"/sales/quotes/{cot_b}/convertir", "ua", mundo.company_a, {})
    assert r.status_code in BLOQUEO, f"A convirtió la cotización de B: {r.status_code}"


def test_el_usuario_con_acceso_a_las_dos_no_cruza_el_contexto(mundo):
    """Tener acceso a B no autoriza sobre B cuando la petición dice A."""
    art = _articulo(mundo, "ub", mundo.company_b, "AB-ART")
    _lista_con_precio(mundo, "ub", mundo.company_b, "MAB", art, "5.0000")
    cli = _cliente(mundo, "ub", mundo.company_b, "AB-CLI")
    cot_b = _cotizacion(mundo, "ub", mundo.company_b, "AB-COT", cli)

    assert mundo.get(f"/sales/quotes/{cot_b}", "uab", mundo.company_a).status_code in BLOQUEO
    assert mundo.get(f"/sales/quotes/{cot_b}", "uab", mundo.company_b).status_code == 200, (
        "uab no pudo leer en B, que sí alcanza: la prueba anterior no probaría la empresa")


def test_no_se_cotiza_un_cliente_de_otra_empresa(mundo):
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CRZ-CLI")
    r = mundo.post("/sales/quotes", "ua", mundo.company_a,
                   {"code": "CRZ-COT", "customer_id": cli_b, "currency": "VED"})
    assert r.status_code in BLOQUEO, f"A cotizó a un cliente de B: {r.status_code}"


def test_la_lista_de_b_no_pone_precio_en_una_cotizacion_de_a(mundo):
    """Mismo código de artículo en las dos, precio solo en B."""
    art_b = _articulo(mundo, "ub", mundo.company_b, "FUG-ART")
    _lista_con_precio(mundo, "ub", mundo.company_b, "FGB", art_b, "888.0000")
    art_a = _articulo(mundo, "ua", mundo.company_a, "FUG-ART")
    cli = _cliente(mundo, "ua", mundo.company_a, "FUG-CLI")
    cot = _cotizacion(mundo, "ua", mundo.company_a, "FUG-COT", cli)
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ua", mundo.company_a,
                   {"product_id": art_a, "quantity": 1})
    assert r.status_code == 422, f"A resolvió con una lista de B: {r.text}"


# --------------------------------------------------------------------------- #
# Lo que 029 NO hace
# --------------------------------------------------------------------------- #
def test_convertir_no_reserva_inventario(mundo):
    """La reserva es de la Spec 030, y `D0-03` sigue sin decidir cuándo.

    Convertir una cotización crea un pedido en `DRAFT`. Nada se reserva ahí.
    """
    from sqlalchemy import text

    cot, _, _ = _cotizacion_lista(mundo, "RSV")
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "ACCEPTED"})

    db = mundo.factory()
    try:
        antes = db.execute(text(
            "SELECT COALESCE(SUM(qty_reserved),0) FROM inventory_balances WHERE company_id = :c"),
            {"c": mundo.company_a}).scalar()
    finally:
        db.close()

    r = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "DRAFT", "el pedido nació fuera de borrador"

    db = mundo.factory()
    try:
        despues = db.execute(text(
            "SELECT COALESCE(SUM(qty_reserved),0) FROM inventory_balances WHERE company_id = :c"),
            {"c": mundo.company_a}).scalar()
    finally:
        db.close()
    assert antes == despues, "convertir reservó inventario: eso es de la Spec 030"


def test_convertir_no_crea_lista_de_preparacion_ni_factura(mundo):
    """Ni picking (031) ni facturación (034) son de esta Spec."""
    from sqlalchemy import text

    cot, _, _ = _cotizacion_lista(mundo, "SEC")
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "SENT"})
    mundo.post(f"/sales/quotes/{cot}/transition", "ua", mundo.company_a, {"target": "ACCEPTED"})
    pedido = mundo.post(f"/sales/quotes/{cot}/convertir", "ua", mundo.company_a, {}).json()["id"]

    db = mundo.factory()
    try:
        picks = db.execute(text("SELECT count(*) FROM pick_lists WHERE company_id = :c"),
                           {"c": mundo.company_a}).scalar()
        facturas = db.execute(text("SELECT count(*) FROM sales_invoices WHERE company_id = :c"),
                              {"c": mundo.company_a}).scalar()
    finally:
        db.close()
    assert picks == 0, "creó una lista de preparación: eso es de la Spec 031"
    assert facturas == 0, "creó una factura: eso es de la Spec 034"
    assert pedido
