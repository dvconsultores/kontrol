# Firmas de fallo (taxonomía del encargo) · `UNKNOWN = 0`

| Firma | Qué | Observada | Mecanismo |
|---|---|---|---|
| F1 `[200, 200]` | las dos renovaciones ganan | **sí** (8/20 sola; 5/5 controlado en (a) y en (b); 18/20 natural en (b)) | las dos sesiones leen `revoked_at IS NULL` antes de que ninguna escriba; sin `FOR UPDATE` (SQLite lo ignora) nada detiene a la segunda. En (a) además comparten la transacción |
| F2 0 ganadores | `[]` | sí (1/20): los dos hilos mueren | `StaleDataError` en los dos por el `rollback`/`commit` ajeno sobre la conexión compartida |
| F3 >1 ganador con follow-up inválido | — | no medido en la prueba (no hay follow-up); en la POC `vivas_delta = +1`: queda una sesión viva huérfana | consecuencia de F1 |
| F4 perdedor con status distinto al contrato | `[401]` solo (1/20) | sí, como consecuencia de F8 | el otro hilo murió |
| F5 IntegrityError filtrado | — | no | no hay unicidad implicada |
| F6 OperationalError / locked | `cannot commit transaction - SQL statements in progress` (5/20) | **sí**, pero no es un bloqueo entre conexiones: es el `commit` de un hilo sobre la única conexión mientras el cursor del otro sigue abierto | conexión compartida (a) |
| F7 ResourceClosedError / transaction closed | — | no en auth (sí en almacenes) | — |
| F8 excepción de hilo relanzada | sí: todo 500 lo relanza `TestClient` (`raise_server_exceptions=True`) y el hilo muere sin `append` | **sí** (F6 y `StaleDataError`) | `len(resultados) == 1` o `0` |
| F9 estado final inconsistente | sí en la POC: `vivas_delta = +1` cuando ganan las dos | **sí** | sesión huérfana (el síntoma de REM-AUTH en producción, 484 vivas) |
| F10 solo aserción | no: cada fallo tiene mecanismo | — | — |
| F11 `StaleDataError: UPDATE statement on table 'sessions' expected to update 1 row(s); 0 were matched` (2/20) | el UPDATE de un hilo no encuentra la fila que el otro acaba de deshacer/confirmar en la misma conexión | **sí** | conexión compartida (a) |

Dos capas distintas, las dos probadas:

- **Capa 1 (arnés)**: F2, F4, F6, F8, F11 existen solo con la conexión compartida de `make_engine()` (sonda: 1 conexión en
  10/10). Desaparecen con una conexión por hilo (`motor_para_hilos`): 0 excepciones en 20 rondas naturales + 5 controladas.
- **Capa 2 (producto sobre SQLite)**: F1/F9 **persisten** con conexiones independientes sobre el mismo datastore: 18/20
  naturales con barrera de arranque y 5/5 controladas. Es la carrera que `with_for_update` cierra en PostgreSQL y que
  SQLite no cierra porque ignora `FOR UPDATE` y pysqlite no retiene ningún bloqueo de lectura entre el SELECT y el UPDATE.
