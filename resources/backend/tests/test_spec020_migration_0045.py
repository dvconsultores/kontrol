"""La migración `0045` y lo que la base impide — Spec 020.

Dos cosas que no se pueden comprobar sin PostgreSQL: que la migración no fabrica
incidencias retroactivas a partir de una cantidad rechazada, y que las
restricciones impiden filas a medio camino aunque alguien escriba SQL directo.
"""

from __future__ import annotations

import os
import subprocess
import uuid

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif("postgresql" not in PG_URL,
                                reason="La integridad solo se verifica sobre PostgreSQL (P21)")
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_020 = "0044_spec019_receipt"
CHECK_VIOLATION = "23514"
FK_VIOLATION = "23503"
UNIQUE_VIOLATION = "23505"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(orden_alembic("upgrade", target),
                          cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900)


def _sql(db_name: str, statements: list[tuple[str, dict]]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.begin() as conn:
        for statement, params in statements:
            conn.execute(text(statement), params)
    engine.dispose()


def _rows(db_name: str, statement: str, **params):
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.connect() as conn:
        out = conn.execute(text(statement), params).fetchall()
    engine.dispose()
    return out


def _falla(db_name: str, statement: str, **params) -> str:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    engine = create_engine(_db_url(db_name), future=True)
    try:
        with pytest.raises(IntegrityError) as info:
            with engine.begin() as conn:
                conn.execute(text(statement), params)
        return getattr(info.value.orig, "pgcode", "") or ""
    finally:
        engine.dispose()


BASE_INSERT = (
    "INSERT INTO receipt_incidents (id, company_id, receipt_id, receipt_line_id, code, incident_type, "
    "affected_base_quantity, status, created_at, updated_at) "
    "VALUES (:id, :c, :r, :l, :code, :t, :q, :s, now(), now())")


@pytest.fixture(scope="module")
def base_migrada():
    from sqlalchemy import create_engine, text

    name = f"k020_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    proc = _alembic(name, PRE_020)
    assert proc.returncode == 0, proc.stderr[-3000:]

    ids = {k: str(uuid.uuid4()) for k in ("inst", "ten", "co", "co2", "wh", "prod", "party",
                                          "po", "pol", "rec", "line", "rec2", "line2")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
         "VALUES (:i, :u, 'ACTIVE', now(), now())", {"i": ids["inst"], "u": "u-" + ids["inst"][:8]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:i, :inst, 'T', 'T', 'MULTI_COMPANY', 'ACTIVE', now(), now())", {"i": ids["ten"], "inst": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, status, created_at, updated_at) "
         "VALUES (:i, :t, 'C', 'C', 'J-1', 'JURIDICA', 'VED', 'ACTIVE', now(), now())", {"i": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, status, created_at, updated_at) "
         "VALUES (:i, :t, 'C2', 'C2', 'J-2', 'JURIDICA', 'VED', 'ACTIVE', now(), now())", {"i": ids["co2"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:i, :c, 'W', 'W', 'ACTIVE', now(), now())", {"i": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, created_at, updated_at) "
         "VALUES (:i, :c, 'P', 'P', 'PRODUCT', 'ACTIVE', now(), now())", {"i": ids["prod"], "c": ids["co"]}),
        ("INSERT INTO parties (id, company_id, code, name, person_type, roles, status, created_at, updated_at) "
         "VALUES (:i, :c, 'PRV', 'Proveedor', 'JURIDICA', CAST(:r AS JSON), 'ACTIVE', now(), now())",
         {"i": ids["party"], "c": ids["co"], "r": '["PROVEEDOR"]'}),
        ("INSERT INTO purchase_orders (id, company_id, code, supplier_id, currency, status, created_at, updated_at) "
         "VALUES (:i, :c, 'OC', :s, 'VED', 'APPROVED', now(), now())", {"i": ids["po"], "c": ids["co"], "s": ids["party"]}),
        ("INSERT INTO purchase_order_lines (id, order_id, product_id, quantity_ordered, quantity_received, "
         "unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:i, :o, :p, 100, 0, 5, 0, true, now(), now())", {"i": ids["pol"], "o": ids["po"], "p": ids["prod"]}),
        ("INSERT INTO goods_receipts (id, company_id, code, order_id, warehouse_id, status, "
         "quality_status, created_at, updated_at) "
         "VALUES (:i, :c, 'REC-1', :o, :w, 'ACCEPTED', 'APPROVED', now(), now())",
         {"i": ids["rec"], "c": ids["co"], "o": ids["po"], "w": ids["wh"]}),
        ("INSERT INTO goods_receipt_lines (id, receipt_id, order_line_id, product_id, quantity_received, "
         "quantity_accepted, quantity_rejected, quality, created_at, updated_at) "
         "VALUES (:i, :r, :ol, :p, 20, 18, 2, 'APPROVED', now(), now())",
         {"i": ids["line"], "r": ids["rec"], "ol": ids["pol"], "p": ids["prod"]}),
    ])
    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stderr[-3000:]
    ids["log"] = proc.stdout + proc.stderr
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    admin.dispose()


