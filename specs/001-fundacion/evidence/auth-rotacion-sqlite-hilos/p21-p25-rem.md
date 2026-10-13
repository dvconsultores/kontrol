# P21 · P25 · REM-AUTH-ROUTE-CRAWL-001

| Registro | Valor |
|---|---|
| `P21_SOURCE` | `.specify/memory/constitution.md` § Principio 21 — Paridad del motor de persistencia |
| `P21_EXACT_MEANING` | «La evidencia de calidad solo es válida sobre el motor de persistencia de producción … PostgreSQL es obligatorio en desarrollo integrado, pruebas de integración y contrato, E2E, QA, staging y producción; cualquier excepción es explícita, declarada y acotada a pruebas que no ejercitan el dialecto.» |
| `P21_MAKES_POSTGRESQL_INTEGRATION_AUTHORITY` | **YES** |
| `P25_SOURCE` | constitución § Principio 25 — Las altas concurrentes las gobierna la base (enmienda E-05, 2026-09-13) |
| `P25_EXACT_MEANING` | «Una prueba de concurrencia **fuerza** la carrera y demuestra que ocurrió; nunca acepta un error 500, un `IntegrityError` ni una excepción arbitraria como rechazo válido.» |
| `P25_RELEVANCE` | la prueba objetivo no fuerza la carrera (dos `start()` seguidos, sin barrera) y un 500 relanzado por `TestClient` mata el hilo: la aserción visible es «faltan resultados», no «hubo un 500» |
| REM-AUTH-ROUTE-CRAWL-001 | `docs/remediation/route-crawl-auth-closeout.md` + `route-crawl-auth-owner.md`: el cliente comparte una sola renovación en vuelo; el servidor bloquea la fila (`with_for_update`) para que la segunda espere y reciba 401; certificado sobre PostgreSQL 18.6 (28/28 ×3) |
| Precedente PostgreSQL-only por `with_for_update` | `tests/test_license_import_race.py` y `test_spec004_installation_race.py`: «en SQLite `with_for_update` no hace nada, así que este fichero solo corre con `KONTROL_TEST_DB_URL`» (`pytestmark = skipif`) |
