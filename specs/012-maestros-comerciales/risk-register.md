# REGISTRO DE RIESGOS — SPEC 012

## 1. Riesgos de producto

| Id | Riesgo | Por qué es real | Mitigación |
|---|---|---|---|
| **R-012-1** | **012 acaba siendo un CRUD** y el precio se sigue tecleando | Es lo más fácil de construir y lo que no resuelve nada | `FR-012-014` autoridad única + `AC-012-11..17`; el criterio de éxito no es que existan tablas |
| **R-012-2** | Precedencia codificada «provisionalmente» | Es más rápido y luego nadie lo saca | `AC-012-03` y `AC-012-12`: reordenar la precedencia debe cambiar el resultado |
| **R-012-3** | Se inventan plazos «obvios» de fábrica | «Contado» y «30 días» parecen universales | `AC-012-01`: los catálogos nacen vacíos, como en 046 |
| **R-012-4** | Confundir `CommercialZone` con `WarehouseZone` | Comparten la palabra y la Spec 008 ya tiene tabla | `FR-012-041`, `AC-012-31`: sin FK entre ambas |
| **R-012-5** | Aparece `price_1..price_5` por presión de plazo | Es el atatajo clásico de los ERP | Prohibido explícitamente; hoy **no existe** en el código y debe seguir así |
| **R-012-6** | Motor de promociones por la puerta de atrás | El descuento invita a crecer | Fuera de alcance declarado; `ADR-D0-005` descartó el motor de expresiones |

## 2. Riesgos de datos e histórico

| Id | Riesgo | Mitigación |
|---|---|---|
| **R-012-7** | Convertir «30 días» automáticamente cuando puede significar cosas distintas | `AC-012-37`: ambiguo → revisión manual, nunca conversión |
| **R-012-8** | Inventar snapshot para documentos históricos | `AC-012-39`: `LEGACY_FREETEXT`. Es la lección de 046 |
| **R-012-9** | Borrar el texto original tras migrar | `AC-012-38`: `legacy_value` se conserva |
| **R-012-10** | Editar una lista y alterar facturas emitidas | `AC-012-26/27`: violación de `P5` |
| **R-012-11** | `float` en precios | `AC-012-42`. La Spec 011 ya pagó ese error una vez |

## 3. Riesgos técnicos

| Id | Riesgo | Mitigación |
|---|---|---|
| **R-012-12** | Solapamiento de vigencias por concurrencia | Restricción en base, no solo validación en servicio — como los índices únicos parciales de 008/011/046 |
| **R-012-13** | Resolver un precio recorriendo todas las versiones | `NFR-012-01`: índice por lista, vigencia y producto |
| **R-012-14** | Fuga entre empresas en la resolución | `AC-012-20` |
| **R-012-15** | Doble autoridad si `sales` calcula su propio precio | `P22`; la revisión de convergencia debe dar 0 cálculos fuera de `pricing.py` |

## 4. Riesgo de gobierno

| Id | Riesgo | Estado |
|---|---|---|
| **R-012-16** | `OQ-06` sin responder y se paraliza la Spec | **Controlado**: `P8` obliga a que esos valores sean dato. La capacidad se especifica igual; lo que falta son los valores que cargará el cliente |
| **R-012-17** | Que negocio pida precedencia fija | Sería violación de `P8`: obligaría a reabrir `ADR-D0-005`, no a torcer la Spec |

## 5. Lo que no es riesgo de esta Spec

- El cálculo de comisiones — `FUTURE CAPABILITY`.
- La exposición crediticia en tiempo real — Spec 030.
- El precio de compra negociado — Spec 016.
