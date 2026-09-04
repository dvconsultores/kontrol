# D0-14 — DECISIONES DE PUT-AWAY

> Cierra las tres preguntas materiales que bloqueaban la Spec 022. Ciclo documental: código de
> producto 0. Las tres se cierran **negándose a inventar**, que es lo que la gobernanza pide cuando
> la fuente no alcanza.

## Lo que las tres tienen en común

Ninguna de las tres necesitaba una decisión nueva de negocio. Dos se cierran porque una política ya
existente las cubría y nadie había leído su consecuencia; la tercera se cierra porque el dato que
haría falta para automatizar **no existe**, y no automatizar es la única opción que no inventa nada.

---

# OQ-022-01 · Alcance de la reserva durante el put-away

## La pregunta

Si la Spec 021 deja la mercancía confirmada en `DISPONIBLE` con `location_id` nula y la Spec 030
puede reservarla ahí, ¿qué pasa con `qty_reserved` cuando el put-away la mueve a `L1`?

## La evidencia

| Fuente | Qué dice |
|---|---|
| `POL-D0-002` §7 | «Dimensión: `(empresa, almacén del pedido, producto)`; lote/serial solo si la línea los exige. **Nunca ubicación**» |
| `POL-D0-002` §1 | «Reservado — Unidades base comprometidas… **Contador sobre el saldo `DISPONIBLE`**; no es un estado de custodia» |
| `POL-D0-002` §11 | «030 no crea listas de picking, **no asigna ubicación**, no elige lote/serial…» |
| `ADR-D0-003` v2 R-D0-03-5 | «Solo consume saldo `DISPONIBLE`. La reserva no cambia el estado» |
| Código: `lock_balance` | filtra `location_id IS NULL` **en duro**; crea la fila con `location_id=None` |
| Código: `get_available` | lee **una** fila —la de ubicación nula— y devuelve su `qty_available` |
| Código: escritores de `qty_reserved` | **solo** `inventory/service.py`. Ningún otro módulo lo escribe |

## La decisión

> **R-D0-14-1 · La reserva es un compromiso de almacén, no de ubicación.** Sus dimensiones son
> empresa, almacén y producto, más lote y serial cuando la línea los exige. La ubicación física
> **no** forma parte de la identidad de una reserva.

Esto **no es nuevo**: es lo que `POL-D0-002` §7 dice desde el 2026-09-02. Lo que D0-14 añade es su
consecuencia, que nadie había escrito: si la ubicación no es dimensión de la reserva, entonces
**mover mercancía entre ubicaciones no puede alterar el compromiso comercial**.

> **R-D0-14-2 · Un put-away puro conserva el compromiso y el disponible del almacén.** Antes y
> después de ubicar, el reservado del almacén y su disponible son idénticos. El put-away no crea, no
> libera, no cancela y no reasigna ninguna reserva.

> **R-D0-14-3 · El disponible para reservar se calcula por almacén, no por fila de ubicación.**
> Que hoy se lea de la fila de ubicación nula es un artefacto de que la ubicación siempre fue nula,
> no una regla. `POL-D0-002` §7 ya lo excluía.

> **R-D0-14-4 · La asignación de una reserva concreta a una ubicación sigue siendo de la Spec 031.**
> El put-away mueve **existencia física**. El picking asignará **demanda** a una ubicación. Son cosas
> distintas y la 022 no hace la segunda.

## El caso canónico, resuelto

| | Antes | Después de ubicar 100 en `L1` |
|---|---:|---:|
| Físico en ubicación nula | 100 | 0 |
| Físico en `L1` | 0 | 100 |
| **Reservado del almacén** | **30** | **30** |
| **Disponible del almacén** | **70** | **70** |

## Semántica cerrada, representación diferida

La decisión de negocio queda cerrada. **Cómo** se persiste el contador agregado es elección de
ingeniería, y se difiere al ciclo de implementación con este contrato:

| Opción | Encaje con la autoridad | A favor | En contra |
|---|---|---|---|
| **A** · contador agregado en una fila de ubicación nula | Compatible | Cambio mínimo; el contador ya vive ahí | Esa fila puede tener `qty_available` negativo leído en aislamiento |
| **B** · derivar el reservado de las filas `Reservation` activas y dejar `qty_reserved` como proyección | Compatible, y ya es así de hecho: `recompute_balances` lo reconstruye desde las reservas | Una sola verdad; sin filas engañosas | Más lecturas; hay que revisar el bloqueo |
| **C** · separar saldo físico de agregado de reserva | Compatible | Explícito | Delta estructural mayor |
| **D** · repartir el reservado entre ubicaciones | **Incompatible**: contradice «nunca ubicación» | — | **Rechazada** |

> **R-D0-14-5 · Cualquier representación vale si cumple estas invariantes**, y elegir entre A, B y C
> es decisión de ingeniería, no de producto:
> 1. El compromiso reservado es del almacén y no se altera al ubicar.
> 2. La verdad física de dónde está la mercancía es `InventoryBalance.location_id`. **No se admite
>    una segunda verdad** en otra tabla.
> 3. La Spec 030 sigue siendo la única autoridad sobre reservas. No se crea un segundo motor.
> 4. `recompute_balances` reconstruye el reservado desde las reservas activas, como ya hace.
> 5. Bajo concurrencia: una reserva y un put-away sobre el mismo stock no pueden perder la reserva,
>    duplicar existencia ni producir un negativo ilegal.

