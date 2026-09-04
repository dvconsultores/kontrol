# SPEC 022 — PUT-AWAY Y UBICACIÓN · CICLO DE IMPLEMENTACIÓN

> 2026-09-04, sobre `b87b543`. Ciclo completo desde `/speckit.specify`. Se detiene antes de
> `/speckit.implement` por tres preguntas abiertas materiales. **Cero código de producto.**

## 1. La reconciliación documental que el ciclo exigía primero

El cierre de la Spec 021 dejó dos afirmaciones que no podían sostenerse a la vez sin volver al DOCX.
Volví. Las dos eran ciertas **de procesos distintos**, y mi resumen las mezcló.

| Sección del DOCX | Etapas de primer nivel | Reparto |
|---|---:|---|
| §2 Recepción de la importación | **12** | 019 (8) · 020 (3) · **022 (1)** |
| §3 Confirmación del inventario recibido | **14** | 019 (2) · 020 (3) · **021 (9)** |
| §4 Clasificación y ubicación en almacén | **11** | **022 (11)** |

Lo que dije —«la duodécima y última etapa del proceso de recepción»— es cierto de **§2**, cuya etapa
12 es «colocar la mercancía **temporalmente** en zona de recepción o validación». Pero decirlo así
daba a entender que el put-away era esa única etapa, y no lo es: el put-away es §4 entero.

**Spec 022 tiene doce etapas, no una y no diez.** El registro de deuda decía diez para DF-05; son
once en §4 más la colocación temporal de §2.

### Una distinción del proceso que conviene no perder

Hay **dos liberaciones** en el documento y no son la misma:

- §3 [77]: «Liberar el lote **para almacenamiento**» → la Spec 021, ya implementada.
- §4 [101]: «Liberar definitivamente la mercancía como disponible **para preparación de pedidos y
  despacho**» → el final de la Spec 022.

Esto **no** exige un estado de mercancía nuevo. `ADR-D0-010` v2 no tiene ninguno para «disponible
pero sin ubicar», y no hace falta: esa condición se representa con `DISPONIBLE` y `location_id` nula,
que es exactamente lo que la Spec 021 deja y lo que este ciclo debía consumir. Crear una arista
`DISPONIBLE → DISPONIBLE` para el put-away está expresamente prohibido y no se propone.

## 2. Lo que ya existe y no hay que construir

| Capacidad | Dueña | Estado |
|---|---|---|
| Zonas, pasillos, racks, niveles y ubicaciones con secuencia | Spec 008 | **completa**, con la cadena entera en cada ubicación y clave foránea compuesta empresa+almacén |
| Estado de la ubicación | Spec 008 | `StatusMixin` |
| Tipo de zona | Spec 008 | `zone_type_id` |
| Ubicación como dimensión del saldo | Spec 023 | **existe** en la clave única, con `COALESCE` null-safe |
| Ubicación en el movimiento | Spec 023 | existe **una** columna, `location_id` |
| Motor de reclasificación y validación | Spec 023 | completo |
| Confirmación que entrega el origen | Spec 021 | completa |

**No existe una sola línea de put-away.** Solo guardias en las suites de 019, 020 y 021 que prohíben
hacerlo fuera de la 022.

## 3. El delta estructural, medido

`InventoryMovement` tiene **una** columna `location_id`. Un traslado de ubicación necesita origen y
destino, igual que el estado de mercancía los necesitó en la Spec 023: sin
`source_location_id`/`target_location_id`, `recompute_balances` no puede reconstruir dónde quedó la
mercancía y la paridad incremental/reconstrucción se rompería en la dimensión de ubicación.

Es delta estructural, **no decisión**: la forma ya está resuelta por precedente en la `0046`.

## 4. `/speckit.analyze` — tres preguntas abiertas materiales

### OQ-022-01 · Qué ocurre con lo reservado cuando la mercancía se ubica · **BLOQUEANTE**

Es el centro del problema y no es evitable: es el camino normal, no un borde.

Medido en el código:

```
lock_balance(...)   → filtra location_id IS NULL en duro, y crea la fila con location_id=None
get_available(...)  → lee UNA fila, la de location_id IS NULL, y devuelve su qty_available
```

La Spec 030 reserva **exclusivamente sobre la fila de ubicación nula**. Y la Spec 021 deja
precisamente ahí la mercancía confirmada: `DISPONIBLE`, `location_id` nula. Por tanto hoy puede
existir, y existirá siempre que alguien venda antes de ubicar:

```
location NULL · DISPONIBLE · qty_on_hand = 100 · qty_reserved = 30
```

