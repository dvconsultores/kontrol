# Spec 015 · delta: suministro abierto por almacén

- **Encargo:** `OPEN_SUPPLY_BY_WAREHOUSE`, del 2026-11-13.
- **Spec dueña:** 015, planificación y reposición.
- **Autoridad de la cantidad pedida y recibida:** Spec 004 (Compras).
- **La brecha la detectó:** la Spec 018 (matriz, brecha 2). La 018 no es dueña de este delta.
- **Evidencia:** `evidence/open-supply/`.

## Requisito

Al calcular la reposición de un par (empresa, almacén, producto), la planificación debe descontar lo que ya se pidió para ese almacén y todavía no se ha recibido. Así no vuelve a sugerir unidades que ya están en camino.

## Arqueología

`evidence/open-supply/OPEN_SUPPLY_TRACEABILITY_CURRENT.md`:
- `ONE_PURCHASE_ORDER_ONE_WAREHOUSE=0`
- `REQUISITION_LINE_TO_PO_LINE_STRUCTURED=0`
- La línea de la orden no tiene almacén → `MATERIAL_DECISION_REQUIRED=1`

## Decisiones de la dueña (2026-11-13)

| Pregunta | Decisión |
|---|---|
| ¿Dónde vive el almacén destino de una cantidad pedida? | **En la línea de la orden**: `purchase_order_lines.destination_warehouse_id`. Una orden puede repartirse entre almacenes. No toca QUOTE-REQUISITION-LINK |
| ¿Qué pasa si se recibe una línea en otro almacén? | **Se bloquea**: una recepción solo admite las líneas destinadas a su almacén (409) |
| ¿Cómo se aplica la obligación? | **Obligatorio en pantalla.** Órdenes exige el almacén destino al agregar una línea y permite fijarlo en las líneas que no lo tienen. El backend lo acepta como opcional: una línea sin destino no cuenta como suministro abierto, y la pantalla lo dice |

```text
WAREHOUSE_AUTHORITY=purchase_order_lines.destination_warehouse_id
OPEN_SUPPLY_REQUIRES_QUOTE_REQUISITION_LINK=0
MATERIAL_DECISION_REQUIRED=0 (resuelta)
```

## Clarificaciones (resueltas con el código y las Specs)

| Pregunta | Respuesta |
|---|---|
| ¿Qué órdenes aportan suministro? | Solo APPROVED y PARTIALLY_RECEIVED. DRAFT, SUBMITTED y REJECTED aún no son compromiso. CANCELLED no llegará. RECEIVED ya llegó. CLOSED se cerró y su saldo ya no llegará |
| ¿Hay cancelación parcial por línea? | No existe en el modelo. La cancelación es de la orden (CANCELLED) o el cierre de su saldo (CLOSED) |
| ¿Qué cuenta como recibido? | `purchase_order_lines.quantity_received`, que la aceptación de la recepción incrementa con lo **aceptado** en unidad base (`accept_receipt`) |
| ¿Y lo rechazado en una recepción? | No es aceptado, de modo que sigue pendiente en la orden mientras esta no se cierre. Coincide con la Spec 004: la orden sigue PARTIALLY_RECEIVED |
| ¿Qué unidad se usa? | Base: `coalesce(base_quantity_ordered, quantity_ordered) − quantity_received`, con mínimo 0 por línea |
| ¿Y las líneas que no son de inventario? | `needs_inventory = false` no cuenta |
| ¿Qué pasa con las líneas históricas sin destino? | `NO_ATTRIBUTION`: no cuentan y no se rellenan. No se infiere el almacén por texto, recepciones anteriores ni almacén por defecto |
| ¿Cuándo puede cambiarse el destino? | Mientras la orden esté en DRAFT, SUBMITTED o APPROVED y la línea no tenga ninguna línea de recepción viva (de una recepción que no esté cancelada). Después queda fijo |
| ¿Y la mercancía aceptada pero sin confirmar (estado RECIBIDO)? | Ya no es suministro abierto, y tampoco es disponible vendible hasta la confirmación (Spec 021). Es un hueco transitorio previo a este ciclo: queda como deuda RECEIVED-UNCONFIRMED-PROJECTION y no se absorbe |

## Contrato

- **OSW-01. Autoridad del almacén.** `purchase_order_lines.destination_warehouse_id`, una FK nullable a `warehouses.id`. Debe ser un almacén de la empresa de la orden; si no, 404 `WAREHOUSE_NOT_FOUND`. Debe estar ACTIVE; si no, 409 `WAREHOUSE_NOT_ELIGIBLE`.
- **OSW-02. Producto.** `purchase_order_lines.product_id`.
- **OSW-03. Cantidad ordenada.** `coalesce(base_quantity_ordered, quantity_ordered)`.
- **OSW-04. Cantidad recibida.** `quantity_received` (aceptado en unidad base).
- **OSW-05. Cantidad abierta, por línea.** `max(0, ordenada − recibida)`, solo si la orden está APPROVED o PARTIALLY_RECEIVED, la línea tiene `needs_inventory` y tiene destino. Una sola autoridad, `app/modules/purchasing/open_supply.py`:
  - `cantidad_abierta(line, order_status) -> Decimal`, para una línea;
  - `suministro_abierto(db, *, company_id, warehouse_id, product_ids) -> dict[str, Decimal]`, para un lote, con una consulta agregada sin N+1.

  Las dos se prueban para que den lo mismo.
