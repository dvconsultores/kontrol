# Contrato de rotación de sesión (recuperado físicamente)

| Registro | Valor | Fuente |
|---|---|---|
| `AUTH_ROTATION_CONTRACT_SOURCE` | `docs/remediation/route-crawl-auth-closeout.md` (REM-AUTH-ROUTE-CRAWL-001, 2026-08-30) · ADR-004 (access token en memoria, refresh en cookie HttpOnly) · Spec 001 FR-001-020/021/022 · `tests/test_auth_session_rotation.py` (8 pruebas) · `service.py::rotate_session` | leídos |
| `ROTATION_ATOMICITY_REQUIRED` | **sí**: «dos renovaciones concurrentes con el mismo refresh token de un solo uso no pueden ganar las dos»; si ganaran las dos desaparece la detección de token robado y queda una sesión viva huérfana | closeout «Segundo defecto» |
| `EXPECTED_WINNER_COUNT` | exactamente 1 | closeout, prueba |
| `EXPECTED_LOSER_HTTP` / `EXPECTED_DOMAIN_ERROR` | **401** `SESSION_REVOKED` («la segunda transacción espera y encuentra la sesión ya revocada»); `SESSION_INVALID` si el hash no coincide; nunca 500 | closeout, `rotate_session` |
| `OLD_REFRESH_TOKEN_INVALID_AFTER` | inmediatamente tras la rotación ganadora (`revoked_at` de la sesión anterior) | `rotate_session`, `test_un_token_ya_usado_no_sirve_dos_veces` |
| `SESSION_VERSION_RULE` / `TOKEN_FAMILY_RULE` | no hay versión ni familia de tokens: una fila `sessions` por refresh token (`refresh_token_hash`), revocación por `revoked_at`; la rotación revoca la fila y crea otra | modelo `Session` |
| `REPLAY_RULE` | un token usado responde 401 `SESSION_REVOKED`/`SESSION_INVALID` | pruebas 2 y 8 del módulo |
| `POSTGRESQL_AUTHORITY` | sí (P21); el cierre de la remediación se certificó sobre PostgreSQL 18.6 | closeout |
| `SQLITE_CONTRACT` | ninguno ratificado: el closeout afirma que `with_for_update` «es inocuo en SQLite —serializa las escrituras por su cuenta—»; esa afirmación se comprueba en este ciclo, no se asume | closeout |
| `POSTGRES_ATOMICITY_MECHANISM` | **bloqueo de fila**: `select(AuthSession).where(id == sid).with_for_update()` antes de leer `revoked_at` (commit `bf0ba9e`, 2026-08-30); bajo READ COMMITTED la segunda transacción espera el bloqueo y relee la fila ya revocada → 401 | `service.py` 196–205 |

Flujo real (`ROUTE` `POST /api/v1/auth/refresh` → `rotate_session(db, refresh_token, request_id)`):

1. `security.decode_token(refresh, expected_type="refresh")` → `SESSION_INVALID` 401 si no decodifica.
2. `LOOKUP`: `SELECT … FROM sessions WHERE id = :sid FOR UPDATE` (SQLite: sin `FOR UPDATE`).
3. `CURRENT_TOKEN_CHECK`: `revoked_at is not None` → 401 `SESSION_REVOKED`; hash ≠ → 401 `SESSION_INVALID`; expirada → marca y 401 `SESSION_EXPIRED`.
4. usuario activo (403 si no).
5. `ROTATION_DECISION` + `UPDATE_SITE`: `session.revoked_at = now()`; `create_session()` → `db.add` + `db.flush()` (INSERT `sessions` y UPDATE `sessions` de la anterior) → regenera el token con el id real → `db.commit()` (**COMMIT_SITE 1**) → `db.refresh`.
6. `_audit(SESSION_REFRESHED)` → `db.commit()` (**COMMIT_SITE 2**).
7. Respuesta: cookie nueva + access token.

`LOCK` = `FOR UPDATE` (solo PostgreSQL) · `CAS_STYLE_UPDATE` = no · `VERSION_CHECK` = no · `UNIQUE_CONSTRAINT` = ninguna
que impida dos rotaciones · `ROWCOUNT_CHECK` = el de SQLAlchemy en el UPDATE (`StaleDataError` si 0 filas) · `DOMAIN_ERROR`
= `KontrolError` 401 · `HTTP_MAPPING` = `KontrolError` → su `status_code`; cualquier otra excepción → 500 «Error no controlado».
