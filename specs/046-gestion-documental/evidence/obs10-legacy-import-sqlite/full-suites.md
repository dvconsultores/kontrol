# Suites completas con analizador real
| Corrida | Resultado | Clasificación |
|---|---|---|
| SQLite #1 | **1692 passed · 1 failed · 1046 skipped** (587 s) | OBS-10 fallos **0** (los 7 pasan); el único rojo es OBS-11 (`test_sync_success_records_run_snapshot_and_event`, KNOWN_INDEPENDENT_OBS11); +4 pasadas (contrato) |
| SQLite #2 | 1692 / 1 / 1046 (2946 s) | idéntica prueba por prueba. Duración ×5: carga de la máquina durante la corrida (observación; ninguna prueba cambió entre ambas; no se repite: sin razón de corrección) |
| PostgreSQL | **2712 passed · 1 failed · 26 skipped** (1869 s) | solo OBS-11; OBS-10 sin regresión (8/8); analizador 0 fallos |
Referencia previa: SQLite 1679/8/1046, PostgreSQL 2706/1/26. TARGET_REGRESSION 0 · UNKNOWN 0 · 0 schemas · 0 dirs temporales.
