# POC de mismo datastore: la misma carrera bajo dos topologías SQLite

Guion `same-datastore-poc.py` (de Claude, fuera del repositorio; copia enmascarada aquí) y su salida en
`same-datastore-poc-output.txt`. Monta el mismo mundo que el fixture de módulo de `tests/test_warehouse_structure.py`
(`init_models` + `create_all` + `initialize` + `create_app` + `TestClient`, que relanza en el hilo las excepciones del
servidor) y corre la misma carrera de la prueba objetivo: dos hilos, barrera, `POST /organization/locations` con el
mismo código en el mismo almacén. Dos modos por topología: **natural** (×30, sin intervenir) y **entrelazado
controlado** (×5): un `before_cursor_execute` del motor hace esperar a cada hilo en una `Barrier(2, timeout=10)` justo
antes de ejecutar su `INSERT INTO warehouse_locations`, de modo que los dos INSERT se liberan a la vez. La barrera es
instrumentación de la POC: no está ni estará en la prueba ni en el producto.

| Topología | Modo | Rondas | `[200, 409]` y total 1 | Fallos | Conexiones DBAPI distintas vistas en `checkout` |
|---|---|---|---|---|---|
| (a) `StaticPool` + `:memory:` (la actual de `make_engine()`) | natural | 30 | 13 | 17 | **1** |
| (a) | controlado | 5 | 0 | **5/5** | 1 |
| (b) fichero temporal, `QueuePool` por defecto, `check_same_thread=False` | natural | 30 | **30** | 0 | **2** |
| (b) | controlado | 5 | **5** | 0 | 2 |

Firmas de fallo en (a), natural (17/30): 15× `[200]` + `ResourceClosedError` en el hilo muerto; 1× `[200]` +
`sqlite3.DatabaseError: UNIQUE constraint failed` (clase base, no `IntegrityError`); 1× `[409]` con total **0** +
`InvalidRequestError: Could not refresh instance` (el `rollback` del perdedor deshizo en la conexión compartida la fila
que el ganador acababa de insertar). En (a) controlado, 5/5 `ResourceClosedError`: con los dos INSERT liberados a la vez
sobre la única conexión pysqlite, el cursor de uno se cierra bajo el otro. En (b) nunca: 35/35 rondas con exactamente un
200, un 409 y una fila; con el entrelazado controlado el segundo INSERT espera el `busy_timeout` por defecto del driver
(5,0 s, no se toca) a que el primero confirme, y entonces recibe la violación única como `IntegrityError`
(5 rondas en 0,2 s: la espera real es de milisegundos).

Regla de mismo datastore (del encargo): en (b) se verifica antes de la carrera que dos conexiones crudas del motor son
objetos distintos (`A != B: True`) y que B lee lo que A confirmó (`B ve lo que confirmó A: True`). Un `:memory:` privado
por conexión no sería un datastore compartido y queda descartado por construcción. Al final el directorio temporal se
elimina (`fichero temporal eliminado: True`).

Corrección de la POC durante el ciclo: la primera corrida (`poc.txt`, no conservada) usaba el mismo prefijo de código de
almacén en el modo natural y en el controlado, el segundo alta devolvía 409 y el guion moría con `KeyError: 'id'`; se
añadió un prefijo por llamada (`W`/`C`). Es un defecto del guion, no una observación sobre el producto ni el arnés.
