# Firmas · `UNKNOWN = 0`
| Firma | Observada | Dónde |
|---|---|---|
| F5 `StaleDataError: UPDATE statement on table 'legacy_document_references' expected to update 1 row(s); 0 were matched` | **7/7, determinista** (módulo ×3: 7 failed) | arnés actual: el `ROLLBACK` de la sesión auxiliar de `_actor()` sobre C1 descarta el INSERT de la referencia |
| F4 `OperationalError: database is locked` | **7/7** en Control B | conexiones propias con el ciclo de vida intacto: S-prueba sostiene el bloqueo de escritura mientras el login de `_company_id()` intenta escribir en otra conexión (5 s de `busy_timeout`) |
| F1/F2/F3/F6/F7…F12 | no | — |
