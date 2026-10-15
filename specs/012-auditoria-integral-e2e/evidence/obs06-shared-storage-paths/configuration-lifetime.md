# Ciclo de vida de la configuración
| Registro | Valor |
|---|---|
| `ENV_SET_SITE` | import de `tests/conftest.py` (`setdefault`, líneas 19-33); el volumen de instalación, en cambio, se fija en `pytest_configure` (líneas 65-70) |
| `SETTINGS_CONSTRUCTION` | primera llamada a `get_settings()`; en un proceso de pruebas ocurre al importar `app.main` (`configure_logging()`) durante la **colección** del primer módulo que lo importa, es decir **después** de `pytest_configure` |
| `SETTINGS_CACHE` | `@lru_cache`; `cache_clear()` al importar el conftest y en `_fijar_volumen()` |
| `IMPORT_TIME_CAPTURE` | `app/modules/documents/storage.py:get_storage()` guarda el proveedor en el global `_provider` **en el primer uso** (no al importar) con `Path(get_settings().storage_path) / "documents"`; `app/modules/reporting/service.py:_exports_dir()` lee `get_settings()` en cada llamada |
| `TESTCLIENT_CAPTURE` | `TestClient(create_app())` no captura rutas: las lee el producto por `get_settings()` en cada petición (reporting) o en el primer uso (documentos) |
| `WORKER_INHERITANCE` | los subprocesos de pruebas heredan `os.environ` (sondas, keepalive, migraciones, E2E); los que fijan su propia ruta la sobrescriben; una raíz fijada en `pytest_configure` **no** debe heredarse: el hijo crea la suya (como el volumen: «nunca la heredada del entorno») |
| `RECONFIGURATION_SUPPORTED` | sí, con `cache_clear()`; pero el global `_provider` de documentos no se reconstruye solo (las pruebas documentales usan `set_storage(...)` explícito y `set_storage(None)` al terminar) |
Orden seguro probado por el precedente del volumen: `pytest_configure` (raíz propia + variable + `cache_clear`) → colección
(importa `app.main`, construye `Settings` con la raíz propia) → pruebas → `pytest_unconfigure` (rmtree + restaurar).
