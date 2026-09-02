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

---

# ACLARACIONES POSTERIORES A ARCH-MC-001

Cincuenta preguntas del ciclo de actualización, resueltas midiendo el código
vigente en `f24b4c0`. Las que cambiaron algo:

**¿Cuál es el alcance final de Tercero?** **Empresa**, con `company_id`
obligatoria y clave foránea a `companies`. Era la premisa del bloqueo de esta
Spec y ya no se sostiene: `CustomerCommercialTerms` sí puede distinguir la
relación de A de la de B.

**¿Y el de Producto?** Empresa, obligatoria. No se asume por costumbre: se midió.

**¿Y el de Moneda y Tasa de cambio?** Empresa, las dos. La clasificación de
tenant que arrastraba la migración `0032` la corrigió N7 y la retiró del esquema
la `0039`. Una lista de precios de A solo referencia una moneda de A.

**¿Cuántas entidades tiene realmente la Spec 012?** **Once.** `spec.md` decía
nueve e incluía una `PriceRule` inexistente; `data-model.md` describía once.
Reconciliado.

**¿Cuáles llevan `company_id` y cuáles la derivan?** Ocho directas, tres
derivadas. Las derivadas **no** la llevan: una segunda respuesta a una pregunta
que ya tiene una puede discrepar de la primera.

**¿Dónde sería `company_id` redundante?** En `price_list_versions`,
`price_list_items` y `customer_commercial_terms`. Su padre ya la determina y la
cadena entera es obligatoria en cada eslabón.

**¿Cuál es la unicidad de cada maestro?** Por empresa, `(company_id, code)`, en
los ocho directos. Y no por mecánica: dos empresas del mismo grupo pueden y
deben usar el mismo código de lista de precios sin colisionar.

**¿Y la de `price_list_items`?** `(version_id, item_id, category_id,
presentation_id, min_quantity)`, con `item_id` y `category_id` excluyentes. Con
columnas anulables dentro de la clave hace falta índice único **parcial**: en
SQL `NULL` no es igual a `NULL`, y una restricción ingenua permitiría duplicados
exactos.

**¿Qué tabla es la «categoría»?** `taxonomy_nodes`, de empresa. No existe
ninguna `item_categories`; el modelo decía «o categoría» sin nombrarla.

**¿Qué comprobación exige la unidad de medida?** «Propia **o** de plataforma».
`units_of_measure.company_id` es **anulable** y el nulo significa unidad de la
plataforma, visible para todas y de solo lectura. Comprobar igualdad estricta
rechazaría una unidad legítima.

**¿A quién pertenece `PaymentTerm`?** A la 012. Ninguna otra Spec lo declara;
`013` es un análisis de brechas, no un maestro financiero.

**¿Y las comisiones?** A la 012, **reservadas** y sin implementar. La 012 no
calcula comisión ni toca nómina.

**¿Qué endpoints anidados existirán y cómo validan al padre?** Cinco, todas bajo
`/listas-precio/{id}/...`. Resuelven el padre acotado por `CompanyContext` y, con
tres niveles, comprueban los tres eslabones. El contrato está en
`nested-resource-security-contract.md`.

**¿Qué error se usa para el cruce entre empresas?** `404`, indistinguible de
inexistente. Un `403` confirma que el recurso existe.

**¿Necesita la 012 la Spec 046?** **No.** Se dice porque la costumbre es
añadirla. Tampoco la 047: `FR-012-073` es explícito en que la 012 no emite
eventos.

## `OQ-06`, revalidada

Sigue abierta como `BUSINESS_VALIDATION_REQUIRED` en `ADR-D0-005`, y **no es una
pregunta abierta material**. Se reclasifica con la terminología vigente:

`OQ-06 — CONFIGURABLE_AT_RUNTIME`

El orden de precedencia, los límites de descuento por rol, el alcance de las
comisiones y la política de crédito son **datos que carga el cliente**. `P8`
obliga a que lo sean, la Spec especifica la capacidad de configurarlos y los
catálogos nacen vacíos.

La política por defecto es: precedencia sembrada como dato reordenable —el orden
de `ADR-D0-005`—, límites sin valor por defecto, y comisiones fuera de alcance.

Con una excepción que conviene repetir en voz alta: si la respuesta de negocio
fuera «la precedencia debe venir fija en el software», eso sería una violación de
`P8` y obligaría a reabrir `ADR-D0-005`. Esta Spec no la aceptaría en silencio.
