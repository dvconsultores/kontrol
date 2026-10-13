# P21 / P25 · texto vigente (`.specify/memory/constitution.md`)

**Principio 21 — Paridad del motor de persistencia.** «La evidencia de calidad solo es válida sobre el motor de
persistencia de producción. Ninguna función se declara terminada con evidencia obtenida sobre un motor distinto del que
operará el cliente. PostgreSQL es obligatorio en desarrollo integrado, pruebas de integración y contrato, E2E, QA, staging y
producción; cualquier excepción es explícita, declarada y acotada a pruebas que no ejercitan el dialecto.»

**Principio 25 — Las altas concurrentes las gobierna la base.** «… Una prueba de concurrencia **fuerza** la carrera y
demuestra que ocurrió; nunca acepta un error 500, un `IntegrityError` ni una excepción arbitraria como rechazo válido.»

| Registro | Valor |
|---|---|
| `P21_SOURCE` | `.specify/memory/constitution.md` § Principio 21 |
| `P21_EXACT_SEMANTIC` | la evidencia válida es la de PostgreSQL; SQLite es una excepción acotada a pruebas que no ejercitan el dialecto |
| `DOES_IT_EXCLUDE_SQLITE_CONCURRENCY_CONTRACT` | **NO**: P21 no prohíbe correr la prueba en SQLite; la prueba de concurrencia corre en los dos motores y la evidencia que cuenta es la de PostgreSQL. P25 exige que la carrera se fuerce y que no se acepte un 500: un 500 en SQLite por un defecto del **arnés** (conexión compartida) es un falso rojo que P25 ordena no aceptar y, por tanto, corregir donde está |
| Marca canónica PostgreSQL-only | `solo_pg = pytest.mark.skipif("postgresql" not in PG_URL, …)` (`test_pg_harness_lifecycle.py`); no se usa aquí: la causa es del arnés SQLite, no del contrato |
