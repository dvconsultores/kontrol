# Observaciones registradas, no absorbidas

| Id | Observación | Dueña |
|---|---|---|
| OBS-01 `WAREHOUSE-INTEGRITY-TRADUCE-TODO` | `_integrity()` de `warehouse_api.py` traduce cualquier `IntegrityError` (ya registrada en el ciclo anterior) | 008 |
| OBS-02 `HILOS-SOBRE-STATICPOOL` | `test_uom_conversion.py` y `test_documents_security.py` siguen lanzando hilos contra la app sobre la conexión compartida de `make_engine()` en SQLite; `test_roles_create.py` y `test_picklist_duplicada.py` la evitan con `skipif(not PG)` | 008 · 013 · 010 · 031 |
| OBS-03 `TESTCLIENT-RELANZA-EN-HILO` | confirmado aquí: todo 500 se relanza en el hilo y la prueba ve «faltan resultados» | 054 |
| OBS-04 `SPEC-SEGURIDAD-SIN-CARPETA` | la Spec 002 «Seguridad / sesiones» del inventario no tiene carpeta `specs/002-<seguridad>`; `specs/002-maestros` es otra Spec; las deltas de auth se alojan en `specs/001-fundacion` | dueña del inventario |
| OBS-05 `COMENTARIO-WITH-FOR-UPDATE-SQLITE` | el comentario de `rotate_session` y el cierre de REM-AUTH afirman que SQLite «serializa las escrituras por su cuenta» y hace inocuo el bloqueo; demostrado falso para la carrera leer-luego-escribir (capa 2). Corregir el texto es parte de la decisión de la dueña | 002 |
| OBS-06 `KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH` compartidos | `tests/conftest.py` los fija a rutas constantes bajo el tmp del sistema (`kontrol-test-storage`, `kontrol-test-backups`), compartidas entre procesos; no intervienen en este ciclo | 054 |
| OBS-07 `csync_02` depende de `csync_01` | registrada por el encargo; no medida aquí | 010/054 |
