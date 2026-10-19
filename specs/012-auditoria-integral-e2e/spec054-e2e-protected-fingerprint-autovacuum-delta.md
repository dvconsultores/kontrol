# SPEC 054 · Delta — E2E-HARNESS-PROTECTED-FINGERPRINT-COUNTS-AUTOVACUUM

- **Dueña:** Spec 054 (herramienta QA de corridas E2E). Apoyo: Spec 046 (certificación de B1).
- **Fecha:** 2026-10-19, rama `develop`, HEAD de partida `97e1ea8`.
- **Atribución de origen:** `specs/046-gestion-documental/evidence/document-upload-db-connection-scan-fix/postgres-failure-attribution.md`.
- **Evidencia:** `evidence/e2e-protected-fingerprint-autovacuum/`.
- **Ruta B:** no hay evidencia Docker externa de OBS-09.

## 1. Specify

`qa/e2e_base.py::huella` debe demostrar DB-17/DB-18 (FR-054-E2EDB-005/009): que ningún proceso de la corrida se conectó
a las bases protegidas ni las escribió, sin que el observador se conecte a ellas. Hoy compara
`tup_inserted + tup_updated + tup_deleted` de `pg_stat_database`, que también mueven autovacuum y autoanalyze: el
resultado es un falso positivo intermitente (`test_e2ecorrida_01`, certificación PostgreSQL de B1).

## 2. Clarify — invariante, desde las fuentes

| Pregunta | Respuesta | Fuente |
|---|---|---|
| PROTECTED_DB_INVARIANT_CONNECTIONS | **Sí, prohibida**: «ningún proceso de la corrida se conecta a ella» | FR-054-E2EDB-005/009 (§24 del delta E2E) |
| PROTECTED_DB_INVARIANT_WRITES | **Sí, prohibida**: «nadie se conectó a ella ni la escribió» | `test_e2ecorrida_01`; DB-17/18 |
| PROTECTED_DB_INVARIANT_DDL | **Sí, prohibido**: «no se crea, trunca, recrea, migra ni elimina» | FR-054-E2EDB-005/009 |
| PROTECTED_DB_INVARIANT_BACKGROUND_MAINTENANCE | **Permitido**: el contrato habla de procesos de la corrida; autovacuum es del servidor | FR-054-E2EDB-005/009 |
| PROTECTED_DB_INVARIANT_OBSERVER_CONNECTION | **No**: la huella se lee «sin conectarse a ellas» | §24 fila 27–28; `test_e2eciclo_23` |
| PREEXISTING_CLIENT_BACKENDS_ALLOWED | **1**: el contrato no prohíbe sesiones ajenas abiertas antes; su actividad durante la corrida debe delatarse | ver §4 |

- La huella solo se escribe en el manifiesto (`protegidas_sin_cambios`).
- No cambia el código de salida del lanzador.
- Su único juez es la prueba.

## 3. Reproducción y semántica medida (PostgreSQL 16.2 de QA)

**Montaje de las sondas:**
- Desechables, no versionadas; sus resultados están en `statistics-semantics.json` y `activity-signal.json`.
- Base propia `kontrol_sonda_huella_*`, eliminada al terminar, con residuo 0.
- El observador lee siempre desde la base administrativa.

| Acción | sessions | clientes visibles | xact_commit | tup_* | active_time |
|---|---|---|---|---|---|
| nada | = | = | = | = | = |
| conexión + SELECT, abierta | +1 al instante | +1 | +1 | = | = |
| INSERT / UPDATE / DELETE desde una conexión nueva | +1 | — | +2 | +1 | + |
| sesión preexistente que escribe | **=** | = | +2 | +1 | + (vuelco diferido) |
| ANALYZE manual (H1A, por un cliente explícito) | +1 | — | +2 | **+2** | + |
| VACUUM manual | +1 | — | +5 | = | + |
| **autovacuum/autoanalyze natural (H1B)** | **=** | **=** | **+5** | **+2** | **=** |

**Lectura:**
- CURRENT_FALSE_POSITIVE_REPRODUCED = 1: H1B mueve la huella actual sin ningún cliente, en 11,4 s.
- `xact_commit` tampoco sirve: autovacuum lo mueve.
- `sessions` no lo mueve autovacuum y cuenta la conexión nueva en cuanto se establece.
- **SESSIONS_ONLY_SUFFICIENT = 0**: una sesión preexistente escribe sin moverla.

**Segunda señal** (`activity-signal.json`): `pg_stat_activity.state_change` de cada `client backend`.
- Se lee de memoria compartida, sin vuelco diferido.
- Es estable entre lecturas mientras la sesión no hace nada.
- Cambia al instante con cualquier sentencia de una sesión preexistente, incluido un SELECT dentro de una transacción.
- `track_activities = on`.
- El `oid` de la base cambia si se recrea.

## 4. Contrato final de la huella

- **WHAT_THE_FINGERPRINT_PROVES:** entre la lectura de antes y la de después, ningún cliente abrió una sesión en la
  base, ninguna sesión cliente ya abierta ejecutó una sentencia en ella, y la base no se eliminó ni se recreó.
- **ALLOWED_ACTIVITY:** autovacuum, autoanalyze y cualquier proceso del servidor que no sea `client backend`; y la
  existencia, sin actividad, de una sesión cliente ajena abierta antes de la lectura de antes.
- **FORBIDDEN_ACTIVITY:** toda sesión cliente nueva, con o sin escritura; toda sentencia de una sesión cliente
  preexistente; DDL; eliminar o recrear la base.
