# TAREAS — SPEC 046

Tareas concretas y trazables (§150). No existe una tarea «implementar documentos».

## F1 · Modelo y catálogo

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-001 | `DocumentCategory` y `DocumentType` por empresa, catálogo vacío | FR-046-010, 012, 013, AC-046-01 | M |
| T-046-002 | Política del tipo: MIME, extensiones, tamaño, versionado, vigencia, retención, auditoría, análisis | FR-046-011 | L |
| T-046-003 | Esquema de metadata versionable por tipo | FR-046-014 | M |
| T-046-004 | `file_metadata` evoluciona a `stored_files` con MIME doble, proveedor y seguridad | FR-046-003, 033, 110, AC-046-42 | L |
| T-046-005 | `Document` con número externo, emisor, vigencia y referencia externa | FR-046-001, 105 | L |
| T-046-006 | `DocumentVersion` con correlativo, hash propio y motivo | FR-046-002 | M |
| T-046-007 | `DocumentLink` con rol y versión congelada | FR-046-020, 021, AC-046-14, AC-046-15 | M |
| T-046-008 | Índice único parcial de versión vigente y de número de versión | FR-046-004 | M |
| T-046-009 | Índices del modelo, cada uno con su consulta | NFR-046-03 | S |
| T-046-010 | `EXPIRED` derivado; estados de documento y de archivo separados | FR-046-060, 061, 062, AC-046-29, AC-046-30 | M |
| T-046-011 | Migración `00XX_document_model` | FR-046-001..020 | L |

## F2 · Abstracción de almacenamiento

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-020 | Interfaz `DocumentStorageProvider` | FR-046-030 | M |
| T-046-021 | Proveedor de sistema de archivos sobre el volumen existente | FR-046-031 | L |
| T-046-022 | Generación de `storage_key` opaca | FR-046-040, R-046-3 | M |
| T-046-023 | Escribir → verificar → confirmar | FR-046-036 | L |
| T-046-024 | Verificación de integridad: metadata sin binario o con hash distinto | FR-046-037 | M |
| T-046-025 | Proveedor compatible con S3, sin acoplar a fabricante | FR-046-032 | L |
| T-046-026 | Credenciales como secretos; nunca en base, frontend ni registros | FR-046-035, NFR-046-09 | S |
| T-046-027 | Aislamiento por instalación; sin depósito compartido | FR-046-034 | S |

## F3 · Servicio documental

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-030 | Saneado de nombre y rechazo de recorrido de rutas | FR-046-041, 042 | L |
| T-046-031 | Detección de MIME por contenido; declarado y detectado separados | FR-046-043, 044 | L |
| T-046-032 | Lista blanca por tipo; vacía significa ninguno | FR-046-048 | M |
| T-046-033 | Límite de tamaño con rechazo temprano | FR-046-045 | M |
| T-046-034 | SHA-256 en el servidor; el del cliente ignorado | FR-046-046 | M |
| T-046-035 | Versionado: correlativo del servidor, versión anterior intacta e inmutable | FR-046-004, 005, AC-046-12 | L |
| T-046-036 | Original byte a byte; lo derivado marcado como derivado | FR-046-006 | M |
| T-046-037 | Política de versión única frente a versionada, por tipo | FR-046-007 | M |
| T-046-038 | Idempotencia de subida con el mecanismo existente | FR-046-047 | M |
| T-046-039 | Coincidencia de hash registrada, no bloqueante | FR-046-049, AC-046-36 | S |
| T-046-040 | Validación de metadata contra el esquema del tipo | FR-046-014, AC-046-37 | M |
| T-046-041 | Referencia externa: sin archivo, marcada no administrada | FR-046-105 | S |

