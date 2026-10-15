# Pruebas dirigidas
## O06-01…20 (`tests/test_almacen_de_pruebas.py`; sondas en procesos `pytest` hijos, en serie y a la vez; 20/20 en ≈ 33 s)
| Id | Qué fija | Resultado |
|---|---|---|
| O06-01 | dos procesos a la vez: almacenes distintos, raíz propia `<tmp>/kontrol-test-almacen-*/storage`, ninguna fija, no heredada, vacíos al empezar | PASS |
| O06-02 | ídem respaldos | PASS |
| O06-03 | B no ve el marcador documental sintético de A (ruta inexistente, listado vacío) | PASS |
| O06-04 | B no ve el marcador de respaldo de A | PASS |
| O06-05 | en A: `Settings`, `create_app` + `TestClient` (salud 200), proveedor documental y exportaciones bajo la misma raíz | PASS |
| O06-06 | en A: respaldos = `Settings.backup_path` = `<raíz>/backups` | PASS |
| O06-07 | B igual de consistente y distinto de A | PASS |
| O06-08 | en proceso: entorno = stash = `Settings` = carpeta de exportaciones; raíz con el prefijo y existente | PASS |
| O06-09 | al terminar A, marcador, almacén y raíz desaparecen | PASS |
| O06-10 | al terminar A, respaldos desaparecen | PASS |
| O06-11 | una raíz ajena con el mismo prefijo sobrevive a la limpieza de B | PASS |
| O06-12 | con fallo deliberado, la raíz desaparece igual | PASS |
| O06-13 | la ruta fija antigua no se reutiliza: ni en el entorno, ni por `setdefault` en `conftest`/`test_migrations_offline`, ni aunque viaje en el entorno del hijo | PASS |
| O06-14 | `config.py` conserva `/data/storage` y `/data/backups`; los consumidores leen `get_settings().storage_path` | PASS |
| O06-15 | pruebas documentales: `set_storage(FilesystemStorageProvider(_ROOT))` y `set_storage(None)` intactos | PASS |
| O06-16 | pruebas de exportación: aserciones `file_ref` intactas; sin rutas fijas | PASS |
| O06-17 | analizador: falso seguro y techo 120 s intactos; el conftest no toca sus variables | PASS |
| O06-18 | OBS-12 distingue raíz huérfana por proceso (residuo) de almacén legado (informativo) | PASS |
| O06-19 | el bloque de aislamiento no tiene sleep/retry/skip/xfail/timeout/glob; `rmtree` solo sobre las raíces exactas del stash; las sondas corren en serie y en orden | PASS |
| O06-20 | el bloque no importa producto ni usa `set_storage`/`/data/`; las sondas tampoco | PASS |
## Regresiones (con analizador real; `-o addopts= -p no:cacheprovider`)
| Conjunto | SQLite | PostgreSQL |
|---|---|---|
| O06 + O12 + documentos (4 módulos) + reporting + n9 + clamav_qa + volumen (2) + motor_para_hilos + UoM (2) + almacenes + auth (2) + licenciamiento (3) + migraciones offline + keepalive + ciclo de base E2E (+ `test_e2e_corrida`, `test_pg_sesion_aislada` en PG) | **281 passed · 0 failed · 44 skipped** (470 s) | **351 passed · 0 failed · 8 skipped** (872 s) |
Residuos `kontrol-test-almacen-*`/`sqlite-*`/`license-*` tras las dirigidas: **0**. `ruff check` limpio en todo lo tocado.
