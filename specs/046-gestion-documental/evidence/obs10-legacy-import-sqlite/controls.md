# Controles (`controls-b-c-output.txt`, `topology-trace.txt`)
| Control | Topología | Ciclo de vida | Resultado |
|---|---|---|---|
| A · arnés actual | 1 conexión (C1) para S-prueba, S-API y S-actor | intacto | 7/7 `StaleDataError` (módulo ×3 deterministas) |
| B · `motor_para_hilos` (copia temporal) | una conexión por sesión, mismo datastore | intacto | **7/7 `database is locked`** (39 s: 5 s de espera por prueba) |
| C · `motor_para_hilos` + `company, actor = _company_id(), _actor()` antes de `db = _FACTORY()` (copia temporal) | ídem | setup sin HTTP ni sesiones auxiliares dentro de la transacción | **8/8 ×3 SQLite · 8/8 PostgreSQL** |
| PostgreSQL · arnés actual | conexión por sesión (PGLIFE) | intacto | 8/8 ×2 (el bloqueo es de fila: el login no espera a la transacción de la prueba) |
Las copias temporales (`tests/test_zz_control_*.py`) se eliminaron; árbol limpio tras los controles.
