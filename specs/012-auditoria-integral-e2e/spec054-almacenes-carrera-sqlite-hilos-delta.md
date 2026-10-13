# SPEC 054 · Delta dirigida — ALMACENES-CARRERA-SQLITE-HILOS (enlace cruzado)

La deuda `ALMACENES-CARRERA-SQLITE-HILOS` es de SPEC008 (la prueba `test_concurrencia_de_codigo_resuelta_por_constraint`
y el servicio de ubicaciones). La delta completa —reproducción, topología de conexiones, firmas, entrelazado controlado,
POC de mismo datastore, causa raíz y compuerta de clasificación, implementación, mutaciones, suites y convergencia— vive en
**`specs/008-almacenes-fisicos/spec008-almacenes-carrera-sqlite-hilos-delta.md`** con su evidencia en
`specs/008-almacenes-fisicos/evidence/almacenes-carrera-sqlite-hilos/`. Aquí solo se deja constancia de lo que cambia en
el arnés de backend, que es de esta Spec:

| | |
|---|---|
| Primitiva nueva en `tests/conftest.py` | `motor_para_hilos(nombre)`: gestor de contexto para módulos que lanzan hilos contra la app. En SQLite, fichero temporal (`kontrol-test-sqlite-<nombre>-…/base.db`) con el pool por defecto —una conexión DBAPI por hilo concurrente sobre el mismo datastore— y `check_same_thread=False`; sin `timeout`, `isolation_level` ni `PRAGMA`; al salir, `dispose()` y eliminación del directorio, pase o falle lo de dentro. En PostgreSQL devuelve `make_engine()` tal cual |
| Lo que no cambia | `make_engine()` (`:memory:` + `StaticPool` para las pruebas sin hilos), `sesion_de_prueba`, `_esquema_del_modulo`, el volumen de instalación por proceso y por módulo, PGLIFE |
| Pruebas del arnés | `tests/test_motor_para_hilos.py` (ACS-01…08: topología, mismo datastore, aislamiento, entrelazado controlado, bloqueo ≠ duplicado, limpieza, limpieza en fallo, contrato estático); corren en los dos motores, sin `skip` |
| Causa raíz, para la familia | `HARNESS_SHARED_CONNECTION`: `StaticPool` + `:memory:` + `check_same_thread=False` reparten la misma conexión pysqlite entre hilos. `AUTH-ROTACION-SQLITE-HILOS` (001/054) tiene la misma firma y presumiblemente la misma causa; no se absorbe (`OBSERVACIONES.md`, OBS-02) |
