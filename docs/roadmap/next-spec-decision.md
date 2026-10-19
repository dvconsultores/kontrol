# DECISIÓN — SIGUIENTE SPEC

## `NEXT SPEC = 029 — COTIZACIÓN Y PEDIDO COMERCIAL`

## El hecho que decide

`resolve_price` existe, está probada, devuelve el precio **y la versión que lo
produjo**, y **nadie la llama**.

Medido hoy:

```
sales_quote_lines   → unit_price, discount        · 0 columnas de origen
sales_order_lines   → unit_price, discount        · 0 columnas de origen
sales_invoice_lines → unit_price                  · 0 columnas de origen
```

La Spec 012 se construyó para cerrar una deuda concreta: que el precio de una
cotización no pudiera reconstruirse. La cerró **como capacidad** y la deuda
sigue abierta **como hecho**, porque cerrarla exige que el consumidor escriba el
origen en la línea.

Ese consumidor es 029.

## ¿Por qué ahora?

Porque el daño se acumula y es irreversible. Cada cotización y cada pedido que
se emiten hoy llevan un precio que alguien tecleó, sin lista, sin versión y sin
vigencia. `P23` lo dice sin adornos: **no se pierde el dato, es que nunca se
captura**. Ninguna migración posterior puede repararlo.

Las demás candidatas esperan algo. 029 no espera nada.

## Dependencias satisfechas

| Capacidad | Proveedora | Comprobación |
|---|---|---|
| Tercero de empresa | 009 | `parties.company_id` obligatoria con FK real |
| Artículo de empresa | 010 | `catalog_items.company_id` obligatoria |
| Unidad y presentación | 011 | `COMPLETE`; factor congelado en línea |
| Resolución de precio con versión | 012 | `COMPLETE`; `resolve_price` probada |
| Validación de descuento | 012 | `validar_descuento`, con señal a la 045 |
| Motor de aprobaciones | 045 | `COMPLETE` |
| Disponibilidad de inventario | 023 | `inventory_balances.qty_available` |
| Alcance multiempresa | ARCH-MC-001 | `COMPLETE / GLOBALLY CONVERGED` |

**Bloqueos restantes: ninguno.**

## Qué desbloquea

**030 Crédito y reserva** queda a la espera de una sola cosa: la decisión `D0-03`
sobre el momento de la reserva. Hoy espera dos.

Y **034 Facturación** hereda el snapshot comercial: una factura que nace de un
pedido con origen de precio puede reconstruirse; una que nace de un número
tecleado, no.

## Qué riesgo reduce

El único riesgo de esta lista que **empeora con el tiempo**. Los bloqueos de
039–043 son legales y no se agravan por esperar. El de 030 es una decisión, y
tampoco. El de 022 es una capacidad ausente, y la mercancía sigue entrando al
almacén sin sitio — eso sí se acumula, pero es corregible: un inventario se
recuenta y se coloca.

Un precio sin origen no se recuenta.

## Por qué antes que la segunda candidata

**020 — Incidencias de recepción** tiene también todas sus dependencias
satisfechas y es la entrada de la cadena que lleva a 022, que es el nodo de
mayor desbloqueo del sistema.

Se elige 029 por tres razones, en este orden:

1. **El daño de 029 es irreversible y el de la cadena de 020 no lo es.** Un
   almacén mal colocado se recuenta; un precio sin origen no se reconstruye.
2. **029 da consumidor a una capacidad recién construida.** Dejar 012 sin
   consumidor durante otro ciclo es dejar terminada una autoridad que nadie
   ejerce, y esa es la forma en que una capacidad se oxida antes de usarse.
3. **029 cuesta menos.** Sus tablas existen; hay que darles origen. La cadena
   020 → 021 → 022 son tres Specs, dos de ellas desde cero.

## Lo que esta decisión NO autoriza

No inicia la implementación de 029. El siguiente ciclo deberá ejecutar de nuevo
la metodología completa —`specify`, `clarify`, `plan`, gate, `checklist`,
`tasks`, `analyze`, trazabilidad, autorización, `implement`, evidencia,
`converge`— y necesita autorización expresa del usuario.

## Segunda candidata, como referencia

`RUNNER-UP = 020 — INCIDENCIAS DE RECEPCIÓN`

Entrada de la cadena `020 → 021 → 022` que desbloquea 031 y 032, y que hace que
la inversión de la Spec 008 empiece a rendir: hoy el almacén tiene estanterías
y toda la mercancía está «en el almacén», en ningún sitio concreto.

**No queda autorizada.**

## Actualización 2026-09-02

029 quedó `COMPLETE / CONVERGED` y `D0-03` cerró con `RESERVATION TRIGGER = ORDER_CONFIRMATION`.
030 pasa a `READY_FOR_IMPLEMENTATION` con contrato completo; su implementación requiere autorización
expresa y no forma parte del checkpoint que la desbloqueó.

## Actualización 2026-09-02 (tarde)

030 quedó `COMPLETE / CONVERGED` en su propio ciclo autorizado. Ya no hay Spec en
`READY_FOR_IMPLEMENTATION`: la siguiente se selecciona en el próximo checkpoint maestro; la cadena
020 → 021 → 022 es la que desbloquea 031 y 032, que ahora reciben pedidos `RELEASED` con reservas por
línea.

---

## Checkpoint de la cadena operativa — 2026-09-03

`NEXT SPEC = 019 — RECEPCIÓN FÍSICA` · `RUNNER-UP = 020 — INCIDENCIAS DE RECEPCIÓN`

Con 030 cerrada, la ruta crítica del producto deja de estar en lo comercial y pasa a la cadena de
entrada: todo lo que vende está listo y espera a que el almacén sepa dónde está la mercancía.

019 se elige porque es la **primera de esa ruta**, tiene **cero bloqueos activos** —sus siete
proveedores están satisfechos— y está **incompleta de forma medible**: tres de las diez etapas
documentadas. Lo decisivo no es el hueco sino su naturaleza: presentación y unidad de lo recibido,
bultos y detalle del daño solo se conocen mientras el camión está en el muelle. Es `P23` en su forma
literal, y es el mismo patrón que la Spec 029 cerró para el precio y la 030 para la reserva: las
columnas de unidad llevan desde la Spec 011 esperando en `GoodsReceiptLine` a que alguien las
escriba.

Hay además un riesgo de corrección latente: `accept_receipt` llama a `record_movement` sin
presentación, así que la cantidad base del asiento es la tecleada. Hoy no hace daño porque la API no
admite presentaciones; el día que se reciba en cajas, el ledger anotará cajas como si fueran
unidades.

020 también tiene cero bloqueos y un hueco mayor —no existe—, pero está aguas abajo. Construirla
antes sería levantar el registro de incidencias sobre una recepción que todavía no sabe describir lo
que llegó.

Detalle completo en `operational-chain-checkpoint.md`. Implementación **no iniciada**: requiere su
propio ciclo con autorización expresa.

---

## Tras la Spec 019 — 2026-09-03

`SPEC 019 — COMPLETE / CONVERGED`. La única Spec en `READY_FOR_IMPLEMENTATION` pasa a ser la **020,
Incidencias de recepción**, que ya lo estaba y ahora cuelga de una recepción capaz de describir lo
que llegó: presentación, bultos, estado físico, daño observado y sobrante.

Detrás siguen la 021 —esperando la capacidad de excepción de la 020 y que el motor de saldos sepa
escribir estados no vendibles (Spec 023)— y la 022, y tras ellas la 031 y la 032.

Implementación de la 020 **no iniciada**: requiere su propio ciclo con autorización expresa.

---

## Tras la Spec 020 — 2026-09-03

`SPEC 020 — COMPLETE / CONVERGED`. Con ella, **once de las doce etapas** del proceso de recepción
física tienen implementación: ocho de la 019, tres de la 020. La duodécima —clasificación y
ubicación— es de la 022.

`READY_FOR_IMPLEMENTATION` queda en **cero**. Ninguna Spec está lista para abrir ciclo sin resolver
antes una pregunta, y por eso este checkpoint **no selecciona una siguiente**: la señala y nombra lo
que falta para poder elegirla.

**La candidata es la 021, Confirmación de inventario**, y su situación cambió: tenía dos bloqueos y
ahora tiene uno.

| Bloqueo | Estado |
|---|---|
| Capacidad de excepción (020) | **Satisfecho** el 2026-09-03: la incidencia se registra, se escala y se resuelve |
| El motor de saldos escribe únicamente `DISPONIBLE` (023) | **Vigente** |

El bloqueo que queda no es una Spec por construir sino una capacidad declarada y no ejercida: el
`ADR-D0-010` enumera quince estados de mercancía y `record_movement` escribe uno solo. Confirmar
inventario sin poder decir «esto entró en cuarentena» sería confirmar de mentira.

**La decisión previa, que no me corresponde tomar aquí:** si esa capacidad se abre dentro de la 023,
que es su dueña, o si la 021 se define explícitamente sin cuarentena. Son dos alcances distintos y
producen dos Specs distintas. Resolverlo antes de abrir el ciclo evita que la 021 termine
corrigiendo un motor ajeno, que es exactamente lo que la 019 tuvo que hacer y solo porque el defecto
era suyo por la línea que lo causaba.

Implementación **no iniciada**. Requiere su propio ciclo con autorización expresa.

---

## Tras el ciclo dirigido de la Spec 023 — 2026-09-03

`SPEC 023 MULTI-STATE BALANCE CAPABILITY — BLOCKED BY MATERIAL DECISION` · `SPEC 021 — BLOCKED`.

El checkpoint anterior dejó a la 021 con un bloqueo que parecía de ingeniería: «el motor solo escribe
`DISPONIBLE`». La auditoría lo desmiente en las dos direcciones.

**Está mejor de lo que se creía.** El estado ya es dimensión de la clave única del saldo, el
disponible ya filtra por él, y la reserva de la Spec 030 ya opera solo sobre `DISPONIBLE`. La prueba
que temíamos tener que construir —que cien unidades en cuarentena no se ofrezcan a un cliente— ya
pasa hoy, porque la suma nunca cruza estados. La vendibilidad y la reservabilidad están cerradas por
`R-D0-10-3`, `R-D0-03-5` y `POL-D0-002` §7 sin preguntar nada a nadie.

**Y está peor de lo que se creía.** Lo que falta no es una columna: `R-D0-10-7` obliga al motor a
rechazar toda transición no declarada, y el ADR **no declara ninguna**. Sin tabla no hay
reclasificación legal; sin reclasificación, la 021 no puede liberar formalmente lo recibido. Y nadie
ha decidido qué pasa con la mercancía ya comprometida a un cliente cuando cambia de estado: hacerlo
sin regla produce disponible negativo por una vía que `POL-D0-002` §6 prohíbe.

Ninguna de las dos se deriva del código. Son decisiones de producto, y este ciclo no las toma.

**Ninguna Spec queda seleccionada.** No por falta de candidatas, sino porque la ruta crítica pasa por
una decisión, no por una implementación. Las opciones están planteadas en
`specs/003-inventario-logistica/spec023-multistate-material-decision.md`, con lo que cada una implica
y hacia dónde apunta la autoridad ya escrita.

Si se prefiere avanzar en paralelo mientras se decide, hay trabajo desbloqueado fuera de esta cadena:
**018 Importaciones** —cero bloqueos, cero tablas, y libera la 026— y **048 Integraciones**, que
desbloquea la tasa BCV de la 013 y las notificaciones de la 047. Ninguna toca el motor de inventario,
así que ninguna prejuzga las dos decisiones pendientes.

Implementación de la capacidad multiestado **no iniciada**: `/speckit.implement` no se ejecutó,
conforme a la autorización condicional del ciclo.

---

## Tras el checkpoint D0-10 — 2026-09-03

`D0-10 — CLOSED` · `ADR-D0-010` **v2**. Las dos decisiones que el ciclo dirigido de la Spec 023 dejó
abiertas se cerraron el mismo día, y la que parecía más difícil se cerró de la forma más limpia.

**El grafo de transiciones** se declaró con nueve aristas, cada una con su evidencia: `R-D0-10-4`
para la liberación formal, `R-D0-10-6` para la salida de `BLOQUEADO`, `FR-003-062` para la diferencia
en transferencia, y el flujo objetivo del checkpoint operativo para la confirmación con rechazo y la
resolución en cuarentena. Todo lo demás queda `DENIED` hasta que su Spec lo active, que es el régimen
que `R-D0-10-7` ya imponía sin declarar contra qué.

**El conflicto con reservas** se cerró por una vía que no se esperaba. Al construir la matriz apareció
que **ninguna de las nueve transiciones activas sale de `DISPONIBLE`**, y las reservas viven solo en
filas `DISPONIBLE`. El conflicto no es alcanzable: la cadena que la 021 necesita va hacia lo vendible,
nunca al revés. Queda la invariante escrita (`R-D0-10-9`), dos de las cuatro salidas rechazadas por
autoridad, y `R-D0-10-10` fijando que quien active la primera arista con origen `DISPONIBLE` —la
Spec 025, previsiblemente— elija entre las dos restantes en su propio ciclo.

**La siguiente es la Spec 023**, retomando su ciclo dirigido: estado como parámetro, validación contra
la matriz, estado en el ledger, reconstrucción sin colapso, los diez call sites y la corrección de
`confirm_transfer_receipt`. Nada de eso requiere una decisión más.

La 021 **no** queda lista y no debe marcarse como tal: cerrar una decisión no implementa una
capacidad. Su estado pasa de `BLOCKED_BY_BUSINESS_DECISION` a `BLOCKED_BY_DEPENDENCY`, que es un
bloqueo de código y ya no de negocio.

---

## Tras la capacidad multiestado de la Spec 023 — 2026-09-04

`SPEC023 MULTI-STATE CAPABILITY — COMPLETE / CONVERGED`. La cadena de entrada queda **sin un solo
bloqueo**: 019 y 020 cerradas y selladas, `D0-10` decidido, y el motor capaz de escribir, validar y
reconstruir estados de mercancía.

`NEXT SPEC = 021 — CONFIRMACIÓN DE INVENTARIO`

Es la única en `READY_FOR_IMPLEMENTATION` y tiene todo lo que pedía: recepción física que describe lo
que llegó (019), resultado estructurado de incidencias (020), y ahora la autoridad de inventario con
estados escribibles (023). Sus cuatro transiciones están declaradas con evidencia y probadas contra
el motor.

Detrás, la 022 —que cierra la duodécima y última etapa del proceso de recepción— y luego 031 y 032.
Implementación de la 021 **no iniciada**: requiere su propio ciclo con autorización expresa.


---

## Tras la Spec 021 — 2026-09-04

`SPEC 021 — COMPLETE / CONVERGED`. **Aceptar una recepción ya no pone la mercancía a la venta**, que
era lo que `R-D0-10-4` exigía desde agosto y que el `ADR-D0-010` había reservado explícitamente para
esta Spec.

Con ella, la deuda del proceso de entrada pasa de rota casi entera a rota en un solo punto: la
recepción física, las incidencias, el motor multiestado y la confirmación están cerrados; falta
decir **dónde** quedó la mercancía.

`NEXT SPEC = 022 — PUT-AWAY Y UBICACIÓN`

No le falta nada. La Spec 008 entrega zonas, pasillos, racks, niveles y ubicaciones con secuencia y
capacidad declarada, y hasta hoy no las usaba nadie. La 021 entrega el estado de origen inequívoco
que pedía: producto, almacén, cantidad base, estado `DISPONIBLE`, lote y serial si los hay, y
`location_id` nula. Es la duodécima y última etapa del proceso de recepción, y cierra la cadena de
entrada entera.

Detrás quedan 031 y 032, que esperan existencia ubicada y que la 022 desbloquea.

Implementación de la 022 **no iniciada**: requiere su propio ciclo con autorización expresa.


---

## Tras la auditoría de la Spec 022 — 2026-09-04

`SPEC 022 — BLOCKED BY MATERIAL DECISION`. Por segunda vez en esta cadena, el bloqueo real no era
código.

La estructura estaba lista de verdad: la Spec 008 entrega zonas, pasillos, racks, niveles y
ubicaciones con su cadena completa, y la Spec 021 entrega el origen inequívoco. Lo que falta son tres
decisiones, y una de ellas no es evitable ni marginal.

**La bloqueante es la interacción con las reservas.** `lock_balance` filtra `location_id IS NULL` en
duro y `get_available` lee esa única fila. La Spec 021 deja la mercancía confirmada exactamente ahí.
En cuanto el put-away la mueva a una ubicación real, la Spec 030 dejará de verla: bloqueará la fila
nula, calculará disponible negativo si había reservas, y la mercancía ubicada será invendible.
`POL-D0-002` §7 dice que la reserva no se dimensiona por ubicación, lo que apunta a agregar el
disponible por almacén; pero dónde vive entonces el contador `qty_reserved` no lo dice ningún
artefacto, y cambiar cómo la 030 calcula el disponible es tocar el contrato de `D0-03`.

Las otras dos: la capacidad de una ubicación tiene columnas —unidades, peso y su unidad— pero
ninguna regla que diga si bloquea o solo avisa; y la clasificación que el proceso pide exige
familia, tamaño, peso, rotación y volumen, **cinco atributos que el maestro de productos no tiene**,
sobre zonas que el propio documento marca como «preliminares que conviene validar».

**Ninguna Spec queda seleccionada.** La ruta crítica vuelve a pasar por una decisión. Las opciones
están en `specs/003-inventario-logistica/spec022-putaway-cycle.md`.

Si se prefiere avanzar en paralelo mientras se decide, sigue habiendo trabajo desbloqueado fuera de
esta cadena: **018 Importaciones** —cero bloqueos, y libera la 026— y **048 Integraciones**, que
desbloquea la tasa BCV de la 013 y las notificaciones de la 047. Ninguna toca inventario, así que
ninguna prejuzga las tres decisiones pendientes.

---

## Tras el checkpoint D0-14 — 2026-09-04

`D0-14 — CLOSED`. Las tres decisiones que bloqueaban la Spec 022 se cerraron el mismo día, y ninguna
requería decidir nada nuevo.

**La de las reservas ya estaba decidida.** `POL-D0-002` §7 dice desde septiembre que la reserva no se
dimensiona por ubicación; de ahí se sigue, sin añadir nada, que mover mercancía entre ubicaciones no
puede tocar el compromiso comercial. Lo que había no era una laguna de negocio sino una
implementación que leía el disponible de una sola fila porque la ubicación siempre había sido nula.
La política gana ahora esa consecuencia escrita.

**Las otras dos se cierran por lo contrario:** porque el dato para decidir otra cosa no existe. La
capacidad tiene columnas y ninguna regla, y su unidad es texto libre sin vínculo al catálogo; la
clasificación pide cinco atributos que el maestro no tiene, sobre zonas que el propio documento marca
como preliminares. Capacidad informativa y ubicación manual son las únicas opciones que no inventan.

`NEXT SPEC = 022 — PUT-AWAY Y UBICACIÓN` (reanudación del mismo ciclo)

Hereda cuatro trabajos de ingeniería y ninguna decisión: reconciliar `lock_balance` y `get_available`
para que el disponible sea del almacén, elegir la representación del contador reservado entre las
tres compatibles, añadir la procedencia de ubicación al movimiento —forma ya resuelta por precedente
en la `0046`— y el put-away manual con filtro de candidatas.

`SPEC 031` sigue bloqueada hasta que la 022 implemente y converja. Cerrar una decisión no implementa
una capacidad.


---

## Tras la Spec 022 — 2026-09-04

`SPEC 022 — COMPLETE / CONVERGED`. **La cadena de entrada queda cerrada.** La mercancía se recibe, su
excepción se trata, se cuenta, se confirma y ahora se coloca. De las 135 etapas de proceso
documentadas, 68 están cubiertas (50 %); en el tramo de entrada, 40 de 50 (80 %), y las diez que
faltan son de importación, que es otro proceso.

Lo que este ciclo tuvo que resolver no era construir el put-away: era que ubicar la mercancía la
habría vuelto invendible. La reserva vivía atada a la fila de ubicación nula por un artefacto de
implementación, no por una regla. `D0-14` cerró la semántica y este ciclo la ejecutó: el disponible
del almacén se suma sobre todas las ubicaciones y el compromiso se queda donde estaba.

`NEXT SPEC = 031 — COLA Y RUTA DE PICKING`

Recibe lo que pedía: existencia con ubicación física real, cantidad base, estado de mercancía y
lote/serial. Y recibe también, explícitamente, lo que **no** está hecho: ninguna reserva está
asignada a ninguna ubicación. El compromiso es del almacén, y decidir de qué ubicación se extrae para
satisfacerlo es exactamente el trabajo de la 031.

Detrás quedan la 032 —preparación y consolidación— y la 033. Implementación de la 031 **no iniciada**:
requiere su propio ciclo con autorización expresa.


---

## Tras el sello de evidencia de la Spec 022 — 2026-09-04

`SPEC 022 — COMPLETE / CONVERGED / EVIDENCE SEALED`. La e2e propia del put-away, que era la deuda
que quedaba, se ejecutó: **27 de 27 en Chromium, Firefox y WebKit**, sin saltos, y con cada acción de
interfaz comprobada después contra el dominio.

La frase que bloqueó esta Spec un ciclo entero —«ubicar la mercancía la volvería invendible»— es hoy
una prueba que pasa en los tres navegadores.

Con ella, **la cadena de entrada está completa**: de la llegada del camión a la ubicación física. La
deuda funcional de ese tramo pasa del 58 % al 80 % de cobertura, y lo único que queda es la
importación, que es otra cadena.

`NEXT SPEC = 031 — COLA Y RUTA DE PICKING`

Es la única en `READY_FOR_IMPLEMENTATION` y ya tiene lo que pedía: inventario **físicamente
ubicado**, con empresa, almacén, ubicación real, producto, estado, lote, serial y cantidad base, y el
traslado reconstruible desde el ledger. Sigue siendo suya la asignación de demanda a ubicación: el
put-away nunca ató una reserva a una ubicación, y hay prueba de ello.

Detrás, la 032, que espera a la 031.

Implementación de la 031 **no iniciada**: requiere su propio ciclo con autorización expresa.


---

## Tras el ciclo de auditoría de la Spec 031 — 2026-09-05

`SPEC 031 — BLOCKED BY MATERIAL DECISION`. El ciclo se detiene antes de `implement` con **cero código
de producto**. El estado `READY_FOR_IMPLEMENTATION` que tenía no autorizaba empezar por ahí, y hacer
la auditoría primero fue lo que evitó construir sobre tres huecos.

Lo que la 031 pedía y **ya estaba hecho**: el recorrido. El ¶30 del DOCX —«Pedido → Zona → Pasillo →
Rack → Ubicación → Producto»— es exactamente `physical_order_query()` de la Spec 008, con orden total
y desempate por código. No había algoritmo que inventar; el pendiente «Algoritmo de ruta» del
roadmap ya tenía respuesta escrita en otra Spec.

Lo que falta no es código:

| | Pregunta | Estado |
|---|---|---|
| **OQ-031-1** | Con qué criterio se ordena la cola | Acotada por `D0-03` §8 a una marca temporal; queda elegir `submitted_at` o `released_at` |
| **OQ-031-2** | Si se planifica lo ubicado cuando es menor que lo reservado | `D0-03` §7 prohíbe la salida silenciosa; queda si el plan avanza o espera |
| **OQ-031-3** | Cancelación, invalidación y replanificación del plan | Sin autoridad; hay un ciclo `DRAFT → CONFIRMED → CLOSED` vivo en código y sin documentar |

Registradas como **`D0-15`** en el registro de decisiones. La solicitud completa, con la evidencia de
cada una, está en `specs/005-ventas-cuentas-por-cobrar/spec031-picking-cycle.md` §5.

`NEXT = D0-15 — CHECKPOINT DE DECISIÓN DE LA COLA DE PICKING`

Documental, sin código, como fueron `D0-10` y `D0-14`. Con las tres respondidas, la 031 es
implementable en un solo ciclo: recorrido, aritmética localizada y división entre ubicaciones ya
están construidos o derivados.

Detrás sigue la 032, que espera a la 031.

---

## Tras el checkpoint D0-15 — 2026-09-05

`D0-15 — CLOSED`. Ciclo documental completo, **cero código de producto**. Las tres preguntas que
bloqueaban la Spec 031 quedan cerradas con 22 reglas `R-D0-15-*` en
`docs/governance/d0-foundational-decisions/d0-15-checkpoint/`.

La primera se cerró con evidencia que el ciclo anterior tenía delante y no leyó como autoridad: el
docstring de `_a_released` dice «el pedido entra en la cola de 031» en la misma función que escribe
`released_at`. La cola se ordena por el sello del acto que mete el pedido en ella, con desempate por
`id` —clave primaria— porque `code` no tiene restricción de unicidad y no haría total el orden.

La segunda permite guardar el trabajo de planificación sin permitir jamás ejecutarlo a medias:
parcial en `DRAFT` con el remanente publicado, confirmación solo al 100 %.

La tercera formaliza cinco estados y, al hacerlo, destapó dos contratos que el modelo de la Spec 030
no cumple: crear un plan mueve hoy el pedido a `PREPARING` demasiado pronto, y no existe camino de
vuelta de `PREPARING` a `RELEASED`, de modo que cancelar un plan confirmado vararía el pedido.
Ambas quedan declaradas y asignadas al ciclo de implementación.

`NEXT SPEC = 031 — COLA Y RUTA DE PICKING`

`READY TO RESUME IMPLEMENTATION`. Implementación **no iniciada**: requiere su propio ciclo con
autorización expresa, empezando de nuevo en `/speckit.specify`. Primer precheck de ese ciclo:
reconstruir PostgreSQL, reconstruir ClamAV, validar migraciones y **validar el número de saltos
esperado** antes de medir nada.

Detrás sigue la 032, bloqueada hasta que la 031 converja.

---

## Tras la implementación de la Spec 031 — 2026-09-05

`SPEC 031 — COMPLETE / CONVERGED`. Backend 1063/1063 con 8 saltos —los esperados, todos de S3—,
frontend 291/291, e2e propia 24/24 en los tres navegadores y la cadena operativa entera 84/84.
Migración `0049` con ida y vuelta sobre base limpia.

La cola se ordena por `released_at` con desempate por `id`; la asignación es por ubicación y descuenta
lo que otros planes vivos ya tomaron; el recorrido lo da la Spec 008 y aquí solo se numera; y el plan
tiene cinco estados con `CHECK` en la base. Planificar no mueve una sola unidad, y hay prueba de ello
midiendo existencia, reservado y número de movimientos antes y después de cada transición.

Los dos deltas dirigidos que `D0-15` había declarado están hechos: crear un borrador ya no saca el
pedido de la cola, y existe `PREPARING → RELEASED` para que cancelar un plan confirmado no lo vare.
La guardia de la Spec 030 se actualizó con el motivo, no se relajó.

De paso, tres hallazgos que no eran de esta Spec: `pgserver` no trae `btree_gist` y sin él toda la
suite falla en el fixture —ahora lo compila `qa/pg-provision.sh`—, y dos e2e de las Specs 019 y 020
leían el listado de saldos sin filtro cuando ese listado pagina.

`NEXT SPEC = 032 — PICKING Y CONSOLIDACIÓN`

Pasa de `BLOCKED_BY_DEPENDENCY` a `NOT_STARTED`: ya no la bloquea nada. Recibe un plan `CONFIRMED`
válido y su contrato de entrada está escrito en `spec032-handoff-after-spec031.md`, incluido lo que
deberá definir ella misma —el primer efecto físico irreversible— y lo que no hereda.

Implementación de la 032 **no iniciada**: requiere su propio ciclo con autorización expresa.

---

## Tras la implementación de la Spec 032 — 2026-09-05

`SPEC 032 — COMPLETE / CONVERGED`. Backend 1098/1098 con los 8 saltos esperados, frontend 291/291,
e2e propia 21/21 en los tres navegadores y la cadena operativa entera 105/105. Migración `0050` con
ida y vuelta sobre base limpia.

La pregunta que parecía material —qué queda del disponible cuando la mercancía reservada sale de
`DISPONIBLE` al recogerse— tenía respuesta, y no estaba en la política de reservas sino en el
vocabulario que fijó `D0-03` §0: **reservado son las unidades «comprometidas y aún no extraídas»**.
Extraer es dejar de estarlo. Sin eso el disponible habría caído de 70 a 40 y ventas habría dejado de
poder vender 30 unidades que sí tiene; y con dos pedidos, despachar el primero habría borrado del
contador el compromiso del segundo.

Los cinco motivos de diferencia tampoco se inventaron: están en los ¶48-52 del proceso fuente, y el
¶53 exige que el pedido no se modifique sin dejar evidencia. Lo recogido se guarda aparte de lo
planificado precisamente para que la diferencia exista.

Cinco deltas dirigidos, sobre las Specs 023, 030 y 031, todos con autoridad previa: las dos aristas
de custodia que la matriz de `D0-10` había declarado «Specs no construidas», el contador de
reservado, `reclassify` respetando la ubicación, `PREPARING → PREPARED` de `ADR-D0-012`, y el
bloqueo de la cancelación una vez empezada la preparación. Las cinco guardias que invalidaron se
actualizaron con su razón escrita; tres cambiaron exactamente como `R-D0-10-10` había previsto.

Con esto la cadena de salida pasa del 38 % al 71 % de cobertura.

`NEXT SPEC = 033 — CONFIRMACIÓN INDEPENDIENTE DEL PEDIDO`

Recibe un pedido `PREPARED` con la mercancía concentrada en el Área de Confirmación y un contrato
que entrega **hechos, no un veredicto**: lo requerido, lo preparado, la diferencia y su motivo. La
032 no compara ni aprueba a propósito: el ¶61 dice que ese control es **independiente**, y si lo
hiciera el preparador dejaría de serlo.

Queda una pregunta abierta que no la bloquea: qué hacer con un pedido cuya preparación empezó y hay
que deshacer. Necesita una arista de devolución `PICKING → DISPONIBLE` con dueña y evidencia.

Implementación de la 033 **no iniciada**: requiere su propio ciclo con autorización expresa.

---

## Tras la implementación de la Spec 033 — 2026-09-06

`SPEC 033 — COMPLETE / CONVERGED`. Backend 1136/1136 con los 8 saltos esperados, frontend 293/293,
e2e propia 21/21 en los tres navegadores y la cadena operativa completa 129/129, incluido el
recorrido del menú. Migración `0051` con ida y vuelta sobre base limpia.

Este es el primer ciclo del tramo en que **no hubo que buscar la autoridad**: `ADR-D0-012` decide las
seis preguntas que el prompt marcaba como materiales, y el proceso fuente enumera literalmente las
cinco dimensiones que el control verifica —producto, SKU, cantidad, presentación y condición—. Lo
único que había que hacer era leerlo antes de escribir.

La frase que gobierna el diseño es de `R-D0-12-2`: la comparación es contra el pedido, **no contra la
lista de picking**, porque comparar la preparación consigo misma no es un control. De ahí sale que lo
requerido se lea de la línea del pedido y no de la reserva —que un picking corto ya encogió— y que un
pedido incompleto no pase el control aunque el verificador cuente exactamente lo que hay preparado.

