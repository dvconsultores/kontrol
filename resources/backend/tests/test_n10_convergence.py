"""Invariantes globales de la convergencia (ARCH-MC-001, fase N10).

N10 no añade capacidades: comprueba que las diez fases anteriores describen un
solo sistema. Estas pruebas fijan lo que la medición encontró roto, para que la
diferencia entre lo que KONTROL declara y lo que hace no pueda reabrirse.
"""

from __future__ import annotations

import os
import pathlib

import pytest
from sqlalchemy import inspect

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope, scope_authority

pytest_plugins = ("tests.conftest_multicompany",)


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("La paridad con el catálogo se verifica sobre PostgreSQL")


def _modelos():
    init_models()
    return [m.class_ for m in Base.registry.mappers]


# --------------------------------------------------------------------------
def test_toda_tabla_de_tenant_dice_por_donde_llega_a_su_tenant():
    """La simetría que faltaba.

    El contrato de `scope.py` obliga a declarar la ruta a quien no lleva columna
    de ámbito, y la prueba que lo exigía solo miraba el alcance de empresa. Ocho
    modelos de tenant no tenían ni `tenant_id` ni ruta declarada: su alcance
    estaba clasificado pero era imposible de verificar, que es otra forma de no
    estar clasificado.

    De los ocho, cuatro llegan por su usuario y lo declaran. Los otros cuatro no
    llegaban a ningún tenant porque no eran de tenant, y se reclasificaron.
    """
    malos = []
    for m in _modelos():
        if declared_scope(m) is not Scope.TENANT:
            continue
        if "tenant_id" in m.__table__.c or scope_authority(m):
            continue
        malos.append(m.__tablename__)
    assert malos == [], f"de tenant, sin columna ni ruta declarada: {malos}"


def test_la_empresa_opcional_siempre_referencia_a_companies():
    """Un nulo significa «todas»; una empresa inventada no significa nada.

    La versión de N7 solo miraba las tablas de tenant. Al reclasificar tres a
    `INSTALLATION` habrían salido de la comprobación sin dejar de llevar
    `company_id`: la regla es del estrechamiento, no del alcance que lo usa.
    """
    problemas = []
    for m in _modelos():
        col = m.__table__.c.get("company_id")
        if col is None or declared_scope(m) is Scope.COMPANY:
            continue
        if not col.nullable:
            problemas.append(f"{m.__tablename__}: obligatoria sin ser de empresa")
        if {f.column.table.name for f in col.foreign_keys} != {"companies"}:
            problemas.append(f"{m.__tablename__}: sin referencia a companies")
    assert problemas == [], "\n  ".join(["estrechamientos mal declarados:", *problemas])


def test_el_tenant_opcional_siempre_referencia_a_tenants():
    """Lo mismo un nivel más arriba: `system_settings` acota por tenant."""
    problemas = []
    for m in _modelos():
        col = m.__table__.c.get("tenant_id")
        if col is None or declared_scope(m) is Scope.TENANT:
            continue
        if {f.column.table.name for f in col.foreign_keys} != {"tenants"}:
            problemas.append(f"{m.__tablename__}: sin referencia a tenants")
    assert problemas == [], "\n  ".join(["estrechamientos por tenant mal declarados:", *problemas])


# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def base_migrada():
    """Una base **construida por Alembic**, no por el ORM.

    Es la única forma de que esta prueba signifique algo. El resto de las suites
    levanta el esquema con `create_all`, es decir, desde el propio ORM: comparar
    el ORM con eso sería preguntarle a alguien si está de acuerdo consigo mismo.
    Es la misma trampa que N7 encontró en las pruebas de corrupción.
    """
    url = os.environ.get("KONTROL_TEST_DB_URL", "")
    if "postgresql" not in url:
        pytest.skip("La paridad con el catálogo se verifica sobre PostgreSQL")

    from sqlalchemy import create_engine, text

    from alembic import command
    from alembic.config import Config

    raiz = pathlib.Path(__file__).resolve().parents[1]
    base, _, nombre = url.rpartition("/")
    destino = f"{nombre}_n10par"
    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as cx:
        cx.execute(text(f'DROP DATABASE IF EXISTS "{destino}"'))
        cx.execute(text(f'CREATE DATABASE "{destino}" ENCODING \'UTF8\''))
        cx.execute(text(f"ALTER DATABASE \"{destino}\" SET timezone TO 'UTC'"))
    url_destino = f"{base}/{destino}"

    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url_destino)
    anterior = os.environ.get("KONTROL_DB_URL")
    os.environ["KONTROL_DB_URL"] = url_destino
    try:
        command.upgrade(cfg, "head")
        motor = create_engine(url_destino)
        yield motor
        motor.dispose()
    finally:
        if anterior is None:
            os.environ.pop("KONTROL_DB_URL", None)
        else:
            os.environ["KONTROL_DB_URL"] = anterior
        with admin.connect() as cx:
            cx.execute(text(f'DROP DATABASE IF EXISTS "{destino}"'))
        admin.dispose()


