"""Spec 047 · esquema: paridad ORM ↔ migración ↔ PostgreSQL, ida y vuelta y permisos.

La base de estas pruebas la construye **Alembic**, no el ORM: comparar el ORM con
un esquema salido de `create_all` sería preguntarle si está de acuerdo consigo
mismo (CORRECTION-013-01).
"""

from __future__ import annotations

import ast
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, init_models
from app.core.integrity import es_violacion_unica

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"),
                                reason="La paridad del esquema se verifica sobre PostgreSQL (P21)")

BACKEND = Path(__file__).resolve().parents[1]
BASE = "kontrol_spec047_schema"
TABLAS = ("scheduler_runs", "scheduler_handler_runs", "notification_rules", "task_priorities",
          "notification_event_receipts", "notifications", "notification_recipients",
          "notification_preferences", "notification_deliveries", "tasks", "task_candidates",
          "task_events", "alerts")
PERMISOS_NUEVOS = {("notificaciones", "configure"), ("tareas", "view"), ("tareas", "assign"),
                   ("tareas", "complete"), ("tareas", "configure"), ("alertas", "view")}


def _url(nombre: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + nombre


def _alembic(*argumentos: str) -> None:
    env = {**os.environ, "KONTROL_DB_URL": _url(BASE)}
    env.pop("KONTROL_TEST_DB_URL", None)
    r = subprocess.run([str(BACKEND / ".venv" / "bin" / "alembic"), *argumentos], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-3000:]


def _permisos_del_admin(motor) -> set[tuple[str, str]]:
    with motor.connect() as c:
        return {tuple(f) for f in c.execute(text(
            "SELECT p.resource, p.action FROM permissions p JOIN role_permissions rp ON rp.permission_id = p.id "
            "JOIN roles r ON r.id = rp.role_id WHERE r.code = 'ADMIN' "
            "AND p.resource IN ('notificaciones', 'tareas', 'alertas')")).all()}


@pytest.fixture(scope="module")
def migrada():
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {BASE} WITH (FORCE)"))
        c.execute(text(f"CREATE DATABASE {BASE}"))
    _alembic("upgrade", "0056_spec013_masters")
    motor = create_engine(_url(BASE))
    # Una instalación ya inicializada: el rol ADMIN existe antes de la migración.
    with motor.begin() as c:
        c.execute(text("INSERT INTO roles (id, code, name, protected, status) "
                       "VALUES (:i, 'ADMIN', 'Administrador', true, 'ACTIVE')"), {"i": str(uuid.uuid4())})
    _alembic("upgrade", "head")
    try:
        yield motor
    finally:
        motor.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {BASE} WITH (FORCE)"))
        admin.dispose()


def test_la_migracion_concede_los_permisos_nuevos_al_administrador(migrada):
    assert _permisos_del_admin(migrada) == PERMISOS_NUEVOS


def test_el_catalogo_del_setup_y_la_migracion_dicen_lo_mismo():
    setup = ast.parse((BACKEND / "app/modules/setup/api.py").read_text())
    catalogo = next(ast.literal_eval(n.value) for n in ast.walk(setup)
                    if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "resources_actions"
                                                         for t in n.targets))
    migracion = ast.parse((BACKEND / "alembic/versions/0057_spec047_notifications.py").read_text())
    permisos = next(ast.literal_eval(n.value) for n in migracion.body
                    if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "PERMISOS" for t in n.targets))
    assert {(r, a) for r, acciones in permisos.items() for a in acciones} == PERMISOS_NUEVOS
    assert {(r, a) for r in permisos for a in catalogo[r]} == PERMISOS_NUEVOS


def test_el_orm_y_la_base_migrada_declaran_lo_mismo(migrada):
    init_models()
    insp = inspect(migrada)
    diferencias = []
    for t in TABLAS:
        tabla = Base.metadata.tables[t]
        pares = (
            ("unicidad", {(c.name, tuple(x.name for x in c.columns)) for c in tabla.constraints
                          if isinstance(c, UniqueConstraint)},
             {(u["name"], tuple(u["column_names"])) for u in insp.get_unique_constraints(t)}),
            ("check", {c.name for c in tabla.constraints if isinstance(c, CheckConstraint)},
             {c["name"] for c in insp.get_check_constraints(t)}),
            ("indice", {(i.name, tuple(x.name for x in i.columns)) for i in tabla.indexes},
             {(i["name"], tuple(i["column_names"])) for i in insp.get_indexes(t)
              if not i.get("duplicates_constraint")}),
            ("foranea", {(tuple(k.column_keys), list(k.elements)[0].column.table.name)
                         for k in tabla.foreign_key_constraints},
             {(tuple(f["constrained_columns"]), f["referred_table"]) for f in insp.get_foreign_keys(t)}),
        )
        for clase, orm, base in pares:
            if orm != base:
                diferencias.append(f"{t} {clase}: solo ORM {sorted(orm - base)} · solo base {sorted(base - orm)}")
        columnas = {c["name"]: c for c in insp.get_columns(t)}
        if set(columnas) != set(tabla.columns.keys()):
            diferencias.append(f"{t} columnas: {sorted(set(columnas) ^ set(tabla.columns.keys()))}")
        for c in tabla.columns:
            if c.name in columnas and bool(c.nullable) != bool(columnas[c.name]["nullable"]):
                diferencias.append(f"{t}.{c.name} nulabilidad")
    assert diferencias == [], "\n".join(diferencias)


def test_la_unicidad_y_los_checks_existen_de_verdad_en_la_base_migrada(migrada):
    fila = ("INSERT INTO scheduler_runs (id, correlation_id, status, scheduled_for, started_at) "
            "VALUES (:i, :c, :s, now(), now())")
    correlacion = str(uuid.uuid4())
    with migrada.begin() as c:
        c.execute(text(fila), {"i": str(uuid.uuid4()), "c": correlacion, "s": "STARTED"})
    with pytest.raises(IntegrityError) as repetida, migrada.begin() as c:
        c.execute(text(fila), {"i": str(uuid.uuid4()), "c": correlacion, "s": "STARTED"})
    assert es_violacion_unica(repetida.value, "uq_scheduler_runs_correlation_id")
    with pytest.raises(IntegrityError) as invalida, migrada.begin() as c:
        c.execute(text(fila), {"i": str(uuid.uuid4()), "c": str(uuid.uuid4()), "s": "OTRO"})
    assert not es_violacion_unica(invalida.value, "uq_scheduler_runs_correlation_id")
    assert "ck_scheduler_runs_status" in str(invalida.value)


def test_zz_la_migracion_se_deshace_y_se_rehace(migrada):
    migrada.dispose()
    _alembic("downgrade", "0056_spec013_masters")
    assert not set(TABLAS) & set(inspect(create_engine(_url(BASE))).get_table_names())
    assert _permisos_del_admin(migrada) == set()
    _alembic("upgrade", "head")
    assert set(TABLAS) <= set(inspect(create_engine(_url(BASE))).get_table_names())
    assert _permisos_del_admin(migrada) == PERMISOS_NUEVOS
