# D0-15 · CONVERGENCIA

`D0-15 — CLOSED`

## Puerta

| Criterio | Resultado |
|---|---|
| `OQ-031-1` orden de la cola | **CERRADA** — `released_at ASC`, desempate `id ASC` (`R-D0-15-1..4`) |
| `OQ-031-2` planificación parcial | **CERRADA** — parcial solo en `DRAFT`, confirmación exige el 100 % (`R-D0-15-5..9`) |
| `OQ-031-3` ciclo de vida del plan | **CERRADA** — cinco estados, con liberación de asignaciones (`R-D0-15-10..19`) |
| Evento de elegibilidad | **explícito**: `RELEASED` |
| Desempate determinista | **explícito**: `id`, clave primaria |
| Orden natural de PostgreSQL | **no se usa** |
| Prioridades `FUTURE` activadas | **0** |
| Remanente representado | **sí**, en el propio plan |
| Plan parcial capaz de llegar a la 032 | **no** |
| Reserva comercial liberada por la 031 | **no** (`R-D0-15-13`) |
| Movimiento físico introducido por la 031 | **0** (`R-D0-15-14`) |
| Autoridad de ruta | Spec 008, `physical_order_query()` |
| Algoritmo de ruta inventado | **0** |
| FIFO/FEFO inventado | **0** |
| Prioridad de lote o serial inventada | **0** |
| Motor de incidencias nuevo | **0** |
| Frontera con la Spec 032 | preservada |
| `D0-03`, `D0-10`, `D0-14` reabiertas | **0** |
| Especificaciones paralelas creadas | **0** |
| Backend / frontend / Alembic | **0 / 0 / 0** |
| Trazabilidad | **100 %**, 23 requisitos, 0 huérfanos |
| Preguntas materiales pendientes | **0** |

## Convergencia por pares

| Comparación | Resultado |
|---|---|
| `OQ-031-1` ↔ ¶14 del proceso | El ¶14 exige un orden; `released_at` lo da sin añadir prioridad |
| `OQ-031-1` ↔ `D0-03` §8 | No se activa ninguna dimensión diferida; el criterio es temporal |
| `OQ-031-1` ↔ sellos de `SalesOrder` | `released_at` existe, lo escribe `_a_released`, se borra al revertir |
| `OQ-031-2` ↔ `D0-03` §7 | El faltante nunca es silencioso: el plan lo publica y bloquea la confirmación |
| `OQ-031-2` ↔ `D0-14` | La reserva sigue siendo de almacén; la parcialidad es de la planificación, no del compromiso |
| `OQ-031-2` ↔ Spec 022 | El inventario ubicado parcialmente es la causa de la pregunta y queda representado |
| `OQ-031-3` ↔ Spec 030 | La invalidación reacciona a la 030 sin actuar sobre ella |
| `OQ-031-3` ↔ Spec 032 | Solo `CONFIRMED` válido se traspasa; la 032 revalida |
| Ruta ↔ Spec 008 | La 031 consume `physical_order_query()`; no hay segundo orden |

## Dos exigencias sobre el modelo de la Spec 030

La convergencia deja dos contratos que el código vigente **no** cumple y que el ciclo de
implementación de la Spec 031 debe satisfacer:

1. `create_picklist` mueve el pedido a `PREPARING` al crear el plan en `DRAFT`. `R-D0-15-18` exige
   que solo lo mueva al confirmar.
2. `ORDER_TRANSITIONS` carece de `PREPARING → RELEASED`. `R-D0-15-19` la exige para que cancelar un
   plan confirmado devuelva el pedido a la cola en vez de vararlo.

Ninguna de las dos se implementa aquí. Están declaradas, trazadas y asignadas.

## Estado resultante

| | |
|---|---|
| `D0-15` | **CLOSED** |
| Spec 031 | **READY TO RESUME IMPLEMENTATION** |
| Spec 032 | **BLOCKED UNTIL SPEC031 CONVERGES** |

La Spec 031 **no** está completa y la Spec 032 **no** está lista. Lo único que ha cambiado es que ya
no hay una decisión pendiente entre la Spec 031 y su implementación.