def test_no_se_fabrica_ninguna_incidencia_retroactiva(base_migrada):
    """Una cantidad rechazada no dice de qué tipo fue la diferencia ni quién la vio."""
    name, ids = base_migrada
    (n,) = _rows(name, "SELECT count(*) FROM receipt_incidents")
    assert n[0] == 0, "la migración inventó incidencias"
    assert "líneas con cantidad rechazada: 1" in ids["log"], ids["log"][-1200:]
    assert "falsificar historia" in ids["log"]


def test_la_tabla_existe_con_sus_restricciones(base_migrada):
    name, _ = base_migrada
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype = 'c' "
                                        "AND conrelid = 'receipt_incidents'::regclass")}
    assert {"ck_receipt_incidents_type", "ck_receipt_incidents_status",
            "ck_receipt_incidents_resolution", "ck_receipt_incidents_line_and_quantity_by_type",
            "ck_receipt_incidents_quantity_positive",
            "ck_receipt_incidents_resolved_has_resolution"} <= checks
    assert not any(c.startswith("ck_receipt_incidents_ck_") for c in checks), "prefijo duplicado"


def test_un_tipo_inventado_no_entra_ni_por_sql(base_migrada):
    name, ids = base_migrada
    estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                    l=ids["line"], code="X1", t="CALIDAD", q=1, s="REGISTRADA")
    assert estado == CHECK_VIOLATION, estado


def test_una_diferencia_documental_con_linea_no_entra(base_migrada):
    """La restricción impide la fila a medio camino en las dos direcciones."""
    name, ids = base_migrada
    estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                    l=ids["line"], code="X2", t="DIFERENCIA_DOCUMENTAL", q=None, s="REGISTRADA")
    assert estado == CHECK_VIOLATION, estado
    estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                    l=None, code="X3", t="DANO", q=None, s="REGISTRADA")
    assert estado == CHECK_VIOLATION, estado


def test_una_cantidad_no_positiva_no_entra(base_migrada):
    name, ids = base_migrada
    for cantidad in (0, -5):
        estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                        l=ids["line"], code=f"X4-{cantidad}", t="DANO", q=cantidad, s="REGISTRADA")
        assert estado == CHECK_VIOLATION, estado


def test_una_incidencia_resuelta_sin_tratamiento_no_entra(base_migrada):
    """Sería una resolución que no dice qué se decidió."""
    name, ids = base_migrada
    estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                    l=ids["line"], code="X5", t="DANO", q=1, s="RESUELTA")
    assert estado == CHECK_VIOLATION, estado


def test_las_claves_foraneas_sujetan_la_cadena(base_migrada):
    name, ids = base_migrada
    inexistente = str(uuid.uuid4())
    assert _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=inexistente, r=ids["rec"],
                  l=ids["line"], code="X6", t="DANO", q=1, s="REGISTRADA") == FK_VIOLATION
    assert _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=inexistente,
                  l=ids["line"], code="X7", t="DANO", q=1, s="REGISTRADA") == FK_VIOLATION
    assert _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                  l=inexistente, code="X8", t="DANO", q=1, s="REGISTRADA") == FK_VIOLATION


def test_el_codigo_es_unico_por_empresa(base_migrada):
    name, ids = base_migrada
    _sql(name, [(BASE_INSERT, {"id": str(uuid.uuid4()), "c": ids["co"], "r": ids["rec"],
                               "l": ids["line"], "code": "UNICO", "t": "DANO", "q": 1,
                               "s": "REGISTRADA"})])
    estado = _falla(name, BASE_INSERT, id=str(uuid.uuid4()), c=ids["co"], r=ids["rec"],
                    l=ids["line"], code="UNICO", t="SOBRANTE", q=1, s="REGISTRADA")
    assert estado == UNIQUE_VIOLATION, estado


def test_la_aplicacion_puede_insertar_en_la_tabla_que_crea_la_migracion(base_migrada):
    """El insert real de la aplicación, contra la tabla real de la migración.

    Las demás pruebas de este módulo escriben SQL crudo con `now(), now()`, y por
    eso ninguna habría visto lo que este caso vio: `TimestampMixin` no pone
    default en Python —lo pone la base con `server_default`—, así que una tabla
    creada por migración sin ese default rechaza **todo** insert del ORM. La
    suite funcional no lo detecta porque su base la construye `create_all` desde
    el ORM, donde el default sí viaja. Solo aquí coinciden las dos mitades.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.database import init_models
    from app.modules.purchasing.models import ReceiptIncident

    init_models()  # las claves foráneas del modelo se resuelven contra la metadata completa

    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True)
    try:
        with Session(engine) as db:
            inc = ReceiptIncident(
                company_id=ids["co"], receipt_id=ids["rec"], receipt_line_id=ids["line"],
                code="ORM-1", incident_type="DANO", affected_base_quantity=2,
                status="REGISTRADA", description="Insert del ORM sin fechas")
            db.add(inc)
            db.commit()
            db.refresh(inc)
            assert inc.created_at is not None, "la base no puso `created_at`"
            assert inc.updated_at is not None, "la base no puso `updated_at`"
    finally:
        engine.dispose()
