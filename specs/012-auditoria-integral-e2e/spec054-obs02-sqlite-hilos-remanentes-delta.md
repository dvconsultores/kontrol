# SPEC 054 · Delta dirigida — OBS-02 · SQLITE-HILOS-REMANENTES

Dueña transversal: 054 (arnés). Dueñas funcionales por objetivo: 011 (UoM), 046 (gestión documental); `evidence/obs02-sqlite-hilos-remanentes/owner-matrix.md`.
Fecha: 2026-10-14. Rama `develop`, HEAD de partida `89d9dee`. Decisión de la dueña: `[X] OBS-02` (ratificada; un encargo
previo sin marca se devolvió sin tocar nada). Producto 0, migraciones 0, esquema 0, `motor_para_hilos` sin cambio.

## 1. Checkpoint — `checkpoint.md`

`89d9dee` = origin, `develop`, limpio, 0/0/0, puertos libres; MASTER57 57; SPEC057 PLANNED / NOT STARTED; NEXT MASTER
SPEC NOT YET PRIORITIZED; producción fuera de alcance.

## 2. `/speckit.specify` — FR-O2-001…031

Recogidos del encargo. Los de descubrimiento (001–005) se cumplen en §3; los de corrección (006, 007, 024, 025) en §7; los
de no-cambio (008–023, 026–031) se verifican en §8–§9.

## 3. `/speckit.clarify` — descubrimiento

