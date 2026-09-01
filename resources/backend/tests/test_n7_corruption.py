"""Lo que PostgreSQL rechaza por sí solo (ARCH-MC-001, fase N7).

N5 hizo que el sistema se comporte bien con dos empresas y N6 que el frontend
opere sobre ese comportamiento. Las dos protecciones viven en código: una
consulta nueva, un trabajo de fondo, un script de importación o un `INSERT` a
mano las esquivan enteras.

Aquí no se prueba la aplicación. Se abre una conexión y se intenta escribir
basura directamente, para ver si la base la acepta. Cada prueba comprueba el
`SQLSTATE` concreto: que una inserción falle no significa nada si falla por una
columna mal escrita en vez de por la invariante que se quería demostrar.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytest_plugins = ("tests.conftest_multicompany",)

#: Códigos de PostgreSQL. Comprobarlos es lo que distingue «falló» de
#: «falló por lo que dijimos».
FK_VIOLADA = "23503"
NULO_VIOLADO = "23502"
UNICIDAD_VIOLADA = "23505"


def _sqlstate(exc: DBAPIError) -> str | None:
    return getattr(exc.orig, "pgcode", None)


def _falla_con(mundo, sql: str, params: dict, esperado: str, motivo: str) -> None:
    """Ejecuta SQL crudo y exige que falle con el código exacto."""
    db = mundo.factory()
    try:
        with pytest.raises(DBAPIError) as capturado:
            db.execute(text(sql), params)
            db.commit()
        estado = _sqlstate(capturado.value)
        assert estado == esperado, (
            f"{motivo}: se esperaba {esperado} y llegó {estado} — "
            f"la inserción falló por otra causa, así que no demuestra nada: "
            f"{capturado.value.orig}")
    finally:
        db.rollback()
        db.close()


def _acepta(mundo, sql: str, params: dict, motivo: str) -> None:
    db = mundo.factory()
    try:
        db.execute(text(sql), params)
        db.commit()
    except DBAPIError as exc:  # pragma: no cover - solo se ejecuta si falla
        pytest.fail(f"{motivo}: la base rechazó una operación válida "
                    f"({_sqlstate(exc)}) — {exc.orig}")
    finally:
        db.close()


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("Las restricciones estructurales se verifican sobre PostgreSQL")


INSERT_TERCERO = (
    "INSERT INTO parties (id, company_id, code, name, person_type, roles, status) "
    "VALUES (:id, :c, :code, :name, 'JURIDICA', '[]', 'ACTIVE')"
)


# ------------------------------------------------- la empresa como referencia
def test_el_tenant_no_se_puede_escribir_como_empresa(mundo):
    """El defecto de origen de KONTROL, intentado a mano.

    Durante toda la vida del proyecto `company_id` guardó el identificador del
    tenant. N5 corrigió el código; esto comprueba que la base ya no lo admita
    aunque el código se equivoque.
    """
    _pg(mundo)
    _falla_con(mundo, INSERT_TERCERO,
               {"id": str(uuid.uuid4()), "c": mundo.t1, "code": "N7-TENANT", "name": "x"},
               FK_VIOLADA, "se escribió un tenant en company_id")


def test_una_empresa_inexistente_se_rechaza(mundo):
    _pg(mundo)
    _falla_con(mundo, INSERT_TERCERO,
               {"id": str(uuid.uuid4()), "c": str(uuid.uuid4()), "code": "N7-FANTASMA", "name": "x"},
               FK_VIOLADA, "se aceptó una empresa que no existe")


def test_la_empresa_de_otro_tenant_es_una_empresa_real(mundo):
    """Matiz que conviene dejar escrito.

    Una empresa de otro tenant **sí** existe, así que la clave foránea la acepta:
    la base no sabe quién puede operar dónde. Eso lo decide el contexto de
    empresa, y su prueba está en la suite de aislamiento.

    N7 impide escribir algo que no es una empresa. No sustituye a N5.
    """
    _pg(mundo)
    _acepta(mundo, INSERT_TERCERO,
            {"id": str(uuid.uuid4()), "c": mundo.company_c, "code": "N7-CRUZADO", "name": "x"},
            "la empresa C existe y la referencia es válida")


def test_la_empresa_no_puede_faltar(mundo):
    _pg(mundo)
    _falla_con(mundo, INSERT_TERCERO,
               {"id": str(uuid.uuid4()), "c": None, "code": "N7-SIN", "name": "x"},
               NULO_VIOLADO, "se aceptó un tercero sin empresa")


# ------------------------------------------------- unicidad por empresa
def test_la_misma_clave_vale_en_dos_empresas(mundo):
    """§28: lo que el negocio permite, la base no debe impedirlo.

    Dos empresas pueden tener un almacén con el mismo código. Si la unicidad
    fuera global, la segunda empresa no podría usar su propia codificación.
    """
    _pg(mundo)
    sql = ("INSERT INTO warehouses (id, company_id, code, name, warehouse_type, status) "
           "VALUES (:id, :c, :code, :name, 'PHYSICAL', 'ACTIVE')")
    for empresa in (mundo.company_a, mundo.company_b):
        _acepta(mundo, sql, {"id": str(uuid.uuid4()), "c": empresa,
                             "code": "N7-COMPARTIDO", "name": "Almacén"},
                "el mismo código en otra empresa debería aceptarse")


def test_la_misma_clave_no_se_repite_dentro_de_una_empresa(mundo):
    _pg(mundo)
    sql = ("INSERT INTO warehouses (id, company_id, code, name, warehouse_type, status) "
           "VALUES (:id, :c, :code, :name, 'PHYSICAL', 'ACTIVE')")
    _acepta(mundo, sql, {"id": str(uuid.uuid4()), "c": mundo.company_a,
                         "code": "N7-UNICO", "name": "Primero"}, "el primero debe entrar")
    _falla_con(mundo, sql, {"id": str(uuid.uuid4()), "c": mundo.company_a,
                            "code": "N7-UNICO", "name": "Duplicado"},
               UNICIDAD_VIOLADA, "se duplicó un código dentro de la misma empresa")


# ------------------------------------------------- coherencia empresa/almacén
def test_una_zona_no_puede_colgar_del_almacen_de_otra_empresa(mundo):
    """El par que antes podía contradecirse.

    `company_id` y `warehouse_id` eran dos referencias válidas por separado.
    Ninguna estaba mal; lo que estaba mal era la combinación.
    """
    _pg(mundo)
    db = mundo.factory()
    try:
        tipo = db.execute(text(
            "SELECT id FROM zone_types WHERE company_id = :c LIMIT 1"),
            {"c": mundo.company_a}).scalar()
    finally:
        db.close()

    sql = ("INSERT INTO warehouse_zones (id, company_id, warehouse_id, code, name, status) "
           "VALUES (:id, :c, :w, :code, :name, 'ACTIVE')")
    params = {"id": str(uuid.uuid4()), "c": mundo.company_a, "w": mundo.warehouse_b,
              "code": "N7-ZONA-CRUZADA", "name": "Cruzada"}
    assert tipo is None or tipo
    _falla_con(mundo, sql, params, FK_VIOLADA,
               "una zona de A colgó de un almacén de B")


def test_la_zona_en_su_propio_almacen_sigue_funcionando(mundo):
    """Sin esto, el bloqueo anterior podría deberse a que nada funciona."""
    _pg(mundo)
    _acepta(mundo, ("INSERT INTO warehouse_zones (id, company_id, warehouse_id, code, name, status) "
                    "VALUES (:id, :c, :w, :code, :name, 'ACTIVE')"),
            {"id": str(uuid.uuid4()), "c": mundo.company_a, "w": mundo.warehouse_a,
             "code": "N7-ZONA-OK", "name": "Propia"},
            "la zona en su propio almacén debería aceptarse")


# ------------------------------------------------- fiscal
def test_una_serie_fiscal_no_pertenece_a_una_empresa_inventada(mundo):
    """Fiscal es donde una empresa equivocada deja de ser un problema de software.

    Cada empresa es un contribuyente distinto: su serie de numeración está
    autorizada a un RIF concreto.
    """
    _pg(mundo)
    _falla_con(mundo,
               ("INSERT INTO fiscal_number_series (id, company_id, document_type, next_number, lock_version) "
                "VALUES (:id, :c, 'INVOICE', 1, 0)"),
               {"id": str(uuid.uuid4()), "c": str(uuid.uuid4())},
               FK_VIOLADA, "una serie fiscal quedó bajo una empresa inexistente")


def test_un_documento_fiscal_no_pertenece_al_tenant(mundo):
    _pg(mundo)
    _falla_con(mundo,
               ("INSERT INTO fiscal_documents (id, company_id, business_document, document_type, "
                " fiscal_mode, invoice_number, control_number, fiscal_currency, status) "
                "VALUES (:id, :c, 'INVOICE:x', 'INVOICE', 'DIGITAL', '1', '1', 'VED', 'EMITTED')"),
               {"id": str(uuid.uuid4()), "c": mundo.t1},
               FK_VIOLADA, "un documento fiscal quedó bajo el tenant")


# ------------------------------------------------- financiero e inventario
def test_un_pago_no_pertenece_a_una_empresa_inexistente(mundo):
    _pg(mundo)
    # El tercero se siembra aquí: saltarse la prueba por falta de datos la
    # dejaría sin comprobar nada y contando como verde.
    tercero = str(uuid.uuid4())
    _acepta(mundo, INSERT_TERCERO,
            {"id": tercero, "c": mundo.company_a, "code": f"N7-PAGO-{tercero[:8]}",
             "name": "Proveedor"}, "sembrar el tercero de la empresa A")

    _falla_con(mundo,
               ("INSERT INTO ap_payments (id, company_id, party_id, direction, currency, amount, applied, status) "
                "VALUES (:id, :c, :p, 'OUT', 'VED', 10, 0, 'DRAFT')"),
               {"id": str(uuid.uuid4()), "c": str(uuid.uuid4()), "p": tercero},
               FK_VIOLADA, "un pago quedó bajo una empresa inexistente")


def test_un_movimiento_de_inventario_no_pertenece_al_tenant(mundo):
    _pg(mundo)
    _falla_con(mundo,
               ("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
                " movement_type_id, quantity, occurred_at, currency, status) "
                "VALUES (:id, :c, :w, :p, :m, 1, now(), 'VED', 'POSTED')"),
               {"id": str(uuid.uuid4()), "c": mundo.t1, "w": mundo.warehouse_a,
                "p": str(uuid.uuid4()), "m": str(uuid.uuid4())},
               FK_VIOLADA, "un movimiento quedó bajo el tenant")
