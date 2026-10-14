# POC I1 en SQLite con el UPDATE condicional exacto (`cas-poc.py`, `cas-poc-output.txt`)

Topología de `motor_para_hilos`: fichero temporal, pool por defecto (una conexión DBAPI por hilo), mismo datastore. Dos
hilos: cada uno abre su `Session`, ejecuta el `SELECT … FOR UPDATE` (ignorado por SQLite), ve `revoked_at IS NULL`,
espera en una barrera (los dos han leído: frontera de escritura) y ejecuta el UPDATE condicional; quien obtiene
`rowcount == 1` inserta la sesión de reemplazo; los dos confirman.

| Rondas | Resultado | Excepciones | `database is locked` | Sesión original | Reemplazos por ronda |
|---|---|---|---|---|---|
| 10 | **10/10**: un hilo `rowcount 1`, el otro `rowcount 0`; los dos habían leído la sesión libre | 0 | 0 | revocada | exactamente 1 (las vivas acumuladas suben de una en una) |

Mecanismo: el primer UPDATE toma el bloqueo RESERVED; el segundo espera dentro del `busy_timeout` por defecto del driver
(ninguno de los dos retiene SHARED entre leer y escribir, así que no hay interbloqueo) y, cuando el primero ha confirmado,
no encuentra ninguna fila con `revoked_at IS NULL`: 0 filas. `FIRST_ROWCOUNT = 1` · `SECOND_ROWCOUNT = 0` ·
`SQLITE_EXCEPTION = 0` · `DATABASE_LOCKED = 0` · `FINAL_REVOKED_STATE = revocada`. Sin retry, sin `BEGIN IMMEDIATE`,
sin tocar el `busy_timeout`. `SQLITE_I1_CAS_BEHAVIOR = PROVEN` · `SQLITE_LOCK_BLOCKER = 0` · `NEW_MATERIAL_DECISION = 0`.

PostgreSQL (misma POC, 5 rondas): `FOR UPDATE` serializa la lectura, el segundo hilo lee la sesión ya revocada y no llega
a escribir (`leyó_revocada`); el primero `rowcount 1`. La barrera «los dos han leído» no puede reunir a los dos en
PostgreSQL por construcción (el segundo `SELECT FOR UPDATE` espera al `commit` del primero): no se fuerza un orden de
bloqueo imposible; se usa barrera de arranque.

Nota ORM observada: con `synchronize_session` por defecto (`evaluate`), la instancia cargada del perdedor también muestra
`revoked_at` en memoria tras el UPDATE de 0 filas; es inocuo (el perdedor lanza y su sesión se deshace) y en el ganador
coincide con la base (SA-13).
