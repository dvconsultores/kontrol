# Inventario · suites que crean un schema PostgreSQL entero por prueba (HEAD 805074c)

Búsqueda: `def db_session` (12 ficheros) y toda fixture de FUNCIÓN que llame a `make_engine()`. La hoja de ruta decía
«trece»: son **12 suites `db_session`** idénticas en patrón más **5 ficheros** con fixtures de función propias.

## Las 12 suites `db_session` (ámbito función; 214 pruebas)

Patrón común (byte a byte salvo la siembra): `engine = make_engine(); init_models(); Base.metadata.create_all(engine);
session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)(); [siembra]; yield; session.close()`.

| FILE | TESTS | SIEMBRA EN FIXTURE | COMMITS en pruebas | FLUSH | ROLLBACK | SECONDARY_SESSIONS (`sessionmaker`/`Session(`/`SessionLocal`) | TestClient / overrides | THREADS | DDL en prueba | SECUENCIAS | CLASSIFICATION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `test_services.py` | 6 | ninguna (las pruebas llaman `initialize`, que hace `db.commit()` en la MISMA sesión) | 0 directos (producto) | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_approvals.py` | 40 | cadena org en la sesión (`add`) | 0 | 7 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |
| `test_treasury.py` | 24 | `sembrar_empresas` + `session.commit()` | 0 | 7 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_fiscal.py` | 21 | `sembrar_empresas` + `session.commit()` | 0 | 2 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_inventory.py` | 20 | `seed_org_chain` (flush) | 0 | 7 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |
| `test_sales.py` | 11 | `seed_org_chain` | 0 | 8 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |
| `test_maestros.py` | 12 | `sembrar_empresas` + `commit` | 7 `db_session.commit()` | 3 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_homologation.py` | 17 | ninguna (`initialize` → commit en la misma sesión) | 0 directos | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_purchasing.py` | 17 | `seed_org_chain` | 0 | 13 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |
| `test_reporting.py` | 16 | `seed_org_chain` | 0 | 9 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |
| `test_licensing_central.py` | 15 | ninguna (`initialize`, `import_license`, `sync_license` → commits en la misma sesión; transporte falso) | 2 `db_session.commit()` | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | COMMIT_WITHIN_MAIN_SESSION |
| `test_regulatory.py` | 15 | `seed_org_chain` | 0 | 6 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | ROLLBACK_SAFE |

Ninguna de las 12 usa `get_bind()`, SQL crudo con schema, `engine.connect/begin`, `dependency_overrides`, `TestClient`,
hilos, DDL en prueba ni `dm._engine`. Los commits que existen (fixture, pruebas y producto) ocurren todos **en la
sesión principal de la prueba**. `USES_SECONDARY_SESSION 0` · `USES_THREAD_WITH_NEW_SESSION 0` ·
`USES_DIRECT_ENGINE_CONNECTION 0` · `OBSERVES_SEQUENCE_VALUES 0` · `REQUIRES_REAL_COMMIT_VISIBILITY 0` ·
`MODULE_SHARED_STATE 0` · **`UNKNOWN 0`**.

## Otras fixtures de FUNCIÓN que crean motor (43 pruebas; fuera del grupo principal, clasificadas aparte)

| FILE | TESTS | Por qué no entra en el grupo rollback | CLASSIFICATION |
|---|---|---|---|
| `test_installation_key_reference.py` | 9 (2 solo PG) | `TestClient` con `dependency_overrides` y `dm._engine`/`_SessionLocal`: sesiones secundarias del arranque/reverificación | USES_SECONDARY_SESSION → SCHEMA_PER_TEST_EXCEPTION |
| `central/test_central_authority.py` | 20 | otra `Base` (Autoridad Central), `TestClient` y conftest propio (`factoria`) | USES_SECONDARY_SESSION → SCHEMA_PER_TEST_EXCEPTION |
| `test_license_import_race.py` | 4 (solo PG) | hilos con sesión propia y commits reales en carrera | USES_THREAD_WITH_NEW_SESSION → SCHEMA_PER_TEST_EXCEPTION |
| `test_license_revision_race.py` | 4 (solo PG) | ídem | USES_THREAD_WITH_NEW_SESSION → SCHEMA_PER_TEST_EXCEPTION |
| `test_volumen_de_instalacion_ambito.py` | 6 (1 crea motor) | prueba del arnés del volumen; una sola creación | ROLLBACK_SAFE pero fuera de alcance (1 schema) |

Los ~35 mundos de **módulo** (`_app_client`/`_mundo`) ya crean un schema por módulo: no son parte de esta deuda.

## Secuencias

`grep Sequence(|Identity(|autoincrement=True` en `app/` → **0**; el schema del arnés tiene **0 secuencias** (`pg_sequences`).
Las claves primarias son cadenas (UUID/códigos). `SEQUENCE_ISOLATION_CONTRACT`: **no hay secuencias que aislar** (probado,
`relations-per-schema.md`).
