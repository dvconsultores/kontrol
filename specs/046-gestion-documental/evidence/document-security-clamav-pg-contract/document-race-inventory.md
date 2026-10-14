# Las seis carreras de `tests/test_documents_security.py` (Spec 046, T-046-106; FR-046-115)

| Prueba | Invariante | `carrera` | `esperar_bloqueados` | `pg_backend_pid` (`_pid`) | Otro SQL PG | SQLite por implementación | PG por implementación | PG por contrato | Analizador antes de la carrera | Resultado hoy sin `clamscan` |
|---|---|---|---|---|---|---|---|---|---|---|
| `test_dos_subidas_simultaneas_no_producen_dos_v2[0..2]` | una V2, una vigente, 409 `VERSION_CONFLICT` | sí | — | (dentro de `carrera`) | `pg_stat_activity` (en `_esperando_bloqueo`) | no | sí | sí | sí (`_upload` base) | 422 en `_upload` |
| `test_la_primera_version_simultanea_tampoco_da_un_500` | sin versión previa, misma regla | sí | — | sí | ídem | no | sí | sí | la subida de la carrera | 422 (KontrolError en la carrera) |
| `test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500` | la ruta HTTP que pierde recibe 409 | — | sí | sí | `pg_stat_activity` | no | sí | sí | sí | 422 |
| `test_tres_subidas_simultaneas_crean_una_sola_version` | tres a la vez, una versión | — | sí | sí | ídem | no | sí | sí | sí | 422 |
| `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora` | idempotencia por clave bajo carrera | — | sí | sí | ídem | no | sí | sí | sí | 422 |
| `test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera` | aislamiento de tenant durante la carrera | sí | — | (dentro de `carrera`) | ídem | no | sí | sí | sí | 422 |

`RACE_PATH_REACHED_WITHOUT_SCANNER = NO` (todas rechazan en la subida previa o en la de la carrera). Sexta carrera identificada
físicamente: `test_la_primera_version_simultanea_tampoco_da_un_500`.
