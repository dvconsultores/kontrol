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

---

## Ranking de la cadena operativa — 2026-09-03

Criterios de 0 a 5. El número ordena; no decide.

| Rank | Spec | Dependencia | Arquitectura | Modelo | Contrato | Existente | Criticidad | Desbloqueo | Riesgo | Total |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **019 Recepción física** | 5 | 5 | 4 | 4 | 3 | 5 | 5 | **5** | **36/40** |
| 2 | 020 Incidencias de recepción | 5 | 5 | 3 | 4 | 0 | 4 | 4 | 4 | 29/40 |
| 3 | 021 Confirmación de inventario | 2 | 4 | 3 | 3 | 1 | 5 | 5 | 4 | 27/40 |
| 4 | 022 Put-away | 1 | 5 | 4 | 3 | 0 | 5 | 5 | 3 | 26/40 |
| 5 | 031 Cola y ruta de picking | 1 | 4 | 2 | 3 | 1 | 4 | 3 | 2 | 20/40 |
| 6 | 032 Picking y consolidación | 0 | 4 | 2 | 2 | 1 | 4 | 2 | 2 | 17/40 |

### Por qué 019 gana sin forzar ningún número

Empata con 020 en dependencias (ambas con cero bloqueos) y pierde en «hueco existente» —020 no
existe en absoluto—. Gana donde el proyecto ya aprendió que se pierde el producto: **riesgo de dato
irreversible**. Lo que la recepción no capture mientras el camión está en el muelle no se reconstruye
después, y hoy no captura ni la presentación ni el detalle del daño.

### Por qué 021 no gana pese a su criticidad

Es la que más desbloquea de las cuatro de entrada, pero arrastra dos bloqueos reales: la capacidad de
excepción que debe 020 y la imposibilidad de escribir saldo en un estado no vendible, que debe 023.
Una Spec con alto valor de desbloqueo y dependencias insatisfechas no puede seleccionarse.

### Por qué 022 no gana pese a desbloquear la salida entera

Su bloqueo dejó de ser «no hay ubicaciones» —la Spec 008 las entrega— y pasó a ser el estado de
origen de la mercancía, que debe la 021. Sigue bloqueada, con mejor nombre.

---

## Actualización tras las Specs 019 y 020 — 2026-09-03

Tres filas de la tabla ya no compiten: **029**, **019** y **020** están implementadas y convergidas.
De las que quedan, la que se movió es la 021.

| Spec | Eje que cambia | Antes | Ahora | Por qué |
|---|---|---:|---:|---|
| 021 Confirmación de inventario | Dependencias | 2 | **4** | Tenía dos bloqueos y le queda uno: la capacidad de excepción existe desde la 020; falta que el saldo admita estados no vendibles (023) |
| 022 Put-away | Dependencias | 1 | **2** | Su cadena se acortó de tres eslabones a dos: ahora solo espera a la 021 |

Ninguna llega a 5 en el eje de dependencias, y por eso este checkpoint **no proclama una ganadora**.
El número acompaña al razonamiento; el razonamiento dice que antes de abrir la 021 hay que decidir
dónde se abre la capacidad de estados de mercancía. Esa decisión no es un ranking.
