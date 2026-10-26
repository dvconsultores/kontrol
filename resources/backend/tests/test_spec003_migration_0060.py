"""Spec 003 · la migración 0060 sobre PostgreSQL real.

Fija el contrato de la migración `0060_spec003_admin_split`:
- Separa el rol ADMIN en ADMIN (permisos técnicos) y FUNCIONAL_COMPLETO (permisos funcionales).
- Actualiza el alcance de user_roles de usuarios `setup` (company_id -> NULL).
- Emite eventos de auditoría para trazabilidad.
"""

import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, text

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="La migración 0060 solo se verifica sobre PostgreSQL",
)

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_060 = "0059_spec002_password_reset"

TECNICAS = frozenset({
    "audit:view", "dashboard:view", "documentos:manage_types", "license:approve",
    "license:create", "license:edit", "license:view", "notificaciones:configure",
    "organization:activate", "organization:create", "organization:deactivate",
    "organization:delete", "organization:edit", "organization:manage_structure",
    "organization:view", "roles:create", "roles:edit", "roles:view",
    "tareas:configure", "users:activate", "users:create", "users:deactivate",
    "users:edit", "users:mfa_reset", "users:view",
})


def _catalogo(name) -> set[str]:
    """«recurso:accion» de toda la tabla permissions."""
    return {fila[0] for fila in _rows(name, "SELECT resource || ':' || action FROM permissions")}


def _postgres_admin_url():
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name):
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _crear_base(name):
    engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        engine.dispose()


def _borrar_base(name):
    engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        engine.dispose()


