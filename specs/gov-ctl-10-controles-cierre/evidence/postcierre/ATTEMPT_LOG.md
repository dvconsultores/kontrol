# CTL-10 POST-CLOSURE-01 · registro de intentos

Norma: máximo 2 reintentos semánticos por subtarea real. Una subtarea nueva declara NEW_ROOT_CAUSE o NEW_TECHNICAL_BOUNDARY. Todo el código y las pruebas los escribió DeepSeek. DEEPSEEK_CALLS = 15.

| Subtarea real | Intento inicial | Reintento 1 | Reintento 2 | Resultado |
|---|---|---|---|---|
| Pruebas backend lc01..lc10 | B0: rechazado, `como(...).get` | B0b: sin parche, el encargo no llevaba el fichero | B0c: aceptado | 2 reintentos |
| Backend T042 | B1: lógica aceptada; encargo de Claude borró `RIESGOS` aún en uso | B1b: aceptado | — | 1 reintento |
| Producto hallazgos | FH: aceptado salvo `in`, corregido en FH2 | — | — | 1 reintento |
| Producto actos | FA: aceptado salvo `in`, corregido en FA2 | — | — | 1 reintento |
| Pruebas HCTX-01..07 | FH: rechazadas | FH2: rechazadas | FH3: aplicadas; 3 fallaron | 2 reintentos, STOP |
| Espera en HCTX-01, 04, 05 | FH4: aceptado | — | — | NEW_ROOT_CAUSE: `LoadingState` también es `role="status"` |
| Pruebas ACTX-01..06 | FA: rechazadas | FA2: aceptadas; 2 fallaron por el mock | FA3: aceptado | 2 reintentos |
| E2E del enlace | E1: aceptado | — | — | 0 reintentos |
| Pruebas HCTX-08, 09; ACTX-07..09 | M3: parcial | M3b: aceptado | — | NEW_TECHNICAL_BOUNDARY: comportamientos sin prueba; 1 reintento |

MAX_SEMANTIC_RETRIES_PER_REAL_SUBTASK = 2.

**Errores de Claude en los encargos:** dejar ambigua la llamada HTTP en B0, B0b sin fichero, borrar `RIESGOS` por una salida de `grep` truncada, años fuera del mock en ACTX.

**Adaptaciones mecánicas, sin lógica:** lado REPLACE de FH3, inserción por nombre de pruebas devueltas como bloque, y aplicación de B1b, que llegó con formato `SEARCH:` / `REPLACE:`. Regeneración por script de `openapi-routes.json`.

FH4 terminó con `finish_reason: length` en el informe; los tres bloques llegaron completos y se comprobaron uno a uno.
