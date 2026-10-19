# Línea temporal medida (D1, carga real con clamscan, PostgreSQL de QA; ms desde el inicio de la sonda)
```
3375.6 checkout #1  → SELECT installations, license_states → rollback → checkin      (middleware de licencia, threadpool)
3378.3 checkout #1  → begin                                                         (autobegin de la sesión de get_db)
3378.4 SELECT installations, license_states                                          (require_write_allowed → get_license_mode)
3379.9 SELECT users · user_roles · permissions · companies · user_scopes ×2           (autenticación, permiso, empresa)
3384.4 SELECT documents · document_types                                             (recurso)
3403.6 scan_start   checked_out = 1                                                  ← conexión prestada, transacción abierta
9652.8 scan_end     checked_out = 1   (6,25 s)
9652.9 storage_start · 9653.2 storage_end
9654.5 INSERT stored_files · file_security_scans · SAVEPOINT · INSERT document_versions · UPDATE documents · INSERT audit_events
9663.0 commit · 9663.2 checkin
```
| Campo | Valor |
|---|---|
| SESSION_CREATED_AT | al resolver `get_db` (antes de las dependencias) |
| FIRST_CONNECTION_CHECKOUT_AT / FIRST_DB_OPERATION | 3378.3 / `SELECT installations` de `get_license_mode` (dependencia `require_write_allowed`) |
| TRANSACTION_BEGIN_AT | 3378.4 (autobegin de SQLAlchemy en la primera sentencia) |
| SCAN_START_AT / SCAN_END_AT | 3403.6 / 9652.8 |
| COMMIT_AT / CONNECTION_CHECKIN_AT | 9663.0 / 9663.2 |
| CONNECTION_HELD_DURING_SCAN | **1** (D1, D2, D3) |
| HOLD_DURATION_DURING_SCAN | 6,25 s con un análisis; p50 18,6 s con 10 concurrentes |
| SESSION_EXISTS_DURING_SCAN | 1 |
