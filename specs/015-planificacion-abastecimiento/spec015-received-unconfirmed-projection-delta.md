# Spec 015 · delta: recibido sin confirmar en la proyección

- **Encargo:** `RECEIVED_UNCONFIRMED_PROJECTION`, del 2026-11-13.
- **Spec dueña:** 015, planificación y reposición.
- **Autoridades que consume, sin reemplazarlas:**
  - Spec 019: la recepción y lo aceptado;
  - Spec 021: la confirmación;
  - Spec 023: el disponible.
- **Deuda que paga:** RECEIVED-UNCONFIRMED-PROJECTION, abierta por `OPEN_SUPPLY_BY_WAREHOUSE`.
- **Evidencia:** `evidence/received-unconfirmed/`.

## Requisito

Lo aceptado en una recepción y todavía sin confirmar ya no es suministro abierto y aún no es disponible. La planificación debe verlo como un componente propio, **en recepción (pendiente de confirmar)**, por (empresa, almacén, producto). Así no vuelve a pedir esas unidades, no las cuenta dos veces y no las llama stock.

## Arqueología y autoridades

Todo está en `evidence/received-unconfirmed/RECEIVED_UNCONFIRMED_AUTHORITY.md`. Las autoridades son inequívocas y están en el código: `MATERIAL_DECISION_REQUIRED=0`.

## Clarificaciones (resueltas con el código y las Specs)

| Pregunta | Respuesta |
|---|---|
| ¿Qué cantidad cuenta? | Lo **aceptado** en unidad base: `coalesce(base_quantity_accepted, quantity_accepted)`. Es lo que la aceptación asienta en `RECIBIDO` y suma a `quantity_received` |
| ¿Cuándo deja de estar pendiente? | Cuando la Spec 021 confirma la recepción (`confirmation_status = CONFIRMADA`). Lo liberado pasa a disponible en esa misma transacción |
| ¿Y lo que la confirmación no decide? | Queda en `RECIBIDO` en una recepción CONFIRMADA y no puede confirmarse otra vez. No cuenta: sería «en camino» para siempre. Queda como deuda de la 021, `RECEIPT-CONFIRMATION-RESIDUE` |
| ¿Hay confirmación parcial? | No: es atómica por recepción. Una aceptación de 60 se confirma de una vez (por ejemplo, 40 a DISPONIBLE y 20 a RECHAZADO). La secuencia 40 → 30 se da con dos recepciones de la misma línea |
| ¿Qué almacén? | `goods_receipts.warehouse_id`, donde está la mercancía |
| ¿Y los estados de la recepción? | Solo cuentan ACCEPTED y PARTIALLY_ACCEPTED con confirmación PENDIENTE. DRAFT, CONFIRMED y QUALITY_PENDING aún no asentaron nada; REJECTED y CANCELLED no asientan; CLOSED exige CONFIRMADA |
| ¿Hay que persistirlo? | No: se deriva de las recepciones. En la necesidad, la instantánea ya guarda disponible, suministro abierto y disponible proyectado, así que se deriva como `proyectado − disponible − suministro abierto`. En las necesidades de antes de este ciclo da 0, que es lo que su cálculo usó. Las de antes de la `0106` dan null |

## Contrato

- **RUP-01. Recepción física.** `goods_receipt_lines.base_quantity_received` (019). Se muestra donde ya se mostraba; no entra en la proyección.
- **RUP-02. Cantidad aceptada.** `coalesce(base_quantity_accepted, quantity_accepted)`, con `quantity_accepted > 0` y la línea de orden con `needs_inventory`.
- **RUP-03. Rechazado excluido.** Lo rechazado en la aceptación o en la confirmación no aporta a lo recibido sin confirmar ni al disponible. El suministro abierto conserva su semántica certificada.
- **RUP-04. Almacén.** `goods_receipts.warehouse_id`. Una recepción en A no mejora B.
- **RUP-05. Confirmación.** Solo cuentan las recepciones ACCEPTED o PARTIALLY_ACCEPTED con `confirmation_status = PENDIENTE`.
- **RUP-06. Sin doble cuenta con el suministro abierto.** La aceptación mueve la cantidad de uno al otro en una transacción. El motor lee los dos en **una sola sentencia** (`UNION ALL`).
- **RUP-07. Sin doble cuenta con el disponible.** `RECIBIDO` no es vendible, y la confirmación libera y cierra lo pendiente en una transacción. Entre la lectura del disponible y la del par, una confirmación concurrente puede faltar durante un tick, pero nunca se cuenta dos veces.
- **RUP-08. Proyección.** El mismo `compute_plan`:
  - `received_unconfirmed` = lo recibido sin confirmar;
  - `projected_available = available + open_supply + received_unconfirmed`;
  - la cantidad sugerida y `condition_met` usan ese disponible proyectado (sin cambiar su forma);
  - `coverage_days` sigue siendo la cobertura del físico disponible.
