# D0-14 · CONVERGENCIA

`D0-14 — CLOSED`

## Puerta

| Criterio | Resultado |
|---|---|
| `OQ-022-01` alcance de la reserva | **CERRADA** — de almacén, no de ubicación (`R-D0-14-1..5`) |
| `OQ-022-02` capacidad | **CERRADA** — informativa en V1 (`R-D0-14-6/7`) |
| `OQ-022-03` selección de ubicación | **CERRADA** — manual con filtro de backend (`R-D0-14-8/9/10`) |
| Autoridad de la Spec 030 | preservada |
| Autoridad de la Spec 031 sobre asignación al picking | preservada |
| Segundo motor de reservas | **0** |
| Segunda verdad física | **0** — prohibida por `R-D0-14-5` regla 2 |
| Unidades inventadas | **0** |
| Atributos de producto inventados | **0** |
| Zonas preliminares tratadas como regla | **0** |
| `D0-10` reabierto | **no** — el put-away no cambia estado de mercancía |
| `D0-03` reabierto | **no** — se aplica `POL-D0-002` §7, no se modifica |
| OQ materiales restantes | **0** |
| Código de producto | backend 0 · frontend 0 · Alembic 0 |
| Trazabilidad | 100 % |

## Por qué las tres se pudieron cerrar

Ninguna necesitaba una decisión nueva.

**La primera** ya estaba decidida y nadie había leído su consecuencia. `POL-D0-002` §7 dice desde
septiembre que la reserva no se dimensiona por ubicación; de ahí se sigue, sin añadir nada, que mover
mercancía entre ubicaciones no puede tocar el compromiso comercial. Lo que había era una
implementación que leía el disponible de una sola fila porque la ubicación siempre había sido nula.

**Las otras dos** se cierran por lo contrario: porque el dato que haría falta para decidir otra cosa
no existe. La capacidad tiene columnas y ninguna regla, y su unidad es texto libre sin vínculo al
catálogo. La clasificación pide cinco atributos que el maestro no tiene, sobre zonas que el propio
documento marca como preliminares. En los dos casos, no imponer una regla es la única opción que no
inventa una.

## Lo que hereda el ciclo de implementación, sin decisiones pendientes

1. Reconciliar `lock_balance` y `get_available` para que el disponible sea del almacén y no de la
   fila de ubicación nula.
2. Elegir la representación del contador reservado entre A, B y C —elección de ingeniería, con las
   cinco invariantes de `R-D0-14-5` como contrato—.
3. Añadir al movimiento la procedencia de ubicación, con la forma ya resuelta por precedente en la
   `0046`.
4. Reconstrucción consciente de la ubicación, sin deriva.
5. Put-away manual con filtro de candidatas en el backend.
6. Capacidad mostrada, nunca aplicada.

## Estados resultantes

- `D0-14 — CLOSED`
- `SPEC 022 — READY TO RESUME IMPLEMENTATION`
- `SPEC 031 — BLOCKED UNTIL SPEC022 CONVERGES`

Cerrar la decisión no implementa la capacidad. La 031 **no** queda lista.
