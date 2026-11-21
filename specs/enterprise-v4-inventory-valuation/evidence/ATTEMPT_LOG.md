# ATTEMPT_LOG · V4

`DEEPSEEK_HARD_CAP=12` · `OWNER_EXCEPTION_USED=0`.

## Entrada

| Campo | Valor |
|---|---|
| Rebaseline publicado | Sí. `29f8fcb9` empujado al empezar el ciclo por SSH (`origin` pasó de HTTPS a `git@github.com:dvconsultores/kontrol.git`; la clave del puesto ya autenticaba). PUSH_RC=0 |
| ENTRY_HEAD = ORIGIN | `29f8fcb9` |
| Alembic | cabeza única `0128_gov_tre04_pago` |

## Clasificación de tareas

Por `.claude/CLAUDE.md` (precedencia 4) son `CLAUDE_ONLY` las de costeo y semántica contable, migración, permisos y
diseño de concurrencia: T002–T007 son eso, y las implementó Claude. DeepSeek recibió las tareas de UI con
contrato cerrado.

## Llamadas a DeepSeek

| # | Tarea | Modelo | Tokens in/out | Costo | Resultado | Motivo |
|---|---|---|---|---|---|---|
| 1 | T010 UI Conteos/Ajustes/Movimientos | deepseek-v4-flash | 4 653 / 2 044 | $0,001906 | **AUDIT_PASS**: 14 bloques aplicados con coincidencia única | Contrato cumplido. Las claves de `ETIQUETAS` no usadas en Ajustes las pidió el contrato (mapa común) |
| 2 | T011 UI Transferencias | deepseek-v4-pro | 4 413 / 3 513 | $0,009705 | **AUDIT_REJECT** | Los 5 bloques traían un `=======` extra y un REPLACE vacío (malformados); botón `type="submit"` fuera de su formulario |
| 3 | T011 reintento 1 | deepseek-v4-pro | 3 735 / 3 336 | $0,008907 | **AUDIT_REJECT** | Formato correcto, pero se desvió del contrato: etiquetas de estado incompletas (REVERSED, PICKING, CANCELLED, REJECTED), sin respaldo al id, valor sin moneda, recepción sin inicializar con lo pendiente, opciones solo con el código |
| 4 | T011 reintento 2 | deepseek-v4-pro | 3 950 / 3 707 | $0,009784 | **AUDIT_REJECT** | `received` enviado como lista de objetos en lugar del diccionario del contrato (la API respondería 422) |

Tras dos reintentos, tope alcanzado: Claude reclasificó T011 y la implementó (no se aplicó ningún bloque de
DeepSeek en Transferencias; nada se atribuye al ejecutor).

`DEEPSEEK_CALLS=4` · `DEEPSEEK_RETRIES=2` · `DEEPSEEK_ACCEPTED_PATCHES=1` · `DEEPSEEK_REJECTED_PATCHES=3` ·
costo total ≈ $0,0303.

## Reparaciones de entorno (autónomas, autorizadas por el prompt)

| Reparación | Motivo |
|---|---|
| `git remote set-url origin` a SSH | El credential helper HTTPS no existía; la clave SSH del puesto ya autenticaba |
| Navegadores de Playwright (chromium y firefox de la versión fijada) | La build instalada no correspondía a la del lockfile |
| ClamAV de QA: `libmspack0` extraído al prefijo de usuario | `clamscan` no arrancaba; sin analizador las cargas documentales se rechazan |
| Node 20 con nvm | La imagen del frontend es `node:20`; con Node 24, 29 pruebas de Vitest fallaban por `AbortSignal` (entorno). Con Node 20: 232/232 ficheros |
| Bases temporales `kmig_v4` y worktrees temporales de base | Prueba de migración y clasificación de fallos; eliminados |

## Clasificación de fallos observados

| Fallo | Clase | Reproducido en base | Acción |
|---|---|---|---|
| `CostingProfile(name=…)` en la prueba nueva | TEST_DEFECT (propio) | n/a | prueba corregida |
| Prueba de doble reversión aceptaba cualquier conflicto (M6 sobrevivía) | TEST_DEFECT (propio) | n/a | prueba reforzada; M6 muere |
| `almacen.id` en el paso 17 de la E2E de importaciones | TEST_DEFECT (propio) | n/a | corregido (lo detecta el typecheck) |
| E2E: navegador ausente de la versión fijada | ENVIRONMENT_FAILURE | — | navegador instalado |
| E2E de importaciones: carga documental rechazada | ENVIRONMENT_FAILURE | — | ClamAV provisionado |
| E2E de importaciones: la pestaña de impresión del reporte de diferencias no llega a `blob:` (línea 515) | BASELINE | **Sí** (`29f8fcb9`, chromium y firefox) | No absorbido. Un intento de esperar la navegación (`waitForURL`) no lo resolvió y se revirtió |
| Vitest: 29 fallos `AbortSignal` en 7 ficheros ajenos | ENVIRONMENT_FAILURE (Node 24) | **Sí** | Node 20: 0 fallos |