- **OSW-06. Recepciones parciales.** Orden de 100: si se aceptan 40, quedan 60 abiertas; si luego se aceptan 30 más, quedan 30; si se recibe o se cierra todo, quedan 0.
- **OSW-07. Canceladas y cerradas.** CANCELLED, CLOSED, RECEIVED, REJECTED, DRAFT y SUBMITTED aportan 0.
- **OSW-08. Varios almacenes.** El suministro se agrega por destino de la línea. Con el producto X pendiente en A (50) y en B (80), A ve 50 y B ve 80.
- **OSW-09. Integración en la planificación.** El mismo motor, `compute_plan`, sin un segundo planificador:
  - `open_supply` = suministro abierto, y `open_supply_available` = true;
  - `projected_available` = disponible + suministro abierto;
  - la cantidad sugerida pasa a `max(0, demanda proyectada + stock de seguridad − disponible proyectado)`;
  - `condition_met` usa `projected_available <= reorder_point` y sugerida > 0;
  - `coverage_days` sigue siendo la cobertura del disponible físico;
  - la necesidad guarda `trigger_open_supply`, `trigger_projected_available`, `current_open_supply` y `current_projected_available`.
- **OSW-10. Sin efecto en el inventario.** No crea movimientos, recepciones ni saldos, y no toca el costo.
- **OSW-11. Aislamiento.** El suministro solo suma órdenes de la empresa del contexto. Una línea u orden ajena da 404.
- **OSW-12. Concurrencia.** El suministro se lee con una sola consulta agregada (una foto coherente por sentencia) y sin bloqueos nuevos. La necesidad conserva su bloqueo de fila y su único episodio ACTIVE. Fijar el destino bloquea la fila de la orden.
- **OSW-13. Explicación en pantalla.**
  - **Necesidad**, en la causa y en la situación actual: disponible, suministro abierto, disponible proyectado, punto de reorden y cantidad sugerida.
  - **Requisición**: el suministro abierto del plan.
  - **Órdenes**:
    - almacén destino obligatorio al agregar una línea;
    - un panel de líneas con el pendiente y el destino («Sin almacén destino: no cuenta en la planificación»);
    - fijar el destino donde se pueda.
  - **Recepciones**: el destino de cada línea en el selector.
  - Sin UUID en ninguna pantalla.
- **OSW-14. Auditoría.**
  - Se audita `PURCHASE_ORDER_LINE_DESTINATION_SET`, con el antes y el después: `{destination_warehouse_id, destination_warehouse_code}`.
  - No se audita cada cálculo.
  - Los eventos de la necesidad no cambian.
- **OSW-15. UAT.** Pasos desde el 134 de la tarjeta de la dueña.

**Recepción (decisión de la dueña).** Si la línea de la orden tiene destino y no coincide con el almacén de la recepción, `add_receipt_line` responde 409 `RECEIPT_LINE_OTHER_WAREHOUSE`. Una línea sin destino se sigue recibiendo como hoy.

**Rutas:**
- `POST /purchasing/orders/{order_id}/lines` acepta `destination_warehouse_id` como opcional.
- `POST /purchasing/orders/{order_id}/lines/{line_id}/destination` (`compras:create`) fija o cambia el destino.
- El detalle de la orden añade a cada línea `destination_warehouse {id, code, name}`, `open_quantity` y `can_set_destination`.

**Base de datos (`MIGRATION_REQUIRED=1`):**
- `0106_open_supply_by_warehouse`:
  - `purchase_order_lines.destination_warehouse_id`, con la FK `fk_purchase_order_lines_destination_warehouse_id_warehouses` y el índice `ix_purchase_order_lines_destination_warehouse_id_product_id`;
  - 4 columnas Numeric(18,6) nullable en `replenishment_needs`.
- Sin backfill.

## Constitution gate

```text
WAREHOUSE_AUTHORITY_CLEAR=1  PRODUCT_AUTHORITY_CLEAR=1  ORDERED_QUANTITY_AUTHORITY_CLEAR=1
RECEIVED_QUANTITY_AUTHORITY_CLEAR=1  CANCELLED_QUANTITY_AUTHORITY_CLEAR=1 (estado de la cabecera)
STATUS_SEMANTICS_CLEAR=1  PARTIAL_RECEIPT_SUPPORTED=1  CROSS_COMPANY_ISOLATION_CLEAR=1
MATERIAL_DECISION_REQUIRED=0 (resuelta por la dueña)  CONSTITUTION_GATE=PASS
```

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T015-OSW-0 Arqueología, decisión, delta y diseño | CLAUDE | n-a | NO | n-a | n-a | documentos | — | gate PASS |
| T015-OSW-A Backend: migración 0106, modelos, `open_supply.py`, Compras (destino, bloqueo de recepción, detalle), motor, necesidad, catálogo, guardias y pruebas | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | ver brief | pytest en PostgreSQL | OSW-01 a OSW-12 y OSW-14 |
| T015-OSW-B Pantallas, Vitest y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | ver brief | Vitest y E2E en Chrome sobre PostgreSQL | OSW-13, 1280, 390 y 320 |
| T015-OSW-C Evidencia, tarjeta de UAT y cierre | CLAUDE | n-a | NO | n-a | n-a | documentos | — | — |

## Trazabilidad

| Requisito | Contratos | Pruebas |
|---|---|---|
| Descontar lo pedido y no recibido por almacén | OSW-01 a OSW-05, OSW-09 | backend: fórmula, parcial, varios almacenes e integración; E2E |
| Recepciones parciales, canceladas y cerradas | OSW-06, OSW-07 | backend |
| No volver a sugerir lo ya pedido | OSW-09 | backend (tick con orden aprobada) y E2E |
| Sin efecto en el inventario | OSW-10 | backend (movimientos sin cambio) |
| Seguridad | OSW-11, OSW-12 | backend (aislamiento y destino ajeno) |
| Explicación y auditoría | OSW-13, OSW-14 | Vitest, E2E y catálogo |
| Recepción en otro almacén bloqueada | decisión de la dueña | backend 409 |
