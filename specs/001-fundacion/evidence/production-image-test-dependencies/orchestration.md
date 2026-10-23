# Orquestación Claude → DeepSeek (PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES)

**Reglas aplicadas:**
- Cada encargo pasó el EGRESS CHECK **antes** de la llamada, y las delegaciones fueron **en serie**.
- No salió nada de `entorno_de_procesos` (`qa/e2e_corrida.py`) ni las partes JWT de `test_seguridad_dependencias.py`: llevan credenciales y claves sintéticas de QA.
- Sin rutas locales.
- Se aplicó desde la respuesta **cruda** de `deepseek_chat` con el aplicador mecánico: una coincidencia por SEARCH, lista cerrada y, para aceptar solo una parte de una respuesta, `--solo-permitidas`.
- Los locks no los escribe nadie: los genera `uv pip compile` con la orden canónica (ver `certification.md`).

| Llamada | Tarea | Modelo | Tokens (in/out) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1: separar `requirements.txt` / `requirements-test.txt`; etapa `dev` con `requirements-test.lock`; README | v4-flash | 1582/1378 | $0.000590 | **AUDIT_PASS** (dos «MATERIAL DECISION» del modelo: falsas alarmas) |
| 2 | T2: IDF-01..09, IDL-05, SDV-08 | v4-pro | 7250/6203 | $0.008440 | **REJECT**. IDF-01 mal construida (exigía que los pines de certificación no fueran herramientas); 3 fallos y 6 errores de ruff; bucle muerto `if False`; `except SyntaxError: continue`. IDF-08 detecta además el import opcional de `boto3` (hallazgo real) |
| 3 | T2 reintento 1 | v4-pro | 6503/7447 | $0.009197 | **A (IDL-05) y B (SDV-08) ACEPTADOS**. C rechazado: IDF-06 e IDF-07 vacías (recorrían nombres de etapa), IDF-08 ignoraba imports perezosos y traducía mal módulo→distribución, `group("paquete")` inexistente |
| 4 | T2 reintento 2 (último) | v4-pro | 5143/5050 | $0.006520 | **REJECT**: rutas en `RAIZ` en lugar de `BACKEND`, B007, la protección de `boto3` detrás de un `continue` → **reclasificación: T2 se divide en T2d + T2e** |
| 5 | T2d: IDF-01..07, 09 desde la base de DeepSeek con C1–C6 | v4-pro | 5134/4060 | $0.005655 | **AUDIT_PASS**; queda I001 → arreglo de formato con la herramienta (ver abajo) |
| 6 | T2e: IDF-08 + ayudantes de protección + casos de IDF-09 | v4-pro | 2762/2439 | $0.003213 | **AUDIT_PASS** |
| 7 | T3: arnés con `--python-de-producto` (backend y autoridad en V6R), sonda de producto, e2ecorrida_27..31 | v4-pro | 5746/4099 | $0.006066 | **REJECT**: sonda con `… if False else …` y canonización por `.replace`; `comprobar()` se saltaba la validación si la ruta era `sys.executable`; sin validar tipos; F841 |
| 8 | T3 reintento 1 | v4-pro | 4346/3809 | $0.005204 | **`qa/e2e_corrida.py` ACEPTADO** (ruff y mypy limpios; sonda ejecutada: 5 claves). Pruebas rechazadas: firmas de `_manifiesto`/`_sin_rastro` erróneas, nombres acortados, `pathlib` sin importar |
| 9 | T3 reintento 2 (último): solo pruebas, las del intento 1 sin la línea F841 | v4-pro | 1450/1404 | $0.001852 | **AUDIT_PASS** |
| 10 | T4: matar M23 y M25 (e2ecorrida_27 + e2ecorrida_32) | v4-flash | 1171/858 | $0.000404 | **AUDIT_PASS** |

**Totales:** DEEPSEEK_TASKS 6 (T1, T2, T2d, T2e, T3, T4) · CLAUDE_BRIEFS 10 · DEEPSEEK_CALLS 10 · DEEPSEEK_RETRIES 4 (T2 ×2, T3 ×2) · DEEPSEEK_AUDIT_FAILURES 5 · coste **$0.047141**.

**Arreglo de formato con la herramienta (OD-ORCH-01):** `ruff check --select I001 --fix tests/test_dependencias_frontera.py`, sobre el T2d ya aceptado. El diff completo, auditado, **solo** mueve `_PIN` dentro de la lista de imports. FORMAT_ONLY_TOOL_FIXES = 1 · FORMAT_ONLY_DIFF_VERIFIED = 1.

**Coste de puente**, en tokens de Claude, aparte del de DeepSeek: T1 29 921; T2 79 067 + 117 995 + 146 345; T2d 49 668; T2e 46 584; T3 54 416 + 71 638 + 79 846; T4 28 541.

**Herramientas desechables del scratchpad**, que no se versionan:
- construcción de V6R y V6C (rootfs por digest);
- humo de runtime;
- muestreador `/proc`, telemetría y condición de salud;
- aplicador y ejecutor de mutaciones.

Claude no escribió código de producto, pruebas ni código QA.

EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1 · LOCAL_PATHS_SANITIZED = 1 · SECRET_EXPOSURE = 0.
