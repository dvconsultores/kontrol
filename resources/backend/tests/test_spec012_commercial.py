"""Maestros comerciales sobre dos empresas y dos tenants — Spec 012.

La Spec 012 es la que más rutas hijas tiene de KONTROL: tres niveles bajo
`/listas-precio/{id}`. Es exactamente la forma de los nueve defectos que N10
encontró, así que aquí se ataca por esa forma antes que por ninguna otra.

Cada prueba de bloqueo debe fallar **por la frontera de empresa**. Si fallara
por carga útil inválida, por estado o por autenticación, no probaría lo que
dice: es la lección que N5 dejó escrita y con la que N10 tropezó dos veces.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)

BLOQUEO = (403, 404)
HOY = hoy_de_negocio()


# --------------------------------------------------------------------------- #
# Ayudantes: todo se crea con datos reales de su empresa
# --------------------------------------------------------------------------- #
def _moneda(mundo, usuario, empresa, code):
    return mundo.crear("/treasury/currencies", usuario, empresa,
                       {"code": code, "name": f"Moneda {code}", "symbol": "$"})


def _articulo(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Artículo {code}", "item_type": "PRODUCT"})


def _crear_en_t2(mundo, ruta, cuerpo):
    """El tenant 2 tiene su propio usuario y su propia empresa."""
    r = mundo.post(ruta, "uc", mundo.company_c, cuerpo, tenant="T2")
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _lista(mundo, usuario, empresa, code, moneda):
    return mundo.crear("/comercial/listas-precio", usuario, empresa,
                       {"code": code, "name": f"Lista {code}", "currency_id": moneda})


def _version(mundo, usuario, empresa, lista, desde=None):
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones", usuario, empresa,
                   {"valid_from": str(desde or HOY)})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --------------------------------------------------------------------------- #
# Los catálogos nacen vacíos
# --------------------------------------------------------------------------- #
def test_los_catalogos_nacen_vacios(mundo):
    """`P8`: ningún plazo, zona, canal ni política viene de fábrica."""
    for ruta in ("/comercial/condiciones-pago", "/comercial/zonas", "/comercial/canales",
                 "/comercial/politicas-descuento", "/comercial/politicas-credito",
                 "/comercial/listas-precio"):
        r = mundo.get(ruta, "ua", mundo.company_a)
        assert r.status_code == 200, r.text
        assert r.json()["items"] == [], f"{ruta} no nació vacía: {r.json()}"


# --------------------------------------------------------------------------- #
# Unicidad por empresa: los dos lados
# --------------------------------------------------------------------------- #
def test_el_mismo_codigo_existe_en_dos_empresas(mundo):
    """Dos empresas del mismo grupo usan el mismo código sin colisionar.

    Es la mitad de la comprobación. Sin la otra —el duplicado dentro de A— no
    se sabría si la unicidad es por empresa o si sencillamente no existe.
    """
    assert mundo.post("/comercial/condiciones-pago", "ua", mundo.company_a,
                      {"code": "CONTADO", "name": "Contado", "kind": "CASH"}).status_code == 201
    r = mundo.post("/comercial/condiciones-pago", "ub", mundo.company_b,
                   {"code": "CONTADO", "name": "Contado", "kind": "CASH"})
    assert r.status_code == 201, f"B no pudo usar el mismo código que A: {r.text}"


def test_el_mismo_codigo_repetido_dentro_de_una_empresa_falla(mundo):
    assert mundo.post("/comercial/condiciones-pago", "ua", mundo.company_a,
                      {"code": "DUP-30", "name": "30 días", "kind": "DAYS",
                       "days": 30}).status_code == 201
    r = mundo.post("/comercial/condiciones-pago", "ua", mundo.company_a,
                   {"code": "DUP-30", "name": "Otro", "kind": "DAYS", "days": 30})
    assert r.status_code in (409, 422, 500), f"se aceptó un código duplicado: {r.status_code}"


# --------------------------------------------------------------------------- #
# El ataque por identificador de padre — N-01 a N-09
# --------------------------------------------------------------------------- #
def test_n01_la_version_propia_se_crea(mundo):
    lista = _lista(mundo, "ua", mundo.company_a, "N01", _moneda(mundo, "ua", mundo.company_a, "N01"))
    assert mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                      {"valid_from": str(HOY)}).status_code == 201


def test_n02_no_se_versiona_la_lista_de_otra_empresa(mundo):
    """El caso que N10 encontró nueve veces. La carga útil es válida y de A."""
    lista_b = _lista(mundo, "ub", mundo.company_b, "N02", _moneda(mundo, "ub", mundo.company_b, "N02"))
    r = mundo.post(f"/comercial/listas-precio/{lista_b}/versiones", "ua", mundo.company_a,
                   {"valid_from": str(HOY)})
    assert r.status_code in BLOQUEO, f"A versionó la lista de B: {r.status_code} {r.text}"


def test_n03_no_se_versiona_la_lista_de_otro_tenant(mundo):
    moneda_c = mundo.crear("/treasury/currencies", "uc", mundo.company_c,
                           {"code": "N03", "name": "Moneda N03", "symbol": "$"}) \
        if False else _crear_en_t2(mundo, "/treasury/currencies",
                                   {"code": "N03", "name": "Moneda N03", "symbol": "$"})
    lista_c = _crear_en_t2(mundo, "/comercial/listas-precio",
                           {"code": "N03", "name": "Lista N03", "currency_id": moneda_c})
    r = mundo.client.post(
        f"/api/v1/comercial/listas-precio/{lista_c}/versiones",
        headers=mundo.como("ua", mundo.company_a), json={"valid_from": str(HOY)})
    assert r.status_code in BLOQUEO, f"T1 versionó una lista de T2: {r.status_code} {r.text}"


def test_n06_el_usuario_con_acceso_a_las_dos_no_cruza_el_contexto(mundo):
    """El caso que más se olvida.

    `uab` alcanza A y B. Operando en A, una lista de B sigue estando fuera:
    la autoridad es el contexto de **esta** petición, no el conjunto de lo que
    el usuario podría alcanzar en otra.
    """
    lista_b = _lista(mundo, "ub", mundo.company_b, "N06", _moneda(mundo, "ub", mundo.company_b, "N06"))
    r = mundo.post(f"/comercial/listas-precio/{lista_b}/versiones", "uab", mundo.company_a,
                   {"valid_from": str(HOY)})
    assert r.status_code in BLOQUEO, f"uab en contexto A escribió en la lista de B: {r.text}"

    # Y en contexto B sí puede: si no, la prueba anterior no probaría la empresa.
    r = mundo.post(f"/comercial/listas-precio/{lista_b}/versiones", "uab", mundo.company_b,
                   {"valid_from": str(HOY)})
    assert r.status_code == 201, f"uab no pudo operar en B, que sí alcanza: {r.text}"


def test_n08_una_version_de_otra_lista_no_es_alcanzable(mundo):
    """El eslabón intermedio.

    La lista es legítima y de A; la versión es legítima y de B. Comprobar solo
    el primer eslabón dejaría pasar la escritura.
    """
    moneda_a = _moneda(mundo, "ua", mundo.company_a, "N08A")
    lista_a = _lista(mundo, "ua", mundo.company_a, "N08A", moneda_a)
    lista_b = _lista(mundo, "ub", mundo.company_b, "N08B", _moneda(mundo, "ub", mundo.company_b, "N08B"))
    version_b = _version(mundo, "ub", mundo.company_b, lista_b)
    art_a = _articulo(mundo, "ua", mundo.company_a, "N08-ART")

    r = mundo.post(
        f"/comercial/listas-precio/{lista_a}/versiones/{version_b}/items", "ua", mundo.company_a,
        {"item_id": art_a, "unit_price": "10.0000"})
    assert r.status_code in BLOQUEO, (
        f"se escribió en una versión que cuelga de otra lista: {r.status_code} {r.text}")


def test_los_items_de_otra_empresa_no_se_leen(mundo):
    lista_b = _lista(mundo, "ub", mundo.company_b, "RD", _moneda(mundo, "ub", mundo.company_b, "RD"))
    version_b = _version(mundo, "ub", mundo.company_b, lista_b)
    r = mundo.get(f"/comercial/listas-precio/{lista_b}/versiones/{version_b}/items",
                  "ua", mundo.company_a)
    assert r.status_code in BLOQUEO, f"A leyó los ítems de B: {r.status_code}"


# --------------------------------------------------------------------------- #
# La empresa no viene del cuerpo
# --------------------------------------------------------------------------- #
def test_el_cuerpo_no_puede_declarar_la_empresa(mundo):
    """El esquema es estricto: no lo ignora, lo rechaza.

    Es la vulnerabilidad que la Spec 045 estrenó, y el contrato documental la
    retiró de los dos endpoints de resolución.
    """
    art = _articulo(mundo, "ua", mundo.company_a, "CUERPO")
    r = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a,
                   {"item_id": art, "company_id": mundo.company_b})
    assert r.status_code == 422, f"el cuerpo pudo declarar la empresa: {r.status_code} {r.text}"

    r = mundo.post("/comercial/descuento/validar", "ua", mundo.company_a,
                   {"scope": "LINE", "percent": "5.0", "company_id": mundo.company_b})
    assert r.status_code == 422, f"el cuerpo pudo declarar la empresa: {r.status_code} {r.text}"


def test_un_articulo_de_otra_empresa_no_se_cotiza(mundo):
    art_b = _articulo(mundo, "ub", mundo.company_b, "AJENO")
    r = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art_b})
    assert r.status_code in BLOQUEO, f"A resolvió el precio de un artículo de B: {r.text}"


# --------------------------------------------------------------------------- #
# Referencias entre maestros
# --------------------------------------------------------------------------- #
def test_una_lista_no_usa_la_moneda_de_otra_empresa(mundo):
    moneda_b = _moneda(mundo, "ub", mundo.company_b, "MB")
    r = mundo.post("/comercial/listas-precio", "ua", mundo.company_a,
                   {"code": "MB-CRUZ", "name": "Cruzada", "currency_id": moneda_b})
    assert r.status_code in BLOQUEO, f"A usó una moneda de B: {r.status_code} {r.text}"


def test_una_unidad_de_plataforma_si_se_puede_usar(mundo, unidad_de_plataforma):
    """La excepción que la medición descubrió.

    `units_of_measure.company_id` admite nulo y ese nulo es la unidad de la
    plataforma. Comprobar igualdad estricta la habría rechazado, y habría sido
    un rechazo invisible: la unidad existe y es legítima.
    """
    moneda = _moneda(mundo, "ua", mundo.company_a, "UP")
    lista = _lista(mundo, "ua", mundo.company_a, "UP", moneda)
    version = _version(mundo, "ua", mundo.company_a, lista)
    art = _articulo(mundo, "ua", mundo.company_a, "UP-ART")
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items",
                   "ua", mundo.company_a,
                   {"item_id": art, "uom_id": unidad_de_plataforma, "unit_price": "5.0000"})
    assert r.status_code == 201, f"se rechazó una unidad de plataforma legítima: {r.text}"


# --------------------------------------------------------------------------- #
# Versionado
# --------------------------------------------------------------------------- #
def test_una_version_publicada_no_admite_items(mundo):
    moneda = _moneda(mundo, "ua", mundo.company_a, "PUB")
    lista = _lista(mundo, "ua", mundo.company_a, "PUB", moneda)
    version = _version(mundo, "ua", mundo.company_a, lista)
    art = _articulo(mundo, "ua", mundo.company_a, "PUB-ART")
    assert mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items",
                      "ua", mundo.company_a,
                      {"item_id": art, "unit_price": "7.0000"}).status_code == 201
    assert mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
                      "ua", mundo.company_a, {"target": "ACTIVE"}).status_code == 200
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items",
                   "ua", mundo.company_a, {"item_id": art, "unit_price": "8.0000"})
    assert r.status_code == 409, f"una versión publicada admitió un ítem: {r.status_code}"


def test_publicar_es_irreversible(mundo):
    moneda = _moneda(mundo, "ua", mundo.company_a, "IRR")
    lista = _lista(mundo, "ua", mundo.company_a, "IRR", moneda)
    version = _version(mundo, "ua", mundo.company_a, lista)
    assert mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
                      "ua", mundo.company_a, {"target": "ACTIVE"}).status_code == 200
    r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
                   "ua", mundo.company_a, {"target": "ACTIVE"})
    assert r.status_code == 409, "una versión activa volvió a activarse"


def test_el_numero_de_version_lo_pone_el_servidor(mundo):
    moneda = _moneda(mundo, "ua", mundo.company_a, "NUM")
    lista = _lista(mundo, "ua", mundo.company_a, "NUM", moneda)
    primera = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                         {"valid_from": str(HOY)})
    segunda = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                         {"valid_from": str(HOY + timedelta(days=30))})
    assert primera.json()["version_number"] == 1
    assert segunda.json()["version_number"] == 2


# --------------------------------------------------------------------------- #
# Resolución de precio
# --------------------------------------------------------------------------- #
def test_la_resolucion_devuelve_el_precio_y_su_version(mundo):
    moneda = _moneda(mundo, "ua", mundo.company_a, "RES")
    lista = _lista(mundo, "ua", mundo.company_a, "RES", moneda)
    version = _version(mundo, "ua", mundo.company_a, lista, HOY - timedelta(days=1))
    art = _articulo(mundo, "ua", mundo.company_a, "RES-ART")
    mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items", "ua", mundo.company_a,
               {"item_id": art, "unit_price": "125.4000"})
    mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
               "ua", mundo.company_a, {"target": "ACTIVE"})

    r = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["resolved"] is True
    assert cuerpo["unit_price"] == "125.4000"
    assert cuerpo["price_list_version_id"] == version, "no devolvió la versión que produjo el precio"


def test_la_resolucion_es_determinista(mundo):
    moneda = _moneda(mundo, "ua", mundo.company_a, "DET")
    lista = _lista(mundo, "ua", mundo.company_a, "DET", moneda)
    version = _version(mundo, "ua", mundo.company_a, lista, HOY - timedelta(days=1))
    art = _articulo(mundo, "ua", mundo.company_a, "DET-ART")
    mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/items", "ua", mundo.company_a,
               {"item_id": art, "unit_price": "33.3300"})
    mundo.post(f"/comercial/listas-precio/{lista}/versiones/{version}/transicion",
               "ua", mundo.company_a, {"target": "ACTIVE"})
    uno = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art}).json()
    dos = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art}).json()
    assert uno == dos, f"dos resoluciones idénticas difirieron:\n{uno}\n{dos}"


def test_sin_lista_aplicable_declara_ausencia_y_no_devuelve_cero(mundo):
    """Un cero es un precio. La ausencia de precio no lo es (`FR-012-016`)."""
    art = _articulo(mundo, "ua", mundo.company_a, "SIN-LISTA")
    r = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["resolved"] is False
    assert "unit_price" not in cuerpo, f"inventó un precio: {cuerpo}"


def test_la_lista_de_b_no_participa_en_una_resolucion_de_a(mundo):
    """Mismo código de artículo en las dos empresas, precio solo en B."""
    moneda_b = _moneda(mundo, "ub", mundo.company_b, "FUGA")
    lista_b = _lista(mundo, "ub", mundo.company_b, "FUGA", moneda_b)
    version_b = _version(mundo, "ub", mundo.company_b, lista_b, HOY - timedelta(days=1))
    art_b = _articulo(mundo, "ub", mundo.company_b, "FUGA-ART")
    mundo.post(f"/comercial/listas-precio/{lista_b}/versiones/{version_b}/items",
               "ub", mundo.company_b, {"item_id": art_b, "unit_price": "999.0000"})
    mundo.post(f"/comercial/listas-precio/{lista_b}/versiones/{version_b}/transicion",
               "ub", mundo.company_b, {"target": "ACTIVE"})

    art_a = _articulo(mundo, "ua", mundo.company_a, "FUGA-ART")
    r = mundo.post("/comercial/precio/resolver", "ua", mundo.company_a, {"item_id": art_a})
    assert r.status_code == 200, r.text
    assert r.json()["resolved"] is False, f"A resolvió con una lista de B: {r.json()}"


# --------------------------------------------------------------------------- #
# Precedencia configurable
# --------------------------------------------------------------------------- #
def test_la_precedencia_es_dato_y_cada_empresa_tiene_la_suya(mundo):
    """Si estuviera codificada, A y B no podrían diferir."""
    r = mundo.get("/comercial/precedencia", "ua", mundo.company_a)
    assert r.status_code == 200 and r.json()["configurada"] is False

    puesta = mundo.client.put(
        "/api/v1/comercial/precedencia", headers=mundo.como("ua", mundo.company_a),
        json={"orden": [{"source_kind": "COMPANY_LIST"}, {"source_kind": "CUSTOMER_LIST"}]})
    assert puesta.status_code == 200, puesta.text

    a = mundo.get("/comercial/precedencia", "ua", mundo.company_a).json()
    b = mundo.get("/comercial/precedencia", "ub", mundo.company_b).json()
    assert a["orden"][0] == "COMPANY_LIST" and a["configurada"] is True
    assert b["configurada"] is False, "la precedencia de A se filtró a B"


# --------------------------------------------------------------------------- #
# Descuentos
# --------------------------------------------------------------------------- #
def test_sin_politica_declarada_no_se_inventa_un_limite(mundo):
    r = mundo.post("/comercial/descuento/validar", "ua", mundo.company_a,
                   {"scope": "LINE", "percent": "40.0"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["allowed"] is True and cuerpo["max_percent"] is None
    assert cuerpo["reason"] == "NO_POLICY_DECLARED"


def test_superar_el_limite_pide_aprobacion_y_no_bloquea(mundo):
    """`FR-012-023`: no bloquea, abre solicitud. Y la abre el consumidor."""
    assert mundo.post("/comercial/politicas-descuento", "ua", mundo.company_a,
                      {"code": "LIM", "name": "Límite de línea", "scope": "LINE",
                       "max_percent": "15.0", "requires_approval_above": "10.0"}
                      ).status_code == 201
    bajo = mundo.post("/comercial/descuento/validar", "ua", mundo.company_a,
                      {"scope": "LINE", "percent": "5.0"}).json()
    assert bajo["allowed"] is True and bajo["requires_approval"] is False

    alto = mundo.post("/comercial/descuento/validar", "ua", mundo.company_a,
                      {"scope": "LINE", "percent": "12.0"}).json()
    assert alto["allowed"] is True, "un descuento sobre el umbral se bloqueó en vez de pedir aprobación"
    assert alto["requires_approval"] is True
    assert alto["policy_id"] and alto["policy_version"] == 1


def test_la_politica_de_a_no_se_aplica_en_b(mundo):
    mundo.post("/comercial/politicas-descuento", "ua", mundo.company_a,
               {"code": "SOLO-A", "name": "Solo A", "scope": "DOCUMENT", "max_percent": "1.0"})
    r = mundo.post("/comercial/descuento/validar", "ub", mundo.company_b,
                   {"scope": "DOCUMENT", "percent": "50.0"}).json()
    assert r["max_percent"] is None, f"la política de A alcanzó a B: {r}"


# --------------------------------------------------------------------------- #
# Fixture de la unidad de plataforma
# --------------------------------------------------------------------------- #
@pytest.fixture()
def unidad_de_plataforma(mundo):
    """Una unidad con `company_id` nulo, que es como se representa la de plataforma.

    Se crea por la base y no por la API a propósito: la API de la Spec 011 no
    ofrece crear unidades de plataforma —son de la instalación—, y lo que esta
    prueba necesita comprobar es que la Spec 012 las **acepta**, no cómo nacen.
    """
    import uuid

    from app.modules.master_data.models import UnitOfMeasure

    db = mundo.factory()
    try:
        unidad = UnitOfMeasure(id=str(uuid.uuid4()), company_id=None, code="PLAT-KG",
                               name="Kilogramo de plataforma", symbol="kg", dimension="MASA",
                               decimals=3, rounding_mode="HALF_UP", status="ACTIVE")
        db.add(unidad)
        db.commit()
        return str(unidad.id)
    finally:
        db.close()
