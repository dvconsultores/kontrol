"""Referencias de ubicación a clave foránea real (Spec 008, F2).

Migración de **datos y esquema** gobernada por `migration-0018-policy.md`, que
es normativa. El orden es obligatorio y está diseñado para poder abortar sin
daño:

  1. Clasificar cada referencia. Sin escribir.
  2. Si hay una sola crítica: emitir el reporte y **abortar**.
  3. Reparar las reconstruibles.
  4. Anular las anulables, preservando el valor original.
  5. Copiar el texto legado a `legacy_path`.
  6. Imponer las claves foráneas.

Está **prohibido** anular una referencia inválida solo para que la migración
termine (R-008-4). Una referencia crítica irrecuperable bloquea (R-008-5).

`zone`/`aisle`/`rack` son texto libre ambiguo: se conservan literalmente y
**no** se convierten en zonas, pasillos ni racks. Crear la jerarquía es una
decisión del cliente, no de una migración (CL-008-15).

Esta migración lee datos: **no** es válida en modo offline (`--sql`) y no debe
evidenciarse así.

Revision ID: 0018_location_fk_and_legacy
Revises: 0017_warehouse_structure
Create Date: 2026-08-30
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0018_location_fk_and_legacy"
down_revision = "0017_warehouse_structure"
branch_labels = None
depends_on = None

VALID = "VALID_REFERENCE"
RECONSTRUCTIBLE = "RECONSTRUCTIBLE_ORPHAN"
NULL_ALLOWED = "NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED"
CRITICAL = "CRITICAL_NON_RECONSTRUCTIBLE"

# Las dos columnas que se convierten. `inventory_movements.location_id` ya era
# clave foránea desde el origen y por eso es dato íntegro: sirve como fuente de
# reconstrucción, no como objetivo de conversión.
TARGETS = (
    ("inventory_balances", "location_id"),
    ("stock_count_lines", "location_id"),
)


class MigrationBlocked(RuntimeError):
    """Aborta la migración por referencia crítica irrecuperable (R-008-5)."""


def _emit(report: dict) -> None:
    print("\n===== REPORTE DE MIGRACIÓN 0018 =====")
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, indent=2, ensure_ascii=False))
    for row in report["details"]:
        print(f"  [{row['classification']}] {row['table_name']}.{row['column_name']} "
              f"id={row['row_id']} legacy={row['legacy_value']} -> {row['new_value']} "
              f"· {row['justification']}")
    print("===== FIN DEL REPORTE =====\n")


def _classify(bind, table: str, column: str, report: dict) -> None:
    """Recorre una tabla y clasifica cada referencia. **No escribe nada.**"""
    known = {row[0] for row in bind.execute(sa.text("SELECT id FROM warehouse_locations"))}

    # `critical_signal` es lo que distingue la clase C de la D: dato vivo cuya
    # pérdida alteraría inventario o un conteo ya cerrado.
    if table == "inventory_balances":
        rows = bind.execute(sa.text(
            f"SELECT id, {column}, company_id, warehouse_id, "
            f"       (COALESCE(qty_on_hand,0) <> 0 OR COALESCE(qty_reserved,0) <> 0) AS critical_signal "
            f"FROM {table} WHERE {column} IS NOT NULL"
        )).fetchall()
    else:
        rows = bind.execute(sa.text(
            f"SELECT l.id, l.{column}, c.company_id, c.warehouse_id, "
            f"       (COALESCE(l.counted_qty,0) <> 0 OR c.status IN ('CLOSED','APPROVED','POSTED')) AS critical_signal "
            f"FROM {table} l JOIN stock_counts c ON c.id = l.count_id "
            f"WHERE l.{column} IS NOT NULL"
        )).fetchall()

    for row_id, legacy, company_id, warehouse_id, critical_signal in rows:
        report["total_rows_checked"] += 1
        if legacy in known:
            report["valid_references"] += 1
            continue

        report["orphan_references"] += 1

        # --- Clase B: reconstrucción determinista y unívoca ---
        # Única fuente admitida: `inventory_movements`, que es clave foránea
        # real desde el origen. El texto de `legacy_path` queda excluido: usarlo
        # sería inventar jerarquía por la puerta de atrás (R-008-4).
        candidates = {
            candidate for (candidate,) in bind.execute(
                sa.text(
                    "SELECT DISTINCT m.location_id FROM inventory_movements m "
                    "WHERE m.warehouse_id = :wh AND m.location_id IS NOT NULL"
                ), {"wh": warehouse_id},
            )
            if candidate in known
        }
        if len(candidates) == 1:
            new_value = candidates.pop()
            report["reconstructed_references"] += 1
            report["details"].append({
                "table_name": table, "column_name": column, "row_id": row_id,
                "company_id": company_id, "legacy_value": legacy, "new_value": new_value,
                "classification": RECONSTRUCTIBLE, "action_applied": "RECONSTRUCTED",
                "justification": "Candidata única desde inventory_movements del mismo almacén",
            })
            report["_repairs"].append((table, column, row_id, legacy, new_value))
            continue

        # Dos o más candidatas no es «la más probable»: es ambigüedad, y sobre
        # dato vivo degrada a crítica.
        ambiguous = len(candidates) > 1

        # --- Clase C frente a D ---
        has_quantity = bool(critical_signal)
        if has_quantity or ambiguous:
            report["critical_orphans"] += 1
            report["details"].append({
                "table_name": table, "column_name": column, "row_id": row_id,
                "company_id": company_id, "legacy_value": legacy, "new_value": None,
                "classification": CRITICAL, "action_applied": "BLOCKED",
                "justification": ("Saldo vivo o conteo cerrado, irrecuperable" if has_quantity
                                  else "Reconstrucción ambigua: más de una candidata"),
            })
            continue

        report["nulled_with_justification"] += 1
        report["details"].append({
            "table_name": table, "column_name": column, "row_id": row_id,
            "company_id": company_id, "legacy_value": legacy, "new_value": None,
            "classification": NULL_ALLOWED, "action_applied": "NULLED",
            "justification": ("Columna nullable en el modelo; sin saldo vivo ni conteo cerrado; "
                              "sin efecto sobre totales, Kardex ni conteos cerrados"),
        })
        report["_nulls"].append((table, column, row_id, legacy))


def upgrade() -> None:
    bind = op.get_bind()

    for table, _column in TARGETS:
        op.add_column(table, sa.Column("legacy_location_id", sa.String(36), nullable=True))

    report: dict = {
        "migration_id": revision,
        "database_version": bind.dialect.name,
        "total_rows_checked": 0,
        "valid_references": 0,
        "orphan_references": 0,
        "reconstructed_references": 0,
        "nulled_with_justification": 0,
        "critical_orphans": 0,
        "migration_blocked": False,
        "details": [],
        "_repairs": [],
        "_nulls": [],
    }

    # 1. Clasificar. Nada se ha escrito todavía.
    for table, column in TARGETS:
        _classify(bind, table, column, report)

    # 2. Evaluar el bloqueo antes de tocar una sola fila.
    if report["critical_orphans"]:
        report["migration_blocked"] = True
        _emit(report)
        raise MigrationBlocked(
            f"{report['critical_orphans']} referencias críticas irrecuperables. "
            "La migración se detiene sin escribir: resuélvalas y vuelva a ejecutar "
            "(migration-0018-policy.md §2, clase D)."
        )

    # 3. Reparar las reconstruibles, conservando el valor anterior.
    for table, column, row_id, legacy, new_value in report["_repairs"]:
        bind.execute(sa.text(
            f"UPDATE {table} SET {column} = :new, legacy_location_id = :legacy WHERE id = :id"
        ), {"new": new_value, "legacy": legacy, "id": row_id})

    # 4. Anular las anulables. El valor original **nunca** se pierde.
    for table, column, row_id, legacy in report["_nulls"]:
        bind.execute(sa.text(
            f"UPDATE {table} SET {column} = NULL, legacy_location_id = :legacy WHERE id = :id"
        ), {"legacy": legacy, "id": row_id})

    # 5. Texto legado a `legacy_path`. Sin crear ninguna zona ni pasillo.
    op.execute(
        "UPDATE warehouse_locations SET legacy_path = "
        "  TRIM(BOTH ' / ' FROM CONCAT_WS(' / ', zone, aisle, rack)) "
        "WHERE (zone IS NOT NULL OR aisle IS NOT NULL OR rack IS NOT NULL)"
        if bind.dialect.name == "postgresql" else
        "UPDATE warehouse_locations SET legacy_path = "
        "  COALESCE(zone,'') || ' / ' || COALESCE(aisle,'') || ' / ' || COALESCE(rack,'') "
        "WHERE (zone IS NOT NULL OR aisle IS NOT NULL OR rack IS NOT NULL)"
    )
    for column in ("zone", "aisle", "rack", "capacity"):
        op.drop_column("warehouse_locations", column)

    # 6. Imponer las claves foráneas.
    for table, column in TARGETS:
        op.create_foreign_key(f"fk_{table}_location", table, "warehouse_locations", [column], ["id"])

    # 7. Permisos que la Spec 008 añade al recurso existente `organization`.
    #    No se crea un sistema paralelo: se extiende el de la Spec 003 con la
    #    convención vigente `recurso:acción`.
    _grant_permissions(bind)

    report.pop("_repairs")
    report.pop("_nulls")
    _emit(report)


def _grant_permissions(bind) -> None:
    admin = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")
    ).fetchone()
    if not admin:
        return
    for action in ("delete", "manage_structure"):
        row = bind.execute(
            sa.text("SELECT id FROM permissions WHERE resource = 'organization' AND action = :a"),
            {"a": action},
        ).fetchone()
        if row:
            permission_id = row[0]
        else:
            permission_id = str(uuid.uuid4())
            bind.execute(
                sa.text("INSERT INTO permissions (id, resource, action, scope_type) "
                        "VALUES (:id, 'organization', :a, 'COMPANY')"),
                {"id": permission_id, "a": action},
            )
        granted = bind.execute(
            sa.text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
            {"r": admin[0], "p": permission_id},
        ).fetchone()
        if not granted:
            bind.execute(
                sa.text("INSERT INTO role_permissions (id, role_id, permission_id) "
                        "VALUES (:id, :r, :p)"),
                {"id": str(uuid.uuid4()), "r": admin[0], "p": permission_id},
            )


def downgrade() -> None:
    # Retira las claves foráneas y conserva `legacy_path` y
    # `legacy_location_id`: los valores anulados quedan disponibles para una
    # restauración explícita, decidida por una persona.
    for table, _column in TARGETS:
        op.drop_constraint(f"fk_{table}_location", table, type_="foreignkey")
    for column, size in (("zone", 64), ("aisle", 64), ("rack", 64)):
        op.add_column("warehouse_locations", sa.Column(column, sa.String(size), nullable=True))
    op.add_column("warehouse_locations", sa.Column("capacity", sa.Float(), nullable=True))
