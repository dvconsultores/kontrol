# Pruebas dirigidas tras el cambio (`-o addopts= -p no:cacheprovider`)
| Serie | SQLite | PostgreSQL |
|---|---|---|
| objetivo `test_sync_success_records_run_snapshot_and_event` ×20 | 20/20 | 20/20 |
| `tests/test_licensing_sync_time_anchor.py` (O11-01…06) ×5 | 5×6/6 | 5×6/6 |
| licenciamiento (11 módulos: central, time_anchor, sync_client, state_reverification, trust_anchor, import_access, import_race, period_rollback, revision_race, revision_client, key_rotation) | 153 passed, 9 skipped (36,5 s) | 162 passed (75,7 s) |
| regresiones de ciclos previos (motor_para_hilos, UoM ×2, auth ×2, documentos contratos ×2, legado, clamav_qa, almacenes) | 111 passed, 3 skipped (24,4 s) | 111 passed, 3 skipped (42,7 s) |
`ruff check` limpio en los dos ficheros. Fuente: `<scratch>/o11/dirigidas.txt`. Nota: `/tmp/kontrol-test-storage` es el
almacén fijo del arnés de documentos (existe desde el 2026-10-13), no un residuo de corrida; residuos `kontrol-test-sqlite-*`
y `kontrol-test-license-*`: 0.