La e2e descubrió lo que ninguna prueba unitaria podía: el usuario que monta el escenario es quien
recoge y consolida, y el backend le negó la confirmación. Hubo que crear un segundo usuario. Que la
primera versión de la e2e no funcionara es la evidencia de que el control funciona.

Con esto la cadena de salida pasa del 71 % al 89 % de cobertura.

`NEXT SPEC = 034 — LIBERACIÓN Y FACTURACIÓN`

Recibe una compuerta única: `GET /sales/confirmacion/{order_id}/facturable` responde si el pedido
tiene confirmación independiente válida, y comprueba las dos cosas —el registro y el estado—, porque
un control que se satisface moviendo un estado a mano no es un control. `READY_FOR_BILLING` no se ha
añadido: lo declara `ADR-D0-012` y lo escribirá su dueña, igual que la 032 dejó `CONFIRMED` para la
033 y la 031 dejó `PREPARED` para la 032.

Sigue abierta, sin bloquear a la 034, la deuda de la Spec 032: un pedido rechazado queda en
`PREPARING` y su plan no tiene camino de reapertura ni existe la arista `PICKING → DISPONIBLE`.

Implementación de la 034 **no iniciada**: requiere su propio ciclo con autorización expresa.

---

## Tras la implementación de la Spec 034 — 2026-09-06

`SPEC 034 — COMPLETE / CONVERGED`. Backend 1169/1169 con los 8 saltos esperados, frontend 295/295,
e2e propia 24/24 en los tres navegadores y la cadena operativa completa 153/153. Migración `0052`
con ida y vuelta sobre base limpia.

El ciclo enumeraba catorce preguntas materiales y ninguna hubo que decidirla, pero por primera vez
la autoridad venía de **tres sitios que se complementan**: el proceso fuente dice qué pasa —el ¶95
genera la factura y el ¶97 emite el documento fiscal, que son dos actos distintos—, `ADR-D0-012` dice
en qué estados, y el backlog maestro fija los criterios de aceptación con una literalidad que no
dejaba margen: `B-007` y `B-060`.

Lo que no había que construir era casi todo lo difícil. El motor fiscal ya tenía reglas versionadas,
series con reserva atómica del correlativo, lotes de números de control y una emisión idempotente; y
la cuenta por cobrar ya nace al emitir. **Lo que faltaba era el gobierno**: antes de este ciclo
cualquiera podía crear una factura para un cliente sin pedido, sin confirmación y dos veces.

Dos mutaciones lo comprobaron. Quitar la comprobación de la confirmación hace fallar la prueba del
pedido puesto en `CONFIRMED` a mano —prueba que hubo que escribir porque la primera guardia miraba el
estado y no el registro, y la mutación lo destapó—. Quitar la comprobación de doble facturación del
servicio hace que **la base** rechace la segunda factura.

Con esto la cadena de salida pasa del 89 % al 96 %: solo queda el despacho final.

`NEXT SPEC = 035 — DESPACHO, TRANSPORTE Y REGULACIÓN`

Recibe las tres compuertas que el ¶103 exige verificar —«Pedido preparado + Pedido confirmado +
Factura emitida»— cada una con su autoridad consultable. `DISPATCHED` no se ha añadido: lo declara
`ADR-D0-012` y lo escribirá su dueña, como cada Spec de este tramo dejó el suyo para la siguiente.
Y la arista `CONFIRMED → SHIPPED`, que viene de antes de este tramo, sigue abierta: cerrarla es su
compuerta, no la de esta Spec.

Queda dicho en voz alta que **la emisión no está legalmente homologada**: `D0-07` mantiene las Specs
039-043 bloqueadas por validación normativa, y este ciclo construyó contra el motor existente sin
afirmar lo contrario.

Implementación de la 035 **no iniciada**: requiere su propio ciclo con autorización expresa.

---

## Tras la implementación de la Spec 035 — 2026-09-07

`SPEC 035 — COMPLETE / CONVERGED`. Con esto la cadena de salida queda cerrada de
punta a punta —cola, picking, consolidación, confirmación, facturación y
despacho— y DF-11 pasa a 6/6: la deuda de salida de mercancía llega al 100 %.

El ciclo enumeró nueve preguntas materiales y ninguna hubo que decidirla,
pero esta vez la autoridad no estaba escondida en una decisión previa: estaba
**escrita en el propio código y sin invocar**. `regulatory.evaluate_shipment`
resolvía los perfiles aplicables por producto y operación, comprobaba los
documentos requeridos y devolvía `BLOCKED` con sus motivos. Funcionaba. Nadie la
llamaba desde el despacho, y `validate_shipment` —cuyo docstring prometía
bloquear— aprobaba siempre.

Tres defectos salieron de conectar la compuerta, y los tres solo eran visibles
con la cadena entera montada:

1. **La compuerta no comprobaba nada.** Ahora exige las tres del ¶103 —preparado,
   confirmado, factura **emitida**— y la cuarta regulatoria, y las comprueba por
   registro, no por estado: la Spec 033 ya había demostrado que un estado se pone
   a mano.
2. **La salida descontaba la cantidad comercial de un estado equivocado.** Dos
   cajas de doce sacaban dos unidades, y las sacaban de `DISPONIBLE` cuando la
   Spec 032 había dejado la mercancía en `PREPARADO`.
3. **La pantalla pedía la cantidad a mano**, que es justamente el campo que
   produce el defecto anterior. Ya no existe: sale lo que la 032 consolidó.

La mutación volvió a ganarse el sitio. Cambiar `base_quantity` por `quantity`
**pasaba**, porque mi propia prueba llevaba la base en los dos campos. Corregida
la prueba, la mutación falla como debía.

`CONFIRMED → SHIPPED` queda cerrada, y no comprobándola: las aristas
`RELEASED → SHIPPED`, `PREPARING → SHIPPED`, `PREPARED → SHIPPED` y
`CONFIRMED → SHIPPED` se quitaron de la máquina. Hoy solo `INVOICED` despacha.

Un hallazgo ajeno, medido y arreglado en su dueña: el selector de almacén de la
Spec 031 pedía 500 de 564 almacenes y descartaba los 64 últimos en silencio. Se
sustituyó el tope por tandas hasta agotar `total`. El mismo patrón sigue abierto
en otras ocho pantallas, siete de ellas en el límite por defecto de 50, y eso es
del módulo de organización.

Y una sexta lección, esta del arnés y no del producto. La primera regresión
completa dejó un solo fallo: `test_spec034_architecture.py::test_facturar_no_despacha`,
acusando a la 034 de absorber el despacho. No lo hacía. El guardia delimitaba su
bloque como «desde mi cabecera hasta `def create_shipment(`» y la 035 había
puesto delante de esa función cuatro auxiliares suyos. `TEST_DEFECT`, no
regresión. Al auditar el tramo aparecieron **cuatro fronteras posicionales más,
vivas y sin fallar todavía**: la 032, la 033 y la 034 delimitaban su bloque de
`api.py` hasta `@router.post("/shipments"`, y mis dos rutas nuevas de despacho
ya estaban dentro de los tres. No saltaba nada porque esos guardias solo miran
que los permisos existan en el catálogo, y `ventas:view` existe.

Se corrigió la clase entera, no el caso: cabeceras canónicas de Spec en
`service.py` y en `api.py`, un helper compartido con las tres únicas formas
legítimas de recortar, y una invariante transversal que prohíbe por
parametrización que cualquiera de los cinco guardias vuelva a recortar el texto
de un módulo a mano. La invariante queda escrita:

> Las Specs son fronteras semánticas, no posiciones accidentales dentro de un
> archivo. Los architecture guards deben reconocer explícitamente al owner
> siguiente mediante un marcador estable de Spec, módulo o namespace, y nunca
> inferir la frontera por la siguiente función o clase.

`NEXT SPEC = 036 — DEVOLUCIONES, NOTAS DE CRÉDITO Y DÉBITO`

Recibe un pedido en `SHIPPED`, un `Shipment` con su sello de salida y su factura,
y la mercancía en `DESPACHADO` con su procedencia entera en el ledger. El
contrato está en `spec035-spec036-handoff-contract.md`. `DESPACHADO → DEVUELTO`
**no** se ha activado: la matriz de `D0-10` se la asigna a la 036 y la escribirá
su dueña, como cada Spec de este tramo dejó la suya para la siguiente.

Sigue abierta, sin bloquear a la 036, la deuda de la Spec 032: un pedido
rechazado queda en `PREPARING` y no existe la arista `PICKING → DISPONIBLE`.

Y queda dicho en voz alta, otra vez, que **la emisión no está legalmente
homologada** (`D0-07`, Specs 039-043 en `BLOCKED_BY_LEGAL_VALIDATION`) y que la
validación regulatoria es **contra lo registrado**: sin API oficial, KONTROL
registra, valida, adjunta y bloquea, pero **no emite ni verifica en línea**
(Spec 044, `BLOCKED_BY_EXTERNAL_SERVICE`).

La 036 queda **desbloqueada por dependencia**, y ahí se queda: **no** es
`READY_FOR_IMPLEMENTATION`. El proceso fuente termina en el ¶107 —«se registra la
salida»— y no dice una palabra del reingreso. Las cuatro preguntas que el
contrato de entrega le pasa siguen siendo **materiales** y ninguna tiene todavía
autoridad consultable: cuándo y cómo vuelve la mercancía, qué inspección precede
al reingreso, cómo se relaciona la nota de crédito con la factura, y qué pasa con
una reserva ya `FULFILLED`. Decirlas resueltas sería inventarlas.

Implementación de la 036 **no iniciada**: requiere su propio ciclo, con su
`/speckit.clarify` sobre esas cuatro y autorización expresa.

---

## Tras la implementación de la Spec 036 — 2026-09-11

`SPEC 036 — COMPLETE / CONVERGED`. Backend 1279/1271 con los 8 saltos S3
esperados, guardias de arquitectura 128/128, frontend 295/295, e2e propia 36/36
en los tres navegadores y la cadena operativa completa 162/162. Migración `0054`
con ida y vuelta sobre base limpia. DF-12 cierra 6/6.

**La 036 entró con cuatro preguntas materiales abiertas y una razón declarada
para no poder cerrarlas. La razón era falsa.** Al converger la 035 quedó escrito
que el proceso fuente «termina en el ¶107 y no dice nada del reingreso». Lo
primero es cierto; lo segundo no. Ese documento describe *un* proceso, no todos,
y la devolución tiene autoridad de nivel más alto: las normas la escriben entera.

> Devolución de venta: Solicitud → Verificación física → Aprobación → **Entrada
> de inventario** → Nota de crédito vinculada → Ajuste de IVA → Ajuste de cuenta
> por cobrar → Registro en libro de ventas.

De ahí salen las cuatro respuestas sin decidir nada: el inventario es el **cuarto**
acto y no el primero; la verificación va antes y tiene dos destinos, los que
`D0-10` concede; la nota va **después** y **vinculada**, porque «la devolución
física no sustituye una nota de crédito»; y la reserva no se toca, porque `D0-03`
dice «re-reservar tras liberar = nueva fila, nunca reactivación» y `FULFILLED` no
es siquiera una liberación sino un consumo.

La lección de este ciclo no es sobre devoluciones: **«no hay autoridad» hay que
demostrarlo buscándola, no deduciéndolo de que un documento no la tenga.** El
manual de Saint, con treinta y nueve menciones al asunto, no se usó: la matriz de
autoridad lo deja en el nivel 8, no vinculante. La autoridad estaba en el nivel 1.

Tres hallazgos que **solo la regresión completa** vio, y ninguno se silenció: una
prueba que creaba la serie fiscal como `"FACTURA"` y emitía un `INVOICE:` —el
guardia nuevo la destapó, y `"FACTURA"` estaba en un solo sitio del repositorio—;
`updated_at` anulable en mi migración y obligatoria en el ORM; y el catálogo de
estados de mercancía empezando a replicarse en ventas al añadir `DEVUELTO`.

Y dos defectos ajenos, medidos y arreglados en su dueña. El motor fiscal de la
**042** tenía el tipo de documento escrito a mano y solo sabía emitir facturas,
aunque su modelo declaraba los tres desde el principio. Y `issue_invoice` de la
**034** **nunca creaba la cuenta por cobrar**: «9. Emitir factura → 10. Crear
CxC» solo ocurría por el camino heredado, así que toda factura emitida por el
proceso real nacía sin documento que cobrar. Llevaba así desde su convergencia y
ninguna prueba lo veía porque ninguna llegaba a cobrar una factura emitida por
ese camino. Se descubrió al aplicarle una nota y no encontrar nada que ajustar.

`NEXT SPEC = 037 — CUENTAS POR COBRAR`

Recibe el efecto financiero ya conectado: la factura abre su documento por
cobrar al emitirse, la nota de crédito lo reduce y la de débito crea el suyo
propio. Y recibe una pregunta que la 036 **no** decidió y le corresponde: qué
pasa con un crédito a favor cuando la nota se emite sobre una factura ya cobrada.
La norma no condiciona la nota a que la factura esté pendiente, así que la nota
se emite y queda sin aplicar; imputarla a otra factura o devolverla es de CxC y
de tesorería.

Sigue abierta, sin bloquear a nadie, la deuda de la Spec 032 —un pedido rechazado
queda en `PREPARING` sin camino de vuelta— y la del selector de almacén en ocho
pantallas del módulo de organización.

Y queda dicho otra vez que **la emisión no está legalmente homologada**: `D0-07`
sigue abierto y las Specs 039-043 en `BLOCKED_BY_LEGAL_VALIDATION`. Esto vale
igual para la nota de crédito y la de débito que para la factura.

Implementación de la 037 **no iniciada**: requiere su propio ciclo con
autorización expresa.

---

## Tras la implementación de la Spec 037 — 2026-09-11

`SPEC 037 — COMPLETE / CONVERGED`. Guardias de arquitectura verdes, frontend
297/297, e2e propia 27/27 en los tres navegadores y la cadena operativa completa
189/189.

**La pregunta que bloqueaba no necesitaba decidirse: estaba escrita.** Una nota
de crédito sobre una factura ya cobrada deja un **crédito sin aplicar sobre su
propia nota**, porque la fórmula de la arquitectura funcional §9 ya resta los
créditos del saldo y porque el modelo declara que una aplicación puede tener por
origen un `credit`. Sin entidad nueva, sin factura negativa, sin pago falso y sin
reabrir la factura cobrada.

**El hallazgo grave del ciclo no era la pregunta, era el código.**
`apply_credit_note` comprobaba la empresa y nada más: dentro de una misma
empresa, el crédito del cliente X podía pagar la factura del cliente Y. No era un
caso raro sino el camino normal, y ninguna prueba lo veía porque ninguna lo
intentaba. La lección se parece a la de la 035: **el defecto no estaba en lo que
faltaba por construir sino en lo que ya estaba y nadie había intentado romper.**

Otros dos del mismo camino: ninguna aplicación dejaba fila —contra el §9, «cada
aplicación relaciona origen, destino, moneda, tasa, monto nominal, monto fiscal y
fecha»— y no existía el reverso, que la misma fuente define como «evento inverso
y reapertura controlada», nunca borrado.

Y un cuarto que no era de esta Spec. `open_item_balance` calculaba el dinero en
coma flotante, y es el motor que comparten CxP, CxC, tesorería y conciliación.
Antes de tocarlo hubo que **desambiguar a su dueño**: en el Máster 56, `004` es
Licenciamiento; la carpeta `004-compras` corresponde a la **Spec 028**. La
autoridad tampoco estaba lejos: `ADR-D0-001` ya registraba `KQA-100` —«`Decimal
+ float`… que rompió factura, pago, cobro»— como defecto CRÍTICO, y el propio
módulo tenía su helper con la advertencia escrita. El motor nunca lo recibió. Y
no hubo que decidir política de redondeo ninguna, porque el cálculo no depende de
una: el `round(..., 6)` no era política sino el margen que la coma flotante
necesitaba, y su huella estaba a la vista en el `<= 1e-6` con que se cerraba un
documento «suficientemente cerca de cero».

`NEXT SPEC = 038 — TESORERÍA`

Recibe el motor de saldos ya exacto y la frontera clara: la 037 gobierna el
derecho de cobro y la 038 el movimiento de dinero, y por eso aplicar un crédito
no crea ningún cobro ni toca tesorería.

Y recibe **dos preguntas que la 037 no decidió porque no son suyas**: si un
crédito a favor puede devolverse en dinero —ninguna fuente lo dice, así que no se
implementó nada— y cuál es la política de diferencia cambiaria que haría posible
aplicar un crédito entre monedas distintas, hoy bloqueada con error de dominio.

Implementación de la 038 **no iniciada**: requiere su propio ciclo con
autorización expresa.

---

## Tras la implementación de la Spec 038 — 2026-09-11

`SPEC 038 — COMPLETE / CONVERGED`. Con ella se cierra la cadena entera de
pedido a cobro: cotizar, pedir, reservar, preparar, consolidar, confirmar,
facturar, despachar, devolver, cobrar y mover el dinero.

**Las dos preguntas que la 037 dejó abiertas no se resolvieron leyendo: las
decidió el owner.** Es la diferencia con los tres ciclos anteriores, donde la
autoridad estaba escrita y solo faltaba leerla como autoridad. Aquí no había
nada que leer —la arquitectura funcional §9 decía «según política» y no existía
política ninguna— y por eso el ciclo empezó con `OWNER-DECISION-038-01` y
`-02`. Ninguna fuente existente las contradice.

**El hallazgo grave del ciclo vuelve a ser lo que ya estaba.** `_rate_snapshot`
devolvía **`1,0`** cuando no había tasa registrada: un pago en divisa quedaba
valorado al cambio uno a uno y nada lo decía. No era un caso raro, era lo que
pasaba cada vez que faltaba la tasa —que es justo cuando más importa—. Tercera
vez seguida que el defecto no está en lo que falta por construir sino en lo que
ya existe y nadie había intentado romper: `validate_shipment` aprobaba siempre,
`apply_credit_note` ignoraba al cliente, `_rate_snapshot` inventaba la tasa.

**Y el doble gasto.** Un crédito a favor puede ahora irse por dos caminos
—imputarse a una factura o devolverse en dinero— y el riesgo evidente es irse
por los dos. La reserva es lo que lo impide, y obligó a separar en la 037 dos
cifras que hasta ahora eran una sola: lo **imputable** y lo **debido**.

## El hecho que decide lo siguiente

Al dejar de inventar la tasa, el sistema se volvió honesto y con ello apareció
un hueco que antes tapaba el `1,0`: **nadie registra tasas**. Hoy tesorería se
niega a convertir y a valorar si no hay tasa del día, y la única forma de que la
haya es que una persona la teclee, todos los días, en `/treasury/exchange-rates`.

El Máster 56 ya lo anotaba —«013 · Maestros financieros · **Tasa BCV depende de
048**»— pero era una deuda teórica mientras el código rellenaba el hueco solo.
Ahora es una parada operativa.

`NEXT SPEC = 013 — MAESTROS FINANCIEROS` (con 048 como proveedora del origen)

`RUNNER-UP = 049 — DASHBOARD`, cuyas cuatro dependencias —023, 034, 037 y 038—
están por primera vez todas en `COMPLETE / CONVERGED`, y que mostraría cifras
cuyas fuentes ya son de fiar.

La búsqueda de la tasa **no se implementa dentro de tesorería**: la 038 consume
la que el maestro tenga registrada y no llama a ninguna web, y así debe seguir.

## Lo que esta decisión NO autoriza

`D0-07` sigue **abierto**. La 038 certifica la tesorería técnica y
funcionalmente; **no** afirma homologación fiscal ni liberación legal, y ninguna
regla legal venezolana está escrita en el código: se configura, se versiona y se
guarda con su referencia de autoridad. El **IGTF** no se tocó: su dueña es la
041, en `BLOCKED_BY_LEGAL_VALIDATION`.

Implementación de la 013 **no iniciada**: requiere su propio ciclo con
autorización expresa.

---

## Tras la implementación de la Spec 013 — 2026-09-11

`SPEC 013 — COMPLETE / CONVERGED`. La tasa dejó de ser un número suelto: tiene
par explícito, fuente con autoridad declarada, momento de vigencia, versión y
procedencia. Y la resolución dejó de tomar decisiones económicas por su cuenta.

**Lo que se buscaba era el hueco; lo que apareció fueron siete defectos en lo ya
escrito.** Que el par no estuviera en ninguna parte —`("VED", "VES")` cableado
en el dominio de un producto que se vende como parametrizable—, que dos monedas
con el mismo código pudieran convivir y la resolución eligiera al azar, que dos
tasas del mismo día dejaran el desempate a PostgreSQL, y que la tasa viajara
declarada como `float` por un borde que siempre fue exacto.

**Dos de los siete los había metido yo en la 038.** Corregir que la tasa se
inventara trajo dos formas nuevas de derivarla sin decirlo: invertir un par y
cruzar dos cotizaciones. Ninguna tenía política que la autorizara y ninguna
dejaba constancia, de modo que la instantánea decía «usó la tasa 40» cuando
había usado 0,025. Cuarta vez seguida que el defecto grave está en lo que ya
existe; la novedad es que esta vez lo que ya existía lo había escrito el ciclo
anterior.

**Y un octavo que solo apareció de punta a punta.** Preguntar «qué tasa rige
hoy» resolvía a las cero horas de hoy, así que una tasa registrada esta mañana
no servía para una operación fechada hoy. Las pruebas unitarias no lo veían
porque registraban y consultaban con el mismo instante. Lo vio la que atraviesa
el sistema entero.

**Y la instalación limpia encontró el resto.** La sesión se cortó con la regresión
final sin terminar y el entorno de QA desapareció. Reinstalar la base de e2e de
cero —el primer día de un cliente real— sacó una familia de 500 que ninguna
corrida sobre meses de datos podía ver: «busco y, si no está, creo» sobre un
índice único, sin nadie que capture la colisión. Uno en inventario (023), en
plena recogida; cinco en código que yo había escrito en este mismo ciclo. Y una
prueba de concurrencia que los debía cubrir aceptaba `IntegrityError` como
rechazo válido.

Detrás había algo peor: **la unicidad de la 013 vivía solo en la migración**. La
base de pruebas sale de los modelos, así que ninguna prueba la ejerció nunca.
`alembic check` bajó de 27 operaciones de deriva a 21, y las 21 que quedan son de
otras doce Specs: están medidas y con dueño, no escondidas.

## Lo que este ciclo deliberadamente no construyó

**El proveedor automático del BCV.** No hay en el repositorio ni canal oficial
estable verificable, y montar un *scraping* frágil y llamarlo integración habría
sido peor que el hueco: daría una cifra con aspecto de autoridad que nadie
respalda. La operación vive de alta manual y de importación de fichero, el
contrato de proveedor queda definido, y el día que exista un canal usable lo
implementa su dueña.

`NEXT SPEC = 048 — INTEGRACIONES` (adaptador de tasas, si aparece canal usable)

`RUNNER-UP = 049 — DASHBOARD`, cuyas dependencias —023, 034, 037 y 038— siguen
todas en `COMPLETE / CONVERGED`, y que ahora además mostraría cifras en moneda
con una tasa que tiene procedencia.

Si la 048 no tiene de dónde tirar, la 049 es la que aporta sin esperar a nadie.

## Lo que esta decisión NO autoriza

`D0-07` sigue **abierto**. Que el BCV pueda configurarse como fuente oficial no
es una afirmación legal: es una fila del maestro con su referencia de autoridad
declarada, y la referencia dice exactamente lo que es. El **IGTF** sigue siendo
de la 041, en `BLOCKED_BY_LEGAL_VALIDATION`.

Implementación de la 048 **no iniciada**: requiere su propio ciclo con
autorización expresa.

---

## Programación de deudas monetarias `float` — 2026-09-13

Resueltas por dueño antes de tocar código, siguiendo el procedimiento completo:
símbolo, fichero, módulo, llamadas, modelos, mapa de equivalencias, máster y
trazabilidad existente. **Ninguna se implementa aquí.**

### Conflictos de identidad de dueño

**`OWNER_IDENTITY_CONFLICT_DEBT = 0`.** El «019» que acompañaba a estas deudas no
era una numeración histórica ni local: fue un error de redacción en
`spec038-convergence.md` §12 y `spec038-implementation-cycle.md` §11, corregido
como errata en `spec038-convergence.md` §14. La Spec 019 global —Recepción
física— no tiene relación y no se toca.

### FLOAT-038-A · El borde de la API de tesorería lee dinero como `float`

| Campo | Valor |
|---|---|
| Dueña | **Spec 038 — Tesorería** |
| Evidencia de dueño | `treasury/api.py` y `treasury/service.py` en `006-tesoreria` (↔ 013, 038, 041); los movimientos bancarios son operación de tesorería, no maestro (013) ni IGTF (041) |
| Símbolos | `BankTransactionCreate.amount` y `.commission` (`api.py:135`, `:141`) → `create_bank_transaction(amount: float, commission: float)` (`service.py:515`) |
| Mismo defecto, misma dueña | `SessionOpen.opened_amount` (`:109`), importe de movimiento de caja (`:114`), importe de ejecución (`:152`), `opening_balance` y `closing_balance` de conciliación (`:166`, `:167`), importe de transferencia (`:197`) |
| Tipo actual | `float` en Pydantic y en la firma del servicio; `Mapped[float]` sobre columnas `Numeric(18,2)` |
| Autoridad monetaria esperada | `Decimal` de extremo a extremo (`MONETARY-BALANCE-INVARIANT`, `KQA-100`) |
| Riesgo | El JSON se lee como `float`, que conserva unos 15-16 dígitos significativos; la columna admite 18. **Un importe grande pierde céntimos** antes de llegar al servicio |
| Consumidores directos | `POST /treasury/bank-transactions`, sesiones de caja, ejecuciones, conciliación, transferencias. La conversión y el reembolso de la 038 ya llaman con `Decimal` desde dentro |
| Severidad | **Alta** — es la entrada de dinero en tesorería |
| Prioridad | **1** |

**Aceptación a programar:** entrada `Decimal` en Pydantic sin conversión a
`float`; ORM `Numeric` con anotación `Decimal`; paridad Alembic; PostgreSQL
`Numeric`; la serialización no degrada; casos `0.10` + `0.20`; un importe de 18
dígitos que hoy pierde precisión; límite de escala; mutación `Decimal → float`
que debe caer; regresión de todos los consumidores listados.

### FLOAT-038-B · Arqueo y cierre de caja

| Campo | Valor |
|---|---|
| Dueña | **Spec 038 — Tesorería** |
| Evidencia de dueño | `CashSession` en `treasury/models.py`; flujo de caja de la 038 (`spec038-implementation-cycle.md` §4.4) |
| Corrección previa | La **resta** ya es exacta: `arqueo_session` usa `_money(counted) - _money(expected)` desde la 038, con `test_el_arqueo_no_arrastra_error_binario`. La deuda anotada como «resta en coma flotante» era falsa (errata §14) |
| Residuo real | `close_session` decide con **épsilon sobre dinero**: `abs(diff) > 1e-6`; `ArqueoBody.counted_amount: float` y la firma de `arqueo_session`; `float(...)` al serializar la auditoría de arqueo y de cierre |
| Autoridad monetaria esperada | cero exacto en `Decimal`, sin épsilon; precisión desde el maestro de moneda (013) |
| Riesgo | Una diferencia menor que el épsilon pero distinta de cero —imposible en `Decimal(18,2)`, posible si llega un `float`— cerraría sin aprobación; la auditoría guarda cifras que ya no son las exactas |
| Consumidores directos | `POST /treasury/cash-sessions/{id}/arqueo`, `…/close`, auditoría de caja |
| Severidad | **Media** |
| Prioridad | **2** |

**Aceptación a programar:** contado, esperado y diferencia en `Decimal`; sin
resta en `float`; semántica de cero exacto; ningún épsilon; precisión desde el
maestro de moneda; sobrante y faltante exactos; mutación de vuelta a `float` o
de reintroducir el épsilon que debe caer; regresión de la conciliación de caja.

### FLOAT-041 · `evaluate_igft` lee la alícuota como `float`

`rate = float(params.get("rate", 0.0))` en `treasury/service.py`, dentro de
`evaluate_igft`. Dueña **Spec 041 — IGTF**, en `BLOCKED_BY_LEGAL_VALIDATION`
(`D0-07`). **Registrada, no programada**: no se puede certificar una alícuota sin
la validación legal que la sostiene.

### CONC-046 · Una subida documental concurrente escapa como excepción

Hallada durante la regresión del delta de la Spec 004, no absorbida.

| Campo | Valor |
|---|---|
| Dueña | **Spec 046 — Gestión documental** |
| Síntoma | en dos subidas simultáneas de la misma versión, la que pierde recibe una `UniqueViolation` de `uq_document_versions_number` **sin capturar** (P25) |
| Prueba afectada | `test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2` **pasa igualmente**: acepta la excepción del hilo como rechazo válido, lo que P25 prohíbe |
| Evidencia | advertencia `PytestUnhandledThreadExceptionWarning` en 1 de 4 regresiones del 2026-09-13; intermitente porque depende de que los hilos coincidan; ni el módulo ni la prueba se tocaron desde `00d7cd2` |
| Clasificación | `PREEXISTING` |
| Severidad | Media — un 500 ante una carrera legítima; la unicidad de la versión sí se sostiene |
| Aceptación a programar | captura estrecha con `es_violacion_unica` y conflicto de dominio; carrera **forzada** que demuestre que ocurrió; la prueba deja de aceptar la excepción; mutación que la reintroduzca y caiga |
| Prioridad | **3**, después de FLOAT-038-A y FLOAT-038-B |

### Ciclo obligatorio para cada delta programado

`SOLICITUD/CAMBIO → /speckit.specify → /speckit.clarify → /speckit.plan →
CONSTITUTION GATE → /speckit.checklist → /speckit.tasks → /speckit.analyze →
traceability → EXPRESS AUTHORIZATION → /speckit.implement → tests/evidence →
/speckit.converge`, dentro de la Spec 038 existente. Con instalación limpia
(P24), paridad modelo ↔ migración si se toca el esquema (P26) y mutaciones con
semántica observable (P27).

**Secuencia recomendada:** FLOAT-038-A → FLOAT-038-B, ambas **antes** de
implementar la Spec 049, que consume movimientos bancarios.

### Deriva de esquema heredada — programada, no absorbida

`GLOBAL_SCHEMA_INHERITED_DRIFT = 21`, con dueño por operación:

| Spec | Tablas | Operaciones |
|---|---|---|
| 009 Terceros | `parties`, `customers`, `suppliers`, `carriers`, `drivers` | 5 |
| 010 Productos y servicios | `products`, `services`, `attribute_applicabilities` | 3 |
| 006 Auditoría | `audit_events` | 2 |
| 023 Inventario | `inventory_balances`, `inventory_movements` | 2 |
| 029 Cotización y pedido | `sales_order_lines`, `sales_quote_lines` | 2 |
| 031 Picking | `pick_list_lines` | 2 |
| 056 Homologación y release | `release_versions` | 2 |
| 004 Licenciamiento | `license_states` | 1 |
| 021 Confirmación de inventario | `receipt_confirmations` | 1 |
| 041 IGTF | `fiscal_rules` | 1 |

