# Entrelazado controlado (instrumentación; nada de esto es una corrección) · `poc-output.txt`, `same-datastore-poc-auth.py`

Mecanismo: oyente `before_cursor_execute` que, en hilos no principales, hace esperar en una `Barrier(2, timeout=10)` a cada
hilo justo antes de su **primera escritura** a `sessions` (`UPDATE sessions …` o `INSERT INTO sessions`). Así los dos
hilos han ejecutado su `SELECT` (la lectura de `revoked_at`) antes de que ninguno escriba: la interleaving I1 del
encargo (T1 lee, T2 lee, T1 rota, T2 rota, T1 commit, T2 commit). Modo natural: barrera solo de arranque de los hilos.

| Topología | Modo | Rondas | Resultado | Sesiones vivas (delta) | Conexiones DBAPI |
|---|---|---|---|---|---|
| (a) `StaticPool` `:memory:` (actual) | natural | 20 | 19× `[200, 401]` · 1× `[]` + `StaleDataError` | +0 / +0 | 1 |
| (a) | controlado I1 | 5 | **3× `[200, 200]`** · 2× `[200]` + `OperationalError: cannot commit transaction - SQL statements in progress` | **+1** | 1 |
| (b) fichero temporal, una conexión por hilo (= `motor_para_hilos`) | natural (barrera de arranque) | 20 | **18× `[200, 200]`** · 2× `[200, 401]` | **+1** / +0 | **2** |
| (b) | controlado I1 | 5 | **5× `[200, 200]`** | **+1** | 2 |
| (c) EXPLORACIÓN: (b) + `BEGIN IMMEDIATE` en cada transacción | natural | 20 | **20× `[200, 401]`** | +0 | 2 |
| (c) | controlado I1 | 5 | 5× `[200]` + `OperationalError: database is locked` | +0 | 2 |

Lecturas:

1. **(a)**: la POC natural pasa 19/20 (sus dos peticiones salen con un `start()` casi simultáneo pero la ventana es corta)
   y la prueba real falla 15/20: la frecuencia depende del entrelazado que cada arranque produce; con I1 forzada, 5/5
   fallan (3 veces ganan las dos, 2 veces muere un hilo). Reproducción determinista de la capa 1.
2. **(b)**: con una conexión por hilo sobre el mismo datastore **no hay ninguna excepción** (capa 1 resuelta) y, con I1,
   **las dos renovaciones ganan 5/5**; en natural, 18/20. Es la carrera del producto: SQLite ignora `FOR UPDATE`, pysqlite
   ejecuta el `SELECT` fuera de transacción (isolation_level `''` legado: `BEGIN` solo antes del primer DML) y no retiene
   ningún bloqueo entre leer y escribir; las dos escrituras se serializan por el `busy_timeout` del driver (por eso no
   hay `database is locked`) y **ambas confirman**. Queda una sesión viva huérfana (+1): exactamente el síntoma de
   REM-AUTH-ROUTE-CRAWL-001 en producción antes del bloqueo de fila.
3. **(c)** es solo exploración para la decisión: si la transacción SQLite empieza con `BEGIN IMMEDIATE` (bloqueo
   RESERVED desde el primer `SELECT`), las dos renovaciones se serializan y la segunda lee la fila ya revocada → 20/20
   `[200, 401]`. Con I1 forzada el resultado `database is locked` es un artefacto de la propia barrera (el segundo
   `BEGIN IMMEDIATE` espera al primero, que está parado en la barrera esperando al segundo: la interleaving I1 es
   imposible por construcción y el `busy_timeout` de 5 s vence). No es una corrección autorizada ni propuesta como tal.
4. El Experimento B (la prueba real con `motor_para_hilos`, 20/20 PASS) pasa porque sin barrera de arranque las dos
   peticiones salen escalonadas y la primera confirma antes de que la segunda lea (traza en `topology-traces.txt`).
   **Sería confianza falsa**: la misma prueba con las dos lecturas antes de la primera escritura da `[200, 200]`.
