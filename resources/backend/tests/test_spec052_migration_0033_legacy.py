"""Actualización de una instalación con histórico: migración `0033` (Spec 052).

La `0016` preserva a propósito las solicitudes regulatorias legadas cuya empresa
ya no existe —las deja en `regulatory_approval_requests` y no las migra al motor—
apoyándose en que esa tabla guardaba `company_id` sin clave foránea. La `0033`
añadió esa clave foránea a 80 tablas y, con ella, la actualización de cualquier
instalación con ese histórico abortaba entera con `ForeignKeyViolation`.

Lo que aquí se demuestra es que las dos decisiones vuelven a convivir: el histórico
sobrevive sin que nadie lo borre, lo reasigne ni le invente una empresa, y toda
escritura nueva sigue teniendo que apuntar a una empresa que exista de verdad.

Sobre PostgreSQL real: una restricción `NOT VALID` no existe en otros motores y el
modo offline no lee datos, así que no podría clasificar nada.
"""

from __future__ import annotations

import os
import subprocess

import pytest

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    "postgresql" not in PG_URL,
    reason="El camino de actualización solo es verificable sobre PostgreSQL (P21)",
)

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Última revisión anterior al motor de aprobaciones: el punto donde vive el legado.
PRE_045 = "0014_numeric_money_2"
DB_LEGADA = "kontrol_legacy_fk_0033"
DB_LIMPIA = "kontrol_fresh_fk_0033"

#: Empresa viva del histórico.
VIVA = "co-viva"
#: Dos empresas distintas, ambas desaparecidas: el caso no es un singular.
BORRADA_A = "co-borrada-a"
BORRADA_B = "co-borrada-b"


def _admin_url() -> str:
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(
        [os.path.join(BACKEND, ".venv", "bin", "alembic"), "upgrade", target],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900,
    )