**Diez Specs**, no doce: el «12» se escribió sin mapear y queda corregido.
Evidencia: migración que creó cada tabla (`0001_fundacion`, `0002_maestros`,
`0003_inventario`, `0005_ventas`, `0006_tesoreria`, `0011_homologacion`,
`0047_spec021`, `0049_spec031`) y `spec-equivalence-map.md`. La Spec 013 sigue
con deriva **0**.

---

## Tras el ciclo de la Spec 047 — 2026-09-14

`SPEC047 — BLOCKED BY MATERIAL DECISION` · `SPEC049 — BLOCKED BY OWNER DEPENDENCY` (sin cambio).

La 047 no tenía nada: ni tablas, ni carpeta, ni planificador, ni sistema de
idiomas. El ciclo llegó hasta `/speckit.analyze` y se detuvo en dos preguntas que
ninguna autoridad del repositorio responde (`specs/047-notificaciones-tareas/clarifications.md` §4).

### El hecho que decide

**KONTROL no tiene nada que se ejecute sin una petición.** La 047 es dueña del
planificador de plataforma por `ADR-D0-003`, y `ADR-009` prohíbe construirlo sin
un ADR. Esa misma ausencia deja hoy sin ejecutor la caducidad de reservas de la
030, `mark_expired` de la 045, el correo de la 048 y el planificador de retención
de la 052.

### Decisiones pendientes que bloquean trabajo

| Decisión | Decide | Desbloquea |
|---|---|---|
| **OQ-047-01** — planificador de plataforma (recomendada: temporizador del sistema con orden idempotente, sin cola) o proyección en lectura | Arquitectura · Producto | 047; y, con la opción A, la caducidad de la 030, el vencimiento de la 045, el correo de la 048 y la retención de la 052 |
| **OQ-047-02** — idioma (recomendada: contrato neutro con clave y parámetros, catálogo ES en v1) | Producto | Pantallas de la 047 |
| OQ-048-01..03 — fuente, TLS y tasa oficial del BCV | Producto · Legal | Proveedor automático de tasas |
| MD-049-01, MD-049-02 — monedas y KPIs fiscales | Producto | 049, junto con sus dueñas |
| D0-06 — hospedaje de la licencia central | Producto · Infraestructura | 004 |
| D0-07 — validación legal fiscal | Legal | 039-043, 056 |

### Siguiente paso

**OQ-047-01 es la decisión de mayor desbloqueo.** Sin ella, lo único ejecutable
sin decidir nada son los deltas programados el 2026-09-13, en su orden:
**FLOAT-038-A → FLOAT-038-B → CONC-046**. Ninguno se ha iniciado.

`READY_FOR_IMPLEMENTATION = 0`.

### Lo que esta decisión NO autoriza

Ni implementar la 047 ni la 049, ni ejecutar los deltas. Cada uno requiere su
ciclo completo y autorización expresa.

---

## Tras converger la Spec 047 — 2026-09-14

`SPEC047 — COMPLETE / CONVERGED` · `SPEC049 — BLOCKED BY OWNER DEPENDENCY` (sin cambio; bloqueos 4 → 3).

El owner cerró OQ-047-01 (planificador: temporizador del sistema → orden idempotente)
y OQ-047-02 (clave de mensaje y parámetros, catálogo `es`, `en` diferido). Se aprobó
`ADR-D0-015` y la 047 se implementó y convergió (`specs/047-notificaciones-tareas/convergence.md`).

### El hecho que decide

**KONTROL ya puede hacer algo cuando pasa el tiempo.** Ese mecanismo existe, pero
casi nadie lo usa todavía: de las cuatro dueñas que lo esperaban, solo la 045 tiene
manejador, y está deshabilitado a propósito.

| Consumidor | Estado | Qué falta | Dueña |
|---|---|---|---|
| Vencimiento de pasos de la 045 | manejador registrado y **deshabilitado** | definir qué pasa con un paso `EXPIRED`, que hoy sale de la bandeja y no se reabre | 045 |
| Caducidad de reservas con TTL | sin manejador | registrar el suyo sobre su contrato canónico | 030 |
| Correo, push y SMS | frontera lista, sin proveedor | adaptador | 048 |
| Retención | sin manejador | su regla | 052 |

### Deuda nueva registrada con su dueña

| Deuda | Dueña | Prioridad sugerida |
|---|---|---|
| `e2e/approvals.spec.ts`: el helper pulsa «Desactivar» por coincidencia de subcadena desde N6, y el escenario multiempresa confía en un `company_id` que la ruta ignora; falla igual con el frontend de `370e10a` | 045 | alta: el motor de aprobaciones no tiene hoy su E2E en verde |
| `GET /approvals/inbox` con `limit`/`offset` y filtrado en Python de todas las empresas | 045 | media |

### Decisiones pendientes que bloquean trabajo

| Decisión | Decide | Desbloquea |
|---|---|---|
| Camino tras `EXPIRED` en la 045 | Producto · 045 | habilitar su manejador programado |
| OQ-048-01..03 — fuente, TLS y tasa oficial del BCV | Producto · Legal | proveedor automático de tasas |
| MD-049-01, MD-049-02 — monedas y KPIs fiscales | Producto | 049, junto con sus dueñas |
| D0-06 — hospedaje de la licencia central | Producto · Infraestructura | 004 |
| D0-07 — validación legal fiscal | Legal | 039-043, 056 |

### Siguiente paso

Lo ejecutable sin decidir nada sigue siendo, en orden, **FLOAT-038-A → FLOAT-038-B →
CONC-046**, las tres programadas el 2026-09-13 y sin iniciar. La precisión del dinero
de tesorería sigue siendo lo que más daño acumula. Detrás, el **delta del E2E de la
045**, que no espera decisiones y devuelve a verde la evidencia del motor de aprobaciones.

`READY_FOR_IMPLEMENTATION = 0`.

### Lo que esta decisión NO autoriza

Ni implementar la 049, ni habilitar el manejador de la 045, ni ejecutar ninguno de los
deltas. Cada uno requiere su ciclo completo y autorización expresa.

---

## Tras el delta FLOAT-038-A — 2026-09-14

`FLOAT-038-A — BLOCKED BY MATERIAL DECISION` · detalle en
`specs/006-tesoreria/spec038-bank-amount-decimal-delta.md`.

La dueña se resolvió con evidencia: es la 038, no la 019 global. La base ya es
`numeric(18,2)` y no hace falta migración. La **entrada** puede pasar a `Decimal`
de forma aditiva, con el precedente del mismo módulo. La **salida** no puede ser
exacta sin cambiar el contrato: FastAPI convierte el `Decimal` a `float` al
serializar, y `1234567890123456.78` sale como `1234567890123456.8`. Además, hoy un
importe de `0.001` crea un movimiento de `0.00`. Sin código tocado.

### Decisiones nuevas que bloquean trabajo

| Decisión | Decide | Recomendada | Desbloquea |
|---|---|---|---|
| **OQ-FLOAT-038-A-01** — importe de tesorería en la respuesta: cadena decimal (cambio público), número con degradación documentada o número literal exacto | Producto · Arquitectura · 038 | cadena decimal para todo el recurso, con el frontend adaptado en el mismo delta | FLOAT-038-A y la frontera de FLOAT-038-B |
| **OQ-FLOAT-038-A-02** — importe con más decimales que la escala: rechazar, redondeo de PostgreSQL o cuantización de `_money` | Producto · 038 | rechazar con 422 | FLOAT-038-A y el `counted_amount` de FLOAT-038-B |

### FLOAT-038-B, revalidada

Sigue siendo la siguiente de la secuencia, y **no está lista entera**:

| Parte | ¿Depende de las OQ nuevas? |
|---|---|
| épsilon `1e-6` en `close_session` | no |
| `float(...)` en la auditoría de arqueo y cierre | no |
| `counted_amount: float` en el borde | sí — escala (OQ-02) |
| importes de la sesión en la respuesta (`opened_amount`, `counted_amount`, `difference` salen como `Decimal` crudo → número) | sí — representación (OQ-01) |

Abrir su ciclo sin esas respuestas lo detendría en la misma pregunta.

### Siguiente paso

**Responder OQ-FLOAT-038-A-01 y -02 una sola vez para tesorería.** Con ellas se
ejecutan FLOAT-038-A y FLOAT-038-B completas, en ese orden. Sin ellas, lo
ejecutable sin decidir nada es **CONC-046** (dueña 046, independiente) y el
**delta del E2E de la 045**.

`READY_FOR_IMPLEMENTATION = 0`. FLOAT-038-B **no se ha iniciado**.

### Lo que esta decisión NO autoriza

Ni ejecutar FLOAT-038-A ni FLOAT-038-B, ni cambiar la representación del dinero
en ninguna ruta, ni CONC-046, ni la 049. Cada uno requiere su ciclo completo y
autorización expresa.

---

## Tras converger FLOAT-038-A — 2026-09-15

**`FLOAT-038-A — CLOSED`** · `TARGETED DELTA COMPLETE / CONVERGED` · detalle en
`specs/006-tesoreria/spec038-bank-amount-decimal-delta.md`.

El owner cerró las dos preguntas y el delta se completó dentro de la 038: el importe
del movimiento bancario entra y sale como texto decimal, viaja como `Decimal`, se
guarda en `numeric(18,2)` sin migración, y lo que no cabe se rechaza con 422. El
cambio de contrato es incompatible y está autorizado.

### Decisiones cerradas que ya tienen autoridad

| Decisión | Regla | Dónde aplica ya |
|---|---|---|
| OQ-FLOAT-038-A-01 | el dinero del contrato público de tesorería viaja como **texto decimal**; un número JSON no es autoridad monetaria | movimiento bancario (`amount`, `commission`) |
| OQ-FLOAT-038-A-02 | más decimales que la escala de la columna → **422**, sin redondeo de PostgreSQL ni de `_money` | ídem |

La herramienta es reutilizable: `app/shared/money.py` lee escala y precisión de la
columna, y `lib/decimal.ts` normaliza sin `Number`.

### FLOAT-038-B, revalidada

Sigue siendo la siguiente, y ahora **no espera ninguna decisión**:

| Parte | Autoridad |
|---|---|
| épsilon `1e-6` en `close_session` | decisión cerrada de antes: cero exacto |
| `float(...)` en la auditoría de arqueo y cierre | `KQA-100` |
| `counted_amount: float` en el borde | OQ-FLOAT-038-A-01 y -02, ya cerradas |
| importes de la sesión en la respuesta | OQ-FLOAT-038-A-01, ya cerrada |

Lo que su propio ciclo tendrá que fijar —sin que sea una pregunta abierta hoy— es
el perímetro: si el contrato de la sesión de caja se corrige entero (`opened_amount`,
`expected_amount`, `difference` y los importes de sus movimientos) o solo el arqueo,
para no dejar el mismo objeto con dos políticas, que es el criterio que siguió
FLOAT-038-A con la comisión.

`READY_FOR_IMPLEMENTATION = 0`: FLOAT-038-B necesita su ciclo completo y autorización
expresa. **No se ha iniciado.**

### Deuda nueva registrada con su dueña

| Deuda | Dueña | Hallazgo | Prioridad sugerida |
|---|---|---|---|
| CLOCK-013 | 013 | cinco pruebas de `test_spec013_financial_masters.py` registran con `datetime.now(UTC)` y consultan con `date.today()` local: fallan entre las 00:00 y las 02:00 en una máquina con UTC+2. Reproducido en `239259b` | media: la evidencia depende de la hora |
| E2E-031-RESERVAS | 031 (prueba) · 023 (filtro) | `GET /inventory/reservations` ignora `source_order_id`; `picking.spec.ts:288` cuenta las reservas de toda la empresa y falla si otro navegador reserva a la vez | media |

La corrección de `AsyncButton.test.tsx` (dueña 005) se hizo dentro del delta
porque bloqueaba la puerta de frontend, y consta como delta recibido en el máster.

### Siguiente paso

En orden, lo ejecutable sin decidir nada: **FLOAT-038-B → CONC-046**, y detrás el
delta del E2E de la 045, CLOCK-013 y E2E-031-RESERVAS.

### Lo que esta decisión NO autoriza

Ni iniciar FLOAT-038-B, ni tocar los otros siete `float` del borde de tesorería, ni
CONC-046, ni la 049. Cada uno requiere su ciclo completo y autorización expresa.

---

## Tras converger FLOAT-038-B — 2026-09-15

**`FLOAT-038-B — CLOSED`** · `TARGETED DELTA COMPLETE / CONVERGED` · detalle en
`specs/006-tesoreria/spec038-cash-close-decimal-delta.md`.

El conteo del arqueo entra como texto exacto con la escala de su columna, el cierre
decide con cero exacto —un céntimo exige aprobación—, la auditoría guarda texto y la
sesión de caja sale con todos sus importes en texto. La resta ya era exacta y no
cambió. Se corrigió además un defecto que hacía inalcanzable el arqueo desde la
pantalla. Sin preguntas nuevas: bastaron las decisiones de FLOAT-038-A.

### Cola revalidada

| Orden | Trabajo | Dueña | ¿Espera decisión? | Motivo del orden |
|---|---|---|---|---|
| 1 | **CONC-046** · una subida documental concurrente escapa como excepción | 046 | no | es un 500 ante una carrera legítima (P25) y la prueba que debería impedirlo lo acepta |
| 2 | **E2E-045** · `approvals.spec.ts` «Desactivar» y el `company_id` ignorado | 045 | no | el motor de aprobaciones sigue sin su E2E en verde |
| 3 | **CLOCK-013** · cinco pruebas de la 013 dependen del reloj | 013 | no | la evidencia de la 013 falla entre las 00:00 y las 02:00 en UTC+2 |
| 4 | **E2E-031-RESERVAS** · el filtro `source_order_id` que la API ignora | 031 · 023 | no | intermitente, solo con navegadores en paralelo |
| 5 | Los **seis `float`** restantes del borde de tesorería: `opened_amount` de apertura, importe de movimiento de caja, importe de ejecución, `opening_balance` y `closing_balance` de conciliación, importe de transferencia | 038 | **no**: la política ya está decidida (texto decimal, 422, cero exacto) | mismo patrón y mismas herramientas (`app/shared/money.py`, `lib/decimal.ts`) |

Siguen bloqueados por decisión: el camino tras `EXPIRED` en la 045, OQ-048-01..03,
MD-049-01/02, D0-06 y D0-07. La 049 sigue `BLOCKED BY OWNER DEPENDENCY`.

`READY_FOR_IMPLEMENTATION = 0`: cada punto de la cola necesita su ciclo completo y
autorización expresa. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni CONC-046, ni el E2E de la 045, ni CLOCK-013, ni E2E-031-RESERVAS, ni los seis
`float` restantes, ni la 049. Cada uno requiere su ciclo completo y autorización expresa.

---

## Tras converger CONC-046 — 2026-09-15

**`CONC-046 — CLOSED`** · `TARGETED DELTA COMPLETE / CONVERGED` · detalle en
`specs/046-gestion-documental/conc-046-concurrent-version-delta.md`.

La perdedora de dos subidas simultáneas de versión recibe `409 VERSION_CONFLICT` en
vez de un 500 y no deja binario; con la misma `Idempotency-Key` recibe la versión
ganadora; y un reintento devuelve la versión de su clave, no la vigente. Sin
migración ni bloqueo nuevo: PostgreSQL ya decidía y ahora la aplicación lo dice.

### Lección que sirve al siguiente

El `uiLogin` del E2E documental casaba «Activar» con «Desactivar» y desactivaba la
empresa. Se corrigió con `exact: true`. **Es el mismo defecto que E2E-045** en
`approvals.spec.ts`, que no se tocó: su corrección ya tiene forma conocida.

### Cola revalidada

| Orden | Trabajo | Dueña | ¿Espera decisión? | Motivo |
|---|---|---|---|---|
| 1 | **E2E-045** · `approvals.spec.ts`: «Desactivar» por subcadena y el `company_id` que la ruta ignora | 045 | no | el motor de aprobaciones sigue sin su E2E en verde; la mitad del arreglo ya se probó en la 046 |
| 2 | **CLOCK-013** · cinco pruebas de la 013 dependen del reloj | 013 | no | la evidencia de la 013 falla entre las 00:00 y las 02:00 en UTC+2 |
| 3 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no | intermitente con navegadores en paralelo |
| 4 | Los **seis `float`** restantes del borde de tesorería | 038 | no | política ya decidida |

### Deuda nueva registrada

| Deuda | Dueña | Hallazgo | Prioridad sugerida |
|---|---|---|---|
| E2E-046-TIPOS | 046 | `documents.spec.ts:309` espera «Página siguiente», que solo existe con más de 10 filas; falla si la tabla aún no tiene suficientes. Precisado el 2026-09-17: sobre una base recién instalada **falla también aislada** —`isEnabled()` sobre un botón que no existe espera hasta agotar la prueba—, y pasa en cuanto la base acumula tipos. No es intermitencia de carga: es el recuento de filas | baja |
| ORPHAN-046-SINGLE | 046 | con un tipo `SINGLE`, `VERSION_NOT_ALLOWED` se lanza después de escribir el binario, que queda huérfano | baja: basura recuperable |
| IDEM-046-TRUNC | 046 | la clave idempotente de subida se trunca a 64 caracteres y solo 10 de la clave del cliente distinguen | media: dos claves largas con el mismo prefijo en el mismo documento se confunden |

Siguen bloqueados por decisión: el camino tras `EXPIRED` en la 045, OQ-048-01..03,
MD-049-01/02, D0-06 y D0-07. La 049 sigue `BLOCKED BY OWNER DEPENDENCY`.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-045, ni CLOCK-013, ni E2E-031-RESERVAS, ni los seis `float`, ni las tres
deudas nuevas de la 046, ni la 049. Cada uno requiere su ciclo completo y
autorización expresa.

---

## Tras converger E2E-045 — 2026-09-16

E2E-045 queda **CERRADA**. Era una deuda de verificación, y así se resolvió: el único
fichero tocado es `resources/frontend/e2e/approvals.spec.ts`. **0 ficheros de producto.**

| Hecho | Detalle |
|---|---|
| Defecto | El ayudante casaba «Activar» por subcadena y pulsaba «Desactivar»; después esperaba ver el botón que él mismo había hecho desaparecer |
| Segundo defecto | La prueba «multiempresa» atribuía a `?company_id=` una autoridad que la ruta no declara |
| Reproducción previa | 2 failed / 9 passed sobre `4d88fbd`, empresa intacta en base; diagnóstico `ambiguo=1 exacto=0 desactivar=1 nombres=["Desactivar"]` |
| Después | 13/13 en Chromium tres veces · 39/39 en tres navegadores · vitest 368/368 |
| Mutaciones | E2E-045-01..03, 0 supervivientes, restauración verificada con `cmp` |

Se descubrió además que, sin empresa activa, el producto no muestra una fila con
«Activar» sino la compuerta «Seleccione una empresa». El ayudante anterior no lo sabía
porque nunca llegó a ese estado; el nuevo resuelve los dos y falla explícitamente en
cualquier tercero.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **CLOCK-013** · cinco pruebas de la 013 dependen del reloj local | 013 | no |
| 2 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 3 | Los **seis `float`** restantes del borde de tesorería | 038 | no |

### Deuda nueva registrada

| Deuda | Dueña | Hallazgo | Prioridad sugerida |
|---|---|---|---|
| **E2E-HELPER-EMPRESA-AMBIGUO** | almacén · unidades de medida | Cuatro ficheros conservan copia del ayudante defectuoso: `warehouse-a11y.spec.ts:11`, `warehouse-structure.spec.ts:51`, `uom-conversion.spec.ts:44`, `uom-a11y.spec.ts:28`. Hoy no fallan porque la empresa suele llegar ya activa; fallarán en cuanto no lo esté | media |
| **INBOX-045-AISLAMIENTO** | 045 | El aislamiento de la bandeja **entre empresas distintas** no está probado en ningún sitio: `test_mc_security_045_046.py` cubre políticas y documentos, no la bandeja, y el entorno E2E tiene una sola empresa. La aserción anterior fingía esta cobertura | media |

Siguen abiertas las tres deudas de la 046 (E2E-046-TIPOS, ORPHAN-046-SINGLE,
IDEM-046-TRUNC) y la paginación de la bandeja de la 045. Siguen bloqueados por decisión:
el camino tras `EXPIRED` en la 045, OQ-048-01..03, MD-049-01/02, D0-06 y D0-07.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni CLOCK-013, ni E2E-031-RESERVAS, ni los seis `float`, ni las dos deudas nuevas de este
delta, ni las tres de la 046, ni la 049. Cada uno requiere su ciclo completo y
autorización expresa.

---

## Tras converger MIGR-0033-FK-HUERFANA — 2026-09-16

El bloqueante que la auditoría maestra encontró queda **cerrado**. Era de la 052 —el
contrato de actualización— y su corrección vive entera en la cadena de migraciones.

| Hecho | Detalle |
|---|---|
| Defecto | `0016` preservó a propósito una solicitud legada cuya empresa ya no existe, apoyándose en que la tabla legada no tenía clave foránea; `0033` se la puso a 80 tablas y la actualización de cualquier instalación con histórico abortaba entera |
| Corrección | La clave foránea nace `NOT VALID` y se valida sola donde no cuelga nada. El pasado se tolera y se anota; toda escritura nueva sigue exigiendo una empresa real |
| Autoridad | «No se inventa empresa» y la clase **MC-D `NON_RECONSTRUCTIBLE`** de la matriz de ARCH-MC-001: anotar, no rellenar |
| Por qué se tocó una migración escrita | No hay política de inmutabilidad, no hay instalaciones desplegadas, y una migración nueva sería inalcanzable: la actualización muere *en* `0033` |
| Evidencia | cero→cabeza y legado→cabeza en verde · histórico 6/6 íntegro · 0 empresas fabricadas · 0 reasignaciones · escritura inválida rechazada · 5 mutaciones sin supervivientes · regresión 1.573/0 · deriva nueva 0 · esquema idéntico al anterior |

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | Los **seis `float`** del borde de tesorería | 038 | no |
| 2 | **CLOCK-013** | 013 | no |
| 3 | **E2E-031-RESERVAS** | 031 · 023 | no |
| 4 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 5 | Verificar restauración (DT-11) | 053 | no |

La recomendación de la auditoría se cumple: cerrado el nº 1 de su secuencia, el
siguiente candidato son los seis `float` de tesorería, cuya política ya decidió la dueña
y cuyo patrón se ha aplicado dos veces. **Revalidado: sigue siendo el mejor siguiente.**

### Deuda nueva registrada

| Deuda | Dueña | Hallazgo | Prioridad |
|---|---|---|---|
| **AUTH-MC-INTERMITENTE** | 054 | El arnés `conftest_multicompany` pide un token nuevo en cada llamada; en tandas largas alguna petición recibe `401` y tumba `test_ttl_opcional…` de la Spec 030, que pasa aislada y pasó en dos de las tres tandas completas | media |

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni los seis `float`, ni CLOCK-013, ni E2E-031-RESERVAS, ni la certificación de compras,
ni la validación de respaldo, ni AUTH-MC-INTERMITENTE, ni ninguna de las decisiones
abiertas (D0-06, D0-07, OQ-048, MD-049, camino tras `EXPIRED`).

---

## Tras converger FLOAT-038-C — 2026-09-16

Las **seis fronteras `float`** que quedaban en el borde monetario de Tesorería están
cerradas. Con A, B y C, ese borde ya no tiene ni un `float`.

| Hecho | Detalle |
|---|---|
| Alcance | `opened_amount`, movimiento de caja, transferencia, los dos saldos de conciliación y la base del IGTF |
| Política | La misma de A y B, sin reabrir nada: texto en el contrato, `Decimal` dentro, `Numeric` en la base, 422 al exceso de escala, cero redondeos silenciosos |
| Reglas de signo | **Tres distintas, todas conservadas**: apertura y saldos admiten signo y cero; movimiento, transferencia e IGTF exigen positivo |
| Lo que no cambió | La fórmula del IGTF, el emparejamiento de la conciliación, la dirección de los movimientos y las comprobaciones de la transferencia |
| Migración | Ninguna: las columnas ya eran `Numeric(18,2)`; lo que mentía era la anotación del ORM |
| Evidencia | 39 dirigidas · regresión 1628/0/8 · frontend 372/372 · E2E 87/87 en tres navegadores · 8 mutaciones sin supervivientes · deriva nueva 0 |
| Cobertura declarada | Movimientos de caja y saldos de conciliación **no tienen interfaz**: certificados por API, no por pantalla. Se dice en vez de fingirlo |

`D0-07` sigue abierta: este delta no homologa nada fiscal.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **CLOCK-013** · cinco pruebas de la 013 dependen del reloj local | 013 | no |
| 2 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 3 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 4 | Verificar restauración (DT-11) | 053 | no |

Revalidado tras ver el estado global: **CLOCK-013** sigue siendo el mejor siguiente.
Es barato, no depende de ninguna decisión de dueña y elimina un rojo intermitente que
contamina toda regresión nocturna, lo que abarata cualquier ciclo posterior.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni CLOCK-013, ni E2E-031-RESERVAS, ni la certificación de compras, ni la validación de
respaldo, ni AUTH-MC-INTERMITENTE, ni las deudas de 045/046, ni ninguna decisión abierta
(D0-06, D0-07, OQ-048, MD-049, camino tras `EXPIRED`).

---

## Tras converger CLOCK-013 — 2026-09-17

La deuda de determinismo de las pruebas financieras queda **cerrada**, y con ella el
parche que la ocultaba: la suite de la 013 ya no necesita `TZ=UTC`.

| Hecho | Detalle |
|---|---|
| Defecto | Las pruebas registraban en instante UTC y preguntaban por el día civil **local**. A las 01:24 UTC, en Caracas aún era el día anterior: la tasa empezaba a regir hora y media después del final del día por el que se preguntaba |
| Reproducción | Mismo código y mismos datos: `TZ=UTC` 58/0 · `TZ=America/Caracas` 1 fallo (`MISSING_RATE`) |
| Corrección | Todas las fechas derivan de una referencia fija y pasada; los cinco instantes que quedaban también. **0 lecturas de reloj** en el fichero |
| Producto | **No se toca**: mide en UTC, que es la autoridad de `ADR-D0-001` |
| Evidencia | 62/62 bajo cinco entornos (dos en día civil distinto y uno **sin `TZ`**) · 4 mutaciones sin supervivientes · regresión 1632/0/8 sin forzar zona |
| Observación declarada | `POLICY-CLOCK-LOCAL`: `active_policy` usa el día civil del servidor. Coherente hoy; se registra sin absorberla |

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 2 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 3 | Verificar restauración (DT-11) | 053 | no |
| 4 | Deudas de 045/046 y el ayudante E2E compartido | varias | no |

Revalidado: **E2E-031-RESERVAS** sigue siendo el mejor siguiente. Cierra la última deuda
conocida de la cadena de salida, es acotada y no depende de ninguna decisión de dueña.
Después conviene decidir entre certificar compras —el trabajo de mayor valor— y la
validación de respaldo, que es requisito de operación responsable.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-031-RESERVAS, ni la certificación de compras, ni la Spec 053, ni
AUTH-MC-INTERMITENTE, ni `POLICY-CLOCK-LOCAL`, ni las deudas de 045/046, ni ninguna
decisión abierta (D0-06, D0-07, OQ-048, MD-049, camino tras `EXPIRED`).

---

## Tras converger POLICY-CLOCK-LOCAL — 2026-09-17

La deuda transversal que la auditoría destapó queda **cerrada**. KONTROL ya tiene una
autoridad de fecha de negocio, y está en el código.

| Hecho | Detalle |
|---|---|
| Defecto | `date.today()` en 26 reglas de negocio de 7 módulos, sin una sola conversión de zona en el producto. Con el despliegue en UTC, entre las 20:00 y las 24:00 de Caracas se aplicaba la política, la tasa y la regla fiscal **del día siguiente** |
| Corrección | `app/shared/clock.py` es la autoridad; `business_timezone` la declara; los 26 usos migran; las 2 pantallas que enviaban el día del navegador dejan de hacerlo; `TZ` en contenedor y unidad systemd queda como **cinturón**, no como autoridad |
| Descubierto dentro | La ventana del día seguía siendo la de UTC: una tasa registrada «ahora» caía fuera de su propio día de negocio. Lo encontró el E2E, no un razonamiento |
| Rectificación | La auditoría dijo que la licencia evaluaba en UTC. **No era cierto**: el contrato emite el desfase de Caracas. Se comprobó contra el motor y se fijó con una prueba |
| Evidencia | Matriz de cuatro zonas · política idéntica en las cuatro · 6 mutaciones sin supervivientes · regresión 1656/0/8 **bajo Ámsterdam** · frontend 376/376 · E2E de los flujos tocados 29/29 |
| Cobertura declarada | Las dos pantallas corregidas no tienen E2E que las visite; se dice, no se finge |

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 2 | **E2E-HELPER-EMPRESA-AMBIGUO** · cuatro suites siguen pulsando «Desactivar» | almacén · UoM | no |
| 3 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 4 | Verificar restauración (DT-11) | 053 | no |

Revalidado: **E2E-031-RESERVAS** sigue primero. Pero la ejecución completa de E2E de este
delta deja un dato nuevo que conviene pesar: **E2E-HELPER-EMPRESA-AMBIGUO** tumba 39
pruebas de la suite completa, más que ninguna otra deuda abierta, y es barata. Si el
objetivo es recuperar señal de la suite E2E, conviene antes que la 031.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-031-RESERVAS, ni el ayudante compartido de empresa, ni la certificación de
compras, ni la Spec 053, ni AUTH-MC-INTERMITENTE, ni la retirada de `license_timezone`,
ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, camino tras `EXPIRED`).

---

## Tras converger E2E-HELPER-EMPRESA-AMBIGUO — 2026-09-17

La suite E2E vuelve a tener señal. El ayudante que apagaba la empresa que necesitaba
encendida queda corregido, y **sin tocar una línea de producto**.

| Hecho | Detalle |
|---|---|
| Defecto | `getByRole("button", { name: "Activar" })` casa por subcadena con «Des**activar**». Con la empresa ya activa, el ayudante pulsaba el control contrario y luego esperaba el botón que él mismo había hecho desaparecer |
| Prueba | `ambiguo=1 exacto=0 desactivar=1 nombres=["Desactivar"]`. El producto expone tres nombres exactos y distintos: la ambigüedad era de la prueba |
| Corrección | Ayudante canónico único: nombre exacto, guarda de regresión, idempotencia, compuerta por identificador del producto, fallo explícito y **postcondición verificada** |
| Señal | La suite completa pasa de **164/38** a **185/26** |
| Restantes | 25 del arranque de `n6-multicompany` y 1 del conflicto de semillas. **Ninguno del ayudante.** Ambos registrados como deuda nueva, no absorbidos |
| Cobertura declarada | A→B y B→A **no se cubren**: no hay usuario con dos empresas en esta base, por diseño de la semilla. Se dice, no se finge |

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 2 | **E2E-N6-ARRANQUE** y **E2E-SEED-EMPRESA-UNICA** · 26 pruebas y el conflicto de semillas | 054 | no |
| 3 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 4 | Verificar restauración (DT-11) | 053 | no |