| Paso | Resultado | Evidencia |
|---|---|---|
| Inventario completo de pruebas con hilos | 26 ficheros; **KNOWN_OBS02_TARGET 1** (`test_uom_conversion.py::test_concurrencia_una_sola_version_abierta`); ENVIRONMENT_BLOCKED 1 familia (6 carreras de `test_documents_security.py`); THREADED_BUT_ALREADY_ISOLATED 4; POSTGRES_ONLY 19 (`skipif`/`pytestmark`/`mundo` de `conftest_multicompany`); NOT_RELEVANT 1; **UNKNOWN 0** | `threaded-test-inventory.md` |
| Dueñas | UoM → 011 (docstring, carpeta, AC-011-12 «dos peticiones simultáneas producen una sola versión abierta», FR-011-035); documentos → 046 (docstring T-046-106); arnés → 054 | `owner-matrix.md` |
| Objetivo UoM | 2 hilos con barrera de arranque sobre `TestClient` compartido y `make_engine()` (`:memory:` + `StaticPool`); aserción única `len(abiertas) == 1`; sin aserción sobre `results`; servicio: SELECT abierta → UPDATE `valid_to` → SELECT todas (solapamiento) → INSERT → commit; `IntegrityError` del índice parcial `uq_ppv_open_version` (con `sqlite_where`) → 409 | `uom-target.md` |
| Documentos | las seis carreras se fuerzan con `pg_backend_pid`/`pg_stat_activity` (PostgreSQL por construcción) y hoy fallan en `_upload` con 422 `SCAN_FAILED` antes de la carrera (`clamscan` ausente) | `documents-security-target.md` |
| Frecuencia UoM (A ×20, A' ×10 sonda, B ×10, C ×10 PG) | **todo PASS**, pero 5/30 corridas SQLite pasan con un hilo muerto (`InvalidRequestError: Could not refresh instance`) y sin versión creada: falso verde; sonda: **1 conexión DBAPI 10/10** | `frequency-study.md`, `frequency-series-before.txt`, `connection-topology.md`, `topology-traces.txt` |
| Firmas | F1 hilo muerto con PASS · F2 `DatabaseError` · F3 `cannot commit transaction` · F4 `[200, 200]` legítimo (serializadas) · F5 `[200, 409]` · F6 `database is locked` (nueva, ciclo de vida de otra prueba) · F7 resultado faltante aceptado; UNKNOWN 0 | `failure-signatures.md` |
| Entrelazado I1 y control `motor_para_hilos` | (a) actual: 7/35 defectos (4 falsos verdes con 0 versiones nuevas); (b) conexiones propias, mismo datastore: 0/35 excepciones, I1 5/5 `[200, 409]` | `controlled-interleavings.md`, `motor-para-hilos-controls.md`, `poc-output.txt` |

`MATERIAL OQ = 0`: no hay decisión de producto ni de contrato (PostgreSQL 10/10; con conexiones propias SQLite cumple el
contrato exacto).

## 4. `/speckit.plan`, 5. CONSTITUTION GATE (etapa 1), 6. `/speckit.checklist` y `/speckit.tasks`

Plan W01–W31 del encargo. Gate etapa 1: G01–G40 cumplidos (inventario completo, dueñas probadas, invariantes y
dependencia de ClamAV mapeadas, instrumentación y series acotadas definidas, producto prohibido, prohibiciones
registradas, mutaciones y certificación planificadas, BLOCKER 0, MATERIAL OQ 0, UNKNOWN 0, trazabilidad 100 %) → **PASS
para el diagnóstico**; diagnóstico ejecutado (§3).

| Tarea | Ficheros | EXECUTOR / MODEL | SECURITY_SENSITIVE / EGRESS_SAFE | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| T01 inventario | evidencia | CLAUDE / n-a | no / n-a | O2-01 | `threaded-test-inventory.md`, UNKNOWN 0 |
| T02 dueñas e invariantes | evidencia | CLAUDE / n-a | no / n-a | — | `owner-matrix.md`, `uom-target.md`, `documents-security-target.md` |
| T03 diagnóstico UoM | guiones fuera del repo | CLAUDE / n-a | no / n-a | series, sonda, POC | §3 |
| T04 diagnóstico documentos | evidencia | CLAUDE / n-a | no / n-a | — | ENVIRONMENT_BLOCKED |
| T05 clasificación | evidencia | CLAUDE / n-a | — | — | `root-cause-matrix.md`, UNKNOWN 0 |
| T06 arnés | `tests/test_uom_conversion.py` (fixture, recogida de resultados, ciclo de vida de una prueba) | CLAUDE / n-a | no / n-a | objetivo ×20, módulo ×10 | FR-O2-006/007/024/025 |
| T07 pruebas dirigidas | `tests/test_uom_concurrencia_hilos.py` (nuevo) | CLAUDE / n-a | no / n-a | O2-02/04/11 ×2 motores | verdes |
| T08 mutaciones | copias temporales | CLAUDE / n-a | — | M-01…M-12 | `mutation-campaign.md` |
| T09 certificación y convergencia | docs, roadmap, puntero | CLAUDE / n-a | — | suites, OpenAPI, E2E | §9 |

`DEEPSEEK CALLS = 0` (concurrencia y arnés: CLAUDE_ONLY).

## 7. Compuerta material de causa raíz y autorización etapa 2

| TARGET | REPRODUCED | ROOT_CAUSE | PRODUCT_CHANGE_REQUIRED | OWNER_DECISION_REQUIRED | IMPLEMENTATION_ALLOWED |
|---|---|---|---|---|---|
| UoM `test_concurrencia_una_sola_version_abierta` | YES (falso verde 5/30; POC 7/35) | HARNESS_SHARED_CONNECTION (+ vector incompleto aceptado) | NO | NO | **YES** (arnés) |
| UoM `test_el_historico_no_cambia_al_cambiar_el_factor` | YES al adoptar conexiones propias (`database is locked`) | HARNESS_STATE_LEAK (sesión de escritura abierta durante llamadas a la API) | NO | NO | **YES** (ciclo de vida, una línea) |
| 6 carreras de `test_documents_security.py` | NO (no se alcanza la carrera) | ENVIRONMENT_BLOCKED (+ PostgreSQL por construcción) | NO | NO | NO (sin cambio; `ENTORNO-SIN-CLAMSCAN` sigue OPEN; OBS-08) |

`BLOCKER = 0` · `MATERIAL OQ = 0` · `UNKNOWN = 0` · trazabilidad 100 % → etapa 2 consumida para los dos objetivos UoM.

## 8. `/speckit.implement` — `implementation-decision.md`

- `tests/test_uom_conversion.py`: fixture sobre `motor_para_hilos("uom-conversion")`; la prueba objetivo recoge las
  excepciones de hilo y exige el vector completo (`errores == []`; `len(results) == 2`, `⊆ {200, 409}`, `200 in results`)
  **antes** de su aserción funcional intacta; `test_el_historico…` resuelve la empresa antes de abrir su sesión de escritura.
- `tests/test_uom_concurrencia_hilos.py`: O2-02 (I1 forzada: `[200, 409]`, `PRESENTATION_VERSION_OVERLAP`, 1/2 versiones,
  2 conexiones DBAPI, 0 excepciones; en PostgreSQL con barrera solo de lectura), O2-11, O2-04 (contrato estático).
- Sin cambio: producto, `motor_para_hilos`, `test_documents_security.py`, migraciones, esquema.

## 9. Resultados, `/speckit.analyze` final y veredicto

| Gate | Resultado | Evidencia |
|---|---|---|
| Dirigidas | objetivo sola ×20 SQLite 20/20 sin avisos (antes 5/30 con hilo muerto); módulo ×10 10/10; O2-02 I1 ×10 SQLite y ×5 PostgreSQL `[200, 409]`; objetivo ×10 PostgreSQL; ACS/almacenes/auth 59+1 skip y 79 passed | `directed-tests.md`, `directed-series-after.txt` |
| Mutaciones | 12/12 muertas (M-04/M-07/M-11 tras reforzar O2-04; documentado) | `mutation-campaign.md` |
| Suites | SQLite 1630/42/1040 ×2 (42 ClamAV, idénticas a la base) · PostgreSQL 2647/37/28 (base) · TARGET_REGRESSION 0 · UNKNOWN 0 | `sqlite-full-1.md`, `sqlite-full-2.md`, `postgres-full.md` |
| OpenAPI · E2E | 544/533/11 sin cambio · 280/0/4 limpia | `openapi.md`, `global-e2e.md` |
| Limpieza | 0 bases, 0 schemas, 0 dirs; puertos libres | — |

`final-analyze.md`: todo a 0, trazabilidad 100 %. **Veredicto: `OBS-02 — CLOSED / CONVERGED`** (`convergence.md`), con el
alcance declarado honestamente: UoM resuelto; documentos ENVIRONMENT_BLOCKED bajo `ENTORNO-SIN-CLAMSCAN` (OPEN) y
PostgreSQL por construcción (OBS-08 nueva). MASTER57 57; SPEC057 PLANNED / NOT STARTED; NEXT MASTER SPEC NOT YET PRIORITIZED.
