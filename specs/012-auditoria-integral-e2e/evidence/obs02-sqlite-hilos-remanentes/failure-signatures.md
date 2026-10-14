# Firmas (UoM) · `UNKNOWN = 0`

| Firma | Qué | Observada | Mecanismo |
|---|---|---|---|
| F1 hilo muerto con PASS | `InvalidRequestError: Could not refresh instance` en el ganador; `results == [409]`; la base conserva solo la versión original abierta | **sí**: 5/30 corridas reales (aviso de pytest), 4/35 rondas de la POC (a) | rollback del perdedor sobre la transacción compartida deshace el trabajo del ganador (conexión compartida) |
| F2 `sqlite3.DatabaseError: UNIQUE constraint failed` (clase base, no `IntegrityError`) + hilo muerto | `[200]` | sí: 1/35 POC (a) | cursor compartido en estado inconsistente |
| F3 `OperationalError: cannot commit transaction - SQL statements in progress` + hilo muerto | `[200]` | sí: 1/35 POC (a) | commit de un hilo con el cursor del otro abierto |
| F4 `[200, 200]` con 3 versiones y 1 abierta | las dos peticiones crean versión | sí: 18/30 natural (a), 3/30 natural (b) | **no es defecto**: la segunda petición leyó la nueva versión ya confirmada como «actual», la cerró y creó otra posterior (`start > current_start`); contrato AC-011-12 intacto (una abierta) |
| F5 `[200, 409]` con 2 versiones | contrato de carrera real | sí: 7/30 (a), 27/30 + 5/5 (b) | el perdedor ve la versión nueva en `assert_no_version_overlap` o choca con el índice parcial |
| F6 `database is locked` | — | **sí, nueva, al adoptar conexiones propias**: `test_el_historico_no_cambia_al_cambiar_el_factor` | la prueba mantenía una sesión de escritura abierta (`flush` sin `commit`) mientras llamaba a la API (`_company_id()` → login → INSERT de auditoría en otra conexión): con el bloqueo de base de SQLite, la petición espera a una transacción que nunca se suelta hasta que la petición vuelve; antes «funcionaba» porque la app escribía en la transacción de la prueba |
| F7 resultado faltante aceptado | `len(results) == 1` sin aserción | **sí** (la prueba no afirma nada sobre `results`) | falso verde |