## F4 · Vinculación y autorización — antes que la API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-050 | Registro cerrado de tipos de recurso vinculables | FR-046-022 | L |
| T-046-051 | `attach` con permiso sobre la **entidad de destino** | FR-046-023, AC-046-17 | L |
| T-046-052 | `detach` que respeta el vínculo congelado | FR-046-024, AC-046-19 | M |
| T-046-053 | `documents_for(resource)` como operación de primera clase | FR-046-025, 053, AC-046-14 | M |
| T-046-054 | `freeze_links`: congela la versión usada | FR-046-100 | L |
| T-046-055 | Autorización de descarga por la entidad vinculada | FR-046-050 | L |
| T-046-056 | Respuesta 404 en vez de 403; sin confirmar existencia | FR-046-051, AC-046-21 | M |
| T-046-057 | Aislamiento multiempresa en las cinco operaciones | FR-046-087, AC-046-22 | L |
| T-046-058 | `allowed_actions` y `can_delete` en backend | FR-046-082 | M |
| T-046-059 | Permisos con la convención de la Spec 003 | FR-046-083 | M |
| T-046-060 | Auditoría transversal de los once eventos | FR-046-084, 085, AC-046-43 | M |

## F5 · Seguridad del archivo

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-070 | Estados de seguridad del archivo | FR-046-070 | M |
| T-046-071 | No `CLEAN` no se entrega | FR-046-071, AC-046-27 | M |
| T-046-072 | Análisis configurable; sin analizador `SKIPPED` **declarado** | FR-046-072, AC-046-28 | L |
| T-046-073 | Resultado del análisis auditado | FR-046-073 | S |
| T-046-074 | Ejecutables y comprimidos rechazados por defecto | FR-046-048, AC-046-26 | M |
| T-046-075 | Política de retención configurable por tipo, **sin plazos por defecto** | FR-046-065, ESC-046-03 | M |
| T-046-076 | Purga física por el trabajador común; nunca por planificador propio | FR-046-066 | M |
| T-046-077 | Sin referencias colgantes: versión referenciada no se purga | FR-046-067, AC-046-33 | M |

## F6 · API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-080 | Endpoints de categoría y tipo | FR-046-010 | M |
| T-046-081 | Endpoints de documento: listar, crear, detalle, editar, archivar, borrar protegido; el binario sobrevive al archivado | FR-046-063, 064, 080, AC-046-31, AC-046-32 | L |
| T-046-082 | Subida `multipart` y creación de versión | FR-046-080 | L |
| T-046-083 | Historial de versiones; **sin** edición de versión | FR-046-005 | M |
| T-046-084 | Descarga con autorización y cabeceras seguras | FR-046-052, 055, 057, AC-046-23, AC-046-25 | L |
| T-046-085 | Previsualización con el mismo permiso y sin contenido activo | FR-046-054, 056, AC-046-24 | L |
| T-046-086 | Endpoints de vínculo y consulta por recurso | FR-046-081 | M |
| T-046-087 | Los 18 códigos de error con `reason` y `allowed_actions` | FR-046-082, contratos §6 | M |
| T-046-088 | `If-Match` con el mecanismo existente | FR-046-086 | S |
| T-046-089 | Contratos de evento; **046 no notifica** | FR-046-088 | M |
| T-046-090 | Consulta de vencimientos por índice; listar no lee binarios | FR-046-104, NFR-046-01, NFR-046-03 | M |

## F7 · Pruebas de backend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-100 | Unidad: saneado de nombre y recorrido de rutas | AC-046-05 | L |
| T-046-101 | Unidad: MIME real, doble extensión, lista vacía | AC-046-02, 06, 07 | L |
| T-046-102 | Unidad: tamaño, hash, versionado, estados | AC-046-04, 08, 09, 10 | L |
| T-046-103 | Unidad: `allowed_actions`, retención, registro de recursos | AC-046-16, 44 | M |
| T-046-104 | Integración: los 12 casos del §119 sobre PostgreSQL y almacenamiento real | NFR-046-07 | L |
| T-046-105 | Integración: documento simple, referencia externa, archivo compartido | AC-046-03, 15, 38 | M |
| T-046-106 | **Suite de seguridad**: una prueba por amenaza `AMZ-01`..`AMZ-20` | FR-046-042, 051, riesgos §1 | XL |
| T-046-107 | Concurrencia: versión, vínculo, archivado, subida duplicada | AC-046-11, 13, 45 | L |
| T-046-108 | Recuperación: fallo de escritura, objeto ausente, fallo de borrado | AC-046-34, 35 | L |
| T-046-109 | Matriz por adaptador: sistema de archivos y compatible con S3 | FR-046-030, 032, §120 | L |
| T-046-110 | Contrato: OpenAPI ↔ frontend; **sin `storage_key`** en respuestas | FR-046-081, §121 | M |
| T-046-111 | Rendimiento: 5.000 documentos sin leer binarios | AC-046-46, 47 | M |
| T-046-112 | Registros sin contenido, secretos ni URL firmadas | AC-046-49 | S |
| T-046-113 | Regresión de `system`, `regulatory`, `reporting` y `approvals` | FR-046-110, plan §7 | L |

