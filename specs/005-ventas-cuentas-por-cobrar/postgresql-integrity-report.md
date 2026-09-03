# SPEC 030 — INTEGRIDAD EN POSTGRESQL (ORM = ALEMBIC = POSTGRESQL)

| Restricción | ORM (`models.py`) | Alembic (`0043`) | PostgreSQL 18.6 (instalación limpia) | Prueba |
|---|---|---|---|---|
| `uq_reservations_active_line` (parcial) | `Index(..., unique=True, postgresql_where=…).ddl_if(postgresql)` | `CREATE UNIQUE INDEX … WHERE status = 'ACTIVE' AND source_line_id IS NOT NULL` | presente | hostil `test_5` → 23505 |
| `ck_reservations_quantity_positive` | `CheckConstraint("quantity > 0", name="quantity_positive")` (convención → nombre completo) | `ALTER TABLE … ADD CONSTRAINT ck_reservations_quantity_positive` | presente | hostil `test_8` → 23514 |
| `uq_inventory_balances_key` | `Index(..., text("COALESCE(…)"), unique=True).ddl_if(postgresql)` | `CREATE UNIQUE INDEX … COALESCE(location_id,''), …` | presente | hostil `test_10` → 23505 |
| `ck_inventory_balances_reserved_nonneg` | `CheckConstraint("qty_reserved >= 0", name="reserved_nonneg")` | SQL directo | presente | hostiles `test_6`, `test_7` → 23514 |
| FK `source_order_id → sales_orders` | `ForeignKey("sales_orders.id")` | `sa.ForeignKey(name="fk_reservations_source_order_id_sales_orders")` | presente | hostil `test_2` → 23503 |
| FK `source_line_id → sales_order_lines` | ídem | ídem | presente | hostil `test_3` → 23503 |
| FK `company_id`, `warehouse_id` (existentes) | — | — | presentes | hostiles `test_1`, `test_4` → 23503 |
| Línea ↔ pedido | no expresable sin clave compuesta; lo asegura el servicio | — | — | hostil `test_9` (medición por consulta) |

Lección N7 aplicada: todo lo anterior está en el ORM **y** en la migración, porque las suites
levantan el esquema con `create_all`. La convención de nombres (`ck_%(table_name)s_%(constraint_name)s`)
obligó a declarar los `CHECK` con nombre corto en el ORM y con SQL directo en Alembic para que ambos
produzcan el mismo identificador (verificado en `test_spec030_migration_0043.py::test_el_indice_parcial_y_los_checks_existen_con_el_nombre_del_orm`).

Autoridad de disponibilidad: sin cambios. `InventoryMovement → InventoryBalance.qty_on_hand`;
`Reservation ACTIVE → qty_reserved`; `qty_available = qty_on_hand − qty_reserved` sobre la fila
`DISPONIBLE`. No se creó ninguna vista, tabla ni cálculo paralelo (§37).
