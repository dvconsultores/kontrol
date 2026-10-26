"""Migración Spec 003: división de ADMIN en rol técnico y rol funcional.

Esta migración aplica las decisiones OD-DEL-10 y OD-DEL-12:
- Reubica las asignaciones ADMIN realizadas por el setup inicial al alcance
  de tenant del administrador (company_id NULL).
- Crea el rol FUNCIONAL_COMPLETO y mueve a él todos los permisos que no son
  técnicos, asignándolo a los usuarios que antes eran ADMIN.

La migración es idempotente: volver a ejecutarla no duplica permisos, roles
ni asignaciones.

Revision ID: 0060_spec003_admin_split
Revises: 0059_spec002_password_reset
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0060_spec003_admin_split"
down_revision = "0059_spec002_password_reset"
branch_labels = None
depends_on = None

_TECNICAS: frozenset[str] = frozenset(
    {
        "dashboard:view",
        "organization:view",
        "organization:create",
        "organization:edit",
        "organization:deactivate",
        "organization:activate",
        "organization:delete",
        "organization:manage_structure",
        "users:view",
        "users:create",
        "users:edit",
        "users:deactivate",
        "users:activate",
        "users:mfa_reset",
        "roles:view",
        "roles:create",
        "roles:edit",
        "audit:view",
        "license:view",
        "license:create",
        "license:edit",
        "license:approve",
        "notificaciones:configure",
        "tareas:configure",
        "documentos:manage_types",
    }
)

_FUNCIONAL = "FUNCIONAL_COMPLETO"

_AUDIT = sa.table(
    "audit_events",
    sa.column("id", sa.String),
    sa.column("tenant_id", sa.String),
    sa.column("user_id", sa.String),
    sa.column("action", sa.String),
    sa.column("entity_type", sa.String),
    sa.column("entity_id", sa.String),
    sa.column("before", sa.JSON),
    sa.column("after", sa.JSON),
    sa.column("source", sa.String),
    sa.column("reason", sa.String),
    sa.column("evidence", sa.JSON),
    sa.column("event_time", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _obtener_role_id(bind: sa.Connection, code: str) -> str | None:
    """Devuelve el id del rol PROTEGIDO de toda la instalación con ese código, o None si no existe."""
    resultado = bind.execute(
        sa.text(
            "SELECT id FROM roles WHERE code = :code AND company_id IS NULL AND protected = true LIMIT 1"
        ),
        {"code": code},
    ).mappings().first()
    return resultado["id"] if resultado else None


def _registrar_auditoria(
    bind: sa.Connection,
    *,
    tenant_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None,
    after: dict | None,
    reason: str,
    ahora: datetime,
) -> None:
    """Inserta un evento de auditoría de la migración."""
    bind.execute(
        _AUDIT.insert().values(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            source="MIGRATION",
            reason=reason,
            evidence={"migration": revision},
            event_time=ahora,
            created_at=ahora,
            updated_at=ahora,
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    ahora = datetime.now(UTC)

    admin_id = _obtener_role_id(bind, "ADMIN")
    if admin_id is None:
        # Base vacía: el arranque creará los roles en tiempo de ejecución.
        return

    # OD-DEL-12: las asignaciones ADMIN creadas por setup pasan a alcance de tenant.
    filas_setup = bind.execute(
        sa.text(
            """
            SELECT ur.id, ur.company_id, u.tenant_id
            FROM user_roles ur
            JOIN users u ON u.id = ur.user_id
            WHERE ur.role_id = :admin AND ur.company_id IS NOT NULL
              AND u.created_by = 'setup'
            """
        ),
        {"admin": admin_id},
    ).mappings().all()

    for fila in filas_setup:
        bind.execute(
            sa.text(
                "UPDATE user_roles SET company_id = NULL, updated_at = :ahora WHERE id = :id"
            ),
            {"id": fila["id"], "ahora": ahora},
        )
        _registrar_auditoria(
            bind,
            tenant_id=fila["tenant_id"],
            action="USER_SCOPE_CHANGED",
            entity_type="UserRole",
            entity_id=fila["id"],
            before={"company_id": fila["company_id"]},
            after={"company_id": None},
            reason="OD-DEL-12",
            ahora=ahora,
        )

    funcional_id = _obtener_role_id(bind, _FUNCIONAL)
    if funcional_id is None:
        funcional_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO roles
                    (id, code, name, company_id, protected, status, created_by, created_at, updated_at)
                VALUES
                    (:id, :code, :name, NULL, true, 'ACTIVE', 'migration-0060', :ahora, :ahora)
                """
            ),
            {
                "id": funcional_id,
                "code": _FUNCIONAL,
                "name": "Funcional completo",
                "ahora": ahora,
            },
        )

    permisos = bind.execute(
        sa.text("SELECT id, resource, action FROM permissions")
    ).mappings().all()

    permisos_admin = {
        fila["permission_id"]
        for fila in bind.execute(
            sa.text(
                "SELECT permission_id FROM role_permissions WHERE role_id = :role"
            ),
            {"role": admin_id},
        ).mappings()
    }
    permisos_funcional = {
        fila["permission_id"]
        for fila in bind.execute(
            sa.text(
                "SELECT permission_id FROM role_permissions WHERE role_id = :role"
            ),
            {"role": funcional_id},
        ).mappings()
    }

    for permiso in permisos:
        clave = f"{permiso['resource']}:{permiso['action']}"
        if clave in _TECNICAS:
            continue

        permiso_id = permiso["id"]
        if permiso_id not in permisos_funcional:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    VALUES (:id, :role, :permission, :ahora, :ahora)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "role": funcional_id,
                    "permission": permiso_id,
                    "ahora": ahora,
                },
            )
            permisos_funcional.add(permiso_id)

        if permiso_id in permisos_admin:
            bind.execute(
                sa.text(
                    "DELETE FROM role_permissions WHERE role_id = :admin AND permission_id = :permission"
                ),
                {"admin": admin_id, "permission": permiso_id},
            )
            permisos_admin.discard(permiso_id)

    # OD-DEL-10: asignar FUNCIONAL_COMPLETO a todos los ADMIN, por cada alcance.
    filas_admin = bind.execute(
        sa.text(
            """
            SELECT ur.user_id, ur.company_id, u.tenant_id
            FROM user_roles ur
            JOIN users u ON u.id = ur.user_id
            WHERE ur.role_id = :admin
            """
        ),
        {"admin": admin_id},
    ).mappings().all()

    filas_funcional = bind.execute(
        sa.text(
            "SELECT user_id, company_id FROM user_roles WHERE role_id = :role"
        ),
        {"role": funcional_id},
    ).mappings().all()
    pares_funcional = {
        (fila["user_id"], fila["company_id"])
        for fila in filas_funcional
    }

    for fila in filas_admin:
        par = (fila["user_id"], fila["company_id"])
        if par in pares_funcional:
            continue

        nuevo_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO user_roles (id, user_id, role_id, company_id, created_at, updated_at)
                VALUES (:id, :user, :role, :company, :ahora, :ahora)
                """
            ),
            {
                "id": nuevo_id,
                "user": fila["user_id"],
                "role": funcional_id,
                "company": fila["company_id"],
                "ahora": ahora,
            },
        )
        pares_funcional.add(par)
        _registrar_auditoria(
            bind,
            tenant_id=fila["tenant_id"],
            action="ROLE_ASSIGNED",
            entity_type="UserRole",
            entity_id=nuevo_id,
            before=None,
            after={
                "role_id": funcional_id,
                "user_id": fila["user_id"],
                "company_id": fila["company_id"],
            },
            reason="OD-DEL-10",
            ahora=ahora,
        )


def downgrade() -> None:
    bind = op.get_bind()

    admin_id = _obtener_role_id(bind, "ADMIN")
    funcional_id = _obtener_role_id(bind, _FUNCIONAL)
    if admin_id is None or funcional_id is None:
        return

    permisos_admin = {
        fila["permission_id"]
        for fila in bind.execute(
            sa.text(
                "SELECT permission_id FROM role_permissions WHERE role_id = :role"
            ),
            {"role": admin_id},
        ).mappings()
    }
    permisos_funcional = bind.execute(
        sa.text(
            "SELECT permission_id FROM role_permissions WHERE role_id = :role"
        ),
        {"role": funcional_id},
    ).mappings().all()

    for fila in permisos_funcional:
        permiso_id = fila["permission_id"]
        if permiso_id not in permisos_admin:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    VALUES (:id, :role, :permission, :ahora, :ahora)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "role": admin_id,
                    "permission": permiso_id,
                    "ahora": datetime.now(UTC),
                },
            )
            permisos_admin.add(permiso_id)

    bind.execute(
        sa.text("DELETE FROM role_permissions WHERE role_id = :role"),
        {"role": funcional_id},
    )
    bind.execute(
        sa.text("DELETE FROM user_roles WHERE role_id = :role"),
        {"role": funcional_id},
    )
    bind.execute(
        sa.text("DELETE FROM roles WHERE id = :role"),
        {"role": funcional_id},
    )

    # OD-DEL-12 no se revierte: la empresa anterior queda en la auditoría y
    # revertir el alcance no es seguro sin saber qué se concedió después.
