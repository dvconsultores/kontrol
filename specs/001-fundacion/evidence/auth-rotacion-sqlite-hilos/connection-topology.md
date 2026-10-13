# Topología hilo → sesión → conexión (sonda `probe-plugin.py`, trazas en `topology-traces.txt`) · `CURRENT_TOPOLOGY = PROVEN`

Arnés actual (`make_engine()` en SQLite): **una sola conexión DBAPI C1** para el hilo principal (setup, login) y para los
hilos de `TestClient` (T1 login, T2/T3 los dos refresh) en 10/10 corridas sondadas (`conexiones=1`). Cada petición abre su
`Session` (`_override_get_db`), pero las dos sesiones se apoyan en el mismo `sqlite3.Connection`, con el mismo cursor y
la misma transacción pysqlite.

Secuencia típica de `[200, 200]` (corrida A'-1): T2 SELECT sessions → T3 SELECT sessions → T2 UPDATE revoked_at → T3
UPDATE revoked_at → T2 INSERT → T3 INSERT → UPDATE hash ×2 → COMMIT T3 → COMMIT T2 → 200 y 200. Los dos leen
`revoked_at IS NULL`, los dos revocan la misma fila y crean dos sesiones; una queda viva y huérfana.

Secuencia de `OperationalError: cannot commit transaction - SQL statements in progress` (A'-2): el `COMMIT` de T3 llega
mientras el cursor de T2 tiene un resultado abierto sobre la misma conexión; pysqlite lo rechaza; 500 → `TestClient`
relanza → el hilo muere → `len([200]) == 1`. La `StaleDataError` (A'-8) es el UPDATE de un hilo que no encuentra la
fila que el otro acaba de cambiar en la misma transacción compartida.

Con `motor_para_hilos` (Experimento B): **2 conexiones DBAPI** (T2 → C1, T3 → C2), cada una con su transacción; el
`TestClient` no abre más sesiones ni conexiones que una por petición. Un `commit`/`rollback` ya no afecta al otro hilo.

Mapa Thread → Session → Connection → DBAPI → datastore:

| Hilo | Session | SQLAlchemy Connection | DBAPI (arnés actual) | DBAPI (`motor_para_hilos`) | Datastore |
|---|---|---|---|---|---|
| MAIN | varias (setup, `_FACTORY()`) | del pool | C1 | C1 | único |
| T1 (login vía TestClient) | S1 | del pool | C1 | C1 | único |
| T2 (refresh A) | S2 | del pool | C1 | C1 | único |
| T3 (refresh B) | S3 | del pool | **C1** | **C2** | único (mismo fichero) |

`TESTCLIENT`: `raise_server_exceptions=True` (por defecto); `THREAD_EXCEPTION_ESCAPES = sí`; un 500 se relanza en el hilo
y la prueba lo ve como «faltan resultados» (`assert 1 == 2`), nunca como 500.
