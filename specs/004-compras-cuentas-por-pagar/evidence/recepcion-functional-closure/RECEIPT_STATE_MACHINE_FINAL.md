# Recepción · máquina de estados final (FR-004-031)

| STATE | MEANING | ENTER_FROM | OPERATION | ACTOR / PERMISSION | MFA | INVARIANTS | AUDIT | EXIT_TO | DOWNSTREAM | TERMINAL |
|---|---|---|---|---|---|---|---|---|---|---|
| DRAFT | Abierta en el muelle | — | `POST /receipts` | Compras, `compras:create` | No | Orden recibible, almacén activo de la empresa | `RECEIPT_CREATED` | CONFIRMED, CANCELLED | — | No |
| CONFIRMED | Recepción física confirmada | DRAFT | `POST /receipts/{id}/confirm` | `compras:create` | No | Admite líneas | `RECEIPT_TRANSITIONED` | QUALITY_PENDING | — | No |
| QUALITY_PENDING | En calidad, esperando veredicto | CONFIRMED | `POST /receipts/{id}/quality` sin veredicto | `compras:quality` | No | Al menos una línea; no admite líneas nuevas | `RECEIPT_TRANSITIONED` | ACCEPTED, PARTIALLY_ACCEPTED, REJECTED | Spec 020 puede abrir incidencias | No |
| ACCEPTED | Aceptado todo lo recibido | QUALITY_PENDING | `/quality` APPROVED y `/accept` | `compras:quality` | No | Líneas íntegras, almacén activo | `RECEIPT_QUALITY_RECORDED`, `RECEIPT_ACCEPTED` (status) | CLOSED | Spec 021 conteo y confirmación | No |
| PARTIALLY_ACCEPTED | Aceptado algo, no todo lo recibido | QUALITY_PENDING | Igual, con alguna línea aceptado < recibido | `compras:quality` | No | Total aceptado > 0 | Igual | CLOSED | Spec 021 | No |
| REJECTED | Recepción rechazada como un todo | QUALITY_PENDING | `/quality` REJECTED | `compras:quality` | No | Sin inventario | `RECEIPT_QUALITY_RECORDED` | CLOSED | Spec 020 | No |
| CLOSED | Ciclo terminado | ACCEPTED, PARTIALLY_ACCEPTED, REJECTED | `POST /receipts/{id}/close` | `compras:approve` | No | Aceptadas: inventario confirmado; rechazada: sin incidencias vivas; no mueve nada | `RECEIPT_TRANSITIONED` | — | No admite incidencias | **Sí** |
| CANCELLED | Borrador creado por error | DRAFT | `POST /receipts/{id}/cancel` con motivo | `compras:approve` | No | Sin incidencias vivas; motivo de 1 a 255 caracteres | `RECEIPT_TRANSITIONED` con `reason` | — | No admite incidencias | **Sí** |

## Reachability

`STATE_MACHINE_ZOMBIE_REQUIRED_STATES = 0`: todo estado tiene operación de entrada y, salvo los terminales, de salida. Lo fija `test_la_maquina_es_la_de_fr004031`.

## Auditoría de transiciones

| OPERATION | FROM_STATE | TO_STATE | MUTATES_BUSINESS | AUDIT_EVENT | CATALOG_ENTRY | ACTOR | BEFORE | AFTER | CORRELATION | GAP |
|---|---|---|---|---|---|---|---|---|---|---|
| create | — | DRAFT | Sí | `RECEIPT_CREATED` | Sí | Sí | — | Sí | `entity_id` | — |
| confirm | DRAFT | CONFIRMED | Sí | `RECEIPT_TRANSITIONED` | Sí | Sí | `source` | `target` | `entity_id` | Cerrado |
| send to quality | CONFIRMED | QUALITY_PENDING | Sí | `RECEIPT_TRANSITIONED` | Sí | Sí | `source` | `target` | `entity_id` | — |
| record quality | QUALITY_PENDING | igual o REJECTED | Sí | `RECEIPT_QUALITY_RECORDED` | Sí | Sí | — | `quality_status`, `status` | `entity_id` | — |
| accept | QUALITY_PENDING | ACCEPTED o PARTIALLY_ACCEPTED | Sí | `RECEIPT_ACCEPTED` | Sí | Sí | — | `status` y líneas | `entity_id` | Cerrado |
| close | aceptada o rechazada | CLOSED | Sí | `RECEIPT_TRANSITIONED` | Sí | Sí | `source` | `target` | `entity_id` | — |
| cancel | DRAFT | CANCELLED | Sí | `RECEIPT_TRANSITIONED` | Sí | Sí | `source` | `target`, `reason` | `entity_id` | — |
| inventory confirmation | aceptada | igual | Sí (Spec 021) | `RECEIPT_INVENTORY_CONFIRMED` | Sí | Sí | Sí | Sí | `entity_id` | — |

`RECEIPT_STATE_TRANSITIONS_WITHOUT_REQUIRED_AUDIT = 0`. Una transición rechazada no audita (`test_au09`).

## Filas contradictorias ya aceptadas

`qa/recepcion_lineas_contradictorias.py` las cuenta por estado, en solo lectura y sin reparar. No hay ninguna base de QA ni controlada disponible en este anfitrión: `LEGACY_ACCEPTED_MISMATCH_SCAN = NOT_EXECUTED_ENVIRONMENT_UNAVAILABLE`, `LEGACY_ACCEPTED_MISMATCH_ROWS_FOUND = UNKNOWN`. La consulta está probada sobre SQLite: cuenta la fila contradictoria y no la modifica.

## Compatibilidad de la anulación

`CANCELLATION_COMPATIBILITY_ANALYSIS`: `CANCELLED` ya existía en la máquina y en `registrar_incidencia`. No se retira ningún estado. Antes no había operación, así que no puede haber filas canceladas que reinterpretar.