Si el put-away mueve las 100 a `L1`:

| | `qty_on_hand` | `qty_reserved` | `qty_available` de esa fila |
|---|---:|---:|---:|
| fila NULL | 0 | 30 | **−30** |
| fila L1 | 100 | 0 | 100 |

El agregado del almacén sigue siendo correcto —100 físicas, 30 comprometidas, 70 disponibles— pero
**la Spec 030 no lo ve**: bloquea la fila nula, calcula −30 y deja de poder reservar aunque haya 70
unidades reales. Ubicar la mercancía la volvería invendible.

`POL-D0-002` §7 dice que la dimensión de la reserva es «(empresa, almacén del pedido, producto)…
**Nunca ubicación**». Eso apunta a que el disponible debería agregarse por almacén y no leerse de una
fila. Pero **dónde vive el contador `qty_reserved`** cuando el stock se reparte entre ubicaciones no
lo dice ningún artefacto, y cambiar cómo la Spec 030 calcula el disponible es tocar su contrato, que
es de `D0-03`.

Opciones, con su consecuencia:

| | Qué hace | Consecuencia |
|---|---|---|
| **A** | El disponible se agrega por almacén; el reservado se queda en la fila nula como contador del almacén | Coherente con «nunca ubicación». Deja filas con `qty_available` negativo cuya lectura aislada miente |
| **B** | El reservado viaja con la mercancía a `L1` | Contradice «nunca ubicación» y convierte la reserva en asignación de ubicación, que es de la Spec 031 |
| **C** | Se bloquea el put-away mientras haya reservado | La mercancía vendida no se ubica nunca, y entonces la 031 no puede recogerla |
| **D** | El reservado se reparte proporcionalmente | Igual que B, y además inventa un criterio de reparto |

**Recomendación técnica: A**, porque es la única coherente con `POL-D0-002` §7 y la única que no
convierte la reserva en una asignación de ubicación. Pero exige cambiar cómo la Spec 030 lee el
disponible, y eso es su contrato. Una recomendación no es una decisión.

### OQ-022-02 · Qué significa la capacidad de una ubicación · **BLOQUEANTE si se aplica**

`WarehouseLocation` tiene `capacity_units`, `capacity_weight` y `capacity_uom`. Existe la magnitud;
**no existe la regla**. Ningún artefacto dice si superarla impide ubicar, si solo advierte, ni contra
cuál de las dos se compara cuando ambas están informadas, ni cómo se calcula la ocupación actual.

Inventar aritmética sobre un número sin semántica declarada sería exactamente lo que este ciclo
prohíbe. Si la capacidad no se aplica, la pregunta deja de bloquear.

### OQ-022-03 · Cómo se determina la ubicación destino · **BLOQUEANTE para el modo automático**

El DOCX §4 pide «clasificar el producto considerando: tipo de producto; familia; tamaño; peso;
rotación; volumen; condiciones especiales». Medido contra el maestro:

| Criterio | ¿Existe en `CatalogItem`? |
|---|---|
| tipo de producto | **sí** (`item_type`, `category_id`) |
| familia | no |
| tamaño | no |
| peso | no |
| rotación | no |
| volumen | no |
| condiciones especiales | parcial (`regulatory_profile_id`) |

**Cinco de siete no existen**, y crearlos es del maestro de productos (Spec 010), no de la 022. Y las
zonas del documento llevan su propia advertencia: *«Zonas preliminares que conviene validar para
HJ»* —A alta rotación, B media, C baja, D pendiente de revisión, E sobredimensionados—. El propio
documento las declara sin validar.

La ubicación **manual** —el operario elige de la estructura que la Spec 008 ya entrega— no necesita
ninguno de esos atributos y es implementable hoy. Elegir entre manual, sugerida y automática es
decisión de producto.

## 5. Lo que este ciclo deja hecho

- Las tres secciones del proceso recontadas desde el DOCX, con su reparto por Spec.
- El error de mi propio informe de la 021 corregido y explicado.
- La estructura de la Spec 008 auditada: completa, sin nada que reconstruir.
- El delta estructural del ledger medido, con su forma ya resuelta por precedente.
- La interacción con reservas medida en el código, no supuesta.
- Los criterios de clasificación contrastados uno a uno contra el maestro.

## 6. Veredicto

`SPEC 022 — BLOCKED BY MATERIAL DECISION`

`SPEC 031 — BLOCKED` (sin cambio)

BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · huérfanos 0 · **MATERIAL OQ 3**.
Código de producto modificado: **backend 0 · frontend 0 · Alembic 0**.
