# D0-15 — DECISIONES DE PLANIFICACIÓN DE PICKING

> Cierra las tres preguntas materiales que bloqueaban la Spec 031. Ciclo documental: **código de
> producto 0**. Sobre `d65ec0d`.

## Lo que las tres tienen en común

`D0-14` cerró sus tres preguntas **negándose a inventar**. Estas tres se cierran por lo contrario:
la autoridad existía y estaba sin leer. Dos de ellas la tenían escrita **en el propio código**, en un
sitio donde nadie la había buscado; la tercera se cierra tras descubrir que lo que el ciclo anterior
llamó «un ciclo de vida vivo en código» no era tal cosa.

### Corrección de un hallazgo del ciclo anterior

`spec031-picking-cycle.md` afirmó que existía «un ciclo `DRAFT → CONFIRMED → CLOSED` vivo en
`uom.py:357` y sin documentar». **No es un ciclo de vida.** `uom.py` contiene un mapa de
`tabla → estados en los que el snapshot de unidad queda congelado` (Spec 011, `R-D0-09-1`); que
mencione `CONFIRMED` y `CLOSED` para `pick_lists` no los convierte en estados existentes.

Lo que hay de verdad es menos: `create_picklist` escribe `DRAFT` y **ningún código escribe nunca
`CONFIRMED` ni `CLOSED`** en un `PickList`. No hay máquina, ni `CHECK`, ni consumidor.

La lista de congelación tiene además un defecto propio que este checkpoint deja anotado sin
resolver, porque es de la Spec 011: para `sales_orders` declara congelar en `CONFIRMED`, `APPROVED`,
`CLOSED` e `INVOICED`, y de esos cuatro **solo `CLOSED` existe** en `ORDER_TRANSITIONS`. La regla de
congelación de unidades de un pedido de venta, por tanto, casi nunca se dispara. No se corrige aquí.

---

# OQ-031-1 · Con qué criterio se ordena la cola

## La pregunta

El ¶14 del proceso fuente afirma que «se establece el orden en que será procesado» y no dice cuál.
El ciclo anterior acotó el espacio a dos marcas temporales, `submitted_at` y `released_at`, y planteó
la pregunta de negocio como: **¿una retención de crédito le cuesta al pedido su puesto en la fila?**

## La evidencia

| Fuente | Qué dice |
|---|---|
| `app/modules/sales/service.py:600` | Docstring de `_a_released`: «`→ RELEASED`: la reserva se hace firme y **el pedido entra en la cola de 031**» |
| `app/modules/sales/service.py:606` | `order.released_at = ahora`, en esa misma función y transacción |
| `FR-030-050` | «`RELEASED` habilita la cola de 031» |
| `order_dict` | `eligible_for_picking = (status == RELEASED)` |
| `D0-03` §8 | «La única prioridad **en 030** es el orden de compromiso… Prioridad por cliente, manual o por antigüedad de cotización es **FUTURE**» |

**La decisión estaba escrita en el código desde la Spec 030 y nadie la había leído como tal.**
`released_at` no es «una fecha disponible»: es el sello del acto que mete el pedido en esta cola,
puesto por la función que lo mete. Ordenar por él no es escoger un criterio entre varios, es ordenar
por el momento de entrada, que es lo único que el ¶14 puede significar sin añadir una dimensión de
prioridad que `D0-03` mantiene diferida.

## Matriz de decisión

| Criterio | `submitted_at ASC` | `released_at ASC` |
|---|---|---|
| Refleja el momento de entrada a la cola | **No**: entra al confirmar, no al liberar | **Sí**, por definición de `_a_released` |
| Interacción con retención de crédito | Conserva el puesto histórico | El pedido entra cuando queda elegible |
| Coherencia con `D0-03` §8 | Introduce antigüedad de pedido, vecina de la «antigüedad de cotización» diferida | Neutral: no añade dimensión |
| Justicia con el ya liberado | Penaliza al que lleva horas listo | Sirve por orden de disponibilidad real |
| Determinista | Sí | Sí |
| Disponible sobre el modelo actual | Sí | Sí |
| Impacto de migración | Ninguno | Ninguno |
| Auditable | `SALES_ORDER_TRANSITIONED` | `SALES_ORDER_TRANSITIONED` |

## El caso canónico

| | `submitted_at` | `released_at` |
|---|---|---|
| Pedido A | 08:00 | 14:00 |
| Pedido B | 10:00 | 10:05 |
| Orden resultante | A, luego B | **B, luego A** |

