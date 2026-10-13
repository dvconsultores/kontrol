# Inventario del arnés · `tests/conftest.py` y conftests anidados (HEAD 1f28c83)

Conftests: `tests/conftest.py` (raíz) y `tests/central/conftest.py` (Autoridad Central: base propia, clave de firma
sintética por módulo; no toca el volumen de instalación).

| Registro | Valor |
|---|---|
| `CURRENT_VOLUME_FIXTURE` | **no hay fixture**: `tests/conftest.py:25-26` ejecuta a nivel de módulo `os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(tempfile.gettempdir(), "kontrol-test-license"))` |
| `SCOPE` | proceso entero (efecto de importación), y de hecho **toda la máquina**: la ruta es fija |
| `AUTOUSE` | n/a (no es fixture) |
| `PATH_SOURCE` | `tempfile.gettempdir()` + nombre fijo `kontrol-test-license`; `setdefault` respeta un valor externo |
| `CREATED_BY` | el producto, en el primer `get_or_create_installation` (`os.makedirs(..., exist_ok=True)`) |
| `CLEANED_BY` | **nadie** (medición 01: el fichero sobrevive entre sesiones y días) |
| `CACHE_CLEAR_BEFORE` | `tests/conftest.py:33` `get_settings.cache_clear()` tras fijar el entorno (import) |
| `CACHE_CLEAR_AFTER` | ninguno a nivel de arnés; cada mundo que cambia otras variables (`ANCLA`, `TRUST_KEYS`) llama `cache_clear()` al entrar y al salir |
| Fixtures autouse del arnés | `_recursos_pg_del_modulo` (module) y `_recursos_pg_de_la_prueba` (function): ciclo de vida PostgreSQL (PGLIFE), ajenas al volumen |
| Hooks del arnés | `pytest_sessionfinish` (red de seguridad PG), `pytest_terminal_summary` |
| Orden de autouse (medido con `--setup-show`) | `SETUP M _recursos_pg_del_modulo` (conftest) **antes** de `SETUP M _app_client` (mundo del módulo): una fixture autouse de módulo del conftest se monta antes que el mundo de cada módulo y se desmonta después |
| Doble importación | `conftest` (registrado por pytest; `tests/` sin `__init__.py`) y `tests.conftest` (importado por 25 pruebas) conviven en `sys.modules` como **dos módulos**; el código a nivel de módulo se ejecuta dos veces. Un `mkdtemp` a nivel de módulo crearía dos raíces: la raíz debe nacer en un hook (`pytest_configure`), que solo corre en el plugin registrado |
| Otros volúmenes fijados igual | `KONTROL_STORAGE_PATH` → `<tmp>/kontrol-test-storage`, `KONTROL_BACKUP_PATH` → `<tmp>/kontrol-test-backups` (fuera de alcance; anotados) |
| `tests/test_migrations_offline.py:35` | repite el mismo `setdefault` del volumen compartido a nivel de módulo (inerte bajo pytest si el conftest ya fijó la variable; su subproceso usa `tmp/"lic"` propio) |

Mundos que escriben la clave (34 + 4): fixture `autouse` de **módulo** (`_app_client` / `_mundo`) que llama a
`initialize(db, SetupRequest(...))` → `get_or_create_installation` → escribe `installation_private_key.pem` en el
volumen configurado; `test_licensing_central` y `test_services` lo hacen por **prueba**; `test_license_import_race`
y `test_license_revision_race` por fixture de función. Lectores de la clave: `sync_license` (producto, vía
`_installation_private_key`), y las pruebas `test_trust_*`, `test_rolla_17`, `test_csync_03/12`, que leen la ruta
derivada de `get_settings().installation_volume_path`: **todas en el mismo ámbito que la escribió**.
