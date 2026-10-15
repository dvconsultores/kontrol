# Matriz de consumidores
| Consumidor | Dominio | Lee/escribe | Almacén/respaldo | Origen de la ruta | Estrategia de nombres | Vida esperada | Limpieza | Pruebas funcionales |
|---|---|---|---|---|---|---|---|---|
| `documents/storage.py` `FilesystemStorageProvider` por defecto | 046 | escribe/lee | almacén `/documents/AAAA/MM/DD/<clave opaca de 32 caracteres>` | `get_settings().storage_path` en el primer uso | token aleatorio opaco (globalmente único) | la del documento | ninguna (producto: persistente) | `test_documents*.py` (con raíz propia por `set_storage`), `test_n9_integrity.py` (**proveedor por defecto → ruta fija**) |
| `reporting/service.py` `_exports_dir()` + `export_report` | 009 | escribe/lee | almacén `/exports/report-<clave>-<AAAAMMDDhhmmss>.<csv|pdf>` | `get_settings()` en cada llamada | **marca de tiempo con resolución de 1 s** | la de la exportación | ninguna | `test_reporting.py` (crea CSV y PDF y descarga por `file_ref`) |
| `backup_path` | — | **ningún consumidor en `app/`** (solo `config.py`; `homologation` cita un gate «backup» sin ruta) | respaldo | — | — | — | — | ninguna |
| `qa/e2e_corrida.py` | 054 | fija rutas propias por corrida para el backend hijo | ambos | `estado/<run>` | — | la corrida | `finally` de la corrida | E2E |
| `qa/functional-e2e-inprocess.py` y bootstraps | 054 QA manual | rutas `kontrol-qa-*` propias | ambos | constante distinta | — | manual | manual | — |
| `tests/sondas_volumen`, `test_backend_keepalive`, `test_migrations_offline`, `test_e2e_base_ciclo` | 054 | rutas propias para sus subprocesos | ambos | `tmp_path`/`estado` | — | la prueba | pytest | — |