Con `submitted_at`, B espera detrás de A pese a llevar casi cuatro horas listo para prepararse, por
una retención de crédito que ni le concierne ni puede resolver.

## La decisión

> **R-D0-15-1 · Un pedido entra en el universo de picking solo al quedar `RELEASED`.**
> Es el estado que `FR-030-050` declara habilitante y el que `eligible_for_picking` ya publica.

> **R-D0-15-2 · El orden primario de la cola es `released_at ASC`.**
> Es el sello del acto de entrada, escrito en la misma transacción que hace firme la reserva.
> Una retención de crédito **no** conserva el puesto: el pedido entra en la fila cuando queda
> elegible, no cuando se emitió.

### Una consecuencia que hay que decir en voz alta

Revertir un pedido a `DRAFT` pone `released_at = None` y libera todas sus reservas
(`service.py:739-742`). Al reemitirlo se reserva desde cero y se libera de nuevo, con un
`released_at` nuevo. **Un pedido revertido pierde su puesto en la cola.** Es coherente —vuelve a
competir por la mercancía desde cero, igual que su reserva— pero no es evidente, y quien opere la
cola debe saberlo.

## El desempate

`released_at` es un `DateTime(timezone=True)`; dos liberaciones en la misma transacción o en el
mismo instante son posibles. Sin desempate total, el residuo lo decidiría el orden natural de
PostgreSQL, que no es un orden.

**Candidato descartado: `code`.** `CodeMixin` lo declara `String(64)` **sin restricción de
unicidad**, y el único índice único de `sales_orders` es `uq_sales_orders_quote`, sobre `quote_id`.
Un desempate por `code` no garantiza totalidad porque nada garantiza que dos pedidos no lo compartan.

> **R-D0-15-3 · El desempate es `id ASC`.**
> `UUIDMixin` lo declara clave primaria: único y estable por construcción, garantizado por la base de
> datos y no por una convención de generación. El orden `(released_at ASC, id ASC)` es **total y
> determinista**: mismos datos, misma cola, siempre. Queda prohibido depender del orden natural.

> **R-D0-15-4 · Prioridad por cliente, manual, por SLA y por ruta siguen siendo `FUTURE`.**
> `D0-03` §8 las difirió y `D0-15` no las activa. No se crea ningún campo de prioridad.

---

# OQ-031-2 · Si se planifica lo ubicado cuando es menor que lo reservado

## La pregunta

La Spec 022 hizo el put-away **manual** sobre una reserva **de almacén**. De ahí que un pedido pueda
estar íntegramente reservado y solo parcialmente ubicado: reserva 100, ubicado `L1`=40 y `L2`=20,
sin ubicar 40.

## La evidencia

| Fuente | Qué dice |
|---|---|
| `D0-03` §7 | «La cadena de preparación (031/032) trata el faltante como **incidencia**, nunca como ajuste silencioso» |
| `POL-D0-002` §3 | Todo o nada por pedido, a nivel de almacén |
| `R-D0-14-1` | La reserva es de almacén, no de ubicación |
| `R-D0-14-8` | El put-away es manual |

`D0-03` §7 ya prohibía la única salida verdaderamente mala —que el faltante desapareciese—, y
`POL-D0-002` §3 impide que un pedido se sirva a medias. Ninguna de las dos prohíbe **guardar el
trabajo de planificación ya hecho** mientras se espera el resto.

## Matriz de decisión

| Criterio | Esperar a tenerlo todo ubicado | DRAFT parcial + CONFIRMED completo |
|---|---|---|
| Faltante silencioso (`D0-03` §7) | Prohibido en ambas | Prohibido en ambas |
| Visibilidad operativa | El pedido se detiene sin decir cuánto falta | El plan dice exactamente cuánto falta y dónde |
| Preservación del trabajo | Se pierde en cada intento | Se conserva |
| Realidad del inventario ubicado | La ignora | La refleja |
| Seguridad para la Spec 032 | Trivial: no hay plan | Garantizada por la compuerta de confirmación |
| Auditabilidad | Nada que auditar | El remanente queda registrado |
| Complejidad de replanificación | Reempezar siempre | Completar lo que falta |

## La decisión

> **R-D0-15-5 · Una demanda de almacén puede repartir su asignación entre varias ubicaciones.**
> Ya derivado en el ciclo anterior: negarlo haría incumplible una reserva válida cuando ninguna
> ubicación contiene la cantidad entera.

> **R-D0-15-6 · La planificación parcial existe únicamente mientras el plan sea `DRAFT`.**

