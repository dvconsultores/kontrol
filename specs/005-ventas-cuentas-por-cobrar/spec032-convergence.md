# SPEC 032 · CONVERGENCIA

`SPEC 032 — COMPLETE / CONVERGED`

> 2026-09-05, sobre `307f303`. Ciclo completo desde `/speckit.specify`.

## Puerta

| Criterio | Resultado |
|---|---|
| Solo un plan `CONFIRMED` es ejecutable | sí |
| Lo recogido se guarda aparte de lo planificado | sí |
| Recoger de más | **bloqueado** |
| Recoger de menos sin motivo | **bloqueado**, en servicio y en `CHECK` |
| Motivos de diferencia | **los cinco del proceso**, ni uno más |
| **El compromiso se resta dos veces** | **no** — caso canónico probado |
| El despacho vuelve a restar lo ya extraído | **no** — probado con dos pedidos |
| Mercancía que sale del almacén al preparar | **0** |
| `InventoryBalance` escrito fuera del motor de la 023 | **0** |
| Estados de mercancía nuevos | **0** — se activan dos aristas ya declaradas |
| FIFO/FEFO/sustitución inventados | **0** |
| Replanificación al encontrar diferencia | **no** |
| Lote y serial preservados | sí |
| Consolidación desde lo recogido, no lo planificado | sí |
| El plan se cierra al consolidar, no antes | sí |
| El pedido llega a `PREPARED` y no más allá | sí; `CONFIRMED` sigue sin existir |
| La 032 confirma, factura o despacha | **no** |
| Backend | 1106 pruebas · **1098 pasan · 8 saltos · 0 fallos** |
| Saltos esperados / reales | **8 / 8** |
| Frontend | **291/291** · `tsc`, `eslint`, `ruff` limpios |
| E2E de la Spec 032 | **21/21** (7 casos × Chromium, Firefox, WebKit) |
| E2E de la cadena operativa | **105/105** (019, 020, 021, 022, 030, 031, 032 × 3) |
| Migración `0050` | ida y vuelta sobre base limpia |
| Trazabilidad | **100 %**, 37 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## La pregunta que parecía material

`§88` del ciclo pedía responder, con autoridad, qué queda tras recoger 30 de una
existencia de 100 con 30 reservadas. La respuesta estaba en el vocabulario que
`D0-03` §0 fijó y que ningún ciclo había leído como aritmética: **reservado son
las unidades «comprometidas y aún no extraídas»**. Extraer es dejar de estarlo.

| | `on_hand` `DISPONIBLE` | `qty_reserved` | disponible | `PICKING` | físico |
|---|---:|---:|---:|---:|---:|
| Antes | 100 | 30 | 70 | 0 | 100 |
| Después | 70 | 0 | **70** | 30 | **100** |

Sin esto el disponible habría caído a 40 y ventas habría dejado de poder vender
30 unidades que sí tiene. Con dos pedidos, además, despachar el primero habría
borrado del contador el compromiso del segundo. Las dos cosas están probadas, y
las dos pruebas fallan si se revierte el código que las sostiene.

## Deltas dirigidos

| Delta | Dueño | Qué | Guardia actualizada |
|---|---|---|---|
| **A** | Spec 023 / `D0-10` | Activadas `DISPONIBLE → PICKING` y `PICKING → PREPARADO` | `test_la_unica_salida_de_disponible_es_la_del_picking`, `test_la_salida_de_disponible_es_solo_la_que_la_032_activo`, `test_la_confirmacion_no_puede_pedir_una_arista_desde_disponible` |
| **B** | Spec 030 | El contador baja al extraer; el despacho solo resta lo aún no extraído | `test_el_contador_solo_resta_lo_aun_no_extraido` |
| **C** | Spec 023 | `reclassify` respeta ubicación, lote y serial en vez de la fila ancla | cubierto por las pruebas de ejecución |
| **D** | Spec 030 | `PREPARING → PREPARED`, declarado por `ADR-D0-012` | `test_la_maquina_de_estados_es_la_de_d0_03` |
| **E** | Spec 031 | `cancel_plan` rechaza un plan cuya preparación empezó | `test_no_se_retira_un_plan_cuya_preparacion_ya_empezo` |

Ninguna de las tres Specs se declara reabierta ni globalmente reconvergida.

Las cinco guardias que estos deltas invalidaron **se actualizaron con su razón
escrita**, no se relajaron. Tres de ellas —las que afirmaban que ninguna arista
salía de `DISPONIBLE`— cambiaron exactamente como `R-D0-10-10` había previsto:
de «no hay ninguna» a «no hay ninguna más».

## Un hueco encontrado al escribir el contrato de entrega

`R-D0-15-16` dejó a esta Spec definir el primer efecto físico irreversible. Al
redactarlo se vio que sin definirlo `cancel_plan` retiraba un plan con recogidas
ya registradas, dejando mercancía en `PICKING` sin arista de vuelta a
`DISPONIBLE`. Queda definido —**la primera recogida**— y bloqueado.

Qué hacer con un pedido que empezó a prepararse y hay que deshacer es una
pregunta abierta: necesita una arista de devolución con dueña y evidencia. No
bloquea a la 033.

## Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| `uom.py` declara para `sales_orders` estados que no existen | Spec 011 |
| Arista de devolución `PICKING → DISPONIBLE` | pendiente, con `D0-10` |
| PostgreSQL ejecutable 16.2 frente al 18.6 documentado | QA · `ENVIRONMENT_BASELINE_DEVIATION` |

## Estado resultante

| | |
|---|---|
| Spec 032 | **COMPLETE / CONVERGED** |
| Spec 023, 030, 031 | `COMPLETE / CONVERGED` con sus deltas dirigidos convergidos |
| Spec 033 | **desbloqueada por dependencia**; contrato de entrada en `spec032-spec033-handoff-contract.md`. **No implementada.** |
