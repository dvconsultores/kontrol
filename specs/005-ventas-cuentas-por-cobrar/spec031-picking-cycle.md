# SPEC 031 — COLA Y RUTA DE PICKING · CICLO DE IMPLEMENTACIÓN

> 2026-09-05, sobre `8f4b560`. Ciclo completo desde `/speckit.specify`. Se detiene antes de
> `/speckit.implement` por **tres preguntas abiertas materiales**. **Cero código de producto**:
> backend 0, frontend 0, Alembic 0.

El estado `READY_FOR_IMPLEMENTATION` que la Spec 031 tenía en el maestro no autorizaba empezar por
`implement`, y el ciclo lo confirma: la ruta estaba resuelta desde antes de abrirlo, y lo que falta
no es código sino tres decisiones de negocio que nadie ha tomado.

## 1. La fuente, leída entera

`requerimientos/Pedido - Organizar Pedido - Confirmar - Facturar - Despachar.docx`, Procesos 2 y 3.
Literal, sin resumir, porque todo el dictamen depende de qué dice y qué no dice:

**Proceso 2 · Recepción del pedido en Almacén**

| ¶ | Texto |
|---|---|
| 12 | Almacén recibe el pedido emitido por Ventas. |
| 13 | El pedido entra en la cola de preparación. |
| 14 | **Se establece el orden en que será procesado.** |
| 15-19 | Se obtiene el detalle de: productos; SKU/referencia; cantidades; **ubicaciones dentro del almacén**. |
| 20 | Salida: Pedido listo para iniciar preparación. |

**Proceso 3 · Organización de la ruta de picking**

| ¶ | Texto |
|---|---|
| 23 | Los productos no se buscan de forma aleatoria. Los pedidos se preparan siguiendo el orden de ubicación física de los productos dentro del almacén. |
| 24 | El sistema/documento identifica las ubicaciones de cada producto. |
| 25 | Se organiza el recorrido de preparación del pedido. |
| 27 | Va tomando los productos según la secuencia de ubicación. |
| 28 | Continúa el recorrido hasta completar todas las líneas del pedido. |
| 30 | Conceptualmente: **Pedido → Zona → Pasillo → Rack → Ubicación → Producto → Siguiente ubicación → Final del recorrido.** |
| 31 | Esto es un proceso de picking por ruta de ubicación. |

El ¶14 es el centro del problema. **Afirma que se establece un orden y no dice cuál.** Un barrido
por expresiones regulares del DOCX completo sobre `prioridad|orden en que|cola|urgen|antig|fecha de
entrega|FIFO|FEFO|lote|serial|vencim|parcial|dividir|split` no devuelve nada más que los ¶13 y ¶14.
La fuente no contiene el criterio.

## 2. Lo que ya existe y no hay que construir

| Capacidad | Dueña | Estado |
|---|---|---|
| Orden físico total y determinista | Spec 008 | **completo**: `physical_order_query()` ordena `zona, pasillo, rack, nivel, ubicación` con nulos primero y desempate final por `code`, que es lo que lo hace total (`FR-008-033`), expuesto en `GET /organization/locations/ordered` |
| Ubicación como dimensión del saldo | Spec 023 | existe en la clave única, con `COALESCE` null-safe |
| Procedencia de ubicación en el movimiento | Spec 022 | `source_location_id` / `target_location_id`, expuestos por `movement_dict` |
| Vendible del almacén sobre todas las ubicaciones | Spec 022 | `warehouse_sellable_on_hand()` |
| Reserva `ACTIVE` por `source_line_id` | Spec 030 | completa, de almacén, con bloqueo en PostgreSQL |
| Membresía de la cola | Spec 030 | `eligible_for_picking = (status == RELEASED)` y `released_at` en `order_dict` |
| Selección de lote por vencimiento | Spec 003 | `fefo_pick_lots()` (`FR-003-034`); el despacho ya la valida en la salida |
| Entidad del plan | Spec 032 (esqueleto) | `PickList` y `PickListLine` existen |
| Prioridad entre pedidos | `D0-03` §8 | orden de compromiso en 030; cliente, manual, SLA y ruta declarados `FUTURE` |
| Tratamiento del faltante | `D0-03` §7 | «la cadena de preparación (031/032) trata el faltante como **incidencia**, nunca como ajuste silencioso» |