Revalidado: **E2E-031-RESERVAS** sigue primero, como estaba previsto. Dicho eso, las dos
deudas nuevas de QA concentran hoy **26 de los 26 fallos** que quedan en la suite: si el
objetivo es dejar el E2E en verde, van antes que la 031.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-031-RESERVAS, ni el arranque de n6, ni el conflicto de semillas, ni E2E-046-TIPOS,
ni INBOX-045-AISLAMIENTO, ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la
Spec 053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-17 · Tras converger el delta N6-MULTICOMPANY-STARTUP (dueña 054)

`E2E-N6-ARRANQUE` queda **CERRADA**. El mundo multiempresa que las 25 pruebas necesitaban
solo existía en una base SQLite que su propio arranque borraba al empezar, así que contra
la base del E2E ni siquiera abrían sesión. Ahora ese mundo se define una vez
(`qa/n6_world.py`), se siembra en la base que sea (`qa/n6-e2e-seed.py`), la cadena tiene un
orden fijado (`qa/e2e-seed.sh`) y la ejecuta la propia suite (`e2e/global-setup.ts`).
25/25 en Chromium, Firefox y WebKit; 0 ficheros de producto; 0 migraciones.

Al poder correr por primera vez afloraron siete suposiciones que la suite había heredado de
su base privada —el nombre literal de la empresa A y que el tercero marcador cupiera en la
primera página—, corregidas leyendo el mundo en vez de suponerlo.

**Sobre base limpia, la suite completa pasa de 185/27 a 211/1.** Las cifras anteriores
(185/26) se descartan: aquella base tenía `D2` inactiva por un experimento de causalidad y
la medición estaba contaminada.

`E2E-SEED-EMPRESA-UNICA` sigue **OPEN**, ahora con causa raíz y radio medidos: los usuarios
que crean las suites no declaran alcance, y sin alcance el servidor admite todas las
empresas del tenant; de las seis suites que crean usuarios por API solo `order-confirmation`
entra por la interfaz con uno, de ahí el único fallo que queda. Se clasificó
`INDEPENDENT_ROOT_CAUSE` frente al arranque de n6 —ninguna de las dos correcciones arregla
la otra— y por eso **no se absorbió**.

Deuda nueva registrada: **SEED-EMPRESA-CODIGO-NO-UNICO** — `companies` no tiene índice
único sobre `(tenant_id, code)`. Corregirlo es una migración; no se hace aquí.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **E2E-031-RESERVAS** · `GET /inventory/reservations` ignora `source_order_id` | 031 · 023 | no |
| 2 | **E2E-SEED-EMPRESA-UNICA** · el único fallo que queda en la suite | 054 | no |
| 3 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 4 | Verificar restauración (DT-11) | 053 | no |
| 5 | **SEED-EMPRESA-CODIGO-NO-UNICO** · exige migración | por decidir | no |

`READY_FOR_IMPLEMENTATION = 0`. **Ninguno se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-031-RESERVAS, ni E2E-SEED-EMPRESA-UNICA, ni E2E-046-TIPOS, ni INBOX-045-AISLAMIENTO,
ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053, ni el índice único
de `companies`, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-17 · Tras converger el delta E2E-SEED-EMPRESA-UNICA (dueña 054)

`E2E-SEED-EMPRESA-UNICA` queda **CERRADA**. La causa era más precisa de lo que decía su
registro: el fixture **sí** declaraba una empresa, pero en `user_roles` —que es el alcance
del permiso— creyendo que eso limitaba el acceso. La autoridad de acceso es `user_scopes`, y
no tiene ni ruta de API ni pantalla: solo se escribe desde `qa/`. Ahora la escribe
`qa/alcance_de_usuario.py`, autoridad única del repositorio, invocada desde el ayudante
canónico `e2e/helpers/usuario.ts` con el mismo patrón que ya usaba `helpers/planificador.ts`.

Las seis copias literales del verificador de escenario quedan en una. `notifications` se
preserva **sin restricción a propósito** —necesita alcanzar las dos empresas— y hay una
prueba que fija ese contrato para que nadie se lo cambie por descuido.

**Suite global re-medida sobre base limpia con `D1` y `D2` activas: 29 ficheros, 220
pruebas, 219 pasan, 1 falla.** 0 ficheros de producto, 0 migraciones, deriva 21 → 21,
6 mutaciones que mueren.

### Dos hallazgos que no se absorben

- **`INV-MOVTYPE-CARRERA`** (nuevo): `create_movement_type` consulta y luego inserta sin
  proteger la carrera, y la segunda alta simultánea sale como 500 en vez de 409. El helper
  interno del mismo módulo sí lo hace bien. Defecto de producto, registrado.
- **`E2E-031-RESERVAS`**: el único fallo de la global es `putaway.spec.ts:341`, que cuenta
  **todas** las reservas de la empresa porque el endpoint no sabe filtrar por documento.
  Es el mecanismo que esa deuda ya describe; se precisa que también se manifiesta en
  `putaway`, no solo en `picking`.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **E2E-031-RESERVAS** · el filtro `source_order_id` que la API ignora | 031 · 023 | no |
| 2 | **INV-MOVTYPE-CARRERA** · alta concurrente de tipo de movimiento | 022 · 003 | no |
| 3 | Certificar compras (015, 016, 017, 027) | 004-compras | no |
| 4 | Verificar restauración (DT-11) | 053 | no |
| 5 | **SEED-EMPRESA-CODIGO-NO-UNICO** · exige migración | por decidir | no |

**Candidata siguiente: `E2E-031-RESERVAS`**, por la regla del propio encargo: `E2E-046-TIPOS`
no se reprodujo —con el antivirus disponible las dos suites de documentos van 12/12—, así que
pasa el turno a la 031, que además acaba de manifestarse.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni E2E-031-RESERVAS, ni INV-MOVTYPE-CARRERA, ni E2E-046-TIPOS, ni INBOX-045-AISLAMIENTO, ni
AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053, ni el índice único de
`companies`, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-17 · Tras converger el delta E2E-031-RESERVAS (dueña 054)

`E2E-031-RESERVAS` queda **CERRADA**, y con ella **la señal global del E2E queda
restaurada: 30 ficheros, 224 pruebas, 224 pasan, 0 fallan.**

La causa no era del producto. `GET /inventory/reservations` cumple su contrato —«reservas
activas/históricas», acotado a la empresa, con `status` y `product_id` como filtros—; lo
que fallaba era la aserción: `putaway` y `picking` afirmaban sobre el **tamaño** de un
conjunto compartido que crece mientras la suite corre (medido: de 330 a 369 reservas en un
mismo ciclo). `picking` además enviaba `?source_order_id=`, que el servidor no declara y
por tanto ignora en silencio, así que creía filtrar y contaba la empresa entera.

El arreglo es de pruebas: un ayudante canónico de identidad y cuatro casos que fijan la
diferencia entre «hay las mismas reservas» y «la mía sigue siendo la que era». Las
aserciones no se debilitan: donde había una comparación de tamaños hay cuatro
comprobaciones sobre la reserva concreta.

**Conviene no confundir el verde con la prueba.** Este fallo era intermitente y ya hubo
ejecuciones verdes con el defecto dentro; de hecho, en este mismo ciclo la suite pasó
220/220 antes de tocar nada. Lo que demuestra el cierre es que la premisa frágil ya no
está y que cuatro mutaciones mueren si vuelve.

### Deudas nuevas registradas, no absorbidas

- **`API-QUERY-SILENCIOSA`** (dueña 023): el endpoint acepta sin protestar parámetros de
  consulta que no declara. Cambiarlo es semántica pública.
- **`E2E-SIN-TYPECHECK`** (dueña 054): `e2e/` no entra en el typecheck del proyecto.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **INV-MOVTYPE-CARRERA** · alta concurrente devuelve 500 en vez de 409 | 022 · 003 | no |
| 2 | **SEED-EMPRESA-CODIGO-NO-UNICO** · exige migración | por decidir | no |
| 3 | **API-QUERY-SILENCIOSA** | 023 | no |
| 4 | **E2E-SIN-TYPECHECK** | 054 | no |
| 5 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 6 | Verificar restauración (DT-11) · SPEC053 | 053 | no |

**Candidata siguiente: `INV-MOVTYPE-CARRERA`**, por ser defecto real de producto con un
HTTP 500 bajo concurrencia, frente a deudas de QA o de esquema.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni INV-MOVTYPE-CARRERA, ni SEED-EMPRESA-CODIGO-NO-UNICO, ni API-QUERY-SILENCIOSA, ni
E2E-SIN-TYPECHECK, ni E2E-046-TIPOS —que **sigue OPEN** aunque no se haya reproducido—, ni
INBOX-045-AISLAMIENTO, ni la certificación de compras, ni la Spec 053, ni ninguna decisión
abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-18 · Tras converger el delta INV-MOVTYPE-CARRERA (dueña 023)

`INV-MOVTYPE-CARRERA` queda **CERRADA**. Era un defecto de producto real: el alta explícita
de un tipo de movimiento consultaba y luego insertaba sin nada entre medias, así que dos
altas simultáneas del mismo código pasaban ambas la consulta y la segunda subía como **500**
—`IntegrityError` crudo, `pgcode=23505`, restricción `uq_movement_types_company_code`— en
vez del `409 MOVEMENT_TYPE_DUPLICATE` que el camino secuencial ya contestaba.

Lo llamativo es que el mismo módulo ya sabía hacerlo: `_get_movement_type_by_code` resolvía
la misma carrera para la auto-configuración, con savepoint y captura precisa, y su comentario
describía el caso. Faltaba en el otro camino. La creación baja al servicio —la ruta confirma
la transacción y una carrera forzada exige que quien inserta no confirme— y se queda con el
patrón del repositorio.

**No hubo migración**: la restricción existe y protege la identidad por empresa. La base
nunca creó dos filas; lo único que faltaba era traducir la colisión.

8 pruebas nuevas, todas sobre PostgreSQL real y con la carrera **forzada** por
`tests/concurrency.py::carrera`, que falla si la carrera no llega a ocurrir. 6 mutaciones,
6 muertas. Regresión completa de backend **1672 · 0 fallos**; deriva 21 → 21.

### Deuda nueva escalada, no resuelta

**`MOVTYPE-GLOBAL-SIN-UNICIDAD`** — un tipo «de toda la instalación» lleva `company_id`
nulo, y en PostgreSQL los nulos no colisionan entre sí: medido, dos altas concurrentes
dejan **dos filas**. Protegerlo exige un índice único parcial, es decir una migración; pero
la Spec no declara unicidad del código —solo dice «company_id/global»—, y decidir si dos
tipos globales pueden compartir código es una decisión de identidad de negocio, no una
inferencia. `MATERIAL_DECISION_REQUIRED`, dueña 023.

### E2E

224 · 223 · 1. El fallo es `documents:309` = **E2E-046-TIPOS**, reproducida: la base tiene
exactamente 10 tipos documentales y la tabla pagina de diez en diez, así que no hay «Página
siguiente» y la espera agota la prueba. No es regresión de esta delta y **no se cierra
aquí**.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **SEED-EMPRESA-CODIGO-NO-UNICO** · `companies` sin único sobre `(tenant_id, code)` | por decidir | no |
| 2 | **MOVTYPE-GLOBAL-SIN-UNICIDAD** · exige decisión de identidad antes que código | 023 | no |
| 3 | **E2E-046-TIPOS** · reproducida hoy | 046 | no |
| 4 | **API-QUERY-SILENCIOSA** | 023 | no |
| 5 | **E2E-SIN-TYPECHECK** | 054 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**Candidata siguiente: `SEED-EMPRESA-CODIGO-NO-UNICO`**, como estaba previsto. Conviene
notar que se parece a la que se acaba de cerrar —una identidad sin garantía en la base— y
que, a diferencia de ella, sí exigirá migración y auditoría de duplicados.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni SEED-EMPRESA-CODIGO-NO-UNICO, ni MOVTYPE-GLOBAL-SIN-UNICIDAD, ni E2E-046-TIPOS, ni
API-QUERY-SILENCIOSA, ni E2E-SIN-TYPECHECK, ni INBOX-045-AISLAMIENTO, ni ORPHAN-046-SINGLE,
ni IDEM-046-TRUNC, ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053,
ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-18 · Tras converger el delta E2E-046-TIPOS (dueña 054)

`E2E-046-TIPOS` queda **CERRADA**, y con ella **la suite E2E global vuelve a 224 · 224 · 0**.

La causa no era del producto. `DataTable` solo pinta el paginador con más de diez
registros, y eso está escrito tres veces: en el componente, en `Pagination.tsx` y en
`FR-001-065` de la Spec 001. La prueba de tipos documentales daba por hecho que «Página
siguiente» siempre está y esperaba por ella con `isEnabled()`, así que cuando la base llegó
a **exactamente diez** la espera agotó la prueba. No era una aserción que fallara: era una
espera que no terminaba, y por eso el síntoma era un *timeout* y no un «esperaba X, había Y».

Dato que conviene retener: **ninguna semilla fija esos diez tipos**. Los crean las propias
suites, así que el número depende de cuántas veces se haya ejecutado el E2E; la prueba
llevaba una bomba de relojería, no un fallo estable.

El arreglo usa la palanca que el producto ofrece justo cuando hace falta —el selector de
tamaño de página, que existe exactamente cuando hay más de una página— y el borde se cubre
donde vive el contrato: `DataTable.test.tsx`, con 10 y con 11. Verificado en los tres
estados (9, 10 y 11) ejecutando tres veces seguidas.

### Un hallazgo que cambia la cola: la rama no compila

**`BUILD-TSC-TESORERIA`** — `npm run build` encadena `tsc -b && vite build`, y `tsc -b`
sale con **código 2** por un parámetro sin usar en `importes-float-c.test.tsx`. Entró en
`e43cf48` (FLOAT-038-C) y no se detectó porque aquellos ciclos ejecutaron
`tsc --noEmit -p tsconfig.json`: ese `tsconfig.json` es de tipo *solution* —`files: []` más
`references`— y **sin `-b` no compila nada, así que sale limpio siempre**. La orden correcta
es la que el propio `package.json` usa en `typecheck` y en `build`.

Es la segunda afirmación vacía sobre `tsc` en esta serie de deltas; la primera fue el
directorio `e2e/`, ya corregida en su documento. Las dos comparten raíz: comprobar con una
orden que no comprueba.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **BUILD-TSC-TESORERIA** · la rama no compila | 038 | no |
| 2 | **SEED-EMPRESA-CODIGO-NO-UNICO** · `companies` sin único sobre `(tenant_id, code)` | por decidir | no |
| 3 | **MOVTYPE-GLOBAL-SIN-UNICIDAD** · exige decisión de identidad | 023 | no |
| 4 | **API-QUERY-SILENCIOSA** | 023 | no |
| 5 | **E2E-SIN-TYPECHECK** | 054 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**Candidata siguiente: `BUILD-TSC-TESORERIA`.** Pasa por delante de todo lo demás por una
razón simple: una rama que no compila es peor que cualquier deuda de identidad o de QA, y
su corrección es pequeña y acotada. Conviene que ese ciclo arregle también el hábito —usar
`tsc -b`— y no solo el símbolo sin usar.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni BUILD-TSC-TESORERIA, ni SEED-EMPRESA-CODIGO-NO-UNICO, ni MOVTYPE-GLOBAL-SIN-UNICIDAD, ni
API-QUERY-SILENCIOSA, ni E2E-SIN-TYPECHECK, ni INBOX-045-AISLAMIENTO, ni ORPHAN-046-SINGLE,
ni IDEM-046-TRUNC, ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053,
ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-19 · Tras converger el delta BUILD-TSC-TESORERIA (dueña 054, apoyo 038)

`BUILD-TSC-TESORERIA` queda **CERRADA**. `npm run build` vuelve a salir en 0 y el
empaquetado se ejecuta.

El defecto de compilación era un parámetro sin usar; se corrige con un carácter, según la
convención del propio repositorio (`_ruta`). Lo que importa de este ciclo es lo otro.

**La orden que se venía usando como evidencia de typecheck no comprobaba nada.**
`tsc --noEmit -p tsconfig.json` sobre una raíz que es un *solution config* —`files: []` más
`references`— recorre **cero ficheros** y termina en 0. Medido: cero frente a los 997 que
recorre el proyecto real. Y demostrado con un control negativo que no deja lugar a dudas:
con `const x: number = "no soy un número"` metido en `src/lib/format.ts`, esa orden sigue
diciendo **exit 0 y cero líneas**, mientras `npm run typecheck` y `npm run build` dicen
**exit 2** y nombran el error.

Conviene decir dónde estaba el fallo y dónde no. **Los gates del repositorio eran
correctos**: `build = tsc -b && vite build` y `typecheck = tsc -b --noEmit` existían desde
antes, y la guía viva ya mandaba `npx tsc -b`. Lo que falló fue no ejecutarlos y sustituirlos
por una orden inventada. Por eso este ciclo **no cambia ninguna configuración**: añade una
guarda —`src/tests/typecheck-gate.test.ts`, seis invariantes— que se rompe si el gate deja
de recorrer las referencias, si se apaga la severidad que detectó el defecto, si las
pruebas salen del grafo o si se pierde una referencia.

Se corrigen además dos afirmaciones escritas en deltas anteriores de esta serie: una daba
el `tsc` por limpio cuando la rama ya no compilaba, y otra describía mal el alcance de la
orden. La evidencia falsa no se corrige sola.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **SEED-EMPRESA-CODIGO-NO-UNICO** · `companies` sin único sobre `(tenant_id, code)` | por decidir | no |
| 2 | **API-QUERY-SILENCIOSA** · el servidor acepta parámetros que no declara | 023 | no |
| 3 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 4 | **MOVTYPE-GLOBAL-SIN-UNICIDAD** · exige decisión de identidad | 023 | no |
| 5 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 6 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**Candidata siguiente: `SEED-EMPRESA-CODIGO-NO-UNICO`**, como estaba previsto antes de que
el build roto se colara por delante.

Vale la pena notar el parecido entre las tres primeras: las tres son **una comprobación que
no comprueba**. Un índice único que no cubre el caso, un parámetro que el servidor ignora en
silencio, y un directorio que ningún typecheck mira. La deuda que se acaba de cerrar era la
cuarta de esa familia.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni SEED-EMPRESA-CODIGO-NO-UNICO, ni API-QUERY-SILENCIOSA, ni E2E-SIN-TYPECHECK, ni
MOVTYPE-GLOBAL-SIN-UNICIDAD, ni INBOX-045-AISLAMIENTO, ni ORPHAN-046-SINGLE, ni
IDEM-046-TRUNC, ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053, ni
ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-19 · `SEED-EMPRESA-CODIGO-NO-UNICO` se detiene en clarify

**No converge, y no por falta de trabajo: por falta de una decisión.**

La deuda decía que `companies` carece de un índice único sobre `(tenant_id, code)` y que
«la identidad de empresa descansa en la disciplina de cada guion, no en el motor». La
primera mitad es cierta. La segunda era una suposición mía, escrita durante N6, y al
medirla no se sostiene: **esa identidad no existe en ninguna parte del producto**.

Lo que se midió:

- ninguna Spec declara unicidad del código de empresa —`data-model.md:31` enumera campos y
  ya; el contrato de la ruta dice «Listar/crear empresa»—;
- el ORM tampoco la declara, y la migración `0001` nunca la creó: no se perdió, nunca estuvo;
- `create_company` **no comprueba duplicados**: dos altas con el mismo código responden
  **200 y 200**, y quedan dos empresas;
- tampoco normaliza: `sonda` y ` SONDA ` se guardan literalmente, como códigos distintos;
- y el producto **nunca** resuelve una empresa por código: cero apariciones de
  `Company.code ==` en todo `app/`. La empresa viaja por `id`, y un centenar de tablas la
  referencian por `id`.

Hoy, en KONTROL, el código de empresa es una **etiqueta**, no un identificador.

El patrón de los hermanos —`uq_warehouses_company_code` y compañía— empieza en el almacén:
`Tenant`, `Company` y `Branch` no lo tienen. Eso admite dos lecturas, omisión o decisión, y
la evidencia no distingue.

### Por qué no se implementó igualmente

Porque añadir `UNIQUE(tenant_id, code)` no es completar algo a medias: es **crear una regla
nueva**. Quien hoy tenga dos empresas con el mismo código está dentro de lo permitido, y
tras una actualización dejaría de estarlo, sin que ninguna Spec se lo hubiera dicho. Eso es
una decisión de negocio, no una inferencia de ingeniería.

**Pregunta escalada:** ¿el código de empresa identifica dentro de su tenant, o etiqueta?

Si identifica, el análisis deja listo el camino: `uq_companies_tenant_code`, `tenant_id` es
`NOT NULL` —así que basta una unicidad normal—, 0 duplicados en este entorno, y la lista de
lo que arrastra: contrato de duplicado en la API (hoy inexistente, y sin él la colisión
saldría como 500), mayúsculas, espacios, y qué pasa con una empresa inactiva que ocupa un
código.

Si etiqueta, la deuda se cierra como no aplicable y basta con dejarlo escrito.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **API-QUERY-SILENCIOSA** · el servidor acepta parámetros que no declara | 023 | no |
| 2 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 3 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 4 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner** (no son cola de implementación):
`SEED-EMPRESA-CODIGO-NO-UNICO` y `MOVTYPE-GLOBAL-SIN-UNICIDAD`. Son **la misma pregunta en
dos tablas**: si un código identifica o etiqueta. Conviene responderlas juntas.

**Candidata siguiente: `API-QUERY-SILENCIOSA`**, la primera que no depende de una decisión
pendiente.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni API-QUERY-SILENCIOSA, ni E2E-SIN-TYPECHECK, ni SEED-EMPRESA-CODIGO-NO-UNICO, ni
MOVTYPE-GLOBAL-SIN-UNICIDAD, ni INBOX-045-AISLAMIENTO, ni ORPHAN-046-SINGLE, ni
IDEM-046-TRUNC, ni AUTH-MC-INTERMITENTE, ni la certificación de compras, ni la Spec 053, ni
ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

---

## 2026-09-20 · `API-QUERY-SILENCIOSA` se detiene en clarify

**No converge: no hay contrato que aplicar, y cambiarlo tiene un precio medido.**

La pregunta era si un endpoint debe rechazar los parámetros de consulta que no declara. Se
buscó la respuesta donde tenía que estar —Constitución, los quince ADR de fundación,
`api-contracts.md`, las Specs 023, 030, 031, 048 y 054, y el propio OpenAPI— y **no existe**.
Lo que sí existe es estrictez **de cuerpo**: `extra="forbid"` en dieciséis modelos, con su
motivo escrito —«`company_id` u otro campo ajeno responde 422, nunca se lee»— pero aplicada
a mano, sin prueba que la fije y sin nada equivalente para la consulta.

El comportamiento actual es uniforme: diez endpoints de siete módulos, y en todos la
respuesta con parámetro desconocido es idéntica a la respuesta sin él. Eso no es una
decisión de KONTROL: es lo que hace el framework.

**Coste de cambiarlo, medido, no estimado.** Con una sonda estricta temporal —retirada, y
`main.py` verificado idéntico con `cmp`— la suite E2E pasa de 224/224 a **197 pasan y 27
fallan**, en ocho ficheros. Rechazar sería un cambio incompatible, no un endurecimiento
inocuo. *(Una primera medición dio 112 fallos y se descartó: Vite no estaba levantado.)*

### Lo que el silencio estaba escondiendo

Cruzando todas las llamadas con query string del frontend contra el OpenAPI vivo aparecen
**diez llamadas de producto** que envían parámetros no declarados. Tres de ellas son un
defecto visible para el usuario: **`EmpresasPage`, `AuditoriaPage` y `ExistenciasPage` tienen
una caja de búsqueda que no busca**. Envían `?q=` a endpoints que no declaran `q`, el
servidor responde 200 y devuelve la lista entera.

```
/maestros/terceros?q=ZZZ-NO-EXISTE        -> 0 terceros    ← el filtro existe
/organization/companies?q=ZZZ-NO-EXISTE   -> 1 empresa     ← el filtro no existe
```

Y no es una libertad del producto: el contrato de listados de la propia Fundación dice
«Listados con `q`, `status`, `sort`, `page`, `page_size`», y `FR-001-065` exige «búsqueda
general». Queda registrado aparte como **`UI-BUSQUEDA-MUERTA`**, con tres dueñas distintas,
y **no se absorbe**: existe con independencia de cómo se decida la política.

Las otras siete envían `company_id` donde la empresa ya la decide la cabecera validada.
Inocuo hoy, pero la asimetría merece quedar escrita: el mismo campo está prohibido en el
cuerpo con un 422 y aceptado en silencio en la consulta. Registrado como
**`API-COMPANY-ID-EN-CONSULTA`**.

**Pregunta escalada:** ¿rechazar los parámetros no declarados, o ignorarlos?

Si se rechaza, hay que arreglar antes esas diez llamadas, decidir el alcance —un endpoint,
un módulo o toda la API— y contar con proxies e integraciones que añaden parámetros por su
cuenta. Si se ignora, conviene escribirlo en el contrato y fijarlo con una prueba, para que
deje de ser «lo que hace el framework» y pase a ser una decisión.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **UI-BUSQUEDA-MUERTA** · tres buscadores que no buscan | 001/007 · 023 · 012 | no |
| 2 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 3 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 4 | SPEC053 · verificar restauración (DT-11) | 053 | no |
| 5 | **API-COMPANY-ID-EN-CONSULTA** · menor | 001 | no |

**A la espera de decisión del owner** (no son cola de implementación):
`API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO` y `MOVTYPE-GLOBAL-SIN-UNICIDAD`.

**Candidata siguiente: `UI-BUSQUEDA-MUERTA`.** Pasa delante porque es lo único de esta
tanda que un usuario nota: escribe en un buscador y no ocurre nada. Y porque, a diferencia
de las tres en espera, su contrato **sí** está escrito.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni UI-BUSQUEDA-MUERTA, ni API-COMPANY-ID-EN-CONSULTA, ni API-QUERY-SILENCIOSA, ni
E2E-SIN-TYPECHECK, ni SEED-EMPRESA-CODIGO-NO-UNICO, ni MOVTYPE-GLOBAL-SIN-UNICIDAD, ni
INBOX-045-AISLAMIENTO, ni ORPHAN-046-SINGLE, ni IDEM-046-TRUNC, ni AUTH-MC-INTERMITENTE, ni
la certificación de compras, ni la Spec 053, ni ninguna decisión abierta (D0-06, D0-07,
OQ-048, MD-049, `EXPIRED`).

## 2026-09-24 · `UI-BUSQUEDA-MUERTA` se detiene en clarify, con una pantalla ya decidida

Las tres cajas de búsqueda están muertas, y ahora está medido en los dos sitios donde se
puede medir. Contra la API, con un término que no existe: `companies` 1→1,
`audit/events` 18→18, `balances` 0→0, frente a `terceros` 1→0, que sí filtra. Y en un
navegador real, entrando por los enlaces del menú: el usuario escribe, la pantalla llama
al servidor, el servidor responde 200 con la lista entera, y no pasa nada.

Que la búsqueda **exista** no era discutible —`FR-001-065`, `api-contracts.md` y DOC-08
§10 la exigen—, y por eso esta delta no se parecía a las tres que esperan decisión: aquí
sí había contrato. Lo que no había, y no lo vimos hasta buscarlo, es **sobre qué campos**
se busca. DOC-08 §10 describe la caja —una por pantalla, debounce, backend— y no enumera
columnas. Solo un FR nombra campos, y solo para su módulo: `FR-002-042`, «RIF/nombre/
código».

Así que la pregunta pasó a ser si se podía deducir. Hay dos buscadores vivos —terceros y
kardex— y de los dos sale la misma regla: `q` busca los **nombres** y los
**identificadores de negocio** propios de la entidad que el listado ya publica, y deja
fuera lo que ya tiene filtro dedicado, los estados, las cantidades y las fechas. No es una
excusa: aplicada a ciegas reproduce exactamente los dos conjuntos implementados, y el
placeholder de terceros se la declara al usuario palabra por palabra.

Aplicada a las tres pantallas, la regla decide una y se rompe en dos.

**Empresas queda decidida.** `Company` publica código, dos nombres y RIF: `q` busca
`code`, `legal_name`, `trade_name`, `rif`. Es la misma terna que `FR-002-042` ya decidió
para terceros, sobre una entidad de la misma forma.

**Auditoría, no.** `AuditEvent` no tiene nombre, y `action`, `entity_type` y `entity_id`
ya tienen filtro dedicado, así que la regla los excluye igual que excluye el estado en
terceros. Queda `request_id` y un borde que ningún precedente cubre. Pero el problema real
apareció debajo: **el listado no filtra por tenant**. Medido: de 20 eventos, uno es de
`DEMO2` y se le devuelve a un administrador de `DEMO`. Poner `q` ahí sería filtrar un
conjunto que antes de `q` ya está mal.

**Existencias, tampoco, y de forma más terminante:** la regla devuelve el **conjunto
vacío**. El listado no publica ni una columna de texto —todo son UUID con filtro propio,
un enum con filtro propio, tres cantidades y una fecha—. Y su caja promete «Buscar por
producto…» mientras la columna «Producto» enseña un UUID crudo, porque el texto del
producto está dos saltos más allá: `balances → products → catalog_items`. Cumplir la
promesa exige decidir que la búsqueda general alcanza una entidad relacionada y publicar
la identidad del producto en la fila, que es cambiar el payload de un listado P0. Y el
contrato del módulo, `FR-003-012`, describe esta consulta por filtros, no por texto.

### Lo que la caja muerta estaba tapando

La pantalla de auditoría **no ha mostrado nunca una fila**. El servidor devuelve un sobre
paginado y la pantalla lo trata como un array; `tsc` no puede verlo porque `apiFetch` es
genérico y quien llama afirma el tipo, y ningún E2E visita esa ruta. La columna «Fecha»
lee `created_at`, que el servidor no publica. Y hay dos entradas «Auditoría» en el menú,
con dos contratos distintos.

Es otra vez lo mismo de esta tanda: un control que no controla. Un índice único que no
cubre su caso, un parámetro que el servidor ignora, un directorio que ningún typecheck
lee, y ahora una tabla que nunca pinta y una caja que nunca busca.

### Por qué no se implementó Empresas, estando decidida

Porque el gate detiene el ciclo con `MATERIAL OQ > 0`, y un gate que se salta cuando
conviene no es un gate. Queda preparada para una sola pasada en cuanto se autorice: campos
resueltos, `q` después del filtro de empresas accesibles y antes de cualquier recorte,
placeholder que nombre los campos como en terceros, y el sobre paginado que hoy le falta.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **AUDIT-EVENTS-SIN-TENANT** · fuga entre inquilinos, medida | 001 | no |
| 2 | **UI-BUSQUEDA-MUERTA · Empresas** · decidida, lista | 001/007 | no |
| 3 | **AUDITORIA-SOBRE-VS-ARRAY** · la tabla nunca pinta | 012 | no |
| 4 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 5 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 6 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner** (no son cola de implementación):
`API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`, `MOVTYPE-GLOBAL-SIN-UNICIDAD` y,
desde hoy, **`UI-BUSQUEDA-MUERTA` en Auditoría y en Existencias**.