- **METRICS_USED** (por base):
  - `oid` (`pg_database.oid`): detecta recreación.
  - `sesiones` (`pg_stat_database.sessions`): solo la mueven los `client backend`; autovacuum, no, según lo medido.
  - `clientes`: la lista ordenada de `[pid, backend_start, state_change]` de `pg_stat_activity` con
    `backend_type = 'client backend'`, sin el propio observador. Detecta, al instante, la sesión todavía abierta y la
    actividad de una sesión preexistente.
- **BACKGROUND_ACTIVITY_IGNORED:** `tup_*`, `xact_*` y `blks_*` dejan de compararse; los trabajadores de autovacuum no
  son `client backend`.
- **CLIENT_ACTIVITY_DETECTED:**
  - conexión nueva: `sesiones` y `clientes`;
  - escritura o lectura desde una sesión nueva: `sesiones`;
  - sentencia de una sesión preexistente: `state_change`;
  - recreación: `oid`.
- **STATISTICS_PROPAGATION_HANDLED_DETERMINISTICALLY = 1, por construcción y sin esperas:**
  - una sesión nueva vuelca `sessions` en su primera espera ociosa;
  - al cerrarse, vuelca de forma forzada antes de desaparecer de `pg_stat_activity` (`before_shmem_exit` precede a
    `on_shmem_exit`);
  - en todo instante, la sesión está listada en `clientes` o ya contada en `sesiones`;
  - la actividad de una preexistente no depende del vuelco: `state_change` es inmediato;
  - `active_time` se descarta precisamente porque su vuelco es diferido.
- **BASELINE_PRECONDITIONS / OBSERVER_CONNECTION_POLICY:**
  - el observador usa una sola conexión administrativa a la base de mantenimiento, nunca a una base medida;
  - si la base administrativa estuviera entre las medidas, la huella **falla cerrada** con `CicloDeBaseRoto` y no da
    un falso PASS;
  - una base inexistente vale `None` antes y después: es el contrato vigente; si aparece o desaparece, la huella cambia.
- **FALSE_POSITIVE_CASES_KILLED:** autovacuum/autoanalyze real (T2/T8).
- **FALSE_NEGATIVE_CASES_KILLED:**
  - conexión abierta (T3a) y conexión ya cerrada (T3b);
  - INSERT, UPDATE y DELETE desde una conexión nueva (T5–T7);
  - escritura de una sesión preexistente (T-pre);
  - recreación (T-rec);
  - observador dentro del conjunto medido (T9).

## 5. Plan · 6. Constitution gate
- **QA:** solo `huella` en `qa/e2e_base.py`.
- **Pruebas:** `tests/test_e2e_base_ciclo.py`.
  - `test_e2eciclo_23` se adapta a las claves nuevas sin perder su intención: estable sin actividad y 0 conexiones.
  - Se añaden pruebas nuevas.
  - El módulo es solo de PostgreSQL por su `pytestmark` vigente, así que no hay omisiones nuevas.
- **Sin cambios en:** producto, `e2e_corrida.py`, configuración de PostgreSQL o de autovacuum, esquema y OpenAPI.
- **Gate:** seguridad ✔ (lectura administrativa, ninguna conexión a las protegidas) · fail-closed ✔ · sin esperas de
  estabilización ✔.

## 7. Tareas
| Tarea | EXECUTOR | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| H01 reconciliación, invariante, sondas, contrato y briefs | CLAUDE | n-a | delta, evidencia | gate |
| H02a huella | DEEPSEEK | deepseek-v4-pro | `qa/e2e_base.py` | AUDIT_PASS, ruff, mypy |
| H02b pruebas | DEEPSEEK | deepseek-v4-pro | `resources/backend/tests/test_e2e_base_ciclo.py` | verdes; rojo contra HEAD por mantenimiento |
| H03 mutaciones, certificación y cierre de B1 | CLAUDE | n-a | evidencia, roadmap | gate de cierre |

## 8. Material gate

| Indicador | Valor |
|---|---|
| CURRENT_FALSE_POSITIVE_REPRODUCED | 1 |
| PROTECTED_DB_CONTRACT_CONFIRMED | 1 |
| METRIC_SEMANTICS_CONFIRMED | 1 |
| SESSIONS_ONLY_SUFFICIENT | **0**, resuelto con la segunda señal `state_change` |
| NEW_FINGERPRINT_DETECTS_CONNECTION / WRITE | 1 / 1 (diseño medido; las pruebas lo confirman) |
| NEW_FINGERPRINT_IGNORES_ALLOWED_MAINTENANCE | 1 |
| BASELINE_PRECONDITION_PROVEN | 1 |
| OBSERVER_POLICY_PROVEN | 1 |
| OWNER_DECISION_REQUIRED | 0 |
| MATERIAL_OQ | 0 |
| UNKNOWN | 0 |

**Resultado: implementación autorizada.**

## 9. Implementación
- **H02a:** `huella` devuelve `{oid, sesiones, clientes}`, con la guarda que falla cerrada si se mide la base del
  observador.
- **H02b:** la prueba 23 se adapta y se añaden las 24–31.
- DeepSeek escribió las dos: 2 llamadas, $0,005592, 0 reintentos. Se aplicaron tal cual.

## 10. Pruebas y mutaciones — `directed-tests.md`, `mutations.json`
- Huella: 11/0/0 en orden normal y 11/0/0 en orden inverso.
- Contra HEAD fallan 7. La 24 falla por mantenimiento interno contado como escritura.
- Mutaciones: 11/11 KILLED; M12 no aplica.

## 11. Certificación — `certification.md`
- SQLite: 1885/0/1056 ×2.
- **PostgreSQL: 2915/0/26.**
- E2E: 284/0/0, con la huella sin cambios.
- OpenAPI: 544/533/11.

## 12. Convergencia — `convergence.md`
**CLOSED / CONVERGED.** Con PostgreSQL en verde, DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN (Spec 046) también
cierra; ver su delta §11.