**El recorrido de la 031 estaba construido antes de abrir la 031.** El ¶30 —zona, pasillo, rack,
ubicación— es exactamente el orden que la Spec 008 implementó y probó. No hay algoritmo que
inventar y no se propone ninguno: `docs/roadmap/011-unlocked-specs.md` daba «Algoritmo de ruta»
como pendiente de la 031 y la respuesta ya estaba escrita en otra Spec.

### El esqueleto que existe no es un plan

`create_picklist` (`app/modules/sales/service.py:867`) **recibe las líneas del llamante**. No calcula
cola, no calcula recorrido, no consulta el saldo, no comprueba que las líneas correspondan al pedido
ni a sus reservas. Y `PickListLine` **no tiene `location_id` ni `sequence`**: hoy es imposible
expresar «recoge esto de aquí, y de aquí antes que de allí», que es el objeto entero de la Spec 031.

Sí fija ya dos cosas que este ciclo debe respetar y no redefinir:

- `create_picklist` mueve el pedido a `PREPARING`, de modo que la arista `RELEASED → PREPARING` existe.
- `app/modules/master_data/uom.py:357` menciona `CONFIRMED` y `CLOSED` para `pick_lists`.
  **Corregido por `D0-15`:** de aquí deduje «un ciclo de vida vigente en código
  `DRAFT → CONFIRMED → CLOSED`», y no lo es. `uom.py` es un mapa de *estados en los que se congela el
  snapshot de unidad* (Spec 011), no una máquina de estados; nadie escribe nunca `CONFIRMED` ni
  `CLOSED` en un `PickList`. Lo que había era menos de lo que dije: solo `DRAFT`.

## 3. Lo que la Spec 030 entrega, y lo que deliberadamente no entrega

| Requisito | Texto | Consecuencia para la 031 |
|---|---|---|
| `FR-030-050` | «`RELEASED` habilita la cola de 031; se entregan pedido, almacén, líneas con base/presentación/lote-serial **exigidos** y reservas `ACTIVE` por `source_line_id`» | La cola sabe **quién está en ella**. Sigue sin saber **en qué orden**. «Habilitar» es entrada, no orden. |
| `FR-030-051` | «030 no crea `PickList`, no asigna ubicación, **no elige lote/serial**» | La elección de lote y serial no viene resuelta de aguas arriba. |
| `FR-030-052` | «030 no escribe estados de custodia (`RESERVADO`, `PICKING`)» | Los estados de custodia, si los hubiera, serían de la 031/032. |
| `R-D0-14-4` | «La asignación de una reserva concreta a una ubicación sigue siendo de la Spec 031» | La asignación por ubicación **está autorizada**; su regla, no escrita. |

## 4. Las once preguntas del §65, una por una

### Cerradas, con autoridad

| # | Pregunta | Autoridad | Veredicto |
|---|---|---|---|
| 1 | **Orden del recorrido** | DOCX ¶23, ¶27, ¶30, ¶31 + `physical_order_query()` (`FR-008-033`) | Zona → pasillo → rack → nivel → ubicación → código. Total y determinista. **Reutilizar, no reimplementar.** |
| 2 | **Membresía de la cola** | `FR-030-050`, `eligible_for_picking` | Los pedidos `RELEASED` del almacén. |
| 3 | **Granularidad del plan** | DOCX ¶30: «Ubicación → **Producto**» | El plan es (ubicación, producto, cantidad, secuencia). La fuente fija la granularidad y **excluye lote y serial de ella**. |
| 4 | **Batching / olas** | DOCX ¶13: «**El** pedido entra en la cola» | Fuera de alcance. Un plan por pedido. No es una pregunta abierta: es una exclusión de la fuente. |
| 5 | **Vencidos** | `RSK-003-04`, `ADR-D0-010` v2 | `VENCIDO` no es vendible y `SELLABLE_STATES` ya lo excluye. Nada que decidir. |

### Cerradas por derivación, no por invención