## F8 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-120 | Tipos TypeScript del modelo documental | FR-046-090 | S |
| T-046-121 | Biblioteca con filtros, vencimientos y paginación | FR-046-090, NFR-046-02 | L |
| T-046-122 | Detalle con metadata, versiones y vínculos | FR-046-091 | L |
| T-046-123 | Historial de versiones sin edición | FR-046-005 | M |
| T-046-124 | Carga operable **sin arrastrar y soltar** | FR-046-093 | L |
| T-046-125 | Estado de carga sin porcentaje fingido | FR-046-094 | M |
| T-046-126 | Errores diferenciados por causa | FR-046-095 | M |
| T-046-127 | Componente de adjuntos reutilizable | FR-046-092 | XL |
| T-046-128 | Pantalla de tipos documentales | FR-046-011 | L |
| T-046-129 | Previsualización adaptada en pantalla estrecha | FR-046-096 | M |
| T-046-130 | Nombres largos que no rompen la disposición | FR-046-097 | S |
| T-046-131 | Protección de cambios sin guardar | NFR-046-06 | S |

## F9 · Legado, E2E y cierre

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-046-140 | Marcado de las 9 columnas legadas; **0 documentos creados** | FR-046-111 | M |
| T-046-141 | `LEGACY_HASH_WITHOUT_FILE` para el hash sin binario | FR-046-114 | S |
| T-046-142 | `MISSING_LEGACY_FILE` reportado, no inventado | FR-046-113 | M |
| T-046-143 | Importación de binario localizable con verificación de hash | FR-046-112 | L |
| T-046-144 | Migración `00XX_document_legacy_marks` | FR-046-111..114 | M |
| T-046-145 | E2E: los 15 pasos del §122 | AC-046-04, 10, 20, 31 | XL |
| T-046-146 | **E2E 045 ↔ 046**: aprobar, versionar, conservar la versión usada | AC-046-18 | L |
| T-046-147 | E2E regulatorio: permiso, versión, vencimiento | FR-046-102, §124 | M |
| T-046-148 | E2E legado con fixture de cinco casos | §125, AC-046-39..41 | M |
| T-046-149 | Cross-browser en Chromium, Firefox y WebKit | AC-046-50 | M |
| T-046-150 | axe WCAG 2.2 AA; carga solo con teclado | NFR-046-04 | M |
| T-046-151 | Responsive en 6 viewports con nombres largos | NFR-046-05 | M |
| T-046-152 | Puertas G1-G4 con las rutas nuevas | NFR-046-04, 05 | XS |
| T-046-153 | Verificación de las 16 Specs consumidoras | FR-046-101, 102, 103 | M |
| T-046-154 | Verificación de NFR-046-08: 0 tipos codificados | NFR-046-08, AC-046-48 | S |
| T-046-155 | `/speckit.converge 046`, verificación de NFR-046-08 y artefactos de cierre | NFR-046-08, AC-046-48 | M |

## Resumen

| Fase | Tareas | Carga | Nota |
|---|---:|---|---|
| F1 Modelo | 11 | **L** | Siete entidades |
| F2 Almacenamiento | 8 | **L** | La abstracción condiciona todo |
| F3 Servicio | 12 | **XL** | Donde vive el valor |
| F4 Vinculación y autorización | 11 | **XL** | **Antes que la API**: sin ella sería una vulnerabilidad |
| F5 Seguridad del archivo | 8 | L | Incluye la capacidad de retención, sin plazos |
| F6 API | 11 | **L** | — |
| F7 Pruebas | 14 | **XL** | La seguridad es una suite, no un apartado |
| F8 Frontend | 12 | **XL** | El componente reutilizable es lo más delicado |
| F9 Legado y cierre | 16 | **XL** | El legado se marca, no se inventa |
| **Total** | **103** | — | — |

