# Gate material y decisión de implementación
`ROOT_CAUSE` ∈ {SHARED_PATH_LEAK, STALE_STATE_ACROSS_RUNS, CROSS_PROCESS_COLLISION, HARNESS_CLEANUP_DEFECT} ·
`PRODUCT_CHANGE_REQUIRED` NO · `MIGRATION_REQUIRED` NO · `SCHEMA_CHANGE_REQUIRED` NO · `TEST_SEMANTICS_CHANGE_REQUIRED` NO ·
`OWNER_DECISION_REQUIRED` NO · BLOCKER 0 · CRITICAL 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % →
**AUTORIZACIÓN EXPRESA — ETAPA 2 consumida** (solo arnés).
Diseño (CLAUDE_ONLY, DeepSeek 0): en `tests/conftest.py`, el mismo patrón del volumen de instalación ampliado al almacén:
`pytest_configure` crea `mkdtemp(prefix="kontrol-test-almacen-")` con `storage/` y `backups/`, guarda las variables
heredadas en el stash, fija `KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH` y limpia la caché de `Settings`;
`pytest_unconfigure` elimina **esa** raíz exacta y restaura las variables. Desaparecen los `setdefault` de importación (y
su eco en `test_migrations_offline.py`). Identidad del proceso: nombre aleatorio de `mkdtemp` (como el volumen; no el
PID: tras una muerte a la fuerza el PID se reutiliza y una raíz huérfana con PID se reusaría). Sin limpieza de arranque
de rutas históricas: `<tmp>/kontrol-test-storage` queda como **legado** (no se borra en este ciclo; su retirada es una
acción manual aparte). Sondas permanentes `tests/sondas_almacen/` + `tests/test_almacen_de_pruebas.py` (O06-01…20).
OBS-12: `qa/suite_tiempos.py` añade `kontrol-test-almacen-` a los efímeros, `modo_almacen = PROCESS_ISOLATED`,
`almacen_por_proceso` y `almacen_fijo_legado_presente` (nunca falla la corrida); O12-09/10 adaptadas.
