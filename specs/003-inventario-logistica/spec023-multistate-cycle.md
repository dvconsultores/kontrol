# SPEC 023 — CAPACIDAD DE SALDO MULTIESTADO · CICLO DIRIGIDO

> Ciclo dirigido sobre la Spec 023 existente. No crea Spec nueva. Ejecutado el 2026-09-03 sobre
> `7dc1fe1`, rama `develop`, PostgreSQL 18.6, cabeza única `0045_spec020_incidents`.

## 1. Qué se pidió y qué se encontró

El checkpoint posterior a la Spec 030 dejó a la Spec 021 con un solo bloqueo: *el motor de saldos
escribe únicamente `DISPONIBLE`*. Este ciclo audita esa capacidad y determina si el `ADR-D0-010`
contiene autoridad suficiente para implementarla sin una decisión nueva de producto.

**La respuesta es que no del todo, y el matiz importa.** La dimensión existe y está mejor construida
de lo que el checkpoint suponía. Lo que falta no es la columna: es el contrato de la transición.

## 2. Tres correcciones al enunciado de partida

### 2.1 El ADR no declara siete estados: declara quince

El prompt del ciclo pedía «extraer los siete estados exactos». Los siete existen, pero son otra cosa:
son los estados de **lote y serial** de `FR-003-035` —`DISPONIBLE, RESERVADO, TRANSITO, CUARENTENA,
VENCIDO, RECHAZADO, DESECHO`—, implementados en `LOT_SERIAL_TRANSITIONS` y aplicados a
`InventoryLot.status` y `InventorySerial.status`.

El `ADR-D0-010` declara **quince** estados de mercancía para `InventoryBalance.state`: siete
conservados, siete nuevos y `ESPERADO`, marcado **FUTURE** (Spec 018). El propio ADR lo dice:
«Estados existentes conservados: 7 · Estados nuevos: 7».

Son dos vocabularios distintos sobre dos entidades distintas. `VENCIDO` existe en el de lote/serial y
**no** en el de mercancía. Confundirlos habría producido exactamente lo que el prompt prohíbe en §12.

### 2.2 El estado ya forma parte de la clave del saldo

`uq_inventory_balances_key` es único sobre
`(company_id, warehouse_id, COALESCE(location_id,''), product_id, COALESCE(lot_id,''), COALESCE(serial_id,''), state)`.

La dimensionalidad multiestado **ya está construida**, con la estrategia null-safe que §64 pedía
evaluar: normalización a `''` dentro de un índice único parcial de PostgreSQL. No hay delta
estructural en la clave.

### 2.3 Los puntos de escritura no son cinco: son diez

| # | Call site | Operación | Estado escrito hoy | ¿Necesita estado parametrizable? | Dueño |
|---|---|---|---|---|---|
| 1 | `inventory/api.py:271` | movimiento manual | `DISPONIBLE` | **Sí** — es la puerta genérica del motor | 023 |
| 2 | `inventory/api.py:618` | operación de entrada | `DISPONIBLE` | Sí | 023 |
| 3 | `inventory/api.py:641` | operación de despacho | `DISPONIBLE` | Según catálogo (`DESPACHADO`) | 035 |
| 4 | `inventory/service.py:476` | reverso de movimiento | hereda | Debe heredar el del original | 023 |
| 5 | `inventory/service.py:990` | salida de transferencia | `DISPONIBLE` | `TRANSITO` según ADR | 025 |
| 6 | `inventory/service.py:1019` | entrada de transferencia | `DISPONIBLE` | **`CUARENTENA` si hay diferencia** | 025 |
| 7 | `inventory/service.py:1083` | ajuste aplicado | `DISPONIBLE` | Según motivo del ajuste | 025 |
| 8 | `inventory/service.py:1148` | operación de inventario | `DISPONIBLE` | Sí | 023 |
| 9 | `purchasing/service.py:645` | aceptación de recepción | `DISPONIBLE` | **`RECIBIDO`** cuando 021 lo decida | 021 |
| 10 | `sales/service.py:932` | salida por venta | `DISPONIBLE` | Según catálogo | 035 |

**El caso 6 es un defecto vivo, no una carencia.** `confirm_transfer_receipt` escribe
`line.destination_state = "CUARENTENA"` cuando hay diferencia entre lo enviado y lo recibido, y acto
seguido llama a `record_movement`, que ignora ese campo y suma en `DISPONIBLE`. El sistema **ya
declara** una intención de cuarentena que el motor no sabe ejecutar. El campo guarda una decisión
que nadie aplica.

## 3. Clasificación de cada regla del ADR-D0-010

