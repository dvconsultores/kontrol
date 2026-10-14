# Orden de operaciones (recuperado y congelado)

| Paso | Antes (`7c9c348`) | Después |
|---|---|---|
| 1 | `decode_token` → 401 `SESSION_INVALID` si no decodifica | igual |
| 2 | `SELECT … FOR UPDATE` de la sesión | igual |
| 3 | `revoked_at` puesto → 401 `SESSION_REVOKED`; hash ≠ → 401 `SESSION_INVALID`; expirada → marca y 401 `SESSION_EXPIRED` | igual |
| 4 | usuario inactivo → 403 `AUTH_USER_INACTIVE` | igual |
| 5 | `session.revoked_at = _now()` (asignación ORM; se escribe en el flush de `create_session`) | **`UPDATE sessions SET revoked_at, updated_at WHERE id AND revoked_at IS NULL` → `rowcount`**: 0 → 401 `SESSION_REVOKED`; ≠1 → `RuntimeError` |
| 6 | `create_session` (INSERT, UPDATE hash, `commit`) | igual, solo el dueño |
| 7 | auditoría `SESSION_REFRESHED` + `commit` | igual, solo el dueño |

`VALIDATIONS_BEFORE_OWNERSHIP` = 1–4 (ninguna muta estado salvo la expiración, que ya revocaba antes) ·
`OWNERSHIP_WRITE` = 5 · `MUTATIONS_AFTER_OWNERSHIP` = 6–7 · `ROLLBACK_SEMANTICS`: el perdedor lanza en 5 y la sesión
de base se cierra con rollback (0 filas tocadas); un fallo en 6–7 deshace también la revocación (misma transacción hasta
el `commit` de `create_session`), igual que antes. SA-08/SA-09 prueban que hash ≠ e inactivo no revocan.
