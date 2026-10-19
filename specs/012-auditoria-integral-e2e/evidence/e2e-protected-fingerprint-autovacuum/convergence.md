# Convergencia — E2E-HARNESS-PROTECTED-FINGERPRINT-COUNTS-AUTOVACUUM

| Requisito (encargo) | Evidencia | Estado |
|---|---|---|
| Invariante fijado desde las fuentes antes de elegir métrica (§6) | delta §2 (FR-054-E2EDB-005/009, DB-17/18) | ✔ |
| Falso positivo reproducido: H1A mantenimiento controlado y H1B autovacuum natural (§8) | `statistics-semantics.json` (H1A: ANALYZE manual +2 tup; H1B: +2 tup, +5 xact, 0 sesiones, 11,4 s) | ✔ |
| Semántica de cada contador medida (§9) | delta §3 | ✔ |
| Gate de `sessions` (§10): cuenta la conexión nueva, sin falso positivo por autovacuum | A1a, H1B | ✔ |
| `sessions` sola NO basta (sesión preexistente) → segunda señal (§11–12) | A5a; `activity-signal.json`; prueba 28 | ✔ |
| Observador modelado; nunca se conecta a la base medida; fail-closed | huella + prueba 30 + M04 | ✔ |
| Propagación determinista sin esperas (§13) | delta §4; pruebas 25/26; M12 no aplica | ✔ |
| Contrato emitido antes de implementar (§14) | delta §4 | ✔ |
| T1–T10 | pruebas 23–31 | ✔ |
| Rojo contra HEAD por la razón exacta (§21) | prueba 24 contra HEAD: `escrituras` 5038 → 5040, mismas sesiones | ✔ |
| Mutaciones ≥ 10, SURVIVED = 0 (§22) | 11/11 KILLED, RESTORED 11/11 | ✔ |
| Pruebas dirigidas, inverso (§23) | 11/0/0 ×2; ciclo 33/0/0; corrida 19/0/0 | ✔ |
| SQLite ×2 (§24) | 1885/0/1056 ×2 (reconciliado) | ✔ |
| **PostgreSQL completo en verde (§25)** | **2915/0/26**; `test_e2ecorrida_01` y `test_e2eciclo_23` PASS | ✔ |
| E2E (§26) | 284/0/0, huella PASS, 0 QueuePool, LIMPIA | ✔ |
| OpenAPI (§27) | 544/533/11 | ✔ |
| Rutas | solo `qa/e2e_base.py` (`huella` + import de `Any`) y la prueba; sin producto, configuración ni `e2e_corrida.py` | ✔ |

**Estado: CLOSED / CONVERGED.** BLOCKER = CRITICAL = CONTRADICTIONS = MATERIAL_OQ = UNKNOWN = 0 · TRACEABILITY 100 %.
