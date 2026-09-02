# SPEC 029 — EVIDENCIA DEL ORIGEN COMERCIAL

## La deuda que cierra

Antes de este ciclo, `resolve_price` existía, devolvía el precio **y la versión
que lo produjo**, estaba probada — y ninguna línea de venta la llamaba.

```
sales_quote_lines   → unit_price, discount   · 0 columnas de origen
sales_order_lines   → unit_price, discount   · 0 columnas de origen
```

`P23` dice por qué eso importa y no es una metáfora: **el dato no se pierde, es
que nunca se captura**. Ninguna migración posterior puede repararlo, porque no
hay nada que reparar — nunca hubo un origen que recuperar.

## Lo que ahora se captura

Nueve columnas en cada línea comercial. Las siete primeras son el contrato §11
de la Spec 012; las dos últimas las añadió 029 para poder distinguir después un
precio escrito de uno resuelto.

| Columna | Qué guarda |
|---|---|
| `price_source_version_id` | La **versión** que produjo el precio. No la lista |
| `price_source_item_id` | El ítem concreto de esa versión |
| `pricing_source` | `RESOLVED` · `MANUAL_JUSTIFIED` · `LEGACY_FREETEXT` |
| `discount_policy_id` + `discount_policy_version` | Qué política autorizó el descuento |
| `discount_approval_request_id` | La solicitud de la Spec 045, si hizo falta |
| `payment_term_snapshot` | La condición de pago **entera**, congelada |
| `resolved_unit_price` | Lo que dijo el resolutor antes del cambio manual |
| `manual_reason` | Por qué se cambió |

## Por qué la versión y no la lista

Una lista cambia. Una versión es lo que produjo **ese** precio, y la Spec 012
garantiza que una versión publicada no se edita y que no se borra: solo se
archiva.

Guardar la lista habría sido guardar el nombre del sitio donde estaba el precio,
no el precio.

## Por qué también un snapshot, y no solo claves foráneas

La condición de pago se congela **entera** —código, nombre, tipo, días,
desplazamiento— y no como identificador.

Una clave foránea apunta al maestro de hoy. Si mañana alguien corrige «30 días»
a «45 días» sobre la misma fila, todos los documentos que la referencian
empezarían a decir 45. El snapshot dice lo que dijo entonces.

Para el precio ocurre lo contrario y por eso ahí basta la referencia: el valor
ya vive en la línea (`unit_price`), y la versión no muta.

## El precio manual

Escribir un precio es legítimo y frecuente: un acuerdo puntual, un cliente
antiguo. Lo que no es legítimo es que después nadie pueda distinguirlo de un
precio de lista.

Un precio distinto del resuelto exige motivo (`422 MANUAL_PRICE_REASON_REQUIRED`)
y **conserva al lado lo que decía la lista**. Sin ese `resolved_unit_price`, la
línea diría 80 y nadie sabría que la lista decía 100.

## Ausencia no es cero

Sin lista aplicable, la línea **no se crea**: `422 PRICE_NOT_RESOLVED`, con el
motivo que devolvió el resolutor.

La alternativa —crear la línea con precio cero— habría sido inventar un dato.
Un cero es un precio; la ausencia de precio no lo es.

## Un truncamiento que solo apareció al conectarlo

`price_list_items.unit_price` es `Numeric(18,4)` y la línea de venta era
`Numeric(18,2)`. Copiar `125.4000` de la lista guardaba `125.40`.

No es cosmético: el origen habría apuntado a una versión cuyo precio **no
coincide** con el de la línea, y la evidencia habría dejado de cuadrar consigo
misma. La migración `0042` iguala la escala.

`sales_invoice_lines` sigue en `Numeric(18,2)` **a propósito**: es de la
Spec 034 y queda anotado para ella, no absorbido aquí.

## El tercer valor del enum, que casi no se escribe

`pricing_source` tiene tres valores y el tercero —`LEGACY_FREETEXT`— parecía
reservado para las líneas anteriores a esta Spec. La regresión demostró que no.

Al conectar el resolutor, toda línea con precio tecleado empezó a exigir un
motivo, y eso rompió las suites de dominio. El fallo no era de las pruebas: era
de mi diseño.

Escribir un precio cuando **no hay lista aplicable** no es una desviación,
porque no hay de qué desviarse. Exigir una justificación ahí sería pedir que se
explique una diferencia contra un precio que no existe. Y dejaría el sistema
inservible el primer día: los catálogos comerciales **nacen vacíos** por `P8`,
así que una empresa recién instalada no podría cotizar hasta cargar listas.

Los tres casos, separados:

| Situación | `pricing_source` | ¿Motivo? |
|---|---|---|
| Sin precio indicado, con lista | `RESOLVED` | no |
| Sin precio indicado, sin lista | *no se crea la línea* — `422` | — |
| Precio indicado, sin lista | `LEGACY_FREETEXT` | no: no hay referencia |
| Precio indicado, igual al de lista | `RESOLVED` | no |
| Precio indicado, distinto | `MANUAL_JUSTIFIED` | **sí** |

La cuarta fila importa: teclear el mismo precio que la lista no convierte la
línea en manual. Lo que decide no es quién escribió el número, sino si coincide
con el que la autoridad comercial produce.

## Lo que no se falsificó

Las nueve columnas nacen anulables. Las líneas que ya existían no reciben un
origen inventado: se quedan sin él.

Asociarles la versión activa de hoy solo para que la clave foránea no quedara
nula habría sido falsificar evidencia histórica — peor que no tenerla, porque
después nadie distinguiría lo capturado de lo supuesto.
