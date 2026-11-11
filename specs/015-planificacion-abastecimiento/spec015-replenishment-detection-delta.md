# Spec 015 · Delta: detección automática de necesidad de reposición

**Estado:** 2026-11-10.

**Fuente:** IMP-01 «Detectar necesidad de reposición o compra», que la matriz completa de la Spec 018 marca PARTIAL porque hoy la necesidad la detecta una persona al consultar.

**Autorización de implement:** encargo de la dueña `SPEC015_AUTOMATIC_REPLENISHMENT_DETECTION`, del 2026-11-10.

**Principio:** detección automática y decisión humana.
- El sistema detecta la condición, la guarda, la avisa y la resuelve.
- No crea requisiciones ni órdenes de compra.

## Autoridades (no se reemplaza ninguna)

| Hecho | Autoridad |
|---|---|
| Cálculo de planificación y recomendación | `planning/engine.py: compute_plan` (Spec 015) |
| Trabajo periódico sin petición HTTP | `scheduler/registry.py` y el tick de la Spec 047 (ADR-D0-015) |
| Alerta | `notifications/service.py: crear_alerta` (Spec 047) |
| Requisición y línea con instantánea | `planning/requisitions.py: add_planned_line` (Spec 015) |
| Saldo y movimientos | Inventario |

## Decisiones

| ID | Decisión |
|---|---|
| RD-01 | La política gana `auto_replenishment_enabled` (booleano, **falso** por defecto en la migración). Las políticas existentes siguen igual hasta que se active. No se añade `trigger_method` a la política: hay un solo método, y queda registrado en cada necesidad. |
| RD-02 | **Condición** `AVAILABLE_AT_OR_BELOW_REORDER_POINT_V1`, que se cumple si `compute_plan` da `status = OK`, `available <= reorder_point` y `recommended_quantity > 0`. Sin política (`PLAN_NOT_CONFIGURED`) o sin historia (`INSUFFICIENT_HISTORY`) no hay necesidad. Disponible 0, punto 0 y sugerencia 0 tampoco son necesidad. |
| RD-03 | Entidad `ReplenishmentNeed` (`replenishment_needs`), propiedad de la Spec 015, con dos partes: la **instantánea de activación**, inmutable (el cálculo que la abrió, completo), y el **estado actual** (última evaluación). Estados: `ACTIVE` y `RESOLVED`. Motivos de resolución: `CONDITION_CLEARED`, `PLAN_UNAVAILABLE`, `POLICY_DISABLED`, `PRODUCT_INACTIVE` y `WAREHOUSE_INACTIVE`. |
| RD-04 | Como máximo una necesidad `ACTIVE` por empresa, almacén y producto. Lo garantiza la base con un índice único parcial. Una necesidad resuelta no se reabre: si la condición vuelve, nace otra (otro episodio) y la historia se conserva. |
| RD-05 | Manejador `planning_replenishment_detection`, Spec dueña `015`, con recuperación `OWNER_IDEMPOTENT`: evalúa el estado actual, así que un tick perdido no exige repetir nada y los efectos son idempotentes por clave. El manejador solo invoca `evaluate_replenishment_needs`. |
| RD-06 | Universo por tick. Primero se reevalúan las necesidades `ACTIVE`, para resolverlas. Después, por empresa con alguna política activa con detección encendida, los almacenes activos cuya política resuelta (precedencia publicada: la de almacén gana a la de empresa) tiene la detección encendida, y en cada uno los productos con movimientos en él. Tope operacional por tick, con un cursor por empresa (`replenishment_scan_cursors`): lo que no cabe entra en los ticks siguientes. Cada candidato va en su propia transacción y se cuentan vistos, procesados, omitidos y fallidos. |
| RD-07 | **Alerta del sistema, no regla configurable.** Las reglas de la 047 traducen hechos de la 045 en efectos para destinatarios. Una alerta no tiene destinatarios: la ve quien tiene `alertas:view` y el permiso del origen. Por eso Spec 015 crea la alerta directamente con el contrato `crear_alerta`. Datos de la alerta: origen `ReplenishmentNeed`, que exige `compras:view`; `route_key` `replenishment_need`; categoría `replenishment.need_detected`; severidad `WARNING`; mensaje `replenishment.need_detected.alert` con producto y almacén; dedupe `replenishment-need:{need_id}`. No se crea tarea. |
| RD-08 | Al resolver la necesidad se resuelve su alerta con un contrato nuevo de la 047, `resolver_alerta_de_sistema`, por clave de dedupe: estado `RESOLVED` y `resolved_at`, sin borrar. `resolver_por_origen` solo cierra lo que abrieron reglas con `auto_close`, por eso hace falta este contrato. |
| RD-09 | Trazabilidad: `requisition_line_plans.replenishment_need_id` (FK) y `add_planned_line` acepta `replenishment_need_id`, validando empresa, almacén y producto. Crear la requisición **no** resuelve la necesidad: la condición de inventario sigue hasta que cambie de verdad. El detalle de la necesidad lista sus requisiciones. |
| RD-10 | Auditoría: `REPLENISHMENT_NEED_DETECTED` y `REPLENISHMENT_NEED_RESOLVED` (actor de sistema, fuente `SCHEDULER`). La línea creada desde una necesidad ya queda en `REQUISITION_LINE_PLANNED`, que gana la clave `replenishment_need_id`. No hay evento redundante de «requisición iniciada». |
| RD-11 | Permisos: ver necesidades exige `compras:view`; crear la requisición, `compras:create`; configurar la detección, `maestros` (política). La alerta no concede permisos. |
| RD-12 | UI: Compras → Planificación → «Necesidades de reposición» (lista con filtros por estado, almacén y búsqueda, más el detalle). La alerta lleva al detalle. «Crear requisición» abre el flujo real de requisición con el almacén, el producto y la cantidad sugerida precargados, y la línea guarda la necesidad. |

## Fuera de alcance

- Suministro abierto por almacén (`OPEN_SUPPLY_NOT_AVAILABLE = 1`).
- Costo estimado de la línea.
- Edición de líneas de requisición.
- Compra automática.
