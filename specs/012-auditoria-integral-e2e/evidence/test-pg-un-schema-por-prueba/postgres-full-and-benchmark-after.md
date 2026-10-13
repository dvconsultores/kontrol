# Suite completa PostgreSQL (W35) y benchmark DESPUÉS (W36/W37) · misma orden y mismo contador que ANTES

```
[CATALOGO ANTES] pg_class=114688 pg_attribute=466944 pg_depend=106496 pg_index=32768 pg_constraint=24576 pg_attrdef=0 pg_type=122880 pg_total(pg_class+attribute+depend)=96092160 base_total=150925795 schemas_t_=0 pg_class_filas=413
[PGS-CONTADOR] schemas_creados=188 schemas_soltados=188 bases_soltadas=17 conexiones_cortadas=0 residuos=0 duracion_s=780.2
rc=1
[TIME] wall=809.991057413 s
[CATALOGO DESPUES] pg_class=114688 pg_attribute=466944 pg_depend=106496 pg_index=32768 pg_constraint=24576 pg_attrdef=0 pg_type=122880 pg_total(pg_class+attribute+depend)=96092160 base_total=151458275 schemas_t_=0 pg_class_filas=413
passed=2600 failed=37 skipped=28
```

Referencia (ciclo anterior): 38 / 2584 / 28. Diferencia: **+15 pasadas** (las 15 PGS) **+1** (el intermitente temporal conocido de `test_licensing_central` hoy pasa); omitidas **28 = 28**.

| Clase | Nº | Detalle |
|---|---|---|
| BASELINE · ENTORNO-SIN-CLAMSCAN | 35 | `test_documents` 10, `test_documents_security` 25 |
| BASELINE · `test_n9_integrity` | 2 | en la base |
| TARGET_REGRESSION | **0** | las 12 suites reescritas 214/214 con 12 schemas; PGLIFE: residuos 0, conexiones cortadas 0 |
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
FAILED tests/test_n9_integrity.py::test_el_binario_ausente_tampoco_se_entrega_en_silencio
FAILED tests/test_n9_integrity.py::test_un_objeto_alterado_no_se_entrega_como_si_nada
```

## Benchmark ANTES → DESPUÉS (suite completa, carga comparable: mismas 2 650 pruebas + 15 PGS)

| METRIC | BEFORE | AFTER | DELTA | DELTA % |
|---|---|---|---|---|
| SCHEMAS_CREATED | 384 | **188** | −196 | **−51,0 %** |
| SCHEMAS_DROPPED | 384 | 188 | −196 | −51,0 % |
| CREATE_ALL_CALLS | 384 | 188 | −196 | −51,0 % |
| RELATIONS_CREATED_ESTIMATE (× 841) | 322 944 | **158 108** | −164 836 | −51,0 % |
| RELATIONS_DROPPED_ESTIMATE | 322 944 | 158 108 | −164 836 | −51,0 % |
| TOTAL_DURATION (pared) | 929,8 s | **810,0 s** | −119,8 s | **−12,9 %** |
| Duración dentro de pytest | 895,8 s | 780,2 s | −115,6 s | −12,9 % |
| CATALOG `pg_class` / `pg_attribute` / `pg_depend` (`pg_relation_size`, antes→después de cada corrida) | 114 688 / 466 944 / 106 496 → iguales | iguales | 0 | 0 % |
| `pg_total(pg_class+pg_attribute+pg_depend)` | 96 092 160 → 96 092 160 | 96 092 160 → 96 092 160 | 0 | 0 % (marca de agua ya alcanzada; reutilizable) |
| Tamaño de la base (`pg_database_size`) durante la corrida | +139 KB | +532 KB | — | ruido de `autovacuum` |
| RESIDUAL_SCHEMAS | 0 | 0 | 0 | — |

Las 188 restantes: ~35 mundos de módulo, 43 de las fixtures de función excluidas con razón (sesiones secundarias, hilos), 13 de las 12 suites + PGS, sondas de PGLIFE y de este ciclo, y el resto de módulos que crean motor una vez.

**Veredicto de rendimiento: MATERIAL_IMPROVEMENT** — la mitad de los schemas y de las relaciones DDL de cada corrida (−196 schemas, −164 836 relaciones) y −120 s de pared (−12,9 %) sin tocar producto ni relajar el aislamiento. El catálogo no cambia porque la marca de agua ya estaba alcanzada: `TEST-PG-CATALOGO-MARCA-DE-AGUA` sigue OPEN (solo se midió).