def test_el_orm_y_la_base_no_difieren_en_nada(base_migrada):
    """Paridad completa, no solo la de las columnas de ámbito.

    La prueba de N7 comparaba las claves foráneas de `company_id` y `tenant_id`.
    Con ese alcance no podía ver lo que N10 encontró: cinco tablas con una
    columna `tenant_id` **en la base y no en el ORM**, resto de una expansión de
    N3 cuya clasificación N7 corrigió y cuya contracción nadie ejecutó. Columnas
    con clave foránea real, vacías, que ningún código escribía ni leía.

    Aquí se comparan tablas, columnas, obligatoriedad y claves foráneas, en las
    dos direcciones, contra el esquema que producen las migraciones.
    """
    init_models()
    insp = inspect(base_migrada)
    todas = set(insp.get_table_names())
    # Sin esto, un fixture que cayera de vuelta a `create_all` haría pasar la
    # prueba sin comparar nada contra las migraciones.
    assert "alembic_version" in todas, "el esquema no lo construyó Alembic"
    base = todas - {"alembic_version"}
    orm = set(Base.metadata.tables)
    assert orm == base, (
        f"solo en el ORM: {sorted(orm - base)} · solo en la base: {sorted(base - orm)}")

    desajustes: list[str] = []
    for nombre in sorted(orm):
        tabla = Base.metadata.tables[nombre]
        columnas = {c["name"]: c for c in insp.get_columns(nombre)}
        faltan = set(tabla.columns.keys()) - set(columnas)
        sobran = set(columnas) - set(tabla.columns.keys())
        if faltan:
            desajustes.append(f"{nombre}: en el ORM y no en la base {sorted(faltan)}")
        if sobran:
            desajustes.append(f"{nombre}: en la base y no en el ORM {sorted(sobran)}")
        for n, col in tabla.columns.items():
            if n in columnas and bool(col.nullable) != bool(columnas[n]["nullable"]):
                desajustes.append(
                    f"{nombre}.{n}: anulable en el ORM={col.nullable}, en la base={columnas[n]['nullable']}")
        del_orm = {(tuple(k.column_keys), list(k.elements)[0].column.table.name)
                   for k in tabla.foreign_key_constraints}
        de_base = {(tuple(f["constrained_columns"]), f["referred_table"])
                   for f in insp.get_foreign_keys(nombre)}
        if del_orm - de_base:
            desajustes.append(f"{nombre}: clave foránea solo en el ORM {sorted(del_orm - de_base)}")
        if de_base - del_orm:
            desajustes.append(f"{nombre}: clave foránea solo en la base {sorted(de_base - del_orm)}")
    assert desajustes == [], "el ORM y la base no dicen lo mismo:\n  " + "\n  ".join(desajustes)


# --------------------------------------------------------------------------
def test_ninguna_operacion_de_la_api_queda_sin_alcance(mundo):
    """Toda operación declara la empresa o pertenece a un módulo que no la usa.

    No se comprueba un número —los números envejecen— sino que no exista una
    operación de un módulo de empresa que calle sobre ella.
    """
    from app.core.company_context import COMPANY_HEADER

    #: Prefijos cuyo alcance no es de empresa, con el motivo.
    SIN_EMPRESA = {
        "/api/v1/auth": "sesión: precede a cualquier empresa",
        "/api/v1/users": "tenant: la identidad es del tenant",
        "/api/v1/roles": "instalación: el catálogo de roles es uno",
        "/api/v1/setup": "instalación: crea el tenant y la primera empresa",
        "/api/v1/health": "instalación: sonda",
        "/api/v1/system": "instalación",
        "/api/v1/license": "instalación",
        "/api/v1/licensing": "instalación",
        "/api/v1/homologation": "instalación: versión fiscal homologada",
        "/api/v1/organization": "tenant e instalación: el selector precede al contexto",
        "/api/v1/audit": "tenant: la bitácora se consulta por tenant",
    }
    #: Operaciones sueltas de módulos de empresa que legítimamente no la llevan.
    EXCEPCIONES = {
        ("/api/v1/fiscal/legal-sources", "get"),
        ("/api/v1/fiscal/legal-sources", "post"),
        ("/api/v1/fiscal/legal-sources/{source_id}/activate", "post"),
        ("/api/v1/fiscal/tax-rule-versions", "get"),
        ("/api/v1/fiscal/tax-rule-versions", "post"),
        ("/api/v1/fiscal/tax-rule-versions/{rule_id}/approve", "post"),
        ("/api/v1/approvals/process-types", "get"),
        ("/api/v1/approvals/requests/{request_id}/cancel", "post"),
        ("/api/v1/approvals/steps/{step_id}/approve", "post"),
        ("/api/v1/approvals/steps/{step_id}/reject", "post"),
        ("/api/v1/approvals/steps/{step_id}/return", "post"),
        ("/api/v1/documentos/salud/almacenamiento", "get"),
        ("/api/v1/gobierno/modulo", "get"),  # instalación: ¿la licencia habilita Gobierno? (GOV-0-01)
        ("/", "get"),
    }
    spec = mundo.client.app.openapi()
    huerfanas = []
    for ruta, metodos in spec["paths"].items():
        for verbo, op in metodos.items():
            if verbo not in ("get", "post", "put", "patch", "delete"):
                continue
            if any(p.get("name", "").lower() == COMPANY_HEADER.lower()
                   for p in (op.get("parameters") or [])):
                continue
            if any(ruta.startswith(p) for p in SIN_EMPRESA):
                continue
            if (ruta, verbo) in EXCEPCIONES:
                continue
            huerfanas.append(f"{verbo.upper()} {ruta}")
    assert huerfanas == [], (
        "operaciones de módulo de empresa que no declaran la empresa:\n  "
        + "\n  ".join(sorted(huerfanas)))