| Regla | Contenido | Clasificación |
|---|---|---|
| R-D0-10-1 | Estado de documento ≠ estado de mercancía | **ACTIVE / IMPLEMENTABLE** — es principio, no operación |
| R-D0-10-2 | Se extiende el conjunto en español, no se renombra | **ACTIVE / IMPLEMENTABLE** — ya cumplido |
| R-D0-10-3 | Vendible es **exclusivamente** `DISPONIBLE` | **ACTIVE / IMPLEMENTADA** — la consulta de disponible ya filtra por ese estado |
| R-D0-10-4 | El paso a `DISPONIBLE` desde la recepción exige liberación formal (021) | **ACTIVE / INCOMPLETE** — vinculante y hoy incumplida: la recepción escribe `DISPONIBLE` directamente |
| R-D0-10-5 | Toda transición es un **movimiento**; el saldo se reconstruye desde movimientos | **ACTIVE / INCOMPLETE** — imposible hoy: el movimiento no tiene columna de estado |
| R-D0-10-6 | `BLOQUEADO` solo se libera cerrando la incidencia | **ACTIVE / IMPLEMENTABLE** — la Spec 020 ya entrega el cierre |
| R-D0-10-7 | Las transiciones no declaradas están prohibidas; el motor las rechaza | **ACTIVE / INCOMPLETE** — **vinculante e inimplementable: el ADR no declara ninguna transición** |
| R-D0-10-8 | `ESPERADO` no computa como existencia física | **FUTURE** — su dueño es la Spec 018, no iniciada |

## 4. Catálogo de estados, extraído

| Estado | Significado (literal del ADR) | Vendible | Reservable | Origen de la autoridad | ¿Escrito hoy? |
|---|---|---|---|---|---|
| `ESPERADO` | Comprometido en orden o embarque; aún no llegó | No | No | ADR + R-D0-10-8 · **FUTURE** | No |
| `RECIBIDO` | Físicamente recibido, aún no conciliado | No | No | ADR (nuevo) | No |
| `PENDIENTE_CONFIRMACION` | En conteo o conciliación | No | No | ADR (nuevo) | No |
| `CUARENTENA` | Retenido por calidad o inspección | No | No | ADR (conservado) | No |
| `BLOQUEADO` | Retenido por incidencia abierta o disputa | No | No | ADR (nuevo) + R-D0-10-6 | No |
| `DISPONIBLE` | Liberado formalmente | **Sí** | **Sí** | R-D0-10-3 · R-D0-03-5 · POL-D0-002 §7 | **Sí, el único** |
| `RESERVADO` | Comprometido a un pedido | No | No | ADR (conservado) — **ver §5** | No |
| `PICKING` | En proceso de extracción | No | No | ADR (nuevo) | No |
| `PREPARADO` | Extraído y consolidado, pendiente de confirmación | No | No | ADR (nuevo) | No |
| `TRANSITO` | En traslado entre almacenes | No | No | ADR (conservado) | No |
| `DESPACHADO` | Salió físicamente | No (fuera de existencia) | No | ADR (nuevo) | No |
| `DEVUELTO` | Reingresado, pendiente de inspección | No | No | ADR (nuevo) | No |
| `RECHAZADO` | No apto; no se incorpora | No | No | ADR (conservado) | No |
| `DESECHO` | Destruido o descartado | No | No | ADR (conservado) | No |
| `VENDIDO` | Consumido por venta | No | No | ADR (conservado) | No |

**Vendibilidad y reservabilidad no requieren decisión nueva.** R-D0-10-3 las cierra de un golpe:
vendible es exclusivamente `DISPONIBLE`. `ADR-D0-003 v2` R-D0-03-5 y `POL-D0-002` §7 añaden que la
reserva solo consume saldo `DISPONIBLE` y **no cambia el estado de custodia**. La columna
«Reservable» de arriba se deriva, no se inventa.

## 5. `RESERVADO` no es el mecanismo de reserva

El prompt advertía en §13 que `RESERVADO` podía existir como estado de custodia o como ciclo de vida
de la reserva. La autoridad ya lo resolvió y conviene dejarlo escrito:

> `POL-D0-002` §1: «Reservado — Unidades base comprometidas a líneas de pedido emitidas y no
> extraídas. **Contador sobre el saldo `DISPONIBLE`; no es un estado de custodia**».

La reserva vive en `qty_reserved` sobre la fila `DISPONIBLE` y en filas `Reservation`. El estado
`RESERVADO` del catálogo del ADR **no tiene hoy productor ni consumidor**, y ninguna Spec construida
lo escribe. No es ambigüedad: es un estado del catálogo sin dueño activo.

