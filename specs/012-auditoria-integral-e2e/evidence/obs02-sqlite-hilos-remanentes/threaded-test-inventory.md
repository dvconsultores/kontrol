# Inventario completo de pruebas con hilos (backend) · `UNKNOWN = 0`

Búsqueda: `threading.(Thread|Barrier|Event)`, `ThreadPoolExecutor`, `concurrent.futures`, `asyncio.to_thread` en `tests/`
cruzada con `make_engine`, `sesion_de_prueba`, `motor_para_hilos`, `TestClient`, `skipif`, `conftest_multicompany`,
`tests.concurrency.carrera` (carreras forzadas con `pg_backend_pid`/`pg_stat_activity`: solo PostgreSQL por construcción).

| Fichero | Prueba(s) con hilos | Dominio / dueña funcional | Motor en SQLite | Hilos · sesión por hilo | Clasificación | Razón |
|---|---|---|---|---|---|---|
| `tests/test_uom_conversion.py` | `test_concurrencia_una_sola_version_abierta` | UoM · **Spec 011** (docstring del módulo; `specs/011-unidades-presentaciones`) | `make_engine()` → `:memory:` + `StaticPool` + `TestClient` compartido | 2 · sí (`get_db` por petición) | **KNOWN_OBS02_TARGET** | única carrera que corre en SQLite sobre la conexión compartida |
| `tests/test_documents_security.py` | `test_dos_subidas_simultaneas_no_producen_dos_v2[0..2]`, `test_la_primera_version_simultanea_tampoco_da_un_500`, `test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500`, `test_tres_subidas_simultaneas_crean_una_sola_version`, `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora`, `test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera` | Gestión documental · **Spec 046** (docstring: «Spec 046, T-046-106») | `make_engine()` + `TestClient`; pero la carrera se fuerza con `carrera()`/`esperar_bloqueados()`/`_pid()` (`pg_backend_pid`, `pg_stat_activity`) | 1 hilo + sesión principal; sesiones propias (`_FACTORY`) | **ENVIRONMENT_BLOCKED** (+ PostgreSQL por construcción) | hoy fallan en `_upload` con 422 `SCAN_FAILED` (sin `clamscan`, `ENTORNO-SIN-CLAMSCAN`) antes de llegar a la carrera; aun con ClamAV, el mecanismo de carrera es exclusivo de PostgreSQL |
| `tests/test_auth_session_rotation.py`, `tests/test_auth_rotacion_atomica.py` | renovaciones simultáneas; SA-01/02 | Seguridad/sesiones · 002 (en 001) | `motor_para_hilos` | 2 · sí | THREADED_BUT_ALREADY_ISOLATED | ciclo anterior |
| `tests/test_warehouse_structure.py` | `test_concurrencia_de_codigo_resuelta_por_constraint` | Almacenes · 008 | `motor_para_hilos` | 2 · sí | THREADED_BUT_ALREADY_ISOLATED | `ALMACENES-CARRERA-SQLITE-HILOS` |
| `tests/test_motor_para_hilos.py` | ACS-01…08 | arnés · 054 | `motor_para_hilos` | 2 | THREADED_BUT_ALREADY_ISOLATED | la primitiva misma |
| `tests/test_roles_create.py` | carrera de 12 hilos | 001 | `skipif(not PG)` en la prueba | 12 | POSTGRES_ONLY | precedente; no se toca |
| `tests/test_picklist_duplicada.py` | PL-11/12/14 | 031 | `skipif(not PG)` | n | POSTGRES_ONLY | precedente; no se toca |
| `tests/test_spec030_concurrency.py`, `test_spec031_picking.py`, `test_spec032_picking_execution.py`, `test_spec033_confirmation.py`, `test_spec034_billing.py`, `test_spec035_dispatch.py`, `test_spec047_notifications.py`, `test_spec047_scheduler.py` | carreras de pedidos/picking/facturación/despacho/notificaciones/scheduler | 030–035, 047 | fixture `mundo` de `conftest_multicompany`: `pytest.skip` sin PostgreSQL («el aislamiento multiempresa se verifica sobre PostgreSQL (P21)») | varios | POSTGRES_ONLY | no corren en SQLite |
| `tests/central/test_central_authority_pg.py`, `test_central_challenge_rate_limit_pg.py`, `test_central_sync_auth_pg.py` | carreras de la autoridad central | 010/licencias | `pytestmark skipif(not PG)` | varios | POSTGRES_ONLY | — |
| `tests/test_license_import_race.py`, `tests/test_license_revision_race.py`, `tests/test_spec004_installation_race.py` | carreras de licencia/instalación | 004/010 | `pytestmark skipif(not PG)` | 2–3 | POSTGRES_ONLY | «en SQLite `with_for_update` no hace nada» |
| `tests/test_spec022_migration_0048.py`, `tests/test_spec023_migration_0046.py`, `tests/test_e2e_corrida.py` | hilos auxiliares (migraciones, corrida E2E) | 022/023/054 | `pytestmark skipif(not PG)` | 1–2 | POSTGRES_ONLY | — |
| `tests/concurrency.py` | ayudante `carrera`/`esperar_bloqueados` | arnés · 054 | n/a (PostgreSQL: `pg_backend_pid`) | 1 | NOT_RELEVANT (ayudante) | no es una prueba |

Totales: ficheros con hilos 26 · KNOWN_OBS02_TARGET **1** (UoM) · ENVIRONMENT_BLOCKED 1 familia (6 pruebas de 046) ·
THREADED_BUT_ALREADY_ISOLATED 4 · POSTGRES_ONLY 19 · NOT_RELEVANT 1 · UNKNOWN **0**.
