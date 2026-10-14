# Objetivos de `tests/test_documents_security.py` (Spec 046, T-046-106) · clasificación `ENVIRONMENT_BLOCKED`

| Prueba | Mecanismo de carrera | `CLAMSCAN_REQUIRED_BEFORE_CONCURRENCY_PATH` | Estado hoy (suite SQLite completa #1 y #2 del ciclo anterior) |
|---|---|---|---|
| `test_dos_subidas_simultaneas_no_producen_dos_v2[0..2]` | `carrera(_FACTORY, …)` de `tests/concurrency.py` (`pg_backend_pid`, `pg_stat_activity`) | sí: `_upload(... base.pdf)` antes de la carrera | FAIL: `assert 422 == 200` en `_upload` (`SCAN_FAILED`: «No se pudo verificar la seguridad del archivo») |
| `test_la_primera_version_simultanea_tampoco_da_un_500` | `carrera(...)` | la subida de la propia carrera pasa por el analizador | FAIL por el mismo 422 dentro de la carrera |
| `test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500` | `_en_hilo` + `esperar_bloqueados(_FACTORY, 1, excluir=_pid(s1))` | sí | FAIL 422 en `_upload` |
| `test_tres_subidas_simultaneas_crean_una_sola_version` | `_en_hilo` ×3 + `esperar_bloqueados` + `_pid` | sí | FAIL 422 |
| `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora` | `_en_hilo` + `esperar_bloqueados` + `_pid` | sí | FAIL 422 |
| `test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera` | `carrera(...)` + `_en_hilo` | sí | FAIL 422 |

Hechos:

- El analizador real (`ClamAVScanner`: `shutil.which("clamscan")` o `KONTROL_CLAMSCAN_PATH`) no está en esta máquina;
  `upload` responde 422 `SCAN_FAILED` **antes** de cualquier concurrencia. Las 25 pruebas del módulo que suben ficheros
  fallan igual; es `ENTORNO-SIN-CLAMSCAN` (OPEN, no se absorbe). No se simula, instala ni evita el analizador para llegar
  a la carrera: sería absorber esa deuda y cambiar la semántica de seguridad (§159 de la propia suite: «un mock no sirve»).
- Aun con ClamAV, la carrera se **fuerza** con primitivas de PostgreSQL (`pg_backend_pid`, `pg_stat_activity`,
  `wait_event_type = 'Lock'`): sesiones propias de `_FACTORY` (no `TestClient` en los dos lados) y bloqueo real de
  índice/fila. Sobre SQLite esas funciones no existen: el contrato de estas pruebas es PostgreSQL por construcción
  (`conc-046-concurrent-version-delta.md`), no una carrera sobre la conexión compartida de `StaticPool`.
- Por tanto no son objetivos de OBS-02 en el sentido de la observación (hilos sobre la conexión pysqlite compartida):
  `motor_para_hilos` no les aplica y no se cambia su fixture. Clasificación: **ENVIRONMENT_BLOCKED** (+ contrato
  PostgreSQL por construcción). Observación para 046/054, no absorbida (OBS-08): el módulo no declara `skipif(not PG)`
  para estas seis pruebas; con `clamscan` presente y sin PostgreSQL fallarían por `pg_backend_pid`, no por la carrera.

`CONCURRENCY_PATH_REACHED_WITHOUT_CLAMSCAN = NO` · `CURRENT_ENV_BLOCKER = clamscan ausente` · series de frecuencia: no
se corren 20 repeticiones sin sentido (el encargo lo prohíbe); la evidencia es la de las dos suites completas del ciclo
anterior (`specs/001-fundacion/evidence/auth-rotacion-sqlite-hilos/full-suites-failed.txt`).
