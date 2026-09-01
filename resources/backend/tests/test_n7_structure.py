"""Invariantes estructurales sobre el catálogo real (ARCH-MC-001, fase N7).

No se comprueba lo que el ORM declara, sino lo que PostgreSQL tiene. Un modelo
puede decir `ForeignKey` y que la columna sea texto suelto en la base: es
exactamente lo que ocurría en 80 tablas antes de esta fase.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope, scope_authority

pytest_plugins = ("tests.conftest_multicompany",)


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("La integridad estructural se verifica sobre PostgreSQL")


def _catalogo(mundo) -> dict:
    """Claves foráneas, unicidad y obligatoriedad tal como están en la base."""
    db = mundo.factory()
    try:
        fks = {
            (t, c): destino
            for t, c, destino in db.execute(text("""
                SELECT con.conrelid::regclass::text, a.attname, con.confrelid::regclass::text
                FROM pg_constraint con
                JOIN unnest(con.conkey) WITH ORDINALITY k(attnum, ord) ON true
                JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
                WHERE con.contype = 'f' AND con.connamespace = current_schema()::regnamespace
            """))
        }
        nulables = {
            (t, c): (n == "YES")
            for t, c, n in db.execute(text("""
                SELECT table_name, column_name, is_nullable FROM information_schema.columns
                WHERE table_schema = current_schema()
            """))
        }
        existentes = {
            r[0] for r in db.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"))
        }
    finally:
        db.close()
    return {"fks": fks, "nulables": nulables, "tablas": existentes}


def _modelos():
    init_models()
    return [m.class_ for m in Base.registry.mappers]


# ------------------------------------------------- alcance declarado
def test_ningun_modelo_se_queda_sin_declarar_su_alcance(mundo):
    """Sin alcance declarado, ninguna de las pruebas de abajo puede mirarlo.

    N0 dio cero sin declarar sobre 153 modelos, pero los de organización
    quedaron fuera de aquel recuento: `warehouses`, `branches` y las cinco de
    estructura de almacén no lo tenían, precisamente las que N7 usa de modelo.
    """
    sin = [t for c in _modelos()
           if (t := getattr(c, "__tablename__", None)) and declared_scope(c) is None]
    assert sin == [], f"modelos sin alcance declarado: {sin}"


# ------------------------------------------------- FR-N7-001
def test_toda_empresa_directa_referencia_a_companies(mundo):
    _pg(mundo)
    cat = _catalogo(mundo)
    faltan = []
    for cls in _modelos():
        t = getattr(cls, "__tablename__", None)
        if not t or t not in cat["tablas"] or declared_scope(cls) is not Scope.COMPANY:
            continue
        if (t, "company_id") not in cat["nulables"]:
            continue
        destino = cat["fks"].get((t, "company_id"))
        if destino != "companies":
            faltan.append((t, destino or "sin clave foránea"))
    assert faltan == [], (
        "tablas de empresa cuyo company_id no referencia a companies:\n  "
        + "\n  ".join(f"{t}: {d}" for t, d in faltan))


def test_ninguna_columna_de_empresa_queda_sin_referencia(mundo):
    """FR-N7-006 se aplica a **toda** columna `company_id`, no solo a las de
    tablas de empresa.

    Nueve tablas de alcance tenant la llevan como estrechamiento opcional: un
    rol puede valer en todo el tenant o solo en una empresa. Que admita nulo no
    la exime de referenciar a alguien real — una empresa nula significa «todas»,
    una empresa inventada no significa nada.

    La primera versión de esta fase las dejó fuera porque clasificó por alcance
    del modelo, y estas son de tenant.
    """
    _pg(mundo)
    cat = _catalogo(mundo)
    sin_referencia = sorted(
        t for (t, c) in cat["nulables"]
        if c == "company_id" and t in cat["tablas"] and (t, "company_id") not in cat["fks"])
    assert sin_referencia == [], (
        f"columnas company_id sin clave foránea: {sin_referencia}")


# ------------------------------------------------- FR-N7-002
def test_todo_tenant_referencia_a_tenants(mundo):
    _pg(mundo)
    cat = _catalogo(mundo)
    faltan = []
    for cls in _modelos():
        t = getattr(cls, "__tablename__", None)
        if not t or t not in cat["tablas"]:
            continue
        if (t, "tenant_id") not in cat["nulables"]:
            continue
        destino = cat["fks"].get((t, "tenant_id"))
        if destino != "tenants":
            faltan.append((t, destino or "sin clave foránea"))
    assert faltan == [], (
        "tablas cuyo tenant_id no referencia a tenants:\n  "
        + "\n  ".join(f"{t}: {d}" for t, d in faltan))


# ------------------------------------------------- FR-N7-004 / 005
def test_toda_ruta_derivada_llega_a_su_autoridad(mundo):
    """Una ruta que puede ser nula no es una ruta.

    Las 35 derivadas ya estaban sanas antes de N7 —N3 las creó con clave real y
    obligatoria— y esta prueba existe para que sigan estándolo.
    """
    _pg(mundo)
    cat = _catalogo(mundo)
    problemas = []
    total = 0
    for cls in _modelos():
        t = getattr(cls, "__tablename__", None)
        if not t or t not in cat["tablas"] or declared_scope(cls) is not Scope.COMPANY:
            continue
        if (t, "company_id") in cat["nulables"]:
            continue  # es directa, no derivada
        total += 1
        autoridad = scope_authority(cls)
        if not autoridad:
            problemas.append((t, "sin autoridad declarada"))
            continue
        col = autoridad.split("→")[0].split("->")[0].strip()
        if (t, col) not in cat["nulables"]:
            problemas.append((t, f"la columna {col} no existe"))
            continue
        if cat["nulables"][(t, col)]:
            problemas.append((t, f"{col} es anulable"))
        if (t, col) not in cat["fks"]:
            problemas.append((t, f"{col} no tiene clave foránea"))
    assert total > 30, f"solo se revisaron {total} rutas derivadas: el barrido es incompleto"
    assert problemas == [], (
        "rutas derivadas rotas:\n  " + "\n  ".join(f"{t}: {p}" for t, p in problemas))


# ------------------------------------------------- FR-N7-029
def test_la_empresa_solo_es_opcional_donde_esta_justificado(mundo):
    """Dos excepciones, ambas con razón escrita.

    Cada excepción tiene su razón escrita: Spec 011 distinguió unidades del
    sistema de las de negocio; un archivo existe antes de saber a qué documento
    pertenecerá; y los tipos de movimiento y perfiles de costo exponen
    `global_scope` en su API, un interruptor cuyo valor **es** el nulo.

    La lista es corta y explícita a propósito: si crece sin justificación, esta
    prueba deja de significar nada.
    """
    _pg(mundo)
    cat = _catalogo(mundo)
    permitidas = {
        "units_of_measure",   # Spec 011: las del sistema son globales
        "stored_files",       # el archivo existe antes que su documento
        "movement_types",     # su API expone `global_scope`
        "costing_profiles",   # ídem
        "audit_events", "outbox_events",
    }
    anulables = []
    for cls in _modelos():
        t = getattr(cls, "__tablename__", None)
        if not t or t not in cat["tablas"] or declared_scope(cls) is not Scope.COMPANY:
            continue
        if cat["nulables"].get((t, "company_id")) and t not in permitidas:
            anulables.append(t)
    assert anulables == [], f"empresa opcional sin justificar: {anulables}"


# ------------------------------------------------- NFR-N7-004
def test_el_orm_y_la_base_dicen_lo_mismo(mundo):
    """La paridad que hace falta para que estas pruebas signifiquen algo.

    Durante esta fase se descubrió que las claves foráneas añadidas por
    migración no existían en el ORM. Como la base de pruebas nace de
    `create_all`, las pruebas de corrupción pasaban «bien» sin comprobar nada:
    el esquema que interrogaban no tenía las restricciones.
    """
    _pg(mundo)
    cat = _catalogo(mundo)
    init_models()
    desajustes = []
    for nombre, tabla in Base.metadata.tables.items():
        if nombre not in cat["tablas"]:
            continue
        for col in tabla.columns:
            if col.name not in ("company_id", "tenant_id"):
                continue
            declara = any(fk.column.table.name in ("companies", "tenants")
                          for fk in col.foreign_keys)
            tiene = (nombre, col.name) in cat["fks"]
            if declara != tiene:
                desajustes.append(f"{nombre}.{col.name}: ORM={declara} base={tiene}")
    assert desajustes == [], "el ORM y la base no coinciden:\n  " + "\n  ".join(desajustes)
