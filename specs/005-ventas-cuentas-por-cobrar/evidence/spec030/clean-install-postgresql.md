# Instalación limpia — PostgreSQL 18.6 vacío (base `kinstall`) — 2026-09-02T23:40:19Z

Ciclo verificado: `upgrade head` → `downgrade 0042_spec029_origin` → `upgrade head`, sin errores.

## Revisión aplicada

```
0043_spec030_reservation (head)
```

## Objetos de la Spec 030 en el catálogo

| Tipo | Objeto |
|---|---|
| columna | `companies.reservation_ttl_days` |
| columna | `reservations.oversell` |
| columna | `reservations.release_reason` |
| columna | `reservations.released_at` |
| columna | `reservations.released_by` |
| columna | `reservations.source_line_id` |
| columna | `reservations.source_order_id` |
| columna | `reservations.source_type` |
| columna | `reservations.trigger` |
| columna | `sales_orders.released_at` |
| columna | `sales_orders.status_reason` |
| columna | `sales_orders.submitted_at` |
| permiso | `ventas:submit` |
| restricción | `ck_inventory_balances_reserved_nonneg` |
| restricción | `ck_reservations_quantity_positive` |
| restricción | `fk_reservations_source_line_id_sales_order_lines` |
| restricción | `fk_reservations_source_order_id_sales_orders` |
| índice | `ix_reservations_source_order` |
| índice | `uq_inventory_balances_key` |
| índice | `uq_reservations_active_line` |
