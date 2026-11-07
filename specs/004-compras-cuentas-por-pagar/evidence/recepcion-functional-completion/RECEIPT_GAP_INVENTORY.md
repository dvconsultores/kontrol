# Recepción · inventario de huecos

Reproducidos en rojo antes de corregir, salvo donde se indica.

| Hueco | Medida | Resultado |
|---|---|---|
| GAP-A selector de orden | `ORDER_SELECTOR_TRUNCATED = 1`: 20 de 26, y la orden 21 no era visible aunque era recibible | Corregido: búsqueda y carga en servidor |
| GAP-B `identification_ok` | `IDENTIFICATION_OK_HARDCODED = 1` | Corregido: se declara |
| GAP-C `reference_ok` | `REFERENCE_OK_HARDCODED = 1` | Corregido: se declara |
| GAP-D histórico | `LEGACY_MISMATCH_ACCEPTED = 1`. Con la línea A y el producto B: movimiento de B, costo de A, recibido en A | Corregido: 409 sin efectos |
| GAP-E almacén | `INACTIVE`, `BLOCKED` y `MAINTENANCE` aceptados al crear y al aceptar | Corregido: solo `ACTIVE`, en backend y pantalla |

## Encontrados en este ciclo

| Hueco | Medida | Resultado |
|---|---|---|
| Estados recibibles repetidos | `create_receipt` y `allowed_actions.receive` discrepaban en `RECEIVED`. `NEW_ROOT_CAUSE = 1` | Corregido: una autoridad |
| Inspección de todo o nada | «Registrar diferencias» marcaba las cuatro comparaciones como falsas | Corregido: una decisión por comparación |
| Estado físico prefijado | Se enviaba «BUENO» sin declararlo | Corregido: sin valor por omisión |
| Rechazo inalcanzable | Sin botón; además no guardaba el veredicto | Corregido |
| Veredicto sin auditoría | `quality` no dejaba evento | Corregido: `RECEIPT_QUALITY_RECORDED` |
| Identificador en la tabla | La columna Orden enseñaba `order_id` recortado | Corregido: `order_code` |

## Filas contradictorias ya aceptadas

La defensa actúa antes de aceptar. Una fila contradictoria **ya aceptada** en el pasado no se detecta ni se corrige aquí. No hay datos no productivos con ella y no se hizo backfill.

## Huecos que siguen abiertos

No bloquean recorrer el proceso, pero son internos de Recepciones:

| Hueco | Por qué sigue abierto |
|---|---|
| RECEPCION-ANULAR-BORRADOR | Una recepción creada por error no se puede anular: `CANCELLED` existe en la máquina y no tiene operación. Exige una operación nueva, no autorizada en este ciclo |
| RECEPCION-CIERRE-SIN-OPERACION | `CLOSED` no tiene operación |
| RECEPCION-CONFIRMAR-SIN-AUDITORIA | `confirm_receipt` no deja evento |
| RECEPCION-LOTE-REGULATORIO | `requires_lot` del perfil regulatorio no se exige en ningún punto del producto. Sin requisito que lo vincule a la recepción todavía |