**Candidata siguiente: `AUDIT-EVENTS-SIN-TENANT`.** Pasa delante de todo lo demás porque
es la única de la lista que enseña datos de un inquilino a otro, porque `FR-001-032` y
`FR-001-033` ya la decidieron —no hay nada que clarificar— y porque bloquea la búsqueda de
esa misma pantalla.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni implementar `q` en ninguna de las tres pantallas —tampoco en Empresas, aunque esté
decidida—, ni corregir el alcance de auditoría, ni el sobre de `AuditoriaPage`, ni
`created_at`, ni la duplicidad del menú, ni `API-QUERY-SILENCIOSA`, ni
`API-COMPANY-ID-EN-CONSULTA`, ni `E2E-SIN-TYPECHECK`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`,
ni `MOVTYPE-GLOBAL-SIN-UNICIDAD`, ni `INBOX-045-AISLAMIENTO`, ni `ORPHAN-046-SINGLE`, ni
`IDEM-046-TRUNC`, ni `AUTH-MC-INTERMITENTE`, ni la certificación de compras, ni la Spec
053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-09-30 · Tras converger el delta AUDIT-EVENTS-SIN-TENANT (dueña 001, contrato ARCH-MC-001, apoyo 012)

La fuga estaba donde el análisis del 24 la había dejado: `GET /audit/events` hacía
`select(AuditEvent)` sin `where` de tenant, exigía `audit:view` y **descartaba** el usuario
que esa misma dependencia le devolvía. La base que vio el hallazgo (`keu`, 20 eventos) ya
no existe —vivía en `/tmp`—, así que la medida se rehízo desde cero sobre PostgreSQL real:
sembrada con `qa/e2e-seed.sh`, un login en DEMO y otro en DEMO2, y el administrador de DEMO
recibe **2 eventos de DEMO2**. Y para no depender de eventos accidentales, dos eventos
**de contenido idéntico** —misma acción, misma entidad, mismo `request_id`—, uno por tenant:
visibles en las dos direcciones, `total` global. Lo único que los distinguía era el tenant,
y eso era lo único que no se miraba.

El encargo prohibía escribir el `where` sin demostrar antes que había algo que filtrar. Lo
había, y de sobra: `tenant_id` existe en `audit_events` desde `0001`, con índice, y con
clave foránea desde `0034`; ORM y PostgreSQL dicen lo mismo (N10 verde); las dos únicas
migraciones que tocan la tabla no hacen backfill porque nunca hizo falta; los **22**
escritores pasan por una sola fábrica, `record_audit`, y todos llevan el tenant —del usuario
autenticado, o deducido de la empresa validada por `CompanyContext`—; el único actor de
fondo, `SISTEMA` de notificaciones, escribe con empresa explícita; y los eventos de
instalación (licencia, homologación) tienen tablas propias, no `AuditEvent`. Filas con tenant
nulo: **0**. Eventos globales de auditoría: **no existen contractualmente**. Migración: 0.
Backfill: 0.

La pregunta que podía parar el ciclo —qué ve un usuario, dentro de su tenant, de las
empresas en las que no opera— ya la había contestado ARCH-MC-001 antes de que nadie la
hiciera: la matriz de alcance por endpoint clasifica `/audit/events` como
`TENANT/INSTALLATION`, empresa «no aplica», y la guarda N10 lo fija en código («tenant: la
bitácora se consulta por tenant»). La vista **por empresa** ya existe y es otra:
`/reporting/audit/timeline`, `COMPANY_SCOPE`, que valida la cabecera y responde 404 a una
empresa ajena. Así que el listado enseña el tenant entero a quien tiene `audit:view`, y no
se acota «indebidamente a la empresa actual». MATERIAL OQ = 0.

El fix es una cláusula, en el sitio donde nace el conjunto: `WHERE tenant_id =
user.tenant_id` antes de los filtros, del recuento y de la paginación. Ni parámetro nuevo,
ni cabecera, ni excepción para `admin` —no existe rol cross-tenant en KONTROL—, ni
`IS NULL OR` que regale a todos lo que no es de nadie. Once pruebas hostiles con dos
tenants; siete mutantes —quitar el filtro, filtrar en Python tras paginar, `IS NULL OR`,
la empresa como sustituto, un rol que exime, el tenant por consulta, `total` global—, los
siete muertos. El sello de integridad de las filas anteriores al fix es idéntico después:
nada se borró, nada se reasignó. Contrato público sin cambio de forma; frontend sin tocar.

### Lo que este delta enseñó del entorno

El `.venv` del backend y `node_modules/.bin` son enlaces simbólicos **aplanados** por la
copia del árbol, y el `python3.11` al que apuntaban ya no existe. Se reconstruyó fuera del
repositorio desde `requirements.lock` —que no trae `reportlab` ni `python-magic`, que el
entorno antiguo sí tenía—, `clamscan` no está instalado y 13 ficheros de prueba invocan
`.venv/bin/alembic` por ruta fija. Nada de eso es del producto, y todo queda registrado
(`LOCK-SIN-REPORTLAB-MAGIC`, `TEST-MIGRACIONES-VENV-FIJO`), con los fallos atribuidos: las
mismas familias fallan igual con el `api.py` original y con el corregido.

### Hallazgos nuevos, registrados y no absorbidos

`AUDIT-DETAIL-NO-IMPLEMENTADO` (el contrato declara `/audit/events/{id}`; el código no lo
tiene), `AUDIT-TOTAL-MATERIALIZA` (`total` carga todas las filas del alcance en lugar de
contar), `E2E-APPROVALS-LIMIT-NO-DECLARADO` (`?limit=200` a un endpoint que no lo declara).
De `UI-BUSQUEDA-MUERTA` en Auditoría queda solo la mitad de OQ-1: **sobre qué campos**; el
conjunto ya es el del tenant.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **UI-BUSQUEDA-MUERTA · Empresas** · decidida, lista | 001/007 | no |
| 2 | **AUDITORIA-SOBRE-VS-ARRAY** · la tabla nunca pinta | 012 | no |
| 3 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 4 | **LOCK-SIN-REPORTLAB-MAGIC** · el lock no reconstruye el entorno | 001/052 | no |
| 5 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 6 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner**: `API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`,
`MOVTYPE-GLOBAL-SIN-UNICIDAD`, `UI-BUSQUEDA-MUERTA` en Auditoría (campos) y en Existencias.

**Candidata siguiente: `UI-BUSQUEDA-MUERTA · Empresas`.** Es la única de la cola con los
campos decididos (`code, legal_name, trade_name, rif`, la terna de `FR-002-042`), ya no
comparte ciclo con una pregunta material, y arrastra `EMPRESAS-SIN-SOBRE`, que le hace
falta para paginar bien lo que filtre.

`READY_FOR_IMPLEMENTATION = 1` (Empresas). **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni implementar `q` en ninguna pantalla —tampoco en Empresas, aunque esté decidida—, ni el
sobre de `AuditoriaPage`, ni `created_at`, ni la duplicidad del menú, ni el detalle de
auditoría, ni `API-QUERY-SILENCIOSA`, ni `API-COMPANY-ID-EN-CONSULTA`, ni
`E2E-SIN-TYPECHECK`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`, ni `MOVTYPE-GLOBAL-SIN-UNICIDAD`,
ni `INBOX-045-AISLAMIENTO`, ni `ORPHAN-046-SINGLE`, ni `IDEM-046-TRUNC`, ni
`AUTH-MC-INTERMITENTE`, ni tocar el lockfile, ni la certificación de compras, ni la Spec
053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-09-30 · Tras converger el delta EMPRESAS-BUSQUEDA-Q (dueña 001, apoyo 012)

Era la única de la cola con todo decidido, y por eso ha sido corta. La caja de Empresas
enviaba `q`; el servidor no lo declaraba y devolvía la lista entera con 200. Medido otra
vez antes de tocar nada, en la API y en Chromium, entrando por el menú: `uab` con dos
empresas, `uc` con una, y cualquier término —inexistente, la razón social de la segunda,
el RIF, el código— devolvía las mismas filas. `B == A`.

Los campos venían decididos de `aae7cd2` —`code`, `legal_name`, `trade_name`, `rif`, la
terna de `FR-002-042` con el segundo nombre que la entidad tiene— y no se reabrieron. La
semántica tampoco se inventó: se leyó del precedente vivo de terceros, que es el mismo
patrón en los siete `q` del producto —`ilike` con `%q%` sobre cada campo en OR, sin `trim`,
sin escape de comodines, `q` vacía sin filtro—. El backend ya acotaba por tenant en SQL y
por `accessible_company_ids` después; el predicado entra entre los dos. Un parámetro y
cuatro `ilike`: ficheros de producto, 1.

El frontend no se tocó porque ya hacía todo lo que debía: caja, `q` en la petición, `q`
en la `queryKey`. Lo que no existe en este endpoint —`total`, `page`, recorte— tampoco
se inventó: `EMPRESAS-SIN-SOBRE` sigue abierta y el encargo fijaba «no cambiar la forma
pública salvo declarar `q`». Lo exigible, y exigido, es que la respuesta sea el conjunto
que coincide, entero y en el orden de siempre.

Diecisiete pruebas backend con la misma `ALFA-OBJETIVO` en dos tenants y un usuario
limitado a D1; tres de página con un servidor de mentira que busca de verdad, para que la
pantalla no pueda fingirlo; cinco E2E sobre el mundo sembrado. Nueve mutantes: siete
muertos en SQLite, el de `like` por `ilike` muere en PostgreSQL —SQLite no distingue
mayúsculas en `LIKE`, así que ahí no podía morir— y el de «la búsqueda sustituye al tenant»
es equivalente, porque la segunda capa lo tapa. Vitest 388/388, `tsc -b` y ESLint limpios,
`vite build` correcto, E2E de la pantalla 22/22.

### Lo que este delta enseñó del entorno

`make_engine` crea un schema de PostgreSQL por módulo de prueba y nunca lo suelta: tres
corridas completas dejaron la base de pruebas en 6,8 GB, llenaron el `tmpfs` de 7,6 GB
donde vive el clúster de QA y PostgreSQL cayó a mitad de la cuarta. Se soltó la base, se
recreó y la regresión se repitió limpia. Registrado como `TEST-SCHEMAS-PG-SIN-LIMPIEZA`.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **AUDITORIA-SOBRE-VS-ARRAY** · la tabla nunca pinta | 012 | no |
| 2 | **EMPRESAS-SIN-SOBRE** · el listado no pagina en el servidor | 001/007 | no |
| 3 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 4 | **LOCK-SIN-REPORTLAB-MAGIC** · el lock no reconstruye el entorno | 001/052 | no |
| 5 | **TEST-SCHEMAS-PG-SIN-LIMPIEZA** · la suite llena el disco | 054/052 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner**: `API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`,
`MOVTYPE-GLOBAL-SIN-UNICIDAD`, `UI-BUSQUEDA-MUERTA` en Auditoría (campos) y en Existencias.

**Candidata siguiente: `AUDITORIA-SOBRE-VS-ARRAY`.** Con el listado ya acotado por tenant,
la pantalla de auditoría es la única del producto que nunca ha mostrado una fila; el
defecto es de una línea de tipo y una de datos, arrastra `AUDITORIA-CREATED-AT`, y no
espera ninguna decisión.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni `q` en Auditoría ni en Existencias, ni el sobre de `AuditoriaPage`, ni `created_at`, ni
`EMPRESAS-SIN-SOBRE`, ni el placeholder de Empresas, ni una política de escape de
comodines, ni `API-QUERY-SILENCIOSA`, ni `API-COMPANY-ID-EN-CONSULTA`, ni
`E2E-SIN-TYPECHECK`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`, ni `MOVTYPE-GLOBAL-SIN-UNICIDAD`,
ni `INBOX-045-AISLAMIENTO`, ni tocar el lockfile ni `conftest.py`, ni la certificación de
compras, ni la Spec 053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-09-30 · Tras converger el delta AUDITORIA-SOBRE-VS-ARRAY (dueña 001, apoyo 012)

La pantalla de auditoría nunca había pintado una fila, y ahora se sabe con números por
qué: el servidor respondía un sobre con 20 eventos y `total` 108, la pantalla lo pedía
como `AuditEvent[]` y se lo entregaba entero a la tabla, que al no encontrar una lista ni
pintaba ni avisaba. Sin error, sin estado vacío: una tabla muda con un 200 detrás. `tsc`
no podía verlo porque `apiFetch<T>` devuelve `payload as T`: el tipo lo afirma quien
llama, y quien llamaba afirmaba mal.

Antes de tocar nada se comprobó que el sobre es el contrato y no un accidente:
`api-contracts.md` lo llama «timeline con filtros y paginación», el contrato de listados
nombra `page` y `page_size`, el handler lo devuelve desde su primera versión, las once
pruebas de aislamiento lo fijan y el E2E de aprobaciones lo consume por `.items`. Lo
único que no lo dice es OpenAPI, porque la operación no declara `response_model`: queda
registrado (`AUDIT-OPENAPI-SIN-RESPONSE-MODEL`), y el backend no se toca.

El fix es del tamaño del defecto: una función tipada por endpoint,
`listAuditEvents(): Promise<PagedResult<AuditEvent>>`, con el tipo de sobre que el
frontend ya tenía, y `items` como filas. A partir de ahí, tratar el sobre como array no
compila —medido con un control negativo— y retipar la petición tampoco, porque una
prueba de tipo lo impide. Ni `as`, ni `Array.isArray`, ni `items ?? data`: el objetivo era
quitar la ambigüedad, no institucionalizarla. Siete pruebas de página —filas, vacío,
carga, error, paginación de cliente, respuesta que no es sobre, contrato de tipo—, dos
E2E con inicios de sesión controlados cuyo `X-Request-ID` devuelve el servidor, en
Chromium, Firefox y WebKit; seis mutantes, seis muertos.

Lo que sigue igual, a propósito: la columna «Fecha» pinta «Invalid Date» porque lee
`created_at` y el servidor publica `event_time` (`AUDITORIA-CREATED-AT`); la caja de
búsqueda sigue muerta hasta que alguien decida sobre qué campos busca; y la tabla pagina
en cliente sobre la página 1 de 20 del servidor, sin enseñar `total` ni poder pedir la 2
(`AUDITORIA-PAGINACION-CLIENTE`, nueva, menor).

### Lo que este delta enseñó del entorno

El `.venv` se reparó **fuera del repositorio**: los intérpretes aplanados apuntan ahora al
3.11 de `uv` y los 26 guiones llevaban aún la ruta del repositorio anterior en su primera
línea. Con eso, `alembic`, `pytest` y `declararAlcance` del E2E vuelven a funcionar; las
deudas de entorno siguen abiertas porque el repositorio no cambió. Y Vitest tiene una
rareza documentada: limpiar un mock dentro de `beforeEach` hace que una prueba cuya
consulta rechaza falle con el propio rechazo (`VITEST-MOCKCLEAR-EN-HOOK`).

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **AUDITORIA-CREATED-AT** · la columna Fecha lee un campo que no llega | 012 | no |
| 2 | **EMPRESAS-SIN-SOBRE** · el listado no pagina en el servidor | 001/007 | no |
| 3 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 4 | **LOCK-SIN-REPORTLAB-MAGIC** · el lock no reconstruye el entorno | 001/052 | no |
| 5 | **TEST-SCHEMAS-PG-SIN-LIMPIEZA** · la suite llena el disco y agota conexiones | 054/052 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner**: `API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`,
`MOVTYPE-GLOBAL-SIN-UNICIDAD`, `UI-BUSQUEDA-MUERTA` en Auditoría (campos) y en Existencias.

**Candidata siguiente: `AUDITORIA-CREATED-AT`.** Ahora que la tabla pinta, la fecha
inválida es lo primero que se ve; el servidor publica `event_time`, el tipo del frontend
declara `created_at`, y no hay nada que decidir.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni `created_at` → `event_time`, ni `q` en Auditoría ni en Existencias, ni la paginación de
servidor de la tabla, ni `response_model` en el backend, ni `EMPRESAS-SIN-SOBRE`, ni tocar
`apiFetch`, ni `E2E-SIN-TYPECHECK`, ni el lockfile, ni `conftest.py`, ni
`API-QUERY-SILENCIOSA`, ni `API-COMPANY-ID-EN-CONSULTA`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`,
ni `MOVTYPE-GLOBAL-SIN-UNICIDAD`, ni `INBOX-045-AISLAMIENTO`, ni la certificación de compras,
ni la Spec 053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-09-30 · Tras converger el delta AUDITORIA-CREATED-AT (dueña 001, apoyo 012)

En cuanto la tabla de auditoría pintó filas, cada una decía «Invalid Date». El origen está
en el primer commit del repositorio: el tipo del frontend y la columna «Fecha» decían
`created_at` —el nombre de la columna del mixin de la tabla— mientras el listado publicaba
`event_time` desde ese mismo día. Nadie lo vio porque durante siete semanas la tabla no
pintó nada. Reproducido con un evento controlado: un login por API cuyo `X-Request-ID`
devuelve el servidor, `event_time` `2026-09-30T21:54:06.507259+00:00` en la API y
«Invalid Date» en su fila.

La pregunta que había que contestar antes de tocar nada no era el campo —ese lo decide el
contrato— sino cómo se enseña un instante en KONTROL. La respuesta existe y tiene nombre:
`formatearFecha`, en `i18n`, que es `toLocaleString("es-VE")` en la zona del navegador, lo
mismo que escriben a mano las otras ocho pantallas con instantes. `fecha-de-negocio` no
aplica: da el día civil de negocio en Caracas para reglas funcionales, y un evento de
auditoría es un instante técnico. Fijar `America/Caracas` como zona de presentación sería
una decisión nueva que alcanza a nueve pantallas: se registra
(`FECHAS-ZONA-DE-PRESENTACION`), no se toma.

El fix son cuatro líneas: `event_time` en el tipo y en la columna, y el formateador
canónico. Volver a `created_at` en el camino tipado no compila (control negativo medido).
Cinco pruebas de página con dos instantes —uno que cruza la medianoche civil según la
zona—, fijadas literalmente bajo UTC, Caracas y Ámsterdam, porque el texto depende de la
zona por convención y el instante no; un E2E con evento controlado en tres navegadores;
siete mutantes, siete muertos. Vitest 400/400 bajo las tres zonas.

### Lo que este delta enseñó del entorno

`/tmp` se vació entre sesiones: el clúster PostgreSQL de QA, el mundo sembrado y el
intérprete del scratchpad desaparecieron. Reaprovisionar cuesta un minuto con el `.venv`
reparado del repositorio; queda escrito en memoria de sesión, no en el producto.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **EMPRESAS-SIN-SOBRE** · el listado no pagina en el servidor | 001/007 | no |
| 2 | **AUDITORIA-PAGINACION-CLIENTE** · página 1 de 20 y `total` invisible | 001 | no |
| 3 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 4 | **LOCK-SIN-REPORTLAB-MAGIC** · el lock no reconstruye el entorno | 001/052 | no |
| 5 | **TEST-SCHEMAS-PG-SIN-LIMPIEZA** · la suite llena el disco y agota conexiones | 054/052 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner**: `FECHAS-ZONA-DE-PRESENTACION` (nueva),
`API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`, `MOVTYPE-GLOBAL-SIN-UNICIDAD`,
`UI-BUSQUEDA-MUERTA` en Auditoría (campos) y en Existencias.

**Candidata siguiente: `EMPRESAS-SIN-SOBRE`.** Es la única deuda funcional de la cola con
contrato escrito (`api-contracts.md`: listados con `page`, `page_size`, `total`) y sin
decisión pendiente; y `AUDITORIA-PAGINACION-CLIENTE` necesitará el mismo mecanismo de
paginación de servidor en `DataTable`, así que conviene resolverlas con una sola forma.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni el sobre de Empresas, ni la paginación de servidor de la tabla, ni fijar una zona de
presentación, ni `q` en Auditoría ni en Existencias, ni `response_model` en el backend, ni
`E2E-SIN-TYPECHECK`, ni el lockfile, ni `conftest.py`, ni `API-QUERY-SILENCIOSA`, ni
`API-COMPANY-ID-EN-CONSULTA`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`, ni
`MOVTYPE-GLOBAL-SIN-UNICIDAD`, ni `INBOX-045-AISLAMIENTO`, ni la certificación de compras,
ni la Spec 053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-09-30 · Tras converger el delta EMPRESAS-SIN-SOBRE (dueña 001, apoyo 012)

El contrato de listados estaba escrito desde la fundación —`api-contracts.md`: «listados
con `q`, `status`, `sort`, `page`, `page_size`»— y dieciséis listados lo cumplían con el
mismo sobre. Empresas era el decimoséptimo y devolvía un array plano: sin `total`, y con
`page` y `page_size` ignorados en silencio, que es la familia de `API-QUERY-SILENCIOSA`.
Medido antes de tocar nada: `?page=2` y `?page_size=1` devolvían las mismas dos empresas.

Lo delicado no era el sobre sino quién lo consume. Treinta y seis consumidores, y uno de
ellos no puede quedarse con una página: el selector de contexto, que es la autoridad de
qué empresa puede activarse. No se le dio un `page_size` inventado ni un `all=true` que el
contrato no tiene: recorre las páginas declaradas, con el tamaño máximo que el contrato
admite, hasta reunir `total`. La pantalla, en cambio, pagina de verdad en el servidor:
diez por página, un solo paginador con el `total` del sobre, y a la primera página al
cambiar la búsqueda. Para eso `DataTable` gana una opción aditiva, `manualPagination`,
que deja de re-paginar en cliente lo que ya vino paginado; el resto de pantallas no cambia.

En el backend, `total` cuenta el mismo conjunto que `items` —tenant, alcance del usuario,
`q`— antes de cortar, y el orden lleva el identificador como desempate porque una siembra
en una transacción deja la fecha de alta igual en todas. Doce pruebas de contrato, quince
de frontend, cuatro E2E; quince mutantes, quince muertos, uno de ellos gracias a una prueba
que hubo que escribir (a diez por página la doble paginación era invisible; a veinticinco
no). Los veintidós E2E que toleraban «array o sobre» pasan a exigir el sobre: la
ambigüedad se retira, no se institucionaliza.

### Cola esperada, por orden

| # | Deuda | Dueña | Autorizada |
|---|---|---|---|
| 1 | **AUDITORIA-PAGINACION-CLIENTE** · ya tiene mecanismo y precedente | 001 | no |
| 2 | **E2E-SIN-TYPECHECK** · `e2e/` fuera del grafo TypeScript | 054 | no |
| 3 | **LOCK-SIN-REPORTLAB-MAGIC** · el lock no reconstruye el entorno | 001/052 | no |
| 4 | **TEST-SCHEMAS-PG-SIN-LIMPIEZA** · la suite llena el disco y agota conexiones | 054/052 | no |
| 5 | **LISTADOS-SIN-RESPONSE-MODEL** · diecisiete sobres sin declarar en OpenAPI | 001 | no |
| 6 | Certificar compras (015 → 016 → 017 → 027 → revalidar 028) | 004-compras | no |
| 7 | SPEC053 · verificar restauración (DT-11) | 053 | no |

**A la espera de decisión del owner**: `FECHAS-ZONA-DE-PRESENTACION`, `API-QUERY-SILENCIOSA`,
`SEED-EMPRESA-CODIGO-NO-UNICO`, `MOVTYPE-GLOBAL-SIN-UNICIDAD`, `UI-BUSQUEDA-MUERTA` en
Auditoría (campos) y en Existencias.

**Candidata siguiente: `AUDITORIA-PAGINACION-CLIENTE`.** Es la misma forma que acaba de
converger —sobre, `manualPagination`, `Pagination` con `total`— aplicada a la única otra
pantalla que la necesita, y no espera ninguna decisión.

`READY_FOR_IMPLEMENTATION = 0`. **Ninguna se ha iniciado.**

### Lo que esta decisión NO autoriza

Ni la paginación de Auditoría, ni `status`/`sort` en Empresas, ni `response_model` en
ningún listado, ni fijar una zona de presentación, ni `q` en Auditoría ni en Existencias,
ni `E2E-SIN-TYPECHECK`, ni el lockfile, ni `conftest.py`, ni `API-QUERY-SILENCIOSA`, ni
`API-COMPANY-ID-EN-CONSULTA`, ni `SEED-EMPRESA-CODIGO-NO-UNICO`, ni
`MOVTYPE-GLOBAL-SIN-UNICIDAD`, ni `INBOX-045-AISLAMIENTO`, ni la certificación de compras,
ni la Spec 053, ni ninguna decisión abierta (D0-06, D0-07, OQ-048, MD-049, `EXPIRED`).

## 2026-10-01 · Tras converger el delta AUDITORIA-PAGINACION-CLIENTE (dueña 001, apoyo 012)

El servidor paginaba la bitácora desde siempre; la pantalla no le pedía más que la primera
página y, encima, la tabla volvía a paginar en cliente los veinte eventos recibidos. Medido
en el navegador antes de tocar nada: 10 279 eventos en el servidor, 20 alcanzables desde la
pantalla, y «siguiente» sin producir ninguna petición.

No hubo nada que diseñar: el mecanismo se había construido en `EMPRESAS-SIN-SOBRE` y se
reutilizó tal cual. La página y su tamaño son estado de la pantalla, viajan en la petición
y en la clave de caché; la tabla recibe `manualPagination`; el paginador es uno y se
gobierna con el `total` del sobre. Dos ficheros de frontend. Backend, `DataTable`, esquema:
cero. La caja de búsqueda no se tocó, y a propósito no reinicia la página: el servidor
ignora `q`, y qué hace esa caja es decisión de la dueña (`UI-BUSQUEDA-MUERTA`).

Fue el primer delta ejecutado con la orquestación Claude + DeepSeek. Claude investigó,
reprodujo, fijó el contrato, diseñó las pruebas y los mutantes, auditó y aplicó; DeepSeek
propuso el producto y las suites: cinco tareas, nueve llamadas, $0.0098. Cuatro propuestas
se rechazaron. Dos, por desviarse del encargo. Las otras dos, por errores de contrato de
quien redactó el encargo —Claude—, que la auditoría y las pruebas bajo carga destaparon: la
aplicación cachea treinta segundos, y una bitácora que crece mientras se pagina repite filas
entre páginas. Ningún parche se retocó a mano. El coste real de delegar no fue DeepSeek sino
el subagente que hace de puente (`EJECUTOR-ABREVIA-EL-CONTEXTO`).

Lo que este delta deja medido y no absorbe: `AUDITORIA-OFFSET-EN-BITACORA-VIVA`,
`AUDIT-TOTAL-CARGA-TODO` (450 ms por página con 10 648 eventos) y
`AUDIT-ORDEN-SIN-DESEMPATE`.

**Candidatas siguientes, sin decisión de la dueña pendiente:** `AUDIT-TOTAL-CARGA-TODO` junto
con `AUDIT-ORDEN-SIN-DESEMPATE` (mismo handler, backend, pequeño), `AUDITORIA-TIMELINE-FECHA-CRUDA`
o `LISTADOS-SIN-RESPONSE-MODEL`. **Con decisión pendiente:** `UI-BUSQUEDA-MUERTA` en Auditoría
y en Existencias. `NEXT SPEC = 029` no cambia.

## 2026-10-01 · Tras converger el delta AUDIT-TOTAL-CARGA-TODO (dueña 001, apoyo 012)

Para decir un número, el servidor construía trece mil objetos. `list_events` calculaba
`total` con `len()` sobre la lista de todas las entidades del tenant: medido en PostgreSQL
con 13 576 eventos y una página de diez, 13 586 filas y 13 586 entidades por petición, y de
los 377 ms del endpoint la base solo gastaba 41. Era el único de los diecisiete listados
que contaba así.

El arreglo son tres cambios en un fichero: `total` sale de un `SELECT count(*)` sobre el
mismo objeto de consulta del que después se corta la página, de modo que el tenant y los
filtros no pueden divergir entre el conteo y los items; y el orden, que contar no necesita,
se aplica solo a los items, cuyo SQL queda idéntico. Después: 11 filas, 10 entidades, 30 ms.
Contrato, sobre, paginación, orden, alcance de tenant, frontend, esquema e índices no cambian.

Las pruebas no miran el código fuente sino lo que la petición hace: un observador cuenta
las sentencias sobre `audit_events` y las entidades que el ORM construye. El cambio del
handler lo hizo Claude —mueve la línea del predicado de tenant, que la política reserva—;
la suite la propuso DeepSeek en una tarea, con un reintento.

Queda medido y sin absorber `AUDIT-PAGINA-SIN-INDICE-DE-ORDEN`: lo que ahora domina la
petición es la página, que recorre y ordena los eventos del tenant sin un índice que la
sirva. `AUDIT-ORDEN-SIN-DESEMPATE` y `AUDITORIA-OFFSET-EN-BITACORA-VIVA` siguen abiertas.

**Candidatas siguientes, sin decisión de la dueña pendiente:** `AUDIT-ORDEN-SIN-DESEMPATE`,
`AUDITORIA-TIMELINE-FECHA-CRUDA`, `LISTADOS-SIN-RESPONSE-MODEL` (con
`AUDIT-OPENAPI-SIN-RESPONSE-MODEL`), `E2E-SIN-TYPECHECK`, `TEST-SCHEMAS-PG-SIN-LIMPIEZA`,
`API-COMPANY-ID-EN-CONSULTA`, `E2E-FLAKY-BAJO-CARGA`. `NEXT SPEC = 029` no cambia.

## 2026-10-01 · Tras converger el delta TEST-SCHEMAS-PG-SIN-LIMPIEZA (dueña 054, apoyo 052)

La suite se ejecuta sobre PostgreSQL desde `579affb`, y desde entonces `make_engine` creaba
un schema entero y un motor en cada llamada sin que nadie los soltara. Trece suites lo
llaman una vez por prueba. Una corrida completa dejaba 313 schemas y 3,2 GB; tres seguidas
llenaron el `tmpfs` y tumbaron el servidor de QA. El remedio era borrar la base y volver a
crearla, a mano, después de cada certificación.

No se reescribieron las 27 fixtures. El ciclo de vida vive ahora en un solo sitio: lo que
la suite crea se apunta al ámbito abierto —la prueba o el módulo— y dos fixtures `autouse`
lo sueltan al cerrarlo, pase o falle la prueba; primero las conexiones, después el schema,
y al final se comprueba que ya no existe. Las bases enteras de las pruebas de migración
entran en el mismo registro. Y nada de eso ocurre si la base no es, por varias señales a la
vez, de prueba.

Medido con dos corridas completas seguidas sin recrear la base: 0 schemas, 0 conexiones,
171 MB al final donde había 3 240, pico de 5 conexiones donde había 60, y siete minutos
menos por corrida. Los fallos son los de siempre —documentos, por falta de `clamscan`— y
son el mismo conjunto que antes del cambio.

Era casi todo trabajo de Claude: diseño del ciclo de vida, seguridad de lo destructivo y
ficheros con direcciones de base de QA. DeepSeek escribió las pruebas de la compuerta, una
función pura, y pasaron la auditoría a la primera.

**Con esto, certificar un cambio de backend en PostgreSQL deja de costar una base.**
Candidatas siguientes, sin decisión de la dueña pendiente: `AUDIT-ORDEN-SIN-DESEMPATE`,
`AUDIT-PAGINA-SIN-INDICE-DE-ORDEN`, `AUDITORIA-TIMELINE-FECHA-CRUDA`,
`LISTADOS-SIN-RESPONSE-MODEL`, `E2E-SIN-TYPECHECK`, `E2E-FLAKY-BAJO-CARGA`,
`ENTORNO-SIN-CLAMSCAN`. `NEXT SPEC = 029` no cambia.

## 2026-10-01 · Tras el delta E2E-FLAKY-BAJO-CARGA (dueña 054, apoyo 008) — parcial, la deuda sigue abierta

La deuda decía que ocho pruebas E2E caían de vez en cuando en las corridas globales y que la
inestabilidad crecía con la base de QA. Lo segundo era literal.

Picking, Pick-execution y Put-away caducaban porque el listado de almacenes preguntaba a la
base doce veces por almacén y la empresa del E2E acumula los almacenes de cada corrida. Se
reprodujo a voluntad —con 1 434 almacenes, 0 de 3— y se corrigió en producto sin cambiar el
contrato: 6 370 sentencias pasan a 16. Otras dos caídas eran carreras escritas en la propia
prueba, y se corrigieron. El `ECONNRESET` también tiene causa: uvicorn y el cliente de
Playwright sueltan una conexión inactiva a los mismos 5 segundos.

Pero al certificar cayó una prueba que nunca había caído, `notifications.spec.ts:142`: el
planificador, que esa prueba ejecuta dentro de sus 30 segundos, tarda ya 33, porque cada
corrida deja reglas y usuarios que multiplican el reparto de la siguiente. Y mis propios
experimentos empujaron la base por encima de otro corte, el de los 500 almacenes del
desplegable de Put-away. **La corrida global final quedó 193/1/40.** No hay un defecto: hay
una base que crece sin límite y varios caminos cuyo coste depende de su tamaño.

Por eso la deuda **no se cierra**: queda `PARTIALLY_CONVERGED`, y lo que la cierra tiene
nombre propio y es una decisión de la dueña.

**Decisión pendiente — `E2E-BASE-QA-ACUMULA` (`MATERIAL_DECISION_REQUIRED`):** cómo se da
ciclo de vida a la base del E2E. Base nueva por corrida, tenant por corrida o limpieza por
prueba. Hasta entonces, `E2E-NOTIFICACIONES-REGLAS-VIVAS` deja la corrida global en rojo.

Registradas y sin absorber: `ALMACENES-DESPLEGABLES-TRUNCADOS` (nueve pantallas),
`BACKEND-KEEPALIVE-5S`, `LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE`, `PICKLIST-DUPLICADA-500`,
`E2E-PANTALLA-SIN-PINTAR` (dos fallos sin causa demostrada) y `LISTADOS-SIN-TOPE`.

**Candidata siguiente, y con diferencia:** `E2E-BASE-QA-ACUMULA`, en cuanto la dueña decida.
Detrás, sin decisión pendiente: `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`AUDIT-ORDEN-SIN-DESEMPATE`, `AUDIT-PAGINA-SIN-INDICE-DE-ORDEN`, `LISTADOS-SIN-RESPONSE-MODEL`,
`E2E-SIN-TYPECHECK`, `ENTORNO-SIN-CLAMSCAN`. `NEXT SPEC = 029` no cambia.

