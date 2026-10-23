# SPEC 054 · Delta — E2E-SPECS-PYTHON-HELPERS-VENV-FIXED

| Campo | Valor |
|---|---|
| Deuda | **E2E-SPECS-PYTHON-HELPERS-VENV-FIXED** (dueña 054; ingeniería de certificación) |
| Decisiones | OD-CERT-18 (autoridad del intérprete de los ayudantes = el de la certificación activa) · OD-CERT-16 · OD-CERT-17 · OD-ORCH-01 · OD-CERT-10/11 (no se reabren) |
| HEAD de entrada | `225fff0` |
| Ruta | H (sin Docker ni evidencia externa de OBS-09) |
| Evidencia | `evidence/e2e-specs-python-helpers/` |

## 1. Specify
- **Objetivo:** que todo proceso Python que lancen las E2E use el intérprete de la certificación en curso, sin ningún V0 fijo dentro de una certificación V5:
  - en una E2E V0, el ayudante corre en V0;
  - en una E2E V5, en CPython 3.13.16.
- **Prohibido como autoridad:**
  - `resources/backend/.venv/bin/python` y `.venv/Scripts/python.exe` fijos;
  - `python` o `python3` del PATH;
  - un Python absoluto del anfitrión;
  - cualquier respaldo silencioso.
- **Ámbito:**
  - `resources/frontend/e2e/**`, solo la selección del intérprete y un lanzador común;
  - `qa/e2e_corrida.py`, solo para exportar la autoridad;
  - sus pruebas.
- **Fuera de alcance:**
  - producto, requirements, lock, Dockerfile, compose, workflows, migraciones y esquema;
  - el comportamiento de los ayudantes;
  - `qa/e2e-seed.sh`;
  - el material de Gobierno.

## 2. Clarify (medido; `helper-inventory.json`)
- **Inventario:**
  - **12 sitios en 11 ficheros** (9 specs y 2 ayudantes TS) lanzan Python con `resolve(BACKEND, ".venv", "bin", "python")`, ya sea directo o a través de una constante `PYTHON`;
  - `e2e/global-setup.ts` lanza `bash` (`qa/e2e-seed.sh`) y sale sin hacer nada si existe `KONTROL_E2E_RUN_ID`, que la certificación fija siempre: queda fuera del camino de certificación;
  - los `.mjs` (crawlers) no lanzan procesos;
  - FIXED_HELPER_INTERPRETER_SITES_PRE = 12.
- **5 ayudantes**, que importan producto y paquetes del lock (ninguno solo stdlib):

  | Ayudante | Clase |
  |---|---|
  | `qa/rol_sin_permiso.py` | TEST_DATA_SETUP |
  | `qa/alcance_de_usuario.py` | TEST_DATA_SETUP |
  | `qa/licencia_firmada.py` | LICENSE / CRYPTO, con la clave sintética de la corrida |
  | `qa/autoridad_central.py` | LICENSE |
  | `-m app.modules.scheduler tick` | OTHER |

  HELPERS_V0_ONLY_DEPENDENCY_REQUIREMENT = 0: compilan y sus 51 imports cargan tanto en V0 como en V5.
- **Previo al ciclo:** lo introdujeron `0e8135a`, `f4fb3c0` y `ecd22fc` (2026-09-14 a 2026-10-06), y `resources/frontend` no cambió entre `d20da5b` y `225fff0`.
- **Procedencia previa, medida** con el muestreador `/proc` en E2E completas (`pre-V0-helpers.jsonl`, `pre-V5-helpers.jsonl`):
  - V0: 113 de 113 ayudantes en 3.11, con el arnés en 3.11.16;
  - **V5: 113 de 113 en 3.11 con el arnés en 3.13.16**: HELPER_INTERPRETER_PARITY_PRE_V5 = **0**.
- **Causa raíz:** E2E_SPEC_HELPER_USES_HISTORICAL_VENV_PATH.
- **Autoridad existente:** `KONTROL_E2E_PYTHON` (= `sys.executable` del arnés), que ya usaba la siembra (`e2e_base.sembrar` → `qa/e2e-seed.sh`) pero no se exportaba a la suite.

## 3. Plan
| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES |
|---|---|---|---|---|---|---|
| TA | `entorno_de_procesos` exporta `"KONTROL_E2E_PYTHON": sys.executable` a todo lo que arranca la corrida, siempre sobre el valor heredado. Pruebas e2ecorrida_25 (la suite recibe exactamente su intérprete, no el heredado) y _26 (AST: valor literal `sys.executable`) | DEEPSEEK | deepseek-v4-flash | no | sí (solo un ancla de 4 líneas: el diccionario completo lleva credenciales sintéticas de QA) | `qa/e2e_corrida.py`, `tests/test_e2e_corrida.py` |
| TB | Lanzador `e2e/helpers/python.ts` (`pythonDeLaCertificacion()` falla cerrado si falta la variable o no es absoluta; `ejecutarPython(argumentos, opciones)` = `execFileSync` sin tocar argumentos ni opciones); los 12 sitios pasan a `ejecutarPython` con argumentos y opciones idénticos; `src/tests/e2e-python-helpers.test.ts` (AST de `.ts/.mts/.js/.mjs`: 0 `.venv`, 0 `python`/`python3`, exactamente dos llamadas de proceso, inventario positivo de 12 llamadas; y 4 pruebas con procesos reales del lanzador) | DEEPSEEK | deepseek-v4-pro | no | sí | `e2e/helpers/python.ts`, 11 ficheros `e2e/**`, `src/tests/e2e-python-helpers.test.ts` |

