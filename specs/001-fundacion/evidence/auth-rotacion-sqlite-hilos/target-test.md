# Prueba objetivo · `tests/test_auth_session_rotation.py::test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos`

| Registro | Valor |
|---|---|
| `THREAD_COUNT` | 2 (`threading.Thread(target=_renovar)` ×2) |
| `START_BARRIER` | ninguna: `start()` consecutivos; un `threading.Lock` solo protege `resultados.append` |
| `SESSION_FACTORY` | `sessionmaker(bind=engine, class_=Session, expire_on_commit=False)` del fixture de módulo `_app_client` |
| `SESSION_PER_THREAD` | sí: cada petición recibe su `Session` por `_override_get_db` (`factory()` … `close()`) |
| `TESTCLIENT_PER_THREAD` / `SHARED_CLIENT` | no / sí: un único `_CLIENT = TestClient(app)` de módulo, compartido por los dos hilos |
| `ENGINE` · `POOL_CLASS` · `SQLITE_URL` · `CHECK_SAME_THREAD` | `make_engine()` → `sqlite+pysqlite:///:memory:` · `StaticPool` · `check_same_thread=False` (PostgreSQL: `pg_harness.crear_motor_de_prueba`) |
| `TARGET_ENDPOINT` | `POST /api/v1/auth/refresh` con `cookies={"kontrol_refresh": cookie}` |
| `TOKEN_SOURCE` / `SESSION_SOURCE` | cookie `kontrol_refresh` de un `POST /auth/login` previo (`_login_cookie`); la sesión es la fila de `sessions` creada por ese login |
| `ASSERTIONS` | `len(resultados) == 2` · `200 in resultados` · `resultados.count(200) == 1` («dos renovaciones prosperaron: …») · `401 in resultados` |
| `EXPECTED_WINNERS` / `EXPECTED_LOSER_STATUS` | exactamente 1 / **401** |
| `FOLLOWUP_ASSERTION` | ninguna en esta prueba; la siguiente (`test_una_renovacion_fallida_no_deja_sesiones_huerfanas`) fija secuencialmente que la carrera perdida no deja sesión viva (`vivas == antes + 1`) |
| `FINAL_SESSION_STATE` | no se comprueba en la prueba objetivo (se comprueba en la POC: delta de sesiones vivas) |
| `RAISE_SERVER_EXCEPTIONS` | `TestClient(app)` por defecto → `True`: un 500 se relanza en el hilo que hizo la petición |

Docstring de la prueba: «No se "arregla" en el servidor: que la segunda falle es **correcto** con tokens de un solo uso.»
La prueba no tiene `skip`, `retry`, `sleep` ni cerrojo de serialización; el `Lock` solo protege la lista.

Nota: la firma `assert 422 == 200` citada en el encargo no pertenece a esta prueba (ninguna aserción compara con 422);
venía de otro fallo documental de la suite completa. Las firmas reales están en `failure-signatures.md`.
