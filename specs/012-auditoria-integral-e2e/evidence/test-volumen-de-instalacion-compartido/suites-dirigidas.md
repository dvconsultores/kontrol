# Suites dirigidas tras T01–T03 (volumen aislado) · `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`

## SQLite (W24) — 16 módulos: todos los que escriben y/o leen la clave, los que parchean su propio volumen y las migraciones

```
pytest tests/test_license_sync_client.py tests/test_license_trust_anchor.py tests/test_license_period_rollback.py
       tests/test_licensing_central.py tests/test_installation_key_reference.py tests/test_spec004_installation_race.py
       tests/test_system_version.py tests/test_license_state_reverification.py tests/test_license_key_rotation.py
       tests/test_license_revision_client.py tests/test_license_access.py tests/test_license_import_access.py
       tests/test_license_sync_rate_limit_client.py tests/test_licensing_offline_sqlite.py tests/test_migrations_offline.py
       tests/test_services.py tests/central/test_central_authority.py -q
.................................................................s...... [ 25%]
..........ssssss........................................................ [ 50%]
........................................................................ [ 76%]
...................................................................      [100%]
raíces kontrol-test-license-* antes: 0 · después: 0
```
283 ejecutadas: **0 fallos**, 7 omitidas (las de solo PostgreSQL de `test_installation_key_reference`
y `test_spec004_installation_race`, preexistentes).

Orden de fixtures medido (`--setup-show`, `tests/test_license_access.py`):
```
SETUP    M _recursos_pg_del_modulo
SETUP    M volumen_de_instalacion
SETUP    M _app_client
TEARDOWN M _app_client
TEARDOWN M volumen_de_instalacion
TEARDOWN M _recursos_pg_del_modulo
```

## TV (W24) — `tests/test_volumen_de_instalacion.py` (SQLite)

```
........                                                                 [100%]
raíces residuales: 0
```
8/8 (TV-01, 02, 03/08, 04, 09, 11, 12, 23).

## PostgreSQL (W25) — `KONTROL_TEST_DB_URL=postgresql+psycopg2://***@localhost:55432/ktest`, 21 módulos (los de SQLite + TV + carreras + PGLIFE)

```
pytest tests/test_volumen_de_instalacion.py <los 16 de arriba> tests/test_license_import_race.py
       tests/test_license_revision_race.py tests/test_pg_harness_lifecycle.py -q
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 65%]
..................................................s..................... [ 87%]
........................................                                 [100%]
raíces residuales: 0
```
328 ejecutadas: **0 fallos**, 1 omitida (preexistente). `TEST-PG-UN-SCHEMA-POR-PRUEBA` sin tocar: PGLIFE
(`test_pg_harness_lifecycle`) sigue verde con la fixture nueva montada entre `_recursos_pg_del_modulo` y el mundo.
