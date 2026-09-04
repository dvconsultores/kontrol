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


---

# LAS TRES PREGUNTAS, RESUELTAS — `D0-14` (2026-09-04)

El checkpoint `D0-14` cerró las tres el mismo día. Ninguna necesitaba una decisión nueva: la primera
ya estaba decidida y faltaba leer su consecuencia; las otras dos se cierran porque el dato que haría
falta para decidir otra cosa **no existe**, y no imponer una regla es lo único que no inventa una.

| OQ | Resultado | Regla |
|---|---|---|
| **01** reservas | La reserva es un compromiso de **almacén**, no de ubicación. Un put-away puro conserva el reservado y el disponible del almacén | `R-D0-14-1..5` |
| **02** capacidad | **Informativa** en V1. No bloquea. Sin avisos calculados mientras `capacity_uom` sea texto libre | `R-D0-14-6/7` |
| **03** selección | **Manual**, con las candidatas filtradas por el backend. Automatismo diferido | `R-D0-14-8/9/10` |

Detalle, matrices y alternativas rechazadas en
`docs/governance/d0-foundational-decisions/d0-14-checkpoint/`.

**`SPEC 022 — READY TO RESUME IMPLEMENTATION`.** Lo que hereda el ciclo productivo está en la
convergencia de `D0-14`: reconciliar `lock_balance` y `get_available` para que el disponible sea del
almacén, elegir la representación del contador reservado entre las tres compatibles, añadir la
procedencia de ubicación al movimiento, y el put-away manual. Ninguna de esas es una decisión.

---

# CICLO REANUDADO — IMPLEMENTACIÓN (2026-09-04)

> El mismo ciclo, retomado tras `D0-14 — CLOSED`. No se abrió Spec nueva.

## Los cuatro trabajos, y ninguno era una decisión

### A · El disponible deja de ser el de una fila

Era el defecto que bloqueó la Spec. `lock_balance` filtraba `location_id IS NULL` en duro y
`get_available` leía esa única fila, de modo que ubicar la mercancía la habría vuelto invendible.

Ahora existe `warehouse_sellable_on_hand`, que **suma** la existencia vendible del almacén sobre
todas las ubicaciones, y `available_under_lock` resta de ahí el compromiso. No suma
indiscriminadamente: solo los estados vendibles de `ADR-D0-010`, así que cien unidades en cuarentena
siguen sin ser cien disponibles.

`lock_balance` sigue bloqueando la fila de ubicación nula —ahora parametrizable—, y hace bien: es un
único punto de serialización por empresa, almacén y producto, que es lo que la garantía de
concurrencia de la Spec 030 necesita.

### B · Dónde vive el contador reservado

`D0-14` dejó tres representaciones compatibles y la elección como decisión de ingeniería. **Se eligió
la A**: el contador sigue en la fila ancla de ubicación nula.

| Criterio | Por qué decide |
|---|---|
| Corrección | Cumple las cinco invariantes de `R-D0-14-5` |
| Compatibilidad | `recompute_balances` **ya** proyectaba las reservas sobre esa fila. No hay divergencia entre el camino incremental y el reconstruido |
| Auditabilidad | Un solo lugar donde mirar el compromiso de un producto en un almacén |
| Concurrencia | Un único punto de bloqueo; no hay que ordenar bloqueos entre ubicaciones para reservar |
| Migración | **Ninguna**. No se movió un solo dato |

No se eligió por ser la de menos código: se eligió porque es la única que no introduce divergencia
entre lo que el motor escribe y lo que la reconstrucción produce. Su contrapartida —que esa fila
pueda mostrar `qty_available` negativo leída en aislamiento— está declarada en `D0-14` y se
neutraliza con un guardia: **ningún módulo lee una sola fila para decidir disponibilidad de almacén**.

### C · El ledger deja de suponer la ubicación

`InventoryMovement` gana `source_location_id` y `target_location_id`, con la misma forma y por la
misma razón que el estado en la `0046`. La reconstrucción los lee: un traslado tiene los dos estados
iguales y las dos ubicaciones distintas; una reclasificación, al revés. La misma aritmética cubre
ambos.

El backfill de la `0048` no inventa dirección: la `location_id` histórica era la ubicación sobre la
que el motor escribió el saldo, y el signo de la cantidad dice si la mercancía entró o salió de ella.
Las filas sin ubicación no se tocan, porque nunca tuvieron una.

### D · El put-away manual

`putaway_candidates` devuelve las ubicaciones activas del almacén, ordenadas solo para que la lista
sea estable. Sin puntuación, sin recomendación, sin «la más vacía»: los atributos que la clasificación
del proceso pide no existen en el maestro y las zonas están sin validar (`R-D0-14-10`).

`putaway` valida la ubicación **en el envío**, no solo al listar: entre que la pantalla carga y el
operario confirma, una ubicación puede desactivarse, y un identificador de otra empresa o de otro
almacén no autoriza nada. Bloquea las dos filas en orden determinista, mueve `qty_on_hand` y **nunca**
`qty_reserved`.

La capacidad se muestra con su unidad declarada y no filtra ni bloquea. La API lo dice en el propio
contrato: `"enforced": false`.

## Pruebas

| Nivel | Suite | Casos |
|---|---|---:|
| Funcional multiempresa | `test_spec022_putaway.py` | 13 |
| Estructural | `test_spec022_architecture.py` | 14 |
| Migración y concurrencia | `test_spec022_migration_0048.py` | 7 |

Las que sostienen la Spec son dos carreras reales sobre PostgreSQL: dos colocaciones simultáneas de
sesenta sobre un origen de cien —gana una, el físico sigue siendo cien— y una reserva concurrente con
una colocación, donde ambas prosperan, el compromiso no se pierde y el físico no se duplica.

## Lo que deliberadamente no se hizo

- **Ninguna tabla nueva.** La existencia sin ubicar ya se representa con `location_id` nula;
  duplicarla en otra tabla habría creado la segunda verdad física que `R-D0-14-5` prohíbe.
- **Ninguna arista nueva** en `ADR-D0-010`. El put-away conserva el estado, y un guardia comprueba
  que `DISPONIBLE → DISPONIBLE` sigue sin existir.
- **Ningún permiso nuevo.** Se usa `inventario:create`, que ya existe y es exactamente «escribir
  movimientos de inventario». Un guardia comprueba que todo permiso citado por la API exista en el
  catálogo — la lección de la Spec 021.
- **Nada de la Spec 031**: ni cola, ni ruta, ni asignación de una reserva a una ubicación.
- **Nada de la Spec 025**: el destino debe ser del mismo almacén, y un guardia lo comprueba.
- **Ninguna aritmética de capacidad**: ni ocupación, ni volumen, ni peso, ni porcentajes.
