# Implementación (solo arnés y QA; Claude, CLAUDE_ONLY; DeepSeek 0)
| Fichero | Cambio |
|---|---|
| `resources/backend/tests/conftest.py` | desaparecen los `setdefault` de importación de `KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH`; bloque «Almacén y respaldos aislados» con `VARIABLE_DEL_ALMACEN`, `VARIABLE_DE_RESPALDOS`, `PREFIJO_DEL_ALMACEN = "kontrol-test-almacen-"`, `RAIZ_DEL_ALMACEN`/`ALMACEN_HEREDADO` (stash), `_fijar_almacen()` (fija o quita las dos variables + `cache_clear`); `pytest_configure` crea `mkdtemp(prefix)` con `storage/` y `backups/` y fija las variables (nunca la heredada); `pytest_unconfigure` elimina **esa** raíz y restaura las variables heredadas (el volumen de instalación sigue igual, en el mismo hook) |
| `resources/backend/tests/test_migrations_offline.py` | se retira el eco del `setdefault` a la ruta fija (no-op bajo pytest; sus subprocesos ya usaban `tmp/st`, `tmp/bk`) y la importación de `tempfile` que quedaba sin uso |
| `resources/backend/tests/sondas_almacen/` (nuevo) | `README.md`, `informar.py` (cuenta entorno, `Settings`, raíz del proveedor documental, carpeta de exportaciones y marcadores sintéticos), `sonda_a.py`, `sonda_b.py`, `sonda_export.py` (fórmula real de nombre con marca inyectada), `sonda_app.py` (`create_app` + `TestClient`), `sonda_falla.py`; no se llaman `test_*` y no los recoge `pytest tests` |
| `resources/backend/tests/test_almacen_de_pruebas.py` (nuevo) | O06-01…20 (`directed-tests.md`) |
| `qa/suite_tiempos.py` | `PREFIJOS_EFIMEROS` incluye `kontrol-test-almacen-`; `ALMACEN_FIJO_LEGADO`, `MODO_DE_ALMACEN = "PROCESS_ISOLATED"`; `residuos()` devuelve `modo_almacen`, `efimeros`, `almacen_por_proceso`, `almacen_fijo_legado_presente` (nunca cambia el veredicto) |
| `resources/backend/tests/test_suite_tiempos_qa.py` | O12-09/10 adaptadas al contrato nuevo |
Producto 0 (`app/` intacto; `config.py` conserva `/data/storage`, `/data/backups`) · migraciones 0 · esquema 0 · timeouts 0 ·
sleep/retry/skip/xfail 0 · reorden 0 · paralelismo 0 · analizador intacto · aserciones documentales y de exportación intactas ·
el almacén fijo histórico `<tmp>/kontrol-test-storage` **no se borra** (legado; retirada manual aparte si la dueña lo decide).
`ruff check` y `mypy qa/suite_tiempos.py` limpios.