> **R-D0-15-7 · Un `DRAFT` parcial registra explícitamente la cantidad aún sin asignar.**
> El remanente **se representa en el propio plan**, no en una entidad nueva. `D0-15` no crea un motor
> de incidencias: no existe dueño de incidencia en ventas —`ReceiptIncident` es de compras— y el
> plan, que es quien conoce el faltante y quien queda bloqueado por él, es su representación
> natural. Si la Spec 032 necesitase escalarlo como incidencia física, será su contrato quien lo
> defina.

> **R-D0-15-8 · Un plan no pasa a `CONFIRMED` mientras quede cantidad base requerida sin asignar.**
> Invariante de completitud: `Σ(asignaciones activas.base_quantity) = cantidad base requerida por la
> reserva activa`. Si `remanente > 0`, el plan **no es ejecutable**.

> **R-D0-15-9 · La Spec 032 no puede consumir un plan incompleto.**
> Planificación parcial **no** es picking parcial. `D0-15` no autoriza preparación física parcial;
> eso es de la Spec 032 y solo si su contrato futuro lo permite.

## El caso canónico

| | |
|---|---|
| Reserva | 100 |
| Ubicado | `L1` 40 · `L2` 20 |
| Plan | `DRAFT` |
| Asignado | 60 |
| Remanente | **40, explícito** |
| Ejecutable por 032 | **No** |
| `CONFIRMED` | **Bloqueado** hasta asignado 100 / remanente 0 |

---

# OQ-031-3 · Ciclo de vida del plan

## La pregunta

Qué le pasa a un plan cuando la realidad cambia: cancelación, invalidación, replanificación, y qué
libera la asignación por ubicación.

## La evidencia

| Fuente | Qué dice |
|---|---|
| `PickList.status` | Nace `DRAFT`, `String(32)`, **sin `CHECK` en la migración** |
| `create_picklist` | Único escritor: pone `DRAFT`. **Nadie escribe `CONFIRMED` ni `CLOSED`** |
| `uom.py:357` | Lista de congelación de unidades, **no** una máquina de estados |
| `ORDER_TRANSITIONS` | `RELEASED → {PREPARING, SHIPPED, CANCELLED, DRAFT}` · `PREPARING → {SHIPPED, CANCELLED}` |
| `service.py:739-742` | Revertir a `DRAFT` libera todas las reservas y borra los dos sellos |
| `_liberar_reservas` | `release_if_active`: la reserva deja de estar `ACTIVE` |

## La decisión — cinco estados

> **R-D0-15-10 · El ciclo de vida del plan de picking tiene cinco estados:**
> `DRAFT`, `CONFIRMED`, `CLOSED`, `CANCELLED`, `INVALIDATED`.
> Camino feliz `DRAFT → CONFIRMED → CLOSED`. Salidas operativas: `DRAFT → CANCELLED`,
> `DRAFT → INVALIDATED`, `CONFIRMED → CANCELLED` (solo antes de efecto físico irreversible),
> `CONFIRMED → INVALIDATED`. `CLOSED`, `CANCELLED` e `INVALIDATED` son terminales.

| Estado | Significa | No significa |
|---|---|---|
| `DRAFT` | Plan en construcción; puede ser parcial y tener remanente > 0; ajustable | **No** es ejecutable por la 032 |
| `CONFIRMED` | Planificación **completa**, asignaciones válidas, ruta determinada, congelado para el traspaso | **No** significa recogido |
| `CLOSED` | La ejecución física de la 032 terminó. Terminal con éxito | **No** significa «terminó de planificar» ni «libérense las asignaciones» |
| `CANCELLED` | Cancelación operativa explícita antes de consumo físico irreversible | **No** libera la reserva comercial |
| `INVALIDATED` | Una precondición aguas arriba dejó de cumplirse | **No** crea acción comercial alguna |

> **R-D0-15-11 · `CANCELLED` e `INVALIDATED` no son el mismo estado.**
> El primero es un acto deliberado sobre el plan; el segundo, la consecuencia de perder una
> precondición. Confundirlos borraría de la auditoría quién decidió qué.

> **R-D0-15-12 · `CANCELLED` e `INVALIDATED` liberan las asignaciones operativas por ubicación y
> nada más.** No tocan la reserva comercial, que sigue el ciclo de la Spec 030, ni la existencia
> física.

> **R-D0-15-13 · La Spec 031 no libera nunca una reserva comercial.** Solo la 030 lo hace.

> **R-D0-15-14 · Ningún estado de la Spec 031 modifica el inventario físico.**
> `InventoryMovement` físico = 0, `qty_on_hand` = 0, ubicación física = 0, total de almacén = 0.
> Planificar no mueve mercancía.

