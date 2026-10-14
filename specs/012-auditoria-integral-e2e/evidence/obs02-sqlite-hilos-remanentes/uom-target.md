# Objetivo UoM · `tests/test_uom_conversion.py::test_concurrencia_una_sola_version_abierta`

| Registro | Valor |
|---|---|
| `UOM_OWNER` / `OWNER_SOURCE` | Spec 011 (docstring; AC: «dos peticiones **simultáneas** producen una sola versión abierta», `acceptance-criteria.md` §AC de versiones; FR-011-035) |
| `UOM_FUNCTIONAL_INVARIANT` | una sola versión abierta (`valid_to IS NULL`) por presentación; lo garantiza el índice único parcial `uq_ppv_open_version` (`postgresql_where` **y** `sqlite_where` `valid_to IS NULL`: existe en los dos motores) |
| `UOM_THREAD_COUNT` · `UOM_START_BARRIER` | 2 · `threading.Barrier(2)` antes del `POST` |
| `UOM_SESSION_FACTORY` · `UOM_ENGINE` · `UOM_SQLITE_URL` · `UOM_POOL` · `CHECK_SAME_THREAD` | `sessionmaker(bind=engine, expire_on_commit=False)` del fixture de módulo `_app_client`; `make_engine()` → `sqlite+pysqlite:///:memory:` · `StaticPool` · `False` (PostgreSQL: `crear_motor_de_prueba`) |
| `TESTCLIENT_PER_THREAD` | no: `_CLIENT` de módulo compartido; una `Session` por petición (`_override_get_db`) |
| `UOM_ASSERTIONS` | **solo** `len(abiertas) == 1` sobre la base al final (mensaje con `results`); no se afirma nada sobre `results` (ni longitud ni códigos) |
| `UOM_EXPECTED_RESULTS` | contrato: una petición 200 y la otra 409 `PRESENTATION_VERSION_OVERLAP` (por `assert_no_version_overlap` si ya ve la nueva versión confirmada, o por la traducción del `IntegrityError` del índice parcial) |
| `UOM_EXPECTED_FINAL_DB_STATE` | una versión abierta (la ganadora), la anterior cerrada (`valid_to = start`) |
| Flujo del servicio (`uom_api.create_version`) | `_get_presentation` → `_get_product` → `_open_version` (SELECT, sin bloqueo) → `current.valid_to = start; flush()` (UPDATE) → `assert_no_version_overlap` (SELECT de todas las versiones) → `add(version)` → `commit()`; `IntegrityError` → rollback + 409; luego auditoría + `commit()` |
| `UOM_POSTGRES_BEHAVIOR` | las dos leen la abierta; la segunda espera en el UPDATE de la fila (bloqueo de fila) hasta el commit de la primera, vuelve a cerrar la misma fila con el mismo valor, y su INSERT choca con el índice parcial → 409; final: una abierta |

Punto crítico de arnés: la prueba acepta un vector de resultados incompleto. Si un hilo muere (500 relanzado por
`TestClient`), `results` tiene un elemento y la prueba **pasa** mientras la base tenga una sola abierta
(FR-O2-025: falso verde potencial, a medir).