## 2026-10-01 · Tras converger E2E-BASE-QA-ACUMULA y cerrar E2E-FLAKY-BAJO-CARGA (dueña 054)

La dueña decidió: una base nueva por corrida E2E. Está hecho. `qa/e2e-run.py` crea la base,
la migra a la cabeza, la siembra, levanta contra ella el backend y Vite, corre la suite y
lo elimina todo, pase o falle; nada destructivo ocurre sobre una base que no sea, por
nombre, marca, entorno y servidor, de una corrida. `kaud` queda para QA manual y no se toca.

Con la base limpia, lo que era acumulación desapareció sin tocarlo —el planificador pasó de
33 segundos a menos de uno— y lo que no lo era quedó a la vista. La primera corrida global
sobre base nueva falló donde la deuda decía «sin causa»: el recorrido de rutas. Había dos
pantallas que caían al pintarse, Listas de precios y Diagnóstico, y una restauración de
sesión que, al recargar, mandaba a Inicio 81 de las 96 rutas del menú; el recorrido leía el
título de Inicio y lo daba por bueno. Los tres defectos están corregidos y el recorrido
comprueba ahora en qué ruta está.

Tres corridas globales seguidas, cada una desde su base: 200 / 0 / 40 las tres, y las tres
acaban en el mismo estado.

**Con esto se cierran `E2E-BASE-QA-ACUMULA`, `E2E-NOTIFICACIONES-REGLAS-VIVAS` y
`E2E-FLAKY-BAJO-CARGA`.** De esta última quedan dos deudas propias: `BACKEND-KEEPALIVE-5S`,
con causa y pendiente de una decisión de despliegue, y `E2E-PANTALLA-SIN-PINTAR`, un login
en blanco visto una vez y sin causa.

Nuevas, sin absorber: `DIAGNOSTICO-SIN-SESION` (seguridad: el diagnóstico responde sin
sesión y enseña una ruta interna), `INSTALACION-KEY-REFERENCE-120`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `ALMACENES-CARRERA-SQLITE-HILOS` y `E2E-CUARENTA-OMITIDAS`.

**Decisiones pendientes de la dueña:** `DIAGNOSTICO-SIN-SESION` y `BACKEND-KEEPALIVE-5S`.
Candidatas siguientes, sin decisión pendiente: `ALMACENES-DESPLEGABLES-TRUNCADOS`,
`PICKLIST-DUPLICADA-500`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `AUDIT-ORDEN-SIN-DESEMPATE`, `LISTADOS-SIN-RESPONSE-MODEL`,
`E2E-SIN-TYPECHECK`, `ENTORNO-SIN-CLAMSCAN`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · Tras converger DIAGNOSTICO-SIN-SESION (dueña 001; apoyo 004 por el permiso)

El diagnóstico de la instalación respondía a cualquiera, sin sesión y con un token inventado:
identidad de la instalación, licencia y la ruta de almacenamiento del servidor. La dueña
decidió: sesión válida y permiso existente. No había recurso de sistema en el catálogo; se
reutiliza `license:view`, que ya gobierna leer licencia e instalación en el menú. Sin sesión
401, sin permiso 403, y el cuerpo ya no lleva la ruta. La pantalla y el menú respetan el mismo
permiso, y los health checks públicos siguen como estaban: Docker, el panel y el lanzador de QA
los usan.

De paso quedó registrado, sin absorber, lo que estaba al lado: `GET /license/status` también
responde sin sesión (lo pide la pantalla de acceso), las lecturas de licenciamiento no exigen
`license:view` aunque exista, no hay API de alta de roles con permisos, y el OpenAPI no
declara ningún esquema de seguridad.

Y una corrida global dejó una lección de entorno: el reloj del equipo saltó cinco horas en
medio de la corrida —NTP, tras el reinicio— y con él un cambio de red; Chromium abortó una
carga (`ERR_NETWORK_CHANGED`: el «login en blanco» de `E2E-PANTALLA-SIN-PINTAR`, por fin con
traza) y seis pruebas recibieron tokens caducados al instante. La siguiente corrida, limpia.

**Decisiones pendientes de la dueña:** `LICENCIA-STATUS-SIN-SESION`, `BACKEND-KEEPALIVE-5S`,
`HEALTH-LIVE-VERSION`. Candidatas siguientes, sin decisión pendiente:
`LICENCIA-LECTURA-SIN-PERMISO`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · Tras converger LICENCIA-STATUS-SIN-SESION, LICENCIA-LECTURA-SIN-PERMISO y HEALTH-LIVE-VERSION (dueña 004)

El estado de la licencia respondía a cualquiera, sin sesión, la identidad de la instalación, el
identificador de la licencia, su `kid`, las cuatro fechas y los derechos; el historial y la
solicitud de activación —con la clave pública de la instalación— también eran anónimos, y las
lecturas de licenciamiento central exigían sesión pero no `license:view`. La dueña decidió
(D1–D4): el estado sigue público porque lo pide la pantalla de acceso, pero **mínimo** —`mode` y
`license_url`, por lista explícita, nunca por exclusión—; todo lo detallado exige sesión y
`license:view` en el backend; `/health/live` deja de publicar la versión y `/health/ready` sigue
mínimo. Nadie parseaba la versión: Docker mira el código, los guiones imprimen el cuerpo y el panel
la leía de un endpoint que nunca la trajo. «Mi licencia» —pantalla del Administrador— exige el
permiso antes de pedir nada, y lo respetan su entrada de menú y el enlace del aviso; el aviso del
modo lo ve todo usuario, porque a eso sirve el estado público. Sin permiso nuevo, sin rol nuevo,
sin esquema, sin migración, sin tocar vigencia, zona horaria, firma ni identidad.

De paso quedó registrado, sin absorber: sobre SQLite la tolerancia offline compara una fecha sin
zona con UTC y rompe dos lecturas (`OFFLINE-NAIVE-EN-SQLITE`); la tarjeta «Versión» del panel
siempre dijo «—» (`PANEL-VERSION-VACIA`); y la importación de licencia sigue anónima, con la
firma como única autoridad (`LICENCIA-IMPORT-SIN-SESION`, decisión de la dueña).

**Decisiones pendientes de la dueña:** `BACKEND-KEEPALIVE-5S`, `LICENCIA-IMPORT-SIN-SESION`,
`PANEL-VERSION-VACIA`. Candidatas siguientes, sin decisión pendiente:
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · Tras converger LICENCIA-IMPORT-SIN-SESION (dueña 004)

Importar una licencia firmada era una operación anónima. Reproducido con un artefacto sintético:
cualquiera activaba la instalación con una licencia válida, la dejaba en solo lectura con una
firmada más vieja, y cada intento fallido engordaba la auditoría. La dueña decidió que no siga
anónima y que se reutilice una autoridad canónica existente sin inventar permiso, rol ni token.
Existía: el administrador local es quien carga la licencia por contrato (US-003) y
`license:create` ya era el permiso de activarla contra el servidor central (US-010-002). Ahora
las dos rutas exigen sesión y ese permiso como dependencia, antes del cuerpo y de la firma; la
firma del propietario y la identidad de la instalación siguen siendo la segunda compuerta, y el
evento lleva quién importó. Se comprobó físicamente que ningún estado deja fuera al administrador:
el login no consulta la licencia, `/api/v1/license/` está exento del bloqueo de solo lectura y el
administrador nace en `setup/initialize`, antes de que exista licencia.

De paso quedó registrado, sin absorber: una licencia firmada **más vieja** sigue reemplazando a la
vigente (`LICENCIA-DOWNGRADE-FIRMADO`), y sin la clave del propietario configurada el ancla de
confianza es la clave de la propia instalación (`LICENCIA-ANCLA-AUTOFIRMADA`). Ambas, decisión de
la dueña.

**Decisiones pendientes de la dueña:** `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`,
`LICENCIA-DOWNGRADE-FIRMADO`, `LICENCIA-ANCLA-AUTOFIRMADA`. Candidatas siguientes, sin decisión
pendiente: `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · Tras converger LICENCIA-ANCLA-AUTOFIRMADA (dueña 004)

Sin la clave del propietario configurada, la instalación verificaba las licencias con su propia
clave pública: quien leyera la clave privada del servidor se emitía una licencia a sí mismo, también
en producción. Reproducido en `prod` con un artefacto sintético. La dueña decidió: ancla del
propietario obligatoria en producción, cerrado si falta, y nada de prueba por ausencia de
configuración. El repositorio ya tenía el contrato para eso —`secret_key` «obligatoria: falla al
inicio»—, así que en `prod` la configuración no carga sin el ancla y, en cualquier entorno, importar
sin ella o con una que no sirve responde 503 sin sustituto, sin evento y sin material en el
registro. La clave de la instalación vuelve a ser solo identidad. QA firma con un firmante sintético
por corrida cuya pública se declara como ancla de esa corrida; los guiones de licencia de prueba se
niegan en producción.

De paso quedó registrado, sin absorber: el ancla es una sola clave sin rotación ni `kid`
verificado (`LICENCIA-SIN-ROTACION-DE-CLAVE`). `LICENCIA-DOWNGRADE-FIRMADO` sigue abierta y es la
siguiente de esta familia.

**Decisiones pendientes de la dueña:** `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`,
`LICENCIA-DOWNGRADE-FIRMADO`, `LICENCIA-SIN-ROTACION-DE-CLAVE`. Candidatas siguientes, sin decisión
pendiente: `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · LICENCIA-DOWNGRADE-FIRMADO detenida antes de implementar (dueña 004)

Una licencia firmada por el propietario, para esta instalación y presentada por un administrador
con `license:create` puede ser anterior a la vigente y aun así reemplazarla: reproducido en siete
variantes, incluida la licencia vencida que deja en solo lectura una instalación activa, y una
carrera en PostgreSQL en la que dos importaciones concurrentes dejan la más vieja en tres de seis
rondas. La dueña decidió que una licencia anterior no sustituya a la vigente, y exigió no inventar
qué significa «anterior». El contrato (DOC-07) ordena las licencias por **período** y prohíbe
retroceder el período; pero también permite reemitir la licencia dentro del mismo período para
ampliar o reducir límites, y el paquete firmado no lleva fecha ni número de emisión: dos
reemisiones del mismo período no se pueden ordenar. Orden parcial, empate sin contrato: el ciclo
se detuvo con el informe para la dueña, sin tocar código, esquema ni migración.

**Decisión material pendiente:** `LICENCIA-DOWNGRADE-FIRMADO` — orden por período ahora (A), claim
firmado de emisión en el paquete (B), o cerrado intra-período (C); recomendación A ahora y B como
objetivo, ambas con bloqueo de fila. Registradas aparte `LICENCIA-IMPORT-SIN-BLOQUEO` (la carrera)
y `LICENCIA-ESTADO-SIN-REVERIFICAR` (observación).

**Decisiones pendientes de la dueña:** `LICENCIA-DOWNGRADE-FIRMADO`, `BACKEND-KEEPALIVE-5S`,
`PANEL-VERSION-VACIA`, `LICENCIA-SIN-ROTACION-DE-CLAVE`. Candidatas siguientes, sin decisión
pendiente: `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · Fase A de LICENCIA-DOWNGRADE-FIRMADO y cierre de LICENCIA-IMPORT-SIN-BLOQUEO (dueña 004)

La dueña resolvió el bloqueo con la opción A: ordenar por período ahora y dejar explícito lo que
el contrato no ordena. El comparador compara solo el período firmado —igual inicio e igual fin es
el mismo período; ambos posteriores, más nuevo; ambos anteriores, más viejo; cualquier otra forma
no es un período del contrato y no se aplica— y la importación bloquea la fila de la instalación,
relee el estado bajo el bloqueo y rechaza antes de persistir: una licencia de período anterior ya
no sustituye a la vigente ni cuando la vigente está vencida o en solo lectura; una posterior entra;
la misma es idempotente; la reemisión del mismo período entra como permite §7.1. Dos importaciones
concurrentes pasan de una en una y terminan siempre en el período mayor, con una prueba
determinista en PostgreSQL y dos mutaciones que demuestran que la carrera está cubierta.

Lo que sigue abierto, con nombre: `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`, con el objetivo
ratificado de una `revision` firmada que no se implementa hasta que cambien el paquete y el emisor.
`LICENCIA-DOWNGRADE-FIRMADO` queda parcialmente convergida, no cerrada.

**Decisiones pendientes de la dueña:** `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` (cuándo y cómo
introducir la `revision` en el paquete y el emisor), `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`,
`LICENCIA-SIN-ROTACION-DE-CLAVE`. Candidatas siguientes, sin decisión pendiente:
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-06 · LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN detenida: no hay emisor (dueña 004)

La dueña ratificó la `revision` firmada: entera, positiva, monótona por instalación y período,
asignada por el emisor, con la transición legacy definida al detalle. Este ciclo probó que el
paquete puede llevarla sin romper una sola licencia emitida: el verificador trabaja sobre el
diccionario recibido, así que una `revision` presente solo en los paquetes nuevos no cambia los
bytes de las legacy (y quedó demostrado el camino que sí los rompería). Pero la `revision` es del
emisor, y el emisor —la Autoridad Central de Licencias de DOC-07— no existe en este repositorio ni
en ninguno accesible: aquí solo hay el cliente y firmantes sintéticos de QA, y el hospedaje de la
autoridad sigue en la decisión empresarial D0-06. Asignarla desde el cliente o desde el firmante de
QA sería aparentar un orden que nadie garantiza, y el encargo lo prohíbe expresamente. El ciclo se
detuvo con el informe para la dueña y las reglas listas para cuando el emisor exista.

**Decisión material nueva:** `EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR` — construir la autoridad
central (Spec propia), una herramienta mínima de emisión del propietario fuera del cliente, o
esperar a D0-06. De ella cuelgan la `revision`, la rotación de claves y la activación en línea.

**Decisiones pendientes de la dueña:** `EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR` (y con ella
`LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` y `LICENCIA-SIN-ROTACION-DE-CLAVE`),
`BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`. Candidatas siguientes, sin decisión pendiente:
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-07 · Autoridad Central de Licencias, Fase 1: el emisor existe (dueña 004)

La dueña decidió construir la autoridad como servicio del propietario, separado del cliente y
agnóstico de proveedor. Este ciclo la implementó en `resources/backend/central_authority/` con
base, migraciones, configuración y clave propias; registro de instalaciones; libro de emisiones
inmutable; `revision` firmada, monótona por instalación + período y segura en concurrencia
(PostgreSQL); CLI del propietario; health mínimo; imagen y compose propios; y una prueba de grafo
de importación que impide que la autoridad dependa de nada del cliente salvo el contrato puro
(`app/core/license_contract.py`, extraído sin cambiar un byte de las licencias legacy). Diez
mutaciones, diez muertas. El cliente importa el paquete emitido y rechaza cerrado una `revision`
inválida. **La API de sync productiva no se expone**: el cliente la llama sin autenticación ligada
a la instalación, y definirla es decisión material de la dueña.

**D0-06** pasa a `CLOSED / IMPLEMENTED` en frontera y hospedaje lógico; el proveedor físico es
operación del propietario, no condición de la decisión.

**Decisión material nueva:** `CENTRAL-SYNC-AUTHORITY-UNDEFINED` — cómo se autentica la
instalación ante la autoridad (clave por instalación, secreto de activación, mTLS…).

**Decisiones pendientes de la dueña:** `CENTRAL-SYNC-AUTHORITY-UNDEFINED`,
`LICENCIA-SIN-ROTACION-DE-CLAVE`, `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`. Candidata
siguiente natural de la familia, ya sin bloqueo: `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`
(ciclo del cliente con este emisor como fuente). Otras candidatas sin decisión pendiente:
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-07 · LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN cerrada en el cliente; LICENCIA-DOWNGRADE-FIRMADO convergida (dueña 004)

Con el emisor real disponible, el cliente aplica ya la `revision` firmada como segundo criterio de
orden, después del período y dentro de la misma sección crítica de la Fase A: mayor entra, menor se
rechaza, igual con el mismo artefacto es idempotente, igual con otra carga es conflicto; una legacy
exacta sigue siendo idempotente, otra legacy del mismo período se rechaza, la revisionada del emisor
sustituye a la legacy y fija el linaje, y ninguna legacy vuelve tras ella. El cliente no asigna,
calcula ni corrige revisiones. Esquema y migraciones del cliente: 0. La certificación E2E usa la
Autoridad Central real (efímera, sobre su propia base) como fuente de los artefactos, en un proyecto
Playwright que corre tras el resto porque el linaje cambia el identificador vigente. Las pruebas que
afirmaban la tolerancia transitoria de la Fase A se adaptaron al contrato nuevo, pieza por pieza.

**Hallazgo colateral, cerrado:** SQLite guardaba el período con la hora de pared y perdía el
`-04:00`, así que leía el mismo período como posterior por cuatro horas; el estado guarda ahora los
instantes normalizados a UTC (mismo instante; PostgreSQL ya lo conservaba).

**Decisiones pendientes de la dueña:** `CENTRAL-SYNC-AUTHORITY-UNDEFINED` (decidida: identidad
Ed25519 de la instalación + desafío-respuesta + nonce + vinculación canónica; **sin implementar**),
`LICENCIA-SIN-ROTACION-DE-CLAVE`, `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`. Candidatas sin
decisión pendiente: `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`,
`PICKLIST-DUPLICADA-500`, `ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`,
`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. `NEXT SPEC = 029` no cambia.

## 2026-10-07 · CENTRAL-SYNC-AUTHORITY-UNDEFINED convergida: la instalación se autentica ante la autoridad (dueña 004)

El mecanismo que la dueña ratificó quedó implementado en los dos lados. La instalación firma con su
clave privada Ed25519 un sobre canónico que liga versión del protocolo, identidad, desafío, nonce,
método, destino y el SHA-256 de los bytes exactos que envía; la autoridad emite desafíos de 256 bits
con caducidad corta, los consume de forma atómica en su PostgreSQL (dos peticiones idénticas a la
vez: una sola autentica), verifica contra la clave pública que el vendor vinculó en el alta (huella
única; sin autorregistro; una clave que llegue en la petición se ignora) y devuelve el artefacto exacto
de su libro, que el cliente pasa por la importación con todas sus compuertas. Sin retroceso a sync
anónimo, HTTPS obligatorio en producción, renovación posible en `READ_ONLY` (el bloqueo estaba en la
ruta y en el middleware; se quitó de los dos). La corrida E2E levanta la autoridad real y el cliente
sincroniza contra ella por HTTP local.

**Deuda nueva:** `CENTRAL-SYNC-SIN-LIMITE-DE-TASA` (endurecimiento del endpoint de desafío; no se
debilitó el diseño para evitarla).

**Decisiones pendientes de la dueña:** `LICENCIA-SIN-ROTACION-DE-CLAVE`, `BACKEND-KEEPALIVE-5S`,
`PANEL-VERSION-VACIA`. Candidatas sin decisión pendiente: `OFFLINE-NAIVE-EN-SQLITE`,
`ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`, `ROLES-SIN-API-DE-ALTA`,
`E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`,
`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`, `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`. `NEXT SPEC = 029` no cambia.

## 2026-10-07 · Reconciliación global: MASTER57, SPEC057 y marco fiscal; el puntero `NEXT SPEC = 029` revisado

**Qué significa físicamente `NEXT SPEC = 029`.** Fue la selección del checkpoint maestro del 2026-08-31
(`master-56-convergence.md`): la siguiente Master Spec a ejecutar entre las candidatas de aquel
momento. La 029 quedó `COMPLETE / CONVERGED` el 2026-09-01 y la 030 el 2026-09-02; el checkpoint de la
cadena operativa del 2026-09-03 volvió a elegir (`NEXT SPEC = 019`), y la 019 también convergió. Desde
entonces ningún checkpoint maestro ha vuelto a seleccionar. La frase «`NEXT SPEC = 029` no cambia» que
repiten los deltas de licenciamiento de octubre es el invariante de esos encargos («no iniciar ninguna
Spec nueva»), no una reselección: como puntero a «la siguiente Spec realmente pendiente de iniciar» está
**obsoleto** (caso C del encargo), y como registro histórico de aquella decisión es exacto y se conserva
arriba tal cual.

**Qué no se hace aquí.** Elegir la siguiente Master Spec exige priorizar entre candidatas que hoy
compiten de verdad —018 Importaciones (`NOT_STARTED`), 047 Notificaciones, 048 Integraciones, las 26
parciales, y la nueva 057 cuando sus dependencias estén estables— y eso es decisión de la dueña:
**`NEXT-SPEC-POINTER-AMBIGUO — MATERIAL_DECISION_REQUIRED`**. No se inventa un número; el encabezado
histórico queda intacto. Lo que sí se fija: ninguna Spec nueva se inicia en este ciclo, y la 057 **no**
es la siguiente por el hecho de incorporarse.

**Lo reconciliado.** Inventario maestro **57** (`master-56-specs-status.md`, nombre histórico, título y
recuento en 57): la 057 Gestión Integral de Activos Fijos entra `PLANNED / NOT_STARTED` con su PDF de
Ingeniería de Requerimientos bajo control de versiones y referenciado desde el mapa de equivalencias,
la matriz de brechas (adenda), las olas (OLA 7b), el grafo de dependencias, el inventario de fuentes,
el mapa de requisitos y el backlog (B-094); la 023 no es su dueña. Marco fiscal: SNAT/2024/000121 fue
derogada por SNAT/2026/00084 (G.O. N.º 43.435, 12-08-2026; verificada con documentación jurídica
fiable); la homologación del software deja de ser requisito vigente (D0-07 `NARROWED`,
`HOMOLOGATION_REQUIREMENT_REMOVED`), la 056 pasa a «Validación de cumplimiento fiscal y liberación a
producción», las 039–043 siguen bloqueadas por la validación de sus reglas y ninguna se declara
completa; la 044 no cambia. Detalle: `master-57-reconciliation.md`.

**Candidatas técnicas tras esta reconciliación (sin iniciar):** `LICENCIA-SIN-ROTACION-DE-CLAVE`, después
`LICENCIA-ESTADO-SIN-REVERIFICAR`, `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`, `BACKEND-KEEPALIVE-5S`,
`PANEL-VERSION-VACIA`, y la convergencia priorizada de las Specs parciales.

## 2026-10-07 · `NEXT-SPEC-POINTER-AMBIGUO` — OWNER_DECIDED / CLOSED

La dueña decidió: `NEXT SPEC = 029` **deja de ser un puntero operativo vigente** (queda arriba como
registro histórico de la selección del 2026-08-31). A partir de ahora se separan dos cosas:

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `LICENCIA-SIN-ROTACION-DE-CLAVE` (ejecutado y convergido el mismo día: `specs/010-licenciamiento-central/spec004-licencia-rotacion-de-clave-delta.md`) |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — no se elige 018, 047, 048, 057 ni ninguna otra; la priorización se hará después |

Los informes de cierre dejan de repetir «`NEXT SPEC = 029` no cambia» y pasan a estos dos punteros.

## 2026-10-07 · LICENCIA-ESTADO-SIN-REVERIFICAR convergida: el vigente se reverifica al arrancar y antes de escribir (dueña 004)