| # | Pregunta | Derivación |
|---|---|---|
| 6 | **División entre ubicaciones** | La reserva es **de almacén** (`POL-D0-002` §7, `R-D0-14-1`) y por tanto puede estar respaldada por existencia repartida entre ubicaciones. Negar la división haría **incumplible un compromiso que el sistema ya concedió**. El ¶30 además describe un recorrido que pasa por varias ubicaciones: «→ Siguiente ubicación →». Se deriva; no se decide. |
| 7 | **Cantidad asignable localizada** | `R-D0-14-4` autoriza asignar demanda a una ubicación. Sin descontar lo que otros planes ya asignaron allí, dos almacenistas irían a por las mismas unidades y la autorización sería inútil. La aritmética se deriva: vendible localizado en `L` menos lo asignado por planes activos en `L`. **Su liberación depende de OQ-031-3.** |
| 8 | **Lote y serial** | El plan no los elige, porque el ¶30 fija la granularidad en producto y la Spec 032 —«Picking y consolidación»— es la dueña del ¶39 «Registra o marca la línea como preparada». FEFO ya se valida donde se ejerce, en la salida. **Recomendación, no decisión:** cuando la 032 se abra, conviene medir la fricción entre FEFO y el orden de recorrido —el lote que antes vence puede estar en el extremo opuesto del almacén—. Se deja anotada; no se resuelve aquí. |

### Materiales · abiertas · bloqueantes

| # | Pregunta |
|---|---|
| **OQ-031-1** | Criterio de orden de la cola |
| **OQ-031-2** | Planificación parcial cuando lo ubicado es menor que lo reservado |
| **OQ-031-3** | Ciclo de vida del plan: cancelación, invalidación y replanificación |

## 5. Las tres decisiones que faltan

### OQ-031-1 · ¿Con qué criterio se ordena la cola?

El ¶14 afirma que se establece un orden y no dice cuál. `B-052` del backlog maestro pide «cola **con
prioridad**» sin definirla. Ninguna Spec, ADR ni política contiene el criterio.

Los datos para varios criterios **ya existen** —`released_at`, `submitted_at`, el cliente— pero
**disponer del dato no es tener la autoridad para usarlo**.

**`D0-03` §8 no decide esta cola, pero reduce mucho el espacio.** Dice, literalmente: «La única
prioridad **en 030** es el orden de compromiso… Prioridad por cliente, manual o por antigüedad de
cotización es **FUTURE** y solo tiene sentido con backorder (cola de pedidos esperando stock), que
está fuera de alcance». Esa cola y esta no son la misma —aquella es de pedidos **esperando
existencia**, esta es de pedidos que **ya la tienen reservada**— y por eso `D0-03` no la cierra. Pero
sí deja dos cosas dichas:

- **Prioridad por cliente, manual, por SLA o por ruta está declarada `FUTURE`.** Usarla en la 031
  contradiría una decisión vigente.
- **El criterio compatible con lo ya decidido es temporal**, el análogo del «orden de compromiso»
  que gobierna la reserva. Si la cola de preparación usara otro, un pedido que perdió la carrera por
  la mercancía podría prepararse antes que el que la ganó, y esa incoherencia entre dos etapas de la
  misma cadena se introduciría sin autoridad ninguna.

**Lo que queda por decidir, ya acotado: qué marca temporal.** `submitted_at` —el compromiso, que es
cuando se reservó, por el disparador `ORDER_CONFIRMATION`— o `released_at` —cuando el pedido entró en
la cola—. No son la misma: un pedido confirmado antes pero liberado después, por retención de
crédito, cae en distinto lugar según cuál se elija. **La decisión es si una retención de crédito le
cuesta al pedido su puesto en la fila.** Eso es negocio, no implementación.

Se anota además una lectura posible del ¶14 —«**se establece** el orden», en voz activa y dentro de
un proceso ejecutado por Almacén, admite leerse como ordenación manual— **sin adoptarla**: es una
lectura, y `D0-03` marca la prioridad manual como `FUTURE`.

### OQ-031-2 · ¿Se planifica parcialmente cuando lo ubicado es menor que lo reservado?

Esta pregunta la creó la Spec 022 al implementarse. El put-away es **manual** (`R-D0-14-8`) y la
reserva es **de almacén**, de modo que la mercancía sin ubicar cuenta como disponible y se reserva.
Un pedido puede estar, por tanto, íntegramente reservado y solo parcialmente ubicado.

Las dos salidas tienen consecuencia operativa real y opuesta:

- **Planificar lo ubicado y dejar el resto pendiente** hace que el almacenista salga con una lista
  incompleta y obliga a definir qué ocurre con el resto.
- **No planificar hasta que todo esté ubicado** deja el pedido detenido por una tarea de almacén que
  nadie le ha pedido a nadie, y `POL-D0-002` §3 —todo o nada por pedido a nivel de almacén— empuja
  en esa dirección sin llegar a decidirlo.

