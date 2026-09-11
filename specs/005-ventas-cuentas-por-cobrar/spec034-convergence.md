# SPEC 034 · CONVERGENCIA

`SPEC 034 — COMPLETE / CONVERGED`

> 2026-09-06, sobre `fe92cf3`. Ciclo completo desde `/speckit.specify`.

## Puerta

| Criterio | Resultado |
|---|---|
| Se factura sin confirmación independiente | **no**, y se comprueba el registro, no el estado |
| Se genera factura sin solicitud | **no** |
| La solicitud tiene autor y momento | sí |
| La factura queda atada al pedido y a su confirmación | sí |
| Un pedido se factura dos veces | **no**, en el servicio **y** en la base |
| Dos facturadores generan dos facturas | **no** |
| El precio y el descuento salen del maestro actual | **no**, del pedido congelado |
| Unidad, presentación y factor se recalculan | **no**, se copian |
| Caja ×12 | 2 comercial · 24 base · factor 12 |
| Tasas de impuesto escritas en esta Spec | **0** — las resuelve la regla versionada |
| Correlativo o número de control propios | **0** — los asigna la Spec 042 |
| Emitir dos veces gasta dos números | **no** |
| Delta de inventario y de reserva al facturar | **0 / 0** |
| Segundo ledger de cuentas por cobrar | **0** |
| `DISPATCHED` añadido | **no** — es de la 035 |
| Backend | 1177 pruebas · **1169 pasan · 8 saltos · 0 fallos** |
| Saltos esperados / reales | **8 / 8** |
| Frontend | **295/295** · `tsc`, `eslint`, `ruff` limpios |
| E2E de la Spec 034 | **24/24** (8 casos × Chromium, Firefox, WebKit) |
| E2E de la cadena operativa | **153/153** (019→034 y recorrido del menú × 3) |
| Migración `0052` | ida y vuelta sobre base limpia |
| Trazabilidad | **100 %**, 40 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## Las catorce preguntas y sus tres fuentes

El ciclo enumeraba catorce preguntas materiales. Ninguna hubo que decidirla, y
el trabajo estaba repartido entre tres autoridades que se complementan:

- **El proceso fuente** dice qué pasa: el ¶95 genera la factura, el ¶96 la asocia
  al pedido y el ¶97 emite el documento fiscal. Son **dos actos**, y esa
  separación es la que estructura toda la implementación.
- **`ADR-D0-012`** dice en qué estados: «`CONFIRMED → READY_FOR_BILLING →
  INVOICED → DISPATCHED`». Esta Spec añade los dos suyos y deja el tercero.
- **El backlog maestro** fija los criterios de aceptación, y son literales:
  `B-007` («migración aditiva con FK nullable; no se puede facturar dos veces la
  misma orden») y `B-060` («solo se factura un pedido `CONFIRMED`; solicitud de
  facturación explícita; imposible doble facturación»).

## Lo que no había que construir

El motor fiscal ya estaba: reglas versionadas y fechadas, series con reserva
atómica del correlativo, lotes y números de control, y `emit_document`, que
consume las dos numeraciones en una transacción y es idempotente por
`INVOICE:{id}`. También estaba la cuenta por cobrar: `transition_invoice` crea el
`OpenItem` al emitir (`FR-005-040`).

**Lo que faltaba era el gobierno.** Antes de este ciclo cualquiera podía crear
una factura para un cliente sin pedido, sin confirmación y dos veces.

## Lo que se midió, no se supuso

Dos mutaciones. Quitando la comprobación de la confirmación, la prueba del pedido
puesto en `CONFIRMED` a mano falla —y esa prueba hubo que escribirla porque la
primera versión de la guardia comprobaba el estado y no el registro, cosa que la
mutación destapó—. Quitando la comprobación de doble facturación del servicio,
**la base la rechaza**: `uq_sales_invoices_order` es defensa en profundidad, no
adorno.

## Deltas dirigidos

| Delta | Dueño | Qué | Guardia |
|---|---|---|---|
| **A** | Spec 030 (`sales`) | `CONFIRMED → READY_FOR_BILLING → INVOICED`, declarados por `ADR-D0-012` | `test_la_maquina_de_estados_es_la_de_d0_03` |
| **B** | Spec 005 (`sales`) | `SalesInvoice` con `order_id`, `confirmation_id`, sellos de emisión e índice único | `test_un_pedido_no_se_factura_dos_veces_ni_en_la_base` |

Tres guardias actualizadas con su razón. Dos marcaban «la 034 no está
construida»; la tercera fue, otra vez, el corte de bloque de la guardia anterior
—la de la 033— que sin ajustarlo se habría comido el bloque de la 034 y habría
afirmado lo contrario de lo que quiere decir. Es la cuarta vez en este tramo.

## La desviación fiscal, dicha en voz alta

`D0-07` mantiene las Specs 039-043 en `BLOCKED_BY_LEGAL_VALIDATION`. El registro
separa «arquitectura fiscal **construible**» de «**liberación legal**». Este
ciclo construyó y probó el camino contra el motor existente. **No afirma que la
emisión esté legalmente homologada**: eso sigue pendiente de `D0-07`.

Y las pruebas corrieron en **PostgreSQL 16.2**, no en el 18.6 documentado
(`ENVIRONMENT_BASELINE_DEVIATION`). Nada de lo implementado usa una capacidad
exclusiva de 18.x.

## Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| `calculate_tax` opera en `float` y redondea a 2 decimales sin política de moneda | Spec 039 |
| `create_invoice`/`add_invoice_line` de la Spec 005 siguen en `float` | Spec 005 |
| Una línea sin clasificación fiscal factura sin impuesto; se expone, no se bloquea | Spec 039/014 |
| Un pedido rechazado en el control queda en `PREPARING` sin camino de corrección | Spec 032 |
| `CONFIRMED → SHIPPED` sigue abierta: el ¶103 exige factura antes de despachar | Spec 035 |
| `uom.py` declara para `sales_orders` estados que no existen | Spec 011 |

## Delta dirigido recibido — 2026-09-11 (desde el ciclo de la Spec 036)

`issue_invoice` **no creaba la cuenta por cobrar**. El proceso de ventas dice
«9. Emitir factura → **10. Crear CxC**», y eso solo ocurría por el camino
heredado `transition_invoice`. `issue_invoice` —el camino que esta Spec
construyó y el único que emite el documento fiscal— ponía el estado a mano y se
saltaba la creación, así que **toda factura emitida por el proceso real nacía
sin documento por cobrar**.

No lo vio ninguna prueba porque ninguna llegaba a cobrar una factura emitida por
ese camino: la del motor de CxC usaba `transition_invoice`, que sí lo creaba. Se
descubrió al aplicarle una nota de crédito y no encontrar nada que ajustar.

La creación se extrajo a `_abrir_cuenta_por_cobrar`, es idempotente, y la llaman
los dos caminos. El comportamiento anterior de `transition_invoice` no cambia.

Esta Spec **no se reabre funcionalmente**: sigue `COMPLETE / CONVERGED`. La
factura, su numeración, su snapshot comercial y su compuerta de confirmación son
las mismas.

## Estado resultante

| | |
|---|---|
| Spec 034 | **COMPLETE / CONVERGED** |
| Specs 005, 030 | `COMPLETE / CONVERGED` con sus deltas dirigidos convergidos |
| Spec 035 | **desbloqueada por dependencia**; compuerta en `spec034-spec035-handoff-contract.md`. **No implementada.** |
