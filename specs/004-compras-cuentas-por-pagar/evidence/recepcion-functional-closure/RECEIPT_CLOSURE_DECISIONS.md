# Recepción · decisiones de cierre de la máquina

## QUALITY_PENDING

- `QUALITY_PENDING_ENTRY_CONTRACT`: `POST /purchasing/receipts/{id}/quality` **sin veredicto** desde `CONFIRMED`, con al menos una línea. Es la operación que el contrato de API ya nombra «Calidad (→ QUALITY_PENDING)». Permiso `compras:quality`: calidad toma la recepción.
- `QUALITY_PENDING_EXIT_CONTRACT`: el veredicto (`APPROVED` o `REJECTED`) solo se registra en `QUALITY_PENDING`. `REJECTED` lleva a `REJECTED`; `APPROVED` permite aceptar, que lleva a `ACCEPTED` o `PARTIALLY_ACCEPTED`.
- Una vez en calidad no se añaden líneas. Inspeccionar sigue permitido.

## PARTIALLY_ACCEPTED

`PARTIAL_ACCEPTANCE_RULE`: al aceptar, en la unidad en que se tecleó cada línea:

- todas las líneas con aceptado = recibido → `ACCEPTED`;
- alguna línea con aceptado < recibido y total aceptado > 0 → `PARTIALLY_ACCEPTED`;
- total aceptado = 0 → no se acepta: 409 `RECEIPT_NOTHING_ACCEPTED`. Una recepción sin nada que aceptar se rechaza con el veredicto «no conforme».

Se mide contra lo **recibido**, no contra lo pedido: la orden ya tiene su propio `PARTIALLY_RECEIVED`.

## REJECTED

`RECEIPT_REJECTED` es el veredicto de calidad sobre la recepción entera. `LINE_QUANTITY_REJECTED` es la cantidad rechazada de una línea, que deja la recepción en `PARTIALLY_ACCEPTED` si se acepta lo demás. No se mezclan.

## CLOSED

`RECEIPT_CLOSE_TRIGGER_CONTRACT = MANUAL_OPERATION` con condiciones tomadas de los dueños de cada etapa:

- `ACCEPTED` o `PARTIALLY_ACCEPTED`: solo con la confirmación de inventario de la Spec 021 hecha (`confirmation_status = CONFIRMADA`); antes, 409 `RECEIPT_NOT_RECONCILED`.
- `REJECTED`: solo sin incidencias vivas de la Spec 020; antes, 409 `RECEIPT_INCIDENTS_OPEN`.

Ninguna fuente fija un disparador automático. El patrón hermano de la orden (`/orders/{id}/close`) es manual, y cerrar automáticamente al confirmar mezclaría las dos dimensiones que la Spec 021 separó a propósito. Cerrar no mueve inventario, no recalcula, no borra incidencias ni toca lotes, seriales u órdenes. Una recepción cerrada no admite incidencias nuevas.

## CANCELLED

`CANCELLATION_REQUIREMENT_STATUS = CANCELLATION_CONDITIONAL`: solo `DRAFT`.

- Fuentes: el motor (`DRAFT → CANCELLED`), la cuestión 7 del ciclo 019, y que todo documento de compra con borrador se anula desde él (orden, factura, pago).
- Un borrador no tiene efectos definitivos: el inventario solo entra al aceptar.
- `CONFIRMED` no se anula: ya está en manos de calidad o a punto, y FR-004-031 no lo prevé.
- Motivo obligatorio; permiso `compras:approve`, como la anulación de la orden; sin incidencias vivas.
- El motivo queda en la auditoría, sin columna nueva.

## Auditoría

Un evento canónico de transición, `RECEIPT_TRANSITIONED` (`source`, `target`, `reason`), como el resto de documentos de compra (`PURCHASE_ORDER_TRANSITIONED`...), para confirmar, entregar a calidad, cerrar y anular. Los hechos con evento propio lo conservan: `RECEIPT_QUALITY_RECORDED` y `RECEIPT_ACCEPTED`, que añade `status` para distinguir aceptación total y parcial.

## Lote regulatorio

`REQUIRES_LOT_APPLIES_TO_PURCHASE_RECEIPT = 0`. `RegulatoryProfile.requires_lot` es de la Spec 008 de traslados (FR-008-005); su `operation` vale `DESPACHO` por defecto y solo se evalúa en `evaluate_shipment`. Ningún requisito lo aplica a la recepción de compra. `RECEPCION_LOTE_REGULATORIO_STATUS = NOT_IN_SCOPE`. Que el despacho tampoco lo exija es una cuestión de la Spec 008.

## Pantalla

La pantalla no decide transiciones: muestra las acciones que el backend publica en `allowed_actions` de cada recepción, y el backend vuelve a validar.
