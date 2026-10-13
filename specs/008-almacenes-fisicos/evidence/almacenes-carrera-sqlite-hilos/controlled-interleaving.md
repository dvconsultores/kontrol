# Entrelazado controlado (instrumentación, no corrección)

Objetivo: dejar de depender de la suerte del planificador para ver el fallo. Mecanismo: un oyente
`before_cursor_execute` sobre `Engine` que, solo en hilos no principales y solo ante `INSERT INTO warehouse_locations`,
espera en una `threading.Barrier(2, timeout=10)`; los dos hilos quedan parados con su INSERT preparado y se sueltan a la
vez. `BrokenBarrierError` se ignora (si un hilo murió antes, el otro sigue). Se quita el oyente al terminar cada ronda.

Resultado (ver `same-datastore-poc-output.txt`):

- Topología actual (StaticPool `:memory:`, una conexión pysqlite para todos los hilos): **5/5 rondas fallan** con la
  misma firma, `resultados=[200]`, hilo muerto por `ResourceClosedError: This result object does not return rows. It has
  been closed automatically.`, total 1. Los dos hilos ejecutan su INSERT sobre el mismo objeto `sqlite3.Connection` y el
  mismo ciclo de cursor/commit; pysqlite serializa las llamadas con su propio cerrojo pero no el ciclo de vida del
  cursor ni de la transacción, de modo que el `commit` de un hilo cierra el cursor cuyo `lastrowid`/`rowcount` está
  leyendo el otro, o el `rollback` del perdedor deshace la fila ya insertada del ganador (firma `[409]` + total 0 del
  modo natural). Lo que la prueba ve es un 500 que `TestClient` relanza en el hilo, un único elemento en `results` y
  `assert [200] == [200, 409]`.
- Fichero temporal con una conexión por hilo: **5/5 rondas `[200, 409]` con una fila**. El segundo INSERT espera (dentro
  del `busy_timeout` por defecto del driver) a que el primero confirme y recibe la violación única como
  `IntegrityError`, que `create_location_full` traduce a 409.

Conclusión: el entrelazado controlado convierte el intermitente en determinista bajo la topología actual y demuestra que
el mismo entrelazado es inocuo cuando cada hilo tiene su conexión. La barrera no forma parte de ninguna corrección: la
prueba objetivo conserva su `Barrier(2)` de arranque y nada más.
