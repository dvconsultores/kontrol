"""Spec 036 — la devolución deja de ser un registro suelto y la nota, un número a mano.

La norma escribe el proceso entero y en orden: «Solicitud → Verificación física
→ Aprobación → **Entrada de inventario** → Nota de crédito vinculada → Ajuste de
IVA → Ajuste de cuenta por cobrar → Registro en libro de ventas». Cuatro actos
antes de tocar el inventario, y la nota **después**, vinculada.

Lo que había no podía sostener nada de eso. `sales_returns` guardaba el origen
como un texto libre —`source_document`— sin factura, sin despacho, sin cliente y
sin almacén, y su creación no comprobaba nada. `sales_credit_notes` recibía el
número por parámetro: ningún correlativo fiscal, ningún número de control,
ninguna línea y ningún tope contra el original. La regla de integridad del
modelo de datos dice «no ajustar por encima de cantidades/base/IVA **pendientes**
del original», y no había con qué calcular lo pendiente.

Todas las columnas nacen anulables y no hay un solo `UPDATE`: las devoluciones y
las notas anteriores no tienen esta procedencia y no se les inventa una.

Revision ID: 0054_spec036_returns
Revises: 0053_spec035_dispatch
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0054_spec036_returns"
down_revision = "0053_spec035_dispatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------- devolución
    # De dónde viene: el documento fiscal que la ampara y la salida física que la
    # produjo. Sin esto no hay forma de saber cuánto queda por devolver.
    for columna, tipo in (("customer_id", sa.String(36)), ("invoice_id", sa.String(36)),
                          ("shipment_id", sa.String(36)), ("order_id", sa.String(36)),
                          ("warehouse_id", sa.String(36)), ("location_id", sa.String(36))):
        op.add_column("sales_returns", sa.Column(columna, tipo, nullable=True))
    # Los cuatro actos del flujo, cada uno con su huella. Un proceso que no dice
    # quién hizo qué y cuándo no es un control.
    for acto in ("requested", "received", "inspected", "approved", "reentered"):
        op.add_column("sales_returns", sa.Column(f"{acto}_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("sales_returns", sa.Column(f"{acto}_by", sa.String(36), nullable=True))
    op.add_column("sales_returns", sa.Column("status_reason", sa.Text(), nullable=True))

    op.create_foreign_key("fk_sales_returns_customer", "sales_returns", "parties", ["customer_id"], ["id"])
    op.create_foreign_key("fk_sales_returns_invoice", "sales_returns", "sales_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_sales_returns_shipment", "sales_returns", "shipments", ["shipment_id"], ["id"])
    op.create_foreign_key("fk_sales_returns_order", "sales_returns", "sales_orders", ["order_id"], ["id"])
    op.create_foreign_key("fk_sales_returns_warehouse", "sales_returns", "warehouses", ["warehouse_id"], ["id"])
    op.create_foreign_key("fk_sales_returns_location", "sales_returns", "warehouse_locations", ["location_id"], ["id"])
    op.create_index("ix_sales_returns_invoice_id", "sales_returns", ["invoice_id"])

    # ------------------------------------------------------------ línea devuelta
    # Contra qué línea de la factura se devuelve: es lo que permite comparar lo
    # devuelto acumulado con lo despachado y negarse a pasarse.
    op.add_column("sales_return_lines", sa.Column("invoice_line_id", sa.String(36), nullable=True))
    op.add_column("sales_return_lines", sa.Column("lot_id", sa.String(36), nullable=True))
    op.add_column("sales_return_lines", sa.Column("serial_id", sa.String(36), nullable=True))
    # Lo que la inspección acepta puede ser menos que lo recibido, y el destino es
    # por línea: media caja puede volver a existencia y la otra media no.
    op.add_column("sales_return_lines", sa.Column("accepted_base_quantity", sa.Numeric(18, 6), nullable=True))
    op.add_column("sales_return_lines", sa.Column("disposition", sa.String(32), nullable=True))
    op.add_column("sales_return_lines", sa.Column("inspection_note", sa.Text(), nullable=True))
    op.create_foreign_key("fk_sales_return_lines_invoice_line", "sales_return_lines",
                          "sales_invoice_lines", ["invoice_line_id"], ["id"])
    # `D0-10` concede a la 036 exactamente dos destinos. Escribir cualquier otro
    # sería inventar un estado de mercancía, y los estados tienen dueño.
    op.create_check_constraint(
        "ck_sales_return_lines_disposition", "sales_return_lines",
        "disposition IS NULL OR disposition IN ('DISPONIBLE', 'RECHAZADO')")

    # ----------------------------------------------------------- nota de crédito
    # La norma exige consecutivo propio, número de control, referencia a la
    # factura original con su fecha/número/control, motivo, líneas y montos.
    for columna, tipo in (("invoice_id", sa.String(36)), ("return_id", sa.String(36)),
                          ("fiscal_document_id", sa.String(36)), ("invoice_number", sa.String(64)),
                          ("control_number", sa.String(64)), ("cause", sa.Text()),
                          ("base_fiscal", sa.Numeric(18, 2)), ("tax_total", sa.Numeric(18, 2)),
                          ("issued_at", sa.DateTime(timezone=True)), ("issued_by", sa.String(36))):
        op.add_column("sales_credit_notes", sa.Column(columna, tipo, nullable=True))
    op.create_foreign_key("fk_sales_credit_notes_invoice", "sales_credit_notes",
                          "sales_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_sales_credit_notes_return", "sales_credit_notes",
                          "sales_returns", ["return_id"], ["id"])
    op.create_index("ix_sales_credit_notes_invoice_id", "sales_credit_notes", ["invoice_id"])

    op.create_table(
        "sales_credit_note_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("note_id", sa.String(36), sa.ForeignKey("sales_credit_notes.id"), nullable=False),
        sa.Column("invoice_line_id", sa.String(36), sa.ForeignKey("sales_invoice_lines.id"), nullable=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("base_fiscal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("uom_id", sa.String(36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("presentation_id", sa.String(36), sa.ForeignKey("presentations.id"), nullable=True),
        sa.Column("conversion_factor_snapshot", sa.Numeric(18, 6), nullable=True),
        sa.Column("base_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_sales_credit_note_lines_note_id", "sales_credit_note_lines", ["note_id"])

    # ------------------------------------------------------------ nota de débito
    # «La nota de débito no puede utilizarse como una factura independiente»: de
    # ahí el vínculo obligatorio con la factura en el servicio. No lleva
    # devolución ni efecto de inventario: su flujo no tiene etapa física.
    for columna, tipo in (("invoice_id", sa.String(36)), ("fiscal_document_id", sa.String(36)),
                          ("invoice_number", sa.String(64)), ("control_number", sa.String(64)),
                          ("cause", sa.Text()), ("base_fiscal", sa.Numeric(18, 2)),
                          ("tax_total", sa.Numeric(18, 2)),
                          ("issued_at", sa.DateTime(timezone=True)), ("issued_by", sa.String(36))):
        op.add_column("sales_debit_notes", sa.Column(columna, tipo, nullable=True))
    op.create_foreign_key("fk_sales_debit_notes_invoice", "sales_debit_notes",
                          "sales_invoices", ["invoice_id"], ["id"])
    op.create_index("ix_sales_debit_notes_invoice_id", "sales_debit_notes", ["invoice_id"])

    op.create_table(
        "sales_debit_note_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("note_id", sa.String(36), sa.ForeignKey("sales_debit_notes.id"), nullable=False),
        sa.Column("invoice_line_id", sa.String(36), sa.ForeignKey("sales_invoice_lines.id"), nullable=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=True),
        sa.Column("concept", sa.Text(), nullable=False),
        sa.Column("base_fiscal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_sales_debit_note_lines_note_id", "sales_debit_note_lines", ["note_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_debit_note_lines_note_id", table_name="sales_debit_note_lines")
    op.drop_table("sales_debit_note_lines")
    op.drop_index("ix_sales_debit_notes_invoice_id", table_name="sales_debit_notes")
    op.drop_constraint("fk_sales_debit_notes_invoice", "sales_debit_notes", type_="foreignkey")
    for columna in ("invoice_id", "fiscal_document_id", "invoice_number", "control_number",
                    "cause", "base_fiscal", "tax_total", "issued_at", "issued_by"):
        op.drop_column("sales_debit_notes", columna)

    op.drop_index("ix_sales_credit_note_lines_note_id", table_name="sales_credit_note_lines")
    op.drop_table("sales_credit_note_lines")
    op.drop_index("ix_sales_credit_notes_invoice_id", table_name="sales_credit_notes")
    op.drop_constraint("fk_sales_credit_notes_return", "sales_credit_notes", type_="foreignkey")
    op.drop_constraint("fk_sales_credit_notes_invoice", "sales_credit_notes", type_="foreignkey")
    for columna in ("invoice_id", "return_id", "fiscal_document_id", "invoice_number",
                    "control_number", "cause", "base_fiscal", "tax_total", "issued_at", "issued_by"):
        op.drop_column("sales_credit_notes", columna)

    op.drop_constraint("ck_sales_return_lines_disposition", "sales_return_lines", type_="check")
    op.drop_constraint("fk_sales_return_lines_invoice_line", "sales_return_lines", type_="foreignkey")
    for columna in ("invoice_line_id", "lot_id", "serial_id", "accepted_base_quantity",
                    "disposition", "inspection_note"):
        op.drop_column("sales_return_lines", columna)

    op.drop_index("ix_sales_returns_invoice_id", table_name="sales_returns")
    for nombre in ("location", "warehouse", "order", "shipment", "invoice", "customer"):
        op.drop_constraint(f"fk_sales_returns_{nombre}", "sales_returns", type_="foreignkey")
    op.drop_column("sales_returns", "status_reason")
    for acto in ("requested", "received", "inspected", "approved", "reentered"):
        op.drop_column("sales_returns", f"{acto}_by")
        op.drop_column("sales_returns", f"{acto}_at")
    for columna in ("customer_id", "invoice_id", "shipment_id", "order_id", "warehouse_id", "location_id"):
        op.drop_column("sales_returns", columna)
