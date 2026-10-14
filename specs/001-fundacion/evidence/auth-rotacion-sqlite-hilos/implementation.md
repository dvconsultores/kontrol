# Implementación (CLAUDE_ONLY; DeepSeek 0)

## Producto · `app/modules/identity_access/service.py::rotate_session`

- Import: `from sqlalchemy import select, text, update`.
- Comentario corregido (OBS-05). `COMMENT_BEFORE`: «`with_for_update` no hace nada en SQLite, que serializa las escrituras
  por su cuenta; sobre PostgreSQL, que es el motor de producción (P21), la segunda transacción espera y encuentra la sesión
  ya revocada.» `COMMENT_AFTER`: «Sobre PostgreSQL, el motor de producción (P21), la segunda transacción espera aquí y
  encuentra la sesión ya revocada. SQLite ignora `FOR UPDATE` y no retiene ningún bloqueo entre leer y escribir: dos
  transacciones pueden leer la misma sesión sin revocar antes de que ninguna escriba (demostrado en
  AUTH-ROTACION-SQLITE-HILOS), así que la propiedad de la rotación la decide además la escritura condicional de más abajo,
  igual en los dos motores.»
- Rotación: `session.revoked_at = _now()` → UPDATE condicional (`id == session.id AND revoked_at IS NULL`, valores
  `revoked_at`/`updated_at` = `_now()`), `rowcount == 0` → `KontrolError(SESSION_REVOKED, 401)`; `rowcount != 1` →
  `RuntimeError` (invariante); después, sin cambio: `create_session`, auditoría, `commit`, respuesta.
- `with_for_update()` conservado. Sin migración, sin esquema, sin `BEGIN IMMEDIATE`, sin retry/sleep/timeout, sin captura
  amplia. Diff del producto: 27 líneas en un fichero.

## Arnés · `tests/test_auth_session_rotation.py`

El fixture de módulo `_app_client` envuelve su cuerpo en `with motor_para_hilos("auth-session-rotation") as engine:`
(sangrado un nivel, comentario de tres líneas, import de `motor_para_hilos` en lugar de `make_engine`). La prueba
objetivo no cambia (aserciones fijadas por SA-16).

## Pruebas · `tests/test_auth_rotacion_atomica.py` (nuevo; SA-01…SA-16)

Mundo propio sobre `motor_para_hilos("auth-rotacion-atomica")`. SA-01/02 fuerzan I1 con `before_cursor_execute`: barrera
antes del `SELECT sessions` en los dos motores y, solo en SQLite, otra antes del primer `UPDATE sessions` (en PostgreSQL
`FOR UPDATE` serializa la lectura y esa barrera pediría un orden de bloqueo imposible); el oyente se instala solo durante
la carrera; las excepciones de hilo se recogen y se exigen vacías (SA-15). SA-14 inyecta un `OperationalError` en
`update` con `monkeypatch` y exige que suba tal cual. SA-16 es el contrato estático (escritura condicional, orden,
`with_for_update`, reloj canónico, sin `BEGIN IMMEDIATE`/captura amplia/sleep/retry; prueba objetivo intacta).

## Documentación · `docs/remediation/route-crawl-auth-closeout.md`

`REM_AUTH_BEFORE`: «`with_for_update` es inocuo en SQLite —serializa las escrituras por su cuenta— y efectivo sobre
PostgreSQL, que es el motor de producción (`P21`).» `REM_AUTH_AFTER`: la misma frase reducida a PostgreSQL más un párrafo
«Corrección del 2026-10-14» que explica el error, la evidencia (5/5) y la escritura condicional. Nada más del documento cambia.
