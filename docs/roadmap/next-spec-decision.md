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
