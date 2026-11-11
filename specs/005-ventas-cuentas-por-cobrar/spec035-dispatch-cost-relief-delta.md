# Spec 035 · delta: el despacho consume el costo del inventario (DISPATCH-COST-RELIEF)

Encargo `DISPATCH-COST-RELIEF`, del 2026-11-11. Spec dueña del evento: 035. Motor de costo: Inventario (Spec 003, FR-003-080..083; lo que el encargo llama «023»). Apoyo: 030 y 036. Origen: el hallazgo de la evidencia `specs/018-importaciones/evidence/release-to-dispatch/`. Evidencia de este delta: `evidence/dispatch-cost-relief/`.

## Defecto medido

`sales.service.confirm_shipment` hace PREPARADO → DESPACHADO con `inv_service.reclassify`. Esa función mueve el saldo de estado, pero no toca las capas de costo, y el movimiento sale con `unit_cost` nulo. Además, `inventory.service.valuation` suma las capas con `quantity_remaining > 0` sea cual sea el estado.

Medido en la E2E de importaciones, con 10 unidades a 5 y 4 despachadas:
- quedan 6 DISPONIBLE y 4 DESPACHADO;
- la valoración vale 50 antes y después del despacho.

D0-10 declara DESPACHADO «fuera de existencia». `MATERIAL_DECISION_REQUIRED = 0`: el método, el momento y la salida de la valoración ya tienen autoridad.

## Decisiones fijadas

- **DCR-01. Momento.** El costo se consume dentro de `confirm_shipment`, en la misma transacción que:
  - la reclasificación PREPARADO → DESPACHADO;
  - el paso de las reservas a FULFILLED;
  - el estado SHIPPED del despacho y del pedido;
  - la auditoría `SHIPMENT_CONFIRMED`.

  No se consume costo en el pedido, la reserva, el picking (medido: `consume_on_pick` no consume capas), la preparación, la confirmación ni la factura.
- **DCR-02. Motor.** Se usa el que existe: `_costing_method` (el perfil vigente; AVERAGE por defecto) y el algoritmo de `_consume_cost`. Solo se extiende para devolver el desglose por capa. `record_movement` y sus llamadores conservan su contrato. La máquina de estados no cambia: no hay VENDIDO ni un segundo movimiento físico de salida.
- **DCR-03. Fórmula.** Es la vigente:
  - costo efectivo de una capa: `unit_cost + landed_cost / quantity_in` (`effective_unit_cost`);
  - FIFO: las capas se toman por `created_at` ascendente; costo = Σ cantidad tomada × costo efectivo; la capa agotada pasa a CLOSED;
  - AVERAGE: promedio = Σ(restante × costo efectivo) / Σ restante; cada capa baja en proporción a lo que le queda; costo = cantidad × promedio.
- **DCR-04. Escala y redondeo.** Cantidades y costos en `Decimal`, con la escala de 6 decimales y el redondeo del `_dec` de Inventario. No se introduce ningún `float` nuevo. El dinero que se muestra usa la convención vigente (0,01 ROUND_HALF_EVEN). Una capa repuesta guarda `unit_cost` con la escala de su columna (0,01, ROUND_HALF_EVEN).
- **DCR-05. Fallar cerrado** (sin estado parcial):
  - **Capas insuficientes.** Si 0 < cantidad cubierta < cantidad pedida, el error es `NO_COST_LAYER`, con cualquiera de los dos métodos. Corrige además el AVERAGE actual, que dejaba `quantity_remaining` negativo.
  - **Mezcla de monedas.** Capas en más de una moneda dentro del mismo consumo: `COST_LAYER_CURRENCY_MIXED`.
  - **Sin ninguna capa.** Se conserva el contrato del motor: con AVERAGE es una salida sin costo (`None`, nunca cero); con FIFO, `NO_COST_LAYER`.
- **DCR-06. Instantánea reconstruible.** Por cada línea del despacho y cada capa consumida se guarda:
  - el despacho, la línea y el movimiento `SHIPMENT:<id>`;
  - la capa;
  - la cantidad;
  - el costo unitario efectivo;
  - el costo total;
  - la moneda;
  - el método aplicado.

  La explicación de una salida pasada no depende del perfil actual. Además, el movimiento `SHIPMENT:<id>` lleva el costo unitario y la moneda reales. La auditoría `SHIPMENT_CONFIRMED` añade el resumen de costo: no hay un ledger nuevo.
- **DCR-07. Idempotencia y concurrencia.** Una segunda confirmación no consume otra vez. La autoridad es PostgreSQL:
  - el bloqueo del pedido que ya existe;
  - se vuelve a comprobar `dispatched_at` después de ese bloqueo;
  - una restricción única en la instantánea.
