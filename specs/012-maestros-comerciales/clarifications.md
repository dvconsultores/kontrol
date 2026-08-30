# ACLARACIONES — SPEC 012

Cada punto se resolvió leyendo `ADR-D0-005`, la Constitución o el código. Solo
lo que ninguno de los tres decidía se eleva.

## CL-012-01 · ¿012 implementa el motor de precios o solo el maestro?

**Implementa la resolución, no el proceso.** `resolve_price(...)` es la
autoridad única (`FR-012-014`), porque si cada Spec resolviera su precio habría
cinco precios distintos para la misma línea y `P22` quedaría roto.

Lo que **no** implementa: cotizar, pedir, facturar. 012 responde «cuánto vale»;
029 decide qué hacer con la respuesta.

## CL-012-02 · ¿Precedencia configurable o fija?

**Configurable.** `R-D0-05-1` es explícito y `P8` lo exige. KONTROL entrega el
orden por defecto documentado; cada empresa lo reordena.

Un orden codificado sería más simple de implementar y estaría mal: el orden de
precedencia comercial es una decisión de negocio de cada empresa, no una
propiedad del software.

## CL-012-03 · ¿Qué pasa si dos reglas empatan?

`R-D0-05-2`: vigencia más reciente; a igualdad, menor precio. Si sigue
habiendo empate, **es un error de configuración y se reporta como tal**
(`FR-012-013`).

Resolverlo al azar sería peor que fallar: produciría precios irreproducibles.

## CL-012-04 · ¿Zona comercial y zona de almacén son lo mismo?

**No, y no comparten tabla** (`FR-012-040`, `FR-012-041`).

`WarehouseZone` (Spec 008) es una división **física** del almacén, con pasillo,
rack, nivel y ubicación. `CommercialZone` es un **territorio de ventas** con
vendedor y ruta. Comparten la palabra «zona» y nada más. Reutilizar la tabla por
el nombre sería el mismo error que confundir presentación de compra con
presentación de venta.

## CL-012-05 · ¿Se duplica `Customer`?

**No** (`FR-012-051`). `Customer` ya existe con sus cuatro campos de texto. 012
añade FK y **conserva** la cadena original en `legacy_value`. No nace una
entidad paralela de cliente comercial.

## CL-012-06 · ¿Qué se congela exactamente al aprobar?

`R-D0-05-5`: precio unitario, descuento aplicado, política de descuento y su
versión, condición de pago, moneda, tasa de cambio **y el identificador de la
versión de lista o regla** que produjo el precio.

Sin el último, el snapshot serviría para reimprimir pero no para **explicar** de
dónde salió el número. Es la diferencia entre guardar el resultado y guardar la
evidencia.

## CL-012-07 · ¿Y los documentos históricos sin snapshot?

**No se inventa nada** (`FR-012-082`). Se marcan `pricing_source = LEGACY_FREETEXT`.

Es la misma decisión que 046 tomó con el legado documental: no se puede
reconstruir lo que nunca se registró, y fingir lo contrario es peor que
admitirlo.

## CL-012-08 · ¿Comisiones dentro o fuera?

**Reservado, no implementado** (`FR-012-090`). `ADR-D0-005` lo declara
`FUTURE CAPABILITY`. El modelo deja el hueco para que incorporarlas no exija
rediseño; la Spec no está obligada a construirlas y **no inventa ninguna regla**.

## CL-012-09 · ¿El descuento excesivo bloquea o se aprueba?

**Se aprueba** (`FR-012-023`). Genera `ApprovalRequest` por el motor de la Spec
045, que ya está `COMPLETE_100`. No se construye una segunda vía de
autorización: sería violar `P22` igual que lo habrían violado unos adjuntos
propios en 046.

## CL-012-10 · ¿Qué valores trae KONTROL de fábrica?

**Ninguno.** Ni un plazo, ni un porcentaje, ni una zona, ni un canal
(`FR-012-022`, `FR-012-032`, `NFR-012-05`). Los catálogos nacen vacíos, como en
046.

«Contado» y «30 días» parecen universales y no lo son: su significado contable y
su cálculo de vencimiento son decisiones de cada empresa.

## CL-012-11 · ¿Moneda propia o la existente?

La existente. `treasury.currencies` y `exchange_rates` ya son maestros. 012 los
**referencia**; no crea un catálogo monetario paralelo.

Y no se confunde **moneda** con **método de pago**: son cosas distintas y ya
viven en tablas distintas (`currencies` vs `payment_methods`).

## CL-012-12 · ¿Precio por unidad o por presentación?

Por presentación, con la semántica de la Spec 011 (`FR-012-004`): el precio se
declara sobre una presentación concreta y el factor se congela igual que en las
líneas transaccionales. Un precio «por caja» sin saber cuántas unidades tiene la
caja no es un precio.

---

## Elevado a negocio

| Id | Qué falta | Bloquea |
|---|---|---|
| **OQ-06** | Orden de precedencia definitivo, límites de descuento por rol, alcance de comisiones, política de crédito | **No** — son datos que el cliente carga; la capacidad se especifica igual |

`OQ-06` es `BUSINESS_VALIDATION_REQUIRED` en `ADR-D0-005` y sigue abierta. No
impide especificar ni implementar, **precisamente porque `P8` obliga a que sean
configurables**. Si la respuesta fuera «que vengan fijos en el código», habría
que reabrir el ADR, no la Spec.