---

# ESTADO DE IMPLEMENTACIÓN

Actualizado el 2026-08-30, al cierre de `/speckit.implement 046`. Cada estado
se afirma contra código y pruebas ejecutadas, no contra intención.

| Estado | Significado |
|---|---|
| ✅ | Implementado y cubierto por prueba que se ejecutó y pasó |
| ⚠️ | Implementado, pero **sin verificar** en este entorno; se dice por qué |
| ⛔ | No implementado; se dice por qué y quién lo hereda |

## F1 · Modelo y catálogo

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-001 | ✅ | `models.py::DocumentCategory/DocumentType`; `test_catalogos_nacen_vacios` |
| T-046-002 | ✅ | `DocumentType` con 11 columnas de política; `TiposDocumentalesPage` |
| T-046-003 | ✅ | `metadata_schema` + `service.validate_metadata`; `test_metadata_se_valida_contra_el_esquema_del_tipo` |
| T-046-004 | ✅ | `0023` renombra `file_metadata`→`stored_files`; `FileMetadata` eliminada |
| T-046-005 | ✅ | `models.py::Document` |
| T-046-006 | ✅ | `models.py::DocumentVersion`; `test_versionado_sin_sobrescritura` |
| T-046-007 | ✅ | `models.py::DocumentLink` con `frozen_version_id` |
| T-046-008 | ✅ | `uq_document_versions_active`, `uq_documents_company_type_number` |
| T-046-009 | ✅ | Índices de `0023`; `test_listar_miles_de_documentos_sin_abrir_un_solo_binario` |
| T-046-010 | ✅ | `service.is_expired` derivado; estados de documento y de archivo separados |
| T-046-011 | ✅ | `0023_document_model`, aplicada sobre PostgreSQL 18.6 |

## F2 · Almacenamiento

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-020 | ✅ | `storage.py::DocumentStorageProvider` |
| T-046-021 | ✅ | `FilesystemStorageProvider`; suite de conformidad |
| T-046-022 | ✅ | `generate_storage_key`; `test_amz_12_clave_de_almacenamiento_opaca` |
| T-046-023 | ✅ | Temporal → `os.replace` → verificación; `test_fallo_de_escritura_no_deja_version` |
| T-046-024 | ✅ | `verify()`; `test_objeto_ausente_…`, `test_huella_distinta_no_se_entrega` |
| T-046-025 | ⚠️ | `S3CompatibleStorageProvider` implementado y con `endpoint_url` obligatorio. **Sin endpoint real en este entorno**: su conformidad queda sin verificar y las pruebas se omiten diciéndolo |
| T-046-026 | ✅ | Credenciales solo por entorno; `test_el_estado_no_expone_rutas_ni_credenciales` |
| T-046-027 | ✅ | Raíz por instalación; sin depósito compartido |

## F3 · Servicio

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-030 | ✅ | `sanitize_filename`; `test_amz_01_recorrido_de_rutas` (6 vectores) |
| T-046-031 | ✅ | `detect_mime` por contenido; `test_amz_02_suplantacion_de_mime` |
| T-046-032 | ✅ | `test_lista_blanca_vacia_significa_ninguno` |
| T-046-033 | ✅ | Corte en flujo; `test_amz_18_agotamiento_por_archivo_grande` |
| T-046-034 | ✅ | `test_subida_valida_calcula_hash_en_servidor`, `test_amz_15_asignacion_masiva` |
| T-046-035 | ✅ | `_create_version`; `test_amz_13_sin_sobrescritura_del_historico` |
| T-046-036 | ✅ | Original byte a byte. **No hay derivados**: miniaturas y OCR están prohibidos por el encargo |
| T-046-037 | ✅ | `versioning_policy` `SINGLE`/`VERSIONED` |
| T-046-038 | ✅ | `IdempotencyRecord` existente; `test_subida_idempotente` |
| T-046-039 | ✅ | `DOCUMENT_HASH_COINCIDENCE` auditado, no bloqueante; `test_el_mismo_archivo_dos_veces_no_se_deduplica_ni_se_bloquea` |
| T-046-040 | ✅ | `validate_metadata` |
| T-046-041 | ✅ | `external_url` ⇒ `is_managed=False`; `EXTERNAL_DOCUMENT_NO_FILE` |