La licencia que la instalación ya tenía persistida solo se había verificado una vez, al importarla.
Desde hoy el artefacto vigente (carga + firma + hash) se reverifica con la política de confianza
**actual** en cada arranque del backend (`lifespan`, informativo: si la base no responde el proceso no
cae) y antes de cada escritura de negocio (en el cálculo del modo que ya leen el middleware y las
rutas): `kid` firmado → clave exacta del conjunto (una clave retirada ya no concede nada), firma del
propietario, integridad del artefacto, vínculo con el estado e identidad de la instalación. Lo que
no verifica deja `SECURITY_SUSPENSION` —el modo que DOC-07 §10.1 reserva a la licencia alterada— sin
tocar el artefacto ni el historial; sesión, lectura, importación y sync siguen y son la recuperación.
Una licencia válida y vencida sigue siendo `READ_ONLY` por fechas. Status público mínimo, diagnóstico
con la clase, un evento de auditoría por fallo distinto sin material. Esquema 0, central 0, frontend 0.
Restaurar un respaldo y arrancar es la misma reverificación, probada copiando filas a una base nueva.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `LICENCIA-ESTADO-SIN-REVERIFICAR` — **ejecutado y convergido** (`specs/010-licenciamiento-central/spec004-licencia-estado-reverificado-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Candidatas técnicas sin decisión pendiente: `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`,
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`,
`PICKLIST-DUPLICADA-500`, `ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`.
Pendientes de la dueña: `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`. MASTER57 y SPEC057 sin cambio.

## 2026-10-08 · CENTRAL-SYNC-SIN-LIMITE-DE-TASA convergida: el endpoint de desafío tiene límite de tasa (dueña 004)

El endpoint pre-autenticación que emite desafíos admite ahora una capacidad global por ventana
deslizante (120 por 60 s por defecto, configurable, imposible de apagar en producción), contada sobre
las filas que la autoridad ya persiste en PostgreSQL: sin tabla nueva, sin memoria por proceso, sin
Redis, exacto entre trabajadores y sin un modo de fallo propio. Con la ventana llena responde un 429
genérico con `Retry-After` determinista, igual para una identidad conocida o desconocida, antes de
crear la fila y sin tocar los desafíos ya emitidos, que siguen autenticando; el cliente lo recibe como
un rechazo acotado sin reintentos ni retroceso, y la renovación en `READ_ONLY` sigue posible. Los
rechazos no inundan la auditoría: un aviso de registro por ventana, sin identidad del llamador. La IP
de origen no se usa porque no hay contrato de proxy de confianza: el límite por origen va en la
pasarela del operador, documentado, junto con la advertencia de que esto no es protección volumétrica.
Esquema central 0, cliente 0, frontend 0; sync autenticado, rotación, reverificación y orden intactos.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `CENTRAL-SYNC-SIN-LIMITE-DE-TASA` — **ejecutado y convergido** (`specs/010-licenciamiento-central/spec004-central-sync-rate-limit-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Candidatas técnicas sin decisión pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`, `E2E-SIN-TYPECHECK`. Pendientes de la
dueña: `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`. MASTER57 y SPEC057 sin cambio.

## 2026-10-08 · BACKEND-KEEPALIVE-5S convergida: no había latido, había un valor por defecto (dueña 054)

El descubrimiento primero: no existe en KONTROL ningún sondeo, temporizador ni *keepalive* de cinco
segundos. El único `refetchInterval` del frontend es la campana de notificaciones (60 s, Spec 047), el
dashboard lee el health una vez al montar, y ni el backend ni la autoridad tienen temporizadores. El
«mecanismo de 5 s» es el `timeout_keep_alive` por defecto de uvicorn —cuánto conserva el servidor una
conexión HTTP ociosa— que coincide con los 5 s del agente de Node, de modo que una petición enviada en
ese instante por una conexión reutilizada recibe `ECONNRESET` o se queda sin respuesta. Es el caso
«keep-alive HTTP del servidor», no un problema de producto: no viaja ninguna petición, no toca base,
sesión ni licencia. Los cinco arranques de uvicorn del repositorio (las dos imágenes, el `dev` con
`--reload`, el backend y la autoridad de la corrida E2E, y el README) fijan ahora `--timeout-keep-alive
75`, por encima de Node y del `keepalive_timeout` de upstream de nginx, con una sonda y una prueba que
arrancan uvicorn con la orden exacta de las imágenes: 20/20 conexiones cerradas a los 5,3 s antes,
0/20 después. Frontend, sesión, licencia, health, nginx y esquema sin cambio.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `BACKEND-KEEPALIVE-5S` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-backend-keepalive-delta.md`). Siguiente, fijado por la dueña: **`PANEL-VERSION-VACIA`** — **no iniciada** (sigue `OPEN` hasta el próximo encargo) |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Candidatas técnicas sin decisión pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-DESPLEGABLES-TRUNCADOS`, `PICKLIST-DUPLICADA-500`,
`ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`, `E2E-SIN-TYPECHECK`,
`E2E-PANTALLA-SIN-PINTAR`. MASTER57 y SPEC057 sin cambio.

## 2026-10-08 · PANEL-VERSION-VACIA convergida: la versión tiene una autoridad y la tarjeta la pinta a quien puede verla (dueña 001)

La tarjeta «Versión» de Inicio pedía la versión a `/health/ready`, que nunca la trajo, y por eso
mostraba «—» siempre; el tipo del frontend declaraba campos que ese endpoint nunca tuvo. El
descubrimiento fijó primero qué significa el campo —la **versión del producto**, la que FR-001-084
pide al diagnóstico y la que ADR-D0-006 llama «versión del producto» en la solicitud de activación— y
quién manda: `app/__init__.py:__version__`, lo único que viaja dentro del artefacto desplegado, que
`pyproject.toml` refleja con un guard y de la que los ajustes se derivan sin literal propio ni puerta
de entorno. La tarjeta pide ahora el diagnóstico solo a quien tiene `license:view` y pinta la versión,
«Cargando…» o «No disponible»; sin permiso no existe, como el enlace a «Mi licencia». La raíz pública
`/` deja de publicar la versión, por la misma decisión que la retiró de `/health/live`. Sin hash de
commit, sin `.git` ni `git` en tiempo de ejecución, sin comparador de versiones, sin esquema, sin
cambio en health, diagnóstico, licencia, sync ni keep-alive.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `PANEL-VERSION-VACIA` — **ejecutado y convergido** (`specs/001-fundacion/spec001-panel-version-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Candidatas técnicas sin decisión pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`OFFLINE-NAIVE-EN-SQLITE`, `E2E-PANTALLA-SIN-PINTAR`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`PICKLIST-DUPLICADA-500`, `ROLES-SIN-API-DE-ALTA`, `E2E-CUARENTA-OMITIDAS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`, `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`,
`E2E-SIN-TYPECHECK`. Fuera de ciclo y pendiente de la dueña: el 502 de `kontrol.globaldv.net`
(backend caído en el servidor; requiere acceso y autorización). MASTER57 y SPEC057 sin cambio.

## 2026-10-12 · OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD convergida: el contrato declara la autenticación que ya existía (dueña 001)

Las 543 operaciones del OpenAPI se publicaban sin `security` y sin `securitySchemes`, porque la
autenticación se leía a mano de la cabecera. El descubrimiento fijó el mecanismo real —un JWT de
acceso en `Authorization: Bearer`, con el refresh en cookie HttpOnly que solo consume `/auth/refresh`,
sin CSRF— y la partición real del runtime leída del árbol de dependencias: 532 operaciones protegidas y
11 públicas (health, bootstrap, estado de licencia, login/refresh/logout/recuperación, raíz). La
solución es framework-native y no duplica nada: la misma dependencia que autentica recibe la
credencial de un `HTTPBearer` con la semántica exacta del analizador anterior, y FastAPI deriva de él
`securitySchemes.BearerAccessToken` (`http`/`bearer`/`JWT`) y el `security` de cada operación protegida.
Sin OAuth2 ni scopes, sin apiKey, sin seguridad global, sin lista manual de rutas; `X-Kontrol-Company`
sigue siendo contexto de empresa, no credencial. El runtime no cambió: 401/403, permisos, alcance,
login, logout, setup, health, licencia, sync, límite de tasa, reverificación, keep-alive y panel de
versión intactos; esquema 0, frontend 0, Autoridad Central fuera (no publica OpenAPI).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD` — **ejecutado y convergido** (`specs/001-fundacion/spec001-openapi-seguridad-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Candidatas técnicas sin decisión pendiente: `ROLES-SIN-API-DE-ALTA`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`OFFLINE-NAIVE-EN-SQLITE`, `E2E-PANTALLA-SIN-PINTAR`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`PICKLIST-DUPLICADA-500`, `E2E-CUARENTA-OMITIDAS`, `MIGRACIONES-URL-CON-PORCENTAJE`,
`INSTALACION-KEY-REFERENCE-120`, `E2E-SIN-TYPECHECK`. Fuera de ciclo y pendiente de la dueña: el 502 de
`kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-12 · ROLES-SIN-API-DE-ALTA convergida: alta de roles personalizados por API (dueña 003)

El catálogo declaraba `roles:create` y nadie lo exigía: la API listaba y asignaba roles, pero no creaba
ninguno ni asociaba permisos a un rol; el E2E los escribía en la base con un guion. `POST /roles` cierra
el hueco con lo que el modelo ya definía: sesión y `roles:create`; roles del catálogo de la instalación,
opcionalmente acotados a una empresa del tenant del actor (404 si no lo es); permisos nombrados como
`recurso:accion` y todos del catálogo (uno desconocido rechaza el alta entera); identidad `(code,
company_id)` con 409 también bajo concurrencia, serializada con el candado consultivo que el repositorio
ya usa (sin migración); `protected`, `status` y `created_by` del servidor; rol y permisos en una sola
transacción; auditoría `ROLE_CREATED`; ningún usuario queda asignado. Hereda `BearerAccessToken` en el
OpenAPI (544 operaciones, 533 protegidas, las 11 públicas iguales). Sin CRUD completo, sin permisos
nuevos, sin esquema, sin frontend. Deuda nueva, abierta y de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`
(ningún punto del modelo fija si quien crea o asigna roles puede otorgar permisos que no posee; hoy
no hay techo, y fijarlo es una política nueva).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `ROLES-SIN-API-DE-ALTA` — **ejecutado y convergido** (`specs/001-fundacion/spec001-roles-alta-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendiente de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`. Candidatas técnicas sin decisión
pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `OFFLINE-NAIVE-EN-SQLITE`, `E2E-PANTALLA-SIN-PINTAR`,
`ALMACENES-CARRERA-SQLITE-HILOS`, `PICKLIST-DUPLICADA-500`, `E2E-CUARENTA-OMITIDAS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`, `E2E-SIN-TYPECHECK`. Fuera de ciclo:
el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-12 · E2E-CUARENTA-OMITIDAS convergida: las 40 omitidas, identificadas y resueltas una a una (dueña 054)

La corrida global canónica terminaba en 236 / 0 / 40 omitidas. Las 40 eran cinco `test.skip` condicionales
(`!USER || !PASSWORD`) en accesibilidad (21 rutas, 008, 011, 046) y documentos (8), y una sola causa real
demostrada: el runner fijaba la contraseña y no `KONTROL_E2E_USER`, mientras los otros veinte ficheros
escriben `?? "admin"`. Con la sola variable, 36 pasan; 4 fallan porque la carga exige un análisis `CLEAN` y
en QA no hay `clamscan` (`SCAN_FAILED`, falso seguro FR-046-072). El runner exporta ahora el usuario (la
misma identidad con la que comprueba el backend) y declara si hay analizador; las cuatro pruebas se omiten
con nombre, causa y dueña 046 solo donde no lo hay. 36 CERTIFY · 4 DECLARE_DEBT (`ENTORNO-SIN-CLAMSCAN`,
abierta) · 0 reescritas · 0 eliminadas · 0 bloqueadas · `UNKNOWN` 0. Dos globales consecutivas
272 / 0 / 4, 17 mutaciones muertas, producto 0, Firefox/WebKit sin cambio (no estaban entre las 40).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `E2E-CUARENTA-OMITIDAS` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-e2e-cuarenta-omitidas-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendiente de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`. Candidatas técnicas sin decisión
pendiente: `E2E-SIN-TYPECHECK`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `TEST-PG-UN-SCHEMA-POR-PRUEBA`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`, `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`PICKLIST-DUPLICADA-500`, `MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`. De entorno:
`ENTORNO-SIN-CLAMSCAN` (ahora con 4 pruebas E2E nombradas esperándola). Fuera de ciclo: el 502 de
`kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-12 · E2E-SIN-TYPECHECK convergida: `e2e/` entra en el gate de tipos (dueña 054)

`tsc -b` recorría `src` y `vite.config.ts`; las 52 suites y ayudantes de `e2e/` y `playwright.config.ts`
se transpilaban sin comprobarse. Medido antes de tocar nada: un error sintético pasaba `npm run typecheck`,
y un experimento con la severidad de `src` más los tipos de Node encontró 4 errores reales, todos de una
raíz (una unión «array o sobre» del listado de empresas, obsoleta desde el sobre `{items}` de 2026-09-30).
Diseño derivado del grafo existente: tercer proyecto `tsconfig.e2e.json` —el patrón ya ratificado para
`tsconfig.node.json`—, Node + DOM + Playwright, misma severidad, `noEmit`, referenciado desde la solución,
de modo que el gate canónico lo recorre sin guion nuevo y el build no emite nada de E2E (`dist` idéntico).
El tipo obsoleto se corrigió sin tocar aserciones; seis pruebas de contrato vigilan referencia, cobertura
real (resolución de `tsc` contra el disco), `noEmit`, entorno, severidad y supresores. 11/11 mutaciones
muertas; typecheck 11,6 s (+1,9 s); Vitest 473/473; E2E dirigida 7/7 y dos globales 272 / 0 / 4; producto 0.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `E2E-SIN-TYPECHECK` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-e2e-sin-typecheck-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendiente de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`. Candidatas técnicas sin decisión
pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `TEST-PG-UN-SCHEMA-POR-PRUEBA`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`, `OFFLINE-NAIVE-EN-SQLITE`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`PICKLIST-DUPLICADA-500`, `MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`. De entorno:
`ENTORNO-SIN-CLAMSCAN`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-12 · PICKLIST-DUPLICADA-500 convergida: el segundo plan vivo es un 409 de dominio (dueña 031)

Reproducido antes de tocar nada: en PostgreSQL el segundo `POST /sales/pick-lists` era un 500
(`UniqueViolation` de `uq_pick_lists_active_order` sin traducir; con diez hilos, un 200 y nueve 500); en
SQLite, sin ese índice parcial, persistía un segundo plan vivo en silencio. El contrato ya estaba escrito
(«un solo plan activo por pedido», predicado del índice = `PLAN_ACTIVE_STATUSES`), así que no hubo decisión
de producto: comprobación previa con el alcance de la empresa, 409 `PICKLIST_DUPLICATE` con el plan vigente
en `details`, inserción en savepoint con el índice como respaldo final traducido solo cuando es esa
violación (el patrón de la moneda funcional, el hermano con constraint real), sin candado, sin migración, sin
`except` amplio; un pedido ajeno sigue siendo 404 y 401/403 van por delante. 14 pruebas backend (2 y 10
hilos, carrera simulada contra el índice, otra violación de integridad que no se disfraza, estados terminales
que liberan) + 1 escenario E2E; 10/10 mutaciones muertas; suites completas sin regresión; E2E 273/0/4 en
dos globales consecutivas tras clasificar, con prueba independiente, dos globales afectadas por
`E2E-PANTALLA-SIN-PINTAR` (sigue OPEN; el host tenía una VPN activa). Frontend de producto 0.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `PICKLIST-DUPLICADA-500` — **ejecutado y convergido** (`specs/005-ventas-cuentas-por-cobrar/spec031-picklist-duplicada-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendiente de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`. Candidatas técnicas sin decisión
pendiente: `E2E-PANTALLA-SIN-PINTAR` (volvió a manifestarse hoy en dos globales: dos fallos por corrida,
siempre el formulario de acceso sin pintar), `OFFLINE-NAIVE-EN-SQLITE`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`, `LISTADOS-SIN-TOPE`. De entorno:
`ENTORNO-SIN-CLAMSCAN`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · E2E-PANTALLA-SIN-PINTAR: NOT REPRODUCED, captura diagnóstica en el arnés (dueña 054)

Se buscó la causa del formulario de acceso sin pintar antes de tocar nada. El grafo de arranque descarta
que una petición previa lo bloquee (`/login` queda fuera del guardia y los providers renderizan siempre):
solo un módulo de Vite que no llega lo explica, y la única traza histórica (2026-10-06) muestra
exactamente eso, seis módulos abortados con `ERR_NETWORK_CHANGED`. Hoy, con traza retenida, una global
canónica, una en serie y tres dirigidas de las suites históricas dieron 0 fallos en ≈730 ejecuciones, con
la huella de red idéntica y el reloj coherente: los fallos del 2026-10-12 quedan sin causa por falta de
captura, y esa es la carencia que se cierra. La configuración canónica retiene traza y captura solo al
fallar (en verde se descarta, +0,1 min), y el runner anota en el manifiesto el estado de red sin
direcciones y el desvío pared/monotónico, avisando sin abortar. Producto 0; tiempos, reintentos,
trabajadores, esperas y omisiones intactos (ahora con un contrato que lo vigila). La deuda sigue OPEN.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `E2E-PANTALLA-SIN-PINTAR` — **ejecutado: NOT REPRODUCED** (`specs/012-auditoria-integral-e2e/spec054-e2e-pantalla-sin-pintar-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`; y la política del arnés ante red
cambiada o reloj saltado (avisar, como hoy; abortar antes de la suite; o invalidar la corrida sin contar
el fallo como de producto). Candidatas técnicas sin decisión pendiente: `OFFLINE-NAIVE-EN-SQLITE`,
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`,
`ALMACENES-CARRERA-SQLITE-HILOS`, `MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`,
`LISTADOS-SIN-TOPE`. De entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR` (OPEN, ahora con
captura). Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · OFFLINE-NAIVE-EN-SQLITE convergida: la tolerancia offline decide lo mismo en los dos motores (dueña 004)

Reproducido por HTTP con reloj fijo antes de tocar nada: sobre SQLite `GET /licensing/offline-status` y
`GET /licensing/overview` eran un 500 (`TypeError` naive/aware) con cualquier fecha confiable persistida;
sobre PostgreSQL, 200. `last_reliable_date` es un instante y el módulo ya tenía el criterio y los helpers
(`_as_utc` al leer, `_utc` al persistir, FR-010-323): `verify_offline` era el único lector que no los usaba.
Tres líneas en el servicio, sin migración ni reinterpretación histórica; las dos pruebas antiguas releen de
la base (por eso no lo veían). 12 pruebas con reloj fijo en ambos motores (frontera exacta: rechazo solo al
superar la gracia; zona del proceso irrelevante), 10/10 mutaciones muertas, suites completas sin regresión,
E2E canónica limpia, frontend 0.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OFFLINE-NAIVE-EN-SQLITE` — **ejecutado y convergido** (`specs/010-licenciamiento-central/spec004-offline-naive-sqlite-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red
cambiada o reloj saltado. Candidatas técnicas sin decisión pendiente: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, `ALMACENES-CARRERA-SQLITE-HILOS`,
`MIGRACIONES-URL-CON-PORCENTAJE`, `INSTALACION-KEY-REFERENCE-120`, `LISTADOS-SIN-TOPE`. De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`.
MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · MIGRACIONES-URL-CON-PORCENTAJE convergida: Alembic acepta una URL con «%» (dueña 052)

Reproducido antes de tocar nada: `config.set_main_option("sqlalchemy.url", …)` es `configparser`, y revienta
al asignar con cualquier credencial codificada (`ValueError: invalid interpolation syntax`); en PostgreSQL,
bases nuevas con `%40`, `%23`, `%25`, query con `%20` y usuario codificado fallaban en el cliente y en la
Autoridad Central (misma forma de `env.py`), y el camino canónico por subproceso salía con código 1: lo
primero que hace el contenedor al arrancar. Diseño derivado de los dos *runtimes* (`create_engine(settings
.db_url)` directo): la URL ya no entra en `configparser`; nada más cambia (revisiones 0, esquema 0,
`alembic.ini` 0, entrypoints 0, dependencias 0, contrato de `KONTROL_DB_URL` 0). 15 pruebas (la URL que
recibe SQLAlchemy es exactamente la lógica; cabezas declaradas; salida sin credenciales; entrypoints
migran antes de arrancar), 10/10 mutaciones muertas, N10 y runner verdes, una global E2E limpia con bases
migradas por `env.py`. Lo que QA no puede certificar con `trust` —la autenticación con una clave con `%`—
se dice.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `MIGRACIONES-URL-CON-PORCENTAJE` — **ejecutado y convergido** (`specs/001-fundacion/spec052-migraciones-url-con-porcentaje-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red
cambiada o reloj saltado. Candidatas técnicas sin decisión pendiente: `INSTALACION-KEY-REFERENCE-120`
(la otra deuda que puede impedir un arranque: `key_reference` de 120 caracteres), `LISTADOS-SIN-TOPE`,
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`,
`ALMACENES-CARRERA-SQLITE-HILOS`. De entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de
ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · INSTALACION-KEY-REFERENCE-120: bloqueada por decisión del contrato de almacenamiento (dueña 004)

Reproducido por el flujo real de instalación: con un volumen de 126 caracteres la referencia persistida
mide 155 y PostgreSQL rechaza el alta (`StringDataRightTruncation`); con ruta corta pasa; SQLite no hace
cumplir el largo. Inventario: un escritor (persiste la ruta absoluta del contenedor) y ningún lector —la
clave se carga siempre por configuración—, sin exposición. Contrato: solo «`key_reference (volumen)`» en el
modelo de datos; la Spec 010, DOC-07 y los ADR no definen el formato. Por eso no se implementó: ampliar la
columna es migración y ratificar una referencia relativa es un contrato nuevo de material criptográfico.
Opciones entregadas con pros y contras; recomendación A3 (referencia relativa al volumen, filas absolutas
respetadas, sin migración). Producto, esquema, filas y runner: sin cambio.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `INSTALACION-KEY-REFERENCE-120` — **ejecutado: BLOCKED BY LICENSE STORAGE CONTRACT DECISION** (`specs/010-licenciamiento-central/spec004-instalacion-key-reference-120-delta.md`); continúa con la decisión de la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `INSTALACION-KEY-REFERENCE-120` (A1/A2/A3/A4),
`ROLES-SIN-TECHO-DE-DELEGACION`, y la política del arnés E2E ante red cambiada o reloj saltado. Candidatas
técnicas sin decisión pendiente: `LISTADOS-SIN-TOPE`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`,
`TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, `ALMACENES-CARRERA-SQLITE-HILOS`. De
entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de
`kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · INSTALACION-KEY-REFERENCE-120 convergida con la decisión A3 de la dueña (dueña 004)

La dueña ratificó A3: `Installation.key_reference` guarda para las altas nuevas una referencia relativa
al volumen (`installation_private_key.pem`); las filas absolutas históricas se respetan tal cual; sin
migración, sin backfill, sin reescritura; la referencia la genera el producto y nunca se persiste material
de clave. Implementación mínima en el módulo de licenciamiento (constante, escritor, resolutor con rechazo
de recorridos de ruta), cargadores sin cambio (siguen por configuración; 0 lectores nuevos), contrato en
`data-model.md`, y el runner E2E sustituye su guarda de longitud por el invariante real comprobado contra la
base de la corrida. Pruebas KR-01…25 en ambos motores (PostgreSQL es la autoridad del largo), mutaciones,
suites completas y dos globales E2E en la evidencia.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `INSTALACION-KEY-REFERENCE-120` — **ejecutado y convergido** (`specs/010-licenciamiento-central/spec004-instalacion-key-reference-120-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red
cambiada o reloj saltado. Candidatas técnicas sin decisión pendiente: `LISTADOS-SIN-TOPE`,
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `TEST-PG-UN-SCHEMA-POR-PRUEBA`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`,
`ALMACENES-CARRERA-SQLITE-HILOS`. De entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de
ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.


## 2026-10-13 · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO convergida (dueña 054)

Ciclo de arnés, producto 0. El `conftest.py` del backend fijaba `KONTROL_INSTALLATION_VOLUME_PATH` en
una ruta constante por máquina y cada mundo de prueba reescribía allí `installation_private_key.pem`:
dos `pytest` a la vez se pisaban la clave y la sincronización firmaba con la clave ajena
(`SYNC_AUTH_INVALID`; reproducido en concurrencia real y de forma determinista antes de tocar nada).
Ahora cada proceso de `pytest` recibe una raíz `mkdtemp` única en `pytest_configure` (eliminada en
`pytest_unconfigure`) y cada módulo un volumen hijo vacío por una fixture `autouse` de módulo, con la
caché de `Settings` limpiada al fijar y al restaurar; la misma pareja de procesos que antes fallaba
pasa entera a la vez. Pruebas TV-01…TV-23 (sondas en procesos aparte, en serie y en paralelo; gestor de
contexto en proceso), 12/12 mutaciones, suites completas en ambos motores sin regresión y una global
E2E en la evidencia. `TEST-PG-UN-SCHEMA-POR-PRUEBA` no se absorbe; el runner E2E no cambia.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-test-volumen-de-instalacion-compartido-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red
cambiada o reloj saltado. Candidatas técnicas sin decisión pendiente: `TEST-PG-UN-SCHEMA-POR-PRUEBA`
(hermana directa de este ciclo: aislamiento del esquema PostgreSQL con el mismo patrón de ciclo de vida),
`LISTADOS-SIN-TOPE`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, `ALMACENES-CARRERA-SQLITE-HILOS`. De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Observaciones anotadas sin absorber: `KONTROL_STORAGE_PATH`
y `KONTROL_BACKUP_PATH` siguen fijos y compartidos en el arnés (el almacenamiento acumula exportaciones entre
corridas), y en `test_license_sync_client` `csync_02` depende de que `csync_01` haya configurado la Autoridad
en el mismo módulo. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · TEST-PG-UN-SCHEMA-POR-PRUEBA convergida (dueña 054)

Ciclo de arnés, producto 0. Doce suites `db_session` creaban en PostgreSQL un schema entero (203 tablas, 638
índices, ≈1,1 s de DDL) por cada prueba: 384 schemas y ≈323 000 relaciones por corrida. Tras medir ANTES, inventariar
commits, sesiones secundarias, hilos y secuencias (ninguna; claves de cadena) y probar una POC medida, el conftest
ofrece `sesion_de_prueba`: en PostgreSQL un schema por módulo (PGLIFE lo suelta con el módulo) y por prueba una
conexión propia con transacción externa y `Session(join_transaction_mode="create_savepoint")` —los `commit` del
código, de la prueba o del producto, solo sueltan un SAVEPOINT—; en SQLite, base en memoria nueva por prueba como
siempre. Las 12 suites la consumen (reescritura mecánica delegada a DeepSeek y auditada); las fixtures con
sesiones secundarias (`TestClient`) o hilos conservan su schema por prueba con razón explícita. Medido: 384 → 188
schemas (−51 %), 929,8 → 810,0 s (−12,9 %); aislamiento probado con pruebas adversariales en proceso y sondas en
procesos aparte (serie, paralelo, orden inverso, prueba sola, prueba que falla); 12/12 mutaciones; suites completas
en ambos motores sin regresión; una global E2E. `TEST-PG-CATALOGO-MARCA-DE-AGUA` solo se midió (sin delta: la marca
de agua ya está alcanzada) y sigue OPEN.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `TEST-PG-UN-SCHEMA-POR-PRUEBA` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-test-pg-un-schema-por-prueba-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: `LISTADOS-SIN-TOPE` (producto: listados sin tope, dueñas
008/031), `ALMACENES-CARRERA-SQLITE-HILOS`, `TEST-PG-CATALOGO-MARCA-DE-AGUA` (observación). De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Observaciones anotadas sin absorber: `KONTROL_STORAGE_PATH` y
`KONTROL_BACKUP_PATH` compartidos en el arnés; `csync_02` dependiente de `csync_01`; la hoja de ruta decía «trece»
suites y «1 129» relaciones: son 12 suites + 5 fixtures de función y 841 relaciones + 811 restricciones. Fuera de
ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · LISTADOS-SIN-TOPE convergida (dueñas 008 y 031)

Ciclo de contrato de producto, discovery-first. El inventario transversal de 177 `GET` de colección dio 17 listados
canónicos (`page`/`page_size` ≤ 100), 8 con `limit/offset` sin máximo y 79 con sobre falso (sin paginar). La convención
ratificada es la de la Spec 001 (`api-contracts.md:11`, transcrita como canon en las deltas de empresas y auditoría):
sobre `{items, total, page, page_size}`, `page_size` 1..100 (20), 422 fuera de rango, `total` antes de cortar, orden
con desempate por `id`. Reproducido con 1 100 listas y 300 almacenes sintéticos: pick-lists devolvía todo (203 KB) e
ignoraba `page`; almacenes aceptaba `limit=100000` y los negativos eran un 500 en PostgreSQL. Corregido sin migración ni
cambio de alcance: `limit` 1..100 y `offset` ≥ 0 en almacenes (defecto 50 y sobre WHL intactos), paginación canónica en
pick-lists; frontend (`listAllWarehouses`, espejo de `listAllCompanies`), E2E (recorrer páginas) y QA adaptados sin
relajar aserciones. 29 pruebas hostiles, 12/12 mutaciones, OpenAPI 544/533/11 con dos operaciones documentadas, suites
completas y dos globales E2E en la evidencia. Los otros 7 listados `limit/offset` y los 78 sobres falsos se registran
como `ADDITIONAL_UNBOUNDED_LISTING` (ver el delta §13) para que cada dueña decida.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `LISTADOS-SIN-TOPE` — **ejecutado y convergido** (`specs/008-almacenes-fisicos/spec008-listados-sin-tope-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: `ALMACENES-CARRERA-SQLITE-HILOS`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`
(observación, medida sin delta), `ADDITIONAL_UNBOUNDED_LISTING` (85 listados; por dueña). De entorno: `ENTORNO-SIN-CLAMSCAN`,
`E2E-PANTALLA-SIN-PINTAR`. Observaciones sin absorber: `ALMACENES-PAGINACION-LIMIT-OFFSET` (estilo de nombres no canónico en 8
listados), `KONTROL_STORAGE_PATH`/`BACKUP_PATH` compartidos en el arnés, `csync_02` dependiente de `csync_01`. Fuera de ciclo: el
502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

Observación añadida al cierre del ciclo `LISTADOS-SIN-TOPE`: en la primera global E2E del ciclo fallaron tres pruebas
(`approvals.spec.ts:496`, `empresa-helper.spec.ts:28` y `:45`) con «estado de empresa no determinable: activar=0
compuerta=0 activa=1 desactivar=1»: el ayudante `activarEmpresa` decide con `count()` instantáneos tras `networkidle` y
la tabla se pintó entre la decisión y el diagnóstico (familia de `E2E-PANTALLA-SIN-PINTAR`, con túnel VPN presente);
sin relación con almacenes ni pick-lists y con el backend limpio. Candidata `E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO`
(dueña 054): hacer que el ayudante espere a que el estado sea determinable (expectativas con auto-espera) en vez de
contar en el acto. No se absorbió; las dos globales siguientes fueron limpias.

## 2026-10-13 · E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO convergida (dueña 054)

Ciclo de arnés E2E, producto 0. Las tres trazas de la global `r20261013t151632…` muestran `networkidle` resuelto antes de
que la página emitiera la petición de la tabla de empresas (≈360 ms tras la ruta, bajo carga) y `desactivar.count()`
pasando de 0 a 1 en 140 ms: el ayudante decidía con una fotografía instantánea. Retrasar la respuesta con `page.route`
no lo reproduce (una petición en vuelo mantiene `networkidle` esperando); diferir la emisión del `fetch` en la propia
página sí, de forma determinista: HE-02 falló con la firma exacta contra el ayudante antiguo. Ahora `activarEmpresa`
(y la copia local de approvals, que comparte la primitiva) espera con `expect.poll` a que la pantalla muestre uno y
solo uno de sus estados —ACTIVA, INACTIVA, COMPUERTA; NO_LISTA es transitorio y AMBIGUO falla al agotar el tiempo
con el diagnóstico— y decide con esa misma lectura, en los 15 s de siempre, sin esperas fijas ni reintentos. HE-02…16,
contrato estático del arnés ampliado, 12 mutaciones, gates de frontend y dos globales E2E limpias en la evidencia.
`E2E-PANTALLA-SIN-PINTAR` (la familia general: página que no llega a pintarse) sigue OPEN.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-e2e-helper-empresa-carrera-de-pintado-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: `ALMACENES-CARRERA-SQLITE-HILOS`, `ADDITIONAL_UNBOUNDED_LISTING`
(85 listados, por dueña), `ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA` (observación). De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Observación nueva: `documents.spec.ts` y `documents-a11y.spec.ts` activan la
empresa con una copia reducida («si veo Activar, pulso») que no decide por estado; con la empresa ya activa no les afecta
la carrera, pero no comparten la primitiva. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-13 · ALMACENES-CARRERA-SQLITE-HILOS convergida (dueña 008; apoyo 054)

Ciclo de arnés de backend, producto 0. Reproducida antes de tocar nada: sola ×20 8 fallos, módulo ×10 4 fallos, nunca en
PostgreSQL. Sonda de eventos de motor: una única conexión pysqlite para todos los hilos (`make_engine()` en SQLite es
`:memory:` + `StaticPool` + `check_same_thread=False`); el `commit` de una petición cierra el cursor de la otra
(`ResourceClosedError`) o la violación única llega como `sqlite3.DatabaseError`, el servicio solo traduce
`IntegrityError`, el 500 mata el hilo y la prueba ve `[200]`; a veces el `rollback` del perdedor deshace la fila del
ganador (`[409]`, total 0). Entrelazado controlado con barrera antes de los dos INSERT: 5/5 fallos deterministas; la
misma carrera sobre un fichero SQLite temporal con una conexión por hilo: 35/35 limpias. Clasificación
`HARNESS_SHARED_CONNECTION`; P21 no excluye SQLite y `skip` está prohibido. Corrección solo de arnés:
`motor_para_hilos(nombre)` en `tests/conftest.py` (fichero temporal efímero, pool por defecto, sin tocar `busy_timeout`,
limpieza en `finally`; PostgreSQL sin cambio), adoptada por el fixture de `test_warehouse_structure.py`; la prueba
objetivo no cambia. ACS-01…12, 12/12 mutaciones, 50/50 corridas dirigidas, dos suites SQLite y una PostgreSQL sin
regresión, una global E2E limpia (280/0/4).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `ALMACENES-CARRERA-SQLITE-HILOS` — **ejecutado y convergido** (`specs/008-almacenes-fisicos/spec008-almacenes-carrera-sqlite-hilos-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: `AUTH-ROTACION-SQLITE-HILOS` (misma causa raíz presumible,
hoy 8–9 de 10 en solitario con firma `[200, 200]`; la primitiva ya existe), los otros módulos con hilos sobre la conexión
compartida (`test_uom_conversion`, `test_documents_security`; OBS-02), `WAREHOUSE-INTEGRITY-TRADUCE-TODO` (OBS-01, dueña
008), `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`. De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057
sin cambio.

## 2026-10-14 · AUTH-ROTACION-SQLITE-HILOS — BLOCKED BY PRODUCT DECISION (dueña 002 · Seguridad / sesiones, en 001; apoyo 054)

Ciclo de causa raíz, producto 0, arnés 0. Reproducida antes de tocar nada: sola ×20 en SQLite 15 fallos (`[200, 200]`
×8; `cannot commit transaction - SQL statements in progress` ×5; `StaleDataError` ×2), módulo ×10 3 fallos, PostgreSQL
×20 limpio. Sonda: una sola conexión pysqlite para los dos hilos (capa de ruido, la misma que cerró almacenes). Con
`motor_para_hilos` (dos conexiones, mismo datastore) el ruido desaparece y la prueba real pasa 20/20 **por
escalonamiento**; con las dos lecturas forzadas antes de la primera escritura, **ganan las dos renovaciones 5/5** (y 18/20
en natural con barrera de arranque) y queda una sesión viva huérfana: la garantía de un solo ganador se apoya solo en
`with_for_update()`, que PostgreSQL honra y SQLite ignora (pysqlite no retiene bloqueo entre leer y escribir). Caso H2 del
encargo: STOP antes de implementar. Producción no expuesta (P21). Opciones en
`specs/001-fundacion/evidence/auth-rotacion-sqlite-hilos/product-defect-report.md`: **A** UPDATE condicional + rowcount
(recomendada, independiente del motor, sin migración), C `BEGIN IMMEDIATE` en producto (no recomendada), **D** contrato
PostgreSQL-only con `skipif` (mínima, producto 0; precedente `test_license_import_race.py`), E2 arnés con `BEGIN IMMEDIATE`
(descartada: confianza falsa). En cualquier caso, adoptar `motor_para_hilos` en el fixture para que la prueba mida el
producto y no el arnés.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `AUTH-ROTACION-SQLITE-HILOS` — **BLOCKED BY PRODUCT DECISION**: el siguiente prompt continúa este bloqueo con la decisión de la dueña (A / C / D) |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: **`AUTH-ROTACION-SQLITE-HILOS` (A/C/D)**, `ROLES-SIN-TECHO-DE-DELEGACION`, la política
del arnés E2E ante red cambiada o reloj saltado. Candidatas técnicas sin decisión pendiente: OBS-02 (módulos con hilos
sobre la conexión compartida), `WAREHOUSE-INTEGRITY-TRADUCE-TODO`, `ADDITIONAL_UNBOUNDED_LISTING`,
`ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`. Observaciones nuevas: OBS-04 (la Spec 002 de
seguridad del inventario no tiene carpeta), OBS-05 (comentario de `rotate_session` sobre SQLite). De entorno:
`ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057
sin cambio.

## 2026-10-14 · AUTH-ROTACION-SQLITE-HILOS convergida con la decisión A (dueña 002 · Seguridad / sesiones, en 001; apoyo 054)

La dueña ratificó A (UPDATE condicional + rowcount). Diagnóstico antes de tocar producto: rowcount 1→0 en SQLite y
PostgreSQL; POC I1 en SQLite con el UPDATE exacto y conexiones independientes: 10/10 un `rowcount 1` y un `rowcount 0`,
sin `database is locked`, sin retry ni `BEGIN IMMEDIATE`. Implementación mínima en `rotate_session` (27 líneas): la
revocación es `UPDATE … WHERE id = :sid AND revoked_at IS NULL`; una fila → sigue el flujo (sesión nueva, auditoría, 200);
cero → 401 `SESSION_REVOKED` sin sesión nueva; `≠ 1` → invariante rota; `with_for_update()` se conserva; reloj canónico.
Arnés: `motor_para_hilos` en el fixture del módulo objetivo y en el módulo nuevo `tests/test_auth_rotacion_atomica.py`
(SA-01…16: I1 forzada en los dos motores → `[200, 401]` y un solo reemplazo; revocada, replay, expirada, hash, inactivo;
ORM; `OperationalError` sin remapear; excepciones de hilo visibles; contrato estático). Prueba objetivo intacta y ahora
20/20 sola, 10/10 módulo, 20/20 PostgreSQL. 14/14 mutaciones (M-11 sobrevivió a la primera pasada y se mató con una
prueba comportamental). Suites: SQLite 1627/42/1040 ×2 (42 ClamAV), PostgreSQL 2644/37/28, OpenAPI 544/533/11 sin cambio,
E2E 280/0/4. Comentario del servicio y cierre de REM-AUTH corregidos (OBS-05 cerrada en ese punto). Sin migración ni esquema.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `AUTH-ROTACION-SQLITE-HILOS` — **ejecutado y convergido** (`specs/001-fundacion/spec001-auth-rotacion-sqlite-hilos-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: OBS-02 (`test_uom_conversion`, `test_documents_security`
con hilos sobre la conexión compartida; la primitiva y el patrón SA ya existen), OBS-01 `WAREHOUSE-INTEGRITY-TRADUCE-TODO`,
`ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, OBS-06
(`KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH` compartidos), OBS-07 (`csync_02` → `csync_01`). OBS-04 (la Spec 002 del
inventario sin carpeta) para la dueña del inventario. De entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`.
Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-14 · OBS-02 · SQLITE-HILOS-REMANENTES convergida (dueña 054; funcionales 011 y 046)

Ratificada por la dueña. Inventario completo de pruebas con hilos (26 ficheros; UNKNOWN 0): el único objetivo real en
SQLite era `test_uom_conversion.py::test_concurrencia_una_sola_version_abierta`, que **no fallaba** pero pasaba en 5/30
corridas con un hilo muerto y sin versión creada: sobre la conexión compartida el rollback del perdedor deshacía el
trabajo del ganador y la aserción «una sola abierta» se cumplía con la versión original (falso verde). Con conexiones
propias sobre el mismo datastore (`motor_para_hilos`): 0 excepciones en 35 rondas y `[200, 409]` 5/5 con las dos
lecturas forzadas. Corrección solo de arnés: fixture sobre `motor_para_hilos("uom-conversion")`, la prueba exige el
vector completo y ninguna excepción de hilo (aserción funcional intacta), `test_el_historico…` resuelve la empresa por
la API antes de abrir su sesión de escritura (con conexiones propias se bloqueaba a sí misma: `database is locked`), y
el módulo nuevo `tests/test_uom_concurrencia_hilos.py` (I1 forzada en los dos motores, dos conexiones medidas,
excepciones visibles, contrato estático). Las seis carreras de `test_documents_security.py` quedan clasificadas
ENVIRONMENT_BLOCKED (422 `SCAN_FAILED` sin `clamscan`, antes de la carrera) y PostgreSQL por construcción
(`pg_backend_pid`): sin cambio; nueva OBS-08 (no declaran `skipif(not PG)`). 12/12 mutaciones; SQLite 1630/42/1040 ×2;
PostgreSQL 2647/37/28; OpenAPI 544/533/11; E2E 280/0/4; producto 0.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OBS-02 · SQLITE-HILOS-REMANENTES` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-obs02-sqlite-hilos-remanentes-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION` y la política del arnés E2E ante red cambiada o
reloj saltado. Candidatas técnicas sin decisión pendiente: OBS-01 `WAREHOUSE-INTEGRITY-TRADUCE-TODO`,
`ADDITIONAL_UNBOUNDED_LISTING`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`, `ALMACENES-PAGINACION-LIMIT-OFFSET`, OBS-06
(`KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH` compartidos), OBS-07 (`csync_02` → `csync_01`), OBS-08 (carreras de
documentos sin `skipif(not PG)`). OBS-03 sigue (solo tocada localmente); OBS-04 para la dueña del inventario. De
entorno: `ENTORNO-SIN-CLAMSCAN`, `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y
SPEC057 sin cambio.

## 2026-10-14 · OBS-08 convergida · ENTORNO-SIN-CLAMSCAN bloqueada por decisión de la dueña (dueña 046; apoyo 054)

Inicio ratificado por la dueña (solo investigar). Arquitectura: `FileSecurityScanner` con `ClamAVScanner` por `clamscan`,
falso seguro (`SCAN_FAILED`, nunca `CLEAN`), `DisabledScanner` declarado, `set_scanner` solo para pruebas; CL-046-09/FR-046-072
lo hacen capacidad configurable; la Spec 046 se certificó con ClamAV 1.4.3 real (ESC-046-01), sin guion en el repo; esta
máquina no lo tiene y `apt` exige privilegios. Inventario exacto con `--tb=line` y precedencia de subida probada: SQLite 42 =
35 del analizador + **7 de `test_documents_legacy_import.py` que no lo son** (OBS-10: `StaleDataError` por la conexión
pysqlite compartida más una petición HTTP con la sesión abierta; PostgreSQL los pasa); PostgreSQL 37 = 35 + 2 n9; E2E 4
cargas (runner `KONTROL_E2E_SCANNER_AVAILABLE=false`). Las carreras documentales son PostgreSQL-only por contrato
(FR-046-115, conc-046 «PostgreSQL decide», `tests/concurrency.py`, P21) y por implementación (`pg_backend_pid`,
`pg_stat_activity`, y dos que exigen bloqueo de fila, no de toda la base): **siete**, no seis. OBS-08 se cierra con el
marcador canónico y un contrato estático; ENTORNO-SIN-CLAMSCAN queda bloqueada: proveer ClamAV real en el QA canónico
(**A**, recomendada) o seguir declarando (B); C (doble `CLEAN`) y D (todo PostgreSQL-only) descartadas. SQLite 1637/33/1049
×2, PostgreSQL 2653/37/29, OpenAPI 544/533/11, E2E 280/0/4; producto 0; 10/10 mutaciones.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `ENTORNO-SIN-CLAMSCAN` — **BLOCKED BY OWNER DECISION** (A/B): el siguiente prompt continúa este bloqueo con la decisión; OBS-08 ejecutada y convergida en la misma delta (`specs/046-gestion-documental/spec046-document-security-clamav-pg-contract-delta.md`) |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Pendientes de decisión de la dueña: **`ENTORNO-SIN-CLAMSCAN` (A/B)**, `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E
ante red/reloj. Candidatas técnicas sin decisión pendiente: OBS-10 (`test_documents_legacy_import.py` sobre la conexión
compartida; `motor_para_hilos` y el patrón de ciclo de vida ya existen), OBS-01, OBS-06, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`,
`ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`. Observación nueva OBS-09 (la imagen de producción no
instala el analizador que el producto usa por defecto; dueña 046). De entorno: `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo:
el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-14 · ENTORNO-SIN-CLAMSCAN convergida con la decisión A + A2 (dueña 046; apoyo 054)

ClamAV real en el QA canónico sin privilegios: A2-POC en prefijo temporal (paquetes oficiales sin root con sumas
verificadas, 1.4.3, una sola biblioteca en el prefijo, firmas por `freshclam` en directorio de usuario, CLEAN rc 0, EICAR
rc 1, sin firmas rc 2) → `qa/clamav_qa.py` (`provisionar` idempotente, `preflight` QAC-01…08, `entorno`), `--con-analizador`
en el runner E2E (preflight antes de crear la base; rutas al backend; manifiesto con motor y firmas), `tests/test_clamav_qa.py`
(dobles del aprovisionamiento, nunca del análisis; reales con el marcador de las pruebas EICAR). Provisión real: 3 min 54 s,
caché 14 s. Con el analizador: PostgreSQL documentos + n9 + carreras 93 passed; SQLite completa 1679/8/1046 ×2 (quedan los 7
de OBS-10 y el intermitente de reloj, ahora OBS-11 con firma); PostgreSQL completa 2706/1/26; E2E 284/0/0 ×2; OpenAPI sin
cambio; 14/14 mutaciones; producto, `scanning.py` y producción intactos; nada en Git. Orden canónica: `python
qa/clamav_qa.py provisionar` · `eval "$(python qa/clamav_qa.py entorno)"` · suite PostgreSQL · `qa/e2e-run.py --con-analizador`.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `ENTORNO-SIN-CLAMSCAN` — **ejecutado y convergido** (`specs/046-gestion-documental/spec046-document-security-clamav-pg-contract-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base nuevas **con analizador**: SQLite 1679/8/1046 (7 OBS-10 + 1 OBS-11), PostgreSQL 2706/1/26 (OBS-11), E2E 284/0/0,
OpenAPI 544/533/11. Pendientes de decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E ante
red/reloj. Candidatas técnicas sin decisión pendiente: **OBS-10** (`test_documents_legacy_import.py` sobre la conexión
compartida: 7 rojos SQLite restantes), **OBS-11** (`test_sync_success_records_run_snapshot_and_event` dependiente del reloj
del módulo), OBS-01, OBS-06, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`; OBS-09 (imagen de producción sin analizador) para 046; OBS-04 para la dueña del
inventario; OBS-03 solo tocada localmente. De entorno: `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de
`kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-15 · OBS-10 · DOCUMENTS-LEGACY-IMPORT-SQLITE convergida (dueña 046; apoyo 054)

Ratificada por la dueña. Siete nodos exactos con una sola causa demostrada: la conexión pysqlite compartida de
`make_engine()` dejaba que el `ROLLBACK` de la sesión auxiliar de `_actor()` (y el commit/rollback de las peticiones HTTP
de `_company_id()`) descartaran la referencia que la prueba tenía insertada sin confirmar, y el `UPDATE` del servicio no
encontraba fila (`StaleDataError`). Con conexiones propias y el ciclo intacto aflora el bloqueo de toda la base (7×
`database is locked`); con la empresa y el actor resueltos antes de abrir la sesión de escritura, 8/8 en SQLite y en
PostgreSQL. Corrección solo de pruebas (fixture sobre `motor_para_hilos`, ayudantes con `company`, orden de los
identificadores, contrato estático por AST), aserciones intactas, producto 0; 12/12 mutaciones; dirigidas 34/34; SQLite
1692/1/1046 ×2; PostgreSQL 2712/1/26; E2E 284/0/0 con analizador. El único rojo de las suites es OBS-11.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OBS-10` — **ejecutado y convergido** (`specs/046-gestion-documental/spec046-obs10-legacy-import-sqlite-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base: SQLite 1692/1/1046 (OBS-11) · PostgreSQL 2712/1/26 (OBS-11) · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de
decisión de la dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E ante red/reloj. Candidatas técnicas sin decisión
pendiente: **OBS-11** (`test_sync_success_records_run_snapshot_and_event` compara con el instante de inicio del módulo; único
rojo en los dos motores), OBS-12 nueva (una SQLite completa tardó 2946 s frente a 587 s con resultados idénticos: carga de la
máquina; medir sensibilidad al tiempo), OBS-01, OBS-06, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`,
`ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`; OBS-09 para 046; OBS-04 para la dueña del inventario;
OBS-03 solo tocada localmente. De entorno: `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`.
MASTER57 y SPEC057 sin cambio.

## 2026-10-15 · OBS-11 · LICENSING-CENTRAL-SYNC-TIME-ASSERTION convergida (dueña 010; apoyo 054)

Ratificada por la dueña. Un solo nodo, única causa demostrada: la referencia de módulo `SERVER_TIME` (importación + 5 min)
hacía de frontera de una operación posterior; con el módulo envejecido más de cinco minutos (toda suite completa) la
activación quedaba por delante del reloj del servidor falso y el producto, monótono como exige FR-010-003, conservaba la
activación. Matriz de envejecimiento determinista sin sleep (FAIL desde 5 min en SQLite y PostgreSQL), control de frontera
de operación 8/8 y verdadero negativo PASS. Corrección solo de pruebas: el transporte falso captura su reloj al construirse y
la prueba compara con él; seis regresiones nuevas (envejecida, monótona, contrato estático, centinela del reloj canónico);
13/13 mutaciones; dirigidas verdes en los dos motores; SQLite 1699/0/1046 ×2; PostgreSQL 2719/0/26; E2E 284/0/0 con
analizador; OpenAPI 544/533/11; producto 0. **Las suites completas quedan sin ningún rojo.** OBS-12 no se absorbe; las
duraciones de este ciclo fueron normales (601 s, 610 s, 1459 s).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OBS-11` — **ejecutado y convergido** (`specs/010-licenciamiento-central/spec010-obs11-sync-time-anchor-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base: SQLite 1699/0/1046 · PostgreSQL 2719/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E ante red/reloj. Candidatas técnicas sin decisión pendiente:
OBS-12 (duración anómala de una SQLite completa: 2946 s frente a ≈ 600 s; medir sensibilidad al tiempo y a la carga),
OBS-01, OBS-06, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`; OBS-09 para 046; OBS-04 para la dueña del inventario; OBS-03 solo tocada localmente. De
entorno: `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-15 · OBS-12 · SUITE-DURATION-VARIABILITY convergida (dueña 054)

Ratificada por la dueña como ciclo de medición y observabilidad. Las corridas instrumentadas de hoy son normales (SQLite
581,6 s; PostgreSQL 1356,5 s) y se descomponen sin resto: analizador real 6,4 s por proceso (55 % / 39 %, coste estable de
seguridad), procesos reales ≈ 15 %, coste estructural del esquema por prueba en PostgreSQL, esperas legítimas < 2 %; ningún
techo ni `busy_timeout` consumido; sin contención del anfitrión. El 2946 s histórico no se reprodujo y no tenía telemetría:
queda como atípico con telemetría insuficiente, sin causa inventada. Desde ahora la certificación backend canónica con
telemetría es `qa/suite_tiempos.py --motor sqlite|postgres --con-analizador` (duración monotónica, perfil, anfitrión
saneado, anomalía no bloqueante; `qa/backend-runs/` fuera de Git); O12-01…20, 13/13 mutaciones; SQLite 1719/0/1046 ×2,
PostgreSQL 2739/0/26, E2E 284/0/0, OpenAPI 544/533/11; producto 0.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OBS-12` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-obs12-suite-duration-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base: SQLite 1719/0/1046 · PostgreSQL 2739/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E ante red/reloj. Candidatas técnicas sin decisión pendiente:
OBS-01, OBS-06, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`, `TEST-PG-CATALOGO-MARCA-DE-AGUA`;
OBS-09 para 046; OBS-04 para la dueña del inventario; OBS-03 solo tocada localmente. De entorno: `E2E-PANTALLA-SIN-PINTAR`.
Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-15 · OBS-06 · HARNESS-SHARED-STORAGE-PATHS convergida (dueña 054)

Ratificada por la dueña. Demostrado con sondas en procesos hijos: el almacén y los respaldos de las pruebas eran una ruta
fija por máquina compartida entre procesos y corridas, con visibilidad cruzada, colisión real de nombres de exportación
(marca de un segundo), persistencia no requerida y sin limpieza; la configuración se captura después de `pytest_configure`,
así que la corrección es solo del arnés: una raíz por proceso (`kontrol-test-almacen-*`) con `storage/` y `backups/`,
eliminada al cerrar, nunca heredada; sondas y O06-01…20; 14/14 mutaciones; OBS-12 ampliada con el modo de almacén, el
residuo por proceso y el almacén legado (informativo). Certificación por `qa/suite_tiempos.py`: SQLite 1739/0/1046 ×2,
PostgreSQL 2759/0/26, E2E 284/0/0, OpenAPI 544/533/11; producto 0. Durante la certificación el equipo se suspendió dos
veces y el contrato de OBS-12 lo registró (`salto: true`, desvíos de 25 917 s y 1550 s) sin alterar ningún veredicto. El
almacén fijo histórico `<tmp>/kontrol-test-storage` se conserva como legado; borrarlo es una acción manual aparte.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | `OBS-06` — **ejecutado y convergido** (`specs/012-auditoria-integral-e2e/spec054-obs06-shared-storage-paths-delta.md`); el siguiente ciclo técnico lo elige la dueña |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base: SQLite 1739/0/1046 · PostgreSQL 2759/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, política del arnés E2E ante red/reloj, retirada del almacén legado. Candidatas
técnicas sin decisión pendiente: OBS-01, OBS-07, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`; OBS-09 (imagen de producción sin analizador) para 046 con decisión de la dueña; OBS-04 para
la dueña del inventario; OBS-03 solo tocada localmente. De entorno: `E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de
`kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-18 · OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER (dueña 046; apoyo 052, 054) — implementada, bloqueada por entorno

Opción B ratificada: `clamd` como servicio separado y el backend transmite cada documento por INSTREAM. Implementado y
certificado todo lo demostrable sin contenedores: adaptador con falso seguro en toda rama y sin alternativa implícita,
selección explícita por configuración, servicio en `compose.yaml` con imagen propia y límites ≥ 50 MiB, QA con el demonio
real (1.4.3, 50 MiB en 1,6 s frente a 6,4 s por proceso de `clamscan`), O09 y CLAMD-QA, 16/16 mutaciones, SQLite 1783/0/1046 ×2,
PostgreSQL 2803/0/26, E2E 284/0/0, OpenAPI sin cambio. El equipo de QA no tiene `docker`/`podman` ni `sudo`: la
construcción de la imagen y el `compose up` reales quedan para un equipo con Docker (lista exacta en
`docs/evidence/docker-validation-checklist.md`). Regla de orquestación mandatoria desde hoy: Claude diseña y escribe el brief,
DeepSeek escribe todo el código y las pruebas, Claude audita, aplica y certifica (T08-DOC fue la primera tarea así).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09 (continuación)**: evidencia de composición en un equipo con Docker, o decisión de la dueña sobre dónde ejecutarla |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio (no se elige 018, 047, 048, 057 ni ninguna otra) |

Líneas base: SQLite 1783/0/1046 · PostgreSQL 2803/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: dónde ejecutar la composición de OBS-09; `ROLES-SIN-TECHO-DE-DELEGACION`; política del arnés E2E ante red/reloj.
Candidatas técnicas: OBS-01, OBS-07 (csync), `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`,
`TEST-PG-CATALOGO-MARCA-DE-AGUA`; OBS-04 para la dueña del inventario; OBS-03 solo tocada localmente. De entorno:
`E2E-PANTALLA-SIN-PINTAR`. Fuera de ciclo: el 502 de `kontrol.globaldv.net`. MASTER57 y SPEC057 sin cambio.

## 2026-10-18 · OBS-07 · CSYNC-AISLAMIENTO convergida (dueña 004, carpeta 010; apoyo 054) · OBS-09 sigue esperando evidencia

Seleccionada por evidencia entre nueve deudas abiertas: la única con causa demostrable, alcance acotado, sin decisión de la
dueña y sin solape con OBS-09 (matriz en `evidence/obs07-csync-aislamiento/candidate-matrix.md`; OBS-01 es más grave pero su
registro exige decidir qué contesta el servicio fuera de PostgreSQL). El módulo CSYNC compartía un mundo de módulo: 10/13
pruebas fallaban solas y 11/13 en orden inverso. Ahora cada prueba parte de bases nuevas con precondiciones explícitas; una
regresión lo demuestra. Orquestación: Claude diseñó, escribió los briefs, auditó (3 rechazos con hallazgos exactos), aplicó y
certificó; DeepSeek escribió todo el código de prueba (5 llamadas, $0,026). SQLite 1800/0/1046 ×2, PostgreSQL 2820/0/26,
E2E 284/0/0, OpenAPI 544/533/11. OBS-09: IMPLEMENTATION IN PROGRESS — BLOCKED BY ENVIRONMENT, sin cambio.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09 (cierre)** en cuanto llegue `OBS09_EXTERNAL_DOCKER_EVIDENCE`; si no llega, la siguiente deuda independiente por matriz |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1800/0/1046 · PostgreSQL 2820/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: OBS-01 (respuesta fuera de PostgreSQL), `ROLES-SIN-TECHO-DE-DELEGACION`, `ADDITIONAL_UNBOUNDED_LISTING`,
`ALMACENES-PAGINACION-LIMIT-OFFSET`, OBS-04, política del arnés E2E ante red/reloj. Observaciones sin efecto demostrado:
`TEST-PG-CATALOGO-MARCA-DE-AGUA`, OBS-03 (guía). MASTER57 y SPEC057 sin cambio.

## 2026-10-18 · OBS-01 · WAREHOUSE-INTEGRITY-TRADUCE-TODO convergida (dueña 008; apoyo 001) · OBS-09 sigue esperando evidencia

La dueña resolvió la decisión pendiente: solo la violación única reconocida de la restricción del código es 409 de dominio, y
cualquier otro `IntegrityError` se relanza al 500 `INTERNAL_ERROR` saneado, en PostgreSQL y en SQLite. El defecto se reprodujo
sin dobles: una clave foránea rota se contestaba como «ya existe». La corrección clasifica por restricción en los dos motores y
conserva los códigos y mensajes del duplicado. Orquestación: Claude diseñó, escribió los briefs, auditó (2 rechazos y una
reclasificación), aplicó y certificó; DeepSeek escribió todo el código y las pruebas (4 llamadas, $0,023). SQLite
1814/0/1046 ×2, PostgreSQL 2834/0/26, E2E 284/0/0, OpenAPI 544/533/11. OBS-09: IMPLEMENTATION IN PROGRESS — BLOCKED BY
ENVIRONMENT, sin cambio.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09 (cierre)** en cuanto llegue `OBS09_EXTERNAL_DOCKER_EVIDENCE`; si no llega, rederivar la matriz entre las deudas restantes |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1814/0/1046 · PostgreSQL 2834/0/26 · E2E 284/0/0 · OpenAPI 544/533/11. Pendientes de decisión de la
dueña: `ROLES-SIN-TECHO-DE-DELEGACION`, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET`, OBS-04, política
del arnés E2E ante red/reloj. Observaciones: OBS-03 (guía), `TEST-PG-CATALOGO-MARCA-DE-AGUA` (sin efecto demostrado),
`branch_id` del alta de almacén sin validar contra la empresa (no medido). MASTER57 y SPEC057 sin cambio.

## 2026-10-19 · WAREHOUSE-BRANCH-CROSS-COMPANY implementada (dueña 008) · E2E bloqueada por el entorno · OBS-09 sigue esperando evidencia

Ruta B: sin `OBS09_EXTERNAL_DOCKER_EVIDENCE`. La observación de `branch_id` se midió antes de tratarla como deuda. Un usuario
de la empresa A podía colgar almacenes de A de sucursales de B o de otro tenant, en el alta y en la edición. Se corrigió con el
contrato vigente: 404 `BRANCH_NOT_FOUND`, como en establecimientos. SQLite 1831/0/1046 ×2, PostgreSQL 2851/0/26 y OpenAPI
544/533/11 están verdes.

La E2E dio 275/5 dos veces. Las 5 fallidas son de carga documental, y el producto de `HEAD` falla igual. Se midió la vida de
clamscan, hasta 33 s, con 311 MB de memoria disponible en el equipo. Orquestación: 4 llamadas a DeepSeek ($0,014). OBS-09 no
cambia.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09 (cierre)** si llega `OBS09_EXTERNAL_DOCKER_EVIDENCE`; si no, **cerrar WAREHOUSE-BRANCH-CROSS-COMPANY** con la E2E en un equipo sin presión de memoria y, después, `WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY` |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1831/0/1046 · PostgreSQL 2851/0/26 · E2E 284/0/0, la última verde, en `e8501f2` · OpenAPI 544/533/11.
Decisiones pendientes de la dueña:
- `ROLES-SIN-TECHO-DE-DELEGACION`, `ADDITIONAL_UNBOUNDED_LISTING`, `ALMACENES-PAGINACION-LIMIT-OFFSET` y OBS-04.
- La política del arnés E2E ante red, reloj y ahora memoria del equipo.
- La revisión de filas cruzadas existentes.

## 2026-10-19 · WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY implementada (dueña 008) · E2E bloqueada por el entorno · OBS-09 sigue esperando evidencia

Ruta C, el ciclo dedicado. Las ubicaciones y zonas de una empresa aceptaban tipos de catálogo de otra empresa o de otro tenant.
Ahora los rechaza un 404 idéntico para ajeno, otro tenant e inexistente, en las cinco rutas de alta, alta masiva y edición.
SQLite 1859/0/1046 ×2, PostgreSQL 2879/0/26, 28 dirigidas, 17/17 mutaciones y OpenAPI 544/533/11 están verdes.

La E2E se ejecutó una vez, cuando el equipo pasó a ser apto, y dio 273/7. Las 7 fallidas venían de un pool agotado en el
middleware de licencia durante una ráfaga de paginación, sin traza en el código cambiado. Orquestación: 4 llamadas a DeepSeek
($0,036).

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09** si llega evidencia; si no, **una E2E con el equipo estable**, que cerraría WAREHOUSE-BRANCH-CROSS-COMPANY y WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY a la vez (mismo árbol); después, rederivar |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1859/0/1046 · PostgreSQL 2879/0/26 · E2E 284/0/0, la última verde, en `e8501f2` · OpenAPI 544/533/11.
Observaciones nuevas: `E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING`, no demostrada como defecto.

## 2026-10-19 · WAREHOUSE-BRANCH-CROSS-COMPANY y WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY convergidas (dueña 008) · OBS-09 sigue esperando evidencia

La E2E global, ejecutada una vez con el equipo apto, dio **284/0/0** y limpieza LIMPIA (`r20261019t030105p679326nda98b2`). Cierra las dos deudas, que
están en el mismo árbol, sin cambio de código. Se reutiliza la certificación backend de `f93232b`: SQLite 1859/0/1046 ×2,
PostgreSQL 2879/0/26 y OpenAPI 544/533/11. Las fugas multiempresa y multitenant de sucursal y de tipos de catálogo quedan
cerradas.

El pool agotado del ciclo anterior **no se reprodujo**, pese a una presión de memoria comparable: 886 MB mínimos y 6,8 GB de
swap. La observación `E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING` sigue abierta, sin causa demostrada.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09** si llega `OBS09_EXTERNAL_DOCKER_EVIDENCE`; si no, rederivar la matriz entre las deudas restantes, sin implementar en el mismo ciclo |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1859/0/1046 · PostgreSQL 2879/0/26 · **E2E 284/0/0 en `f93232b`** · OpenAPI 544/533/11.

## 2026-10-19 · E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING: causa demostrada (diagnóstico 054; corrección 001) · OBS-09 sigue esperando evidencia

Ciclo de diagnóstico, sin cambio de producto. El middleware de licencia es `async`, pero espera una conexión del pool de forma
síncrona en el bucle de eventos. Con el pool saturado, el servidor entero se congela 30 s y termina en `TimeoutError`.

La sonda, con uvicorn real y la configuración de producción, lo reproduce con el equipo en calma: un 500 a los 30,05 s, y
peticiones de 3 s que tardan 30,28 s. Los controles y el contrafactual, que descarga la llamada al threadpool, lo eliminan.
No hay fugas. Ni la memoria ni el tamaño del pool son la causa: la paginación y las cargas que retienen su conexión durante
clamscan solo hacen más probable la saturación.

| Puntero | Valor |
|---|---|
| `NEXT TECHNICAL CYCLE` | **OBS-09** si llega su evidencia; si no, **LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP** (corrección mínima de la Spec 001: `await run_in_threadpool(self._get_mode)`, con material gate sobre la semántica de licencia) |
| `NEXT MASTER SPEC` | **NOT YET PRIORITIZED** — sin cambio |

Líneas base: SQLite 1859/0/1046 · PostgreSQL 2879/0/26 · E2E 284/0/0 (`f93232b`) · OpenAPI 544/533/11.

