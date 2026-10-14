# Contrato de la escritura condicional (congelado antes de implementar)

| Registro | Valor |
|---|---|
| `AUTH_SESSION_MODEL` / `SESSION_TABLE` | `app.modules.identity_access.models.Session` (importado como `AuthSession` en el servicio) / `sessions` |
| `ID_COLUMN` · `REVOKED_AT_COLUMN` · `UPDATED_AT_COLUMN` | `id` (UUID, PK) · `revoked_at` (`DateTime(timezone=True)`, nullable) · `updated_at` (`TimestampMixin`, `onupdate=utcnow`) |
| `UPDATE_PRIMITIVE` | `db.execute(update(AuthSession).where(AuthSession.id == session.id, AuthSession.revoked_at.is_(None)).values(revoked_at=ahora, updated_at=ahora)).rowcount` — el mismo patrón que ya usa `notifications/service.py` (`marcar_leida`, `archivar`: `update(...).where(..., read_at.is_(None)).rowcount`) |
| `EXECUTION_SITE` | `rotate_session`, tras todas las validaciones puras y antes de `create_session` |
| `ROWCOUNT_SOURCE` | `CursorResult.rowcount` del UPDATE (SQLite: `sqlite3_changes`; psycopg2: filas afectadas) — probado 1→0 en los dos motores (`rowcount-sqlite.md`, `rowcount-postgres.md`) |
| `SESSION_SYNCHRONIZE_OPTION` | por defecto (`'auto'` → `'evaluate'`): la instancia ya cargada por el `SELECT … FOR UPDATE` recibe `revoked_at`/`updated_at` en memoria; nadie vuelve a asignar `revoked_at` por atributo en la rotación, así que no hay flush que lo reescriba (SA-13) |
| `FLUSH_BEHAVIOR` / `COMMIT_OWNER` | el UPDATE viaja en la transacción abierta; `create_session` hace el `commit` (incluye la revocación y la fila nueva); después la auditoría y un segundo `commit`, como antes. El perdedor lanza `KontrolError` y la ruta/`get_db` cierran la sesión: `rollback` de un UPDATE que no tocó filas |
| `ORM_OBJECT_ALREADY_LOADED` / `ORM_REFRESH_REQUIRED` | sí / no (`expire_on_commit=False` en el producto; `create_session` refresca solo la sesión nueva) |
| `rowcount > 1` | imposible con PK; se trata como invariante rota: `RuntimeError` → 500 «Error no controlado», nunca éxito ni 401 (SA-16 lo fija estáticamente) |
| Ganador / perdedor | `rowcount == 1` → sigue el flujo existente (sesión nueva, auditoría `SESSION_REFRESHED`, 200) · `rowcount == 0` → `KontrolError(code="SESSION_REVOKED", status_code=401)`, sin sesión nueva, sin credenciales, sin auditoría de éxito |
| `with_for_update()` | se conserva (defensa en profundidad en PostgreSQL) |
| No se toca | hash del refresh, expiración, usuario inactivo, `create_session`, auditoría, respuesta, OpenAPI, modelo, esquema |