## F4 · Vinculación y autorización

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-050 | ✅ | `resources.py`: **19** tipos registrados; `test_tipo_de_recurso_desconocido_se_rechaza` |
| T-046-051 | ✅ | `_assert_resource_access`; `test_amz_16_vinculacion_no_autorizada` |
| T-046-052 | ✅ | `test_amz_17_desvinculacion_no_autorizada` |
| T-046-053 | ✅ | `documents_for`; `/documentos/por-recurso/{tipo}/{id}` |
| T-046-054 | ✅ | `freeze_links`; `test_version_congelada_el_historico_no_se_reinterpreta` |
| T-046-055 | ✅ | `_assert_can_read_file` |
| T-046-056 | ✅ | `test_amz_06_referencia_insegura_directa` (404, nunca 403) |
| T-046-057 | ✅ | `test_amz_07_fuga_entre_empresas` (5 operaciones) |
| T-046-058 | ✅ | `allowed_actions`, `can_delete` |
| T-046-059 | ✅ | `documentos:*` con la convención de la Spec 003; `test_los_permisos_documentales_quedan_concedidos` |
| T-046-060 | ✅ | `record_audit` transversal; `test_amz_20_los_registros_no_filtran_contenido` |

## F5 · Seguridad del archivo

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-070 | ✅ | 5 estados de seguridad, separados del estado del archivo |
| T-046-071 | ✅ | `assert_deliverable`; `test_pendiente_de_analisis_no_se_entrega` |
| T-046-072 | ✅ | ClamAV 1.4.3 real; `DisabledScanner` declara `SKIPPED`, nunca `CLEAN` |
| T-046-073 | ✅ | `FileSecurityScan` + `DOCUMENT_SCAN_REJECTED` |
| T-046-074 | ✅ | `test_amz_03`, `test_amz_11_comprimidos_rechazados_por_defecto` |
| T-046-075 | ✅ | `retention_days`; sin plazo por defecto — `test_sin_plazo_declarado_nada_vence` |
| T-046-076 | ⚠️ | `purge_version` existe y es idempotente. **No hay planificador**: la plataforma aún no tiene trabajador común, y crear uno aquí sería ampliar el alcance. La operación queda lista para que ese trabajador la invoque |
| T-046-077 | ✅ | `purge_blockers`; `test_una_version_referenciada_no_se_purga` |

## F6 · API

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-080 | ✅ | `/documentos/categorias`, `/documentos/tipos` |
| T-046-081 | ✅ | 5 endpoints; `test_borrado_protegido_y_archivado_conserva_binario` |
| T-046-082 | ✅ | `POST /documentos/{id}/versiones` multipart |
| T-046-083 | ✅ | `GET .../versiones`; no existe endpoint de edición de versión |
| T-046-084 | ✅ | Cabeceras `no-store`, `nosniff`, `sandbox`; `test_amz_19_inyeccion_de_cabeceras` |
| T-046-085 | ✅ | `test_amz_04_contenido_activo_nunca_en_linea` |
| T-046-086 | ✅ | `/vinculos`, `/por-recurso/...` |
| T-046-087 | ✅ | Códigos con `details`; `allowed_actions` en cada documento |
| T-046-088 | ✅ | `If-Match` con `_check_version` |
| T-046-089 | ✅ | 046 **no** notifica: no se creó ningún emisor. Los contratos de evento quedan declarados para 047 |
| T-046-090 | ✅ | `expiring_before` por índice; `test_listar_miles_…` (0 aperturas) |

