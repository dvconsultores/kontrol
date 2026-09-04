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
