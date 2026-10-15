# Inventario de definiciones de `KONTROL_STORAGE_PATH` / `KONTROL_BACKUP_PATH`
| Símbolo | Fichero | Ámbito | Origen del valor | Cuándo se fija | Cuándo se lee | Interacción con la caché de settings | Dueño | Producto/arnés |
|---|---|---|---|---|---|---|---|---|
| `Settings.storage_path` / `backup_path` | `app/core/config.py:78-79` | producto | env (`pydantic-settings`), por defecto `/data/storage` / `/data/backups` | al construir `Settings()` | `get_settings()` con `@lru_cache` | la primera construcción fija el valor para todo el proceso salvo `cache_clear()` | 001 | producto |
| `os.environ.setdefault(...)` → `<tmp>/kontrol-test-storage`, `<tmp>/kontrol-test-backups` | `tests/conftest.py:32-33` | **todo proceso pytest** | constante por máquina | al **importar** el conftest (antes de la colección) | por `Settings` | seguido de `get_settings.cache_clear()` (línea 38) | 054 | arnés (**objeto de OBS-06**) |
| mismo `setdefault` | `tests/test_migrations_offline.py:35-36` | módulo | constante | al importar el módulo (en la colección; con el conftest ya cargado es no-op) | sus subprocesos usan `tmp/st`, `tmp/bk` propios | — | 054 | arnés (redundante) |
| `KONTROL_STORAGE_PATH: /data/storage` | `compose.yaml:43-44` | despliegue | fijo | arranque del contenedor | producto | — | ops | producto (fuera de alcance) |
| `estado/storage`, `estado/backups` | `qa/e2e_corrida.py:211-212`, `tests/test_e2e_base_ciclo.py:99`, `tests/test_backend_keepalive.py:94`, `tests/test_migrations_offline.py:48-49` | subprocesos de una corrida/prueba | **ruta propia por corrida** | antes de lanzar el proceso hijo | hijo | — | 054 | arnés, ya aislado |
| `<tmp>/kontrol-qa-storage`, `kontrol-qa-backups` | `qa/functional-e2e-inprocess.py`, `qa/local-backend-bootstrap.py`, `qa/n6-multicompany-bootstrap.py` | QA manual | constante distinta de la de pytest | al importar | producto | `cache_clear()` | 054 | QA manual (no comparte nombre con pytest) |
| `<tmp>/kontrol-kaud-*`, `/tmp/k-st`, `k-sto`… | `qa/repro-*.py`, `qa/pg-e2e-seed.py`, `qa/pg-migration-validation.sh` | reproducciones | constantes propias | al importar | producto | — | 054 | QA manual |
Conclusión: la única definición compartida entre procesos **de pytest** es la del `conftest.py` (y su eco en
`test_migrations_offline.py`). El resto de rutas fijas pertenecen a herramientas de QA manual con nombres distintos.
