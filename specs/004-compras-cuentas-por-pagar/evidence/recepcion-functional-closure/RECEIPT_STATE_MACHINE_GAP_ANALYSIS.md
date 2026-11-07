# Recepción · análisis de la máquina de estados (antes)

Autoridad: **FR-004-031** (P0): `DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED / PARTIALLY_ACCEPTED / REJECTED → CLOSED`. No se encontró ninguna fuente posterior que la sustituya: `SUPERSEDING_REQUIREMENT_FOUND = 0`.

| STATE | REQUIRED_BY | CURRENT_ENTRY_OPERATION | CURRENT_EXIT_OPERATION | UI_REACHABLE | API_REACHABLE | EXPECTED_SEMANTICS | GAP | ACTION |
|---|---|---|---|---|---|---|---|---|
| DRAFT | FR-004-031 | `create_receipt` | `confirm` | Sí | Sí | Recepción abierta en el muelle | Salida a `CANCELLED` sin operación | Anulación con motivo |
| CONFIRMED | FR-004-031 | `confirm` | `accept` y `quality` directo | Sí | Sí | Recepción física confirmada | Salta `QUALITY_PENDING` | Entregar a calidad |
| QUALITY_PENDING | FR-004-031; contrato `/quality` «→ QUALITY_PENDING» | Ninguna | — | No | No | Confirmada, esperando veredicto | **Inalcanzable** | Entrar por `/quality` sin veredicto |
| ACCEPTED | FR-004-031 | `accept` | — | Sí | Sí | Aceptada por completo | También significa parcial | Regla parcial |
| PARTIALLY_ACCEPTED | FR-004-031; Spec 021 la acepta | Ninguna | — | No | No | Aceptada con parte no aceptada | **Inalcanzable** | Derivarla al aceptar |
| REJECTED | FR-004-031 | veredicto no conforme | — | Sí | Sí | Recepción rechazada como un todo | Ninguno | Conservar |
| CLOSED | FR-004-031 | Ninguna | — | No | No | Fin del ciclo de vida | **Inalcanzable** | Operación de cierre |
| CANCELLED | Motor; cuestión 7 del ciclo 019; patrón de documentos de compra | Ninguna | — | No | No | Creada por error, sin efectos | Estado sin operación | Anulación de borrador |

`P0_FUNCTIONAL_GAP = 1` hasta corregirse.

## Auditoría antes

| OPERATION | FROM_STATE | TO_STATE | AUDIT_EVENT | GAP |
|---|---|---|---|---|
| create | — | DRAFT | `RECEIPT_CREATED` | — |
| arrival | DRAFT, CONFIRMED | igual | `RECEIPT_ARRIVAL_CONFIRMED` | — |
| inspection | abierta | igual | `RECEIPT_INSPECTED` | — |
| add line | DRAFT, CONFIRMED | igual | `RECEIPT_LINE_ADDED` | — |
| **confirm** | DRAFT | CONFIRMED | **ninguno** | `CONFIRM_AUDIT_GAP_PROVEN = 1` |
| quality verdict | CONFIRMED | igual o REJECTED | `RECEIPT_QUALITY_RECORDED` | — |
| accept | CONFIRMED | ACCEPTED | `RECEIPT_ACCEPTED` | No registra el estado de llegada |
| count | ACCEPTED | igual | `RECEIPT_LINE_COUNTED` | — |
| inventory confirmation | ACCEPTED | igual (dimensión aparte) | `RECEIPT_INVENTORY_CONFIRMED` | — |