**`D0-03` §7 cierra una parte:** «un almacén con sobreventa permitida puede tener `qty_available < 0`;
**la cadena de preparación (031/032) trata el faltante como incidencia**, nunca como ajuste
silencioso». La causa allí es otra —sobreventa, no mercancía sin ubicar— pero la forma es idéntica: el
plan no puede cubrir la línea. De modo que **la tercera salida, la silenciosa, queda prohibida**: sea
cual sea la decisión, el faltante se registra como incidencia.

Lo que sigue sin autoridad es si el plan **avanza** con lo ubicado mientras tanto. Inventarlo
decidiría, en silencio, si KONTROL sirve pedidos incompletos.

### OQ-031-3 · ¿Qué le pasa a un plan cuando la realidad cambia?

`PickList.status` nace `DRAFT` **sin restricción `CHECK` en la migración y sin máquina de estados
documentada**. El código congela unidades en `CONFIRMED` y `CLOSED`, y `create_picklist` mueve el
pedido a `PREPARING`. Eso es todo lo que hay.

Quedan sin definir: si un plan se puede **cancelar** y qué le ocurre entonces al pedido; si un plan
confirmado se **invalida** cuando la mercancía que tenía asignada se mueve, se ajusta o se
reclasifica; y si se **replanifica** o se corrige a mano. El ¶77 del DOCX —«El pedido regresa a
preparación/corrección según corresponda»— habla del control posterior a la consolidación, que es de
la Spec 032, y no resuelve esto.

Es material por partida doble: sin ciclo de vida, un plan obsoleto manda al almacenista a una
ubicación vacía, y **la asignación localizada de la pregunta 7 no tiene evento que la libere**, con lo
que la existencia quedaría asignada para siempre a un plan muerto.

## 6. Lo que este ciclo no ha hecho, a propósito

- No se ha creado `specs/031-*` ni ninguna Spec paralela. Este documento vive en la Spec dueña.
- No se ha añadido `location_id` ni `sequence` a `PickListLine`: son necesarios, pero su semántica
  depende de OQ-031-2 y OQ-031-3.
- No se ha escrito algoritmo de ruta: existe en la Spec 008.
- No se ha inventado prioridad, ni FIFO, ni FEFO en la cola, ni política de división, ni estados.
- No se ha tocado la reserva, que sigue siendo de almacén.

## 7. Qué desbloquea cada respuesta

| Decisión | Habilita |
|---|---|
| OQ-031-1 | El orden de la cola y su prueba de determinismo |
| OQ-031-2 | La regla de planificación y el contrato del plan incompleto |
| OQ-031-3 | Los estados del plan, su `CHECK`, y la liberación de la asignación localizada |

Con las tres respondidas, la 031 es implementable en un solo ciclo: el recorrido, la aritmética
localizada y la división ya están derivados o construidos.


---

# 8. CIERRE — `D0-15`, 2026-09-05

Las tres preguntas quedaron cerradas por el checkpoint `D0-15`, documental y sin código de producto.
Las decisiones completas, con su evidencia y sus matrices, están en
`docs/governance/d0-foundational-decisions/d0-15-checkpoint/`.

| | Pregunta | Cierre |
|---|---|---|
| **OQ-031-1** | Orden de la cola | `released_at ASC`, desempate `id ASC`. Una retención de crédito **no** conserva el puesto (`R-D0-15-1..4`) |
| **OQ-031-2** | Planificación parcial | Permitida solo en `DRAFT`, con remanente explícito; `CONFIRMED` exige el 100 % (`R-D0-15-5..9`) |
| **OQ-031-3** | Ciclo de vida | Cinco estados: `DRAFT`, `CONFIRMED`, `CLOSED`, `CANCELLED`, `INVALIDATED` (`R-D0-15-10..19`) |

La primera se cerró con evidencia que este ciclo tenía delante y no leyó como autoridad: el docstring
de `_a_released` dice «el pedido entra en la cola de 031» **en la misma función que escribe
`released_at`**. No era una fecha disponible entre varias; era el sello del acto de entrada.

`D0-15` deja además dos exigencias sobre el modelo de la Spec 030 que el ciclo de implementación debe
satisfacer: que crear un plan `DRAFT` no saque al pedido de `RELEASED` (`R-D0-15-18`), y que exista
`PREPARING → RELEASED` para que cancelar un plan confirmado no vare el pedido (`R-D0-15-19`).

**Estado: `READY TO RESUME IMPLEMENTATION`.** No implementada. El próximo ciclo empieza de nuevo en
`/speckit.specify`, y su primer precheck es reconstruir PostgreSQL y ClamAV y validar el número de
saltos esperado.
