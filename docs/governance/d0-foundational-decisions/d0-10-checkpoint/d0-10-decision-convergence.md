# D0-10 · CONVERGENCIA DEL CHECKPOINT DE DECISIÓN

> 2026-09-03. Ciclo exclusivamente documental. Código de producto modificado: **0**.

## Qué bloqueaba y qué lo desbloquea

El ciclo dirigido de la Spec 023 (`575cbe0`) dejó dos preguntas materiales. Este checkpoint las
cierra, una por declaración y otra por alcance.

| OQ | Pregunta | Resultado |
|---|---|---|
| `OQ-D010-01` | ¿Qué transiciones son legales y quién puede pedirlas? | **CERRADA** — nueve transiciones activas con evidencia, deny-by-default para el resto, dueño del evento separado del dueño del motor |
| `OQ-D010-02` | ¿Qué pasa si una transición vendible → no vendible afecta cantidad reservada? | **CERRADA** — la invariante se declara (`R-D0-10-9`); dos opciones quedan rechazadas por autoridad; la elección entre las dos restantes se traslada, con `R-D0-10-10`, al ciclo de la Spec que active la primera arista con origen `DISPONIBLE`. Ninguna arista activa puede producir el conflicto |

## Por qué cerrar la segunda no es aplazarla

La respuesta contractual al caso canónico existe hoy y es determinista:

```
on_hand = 100 · reserved = 30 · reclasificar 80 a no vendible
can_transition(DISPONIBLE, <no vendible>, ctx) → DENIED
```

Denegada porque no está declarada —`R-D0-10-7`—, no porque el conflicto sea difícil: el conflicto ni
llega a evaluarse. Y la invariante que lo prohibiría queda escrita para cuando alguien active esa
arista, con dos de las cuatro salidas ya descartadas y sus razones.

El criterio que hace legítimo el cierre: **el próximo ciclo puede completarse sin ninguna decisión de
negocio adicional.** La Spec 023 implementa el estado como parámetro, la validación contra la matriz,
el estado en el ledger, la reconstrucción sin colapso y la corrección de los diez call sites. Nada de
eso requiere elegir entre bloquear y reclasificar parcialmente.

## Puerta de convergencia

| Criterio | Exigido | Resultado |
|---|---|---|
| Estados de mercancía identificados | 15 | **15** |
| Estados de lote/serial identificados por separado | 7 | **7** |
| Mezcla de vocabularios | 0 | **0** (6 etiquetas coinciden, 0 semánticas) |
| Transiciones activas necesarias definidas | 100 % | **100 %** — nueve, con evidencia |
| Comportamiento ante transición no declarada | `DENY` | **`DENY`**, por `R-D0-10-7` |
| Transiciones que necesita la 021 | definidas | **cuatro**, más la de entrada |
| Transición de diferencia en transferencia | definida | **#9**, `FR-003-062`, con aprobación de la 045 |
| Dueños de evento | definidos | **sí**, separados del dueño del motor |
| Permisos y aprobaciones | definidos | **sí** |
| Conflicto con reservas | decidido | **sí** — invariante cerrada, C y D rechazadas, elección restante con dueño y momento |
| `qty_reserved > qty_on_hand` accidental | prohibido | **`R-D0-10-9`** |
| Mutación silenciosa de pedidos o reservas | prohibida | **sí** — opción C rechazada |
| Conservación física | definida | **sí**, se deriva de R-D0-10-5 |
| Frontera 023 / 030 | explícita | **sí** |
| Contrato futuro de `InventoryMovement` | suficiente | **sí** — debe conservar estado de origen y destino |
| Contrato futuro de `recompute_balances` | suficiente | **sí** — no puede asumir `DISPONIBLE`; el legacy lo clasifica el ciclo de implementación |
| OQ materiales restantes | 0 | **0** |
| Cambios de código de producto | 0 | **0** |
| Trazabilidad | 100 % | **100 %** |

## Estados resultantes

- `D0-10 — CLOSED` · `ADR-D0-010` **v2 · APPROVED · ACTIVE**
- `SPEC 023 MULTI-STATE INVENTORY BALANCE WRITE CAPABILITY — READY TO RESUME IMPLEMENTATION`
- `SPEC 021 — BLOCKED UNTIL SPEC023 CAPABILITY CONVERGES`

La 021 **no** queda lista. Cerrar la decisión no implementa la capacidad.

## Lo que hereda el próximo ciclo, sin decisiones pendientes

1. Estado como parámetro del movimiento y del saldo, validado contra la matriz.
2. `InventoryMovement` con estado de origen y destino.
3. `recompute_balances` reconstruyendo por estado; clasificación del histórico —47 filas, todas
   `DISPONIBLE` legítimo— sin reinterpretarlo.
4. Los diez call sites, cada uno con su semántica declarada.
5. La corrección de `confirm_transfer_receipt`, hoy defecto vivo.
6. La invariante `R-D0-10-9` aplicada defensivamente aunque ninguna arista activa pueda violarla.