RETRY_MAX: 2 por tarea.

## 4. Constitution gate y trazabilidad
- P2: autorizado por el encargo, que nombra la iniciativa.
- Sin producto, esquema, migraciones, lock ni base.

| Requisito | Tarea | Prueba |
|---|---|---|
| R1 Ningún literal `.venv` en `e2e/` | TB | vitest «contrato estructural» (literales) |
| R2 Ningún `python`/`python3` del PATH | TB | vitest (literales) |
| R3 Todo Python de las E2E pasa por el lanzador central (exactamente 2 llamadas de proceso; 12 llamadas a `ejecutarPython`) | TB | vitest (llamadas e inventario) |
| R4 Sin autoridad, o con una relativa, el ayudante no se ejecuta (falla cerrado; sin respaldo) | TB | vitest (lanzador, casos 1 y 2) |
| R5 El lanzador usa exactamente la autoridad y conserva argumentos, `cwd`, entorno y código de salida | TB | vitest (lanzador, casos 3 y 4) |
| R6 El arnés exporta `sys.executable`, nunca el valor heredado | TA | e2ecorrida_25, _26 |
| R7 Paridad de ayudantes medida: V0 = V0 y V5 = 3.13.16 | TA, TB | muestreo `/proc` de las E2E finales |

Trazabilidad: 7 de 7.

## 5. Material gate
| Indicador | Valor |
|---|---|
| FIXED_HELPER_INTERPRETER_SITES_PRE · HELPERS_TOTAL | 12 · 5 |
| ROOT_CAUSE_PROVEN · PREEXISTING_CONFIRMED · CERTIFICATION_INTERPRETER_AUTHORITY_FOUND · CENTRAL_LAUNCHER_FEASIBLE | 1 · 1 · 1 · 1 |
| V0_HELPER_COMPATIBLE · V5_HELPER_COMPATIBLE | 1 · 1 |
| PRODUCT · REQUIREMENTS · LOCK · BASE · SCHEMA · MIGRATION change required | 0 · 0 · 0 · 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 6. Cierre (2026-10-23)
- **Rojo contra `225fff0`** (`red-against-head.txt`): fallan las 4 pruebas estructurales y e2ecorrida_25/26. Las 4 del lanzador pasan, porque prueban el código nuevo.
- **Dirigidas:**
  - frontend: tsc y eslint limpios, vitest **490/490**;
  - backend: ruff y mypy limpios, arnés E2E y AIC **55/0/0** (PostgreSQL).
- **Mutaciones:** **19/19** eliminadas, 100 % restauradas (`mutations.json`).
- **Backend:** SQLite V0 y V5 **1956/0/1064** (+2 omitidas: e2ecorrida_25/26 solo corren sobre PostgreSQL); PostgreSQL V5 **2994/0/26** (+2).
- **V5:** reconstruido por digest; `pip check` PASS; freeze = lock; pip-audit 0/0; CA 148.
- **OpenAPI:** 544/533/11 en V0 y en V5, con la misma huella de `paths`.
- **Primer intento de E2E final no verde** (V0 280/1/3, V5 277/3/4): timeouts de 30 s con el anfitrión contendido por procesos ajenos (swap de 5,7–6,8 GB, load1 de 14–15). ENVIRONMENT, CYCLE_CHANGE_CAUSAL = 0 (`first-final-attempt-attribution.md`).
- **E2E final con la salud del anfitrión exigida y medida** (`salud.jsonl`), una vez por intérprete:

  | Intérprete | Resultado | Arnés = migración | Ayudantes |
  |---|---|---|---|
  | V0 | **284/0/0**, LIMPIA | 3.11.16 = 3.11.16 | 113 de 113 en 3.11 |
  | V5 | **284/0/0**, LIMPIA | 3.13.16 = 3.13.16 | **113 de 113 en 3.13**, ejecutable real = `ld-linux` del rootfs |

  HELPER_INTERPRETER_PARITY_V0 = HELPER_INTERPRETER_PARITY_V5 = **1**.
- **Estado:** E2E-SPECS-PYTHON-HELPERS-VENV-FIXED **CLOSED / CONVERGED**.
- **No absorbido:** E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY. Recurrió y además afectó a las cargas con `clamscan`. En V5 `licencia-revision` tarda 19,6 s frente a 17,9 s en V0 (+9 %; microbanco 1,08×).
