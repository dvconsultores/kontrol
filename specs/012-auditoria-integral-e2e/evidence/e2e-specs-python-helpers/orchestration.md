# Orquestación Claude → DeepSeek (E2E-SPECS-PYTHON-HELPERS-VENV-FIXED)

Cada encargo pasó el EGRESS CHECK antes de la llamada: `ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`.
- De `qa/e2e_corrida.py` solo salió el ancla de 4 líneas: el diccionario de `entorno_de_procesos` contiene valores por defecto de credenciales sintéticas de QA.
- Sin rutas locales.
- Los encargos se validaron primero sobre **copias aisladas**, porque las E2E previas al arreglo usaban el árbol real.
- Se aplicaron al árbol real con el aplicador mecánico (una coincidencia por SEARCH, lista cerrada de rutas, ficheros nuevos con SEARCH vacío) y se comprobó que el resultado era byte a byte igual a las copias.

| Llamada | Tarea | Modelo | Tokens (in/out) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | TA: `KONTROL_E2E_PYTHON = sys.executable` en `entorno_de_procesos`; pruebas e2ecorrida_25/26 | deepseek-v4-flash | 1779/1089 | $0.000536 | **AUDIT_REJECT**: B905 `zip()` sin `strict=`. No es una regla de formato (`strict` cambia la conducta), así que no se arregla con la herramienta |
| 2 | TA reintento 1 | deepseek-v4-flash | 1726/1094 | $0.000530 | **AUDIT_PASS** (ruff y mypy limpios) |
| 3 | TB: `e2e/helpers/python.ts`, 12 sitios en 11 ficheros, `src/tests/e2e-python-helpers.test.ts` | deepseek-v4-pro | 5109/6542 | $0.007804 | **Lanzador y 12 sitios ACEPTADOS**. Prueba **RECHAZADA**: solo recorría `.ts` (el contrato pedía `.mts/.js/.mjs`); 11 falsos positivos porque la regex de `python` casaba con el especificador `"./helpers/python"` (defecto del contrato de Claude, corregido en el reintento); errata; análisis repetido; `JSON.parse` sin tipar; prueba del código de salida ambigua |
| 4 | TB reintento 1 (solo la prueba) | deepseek-v4-pro | 4068/3222 | $0.004573 | **AUDIT_REJECT**: tsc TS2322 en el tipo de retorno de `obtenerLiteral` (vitest 13/13, eslint limpio) |
| 5 | TB reintento 2 (último): la firma de tipo | deepseek-v4-pro | 1712/298 | $0.001004 | **AUDIT_PASS**: tsc, eslint y vitest 490/490 |

- DEEPSEEK_TASKS 2 (TA; TB = lanzador + specs + pruebas) · CLAUDE_BRIEFS 5 · DEEPSEEK_CALLS 5 · DEEPSEEK_RETRIES 3 (TA 1, TB 2).
- DEEPSEEK_AUDIT_FAILURES 3 · FORMAT_ONLY_TOOL_FIXES 0 · coste **$0.014447**.
- Coste de puente en tokens de Claude, aparte del de DeepSeek: TA 31 850 + 39 513; TB 70 369 + 90 520 + 96 074.
- Herramientas desechables del scratchpad, que no se versionan: muestreador `/proc` de ayudantes, telemetría, reconstrucción de V5, aplicador y ejecutor de mutaciones. Claude no escribió código de producto, pruebas ni código QA.
- EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1 · LOCAL_PATHS_SANITIZED = 1 · SECRET_EXPOSURE = 0.
