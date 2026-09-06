# SPEC 033 · CONVERGENCIA

`SPEC 033 — COMPLETE / CONVERGED`

> 2026-09-06, sobre `4b29eaf`. Ciclo completo desde `/speckit.specify`.

## Puerta

| Criterio | Resultado |
|---|---|
| Solo un pedido `PREPARED` con preparación consolidada entra al control | sí |
| **Se compara contra el pedido, no contra la preparación** | sí (`R-D0-12-2`) |
| Las tres cifras —requerida, preparada, verificada— se conservan | sí |
| Dimensiones verificadas | producto/SKU, cantidad, presentación y condición (¶65-69) |
| El veredicto lo calcula el backend | sí; el cliente no puede enviarlo |
| Quien preparó puede confirmar | **no**, salvo que la empresa lo permita a conciencia |
| Defecto de la política de segregación | **exigirla** (`R-D0-12-5`) |
| Control parcial | **imposible** |
| Rechazo | incidencia registrada y el pedido regresa a preparación (¶77) |
| Intentos anteriores conservados | sí |
| Un pedido se confirma dos veces | **no**, ni en la base |
| Dos verificadores dejan dos veredictos | **no** |
| Delta de inventario | **0** en saldos, movimientos y reserva |
| La 033 ejecuta o replanifica picking | **no** |
| La 033 factura o despacha | **no** |
| La 033 renegocia la venta | **no** |
| `READY_FOR_BILLING` añadido | **no** — es de la 034 |
| Confirmación como booleano | **no** — entidad con actor, momento, resultado y evidencia |
| Backend | 1144 pruebas · **1136 pasan · 8 saltos · 0 fallos** |
| Saltos esperados / reales | **8 / 8** |
| Frontend | **293/293** · `tsc`, `eslint`, `ruff` limpios |
| E2E de la Spec 033 | **21/21** (7 casos × Chromium, Firefox, WebKit) |
| E2E de la cadena operativa | **129/129** (019→033 y recorrido del menú × 3) |
| Migración `0051` | ida y vuelta sobre base limpia |
| Trazabilidad | **100 %**, 40 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## El ciclo en que la autoridad ya estaba escrita

Los tres ciclos anteriores se pasaron la mitad del tiempo buscando quién había
decidido qué, y en dos de ellos la respuesta estaba repartida entre cinco
documentos. Aquí no: `ADR-D0-012` decide las seis preguntas que el ciclo
señalaba como materiales, y el proceso fuente enumera literalmente las cinco
dimensiones que el control verifica.

Lo único que hubo que hacer fue leerlo antes de escribir.

La frase que gobierna todo el diseño es de `R-D0-12-2`: «la comparación es contra
el pedido, **no contra la lista de picking**: comparar la preparación consigo
misma no es un control». De ahí sale que lo requerido se lea de la línea del
pedido y no de la reserva —que un picking corto ya encogió— y que un pedido
incompleto no pueda pasar el control aunque el verificador cuente exactamente lo
que hay preparado. Está probado con ese caso.

## Deltas dirigidos

| Delta | Dueño | Qué | Guardia |
|---|---|---|---|
| **A** | Spec 030 (`sales`) | `PREPARED → CONFIRMED` y `PREPARED → PREPARING` | `test_la_maquina_de_estados_es_la_de_d0_03` |
| **B** | Spec 001 (`organization`) | `Company.confirmation_same_user_allowed`, defecto `false` | `test_el_defecto_de_la_politica_es_exigir_separacion` |

Tres guardias se actualizaron con su razón escrita. Dos de ellas —las de la 032—
marcaban «la 033 no está construida»; la tercera fue el corte de bloque de la
guardia de la 032, que sin ajustarlo se habría comido el bloque de la 033 y
habría afirmado lo contrario de lo que quiere decir. Es el mismo cuidado que
necesitó la 031 un ciclo antes.

## Lo que se midió en la pila real

La e2e descubrió algo que ninguna prueba unitaria podía: el `admin` que monta el
escenario **es** quien recoge y consolida, así que el backend le negó la
confirmación. Hubo que crear un segundo usuario para poder probar el camino
conforme. Que la primera versión de la e2e no funcionara **es la evidencia de
que el control funciona**.

## Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| Un pedido rechazado queda en `PREPARING` y la 032 no tiene camino de reapertura ni arista `PICKING → DISPONIBLE` | Spec 032 |
| `uom.py` declara para `sales_orders` estados que no existen | Spec 011 |
| PostgreSQL ejecutable 16.2 frente al 18.6 documentado | QA · `ENVIRONMENT_BASELINE_DEVIATION`; la Spec 033 no usa nada de 18.x |

## Estado resultante

| | |
|---|---|
| Spec 033 | **COMPLETE / CONVERGED** |
| Specs 001, 030 | `COMPLETE / CONVERGED` con sus deltas dirigidos convergidos |
| Spec 034 | **desbloqueada por dependencia**; compuerta en `spec033-spec034-handoff-contract.md`. **No implementada.** |
