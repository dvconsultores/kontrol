# RANKING DE DISPONIBILIDAD

Ocho ejes, 0–5 cada uno, sobre 40. El número **no decide**: acompaña al
razonamiento de dependencias, que es lo que decide.

| # | Spec | Dep. | Arq. | Modelo | Contrato | Existente | Criticidad | Desbloqueo | Riesgo | Total |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **029 Cotización y pedido** | **5** | 5 | 4 | **5** | 3 | 5 | 3 | **5** | **35** |
| 2 | 020 Incidencias de recepción | 5 | 5 | 2 | 3 | 1 | 4 | 3 | 3 | 26 |
| 3 | 018 Importaciones | 5 | 5 | 1 | 2 | 0 | 4 | 2 | 4 | 23 |
| 4 | 013 Maestros financieros | 4 | 5 | 4 | 3 | 4 | 3 | 2 | 2 | 27 |
| 5 | 014 Maestros fiscales | 4 | 5 | 4 | 3 | 4 | 4 | 4 | 2 | 30 |
| 6 | 036 Devoluciones / NC / ND | 5 | 5 | 3 | 3 | 3 | 3 | 1 | 2 | 25 |
| 7 | 048 Integraciones | 4 | 4 | 2 | 2 | 2 | 3 | 3 | 2 | 22 |
| 8 | 022 Put-away | **1** | 5 | 3 | 3 | 1 | 5 | 4 | 4 | 26 |
| 9 | 021 Confirmación de inventario | **2** | 5 | 3 | 3 | 2 | 4 | 3 | 3 | 25 |
| 10 | 033 Confirmación de pedido | **0** | 5 | 1 | 3 | 0 | 4 | 3 | 3 | 19 |

## Por qué 029 gana sin forzar ningún número

Su eje de dependencias es **5** y es el único: todas las suyas —tercero,
artículo, unidad, presentación, maestros comerciales, disponibilidad— están
satisfechas, y la última se cerró en el ciclo inmediatamente anterior.

Su eje de contrato es **5** porque `resolve_price` ya existe, devuelve la
versión que produjo el precio y está probada. No hay que diseñar el contrato:
hay que consumirlo.

Su eje de riesgo es **5**, y es el que más pesa. `sales_quote_lines.unit_price`
y `sales_order_lines.unit_price` siguen siendo números tecleados sin origen.
Cada documento que se emite así es un documento que **nunca podrá
reconstruirse**: no es que el dato se pierda, es que no se captura (`P23`).
Ninguna migración posterior lo repara.

## Por qué 022 no gana pese a desbloquear más

Su eje de dependencias es **1**. Su prerequisito declarado es 021, cuyo
prerequisito es 020, que no existe. Seleccionarla sería declarar `READY` con un
bloqueo activo, que es exactamente lo que este checkpoint prohíbe.

Su criticidad operativa es la más alta de la tabla —**5**— y por eso encabeza la
recomendación de la ola siguiente, no de esta.

## Por qué 014 no gana pese a puntuar 30

Desbloquea seis Specs, pero las seis están detenidas por `D0-07`, que no es
técnico. Construir 014 ahora adelanta trabajo cuyo cuello de botella seguirá
cerrado, y no reduce ningún riesgo que se esté acumulando.