> **R-D0-15-15 · Los disparadores de `INVALIDATED` son exactamente dos:** que el pedido salga del
> universo elegible —a `DRAFT` o `CANCELLED`— o que la reserva deje de estar `ACTIVE`.
> `PREPARING` **no** es un disparador: está **dentro** del universo elegible, es el estado que
> significa «tiene plan». Sin esta precisión, la regla «si el pedido deja `RELEASED`, invalídese el
> plan» invalidaría todo plan en el instante de crearse.

> **R-D0-15-16 · `CONFIRMED` puede cancelarse solo antes del primer efecto físico irreversible de la
> Spec 032.** Mientras la 032 no exista, la 031 debe tratar todo `CONFIRMED` como **no ejecutado
> físicamente**. El evento concreto lo definirá la 032; `D0-15` no lo inventa.

> **R-D0-15-17 · La Spec 032 solo consume un plan `CONFIRMED` que siga siendo válido al traspaso, y
> debe revalidarlo.** Nunca `DRAFT`, `CANCELLED`, `INVALIDATED` ni `CLOSED`.

## Dos consecuencias sobre el pedido que el modelo actual no soporta

Definir el ciclo de vida del plan obliga a decir cuándo el **pedido** cambia de estado, y ahí el
código vigente contradice las reglas que se acaban de aprobar.

`create_picklist` mueve hoy el pedido a `PREPARING` **al crear el plan**, es decir, en `DRAFT`.

> **R-D0-15-18 · Crear un plan `DRAFT` no saca al pedido de `RELEASED`. Solo `CONFIRMED` lo mueve a
> `PREPARING`.**
> Se deriva de `R-D0-15-6` y `R-D0-15-8`: un `DRAFT` puede ser parcial y no es ejecutable, de modo
> que el pedido sigue esperando a ser planificado y debe seguir en la cola. Con el comportamiento
> actual, un `DRAFT` parcial sacaría al pedido de la cola sin que ningún plan pudiera ejecutarse:
> desaparecería de la fila sin estar preparado, que es exactamente el faltante silencioso que
> `D0-03` §7 prohíbe.

> **R-D0-15-19 · Cancelar o invalidar un plan antes de efecto físico devuelve el pedido a
> `RELEASED`.**
> Un pedido con reservas vivas y sin plan tiene que poder volver a planificarse.

**`ORDER_TRANSITIONS` no tiene hoy la arista `PREPARING → RELEASED`**, y sus únicas salidas de
`PREPARING` son `SHIPPED` y `CANCELLED`. Cancelar un plan `CONFIRMED` dejaría el pedido varado en
`PREPARING`: con reserva viva, sin plan y sin camino de vuelta. `D0-15` **exige** la arista; no la
implementa. Es trabajo del ciclo de implementación de la Spec 031, junto con el cambio de
`create_picklist` que impone `R-D0-15-18`.

---

# Fronteras que este checkpoint confirma sin reabrir

> **R-D0-15-20 · La Spec 008 es la autoridad del orden físico de recorrido.**
> `physical_order_query()`, `FR-008-033`: zona → pasillo → rack → nivel → ubicación, con nulos
> primero y desempate por código. La Spec 031 **consume** esa secuencia. No se crea otro algoritmo:
> ni ruta más corta, ni TSP, ni vecino más próximo, ni distancia geométrica.

> **R-D0-15-21 · La Spec 031 no inventa política de selección de lote ni de serial.**
> El ¶30 fija la granularidad operativa en producto. No se introduce FIFO, FEFO, prioridad de lote
> ni de serial. Las dimensiones existentes se preservan cuando el inventario las tenga. Si en la
> implementación apareciera necesidad real de elegir entre lotes o seriales sin contrato que lo
> gobierne, **eso es una parada material** y no se resuelve aquí.

> **R-D0-15-22 · La cantidad asignable por ubicación es existencia vendible localizada menos las
> asignaciones operativas activas en esa ubicación.** Derivada de `R-D0-14-4` en el ciclo anterior;
> su liberación queda definida por `R-D0-15-12`.

---

## Lo que este checkpoint deja anotado y no resuelve

| Hallazgo | Dueño |
|---|---|
| La lista de congelación de unidades nombra para `sales_orders` cuatro estados de los que solo `CLOSED` existe | Spec 011 |
| `PickList.status` no tiene `CHECK` en la migración | Ciclo de implementación de la 031 |
| `create_picklist` no tiene ninguna prueba: su único llamador es el endpoint | Ciclo de implementación de la 031 |
