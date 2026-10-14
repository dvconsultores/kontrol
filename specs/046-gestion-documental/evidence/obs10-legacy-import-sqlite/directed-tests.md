# Pruebas dirigidas O10-01…20 (`directed-series-after.txt`; analizador real exportado)
| Id | Qué | Resultado |
|---|---|---|
| O10-01 | inventario exacto: 7 nodos de 8 | `seven-node-inventory.md` |
| O10-02 | invariantes ligadas a FR-046-112/113, §144 | `functional-contract.md` |
| O10-03 | topología actual: C1 para S-prueba, S-API y S-actor | `topology-trace.txt` |
| O10-04 | fallo base reproducido 3/3 (`StaleDataError`) y explicado | `session-lifecycle.md` |
| O10-05 | control de conexiones propias (B): 7× `database is locked`; mismo datastore | `controls.md` |
| O10-06 | control de ciclo de vida (C): 8/8 ×3 SQLite, 8/8 PostgreSQL | `controls.md` |
| O10-07 | aserciones del legado intactas (contrato estático) | PASS |
| O10-08 | `GET /descargar` → 409 `FILE_NOT_SCANNED` | PASS |
| O10-09 / O10-10 / O10-11 | estado final, empresa, metadatos del legado | PASS (aserciones originales) |
| O10-12 | analizador real exportado; el legado declara `PENDING_SCAN` sin analizar | PASS |
| O10-13 | sin hilos en el módulo; excepciones no ocultas | n/a (sin hilos) |
| O10-14…17 | ACS, UoM, auth, almacenes (+ contratos de carreras y CLAM) | 101 passed + 1 skip |
| O10-18 | PostgreSQL: módulo ×3 8/8 + contrato; documentos + seguridad + n9 65/65 | PASS |
| O10-19 / O10-20 | producto 0 · migración/esquema 0 | `git diff -- app/ alembic/` vacío |
Series: siete objetivos ×3 solos 21/21 · módulo ×10 10/10 (12 pruebas) · PostgreSQL módulo ×3 3/3.
