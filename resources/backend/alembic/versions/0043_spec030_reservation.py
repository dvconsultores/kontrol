"""Spec 030 — la reserva nace al confirmar el pedido.

Revision ID: 0043_spec030_reservation
Revises: 0042_spec029_origin

`RESERVATION TRIGGER = ORDER_CONFIRMATION` (ADR-D0-003 v2). Hasta aquí la
reserva nacía al aprobar el crédito, sin bloqueo, sin cantidad base, sin
liberarse al cancelar y sin saber a qué línea pertenecía. Esta migración da al
modelo lo que la política exige y clasifica lo que ya existía **sin inventarle
un origen**:

- `reservations`: identidad estructural (`source_type`, `source_order_id`,
  `source_line_id`), `trigger` con el que nació, `oversell`, ciclo de liberación
  (`released_at/by`, `release_reason`), una sola reserva ACTIVE por línea
  (índice único parcial) y `quantity > 0`.
- `inventory_balances`: una fila por clave de saldo (índice único con COALESCE)
  y `qty_reserved >= 0`.
- `sales_orders`: `RESERVED → RELEASED` (mismo significado: aprobado y con
  reserva), `APPROVED → RELEASED` (nunca fue observable), `CREDIT_PENDING →
  SUBMITTED` (emitido a la espera de crédito). Los dos últimos grupos **no**
  tienen reserva bajo la nueva semántica y quedan listados para revisión manual;
  la migración no reserva por ellos. Motivo y marcas de tiempo nuevas.
- `companies.reservation_ttl_days`: vigencia opcional, defecto NULL.
- Permiso `ventas:submit`, concedido a ADMIN como hizo 0013.

Clasificación de las reservas existentes (informe en
`specs/005-ventas-cuentas-por-cobrar/reservation-migration-report.md`):

  ORDER_RECONSTRUCTIBLE  `SALES_ORDER:{id}` y el pedido existe → trigger
                         LEGACY_CREDIT_APPROVAL; la línea solo si el pedido
                         tiene exactamente una línea de ese producto.
  CRITICAL_AMBIGUOUS     el pedido existe con varias líneas del producto →
                         línea NULL, listado.
  LEGACY_UNVERIFIED      patrón de pedido sin pedido en la base.
  MANUAL                 sin patrón de pedido.

`base_quantity` nulo pasa a ser la cantidad, con factor 1 y
`uom_source = LEGACY_ASSUMED_BASE`: es lo que el motor siempre supuso.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0043_spec030_reservation"
down_revision = "0042_spec029_origin"
branch_labels = None
depends_on = None


def _pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _log(msg: str) -> None:
    print(f"[0043 spec030] {msg}")


def upgrade() -> None:
    bind = op.get_bind()

    # -- pedidos: motivo y marcas de tiempo --------------------------------- #
    op.add_column("sales_orders", sa.Column("status_reason", sa.String(500), nullable=True))
    op.add_column("sales_orders", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales_orders", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))

    # -- empresa: vigencia opcional ----------------------------------------- #
    op.add_column("companies", sa.Column("reservation_ttl_days", sa.Integer(), nullable=True))

    # -- reservas: identidad, trigger, liberación ---------------------------- #
    op.add_column("reservations", sa.Column("source_type", sa.String(24), nullable=True))
    op.add_column("reservations", sa.Column(
        "source_order_id", sa.String(36),
        sa.ForeignKey("sales_orders.id", name="fk_reservations_source_order_id_sales_orders"), nullable=True))
    op.add_column("reservations", sa.Column(
        "source_line_id", sa.String(36),
        sa.ForeignKey("sales_order_lines.id", name="fk_reservations_source_line_id_sales_order_lines"), nullable=True))
    op.add_column("reservations", sa.Column("trigger", sa.String(32), nullable=True))
    op.add_column("reservations", sa.Column("oversell", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reservations", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reservations", sa.Column("released_by", sa.String(36), nullable=True))
    op.add_column("reservations", sa.Column("release_reason", sa.String(120), nullable=True))
    op.create_index("ix_reservations_source_order", "reservations", ["source_order_id"])

    # -- clasificación del legado (sin inventar origen) ---------------------- #
    rows = bind.execute(sa.text(
        "SELECT id, source_document, product_id, quantity, base_quantity FROM reservations")).fetchall()
    conteo = {"ORDER_RECONSTRUCTIBLE": 0, "CRITICAL_AMBIGUOUS": 0, "LEGACY_UNVERIFIED": 0, "MANUAL": 0,
              "BASE_ASSUMED": 0}
    ambiguas: list[str] = []
    for rid, doc, product_id, _quantity, base in rows:
        if doc and doc.startswith("SALES_ORDER:"):
            order_id = doc.split(":", 1)[1]
            existe = bind.execute(sa.text("SELECT 1 FROM sales_orders WHERE id = :o"), {"o": order_id}).fetchone()
            if existe:
                lineas = bind.execute(sa.text(
                    "SELECT id FROM sales_order_lines WHERE order_id = :o AND product_id = :p"),
                    {"o": order_id, "p": product_id}).fetchall()
                line_id = lineas[0][0] if len(lineas) == 1 else None
                if len(lineas) > 1:
                    conteo["CRITICAL_AMBIGUOUS"] += 1
                    ambiguas.append(rid)
                else:
                    conteo["ORDER_RECONSTRUCTIBLE"] += 1
                bind.execute(sa.text(
                    "UPDATE reservations SET source_type = 'SALES_ORDER', source_order_id = :o, "
                    "source_line_id = :l, trigger = 'LEGACY_CREDIT_APPROVAL' WHERE id = :i"),
                    {"o": order_id, "l": line_id, "i": rid})
            else:
                conteo["LEGACY_UNVERIFIED"] += 1
                bind.execute(sa.text(
                    "UPDATE reservations SET trigger = 'LEGACY_CREDIT_APPROVAL' WHERE id = :i"), {"i": rid})
        else:
            conteo["MANUAL"] += 1
            bind.execute(sa.text(
                "UPDATE reservations SET source_type = 'MANUAL', trigger = 'MANUAL' WHERE id = :i"), {"i": rid})
        if base is None:
            conteo["BASE_ASSUMED"] += 1
            bind.execute(sa.text(
                "UPDATE reservations SET base_quantity = quantity, conversion_factor_snapshot = 1, "
                "uom_source = COALESCE(uom_source, 'LEGACY_ASSUMED_BASE') WHERE id = :i"), {"i": rid})
    _log(f"reservas clasificadas: {conteo}")
    if ambiguas:
        _log(f"CRITICAL_AMBIGUOUS (revisión manual, línea no reconstruible): {ambiguas}")

    # Las filas ya liberadas/consumidas del despacho antiguo quedan como
    # RELEASED: la semántica con la que nacieron no se reinterpreta (P5).

    # -- reservas: integridad ------------------------------------------------ #
    invalidas = bind.execute(sa.text("SELECT count(*) FROM reservations WHERE quantity <= 0")).scalar()
    if invalidas:
        raise RuntimeError(f"[0043] {invalidas} reservas con cantidad <= 0: revisión manual antes de migrar")
    if _pg():
        op.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reservations_active_line
            ON reservations (source_line_id)
            WHERE status = 'ACTIVE' AND source_line_id IS NOT NULL
        """)
        # SQL directo: `op.create_check_constraint` aplicaría la convención de
        # nombres del metadata y duplicaría el prefijo (`ck_reservations_ck_…`),
        # dejando el nombre distinto del que declara el ORM (paridad N7).
        op.execute("ALTER TABLE reservations ADD CONSTRAINT ck_reservations_quantity_positive CHECK (quantity > 0)")

    # -- saldos: una fila por clave y reservado no negativo ------------------ #
    dup = bind.execute(sa.text(
        "SELECT count(*) FROM (SELECT company_id, warehouse_id, COALESCE(location_id, ''), product_id, "
        "COALESCE(lot_id, ''), COALESCE(serial_id, ''), state, count(*) c FROM inventory_balances "
        "GROUP BY 1,2,3,4,5,6,7 HAVING count(*) > 1) d")).scalar()
    if dup:
        raise RuntimeError(f"[0043] {dup} claves de saldo duplicadas en inventory_balances: "
                           "ejecutar recompute_balances y revisar antes de migrar")
    negativos = bind.execute(sa.text("SELECT count(*) FROM inventory_balances WHERE qty_reserved < 0")).scalar()
    if negativos:
        # Un reservado negativo es una liberación de más: no es información,
        # es un contador roto. Se corrige y se informa.
        _log(f"qty_reserved negativo en {negativos} saldos: se lleva a 0 (revisión manual)")
        bind.execute(sa.text(
            "UPDATE inventory_balances SET qty_reserved = 0, qty_available = qty_on_hand WHERE qty_reserved < 0"))
    if _pg():
        op.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_balances_key
            ON inventory_balances (company_id, warehouse_id, COALESCE(location_id, ''), product_id,
                                   COALESCE(lot_id, ''), COALESCE(serial_id, ''), state)
        """)
        op.execute("ALTER TABLE inventory_balances ADD CONSTRAINT ck_inventory_balances_reserved_nonneg "
                   "CHECK (qty_reserved >= 0)")

    # -- pedidos: estados ---------------------------------------------------- #
    for viejo, nuevo, nota in (
        ("RESERVED", "RELEASED", "aprobado y reservado: mismo significado"),
        ("APPROVED", "RELEASED", "estado nunca observable; sin reserva propia → revisión manual"),
        ("CREDIT_PENDING", "SUBMITTED", "emitido a la espera de crédito; SIN reserva → revisión manual"),
    ):
        ids = [r[0] for r in bind.execute(
            sa.text("SELECT id FROM sales_orders WHERE status = :s"), {"s": viejo}).fetchall()]
        if ids:
            _log(f"sales_orders {viejo} → {nuevo}: {len(ids)} ({nota}): {ids}")
            bind.execute(sa.text("UPDATE sales_orders SET status = :n WHERE status = :s"), {"n": nuevo, "s": viejo})

    # -- permiso ventas:submit ---------------------------------------------- #
    perm = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE resource = 'ventas' AND action = 'submit'")).fetchone()
    if perm:
        perm_id = perm[0]
    else:
        perm_id = str(uuid.uuid4())
        bind.execute(sa.text(
            "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, 'ventas', 'submit', 'COMPANY')"),
            {"id": perm_id})
    admin = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")).fetchone()
    if admin:
        ya = bind.execute(sa.text(
            "SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
            {"r": admin[0], "p": perm_id}).fetchone()
        if not ya:
            bind.execute(sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :r, :p)"),
                {"id": str(uuid.uuid4()), "r": admin[0], "p": perm_id})


def downgrade() -> None:
    bind = op.get_bind()
    # Solo RELEASED vuelve a RESERVED: SUBMITTED ya no distingue el legado
    # CREDIT_PENDING, y no se inventa.
    bind.execute(sa.text("UPDATE sales_orders SET status = 'RESERVED' WHERE status = 'RELEASED'"))
    if _pg():
        op.execute("ALTER TABLE inventory_balances DROP CONSTRAINT IF EXISTS ck_inventory_balances_reserved_nonneg")
        op.execute("ALTER TABLE inventory_balances DROP CONSTRAINT IF EXISTS "
                   "ck_inventory_balances_ck_inventory_balances_reserved_nonneg")
        op.execute("DROP INDEX IF EXISTS uq_inventory_balances_key")
        op.execute("ALTER TABLE reservations DROP CONSTRAINT IF EXISTS ck_reservations_quantity_positive")
        op.execute("ALTER TABLE reservations DROP CONSTRAINT IF EXISTS ck_reservations_ck_reservations_quantity_positive")
        op.execute("DROP INDEX IF EXISTS uq_reservations_active_line")
    op.drop_index("ix_reservations_source_order", table_name="reservations")
    for col in ("release_reason", "released_by", "released_at", "oversell", "trigger",
                "source_line_id", "source_order_id", "source_type"):
        op.drop_column("reservations", col)
    op.drop_column("companies", "reservation_ttl_days")
    for col in ("released_at", "submitted_at", "status_reason"):
        op.drop_column("sales_orders", col)
