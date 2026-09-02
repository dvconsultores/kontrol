# SPEC 012 — CHECKPOINT FINAL

## Veredicto

`SPEC 012 — COMPLETE / CONVERGED`

## La deuda que cerró

Antes de este ciclo, cada cotización emitida llevaba un precio cuyo origen **no
podía reconstruirse**: no se sabía de qué lista salió, con qué vigencia, ni
quién autorizó el descuento. Un descuento del 40 % y uno del 4 % eran
indistinguibles para el sistema: los dos, un número que alguien escribió.

Ahora `resolve_price` devuelve el precio **y la versión que lo produjo**, y esa
versión, una vez publicada, no cambia.

## Baseline

| | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 166 | **177** |
| Migraciones | 39 | **41** |
| Claves foráneas | 331 | **356** |
| Rutas | 294 | **308** |
| Operaciones | 404 | **426** |
| Operaciones con contrato de empresa | 342 | **364** |

Las 22 operaciones nuevas son las 22 del módulo comercial, y **las 22 declaran
la empresa**. Ninguna ruta anterior se perdió.

## Las once

| Entidad | Alcance | Autoridad | Probada |
|---|---|---|---|
| `payment_terms` | COMPANY | `company_id` | sí |
| `commercial_zones` | COMPANY | `company_id` | sí |
| `sales_channels` | COMPANY | `company_id` | sí |
| `price_lists` | COMPANY | `company_id` | sí |
| `price_list_versions` | COMPANY | `price_list_id → price_lists` | sí |
| `price_list_items` | COMPANY | `version_id → price_list_versions` | sí |
| `price_precedence` | COMPANY | `company_id` | sí |
| `discount_policies` | COMPANY | `company_id` | sí |
| `credit_policies` | COMPANY | `company_id` | sí |
| `customer_commercial_terms` | COMPANY | `customer_id → customers` | sí |
| `sales_commission_policies` | COMPANY | `company_id` | reservada |

Indeterminadas: **0**.

## Lo que este ciclo encontró

Cuatro fallos propios, corregidos con prueba antes y después. Y uno ajeno.

**La restricción que protegía y no lo contaba.** Un código duplicado y un solape
de vigencias terminaban en `500`: la base hacía su trabajo y la respuesta no lo
decía. Es la misma forma que N10 encontró en el desbordamiento de `entity_id`, y
aparece siempre por el mismo motivo — la restricción se prueba desde la base y
no desde la respuesta.

**La prueba en verde que no probaba nada.** La exclusión de solape vivía solo en
la migración, y las suites levantan el esquema desde el ORM. Interrogaban un
esquema más débil que el de producción. Es literalmente la lección de N7, y me
la encontré de frente al escribir la prueba que la verificaba.

**El clasificador de N4, que llevaba desde N4 con un hueco.** Preguntaba al
catálogo del destino por sus restricciones, pero no por la existencia de la
tabla. Planificaba revisar tablas que una instalación heredada no tiene. Nadie
lo había visto porque nadie había añadido una tabla de empresa nueva desde que
existe el clasificador; la Spec 012 añadió once.

No es una regresión: nada que funcionara dejó de funcionar. Es un límite que
nadie había alcanzado. Se corrigió completando lo que `planes()` ya prometía en
su propio docstring, y está escrito, no aplicado en silencio.

## `OQ-06`

`CONFIGURABLE_AT_RUNTIME`, y demostrado: `test_la_precedencia_es_dato_y_cada_empresa_tiene_la_suya`
hace que A configure su orden y B no, y comprueba que difieren. Si estuviera
codificada, no podrían.

## Regresión

Backend **0 fallos, 0 errores, 8 saltos** —todos S3, P1 externa— sobre
PostgreSQL 18.6 con ClamAV real. Frontend **282/282**, `tsc`, ESLint y build
limpios.

Los quince errores que apareció una pasada intermedia eran el hueco del
clasificador de N4, no un fallo de esta Spec. Corregido y reejecutado: el
clasificador sigue produciendo las ocho clases y las cuatro estrategias sobre el
fixture hostil.

## Deuda propia de la Spec 012

**Ninguna.** No queda ningún endpoint hijo sin validar, ninguna prueba
pendiente, ningún resolutor tomando la empresa del cuerpo, ningún versionado
para después.

## Lo que no se hizo, por contrato

Comisiones —reservadas por `FR-012-090`—, motor de aprobación propio, motor de
unidades propio, maestro de monedas propio, emisión de eventos y cualquier valor
comercial por defecto.

## Lo que sigue

La Spec 012 habilita a 029, 030, 034, 036 y 037. Ninguna se implementa aquí:
esta Spec **prepara sus contratos**, no ejecuta sus procesos.
