# SPEC 032 → SPEC 033 · CONTRATO DE ENTREGA

> Qué recibe la confirmación independiente y qué **no** viene decidido. No
> implementa la Spec 033.

## Lo que la Spec 032 entrega

Un pedido en estado `PREPARED` —«pedido preparado pendiente de control» (¶59)—
con su plan de picking en `CLOSED` y la mercancía concentrada en el Área de
Confirmación en estado `PREPARADO`.

`GET /sales/picking/{plan_id}/preparacion` devuelve **hechos, no un veredicto**:

| Campo | Qué es |
|---|---|
| `demand[].required_base_quantity` | Lo que el pedido comprometió |
| `demand[].prepared_base_quantity` | Lo que **de verdad** se preparó |
| `picking[].planned_base_quantity` | Lo que el plan decía recoger de cada ubicación |
| `picking[].picked_base_quantity` | Lo que se recogió allí |
| `picking[].difference` | La diferencia, con signo |
| `picking[].discrepancy_kind` · `discrepancy_note` | Su motivo, de los cinco del ¶48-52 |
| `picking[].location_id` · `lot_id` · `serial_id` | De dónde salió y con qué identidad |
| `picking[].picked_by` · `picked_at` | Quién y cuándo |
| `has_discrepancy` | Si hubo alguna diferencia |
| `consolidation_location_id` · `consolidated_at` | Dónde y cuándo se concentró |

La 033 no tiene que reconstruir nada desde el ledger, pero el ledger está: cada
extracción y cada traslado dejó su movimiento con estado y ubicación de origen y
destino.

## Lo que la Spec 032 deliberadamente **no** hace

- **No certifica que el pedido esté correcto.** El ¶61 dice que la confirmación
  «constituye un control **independiente** después del picking». Si la 032
  comparara y aprobara, ese control dejaría de ser independiente y sería el
  preparador validándose a sí mismo.
- **No resuelve las diferencias.** Las registra. El ¶45 manda el pedido al área
  de confirmación **igual**, con la diferencia anotada.
- **No consume la reserva.** Sigue `ACTIVE`; la consume el despacho
  (`POL-D0-002` §8).
- **No factura ni despacha.**

## Lo que la Spec 033 tendrá que decidir por su cuenta

| Cuestión | Por qué no se decide aquí |
|---|---|
| Segregación entre quien prepara y quien confirma | `ADR-D0-012` la menciona; su régimen es de la 033 con la 045. La 032 no la impone ni la contradice |
| Qué pasa cuando el control encuentra una diferencia que el picking no registró | Es el objeto de ese control |
| Qué estado sigue a `PREPARED` | `ADR-D0-012` declara `CONFIRMED`, y esta Spec **no lo ha añadido** a la máquina: lo añadirá su dueña |
| El primer efecto físico irreversible | `R-D0-15-16` lo dejó a la 032; hoy la extracción **es** ese efecto, y por eso un plan `CLOSED` ya no se cancela |

## Nota sobre `R-D0-15-16`

`D0-15` dijo que un plan `CONFIRMED` puede cancelarse «solo antes del primer
efecto físico irreversible de la Spec 032», y dejó a la 032 definir ese momento.

Queda definido: **es la primera recogida registrada**. A partir de ahí hay
mercancía en `PICKING` y el contador de reservado ya bajó, así que `cancel_plan`
rechaza el plan con `PICKING_ALREADY_STARTED`. Retirarlo dejaría existencia en un
estado de custodia sin dueño: devolverla a `DISPONIBLE` exigiría una arista que
la matriz de `D0-10` **no declara**, y este ciclo no la inventa.

Qué hacer con un pedido que empezó a prepararse y hay que deshacer es, por tanto,
una pregunta abierta —necesita una arista de devolución con su dueña y su
evidencia—. No bloquea a la 033: se llega a ella por el camino normal.