## 6. Disponibilidad — autoridad única, ya correcta

> `POL-D0-002` §1: `Disponible = físico − reservado − bloqueado = qty_on_hand − qty_reserved` de la
> fila `DISPONIBLE`.

El código ya lo hace: la consulta de disponible filtra `state == "DISPONIBLE"` y `lock_balance` usa
`state="DISPONIBLE"` por defecto, que es como lo llama la confirmación de pedidos de la Spec 030.

**La prueba P0 del §44 del prompt ya pasa hoy, y se midió en vez de razonarse.** Sembrando en
PostgreSQL diez unidades `DISPONIBLE` y cien `CUARENTENA` del mismo producto y almacén:

```
físico total = 110 | get_available = 10.000000 | available_under_lock = 10.000000 | fila bloqueada = DISPONIBLE
```

La suma nunca cruza estados, ni en la consulta ni bajo bloqueo. No hay que construir esa garantía:
hay que **protegerla con una prueba propia** cuando existan saldos en otros estados, porque hoy
ninguna la cubre —no había con qué—. La verificación se hizo con `rollback`: no dejó datos.

## 7. Consumidores de saldo, clasificados

| Consumidor | Qué necesita | ¿Roto por multiestado? |
|---|---|---|
| `sales/service.py:644` — confirmación de pedido | Vendible | **No**: ya bloquea y lee la fila `DISPONIBLE` |
| `inventory/service.py:300` — disponible | Vendible | **No**: ya filtra por estado |
| `inventory/api.py:212` — listado de existencias | Desglose por estado | **No**: ya admite `state` como filtro |
| `reporting/service.py:147` — reporte operativo | **Total físico** | **No**: suma todos los estados, que es la semántica correcta de un total físico, y expone `state` por fila |
| `inventory/service.py:244` — reconstrucción | Todos | **Sí** — ver §8 |

Ningún consumidor asume «una sola fila por producto y almacén». La plataforma resiste el multiestado
mejor de lo que el checkpoint anticipó.

## 8. El hueco estructural real: el ledger no lleva el estado

`InventoryMovement` tiene empresa, almacén, ubicación, producto, tipo, cantidad, unidad, coste,
presentación, factor y cantidad base. **No tiene estado de mercancía. Ni lote ni serial.**

Y `recompute_balances` fija `state="DISPONIBLE"` para cada movimiento al reconstruir el saldo, porque
es lo único coherente que puede hacer con un ledger que no guarda el estado.

Esto choca de frente con R-D0-10-5: «el saldo se reconstruye desde movimientos». Con saldos en varios
estados, una reconstrucción **hoy los colapsaría todos en `DISPONIBLE`**, destruyendo la información
que la capacidad viene a crear. No es un riesgo teórico: `recompute_balances` está expuesto y borra
las filas antes de recrearlas.

**Este es el delta estructural del ciclo:** el movimiento necesita evidencia de estado —origen y
destino— para que el saldo multiestado sea reconstruible. Sin él, la capacidad nace violando el
principio P5 que la sostiene.

## 9. Preguntas de `/speckit.clarify` — 36 planteadas, 34 resueltas con autoridad existente

Resueltas por `ADR-D0-010`, `ADR-D0-003 v2`, `POL-D0-002`, `FR-003-035` o por medición del código:
el catálogo y su tamaño (§2.1), la clave del saldo (§2.2), la vendibilidad y la reservabilidad (§4),
la naturaleza de `RESERVADO` (§5), la fórmula de disponible (§6), los productores actuales de cada
estado (§2.3), los consumidores (§7), la ausencia de estado en el ledger (§8), la estrategia
null-safe de unicidad (§2.2), el gobierno del catálogo —enum semántico global, no configurable por
empresa, porque `R-D0-10-3` fija la vendibilidad sin excepción de empresa—, y la clasificación de
los saldos heredados: **47 filas, todas `DISPONIBLE`, legítimamente `DISPONIBLE`**; ninguna se
reinterpreta.

Dos no se resuelven sin decisión de producto. Son las de §10.

## 10. `/speckit.analyze` — dos preguntas abiertas materiales

### OQ-023-MS-01 · No existe la tabla de transiciones que R-D0-10-7 hace obligatoria

R-D0-10-7 es vinculante: «Las transiciones no declaradas están prohibidas; el motor las rechaza».
Ningún artefacto de KONTROL declara **ninguna** transición entre estados de mercancía. La única
tabla de transiciones del motor, `LOT_SERIAL_TRANSITIONS`, gobierna lotes y seriales, es otro
vocabulario y no incluye siete de los quince estados.