- **RUP-09. Aceptación parcial.** Con 100 recibidas, 80 aceptadas y 20 rechazadas, lo recibido sin confirmar es 80.
- **RUP-10. Confirmación.** Con 60 aceptadas, confirmar 40 a DISPONIBLE y 20 a RECHAZADO deja disponible +40 y pendiente 0. Con dos recepciones de la misma línea de 100 (40 y luego 30), la secuencia es:

  | Momento | Disponible | Suministro abierto | Recibido sin confirmar |
  |---|---|---|---|
  | Orden aprobada | 0 | 100 | 0 |
  | Se aceptan 40 | 0 | 60 | 40 |
  | Se confirman | 40 | 60 | 0 |
  | Se aceptan 30 | 40 | 30 | 30 |
  | Se confirman | 70 | 30 | 0 |
- **RUP-11. Aislamiento.** Solo cuentan recepciones de la empresa del contexto.
- **RUP-12. Concurrencia.** Sin bloqueos nuevos. Las dos lecturas son las de RUP-06 y RUP-07.
- **RUP-13. Explicación en pantalla.**
  - **Necesidad**, en la causa y en la situación actual: «En recepción (pendiente de confirmar)», entre «Suministro abierto» y «Disponible proyectado».
  - **Requisición** (plan en vivo): «En recepción (pendiente de confirmar)» y «Disponible proyectado».
  - No se llama stock y no hay UUID.
- **RUP-14. E2E.** Chrome sobre PostgreSQL, a 1280, 390 y 320, con Axe.
- **RUP-15. UAT.** Pasos desde el 144 de la tarjeta de la dueña.

**API:**
- `GET /planning/plan` y `/planning/plans` añaden `received_unconfirmed`.
- La necesidad añade `received_unconfirmed` en `trigger` y `current`.
- Todas responden `dict`: OpenAPI no cambia.

**Base de datos:** `MIGRATION_REQUIRED=0`.

**Auditoría:** sin eventos nuevos. La recepción, la aceptación y la confirmación ya auditan.

## Constitution gate

```text
ACCEPTED_QUANTITY_AUTHORITY_CLEAR=1  CONFIRMATION_AUTHORITY_CLEAR=1  WAREHOUSE_AUTHORITY_CLEAR=1
AVAILABLE_STOCK_AUTHORITY_CLEAR=1  NO_DOUBLE_COUNT_PROVEN=1  PARTIAL_ACCEPTANCE_SUPPORTED=1
PARTIAL_CONFIRMATION_SUPPORTED=0 (no existe: confirmación atómica por recepción; documentado y probado)
MATERIAL_DECISION_REQUIRED=0  CONSTITUTION_GATE=PASS
```

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T015-RUP-0 Arqueología, autoridades, delta y diseño | CLAUDE | n-a | NO | n-a | n-a | documentos | — | gate PASS |
| T015-RUP-A Backend: `open_supply.py` (`recibido_sin_confirmar`, `en_camino`), motor, necesidad y pruebas | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `open_supply.py`, `engine.py`, `replenishment.py`, `tests/test_spec015_received_unconfirmed.py` | pytest en PostgreSQL | RUP-01 a RUP-12 |
| T015-RUP-B Pantallas, Vitest y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `NecesidadDetallePage.tsx`, `RequisicionDetallePage.tsx`, sus pruebas y `e2e/recibido-sin-confirmar.spec.ts` | Vitest y E2E | RUP-13, RUP-14 |
| T015-RUP-C Evidencia, tarjeta y cierre | CLAUDE | n-a | NO | n-a | n-a | documentos | — | — |

## Trazabilidad

| Requisito | Contratos | Pruebas |
|---|---|---|
| Componente propio, derivado | RUP-01, RUP-02, RUP-04, RUP-05 | backend: estados, aceptación y almacén |
| Sin doble cuenta | RUP-06, RUP-07, RUP-10 | backend: la secuencia 100 → 60/40 → 40/60/0 → … y el total proyectado constante al confirmar |
| Rechazado y parcial | RUP-03, RUP-09, RUP-10 | backend |
| No reponer lo recibido | RUP-08 | backend (tick) y E2E |
| Aislamiento | RUP-11 | backend |
| Sin efecto en el inventario | §14 del encargo | backend (movimientos y saldos sin cambio al calcular) |
| Explicación | RUP-13 | Vitest y E2E |
