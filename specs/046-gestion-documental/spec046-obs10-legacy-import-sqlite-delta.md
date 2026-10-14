# SPEC 046 · Delta dirigida — OBS-10 · DOCUMENTS-LEGACY-IMPORT-SQLITE

Dueña: 046 (FR-046-112/113, T-046-143/148). Apoyo: 054 (arnés; enlace cruzado en
`specs/012-auditoria-integral-e2e/spec054-obs10-legacy-import-sqlite-delta.md`). Fecha: 2026-10-14. HEAD de partida
`714b695`. Decisión `[X] OBS-10` ratificada. Evidencia en `evidence/obs10-legacy-import-sqlite/`. Producto 0, migraciones 0,
esquema 0, analizador canónico intacto, OBS-11 fuera.

## 1. Checkpoint — `checkpoint.md`
## 2. `/speckit.specify` — FR-O10-001…032 (del encargo; los de descubrimiento en §3, los de corrección en §6, los de no-cambio en §8)
## 3. `/speckit.clarify` — descubrimiento
| Paso | Resultado | Evidencia |
|---|---|---|
| Inventario | 7 nodos exactos (de 8), todos con la misma estructura de ayudantes; PostgreSQL 8/8 | `seven-node-inventory.md` |
| Contrato | FR-046-112/113; ningún test exige estado sin confirmar visible entre conexiones; los HTTP son ayudantes de identificadores; SQLite y PostgreSQL en alcance | `functional-contract.md` |
| Fixture y ciclo de vida | `make_engine()` compartido; S-prueba, S-API y S-actor sobre C1; HTTP y sesión auxiliar con escrituras pendientes | `fixture-chain.md`, `session-lifecycle.md`, `topology-trace.txt` |
| Reproducción acotada | módulo ×3 SQLite: 7 failed deterministas (`StaleDataError`); PostgreSQL ×2: 8 passed | `failure-taxonomy.md` |
| Controles | A: 1 conexión; **B** (`motor_para_hilos`, ciclo intacto): 7× `database is locked`; **C** (+ ayudantes antes de la sesión): 8/8 ×3 SQLite y 8/8 PostgreSQL | `controls.md`, `controls-b-c-output.txt` |
| Causa raíz | **HARNESS_SHARED_CONNECTION_PLUS_LIFECYCLE** para las siete; `CLASSIFICATION = FROZEN`; MATERIAL OQ 0 | `root-cause-matrix.md` |
## 4. `/speckit.plan`, CONSTITUTION GATE y `/speckit.tasks`
W01–W32; gate G01–G41 cumplidos para el diagnóstico (sin producto, migración, esquema, skip, retry, sleep, cerrojos,
busy_timeout, PG-only); tareas T01–T09 CLAUDE_ONLY; `DEEPSEEK CALLS = 0`.
## 5. Compuerta material
`SEVEN_TARGETS_CLASSIFIED = YES` · `PRODUCT_CHANGE_REQUIRED = NO` · `OWNER_DECISION_REQUIRED = NO` ·
`FUNCTIONAL_ASSERTIONS_CHANGED = NO` · `REAL_SCANNER_PRESERVED = YES` · BLOCKER 0 · MATERIAL OQ 0 · UNKNOWN 0 → etapa 2.
## 6. `/speckit.implement` — `implementation.md`
## 7. Mutaciones — `mutation-campaign.md`: 12/12 aplicables muertas (M-05 y M-10 tras reforzar el contrato; M-08/M-09 no aplican)
## 8. Certificación — `directed-tests.md`, `full-suites.md`, `global-e2e.md`
Dirigidas 34/34 (siete ×3 solas, módulo ×10, PostgreSQL ×3) + regresiones 101/1 + documentos PostgreSQL 65/65; SQLite completa
1692/1/1046 ×2; PostgreSQL 2712/1/26; E2E `--con-analizador` 284/0/0; OpenAPI 544/533/11; el único rojo restante es OBS-11.
## 9. `/speckit.analyze` final y veredicto — `final-analyze.md`, `traceability-matrix.md`, `convergence.md`
**OBS-10 → CLOSED / CONVERGED.** OBS-11 sigue independiente (OBS-12 nueva: duración anómala de una suite). MASTER57 57;
SPEC057 PLANNED / NOT STARTED; NEXT MASTER SPEC NOT YET PRIORITIZED.
