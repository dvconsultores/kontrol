# SPEC 004 · Delta dirigida — OBS-07 · CSYNC-AISLAMIENTO (carpeta 010; apoyo 054)

Dueña: 004 (licenciamiento central; pruebas CSYNC de `spec004-central-sync-auth-delta.md`). Apoyo: 054 (arnés). Fecha:
2026-10-18. HEAD de partida `ddc46a8`. Autorización: encargo «NEXT TECHNICAL CYCLE» (selección por evidencia + ejecución).
Evidencia en `evidence/obs07-csync-aislamiento/`. OBS-09 congelada y no tocada.

## 1. Selección — `candidate-matrix.md`
## 2. PROBLEM
`tests/test_license_sync_client.py` solo pasa en su orden: una prueba aislada o el módulo reordenado dan falsos rojos.
## 3. ROOT_CAUSE (demostrada) — `diagnosis.md`
`_mundo` de módulo compartido y precondiciones implícitas: 10/13 fallan solas y 11/13 en orden inverso.
## 4. IN_SCOPE
Solo pruebas: cada prueba CSYNC parte de un mundo propio (bases de cliente y de autoridad nuevas) y establece de forma
explícita sus precondiciones (autoridad configurada, licencia importada) con ayudantes; regresión que ejecuta el módulo en
orden inverso y la prueba csync_02 sola en subprocesos.
## 5. OUT_OF_SCOPE
Producto (licenciamiento, autoridad central, sync, firmas, transporte), otras pruebas, `conftest.py`, OBS-09, otras deudas,
paralelismo, reordenación como remedio, sleeps, reintentos, skips.
## 6. INVARIANTS
Las aserciones de las 13 pruebas no se debilitan ni se eliminan; la autoridad sigue siendo la real en proceso; ninguna
clave real; el transporte real sigue siendo el de producto (`TransporteReal` por la ruta HTTP).
## 7. ACCEPTANCE_CRITERIA
Cada una de las 13 pruebas pasa sola; el módulo pasa en orden directo e inverso en SQLite y PostgreSQL; la regresión nueva
falla si se restaura el mundo de módulo; duración del módulo razonable (≤ 4 × la actual).
## 8. TEST_PLAN · MUTATION_PLAN · REGRESSION_PLAN
Dirigidas: 13 solas + directo + inverso (dos motores). Mutaciones ≥ 10 sobre el aislamiento (mundo de módulo, ayudante
de precondición omitido, aserción debilitada, regresión desactivada…). Regresión: licenciamiento completo y suites
completas (SQLite ×2, PostgreSQL, E2E) por cambio de pruebas.
## 9. CONSTITUTION GATE · checklist · tasks · analyze
Producto 0 · migraciones 0 · esquema 0 · OBS-09 0 · BLOCKER/CRITICAL/CONTRADICTIONS/MATERIAL OQ/UNKNOWN 0. Tareas: T1 (brief +
DeepSeek: reescritura del aislamiento + regresión), T2 (mutaciones), T3 (certificación). Ejecutor: DeepSeek escribe todo el
código de pruebas; Claude diseña, audita, aplica y certifica.
## 10. Diagnóstico y gate material
ROOT_CAUSE_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 · SCOPE_BOUNDED 1 · OBS09_OVERLAP 0 · decisiones de arquitectura, seguridad o
dueña 0 · MATERIAL_OQ 0 · UNKNOWN 0 → implementación autorizada por el encargo.
## 11. Implementación (DeepSeek escribe, Claude audita) — `orchestration.md`
`_aplicaciones` (módulo: claves, ancla, apps de cliente y autoridad con overrides que leen las factorías vigentes, transporte
parcheado) + `_mundo` (prueba: bases nuevas de cliente y autoridad, instalación registrada, motores liberados al final);
ayudantes `_configura_autoridad`, `_importa_licencia`, `_sincronizacion_previa` como primera sentencia de cada prueba que
los necesita; regresión `test_license_sync_client_aislamiento.py` (csync_02 sola, módulo en orden inverso con orden verificado,
contrato estático por AST). Ninguna aserción eliminada ni debilitada.
## 12. Pruebas, mutaciones, certificación — `directed-tests.md`, `mutation-campaign.md`, `certification.md`
## 13. Convergencia — `convergence.md`: **CLOSED / CONVERGED 2026-10-18**.
