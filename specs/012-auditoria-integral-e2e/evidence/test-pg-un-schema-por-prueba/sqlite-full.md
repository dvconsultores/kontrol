# Suite completa SQLite (W34) · `pytest tests -q -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, sin `KONTROL_TEST_DB_URL`

```
passed=1582 failed=43 skipped=1040 errors=0 · rc=1
[PGS-CONTADOR] schemas_creados=0 schemas_soltados=0 bases_soltadas=0 conexiones_cortadas=0 residuos=0 duracion_s=218.9
```

Referencia (ciclo anterior): 43 / 1567 / 1040. Diferencia: **+15 pasadas** = las 15 pruebas PGS; omitidas **1040 = 1040** (ningún `skip` nuevo); 0 schemas (SQLite no crea ninguno: semántica intacta).

| Clase | Nº | Detalle |
|---|---|---|
| BASELINE · ENTORNO-SIN-CLAMSCAN | 42 | `test_documents` 10, `test_documents_legacy_import` 7, `test_documents_security` 25 |
| KNOWN_INTERMITTENT | 1 | `test_warehouse_structure::test_concurrencia_de_codigo_resuelta_por_constraint` (ALMACENES-CARRERA-SQLITE-HILOS; en la base) |
| BASELINE que hoy pasa | 1 | `test_auth_session_rotation::test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos` (intermitente de hilos; no se reclama) |
| TARGET_REGRESSION | **0** | las 12 suites reescritas: 214/214 |
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
FAILED tests/test_documents_legacy_import.py::test_binario_localizable_y_verificable_se_importa
FAILED tests/test_documents_legacy_import.py::test_lo_importado_no_se_entrega_hasta_verificarse
FAILED tests/test_documents_legacy_import.py::test_un_archivo_que_no_esta_se_reporta_no_se_inventa
FAILED tests/test_documents_legacy_import.py::test_un_hash_suelto_sigue_sin_ser_un_documento
FAILED tests/test_documents_legacy_import.py::test_una_huella_que_no_coincide_detiene_la_importacion
FAILED tests/test_documents_legacy_import.py::test_una_ruta_heredada_no_autoriza_a_salir_del_volumen
FAILED tests/test_documents_legacy_import.py::test_una_url_externa_no_se_importa_como_archivo_propio
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
FAILED tests/test_warehouse_structure.py::test_concurrencia_de_codigo_resuelta_por_constraint
```