def _crear_base(nombre: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_admin_url(), future=True, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{nombre}" ENCODING \'UTF8\''))
    engine.dispose()
    # La base tiene dueño: se suelta al terminar el ámbito —la prueba o el módulo— que la creó.
    from pg_harness import registrar_base

    registrar_base(nombre)


def _sql(db_name: str, statements: list[str]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    engine.dispose()


def _query(db_name: str, statement: str):
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.connect() as conn:
        rows = conn.execute(text(statement)).fetchall()
    engine.dispose()
    return rows


def _escribir(db_name: str, statement: str) -> str | None:
    """Ejecuta una escritura y devuelve el error de la base, o `None` si pasó."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    engine = create_engine(_db_url(db_name), future=True)
    try:
        with engine.begin() as conn:
            conn.execute(text(statement))
        return None
    except IntegrityError as error:
        return str(error.orig)
    finally:
        engine.dispose()


def _solicitud(ident: str, empresa: str, ref: str, importe: str,
               decision: str | None, estado: str, tabla: str = "approval_requests") -> str:
    """Solicitud regulatoria.

    Antes de la `0015` la tabla se llama `approval_requests`; después de ella ese
    nombre pasa al motor y el legado vive en `regulatory_approval_requests`. Por eso
    la siembra histórica y las escrituras posteriores a la actualización no escriben
    en el mismo sitio aunque sean la misma entidad.
    """
    decision_sql = "NULL" if decision is None else f"'{decision}'"
    return (
        f"INSERT INTO {tabla} (id, company_id, object_ref, requester_id, "
        "  amount, decision, status, created_at, updated_at) "
        f"VALUES ('{ident}','{empresa}','{ref}','u-1',{importe},{decision_sql},"
        f"        '{estado}',now(),now())"
    )


#: El histórico tal como queda tras la vida de una instalación real: filas de una
#: empresa viva mezcladas con filas de dos empresas que ya no existen.
HISTORICO = [
    ("leg-viva-1", VIVA, "DESP-0001", "1500.00", "APPROVED", "APPROVED"),
    ("leg-viva-2", VIVA, "DESP-0002", "2500.00", "REJECTED", "REJECTED"),
    ("leg-viva-3", VIVA, "DESP-0003", "900.00", None, "PENDING"),
    ("leg-huerf-1", BORRADA_A, "DESP-0004", "100.00", "APPROVED", "APPROVED"),
    ("leg-huerf-2", BORRADA_A, "DESP-0005", "250.50", "REJECTED", "REJECTED"),
    ("leg-huerf-3", BORRADA_B, "DESP-0006", "777.77", None, "PENDING"),
]


@pytest.fixture(scope="module")
def base_legada() -> str:
    """Instalación anterior al motor, con histórico válido y huérfano mezclados."""
    _crear_base(DB_LEGADA)
    previo = _alembic(DB_LEGADA, PRE_045)
    assert previo.returncode == 0, previo.stderr[-3000:]

    _sql(DB_LEGADA, [
        "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
        "VALUES ('inst-1','uuid-1','ACTIVE',now(),now())",
        "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
        "VALUES ('ten-1','inst-1','DEMO','Demo','MULTI_COMPANY','ACTIVE',now(),now())",
        "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
        "  functional_currency, status, created_at, updated_at) "
        f"VALUES ('{VIVA}','ten-1','D1','Demo CA','J-1','CA','VED','ACTIVE',now(),now())",
        "INSERT INTO roles (id, code, name, protected, status, created_at, updated_at) "
        "VALUES ('role-admin','ADMIN','Administrador',true,'ACTIVE',now(),now())",
        "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
        "  mfa_enabled, must_change_password, failed_attempts, created_at, updated_at) "
        "VALUES ('u-1','ten-1','admin','a@d.com','x','ACTIVE',false,false,0,now(),now())",
        "INSERT INTO user_roles (id, user_id, role_id, created_at, updated_at) "
        "VALUES ('ur-1','u-1','role-admin',now(),now())",
        *[_solicitud(*fila) for fila in HISTORICO],
    ])
    return DB_LEGADA


@pytest.fixture(scope="module")
def base_legada_migrada(base_legada: str) -> str:
    """La misma instalación, ya llevada a la cabeza de migraciones."""
    resultado = _alembic(base_legada, "head")
    assert resultado.returncode == 0, (
        "la actualización de una instalación con histórico debe llegar a la cabeza:\n"
        + resultado.stderr[-3000:])
    return base_legada


# --------------------------------------------------------------------------- #
# El camino de actualización
# --------------------------------------------------------------------------- #
def test_una_instalacion_con_historico_huerfano_llega_a_la_cabeza(base_legada_migrada):
    """Antes fallaba en `0033`; la instalación entera se quedaba sin actualizar."""
    revision = _query(base_legada_migrada, "SELECT version_num FROM alembic_version")[0][0]
    cabeza = subprocess.run(
        [os.path.join(BACKEND, ".venv", "bin", "alembic"), "heads"],
        cwd=BACKEND, env={**os.environ, "KONTROL_DB_URL": _db_url(base_legada_migrada)},
        capture_output=True, text=True, timeout=120,
    ).stdout
    assert revision in cabeza, f"la base quedó en {revision}, que no es la cabeza"


def test_el_historico_sobrevive_entero_y_sin_un_solo_cambio(base_legada_migrada):
    """Ni se borra, ni se reasigna, ni se le toca la carga de negocio."""
    filas = _query(base_legada_migrada,
                   "SELECT id, company_id, object_ref, amount, decision, status "
                   "FROM regulatory_approval_requests ORDER BY id")
    obtenido = {f[0]: (f[1], f[2], str(f[3]), f[4], f[5]) for f in filas}
    esperado = {i: (e, r, imp, d, s) for i, e, r, imp, d, s in HISTORICO}

    assert set(obtenido) == set(esperado), "falta o sobra alguna solicitud legada"
    for ident, valores in esperado.items():
        assert obtenido[ident] == valores, f"la solicitud {ident} cambió: {obtenido[ident]}"


def test_no_se_fabrica_ninguna_empresa(base_legada_migrada):
    """Satisfacer una clave foránea inventando la empresa que falta está prohibido."""
    empresas = _query(base_legada_migrada, "SELECT id FROM companies ORDER BY id")
    assert [e[0] for e in empresas] == [VIVA], f"apareció una empresa nueva: {empresas}"


def test_solo_se_migra_al_motor_lo_que_tiene_empresa_viva(base_legada_migrada):
    """La regla de la `0016` sigue intacta: lo huérfano no entra al motor."""
    migradas = _query(base_legada_migrada,
                      "SELECT document_id FROM approval_requests "
                      "WHERE document_type = 'RegulatoryApprovalRequest' ORDER BY document_id")
    assert [m[0] for m in migradas] == ["leg-viva-1", "leg-viva-2", "leg-viva-3"]


# --------------------------------------------------------------------------- #
# La integridad que sí se exige
# --------------------------------------------------------------------------- #
def test_la_restriccion_existe_y_tolera_solo_lo_historico(base_legada_migrada):
    """`NOT VALID` en la tabla con histórico colgante; validada en todas las demás."""
    sin_validar = _query(base_legada_migrada,
                         "SELECT conrelid::regclass::text FROM pg_constraint "
                         "WHERE conname LIKE 'fk_%_company' AND contype = 'f' "
                         "AND NOT convalidated ORDER BY 1")
    assert [s[0] for s in sin_validar] == ["regulatory_approval_requests"]

    validadas = _query(base_legada_migrada,
                       "SELECT count(*) FROM pg_constraint WHERE conname LIKE 'fk_%_company' "
                       "AND contype = 'f' AND convalidated")[0][0]
    assert validadas > 0, "ninguna restricción quedó validada"


def test_una_escritura_nueva_con_empresa_inexistente_es_rechazada(base_legada_migrada):
    """Tolerar el pasado no es abrir la puerta al presente."""
    error = _escribir(base_legada_migrada, _solicitud(
        "nueva-invalida", "co-que-no-existe", "X-1", "1.00", None, "PENDING",
        tabla="regulatory_approval_requests"))
    assert error is not None, "la base aceptó una empresa inexistente"
    assert "fk_regulatory_approval_requests_company" in error


def test_mover_una_fila_a_una_empresa_inexistente_tambien_es_rechazado(base_legada_migrada):
    """La restricción vigila la actualización igual que la inserción."""
    error = _escribir(base_legada_migrada,
                      "UPDATE regulatory_approval_requests SET company_id = 'co-que-no-existe' "
                      "WHERE id = 'leg-viva-1'")
    assert error is not None, "la base aceptó mover una fila a una empresa inexistente"
    assert "fk_regulatory_approval_requests_company" in error


def test_una_escritura_nueva_con_empresa_real_se_acepta(base_legada_migrada):
    """La corrección no puede volverse un candado para la operación normal."""
    error = _escribir(base_legada_migrada, _solicitud(
        "nueva-valida", VIVA, "X-2", "10.00", None, "PENDING",
        tabla="regulatory_approval_requests"))
    assert error is None, f"la base rechazó una empresa real: {error}"
    _sql(base_legada_migrada, ["DELETE FROM regulatory_approval_requests WHERE id = 'nueva-valida'"])


def test_repetir_la_actualizacion_no_cambia_nada(base_legada_migrada):
    """Una base ya en la cabeza no vuelve a anotar, ni duplica, ni muta."""
    antes = _query(base_legada_migrada,
                   "SELECT (SELECT count(*) FROM regulatory_approval_requests), "
                   "       (SELECT count(*) FROM approval_requests), "
                   "       (SELECT count(*) FROM companies)")[0]
    resultado = _alembic(base_legada_migrada, "head")
    assert resultado.returncode == 0, resultado.stderr[-2000:]
    despues = _query(base_legada_migrada,
                     "SELECT (SELECT count(*) FROM regulatory_approval_requests), "
                     "       (SELECT count(*) FROM approval_requests), "
                     "       (SELECT count(*) FROM companies)")[0]
    assert tuple(antes) == tuple(despues)


# --------------------------------------------------------------------------- #
# La instalación limpia no paga el precio del histórico
# --------------------------------------------------------------------------- #
def test_una_instalacion_limpia_termina_con_todo_validado():
    """Sin histórico colgante no hay excepción que tolerar: todo queda comprobado."""
    _crear_base(DB_LIMPIA)
    resultado = _alembic(DB_LIMPIA, "head")
    assert resultado.returncode == 0, resultado.stderr[-3000:]

    sin_validar = _query(DB_LIMPIA,
                         "SELECT conrelid::regclass::text FROM pg_constraint "
                         "WHERE conname LIKE 'fk_%_company' AND contype = 'f' "
                         "AND NOT convalidated")
    assert sin_validar == [], f"una instalación limpia dejó restricciones sin validar: {sin_validar}"
