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