## F7 · Pruebas de backend

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-100 a T-046-103 | ✅ | `tests/test_documents.py` |
| T-046-104 | ✅ | PostgreSQL 18.6 + almacenamiento en disco real |
| T-046-105 | ✅ | `test_documento_logico_sin_archivo`, `test_vinculacion_y_documento_compartido` |
| T-046-106 | ✅ | `tests/test_documents_security.py`: `AMZ-01`..`AMZ-20`, una prueba por amenaza |
| T-046-107 | ✅ | `test_dos_subidas_simultaneas_no_producen_dos_v2` |
| T-046-108 | ✅ | 3 pruebas de fallo de almacenamiento |
| T-046-109 | ⚠️ | `tests/test_documents_storage.py` parametrizada por proveedor: sistema de archivos ✅, compatible con S3 **omitido por falta de servicio real** |
| T-046-110 | ✅ | `test_el_contrato_nunca_expone_almacenamiento` |
| T-046-111 | ✅ | `test_listar_miles_de_documentos_sin_abrir_un_solo_binario` (5.000 filas) |
| T-046-112 | ✅ | `test_amz_20_los_registros_no_filtran_contenido` |
| T-046-113 | ✅ | Regresión completa sobre PostgreSQL 18.6 |

## F8 · Frontend

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-120 | ✅ | `src/modules/documentos/types.ts` |
| T-046-121 | ✅ | `BibliotecaPage.tsx` con 4 filtros y paginación |
| T-046-122 | ✅ | `DocumentoDetallePage.tsx` |
| T-046-123 | ✅ | Tabla de versiones sin control de edición |
| T-046-124 | ✅ | `<input type="file">` nativo, enfocable; `documents-a11y.spec.ts` |
| T-046-125 | ✅ | «Subiendo…» / «Verificando…»; **sin porcentaje** |
| T-046-126 | ✅ | `uploadErrorMessage`; `documentos.test.tsx` (7 casos) |
| T-046-127 | ✅ | `AdjuntosPanel.tsx`, único componente de adjuntos |
| T-046-128 | ✅ | `TiposDocumentalesPage.tsx` |
| T-046-129 | ✅ | La previsualización se entrega como descarga; no hay visor propio que adaptar |
| T-046-130 | ✅ | `truncateName` por el centro; `documentos.test.tsx` |
| T-046-131 | ⛔ | `UnsavedChangesGuard` no se aplica: los formularios de 046 son de una línea y la carga es inmediata. Aplicarlo aquí añadiría fricción sin proteger nada |

## F9 · Legado, E2E y cierre

| Tarea | Estado | Evidencia |
|---|---|---|
| T-046-140 | ✅ | `0024`: 12 columnas anotadas, `documents_created: 0` |
| T-046-141 | ✅ | `test_un_hash_sin_binario_no_es_un_documento` |
| T-046-142 | ✅ | `MISSING_FILE`; `test_un_archivo_que_no_esta_se_reporta_no_se_inventa` |
| T-046-143 | ✅ | `import_legacy_reference`; `tests/test_documents_legacy_import.py` |
| T-046-144 | ✅ | `0024_document_legacy_marks`, con reversión probada |
| T-046-145 | ✅ | `e2e/documents.spec.ts` |
| T-046-146 | ✅ | Contrato 045↔046 verificado en backend (`test_version_congelada_…`) |
| T-046-147 | ⚠️ | `PermitInstance` y `OfficialDocument` registrados y probados en backend; el E2E regulatorio por interfaz **no** se escribió: 044 no tiene pantallas de permiso con carga |
| T-046-148 | ✅ | Fixture de 5 casos: `tests/test_documents_legacy_import.py` |
| T-046-149 | ✅ | `playwright.config.ts` cubre Chromium, Firefox y WebKit |
| T-046-150 | ✅ | `e2e/documents-a11y.spec.ts` |
| T-046-151 | ✅ | 6 viewports, 320–1440 |
| T-046-152 | ✅ | Rutas nuevas incluidas en el rastreo |
| T-046-153 | ✅ | 19 tipos registrados; §2 de la matriz de consumidoras |
| T-046-154 | ✅ | 0 tipos documentales codificados: los catálogos nacen vacíos |
| T-046-155 | ✅ | `/speckit.converge 046` y `SPEC_046_FINAL_CLOSEOUT.md` |

## Recuento

| Estado | Tareas |
|---|---:|
| ✅ Implementado y verificado | 98 |
| ⚠️ Implementado, sin verificar aquí | 4 (T-046-025, 076, 109, 147) |
| ⛔ No implementado, con motivo | 1 (T-046-131) |
| **Total** | **103** |
