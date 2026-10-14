# Topología hilo → sesión → conexión (UoM) · `probe-plugin.py`, `topology-traces.txt` · `CONNECTION_TOPOLOGY = PROVEN`

Arnés actual: **una sola conexión DBAPI C1** para el hilo principal y los hilos T5/T6 de las dos peticiones (10/10 corridas
sondadas). Cada petición abre su `Session` (`_override_get_db`) sobre la misma `sqlite3.Connection`/transacción.

Secuencia de una corrida PASS limpia (A'-1): T5 SELECT abierta → T6 SELECT abierta → T5 UPDATE `valid_to` → T6 UPDATE
`valid_to` → T5 SELECT todas → T6 SELECT todas → T5 INSERT → T6 INSERT → `IntegrityError` en T6 (índice parcial) → COMMIT
T5 → ROLLBACK T6 → `[200, 409]`. Funciona porque el rollback de T6 llegó **después** del commit de T5.

Secuencia del falso verde (A'-8): el ROLLBACK del perdedor (T6) llega **antes** del COMMIT del ganador (T5) sobre la misma
transacción compartida: deshace el UPDATE y el INSERT de T5; el COMMIT de T5 confirma nada; `db.refresh(version)` no
encuentra la fila → `InvalidRequestError` → 500 → `TestClient` lo relanza → el hilo muere; `results == [409]`; en la base
solo queda la versión original, abierta → la aserción `len(abiertas) == 1` pasa.

Con `motor_para_hilos` (O2-02 y POC (b)): dos conexiones DBAPI (C1/C2), una transacción por petición; el rollback de una no
toca a la otra.

| Hilo | Session | DBAPI (actual) | DBAPI (`motor_para_hilos`) | Datastore |
|---|---|---|---|---|
| MAIN (setup, `_FACTORY()`) | varias | C1 | C1 | único |
| T5 (POST versión 120) | S1 | C1 | C1 | único |
| T6 (POST versión 130) | S2 | **C1** | **C2** | único (mismo fichero) |