def _alembic(name, target, comando="upgrade"):
    env = {**os.environ, "KONTROL_DB_URL": _db_url(name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    result = subprocess.run(
        orden_alembic(comando, target),
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, (
        f"Alembic {comando} {target} falló:\n"
        f"stdout[-2000:]: {result.stdout[-2000:]}\n"
        f"stderr[-2000:]: {result.stderr[-2000:]}"
    )


def _sql(name, statements):
    engine = create_engine(_db_url(name))
    try:
        with engine.begin() as conn:
            for stmt, params in statements:
                conn.execute(text(stmt), params)
    finally:
        engine.dispose()


def _rows(name, statement, **params):
    engine = create_engine(_db_url(name))
    try:
        with engine.connect() as conn:
            result = conn.execute(text(statement), params)
            return result.fetchall()
    finally:
        engine.dispose()


PERMISOS = [
    ("users", "create"),
    ("roles", "edit"),
    ("users", "mfa_reset"),
    ("dashboard", "view"),
    ("compras", "view"),
    ("inventario", "view"),
    ("aprobaciones", "configure"),
]


def _sembrar(name):
    """Siembra datos previos a la migración 0060."""
    ids = {}

    inst = str(uuid.uuid4())
    ten = str(uuid.uuid4())
    d1 = str(uuid.uuid4())
    admin = str(uuid.uuid4())
    inicial = str(uuid.uuid4())
    otro = str(uuid.uuid4())
    ur_inicial = str(uuid.uuid4())
    ur_otro = str(uuid.uuid4())

    ids["inst"] = inst
    ids["ten"] = ten
    ids["d1"] = d1
    ids["admin"] = admin
    ids["inicial"] = inicial
    ids["otro"] = otro
    ids["ur_inicial"] = ur_inicial
    ids["ur_otro"] = ur_otro

    statements = [
        (
            "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
            "VALUES (:id, :uuid, 'ACTIVE', now(), now())",
            {"id": inst, "uuid": str(uuid.uuid4())},
        ),
        (
            "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
            "VALUES (:id, :installation_id, :code, :name, 'MONO_COMPANY', 'ACTIVE', now(), now())",
            {"id": ten, "installation_id": inst, "code": "T001", "name": "Tenant 001"},
        ),
        (
            "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, "
            "confirmation_same_user_allowed, status, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :code, :legal_name, :rif, 'JURIDICA', 'VED', false, 'ACTIVE', now(), now())",
            {"id": d1, "tenant_id": ten, "code": "D1", "legal_name": "Empresa D1", "rif": "J-00000000-0"},
        ),
        (
            "INSERT INTO roles (id, code, name, company_id, protected, status, created_at, updated_at) "
            "VALUES (:id, 'ADMIN', 'ADMIN', NULL, true, 'ACTIVE', now(), now())",
            {"id": admin},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, must_change_password, "
            "failed_attempts, mfa_enabled, credential_stamp, created_by, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :username, :email, 'x', 'ACTIVE', false, 0, false, :credential_stamp, "
            ":created_by, now(), now())",
            {
                "id": inicial,
                "tenant_id": ten,
                "username": "inicial",
                "email": "inicial@example.com",
                "credential_stamp": uuid.uuid4().hex,
                "created_by": "setup",
            },
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, must_change_password, "
            "failed_attempts, mfa_enabled, credential_stamp, created_by, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :username, :email, 'x', 'ACTIVE', false, 0, false, :credential_stamp, "
            ":created_by, now(), now())",
            {
                "id": otro,
                "tenant_id": ten,
                "username": "otro",
                "email": "otro@example.com",
                "credential_stamp": uuid.uuid4().hex,
                "created_by": None,
            },
        ),
        (
            "INSERT INTO user_roles (id, user_id, role_id, company_id, created_at, updated_at) "
            "VALUES (:id, :user_id, :role_id, :company_id, now(), now())",
            {"id": ur_inicial, "user_id": inicial, "role_id": admin, "company_id": d1},
        ),
        (
            "INSERT INTO user_roles (id, user_id, role_id, company_id, created_at, updated_at) "
            "VALUES (:id, :user_id, :role_id, :company_id, now(), now())",
            {"id": ur_otro, "user_id": otro, "role_id": admin, "company_id": d1},
        ),
    ]

    for recurso, accion in PERMISOS:
        pid = str(uuid.uuid4())
        ids[f"p:{recurso}:{accion}"] = pid
        statements.append(
            (
                "INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at) "
                "VALUES (:id, :resource, :action, 'COMPANY', now(), now())",
                {"id": pid, "resource": recurso, "action": accion},
            )
        )
        statements.append(
            (
                "INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) "
                "VALUES (:id, :role_id, :permission_id, now(), now())",
                {"id": str(uuid.uuid4()), "role_id": admin, "permission_id": pid},
            )
        )

    _sql(name, statements)
    return ids


def _permisos_de(name, role_id):
    rows = _rows(
        name,
        "SELECT p.resource || ':' || p.action AS permiso "
        "FROM role_permissions rp "
        "JOIN permissions p ON p.id = rp.permission_id "
        "WHERE rp.role_id = :role_id",
        role_id=role_id,
    )
    return {row[0] for row in rows}


def _funcional(name):
    rows = _rows(
        name,
        "SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL",
    )
    return rows[0][0] if rows else None


@pytest.fixture(scope="module")
def base_vacia():
    name = f"kontrol_test_0060_vacia_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    try:
        _alembic(name, "head")
        yield name
    finally:
        _borrar_base(name)


@pytest.fixture(scope="module")
def base_actualizada():
    name = f"kontrol_test_0060_actualizada_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    try:
        _alembic(name, PRE_060)
        ids = _sembrar(name)
        _alembic(name, "head")
        yield name, ids
    finally:
        _borrar_base(name)


def test_adm_mig_r01_base_vacia_no_genera_funcional_ni_eventos(base_vacia):
    """ADM-MIG-R01: base vacía no genera rol FUNCIONAL_COMPLETO ni eventos de migración."""
    name = base_vacia
    funcional = _funcional(name)
    assert funcional is None, "No debe existir FUNCIONAL_COMPLETO en base vacía"

    rows = _rows(
        name,
        "SELECT COUNT(*) FROM audit_events WHERE source = 'MIGRATION'",
    )
    assert rows[0][0] == 0, "No debe haber eventos con source 'MIGRATION' en base vacía"


def test_adm_mig_r02_admin_solo_tecnicos_funcional_completo(base_actualizada):
    """ADM-MIG-R02: ADMIN conserva solo permisos técnicos y FUNCIONAL_COMPLETO recibe los funcionales."""
    name, ids = base_actualizada
    admin_id = ids["admin"]

    permisos_admin = _permisos_de(name, admin_id)
    assert permisos_admin == {
        "users:create",
        "roles:edit",
        "users:mfa_reset",
        "dashboard:view",
    }, f"Permisos ADMIN inesperados: {permisos_admin}"

    funcional_id = _funcional(name)
    assert funcional_id is not None, "Debe existir FUNCIONAL_COMPLETO"

    row = _rows(
        name,
        "SELECT protected, status, company_id FROM roles WHERE id = :id",
        id=funcional_id,
    )[0]
    assert row[0] is True, "FUNCIONAL_COMPLETO debe ser protegido"
    assert row[1] == "ACTIVE", "FUNCIONAL_COMPLETO debe estar ACTIVO"
    assert row[2] is None, "FUNCIONAL_COMPLETO debe ser global (company_id NULL)"

    permisos_funcional = _permisos_de(name, funcional_id)
    esperado_funcional = _catalogo(name) - TECNICAS
    assert permisos_funcional == esperado_funcional, (
        "Permisos FUNCIONAL_COMPLETO inesperados: "
        f"sym_diff={permisos_funcional ^ esperado_funcional}"
    )
    assert {"compras:view", "inventario:view", "aprobaciones:configure"} <= permisos_funcional


def test_adm_mig_r03_alcance_inicial_y_evento_scope_changed(base_actualizada):
    """ADM-MIG-R03: el user_role del usuario setup cambia a NULL con evento USER_SCOPE_CHANGED."""
    name, ids = base_actualizada
    d1 = ids["d1"]
    ur_inicial = ids["ur_inicial"]
    ur_otro = ids["ur_otro"]

    fila_inicial = _rows(
        name,
        "SELECT company_id FROM user_roles WHERE id = :id",
        id=ur_inicial,
    )[0]
    assert fila_inicial[0] is None, "El user_role del usuario setup debe tener company_id NULL"

    fila_otro = _rows(
        name,
        "SELECT company_id FROM user_roles WHERE id = :id",
        id=ur_otro,
    )[0]
    assert fila_otro[0] == d1, "El user_role del otro usuario debe conservar company_id"

    eventos = _rows(
        name,
        "SELECT entity_id, before->>'company_id' AS before_company, "
        "after->>'company_id' AS after_company, reason, source "
        "FROM audit_events "
        "WHERE action = 'USER_SCOPE_CHANGED' AND source = 'MIGRATION'",
    )
    assert len(eventos) == 1, f"Se esperaba 1 evento USER_SCOPE_CHANGED, hay {len(eventos)}"
    evento = eventos[0]
    assert evento[0] == ur_inicial, "El evento debe referenciar el user_role del usuario setup"
    assert evento[1] == d1, "El before debe contener el company_id original"
    assert evento[2] is None, "El after debe contener company_id null"
    assert evento[3] == "OD-DEL-12", "El reason debe ser OD-DEL-12"
    assert evento[4] == "MIGRATION", "El source debe ser MIGRATION"


def test_adm_mig_r04_asignacion_funcional_y_eventos_role_assigned(base_actualizada):
    """ADM-MIG-R04: cada usuario recibe FUNCIONAL_COMPLETO con su company_id y se emiten eventos ROLE_ASSIGNED."""
    name, ids = base_actualizada
    d1 = ids["d1"]
    inicial = ids["inicial"]
    otro = ids["otro"]
    funcional_id = _funcional(name)
    assert funcional_id is not None

    fila_inicial = _rows(
        name,
        "SELECT company_id FROM user_roles WHERE user_id = :user_id AND role_id = :role_id",
        user_id=inicial,
        role_id=funcional_id,
    )
    assert len(fila_inicial) == 1, "El usuario setup debe tener exactamente 1 user_role FUNCIONAL_COMPLETO"
    assert fila_inicial[0][0] is None, "El user_role FUNCIONAL_COMPLETO del setup debe ser global"

    fila_otro = _rows(
        name,
        "SELECT company_id FROM user_roles WHERE user_id = :user_id AND role_id = :role_id",
        user_id=otro,
        role_id=funcional_id,
    )
    assert len(fila_otro) == 1, "El otro usuario debe tener exactamente 1 user_role FUNCIONAL_COMPLETO"
    assert fila_otro[0][0] == d1, "El user_role FUNCIONAL_COMPLETO del otro debe conservar company_id"

    eventos = _rows(
        name,
        "SELECT reason, source FROM audit_events "
        "WHERE action = 'ROLE_ASSIGNED' AND source = 'MIGRATION'",
    )
    assert len(eventos) == 2, f"Se esperaban 2 eventos ROLE_ASSIGNED, hay {len(eventos)}"
    assert all(e[0] == "OD-DEL-10" for e in eventos), "El reason debe ser OD-DEL-10"
    assert all(e[1] == "MIGRATION" for e in eventos), "El source debe ser MIGRATION"


@pytest.fixture
def base_downgrade_upgrade():
    name = f"kontrol_test_0060_downgrade_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    try:
        _alembic(name, PRE_060)
        ids = _sembrar(name)
        _alembic(name, "head")
        yield name, ids
    finally:
        _borrar_base(name)


def test_adm_mig_r05_downgrade_y_upgrade_idempotente(base_downgrade_upgrade):
    """ADM-MIG-R05: el downgrade revierte roles/permisos pero no el alcance ni los eventos; el upgrade es idempotente."""
    name, ids = base_downgrade_upgrade
    admin_id = ids["admin"]
    ur_inicial = ids["ur_inicial"]
    inicial = ids["inicial"]
    otro = ids["otro"]

    _alembic(name, PRE_060, comando="downgrade")

    funcional_id = _funcional(name)
    assert funcional_id is None, "Tras downgrade no debe existir FUNCIONAL_COMPLETO"

    permisos_admin = _permisos_de(name, admin_id)
    esperado = {"users:create", "roles:edit", "users:mfa_reset", "dashboard:view"} | (
        _catalogo(name) - TECNICAS
    )
    assert permisos_admin == esperado, (
        "Tras downgrade ADMIN debe recuperar sus permisos y los funcionales: "
        f"sym_diff={permisos_admin ^ esperado}"
    )

    fila_inicial = _rows(
        name,
        "SELECT company_id FROM user_roles WHERE id = :id",
        id=ur_inicial,
    )[0]
    assert fila_inicial[0] is None, "El downgrade no debe revertir el company_id NULL del usuario setup"

    eventos_migracion = _rows(
        name,
        "SELECT COUNT(*) FROM audit_events WHERE source = 'MIGRATION'",
    )[0][0]
    assert eventos_migracion >= 3, "Los eventos de migración deben persistir tras downgrade"

    _alembic(name, "head")

    permisos_admin = _permisos_de(name, admin_id)
    assert permisos_admin == {
        "users:create",
        "roles:edit",
        "users:mfa_reset",
        "dashboard:view",
    }, f"Tras re-upgrade ADMIN debe tener solo técnicos, tiene: {permisos_admin}"

    funcional_id = _funcional(name)
    assert funcional_id is not None, "Tras re-upgrade debe existir FUNCIONAL_COMPLETO"
    permisos_funcional = _permisos_de(name, funcional_id)
    esperado_funcional = _catalogo(name) - TECNICAS
    assert permisos_funcional == esperado_funcional, (
        "Tras re-upgrade FUNCIONAL_COMPLETO debe tener funcionales: "
        f"sym_diff={permisos_funcional ^ esperado_funcional}"
    )

    for user_id in (inicial, otro):
        filas = _rows(
            name,
            "SELECT COUNT(*) FROM user_roles WHERE user_id = :user_id AND role_id = :role_id",
            user_id=user_id,
            role_id=funcional_id,
        )
        assert filas[0][0] == 1, (
            f"Tras re-upgrade el usuario {user_id} debe tener exactamente 1 user_role FUNCIONAL_COMPLETO"
        )
