# Orquestación Claude → DeepSeek (CERTIFICATION-ALEMBIC-INTERPRETER-PARITY)

Cada encargo se redactó con fragmentos literales y pasó el EGRESS CHECK **antes** de la llamada, nunca en paralelo:
`ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`. Sin rutas locales ni
URL de PostgreSQL. Los parches se aplicaron desde la respuesta **cruda** de `deepseek_chat` (traza del subagente) con un
aplicador mecánico que exige una sola coincidencia por SEARCH y una lista cerrada de rutas.

| Llamada | Tarea | Modelo | Tokens (in/out) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1: helper `tests/alembic_orden.py` y 19 sitios en 15 ficheros; 3 guardas de omisión retiradas | deepseek-v4-pro | 6100/4936 | $0.006837 | **AUDIT_PASS** a la primera (35 bloques, una sola coincidencia cada uno; ruff y mypy limpios) |
| 2 | T2: prueba estructural y de procedencia AIC-01..07 | deepseek-v4-pro | 5222/5070 | $0.006572 | **AUDIT_REJECT** (R1 AIC-03 definida dos veces, sin `parametrize` (F811); R2 `_docstrings` no excluía la docstring del módulo ni las anidadas (mypy); R3 `try/except OSError: continue`; R4 AIC-05 comparaba claves relativas a RAIZ con rutas relativas a BACKEND (siempre fallaría); R5 sin `-> None`; R6 función anidada) |
| 3 | T2 reintento 1 | deepseek-v4-pro | 6304/4600 | $0.006634 | **AUDIT_REJECT** solo de formato: R7 I001 (bloque de imports) y R8 UP038 (`isinstance` con tupla). Funcionalmente correcto: 25/27, con los 2 fallos esperados hasta T3 |
| 4 | T2 reintento 2 (último) | deepseek-v4-pro | 2126/373 | $0.001139 | **AUDIT_PASS** (3 bloques exactos; ruff y mypy limpios) |
| 5 | T3: `qa/e2e_corrida.py:393` | deepseek-v4-flash | 1564/490 | $0.000339 | **AUDIT_PASS** a la primera (1 línea) |

- DEEPSEEK_TASKS 3 · CLAUDE_BRIEFS 5 (3 encargos y 2 reintentos) · DEEPSEEK_CALLS 5 · DEEPSEEK_RETRIES 2 (T2) ·
  DEEPSEEK_AUDIT_FAILURES 2 · coste total **$0.021521**.
- El puente truncó una vez el contexto del intento anterior (reintento 2 de T2), como en la deuda conocida
  EJECUTOR-ABREVIA-EL-CONTEXTO. No afectó: los tres SEARCH venían literales en el propio encargo y se verificaron contra
  el fichero.
- Claude no escribió código de producto, pruebas ni guiones QA. Las sondas de medida (`sitecustomize`, inventario AST,
  reconstrucción de V5, aplicador, ejecutor de mutaciones) son herramientas desechables del scratchpad y no se
  versionan.
- EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1 · LOCAL_PATHS_SANITIZED = 1 · SECRET_EXPOSURE = 0.

## Cierre (2026-10-22): procedencia del intérprete en E2E (T4) y pruebas de los supervivientes (T5)

| Llamada | Tarea | Modelo | Tokens (in/out) | Coste | Auditoría |
|---|---|---|---|---|---|
| 6 | T4: sonda del intérprete y `manifiesto["interpretes"]` en `qa/e2e_corrida.py`; pruebas e2ecorrida_19..22 | deepseek-v4-pro | 4259/3858 | $0.005099 | **AUDIT_REJECT**. R1: la 19 no ejecutaba la corrida. R2: E401. R3: `import os` local. R4: B904. R5: no exigía exactamente 8 claves str en un objeto JSON. R6: paridad calculada dos veces. R7: `str(valor)` |
| 7 | T4 reintento 1 | deepseek-v4-pro | 4252/3750 | $0.005002 | **AUDIT_PASS funcional** (aplicado; añade e2ecorrida_23). Ruff tras aplicar: UP031 ×2 e I001 |
| 8 | T4 reintento 2 (último): solo los 3 errores de ruff y la aserción de consola por línea | deepseek-v4-pro | 1417/1658 | $0.002059 | **AUDIT_PASS** (2 bloques exactos) |
| 9 | T5: AIC-08 (la sonda con el mismo `cwd`/`env` que la migración y antes que ella) y e2ecorrida_24 (JSON válido con código ≠ 0) | deepseek-v4-flash | 2785/1718 | $0.000871 | **AUDIT_PASS** a la primera; mata M22, M24 y M25 |

- **Excepción de formato (declarada):** tras el reintento 2 quedó un I001. Ruff trata `alembic` como de primera parte por el directorio `alembic/` del backend y exige separarlo de `sqlalchemy`. Agotados los reintentos, se aplicó `ruff check --select I001 --fix tests/test_e2e_corrida.py`: reordenación generada por la herramienta, sin autoría de código.
- **Aplicación:** desde la respuesta cruda de `deepseek_chat` (traza del subagente), con el aplicador mecánico (una coincidencia por SEARCH, lista cerrada de rutas, pasada en seco antes).
- **Cierre:** DEEPSEEK_TASKS 2 · CLAUDE_BRIEFS 4 · DEEPSEEK_CALLS 4 · DEEPSEEK_RETRIES 2 (T4) · AUDIT_FAILURES 1 · coste **$0.013031**.
- **Ciclo completo:** DEEPSEEK_TASKS 5 · CLAUDE_BRIEFS 9 · DEEPSEEK_CALLS 9 · RETRIES 4 · AUDIT_FAILURES 3 · coste **$0.034552**.
- **Coste de puente:** el subagente puente consumió 65 529 + 86 988 + 97 499 (T4, tres llamadas acumuladas) y 45 176 (T5) tokens de Claude, aparte del coste de DeepSeek.
- **Herramientas desechables del scratchpad, que no se versionan:** reconstrucción de V5, telemetría, desglose de trazas, aplicador y ejecutor de mutaciones. Claude no escribió código de producto, pruebas ni guiones QA.
- EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1 · LOCAL_PATHS_SANITIZED = 1 · SECRET_EXPOSURE = 0.
