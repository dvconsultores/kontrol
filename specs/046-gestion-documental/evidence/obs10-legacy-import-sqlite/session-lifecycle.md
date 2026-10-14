# Línea de tiempo (antes) · `topology-trace.txt` (Control A, un solo id de conexión C1)
1. `db = _FACTORY()` (S-prueba, C1). 2. `_doc_type(db)` → `_company_id()` → **HTTP** login (S-API en C1: `INSERT audit_events`,
`COMMIT` → confirma también lo pendiente de S-prueba) y companies (`ROLLBACK` al cerrar) → `db.add(doc_type); flush()` (INSERT
sin confirmar). 3. `_reference(db, …)` → `_company_id()` de nuevo → **HTTP** (`COMMIT` + `ROLLBACK` en C1) → `db.add(reference);
flush()` (INSERT sin confirmar). 4. `actor=_actor()` → **sesión auxiliar** en C1, `close()` → `ROLLBACK`: **descarta el INSERT
de la referencia**. 5. `import_legacy_reference` → `reference.classification = …; db.flush()` → `UPDATE legacy_document_references`
→ 0 filas → `StaleDataError`.
`SESSION_OPEN_ACROSS_HTTP` = sí · `TRANSACTION_OPEN_ACROSS_HTTP` = sí · `PENDING_WRITE_ACROSS_HTTP` = sí (doc_type y
referencia) · `SAME_CONNECTION_CURRENTLY` = sí (C1 para todo) · `SAME_DATASTORE_IF_ISOLATED` = sí (`motor_para_hilos`).
