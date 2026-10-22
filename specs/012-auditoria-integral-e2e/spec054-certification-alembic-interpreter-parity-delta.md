# SPEC 054 · Delta — CERTIFICATION-ALEMBIC-INTERPRETER-PARITY

| Campo | Valor |
|---|---|
| Deudas | **TEST-MIGRACIONES-VENV-FIJO** (dueñas 052/054) · **E2E-HARNESS-INTERPRETER-FIXED** (dueña 054). Se conservan por separado para la trazabilidad; comparten causa, diseño y evidencia |
| Decisiones | **OD-CERT-10** (cierre conjunto autorizado) · **OD-CERT-11** (autoridad de ejecución de alembic = intérprete del proceso que certifica) · OD-CERT-01..09 · OD-LOCK-01..03 · OD-SEC-01/02 |
| Spec cruzada | Spec 052 (`specs/001-fundacion/dependency-matrix.md`: V5 como línea base del intérprete de despliegue) |
| HEAD de entrada | `d20da5b` |
| Ruta | M (sin evidencia externa de OBS-09) |
| Evidencia | `evidence/certification-alembic-interpreter-parity/` |

## 1. Specify
- **Objetivo:** que todo alembic que participa en la certificación se ejecute con el intérprete que se está
  certificando. Al certificar V0, la migración corre con V0; al certificar V5, con V5.
- **Ámbito:** las pruebas de migración de `resources/backend/tests/**` y la migración de la Autoridad Central en
  `qa/e2e_corrida.py`.
- **Prohibido como autoridad:** `.venv/bin/alembic` (o `Scripts/alembic.exe`), `alembic`, `python` o `python3` del
  PATH, y cualquier recurso al anfitrión.
- **Fuera de alcance:**
  - el producto, `alembic/versions/**`, el lock, `requirements.txt`, la base, la CA, Dockerfile, compose y workflows;
  - el resto de `qa/**`: `pg-migration-validation.sh` es QA manual y queda solo en el inventario;
  - las demás deudas.

## 2. Clarify
Todo medido en `evidence/certification-alembic-interpreter-parity/pre-fix-reproduction.md` y
`fixed-path-inventory.json`.

- **Inventario (AST):**
  - 19 rutas fijas en 15 ficheros de prueba y 1 en `qa/e2e_corrida.py:393`: FIXED_VENV_PATHS_PRE = 20;
  - 0 `alembic` sin ruta y 0 `python` del PATH;
  - los usos de la API en proceso (`command.upgrade`) ya corren en el intérprete que certifica.
- **Gate de capacidad:** `python -m alembic` funciona en V0 y en V5 (alembic 1.14.0). Mismo `alembic.config.main`,
  mismo código de salida; `prepend_sys_path = .` y `cwd=BACKEND` neutralizan la diferencia de `sys.path[0]`.
- **Defecto en V5:**
  - pruebas: pytest corre en 3.13.16, pero los 72 hijos alembic usan el `.venv` de V0 (3.11.16);
  - E2E: el tenant se migra con V5, pero la autoridad con V0.
- **Sin `.venv`:** 88 FileNotFoundError y 3 omisiones silenciosas (`test_migrations_offline.py`).
- **Decisión sobre las omisiones:** las tres guardas `if not alembic_bin.exists(): pytest.skip(...)` dependen de la
  ruta fija. Con el contrato nuevo, alembic forma parte del grafo certificado, así que su ausencia debe **fallar**, no
  omitirse. Se retiran las guardas, sin añadir ningún skip.

## 3. Plan
| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES |
|---|---|---|---|---|---|---|
| T1 | Helper de pruebas `tests/alembic_orden.py` (`orden_alembic(*argumentos)` → `[sys.executable, "-m", "alembic", *argumentos]`). Los 19 sitios pasan a usarlo con los mismos argumentos, cwd, env, timeout y captura. Se retiran las 3 guardas de omisión | DEEPSEEK | deepseek-v4-pro | no | sí | `tests/alembic_orden.py` + los 15 ficheros del inventario |
| T2 | Prueba estructural y de procedencia `tests/test_alembic_interprete_certificado.py` (AIC-01..07) | DEEPSEEK | deepseek-v4-pro | no | sí | `tests/test_alembic_interprete_certificado.py` |
| T3 | `qa/e2e_corrida.py:393`: la migración de la autoridad usa `[sys.executable, "-m", "alembic", "-c", "central_authority/alembic.ini", "upgrade", "head"]`; nada más cambia | DEEPSEEK | deepseek-v4-flash | no | sí | `qa/e2e_corrida.py` |
| T4 (cierre) | Procedencia medida en el manifiesto E2E (OD-CERT-15): `SONDA_DEL_INTERPRETE`, con el mismo ejecutable, `cwd` y entorno que la migración y antes que ella; `manifiesto["interpretes"]` = arnés, migración de la autoridad (orden, ejecutable, `exe_real`, Python, alembic, SQLAlchemy) y paridad, todo saneado; solo observa; la corrida aborta si la sonda falla. Pruebas e2ecorrida_19..23 | DEEPSEEK | deepseek-v4-pro | no | sí | `qa/e2e_corrida.py`, `tests/test_e2e_corrida.py` |
| T5 (cierre) | Pruebas de los supervivientes M22, M24 y M25: AIC-08 (`cwd`/`env` de la sonda = los de la migración, y llamada anterior a ella) y e2ecorrida_24 (JSON válido con código ≠ 0) | DEEPSEEK | deepseek-v4-flash | no | sí | `tests/test_alembic_interprete_certificado.py`, `tests/test_e2e_corrida.py` |