Sin la tabla, el motor no puede ni permitir ni rechazar: un motor permisivo incumple R-D0-10-7 y uno
restrictivo no tiene contra qué contrastar. Y sin transición legal no hay reclasificación; sin
reclasificación, la Spec 021 no puede liberar `RECIBIDO → DISPONIBLE`, que es exactamente lo que este
ciclo debía habilitar.

Derivar el grafo del significado de cada estado sería inventarlo. El significado sugiere la
secuencia; no la declara. Y la decisión reparte competencias entre Specs no construidas —022, 025,
031, 032, 035, 036—, lo que la hace decisión de producto, no de ingeniería.

**Mínimo que la decisión debe cubrir para desbloquear la 021:** las transiciones de la cadena de
recepción, incluida la liberación formal a `DISPONIBLE` y la entrada y salida de `BLOQUEADO` que
R-D0-10-6 ya condiciona al cierre de la incidencia.

### OQ-023-MS-02 · Qué ocurre con lo reservado cuando el saldo se reclasifica

`POL-D0-002` fija que el reservado es un contador sobre la fila `DISPONIBLE` y que la reserva no
cambia el estado de custodia. No dice qué pasa en el sentido contrario: cuando una cantidad
`DISPONIBLE` con reserva viva se reclasifica a un estado no vendible.

Mover la cantidad reduce `qty_on_hand` de la fila `DISPONIBLE` y puede dejar `qty_reserved >
qty_on_hand`, es decir disponible negativo, por una vía que **no** es la sobreventa autorizada de
`allow_negative`. `POL-D0-002` §6 prohíbe la sobreventa salvo por esa política explícita, así que
producirla por reclasificación contradiría la política.

Las tres salidas posibles —bloquear la transición mientras haya reservado, mover solo lo no
reservado, o liberar las reservas primero— tienen consecuencias comerciales distintas: la tercera
cancela compromisos con clientes sin que nadie de ventas intervenga. Elegir es decisión de producto.

## 11. Lo que **no** es pregunta abierta, y conviene no confundir

- **Conservación de cantidad.** Se deriva de R-D0-10-5: si la transición es un movimiento, una
  reclasificación pura no crea ni destruye físico. No hace falta decidirlo.
- **Cantidad negativa por transición.** Se deriva de la conservación: no se puede mover más de lo que
  hay en el origen. No es decisión.
- **Salida de `CUARENTENA`.** Es un subconjunto de OQ-01, no una pregunta aparte.
- **Gobierno del catálogo.** R-D0-10-3 fija la vendibilidad sin excepción por empresa: el catálogo es
  enum semántico global. No se cambia el gobierno.

## 12. Puerta

| Criterio | Exigido para implementar | Resultado |
|---|---|---|
| Constitution Gate | PASS | **PASS** — un solo motor, una sola autoridad de saldo y de disponible, sin flujo de 021, `CompanyContext` intacto |
| BLOCKER | 0 | 0 |
| CRITICAL | 0 | 0 |
| CONTRADICTIONS | 0 | 0 |
| Requisitos huérfanos | 0 | 0 |
| Tareas huérfanas | 0 | 0 |
| **OQ material** | **0** | **2** |
| Trazabilidad | 100 % | 100 % del alcance auditado |

`/speckit.implement` **no se ejecuta.** La autorización del §5 del ciclo es condicional y la
condición no se cumple.

## 13. Veredicto

`SPEC 023 MULTI-STATE BALANCE CAPABILITY — BLOCKED BY MATERIAL DECISION`

`SPEC 021 — BLOCKED`

Cero líneas de código de producto modificadas. Cero migraciones. Cero cambios de contrato.

---

# CICLO RETOMADO — IMPLEMENTACIÓN (2026-09-04)

> El mismo ciclo dirigido, reanudado tras `D0-10 — CLOSED` y `ADR-D0-010` v2. No se abrió Spec nueva
> ni ciclo paralelo. `/speckit.implement` se ejecutó con la autorización condicional cumplida:
> Constitution Gate PASS, OQ material 0.

## 14. Lo que se construyó

### 14.1 Una autoridad de estados donde no había ninguna

`app/modules/inventory/states.py`. Antes, el catálogo vivía en un ADR y el motor escribía
`DISPONIBLE` fijo; `R-D0-10-7` obligaba a rechazar lo no declarado y no había contra qué decidir.

