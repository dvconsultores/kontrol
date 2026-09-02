"""Lo que la base impide por sí sola — Spec 012.

No se comprueba lo que el servicio valida, sino lo que PostgreSQL rechaza aunque
el servicio se equivoque. Un modelo puede decir `ForeignKey` y que la columna
sea texto suelto en la base: es exactamente lo que ocurría en 80 tablas antes
de N7.

Se verifica el `SQLSTATE` real, no el mensaje: el mensaje viene traducido y
depende de la configuración regional.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytest_plugins = ("tests.conftest_multicompany",)

HOY = date.today()


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("La integridad estructural se verifica sobre PostgreSQL")


def _sqlstate(exc: Exception) -> str:
    original = getattr(exc, "orig", exc)
    return getattr(original, "pgcode", "") or ""


def _falla_con(mundo, sql: str, params: dict, estado: str, motivo: str) -> None:
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError) as info:
            db.execute(text(sql), params)
            db.flush()
        assert _sqlstate(info.value) == estado, (
            f"{motivo}: se esperaba SQLSTATE {estado} y llegó {_sqlstate(info.value)}")
    finally:
        db.rollback()
        db.close()


def _nodo_de_taxonomia(mundo) -> str:
    """Un nodo real de la empresa A.

    Se siembra en vez de saltar la prueba si no lo hay: un salto ambiental que
    esconde una comprobación se lee igual que un salto legítimo, y N10 encontró
    dieciséis así ocultando la verificación de una fase entera.
    """
    from app.modules.master_data.models import TaxonomyNode

    db = mundo.factory()
    try:
        existente = db.execute(text(
            "SELECT id FROM taxonomy_nodes WHERE company_id = :c LIMIT 1"),
            {"c": mundo.company_a}).scalar()
        if existente:
            return str(existente)
        nodo = TaxonomyNode(id=str(uuid.uuid4()), company_id=mundo.company_a,
                            code=f"CAT-{uuid.uuid4().hex[:6]}", name="Categoría de prueba",
                            level=1, applies_to="ITEM", status="ACTIVE")
        db.add(nodo)
        db.commit()
        return str(nodo.id)
    finally:
        db.close()


def _lista_activa(mundo, empresa="A"):
    """Crea moneda + lista y devuelve sus identificadores, por la API."""
    emp = mundo.company_a if empresa == "A" else mundo.company_b
    usr = "ua" if empresa == "A" else "ub"
    marca = uuid.uuid4().hex[:6]
    moneda = mundo.crear("/treasury/currencies", usr, emp,
                         {"code": f"P{marca[:3]}", "name": "Moneda", "symbol": "$"})
    lista = mundo.crear("/comercial/listas-precio", usr, emp,
                        {"code": f"PG-{marca}", "name": "Lista PG", "currency_id": moneda})
    return moneda, lista


# --------------------------------------------------------------------------- #
# Claves foráneas y obligatoriedad
# --------------------------------------------------------------------------- #
def test_una_empresa_inexistente_no_entra(mundo):
    _pg(mundo)
    _falla_con(mundo, """
        INSERT INTO payment_terms (id, company_id, code, name, status, kind, due_offset_from,
                                   created_at, updated_at)
        VALUES (:id, :company, 'X', 'X', 'ACTIVE', 'CASH', 'ISSUE_DATE', now(), now())
    """, {"id": str(uuid.uuid4()), "company": str(uuid.uuid4())},
        "23503", "la empresa inventada debía violar la clave foránea")


def test_una_condicion_sin_empresa_no_entra(mundo):
    _pg(mundo)
    _falla_con(mundo, """
        INSERT INTO payment_terms (id, company_id, code, name, status, kind, due_offset_from,
                                   created_at, updated_at)
        VALUES (:id, NULL, 'X', 'X', 'ACTIVE', 'CASH', 'ISSUE_DATE', now(), now())
    """, {"id": str(uuid.uuid4())}, "23502", "la empresa nula debía violar NOT NULL")


def test_una_version_sin_lista_no_entra(mundo):
    _pg(mundo)
    _falla_con(mundo, """
        INSERT INTO price_list_versions (id, price_list_id, version_number, valid_from, status,
                                         created_at, updated_at)
        VALUES (:id, NULL, 1, :hoy, 'DRAFT', now(), now())
    """, {"id": str(uuid.uuid4()), "hoy": HOY},
        "23502", "una versión sin lista no tiene por dónde llegar a su empresa")


def test_un_item_con_version_inventada_no_entra(mundo):
    """Con un artículo **real**, para que lo único que falle sea la versión.

    Sin artículo, la restricción de «uno de los dos» salta antes y la prueba
    pasaría sin haber comprobado nunca la clave foránea.
    """
    _pg(mundo)
    art = mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                      {"code": f"FK-{uuid.uuid4().hex[:6]}", "name": "Art",
                       "item_type": "PRODUCT"})
    _falla_con(mundo, """
        INSERT INTO price_list_items (id, version_id, item_id, unit_price, created_at, updated_at)
        VALUES (:id, :version, :art, 1.0, now(), now())
    """, {"id": str(uuid.uuid4()), "version": str(uuid.uuid4()), "art": art},
        "23503", "la versión inventada debía violar la clave foránea")


# --------------------------------------------------------------------------- #
# Artículo o categoría, nunca ambos ni ninguno
# --------------------------------------------------------------------------- #
def test_un_item_sin_articulo_ni_categoria_no_entra(mundo):
    _pg(mundo)
    _, lista = _lista_activa(mundo)
    version = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                         {"valid_from": str(HOY)}).json()["id"]
    _falla_con(mundo, """
        INSERT INTO price_list_items (id, version_id, item_id, category_id, unit_price,
                                      created_at, updated_at)
        VALUES (:id, :version, NULL, NULL, 1.0, now(), now())
    """, {"id": str(uuid.uuid4()), "version": version},
        "23514", "sin artículo ni categoría el ítem no dice a qué pone precio")


def test_un_item_con_articulo_y_categoria_no_entra(mundo):
    _pg(mundo)
    _, lista = _lista_activa(mundo)
    version = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                         {"valid_from": str(HOY)}).json()["id"]
    art = mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                      {"code": f"AC-{uuid.uuid4().hex[:6]}", "name": "Art", "item_type": "PRODUCT"})
    nodo = _nodo_de_taxonomia(mundo)
    _falla_con(mundo, """
        INSERT INTO price_list_items (id, version_id, item_id, category_id, unit_price,
                                      created_at, updated_at)
        VALUES (:id, :version, :art, :cat, 1.0, now(), now())
    """, {"id": str(uuid.uuid4()), "version": version, "art": art, "cat": nodo},
        "23514", "artículo y categoría a la vez es ambiguo")


# --------------------------------------------------------------------------- #
# Solape de vigencias
# --------------------------------------------------------------------------- #
def test_dos_versiones_activas_no_solapan(mundo):
    """`FR-012-005`, y en la base, no en el servicio.

    Una comprobación en Python pierde ante dos peticiones simultáneas. La
    Spec 046 ya enseñó que dos subidas concurrentes producen dos versiones si
    nada en la base lo impide.
    """
    _pg(mundo)
    _, lista = _lista_activa(mundo)
    for desde in (HOY - timedelta(days=10), HOY - timedelta(days=5)):
        v = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                       {"valid_from": str(desde)}).json()["id"]
        r = mundo.post(f"/comercial/listas-precio/{lista}/versiones/{v}/transicion",
                       "ua", mundo.company_a, {"target": "ACTIVE"})
        if desde == HOY - timedelta(days=10):
            assert r.status_code == 200, r.text
        else:
            assert r.status_code in (409, 500), (
                f"dos versiones activas solaparon: {r.status_code} {r.text}")


def test_dos_borradores_si_pueden_solapar(mundo):
    """El `WHERE status = 'ACTIVE'` de la exclusión es esencial.

    Sin él, dos borradores en paralelo —que son legítimos— quedarían
    prohibidos, y la restricción impediría trabajar en vez de proteger.
    """
    _pg(mundo)
    _, lista = _lista_activa(mundo)
    for desde in (HOY, HOY):
        r = mundo.post(f"/comercial/listas-precio/{lista}/versiones", "ua", mundo.company_a,
                       {"valid_from": str(desde)})
        assert r.status_code == 201, f"un borrador solapado se rechazó: {r.text}"


# --------------------------------------------------------------------------- #
# Unicidad por empresa, en el catálogo
# --------------------------------------------------------------------------- #
def test_el_catalogo_declara_la_unicidad_por_empresa(mundo):
    _pg(mundo)
    db = mundo.factory()
    try:
        filas = db.execute(text("""
            SELECT t.relname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
            WHERE c.contype = 'u' AND t.relname IN
              ('payment_terms','commercial_zones','sales_channels','price_lists',
               'price_precedence','discount_policies','credit_policies',
               'sales_commission_policies')
        """)).all()
    finally:
        db.close()
    sin_empresa = [f"{t}: {d}" for t, d in filas if "company_id" not in d]
    assert sin_empresa == [], (
        "maestros de empresa con unicidad que no la incluye:\n  " + "\n  ".join(sin_empresa))


def test_las_derivadas_no_llevan_empresa(mundo):
    """Duplicarla daría dos respuestas a la misma pregunta, y pueden discrepar."""
    _pg(mundo)
    db = mundo.factory()
    try:
        con_empresa = db.execute(text("""
            SELECT table_name FROM information_schema.columns
            WHERE table_schema = current_schema() AND column_name = 'company_id'
              AND table_name IN ('price_list_versions','price_list_items',
                                 'customer_commercial_terms')
        """)).scalars().all()
    finally:
        db.close()
    assert list(con_empresa) == [], f"derivadas con company_id redundante: {con_empresa}"


def test_ningun_importe_es_de_coma_flotante(mundo):
    """`NFR-012-06`. La Spec 011 dejó cara esta lección."""
    _pg(mundo)
    db = mundo.factory()
    try:
        flotantes = db.execute(text("""
            SELECT table_name || '.' || column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name IN ('price_list_items','discount_policies','credit_policies',
                                 'payment_terms')
              AND data_type IN ('double precision','real')
        """)).all()
    finally:
        db.close()
    assert list(flotantes) == [], f"importes en coma flotante: {flotantes}"
