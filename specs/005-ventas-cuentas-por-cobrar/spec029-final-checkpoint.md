# SPEC 029 — CHECKPOINT FINAL

## Veredicto

`SPEC 029 — COMPLETE / CONVERGED`

## La frase que ya no describe el sistema

> «`resolve_price` existe, devuelve el precio y la versión que lo produjo, está
> probada — y nadie la llama.»

Era el hallazgo con más consecuencias del checkpoint maestro de las 56 Specs, y
la razón por la que 029 se eligió sobre candidatas que desbloqueaban más.

Ahora la llama la línea de cotización, la línea de pedido directo, y la
conversión **no** la vuelve a llamar, que es igual de importante.

## Lo que se captura, y por qué importa

Nueve columnas de origen en cada línea comercial. La que decide es
`price_source_version_id`: no la lista, la **versión**. Una lista cambia; una
versión es lo que produjo ese precio, y la Spec 012 garantiza que no se edita ni
se borra.

Con eso, una cotización de marzo se reconstruye en diciembre sin consultar los
maestros de diciembre. Es la diferencia entre saber qué se ofreció y adivinar
qué se habría ofrecido hoy.

## Baseline

| | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 177 | 177 |
| Migraciones | 41 | **42** |
| Claves foráneas | 356 | **366** |
| Rutas · operaciones | 308 · 426 | **311 · 429** |
| Con contrato de empresa | 364 | **367** |

Ninguna tabla nueva. 029 completó lo que existía en vez de duplicarlo, que es lo
que corresponde a una Spec cuya deuda no era de ausencia sino de captura.

## Cuatro hallazgos propios

**El precio se truncaba al copiarse.** El maestro guarda cuatro decimales y la
línea guardaba dos: `125.4000` se convertía en `125.40`. El origen habría
apuntado a una versión cuyo precio no coincidía con el de la línea, y la
evidencia habría dejado de cuadrar consigo misma.

**La cotización nacía en un estado inexistente.** `ACTIVE` no aparecía en
ninguna transición, porque no había transiciones: el campo existía y nada lo
movía.

**El detalle del pedido guardaba el origen y no lo mostraba.** Tener la
evidencia y no poder enseñarla es casi no tenerla.

**La reserva ya estaba, y no es de esta Spec.** `_reserve_order` se dispara en
`APPROVED → RESERVED` desde la Spec 005. No se tocó: retirarla habría sido
decidir `D0-03` por eliminación, y `D0-03` sigue siendo una decisión de negocio.

## La frontera con la Spec 030, medida

No se declara: se mide. Dos pruebas cuentan el inventario reservado antes y
después de convertir, y cuentan listas de preparación y facturas.

Convertir crea un pedido en `DRAFT` y nada más.

## Regresión

Backend **0 fallos, 0 errores, 8 saltos** —todos S3, P1 externa— sobre
PostgreSQL 18.6 con ClamAV real. Frontend **283/283**, `tsc`, ESLint y build
limpios.

Un fallo apareció a mitad de camino y no era de las pruebas: exigir motivo a
todo precio tecleado rompía las suites de dominio porque los catálogos
comerciales nacen vacíos. Sin lista no hay de qué desviarse. Corregido y
reejecutado.

## Deuda propia

**Ninguna.** No queda origen sin persistir, ni evidencia que se pierda al
convertir, ni conversión sin proteger, ni ruta hija sin validar, ni pantalla sin
aislamiento de empresa.

## Anotado para otra Spec

`sales_invoice_lines.unit_price` sigue en `Numeric(18,2)`. Cuando la Spec 034
consuma esta evidencia tendrá el mismo truncamiento que 029 acaba de cerrar. Se
deja escrito y no se absorbe.

## Lo que sigue

029 habilita a 030, que espera una decisión —`D0-03`, cuándo se reserva— y no
código. El pedido ya llega con su evidencia comercial intacta.
