# Convención PostgreSQL-only del repositorio

`CANONICAL_PG_ONLY_MARKER`: `PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")` +
`pytest.mark.skipif(not PG, reason="… (P21)")` por prueba (`test_roles_create.py`, `test_picklist_duplicada.py`) o `pytestmark`
por módulo (`test_license_import_race.py`: «la concurrencia de la importación la gobierna PostgreSQL; SQLite no bloquea filas»;
`test_spec004_installation_race.py`; `tests/central/*_pg.py`; migraciones; `test_e2e_corrida.py`); `pytest.skip` en fixture
(`conftest_multicompany.mundo`, `test_n9_*`: «se verifica sobre PostgreSQL (P21)»). `REASON_FORMAT`: frase en español que nombra
la garantía y cita P21/la Spec. `OWNER_AUTHORITY`: la Spec dueña del contrato + P21. `COVERAGE_REQUIREMENT_FOR_SQLITE`: la
cobertura no concurrente se mantiene en los dos motores (precedentes: roles, picklist, licencias conservan sus pruebas secuenciales).