RETRY_MAX: 2 por tarea. DONE_WHEN:
- T1: 0 rutas `.venv` en `tests/**` y las 98 pruebas afectadas verdes en V0 y V5;
- T2: AIC en rojo contra `d20da5b` por las rutas fijas, y verde después;
- T3: AIC-06 verde, E2E 284/0/0 en V0 y V5, con paridad medida.

## 4. Constitution gate y trazabilidad
- P2: implementación autorizada en el encargo, que nombra la iniciativa.
- P21 (PostgreSQL real): las pruebas de migración siguen corriendo sobre PostgreSQL.
- Sin cambios de producto, esquema, migraciones, lock ni base.

| Requisito | Deuda | Tarea | Prueba |
|---|---|---|---|
| R1 Ninguna ruta `.venv` en el código de certificación | ambas | T1, T3 | AIC-01 |
| R2 Ningún alembic ni python del PATH para migrar | ambas | T1, T3 | AIC-02 |
| R3 El detector reconoce cada variante prohibida y no rechaza docstrings ni comentarios | ambas | T2 | AIC-03 |
| R4 El helper usa `sys.executable` | TEST-MIGRACIONES-VENV-FIJO | T1 | AIC-04 |
| R5 Cada subproceso de alembic de las pruebas usa el contrato | TEST-MIGRACIONES-VENV-FIJO | T1 | AIC-05 |
| R6 La migración de la autoridad en E2E usa el contrato exacto, con cwd y env intactos | E2E-HARNESS-INTERPRETER-FIXED | T3 | AIC-06 |
| R7 El hijo alembic tiene el mismo intérprete, Python, alembic y SQLAlchemy que el padre | ambas | T1 | AIC-07 |
| R8 Mismos argumentos, cwd y env que antes | ambas | T1, T3 | las 98 pruebas de migración sobre PostgreSQL y E2E |
| R9 Sin `.venv` las pruebas pasan, sin omisiones | TEST-MIGRACIONES-VENV-FIJO | T1 | árbol aislado en V5 |
| R10 Cada corrida E2E deja medido, saneado, el intérprete del arnés y el de la migración de la autoridad, y su paridad | E2E-HARNESS-INTERPRETER-FIXED | T4 | e2ecorrida_19, _20, _21 |
| R11 La sonda mide con el mismo `cwd` y entorno que la migración y antes que ella; si falla o miente, la corrida no sigue y limpia | E2E-HARNESS-INTERPRETER-FIXED | T4, T5 | AIC-08, e2ecorrida_22, _23, _24 |

Trazabilidad: 11 de 11 requisitos con tarea y prueba.

## 5. Material gate
| Indicador | Valor |
|---|---|
| FIXED_VENV_PATHS_PRE | 20 (19 en pruebas y 1 en QA) |
| FILES_AFFECTED_TESTS · FILES_AFFECTED_QA | 15 · 1 |
| V0_PYTHON_M_ALEMBIC_SUPPORTED · V5_PYTHON_M_ALEMBIC_SUPPORTED | 1 · 1 |
| MIGRATION_INTERPRETER_PARITY_PRE · E2E_INTERPRETER_PARITY_PRE | 0 · 0 (V5) |
| SHARED_ROOT_CAUSE · SHARED_MECHANISM | 1 · 1 |
| DESIGN_PRESERVES_ARGUMENTS · ENV · CWD | 1 · 1 · 1 |
| PRODUCT · MIGRATION · REQUIREMENTS · LOCK · BASE change required | 0 · 0 · 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 6. Cierre (2026-10-22)

**Entrada:** `PARTIAL`, con T1..T3 aplicados y sin confirmar. El único bloqueo era la E2E completa: `licencia-revision.spec.ts:115` superó los 30 s en dos corridas, sin intérprete registrado.

- **Atribución del timeout** (`evidence/certification-alembic-interpreter-parity/timeout-attribution.md`):
  - D1 (`d20da5b`, V0), D2 (árbol, V0) y D3 (árbol, V5) son verdes con el mismo perfil: 17,3–17,5 s, de los que 0,8 s son API y 16,5–16,7 s ayudantes Python síncronos;
  - en la ventana del fallo la suite completa tardó un 26–44 % más (swap 7–8 GB y paginación) y otra prueba (`accessibility`) también superó los 30 s;
  - **ROOT_CAUSE_CLASS = ENVIRONMENT** · CYCLE_CHANGE_CAUSAL = 0 · `Request context disposed` = CONSEQUENCE_OF_GLOBAL_TIMEOUT. Ningún timeout cambió (OD-CERT-13).
- **Procedencia (OD-CERT-15):** T4 la mide y T5 cierra los supervivientes de las mutaciones.
- **Certificación final** (`certification.md`):

  | Ámbito | Resultado |
  |---|---|
  | SQLite V0 · V5 | 1956/0/1062 · 1956/0/1062 |
  | PostgreSQL V5 | 2992/0/26 |
  | E2E V0 | **284/0/0**, paridad 3.11.16 = 3.11.16 |
  | E2E V5 | **284/0/0**, paridad 3.13.16 = 3.13.16 |
  | OpenAPI | 544/533/11 |
  | Mutaciones | 26/26 |
  | V5 | pip-audit 0/0, `pip check` PASS |

- **Deudas nuevas, no absorbidas:**
  - **E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY**;
  - **E2E-SPECS-PYTHON-HELPERS-VENV-FIXED** (12 sitios en `e2e/*.ts`, fuera de OD-CERT-11).
- **Estado:** TEST-MIGRACIONES-VENV-FIJO **CLOSED / CONVERGED** · E2E-HARNESS-INTERPRETER-FIXED **CLOSED / CONVERGED**.
