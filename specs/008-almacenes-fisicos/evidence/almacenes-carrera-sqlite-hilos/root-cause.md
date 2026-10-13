# Causa raíz y clasificación

## Clasificación: `HARNESS_SHARED_CONNECTION`

`make_engine()` sin `KONTROL_TEST_DB_URL` devuelve `create_engine("sqlite+pysqlite:///:memory:",
connect_args={"check_same_thread": False}, poolclass=StaticPool)`. `StaticPool` entrega **la misma conexión DBAPI** a
todos los `checkout`, y `check_same_thread=False` permite que cualquier hilo la use. El fixture de módulo de
`tests/test_warehouse_structure.py` monta la app sobre ese motor y un `TestClient`; la prueba objetivo lanza dos hilos
que hacen `POST /organization/locations` con el mismo código. Cada petición abre su `Session` (`_override_get_db`), pero
las dos sesiones se apoyan en el **mismo** `sqlite3.Connection` (sonda `connection-topology.md`: un solo id de conexión
C1 en todos los hilos T3–T6).

Mecanismo del fallo (firmas en `failure-signatures.md` y `same-datastore-poc-output.txt`):

1. T5 ejecuta `INSERT INTO warehouse_locations` y entra en `COMMIT` mientras T6 ejecuta su `INSERT` sobre la misma
   conexión → en T6 el cursor queda cerrado bajo sus pies (`ResourceClosedError`), o la violación única sube como
   `sqlite3.DatabaseError` (clase base: pysqlite ya no está en el estado en que clasifica el error como `IntegrityError`).
2. `create_location_full` solo captura `IntegrityError` → cualquier otra excepción es un 500 → `TestClient` (que no
   envuelve errores del servidor) la relanza en el hilo → el hilo muere sin `results.append` → `results == [200]`.
3. Variante menos frecuente: el `rollback` del perdedor, sobre la conexión compartida, deshace la fila ya insertada por
   el ganador: `[409]` y total 0 (1 de 30 en la POC natural; `InvalidRequestError: Could not refresh instance` en el
   ganador al refrescar una fila que ya no existe).

Cuando el planificador deja que T5 complete INSERT+COMMIT antes del INSERT de T6, la violación llega como
`IntegrityError` y la prueba pasa: por eso es intermitente (2/20 sola sin sonda, 4/20 con sonda, 4/10 en módulo) y por
eso el entrelazado controlado la vuelve determinista (5/5).

## Por qué no es otra cosa

- **No `HARNESS_STATE_LEAK`**: la prueba crea su propio almacén `CONC-1` y falla sola, en un proceso nuevo, en 2/20
  corridas; no depende de lo que corrió antes.
- **No `SQLITE_LOCKING_SEMANTICS`**: nunca aparece `database is locked` (ni en 40 corridas sondadas ni en 70 rondas de
  POC); con conexiones separadas sobre el mismo fichero el bloqueo se resuelve dentro del `busy_timeout` por defecto y
  no hace falta tocarlo. El error de bloqueo, si se diera, sería `OperationalError`, distinto de `IntegrityError`, y la
  traducción del servicio no lo confundiría con un duplicado (certificado en `tests/test_motor_para_hilos.py`).
- **No `PRODUCT_DEFECT`**: sobre PostgreSQL (una conexión por hilo) la prueba pasa 5/5 y la restricción
  `uq_warehouse_locations_wh_code` responde 409 exactamente a uno; con SQLite en fichero y una conexión por hilo, 35/35.
  El producto no ejecuta nunca dos peticiones sobre una conexión compartida. Observación registrada, no absorbida: la
  traducción `_integrity()` de `warehouse_api.py` convierte **cualquier** `IntegrityError` en 409 sin usar
  `es_violacion_unica` (dueña 008, `OBSERVACIONES.md`).
- **No `POSTGRESQL_ONLY_CONTRACT`**: P21 exige PostgreSQL para la evidencia de integración y acota las excepciones a
  pruebas que no ejerciten el dialecto; no excluye que la prueba corra también en SQLite (`p21-authority.md`). La prueba
  ya corre en SQLite en la suite completa y en el commit que la trae; marcarla `skipif(not PG)` (precedente en
  `test_roles_create.py` y `test_picklist_duplicada.py`) sería un `skip` como corrección, prohibido por el encargo.

## Corrección autorizada (solo arnés)

Una primitiva del arnés para los módulos que lanzan hilos contra la app en SQLite: un datastore SQLite **en fichero
temporal efímero** con el pool por defecto (`QueuePool`: una conexión DBAPI por hilo concurrente) y los mismos
`connect_args` de siempre (`check_same_thread=False`, necesario porque el pool reparte conexiones entre hilos), sin tocar
`busy_timeout`; el fichero se crea al entrar y se elimina al salir, pase lo que pase. Sobre PostgreSQL devuelve el motor
de `make_engine()` tal cual. `make_engine()` por defecto no cambia: `:memory:` + `StaticPool` sigue siendo lo correcto
para las pruebas sin hilos (rápido, sin ficheros). Solo `tests/test_warehouse_structure.py` la adopta en este ciclo.