Contiene los quince estados, `SELLABLE_STATES` y `RESERVABLE_STATES` —ambos `{DISPONIBLE}` por
`R-D0-10-3` y `R-D0-03-5`—, y las transiciones activas con evidencia, permiso, aprobación y motivo.
`can_transition` y `assert_transition` son la única puerta: lo no declarado es `DENIED`, sin
inferencia por parecido.

**Diez entradas en la tabla, no nueve.** Las nueve del ADR v2 más la que la propia v2 conserva en su
§Migración: la entrada a `DISPONIBLE` que todos los llamantes usan hoy y que solo la Spec 021 puede
cambiar. Contarlas como nueve habría roto el sistema entero al primer movimiento.

### 14.2 Procedencia de estado en el ledger

`InventoryMovement` gana `source_state` y `target_state`, con `CHECK` que exige al menos uno.

| Caso | `source_state` | `target_state` |
|---|---|---|
| Entrada | `NULL` | destino |
| Salida | origen | `NULL` |
| Reclasificación | origen | destino |

Migración `0046`. El backfill **no supone**: hasta esta migración `record_movement` escribía el saldo
con `state="DISPONIBLE"` fijo, sin parámetro ni excepción, y eso es comprobable en el código de todas
las versiones anteriores. Las entradas tuvieron `DISPONIBLE` por destino y las salidas por origen.
Si alguna fila quedara sin clasificar, la migración **aborta** en vez de rellenarla a ciegas.

### 14.3 `record_movement` deja de fijar el estado

Admite `state`. Valida contra la matriz **antes** de convertir unidades o escribir nada, y exige la
aprobación de la Spec 045 cuando la arista la declara. Sin `state`, el default declarado sigue siendo
`DISPONIBLE`: es compatibilidad contractual, no inercia.

### 14.4 `reclassify`, el único camino legal de transición

Matriz → motivo → aprobación → bloqueo de las dos filas en orden determinista → validación de
cantidad → invariante `R-D0-10-9` → ledger → saldos → auditoría. Nadie más toca
`InventoryBalance.state`, y un guardia estructural falla si alguien lo intenta.

### 14.5 Dos defectos vivos cerrados

**El de la transferencia**, que el checkpoint anterior había medido: `confirm_transfer_receipt`
decidía `destination_state = "CUARENTENA"` ante una diferencia y el motor lo ignoraba, dejando a la
venta mercancía con faltante. Ahora el destino que decide el consumidor es el que se materializa.

**El de la reconstrucción, que nadie había visto.** `recompute_balances` acumulaba
`m.quantity` —la cantidad **tecleada**— en lugar de la base. Es exactamente la caja ×12 que la Spec
019 corrigió en el camino incremental y que aquí seguía viva: reconstruir un saldo de dos cajas de
doce devolvía 2 en vez de 24. Nadie lo detectó porque ninguna prueba comparaba los dos caminos.
Ahora la reconstrucción usa la cantidad base y lee el estado del ledger en vez de fijar `DISPONIBLE`.

## 15. Lo que deliberadamente no se hizo

- **No se implementó política de conflicto con reservas.** `R-D0-10-10` la reserva para la Spec que
  active la primera arista con origen `DISPONIBLE`. Ninguna activa lo tiene, así que no es alcanzable.
  La invariante `R-D0-10-9` sí se comprueba, porque es del motor y no de la tabla que hoy tenga.
- **No se tocó `get_available`.** Ya filtraba por estado y ya era correcto.
- **No se expuso `state` en la API pública.** El consumidor de esta capacidad es la Spec 021, que
  opera a nivel de servicio, y la corrección de la transferencia es interna. Cambiar el contrato
  público sin requisito habría ampliado el alcance y el radio de impacto sin necesidad.
- **No se implementó nada de la 021**: ni confirmación, ni conciliación, ni liberación de lote, ni
  endpoint alguno. Un guardia estructural lo comprueba por nombre.
- **No se activó ninguna arista futura**, ni siquiera las que «se ven venir» como
  `RECIBIDO → PENDIENTE_CONFIRMACION`. Su dueña las declarará con su evidencia.

## 16. Pruebas

| Nivel | Suite | Casos |
|---|---|---:|
| Funcional multiempresa | `test_spec023_multistate.py` | 20 |
| Estructural | `test_spec023_architecture.py` | 14 |
| Migración, integridad y concurrencia | `test_spec023_migration_0046.py` | 6 |

La que sostiene la Spec es la paridad: escribir por el camino incremental y reconstruir desde el
ledger deben dar **exactamente** los mismos saldos, estado por estado. Y la carrera: dos
reclasificaciones simultáneas pidiendo 8 de un origen de 10 —gana una, el físico sigue siendo 10—.