**Alternativa expresamente rechazada:** dejar todo el inventario en ubicación nula y guardar la
ubicación en otra tabla. Duplicaría la verdad física y es exactamente lo que la regla 2 prohíbe.

---

# OQ-022-02 · Política de capacidad de una ubicación

## La evidencia

| Hecho | Medido |
|---|---|
| Columnas | `capacity_units` (Numeric 18,3), `capacity_weight` (Numeric 18,3), `capacity_uom` (**String(16)**) |
| ¿`capacity_uom` referencia el catálogo de unidades? | **No.** Es texto libre, sin clave foránea a `units_of_measure` |
| ¿Quién las consume? | **Nadie.** Solo el CRUD de la Spec 008 las lee y las escribe |
| ¿Existe fórmula de ocupación? | **No** existe en ninguna parte |
| ¿Tiene el producto peso o volumen? | **No** |
| ¿El proceso fuente exige bloqueo por capacidad? | **No** lo menciona |

## La decisión

> **R-D0-14-6 · La capacidad de una ubicación es informativa en la versión 1.** No bloquea ningún
> put-away. Es guía operativa: se muestra, se consulta y se reporta.

> **R-D0-14-7 · No se emiten avisos calculados mientras `capacity_uom` sea texto libre.** Comparar
> una cantidad en unidad base contra un número cuya unidad es una cadena sin validar daría una
> apariencia de rigor que el dato no sostiene. Mostrar la capacidad declarada junto a lo que hay: sí.
> Calcular un porcentaje de ocupación: no.

**Por qué no bloqueo:** un `capacity_units = 100` que no se sabe si son unidades, kilos, metros
cúbicos o pallets no puede rechazar una operación. Bloquear con una unidad inventada produciría
rechazos falsos sobre mercancía real.

## Requisitos para activar el bloqueo en el futuro

Antes de que ningún ciclo convierta la capacidad en restricción dura hacen falta, todos: unidad de
capacidad tipada contra el catálogo de unidades; peso y volumen en el maestro de productos; efecto
de la presentación sobre el consumo de capacidad; fórmula de ocupación; tolerancia; bloqueo
determinista para colocaciones simultáneas; política de excepción con aprobación (Spec 045); y
migración de los datos ya cargados.

---

# OQ-022-03 · Cómo se determina la ubicación destino

## La evidencia

El DOCX §4 pide clasificar considerando siete criterios. Contrastados uno a uno contra `CatalogItem`:

| Criterio | ¿Existe? |
|---|---|
| tipo de producto | **sí** (`item_type`, `category_id`) |
| condiciones especiales | parcial (`regulatory_profile_id`) |
| familia · tamaño · peso · rotación · volumen | **no, ninguno** |

Y además: **no existe ninguna regla producto→zona ni producto→ubicación** en el modelo. Las zonas
A–E del documento llevan su propia advertencia: *«Zonas preliminares que conviene validar para HJ»*.

## La decisión

> **R-D0-14-8 · En la versión 1 la ubicación destino la elige una persona**, de entre las
> candidatas que el backend declara elegibles.

> **R-D0-14-9 · Manual no significa sin control.** El backend valida y filtra: misma empresa, mismo
> almacén que el origen, ubicación activa, y las restricciones que ya sean autoridad. Un usuario no
> puede forzar un movimiento escribiendo un identificador arbitrario de ubicación.

> **R-D0-14-10 · La recomendación y la asignación automáticas quedan diferidas.** No se implementa
> ninguna heurística improvisada —«la primera ubicación activa con menor secuencia» y equivalentes—
> porque sería *slotting* sin autoridad, con la agravante de parecer una regla de negocio.

## Requisitos para automatizar en el futuro

Familia, tamaño, peso, rotación y volumen en el maestro de productos; zonificación **aprobada**, no
preliminar; reglas de compatibilidad producto↔zona; prioridades y criterio de desempate; semántica de
capacidad cerrada (R-D0-14-6 la difiere); recomendación explicable; y política de anulación manual.

---

# Consecuencias técnicas que quedan contratadas

> **R-D0-14-11 · El movimiento de inventario deberá reconstruir el traslado de ubicación.** Hoy
> `InventoryMovement` tiene una sola columna `location_id`, y un traslado necesita origen y destino,
> igual que el estado los necesitó en la Spec 023. Para un put-away normal: mismo almacén, origen
> nulo, destino no nulo, estado de mercancía conservado. La forma física de las columnas es del
> ciclo de implementación; la semántica es obligatoria.

> **R-D0-14-12 · `recompute_balances` debe reconstruir la ubicación sin deriva.** Incremental y
> reconstrucción deben dar el mismo saldo por ubicación. Deriva: cero.

> **R-D0-14-13 · El put-away no cambia el estado de mercancía.** No se crea ni se propone una arista
> `DISPONIBLE → DISPONIBLE` en `ADR-D0-010`: el estado se conserva y lo que cambia es la ubicación.
> Son dimensiones distintas y `D0-10` no se reabre.