- **DCR-08. Devolución (Spec 036), inseparable.** Sin este paso, la mercancía que vuelve a DISPONIBLE quedaría sin capa y su siguiente despacho fallaría por `NO_COST_LAYER`. Por eso, cuando `reenter_return` reingresa a `DISPONIBLE`, repone una capa:
  - cantidad: la aceptada;
  - costo unitario: el efectivo de la instantánea de ese despacho para ese producto (Σ total / Σ cantidad);
  - moneda: la de la instantánea;
  - `receipt_ref`: `SALES_RETURN:<id>`.

  Si el despacho salió sin costo, no se repone capa. Lo que se reingresa a RECHAZADO no se valora: deuda RETURN-REJECTED-VALUATION.
- **DCR-09. Landed cost.** Lo consume el costo efectivo de la capa. Una vez consumida la capa, `IMPORT_COST_LAYER_CONSUMED` e `IMPORT_COST_REVERSAL_BLOCKED` se activan sin tocarlos.
- **DCR-10. Fuera de alcance.**
  - El asiento contable de costo de ventas: `COGS_ACCOUNTING_ENTRY_IMPLEMENTED = NO`; no hay módulo contable.
  - Los despachos anteriores a este delta: no se repara ningún dato, porque es un backfill que solo autoriza la dueña. Queda la deuda DISPATCH-COST-RELIEF-HISTORICO.

## Estado

CONVERGED el 2026-11-11. Implementado por DeepSeek y auditado por Claude: 3 llamadas y 3 reintentos, $0,045. Los 9 vectores y el aislamiento pasan en PostgreSQL, y la E2E pasa en Chrome a 1280, 390 y 320. Evidencia en `evidence/dispatch-cost-relief/`.

**Aclaración de diseño (medida):** con AVERAGE, la instantánea guarda una fila por cada capa consumida en proporción. En el vector V2 son 2 filas de 2 unidades cada una, con costo efectivo 6.

## Vectores de prueba (PostgreSQL)

| # | Perfil | Capas antes | Despacho | Costo consumido | Capas después | Valoración |
|---|---|---|---|---|---|---|
| V1 | AVERAGE | 10 @ 5,00 | 4 | 20,00 | 6 | 50 → 30 |
| V2 | AVERAGE | 10 @ 5,00 + 10 @ 7,00 | 4 | 24,00 (promedio 6) | 8 + 8 | 120 → 96 |
| V3 | FIFO | 3 @ 5,00 y luego 10 @ 8,00 | 5 | 31,00 (unitario 6,2) | 0 (CLOSED) + 8 (OPEN) | 95 → 64 |
| V4 | FIFO | 10 @ 5,00 | 4 | 20,00 | 6 (OPEN) | 50 → 30 |
| V5 | AVERAGE + landed | 10 @ 5,00, landed 10,00 (efectivo 6) | 4 | 24,00 | 6 | 60 → 36 |
| V6 | FIFO | 3 con costo; físico 5 | 5 | `NO_COST_LAYER` | sin cambios | sin cambios, y el despacho sigue READY |
| V7 | AVERAGE | 3 con costo; físico 5 | 5 | `NO_COST_LAYER` | sin cambios | sin cambios |
| V8 | V1 confirmado dos veces, en serie y en concurrencia | — | — | una sola vez | 6 | 30 |
| V9 | V1 y luego devolución de 2 a DISPONIBLE | — | — | — | 6 + capa repuesta de 2 @ 5,00 | 30 → 40 |

Además:
- **Aislamiento.** Las capas de la empresa B y las de otro almacén de A no se tocan.
- **Reservas.** Quedan en FULFILLED.
- **Trazabilidad.** El saldo DESPACHADO sigue registrado.
- **Reversión.** Revertir el landed cost de V5 tras el despacho se rechaza.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T035-DCR-A Motor con desglose, instantánea con modelo y migración 0098, alivio en `confirm_shipment`, reposición en `reenter_return`, guardas de cabeza, pruebas de V1 a V9 | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `inventory/{service,models}.py`, `sales/service.py`, `alembic/versions/0098_*`, `tests/test_spec035_dispatch_cost_relief.py`, guardas de cabeza | pytest dirigido sobre PostgreSQL | V1 a V9 PASS; 035, 036 y landed cost sin regresión |
| T035-DCR-B E2E: landed cost vigente → despacho → V1 = V0 − costo consumido | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `e2e/importaciones.spec.ts` | la propia E2E | PASS en Chrome sobre PostgreSQL a 1280, 390 y 320 |
| T035-DCR-C Delta, auditoría, QA, evidencia, tarjeta y matriz | CLAUDE | n-a | NO | n-a | n-a | documentos | — | evidencia completa |

Excepción a la política, porque la dueña manda (precedencia 1): el encargo asigna a DeepSeek la migración y el código de dinero. Claude fijó antes la fórmula, la escala, el redondeo, el contrato y los vectores.
