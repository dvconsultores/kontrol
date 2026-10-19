# Inventario del flujo (lectura del código en `0e2cb7b`)
Único camino que analiza: `POST /api/v1/documentos/{document_id}/versiones` → `documents/api.py::upload_version` →
`documents/service.py::upload_version`. `import_legacy_reference` guarda sin analizar y no entra en esta deuda.

| Etapa | ¿Sesión? | ¿Conexión prestada? | ¿Transacción? | E/S de base | E/S externa | Fichero persistido | Mutación de base |
|---|---|---|---|---|---|---|---|
| `LicenseMiddleware` (`_get_mode`, threadpool) | propia | sí, breve | sí, rollback | SELECT installations, license_states | — | no | no |
| `require_write_allowed` → `get_license_mode` | la de `get_db` | **sí, primer checkout** | **autobegin** | SELECT installations, license_states | — | no | no |
| autenticación (`get_current_user`) | misma | sí | sí | SELECT users | — | no | no |
| permiso (`require_permission`) | misma | sí | sí | SELECT user_roles, permissions | — | no | no |
| empresa (`get_company_context`) | misma | sí | sí | SELECT companies, user_scopes | — | no | no |
| documento y tipo (`_get_document`, `_get_type`) | misma | sí | sí | SELECT documents, document_types | — | no | no |
| idempotencia (si hay clave) | misma | sí | sí | SELECT idempotency | — | no | no |
| temporal, tamaño, MIME, política | misma | **sí** | **sí** | — | disco temporal | temporal | no |
| **análisis (`scanner.scan`)** | misma | **sí, 6-21 s** | **sí, `idle in transaction`** | — | **clamscan / clamd** | temporal | no |
| almacenamiento + verificación | misma | sí | sí | — | almacén | **sí** | no |
| `StoredFile`, `FileSecurityScan`, versión, documento, auditoría | misma | sí | sí | INSERT/UPDATE | — | sí | **sí** |
| `IdempotencyRecord` + `commit` | misma | sí → checkin | commit | INSERT | — | sí | sí |
| respuesta (`db.get(StoredFile)`) | misma | breve | autobegin + rollback al cerrar | SELECT | — | — | — |
