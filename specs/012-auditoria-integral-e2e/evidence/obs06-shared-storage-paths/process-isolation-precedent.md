# Precedente de aislamiento por proceso (TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO, mismo `conftest.py`)
| Registro | Valor |
|---|---|
| `CANONICAL_PROCESS_IDENTITY` | raíz `tempfile.mkdtemp(prefix="kontrol-test-license-")` creada en `pytest_configure` y guardada en `config.stash[RAIZ_DEL_VOLUMEN]`; nunca la heredada del entorno (un proceso hijo crea la suya aunque la variable viaje en su entorno) |
| `CANONICAL_SESSION_TEMP_FACTORY` | `mkdtemp` en el hook (no `tmp_path_factory`: los hooks de configuración corren antes de las fixtures y el nombre aleatorio evita reutilizar rutas tras una muerte a la fuerza) |
| `CLEANUP_PATTERN` | `pytest_unconfigure`: `shutil.rmtree(raiz)` **de la raíz exacta del stash** y restauración de la variable previa (`VOLUMEN_HEREDADO`); nunca un glob |
| `STATIC_CONTRACT_PATTERN` | `tests/test_volumen_de_instalacion.py` (TV-01…12: procesos hijos en serie y a la vez sobre `tests/sondas_volumen/`, informes JSON saneados con huellas) + `test_volumen_de_instalacion_ambito.py` (en proceso) |
| `motor_para_hilos` | mismo patrón a escala de fixture: `mkdtemp` + `dispose()` + `rmtree` en `finally` |
Reutilizable para OBS-06 **sin copiarlo mecánicamente**: una sola raíz por proceso que contenga `storage/` y `backups/`
(el almacén debe ser único por proceso y estable durante toda la sesión, no por módulo como el volumen, porque
`documents/storage.py` fija su proveedor en el primer uso y `reporting` descarga por `file_ref` dentro de la sesión).
