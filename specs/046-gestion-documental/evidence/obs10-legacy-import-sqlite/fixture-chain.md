# Cadena de fixtures (antes)
`ENGINE_FACTORY` `make_engine()` → `SQLITE_URL` `sqlite+pysqlite:///:memory:` · `POOL` `StaticPool` · `CHECK_SAME_THREAD`
`False` · `FIXTURE_SCOPE` módulo (`_app_client`, autouse) · `DIRECT_SESSION_FACTORY` = `API_SESSION_FACTORY` = `_FACTORY`
(`sessionmaker(bind=engine, expire_on_commit=False)`) · `TESTCLIENT` único de módulo · `DEPENDENCY_OVERRIDE` `get_db` →
`factory()`/`close()` por petición · `SCANNER_MODE`: tipos con `scan_required=False`; el analizador real queda exportado
pero el legado no lo invoca (`PENDING_SCAN` declarado) · almacenamiento en disco temporal (`set_storage`).
