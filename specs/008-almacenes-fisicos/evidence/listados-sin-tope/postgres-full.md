# Suite completa PostgreSQL (W33) · `KONTROL_TEST_DB_URL=postgresql+psycopg2://***@localhost:55432/ktest pytest tests -q -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`

```
passed=2625 failed=38 skipped=28 errors=0 · rc=1 · schemas t_ residuales de la suite: 0 (los 2 que había los dejó el guion de medición; purgados) · arnés por módulo intacto
```

Referencia (ciclo anterior): 37 / 2600 / 28. Diferencia: **+25 pasadas** (las pruebas LT en PostgreSQL) y **+1 fallo** = el intermitente temporal conocido; omitidas **28 = 28**.

| Clase | Nº | Detalle |
|---|---|---|
| BASELINE · ENTORNO-SIN-CLAMSCAN | 35 | `test_documents` 10, `test_documents_security` 25 |
| BASELINE · `test_n9_integrity` | 2 | en la base |
| KNOWN_INTERMITTENT | 1 | `test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event`: `last_reliable_date` 15:03:32 ≠ `SERVER_TIME` 15:03:01 (dependencia temporal conocida de ciclos anteriores); **PASSED ×3 dirigido** después de la suite; no toca listados |
| TARGET_REGRESSION | **0** | LT 25/25, WHL, estructura, picking 031/032, duplicada, OpenAPI verdes |
| NEW_INDEPENDENT_DEBT · UNKNOWN | 0 · **0** | — |

```
FAILED tests/test_documents.py::test_borrado_protegido_y_archivado_conserva_binario
FAILED tests/test_documents.py::test_el_mismo_archivo_dos_veces_no_se_deduplica_ni_se_bloquea
FAILED tests/test_documents.py::test_el_nombre_del_usuario_nunca_es_ruta
FAILED tests/test_documents.py::test_subida_idempotente
FAILED tests/test_documents.py::test_subida_valida_calcula_hash_en_servidor
FAILED tests/test_documents.py::test_una_version_referenciada_no_se_purga
FAILED tests/test_documents.py::test_version_congelada_el_historico_no_se_reinterpreta
FAILED tests/test_documents.py::test_versionado_sin_sobrescritura
FAILED tests/test_documents.py::test_vinculacion_y_documento_compartido
FAILED tests/test_documents.py::test_vinculo_congelado_no_se_desvincula
FAILED tests/test_documents_security.py::test_amz_01_recorrido_de_rutas
FAILED tests/test_documents_security.py::test_amz_05_xss_por_nombre_de_archivo
FAILED tests/test_documents_security.py::test_amz_12_clave_de_almacenamiento_opaca
FAILED tests/test_documents_security.py::test_amz_13_sin_sobrescritura_del_historico
FAILED tests/test_documents_security.py::test_amz_14_el_hash_no_autoriza
FAILED tests/test_documents_security.py::test_amz_15_asignacion_masiva
FAILED tests/test_documents_security.py::test_amz_17_desvinculacion_no_autorizada
FAILED tests/test_documents_security.py::test_amz_19_inyeccion_de_cabeceras
FAILED tests/test_documents_security.py::test_amz_20_los_registros_no_filtran_contenido
FAILED tests/test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2[0]
FAILED tests/test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2[1]
FAILED tests/test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2[2]
FAILED tests/test_documents_security.py::test_el_contrato_nunca_expone_almacenamiento
FAILED tests/test_documents_security.py::test_fallo_de_escritura_no_deja_version
FAILED tests/test_documents_security.py::test_huella_distinta_no_se_entrega
FAILED tests/test_documents_security.py::test_la_misma_clave_en_carrera_devuelve_la_version_ganadora
FAILED tests/test_documents_security.py::test_la_misma_clave_en_otro_documento_no_devuelve_una_version_ajena
FAILED tests/test_documents_security.py::test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500
FAILED tests/test_documents_security.py::test_la_primera_version_simultanea_tampoco_da_un_500
FAILED tests/test_documents_security.py::test_objeto_ausente_no_se_entrega_otra_cosa
FAILED tests/test_documents_security.py::test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera
FAILED tests/test_documents_security.py::test_pendiente_de_analisis_no_se_entrega
FAILED tests/test_documents_security.py::test_subidas_a_documentos_distintos_no_se_esperan
FAILED tests/test_documents_security.py::test_tres_subidas_simultaneas_crean_una_sola_version
FAILED tests/test_documents_security.py::test_un_reintento_devuelve_la_version_de_su_clave_aunque_haya_otra_despues
FAILED tests/test_licensing_central.py::TestSincronizacion::test_sync_success_records_run_snapshot_and_event
FAILED tests/test_n9_integrity.py::test_el_binario_ausente_tampoco_se_entrega_en_silencio
FAILED tests/test_n9_integrity.py::test_un_objeto_alterado_no_se_entrega_como_si_nada
```

## Intermitente, dirigido ×3

```
.                                                                        [100%] ← corrida 1
.                                                                        [100%] ← corrida 2
.                                                                        [100%] ← corrida 3
```
