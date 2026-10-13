# Diseño de la corrección (solo arnés; producto 0; migraciones 0)

## Primitiva nueva en `tests/conftest.py`: `motor_para_hilos(nombre)`

Gestor de contexto (`@contextmanager`, como `volumen_de_instalacion_aislado`) que entrega un motor apto para que varios
hilos lo usen a la vez contra la app:

- **SQLite (sin `KONTROL_TEST_DB_URL`)**: directorio temporal propio (`tempfile.mkdtemp(prefix=f"kontrol-test-sqlite-{nombre}-")`)
  con un fichero `base.db`; `create_engine(f"sqlite+pysqlite:///{ruta}", future=True, connect_args={"check_same_thread": False})`
  con el pool por defecto de SQLAlchemy para SQLite en fichero (`QueuePool`): cada hilo concurrente obtiene su propia
  conexión DBAPI, y todas apuntan al mismo datastore. `check_same_thread=False` sigue siendo necesario porque el pool
  reparte conexiones entre hilos. No se fija `timeout` (el `busy_timeout` por defecto del driver, 5,0 s, no se toca), ni
  `isolation_level`, ni `PRAGMA` alguno. Al salir, pase o falle lo de dentro: `dispose()` del motor y `rmtree` del
  directorio.
- **PostgreSQL**: devuelve `make_engine()` tal cual (schema propio del ámbito, que PGLIFE suelta); nada que limpiar.

`make_engine()` **no cambia**: `:memory:` + `StaticPool` sigue siendo el defecto para las pruebas sin hilos. La primitiva
es opt-in para los módulos que lanzan hilos contra la app sobre SQLite.

## Adopción: solo `tests/test_warehouse_structure.py`

El fixture de módulo `_app_client` pasa a montar el mundo dentro de `with motor_para_hilos("warehouse-structure") as engine:`
(mismo cuerpo, misma factoría, misma `TestClient`), de modo que el datastore vive lo que vive el módulo y desaparece
con él. La prueba objetivo **no cambia ni una línea**: conserva `Barrier(2)`, `sorted(results) == [200, 409]` y
`total == 1`. Ningún otro módulo se toca en este ciclo (los que podrían adoptarla quedan como observación).

## Certificación del arnés: `tests/test_motor_para_hilos.py` (ACS-01…08)

Pruebas que corren en los dos motores, sin `skip`:

| Id | Qué demuestra | Cómo |
|---|---|---|
| ACS-01 | una conexión DBAPI por hilo | dos hilos, cada uno con su `Session`, abren una transacción y se encuentran en una barrera con la conexión en la mano; los ids de la conexión cruda son distintos |
| ACS-02 | mismo datastore | lo que confirma el hilo A lo lee el hilo B por su propia conexión |
| ACS-03 | aislamiento | lo que A inserta sin confirmar no lo ve B; tras el `rollback` de A, B no lo ve |
| ACS-04 | entrelazado controlado | dos hilos insertan la misma clave única; una barrera en `before_cursor_execute` suelta los dos INSERT a la vez: exactamente un éxito, exactamente un `IntegrityError`, una fila, ningún otro error |
| ACS-05 | bloqueo ≠ duplicado | sobre un fichero SQLite aparte, una conexión que tiene la escritura y otra con `timeout=0` que intenta escribir: `OperationalError` («database is locked»), no `IntegrityError`; `es_violacion_unica` lo rechaza. Usa `sqlite3` de la biblioteca estándar y un motor propio de la prueba (no la primitiva): vale en cualquier corrida |
| ACS-06 | limpieza | en SQLite el directorio existe dentro del `with` y no existe después, y el pool queda sin conexiones; en PostgreSQL no se crea ningún directorio `kontrol-test-sqlite-*` |
| ACS-07 | limpieza en fallo | una excepción dentro del `with` también deja el directorio eliminado |
| ACS-08 | contrato estático | el código de la primitiva no contiene `timeout`, `StaticPool`, `:memory:`, `sleep`, `PRAGMA` ni `isolation_level` |

Y sobre la prueba objetivo y el módulo: ACS-09 prueba sola ×20 SQLite; ACS-10 módulo ×10 SQLite; ACS-11 prueba sola
×20 PostgreSQL; ACS-12 suites de almacenes en PostgreSQL; ACS-13…16 suites completas (SQLite ×2, PostgreSQL ×1, clasificadas
contra la línea base), E2E global ×1, `git diff --stat -- app/ alembic/` vacío; ACS-17…20 mutaciones M-01…M-12.

## Mutaciones diseñadas (M-01…M-12)

| Id | Mutación (en `conftest.py` salvo que se diga) | Detector esperado |
|---|---|---|
| M-01 | la primitiva devuelve `make_engine()` también en SQLite (vuelve a `StaticPool :memory:`) | ACS-01 (una sola conexión), ACS-04 (500/ResourceClosedError), ACS-06 (sin directorio) |
| M-02 | `:memory:` con `QueuePool` (un `:memory:` privado por conexión: datastores distintos) | ACS-02 (B no ve lo de A), ACS-04 (dos éxitos, no hay conflicto) |
| M-03 | `poolclass=StaticPool` sobre el fichero | ACS-01, ACS-04 |
| M-04 | se quita `check_same_thread=False` | ACS-01/02 (`ProgrammingError` de pysqlite al reutilizar la conexión en otro hilo) o ACS-09 |
| M-05 | sin `rmtree` al salir | ACS-06, ACS-07 |
| M-06 | sin `dispose()` al salir | ACS-06 (pool con conexiones vivas) |
| M-07 | `connect_args` con `timeout=60` | ACS-08 |
| M-08 | el fixture de `test_warehouse_structure.py` vuelve a `make_engine()` | ACS-09/10 (la carrera reaparece) |
| M-09 | `except IntegrityError` → `except Exception` en `create_location_full` (producto, mutación de diagnóstico) | ACS-05/… no lo ve el arnés: lo detecta `git diff -- app/` = 0 (tripwire ACS-16) y la prueba de bloqueo deja claro por qué no se traduce todo |
| M-10 | `rollback` de A sustituido por `commit` en ACS-03 (prueba vacía) | ACS-03 falla contra su propio contrato (B ve la fila) |
| M-11 | barrera de ACS-04 retirada (los INSERT ya no coinciden) | ACS-04 sigue pasando → la mutación se declara **equivalente en resultado** y se mide con la sonda que los INSERT ya no se solapan (documentado, no cuenta como detector) |
| M-12 | `test_concurrencia…` con `sorted(results) == [200, 409] or len(results) == 1` (debilitar la aserción) | contrato estático del arnés: el texto de la prueba objetivo conserva `sorted(results) == [200, 409]` exacto (ACS-08 lo cubre) |

Las mutaciones se aplican sobre copias, se restauran desde la copia (nunca `git checkout`), con `__pycache__` purgado y
`PYTHONDONTWRITEBYTECODE=1`; GOOD→PASS, MUTATED→FAIL, RESTORED→PASS.
