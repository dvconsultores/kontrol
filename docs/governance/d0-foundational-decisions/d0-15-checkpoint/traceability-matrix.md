# D0-15 · TRAZABILIDAD

| Requisito | OQ | Evidencia | Decisión | Dueño | Prueba futura | Estado |
|---|---|---|---|---|---|---|
| FR-D015-001 · la elegibilidad empieza en `RELEASED` | 1 | `FR-030-050`; `eligible_for_picking = status == RELEASED` | **R-D0-15-1** | 030 | un pedido no `RELEASED` no aparece en la cola | ✔ |
| FR-D015-002 · el orden primario es temporal y de entrada | 1 | docstring de `_a_released`: «el pedido entra en la cola de 031»; `released_at` se escribe ahí | **R-D0-15-2** | 031 | el caso canónico A/B ordena B antes que A | ✔ |
| FR-D015-003 · prioridad por cliente, manual, SLA y ruta siguen diferidas | 1 | `D0-03` §8 | **R-D0-15-4** | 030 | guardia: ningún campo de prioridad en el modelo | ✔ |
| FR-D015-004 · la cola es determinista y total | 1 | `code` es `String(64)` sin unicidad; único índice único es `uq_sales_orders_quote`; `id` es clave primaria | **R-D0-15-3** `(released_at, id)` | 031 | mismos datos → misma cola en ejecuciones repetidas | ✔ |
| FR-D015-005 · un pedido revertido pierde su puesto | 1 | `service.py:739-742` borra `released_at` y libera reservas | **R-D0-15-2** consecuencia | 030 | revertir y reemitir manda el pedido al final | ✔ |
| FR-D015-006 · la división entre ubicaciones está soportada | 2 | `POL-D0-002` §7, `R-D0-14-1`: la reserva es de almacén | **R-D0-15-5** | 031 | reserva 100 con `L1` 60 y `L2` 40 se planifica | ✔ |
| FR-D015-007 · la asignación parcial solo existe en estado no ejecutable | 2 | `D0-03` §7 prohíbe el faltante silencioso | **R-D0-15-6** | 031 | un `DRAFT` parcial no es consumible | ✔ |
| FR-D015-008 · el remanente es explícito | 2 | no hay dueño de incidencia en ventas; `ReceiptIncident` es de compras | **R-D0-15-7** | 031 | el plan publica cuánto falta | ✔ |
| FR-D015-009 · no se confirma con cantidad requerida sin asignar | 2 | `POL-D0-002` §3 todo o nada | **R-D0-15-8** | 031 | `DRAFT` 60/100 rechaza `CONFIRMED` | ✔ |
| FR-D015-010 · la 032 no consume un plan incompleto | 2 | frontera 031/032 del maestro | **R-D0-15-9**, **R-D0-15-17** | 032 | traspaso rechazado salvo `CONFIRMED` válido | ✔ |
| FR-D015-011 · el ciclo de vida distingue cinco situaciones | 3 | `PickList.status` sin `CHECK`; nadie escribe `CONFIRMED` ni `CLOSED` | **R-D0-15-10** | 031 | `CHECK` de estados en la migración | ✔ |
| FR-D015-012 · cancelación e invalidación no son el mismo estado | 3 | ninguna existe hoy | **R-D0-15-11** | 031 | auditoría distingue acto de consecuencia | ✔ |
| FR-D015-013 · cancelar o invalidar libera las asignaciones operativas | 3 | `R-D0-14-4` autoriza la asignación; sin liberación quedaría secuestrada | **R-D0-15-12** | 031 | tras cancelar, la ubicación vuelve a ser asignable | ✔ |
| FR-D015-014 · la 031 no libera la reserva comercial | 3 | `_liberar_reservas` es de la 030 | **R-D0-15-13** | 030 | guardia estructural sobre el servicio de la 031 | ✔ |
| FR-D015-015 · ningún estado de la 031 muta el inventario físico | 3 | planificar no es mover | **R-D0-15-14** | 031 | guardia: sin `InventoryMovement` en el servicio del plan | ✔ |
| FR-D015-016 · los disparadores de invalidación son cerrados | 3 | `ORDER_TRANSITIONS`: `RELEASED → {PREPARING, SHIPPED, CANCELLED, DRAFT}` | **R-D0-15-15** | 031 | pasar a `PREPARING` no invalida | ✔ |
| FR-D015-017 · `CONFIRMED` se cancela solo antes de efecto físico | 3 | la 032 no existe | **R-D0-15-16** | 032 | frontera contractual documentada | ✔ |
| FR-D015-018 · un `DRAFT` no saca al pedido de la cola | 3 | `create_picklist` lo mueve hoy a `PREPARING` al crear | **R-D0-15-18** | 031 | crear un `DRAFT` deja el pedido `RELEASED` | ✔ |
| FR-D015-019 · cancelar antes de efecto físico devuelve el pedido a la cola | 3 | `ORDER_TRANSITIONS` carece de `PREPARING → RELEASED` | **R-D0-15-19** | 030 | la arista existe y se ejerce | ✔ |
| FR-D015-020 · la Spec 008 es la autoridad de ruta | — | `physical_order_query()`, `FR-008-033` | **R-D0-15-20** | 008 | guardia: sin segundo algoritmo de recorrido | ✔ |
| FR-D015-021 · sin política inventada de lote o serial | — | ¶30 fija la granularidad en producto; `FR-030-051` | **R-D0-15-21** | 031 | guardia: sin FIFO/FEFO en el servicio del plan | ✔ |
| FR-D015-022 · la cantidad asignable localizada está definida | — | `R-D0-14-4` | **R-D0-15-22** | 031 | dos planes no asignan las mismas unidades | ✔ |
| FR-D015-023 · código de producto cero en `D0-15` | — | `git diff` | ciclo documental | gobernanza | guardia de commit | ✔ |

## Cobertura

| | |
|---|---:|
| Requisitos | 23 |
| Con evidencia y decisión | **23** |
| Requisitos huérfanos | **0** |
| Tareas huérfanas | **0** |
| Cobertura | **100 %** |

Las «pruebas futuras» son deuda declarada del ciclo de implementación de la Spec 031, no de este
checkpoint: `D0-15` es documental y no ejecuta código.
