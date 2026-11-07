# GOV-CTL-10 · registro de intentos (NC-ORCH-01)

Máximo 2 intentos semánticos por subtarea. Tras el segundo: dividir, rediseñar o bloquear. `MAX_SEMANTIC_RETRIES_PER_SUBTASK_OBSERVED = 2` por subtarea definida; las correcciones de pruebas y de la E2E se dividieron por suite, función o bloque, y esa división consta aquí.

## Backend

| Tarea | Intento 1 | Intento 2 | Decisión | Subtareas |
|---|---|---|---|---|
| T004, T009 (pruebas y servicio) | rechazado | rechazado | SPLIT por fichero | T004S, T009S, T009U |
| T005 (registro compartido) | rechazado | aceptado | n/a | T005R |
| Suites CTL-10 tras el producto | rechazado por suite | rechazado por suite | SPLIT por función | FIX-*, FIX2/G-*, S-*, S3-* |
| S3-guarda, S3-seguridad, S3-bloqueos, S3-políticas | parcial | n/a | REDISEÑO con causa raíz medida | S4-guarda, S4-resto |
| test_sg08 | S4: sin hallazgo pedido | S4b: control erróneo | REDISEÑO: ayudante común | S5 |
| M1 | parcial: SEARCH cortado por el encargo y bl07 con API inventada | aceptado | n/a | M1b |

Defectos reales de producto hallados por las pruebas: CHECK `riesgo_minimo` admitía NULL; slice sobre `ScalarResult` (dos veces, P6a y P9); regla inventada de vigencia no anterior a hoy; claves de auditoría; filtro de bloqueos tras paginar; esquema `BloqueoOut`; `GovernmentAct.tenant_id` inexistente; usuario como UUID y sin `politica_id` en bloqueos; código muerto `_politica_efectiva`; etiquetas SoD sin tilde.

## Frontend

| Tarea | Intento 1 | Intento 2 | Decisión | Subtareas |
|---|---|---|---|---|
| T012 | parcial: consultas como ruta | aceptado | n/a | T012b |
| T013 PoliticasPage | aceptado | n/a | mejoras en F1 | F1 |
| T014 NuevaPoliticaPage | rechazado: regla inventada | aceptado (T014b); el `min` restante se quitó en F1 | n/a | T014b, F1 |
| T015 PoliticaPage | rechazado: 428 como MFA, sin SoD | parcial: PC-11/12 con TODO | SPLIT | F1, T015c |
| T019, T020 | rechazado: paquete del router, `/>` doble, SEARCH inexistente | parcial: import incompleto por encargo ambiguo | SPLIT | T019b, F1 |
| T026 BloqueosPage | rechazado: import y ruta de política erróneos | aceptado | n/a | T026b, M1 |
| Vitest y tsc | F2 | F3 (`exact` dictado por Claude) | n/a | F2, F3 |
| T034 | parcial: ids en colisión, dictados por Claude | aceptado | n/a | T034b |
| T032 E2E | rechazado: rutas y firmas inventadas | parcial | SPLIT por prueba | T032s1, T032s2 |
| T032s1 (retirar la vigente) | sin texto en el encargo | parcial, solape de bloques | SPLIT de un bloque | T032s1c |
| T032s2 (CIE-E2E-03) | parcial | parcial; un bloque descartado sin reintento | n/a | T032s2b, L1 |

## Tras la E2E y las mutaciones

| Tarea | Intento 1 | Intento 2 | Decisión | Subtareas |
|---|---|---|---|---|
| L1, L2 | aceptados | n/a | n/a | L2 corrige dos fallos medidos: recurso de evidencia y `level: 1` |
| M2 (8 supervivientes y 3 muertes falsas) | aceptado, con formato irregular y dos `F841` retirados por `ruff` | n/a | n/a | M2 |
| F4 | PC-13 rechazada: permiso inventado | aceptado | n/a | F4b |
| G1, F5 | aceptados | n/a | n/a | — |
| T043 | no enviada: MCP de DeepSeek sin conexión tras el reinicio | — | ABIERTA | — |

## Errores de Claude en la orquestación, declarados

- Egress de T038a2 leído después de lanzar (falso positivo).
- Uso indebido de Workflow para 8 encargos sin orden de la dueña. No se repitió.
- Encargos con datos erróneos: `count(1980)` contra el CHECK, `exact` de Playwright en Testing Library, ids `K*` duplicados, permiso `gobierno_actos:emit`, rótulo «Tipo de control», T032s1 sin texto.
- S4b aplicado y medido en el mismo comando sin leerlo antes; desde entonces cada respuesta se extrae y audita antes de aplicar.
- Bloque 6 de T032s2b descartado por «inocuo»: la corrida demostró lo contrario y lo corrigió L2.
- Excepciones mecánicas sobre código de DeepSeek: `ruff --fix` de imports, inserción de importaciones y de la fixture indicadas por su respuesta, retirada de `scope="module"` conservando el decorador, y adaptación de bloques con SEARCH vacío a su lugar real. Ninguna añadió lógica.
- Regeneración por script, no escrita a mano: fixtures de frontend y espejo del catálogo.

CLAUDE_SEMANTIC_CODE_WRITTEN = 0.
