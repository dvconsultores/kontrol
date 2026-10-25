# MATRIZ DE TRAZABILIDAD — SPEC 046

Derivada por script de `spec.md`, `tasks.md` y `acceptance-criteria.md`. No se escribe a mano.

## 1. Cobertura — verificada por comando

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 84 |
| Requisitos no funcionales | 9 |
| Criterios de aceptación | 50 |
| Tareas | 103 |
| **Requisitos funcionales sin tarea** | **0** |
| **Requisitos no funcionales sin tarea** | **0** |
| **Criterios sin tarea que los cubra** | **0** |
| **Tareas sin requisito ni criterio** | **0** |

## 2. Requisito funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| FR-046-001 | `Document` con empresa, tipo, título, número externo, emisor, estado y vigenci | T-046-005, T-046-011 |
| FR-046-002 | `DocumentVersion` con número correlativo, archivo, motivo del reemplazo, autor | T-046-006, T-046-011 |
| FR-046-003 | `StoredFile` con nombre original, `storage_key` opaca, MIME declarado y detect | T-046-004, T-046-011 |
| FR-046-004 | El número de versión lo asigna el **servidor**; jamás el cliente (§101) | T-046-008, T-046-011, T-046-035 |
| FR-046-005 | Una versión anterior **nunca** se sobrescribe (R-046-4) | T-046-011, T-046-035, T-046-083, T-046-123 |
| FR-046-006 | El original se conserva **byte a byte**; toda miniatura o conversión es deriva | T-046-011, T-046-036 |
| FR-046-007 | Distinguir «nueva versión del mismo documento» de «documento nuevo»; la políti | T-046-011, T-046-037 |
| FR-046-010 | `DocumentCategory` y `DocumentType` como catálogo **por empresa**; nace vacío | T-046-001, T-046-011, T-046-080 |
| FR-046-011 | `DocumentType` declara extensiones y MIME admitidos, tamaño máximo, política d | T-046-002, T-046-011, T-046-128 |
| FR-046-012 | Ningún tipo documental está codificado: todos son dato (P8) | T-046-001, T-046-011 |
| FR-046-013 | `DocumentType` es distinto del MIME: `PACKING_LIST` no es `application/pdf` (§ | T-046-001, T-046-011 |
| FR-046-014 | Metadata extensible **validada por esquema** del tipo; nunca JSON libre para d | T-046-003, T-046-011, T-046-040 |
| FR-046-020 | `DocumentLink` vincula un documento a una entidad de cualquier dominio, con ro | T-046-007, T-046-011 |
| FR-046-021 | Un mismo documento puede servir a **varias** entidades sin duplicar el binario | T-046-007 |
| FR-046-022 | `resource_type` pertenece a un **registro cerrado y validado**, no a texto lib | T-046-050 |
| FR-046-023 | Vincular exige permiso sobre la **entidad de destino**, no solo sobre el docum | T-046-051 |
| FR-046-024 | Un documento vinculado a una entidad inmutable no puede desvincularse (R-D0-08 | T-046-052 |
| FR-046-025 | Consultar los documentos de una entidad es una operación de primera clase | T-046-053 |
| FR-046-030 | Abstracción `DocumentStorageProvider` con proveedor **intercambiable por confi | T-046-020, T-046-109 |
| FR-046-031 | Proveedor de sistema de archivos como implementación por defecto, sobre el vol | T-046-021 |
| FR-046-032 | Proveedor compatible con S3 como segunda implementación, **sin acoplar a ningú | T-046-025, T-046-109 — **NOT_SUPPORTED_BY_PRODUCT_BASELINE** (OD-S3-01, 2026-10-25) |
| FR-046-033 | Ningún binario en PostgreSQL (R-D0-08-3) | T-046-004 |
| FR-046-034 | Aislamiento por instalación: sin depender de un depósito compartido entre clie | T-046-027 |
| FR-046-035 | Las credenciales del almacenamiento son secretos: nunca en base de datos, fron | T-046-026 |
| FR-046-036 | La escritura es **verificar y luego confirmar**: no puede quedar metadata sin  | T-046-023 |
| FR-046-037 | Verificación de integridad que detecte metadata sin binario o con hash distint | T-046-024 |
| FR-046-040 | La `storage_key` la genera el servidor; el nombre del usuario **nunca** es rut | T-046-022 |
| FR-046-041 | `original_filename` se conserva y se sanea solo para mostrarlo | T-046-030 |
| FR-046-042 | Recorrido de rutas imposible: `../`, rutas absolutas, Unicode y doble codifica | T-046-030, T-046-106 |
| FR-046-043 | MIME **declarado** y MIME **detectado por contenido** se guardan por separado  | T-046-031 |
| FR-046-044 | Discrepancia entre ambos: política del tipo, rechazo por defecto (§18) | T-046-031 |
| FR-046-045 | Tamaño máximo configurable por tipo, con máximo global; rechazo **antes** de c | T-046-033 |
| FR-046-046 | SHA-256 calculado en el servidor sobre el contenido recibido (R-D0-08-4) | T-046-034 |
| FR-046-047 | Subida **idempotente**: doble clic, reintento o repetición no crean dos versio | T-046-038 |
| FR-046-048 | Ejecutables rechazados; SVG y comprimidos con política explícita (§50, §51, §8 | T-046-032, T-046-074 |
| FR-046-049 | Coincidencia de hash se **registra**, no se bloquea: dos documentos pueden ser | T-046-039 |
| FR-046-050 | La descarga se autoriza por permiso sobre la **entidad vinculada** (R-D0-08-6) | T-046-055 |
| FR-046-051 | Conocer el identificador **no** da acceso; se responde como inexistente (§128) | T-046-056, T-046-106 |
| FR-046-052 | Sin URL pública permanente (§81) | T-046-084 |
| FR-046-053 | Si hay URL firmada: expiración corta, alcance mínimo, no persistida ni registr | T-046-053 |
| FR-046-054 | Previsualización con **la misma** autorización que la descarga (§107) | T-046-085 |
| FR-046-055 | Formatos no seguros se fuerzan a descarga, no se muestran en línea (§47) | T-046-084 |
| FR-046-056 | Sin ejecución de contenido activo; cabeceras de seguridad y aislamiento en la  | T-046-085 |
| FR-046-057 | Los documentos sensibles no quedan en cachés compartidas (§82) | T-046-084 |
| FR-046-060 | Estados del **documento**: `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED`, `REVOK | T-046-010 |
| FR-046-061 | `EXPIRED` se **deriva** de `expiration_date`; no se persiste como estado (§38) | T-046-010 |
| FR-046-062 | El estado del documento es distinto del estado de seguridad del archivo (§49) | T-046-010 |
| FR-046-063 | Un documento en uso histórico **no se borra**: se archiva (§39) | T-046-081 |
| FR-046-064 | Archivar es lógico: el binario **no** se destruye si hay histórico (§42) | T-046-081 |
| FR-046-065 | Política de retención configurable por tipo; **sin plazos legales inventados** | T-046-075 |
| FR-046-066 | El borrado físico, cuando proceda, se ejecuta por el trabajador común, no por  | T-046-076 |
| FR-046-067 | Sin referencias colgantes: una versión referenciada históricamente es estable  | T-046-077 |
| FR-046-070 | Estado de seguridad del archivo: `PENDING_SCAN`, `CLEAN`, `INFECTED`, `SCAN_FA | T-046-070 |
| FR-046-071 | Un archivo no `CLEAN` **no se descarga ni se previsualiza** | T-046-071 |
| FR-046-072 | El análisis es una **capacidad de despliegue configurable**; sin analizador, e | T-046-072 |
| FR-046-073 | El resultado del análisis se audita | T-046-073 |
| FR-046-080 | Contratos de documento, versión, vínculo, subida, descarga y previsualización | T-046-081, T-046-082 |
| FR-046-081 | Contrato de vinculación que **no expone** el almacenamiento (§94) | T-046-086, T-046-110 |
| FR-046-082 | `allowed_actions` calculado en backend según permiso, estado, referencias, ret | T-046-058, T-046-087 |
| FR-046-083 | Permisos con la convención vigente de la Spec 003; sin RBAC nuevo | T-046-059 |
| FR-046-084 | Auditoría por la capacidad transversal; sin tabla local (§60) | T-046-060 |
| FR-046-085 | La descarga se audita **según política del tipo**, no siempre (§61) | T-046-060 |
| FR-046-086 | `If-Match` con el mecanismo existente (§59) | T-046-088 |
| FR-046-087 | Aislamiento multiempresa en listar, consultar, descargar, vincular y versionar | T-046-057 |
| FR-046-088 | Contratos de evento `document.uploaded`, `version.created`, `document.expiring | T-046-089 |
| FR-046-090 | Biblioteca documental con URL propia, filtros y paginación | T-046-120, T-046-121 |
| FR-046-091 | Detalle con metadata, vínculos e historial de versiones | T-046-122 |
| FR-046-092 | Componente de adjuntos **reutilizable** por cualquier dominio (§97) | T-046-127 |
| FR-046-093 | Subida operable **sin arrastrar y soltar** (§161) | T-046-124 |
| FR-046-094 | Estado de la carga claro; sin porcentaje fingido si no se conoce (§99) | T-046-125 |
| FR-046-095 | Errores diferenciados por causa; nunca «error desconocido» (§100) | T-046-126 |
| FR-046-096 | Previsualización adaptada en pantalla estrecha; alternativa usable (§106) | T-046-129 |
| FR-046-097 | Nombres de archivo largos no rompen la disposición (§104) | T-046-130 |
| FR-046-100 | Contrato de la Spec 045 satisfecho **sin cambiar el modelo de 045** (§27) | T-046-054 |
| FR-046-101 | Contratos para 018, 019, 020, 027, 035, 040, 044 y 051 | T-046-153 |
| FR-046-102 | Metadata regulatoria (emisor, número, emisión, vencimiento) disponible **sin** | T-046-147, T-046-153 |
| FR-046-103 | El consumidor declara qué tipos exige y su cardinalidad; 046 **no** los codifi | T-046-153 |
| FR-046-104 | Consulta eficiente de documentos próximos a vencer, para que 047 la consuma (§ | T-046-090 |
| FR-046-105 | Referencia externa admitida y **marcada como no administrada** (§112) | T-046-005, T-046-041 |
| FR-046-110 | `file_metadata` evoluciona sin backfill: está vacía de uso (ADR: `SAFE_MIGRATI | T-046-004, T-046-113 |
| FR-046-111 | Las 9 columnas `UNVERIFIED_LEGACY` se conservan y se marcan; **no** se crean d | T-046-140, T-046-144 |
| FR-046-112 | Un binario localizable se importa calculando su hash y preservando el original | T-046-143, T-046-144 |
| FR-046-113 | Si la base afirma archivo y no está, se registra `MISSING_LEGACY_FILE`; **no s | T-046-142, T-046-144 |
| FR-046-114 | Un hash histórico **sin binario** no se convierte en documento (R-046-5) | T-046-141, T-046-144 |

## 3. Requisito no funcional → tarea

| NFR | Tareas |
|---|---|
| NFR-046-01 | T-046-090 |
| NFR-046-02 | T-046-121 |
| NFR-046-03 | T-046-009, T-046-090 |
| NFR-046-04 | T-046-150, T-046-152 |
| NFR-046-05 | T-046-151, T-046-152 |
| NFR-046-06 | T-046-131 |
| NFR-046-07 | T-046-104 |
| NFR-046-08 | T-046-154, T-046-155 |
| NFR-046-09 | T-046-026 |

## 4. Criterio de aceptación → tarea

| Criterio | Tareas |
|---|---|
| AC-046-01 | T-046-001 |
| AC-046-02 | T-046-101 |
| AC-046-03 | T-046-105 |
| AC-046-04 | T-046-102, T-046-145 |
| AC-046-05 | T-046-100 |
| AC-046-06 | T-046-101 |
| AC-046-07 | T-046-101 |
| AC-046-08 | T-046-102 |
| AC-046-09 | T-046-102 |
| AC-046-10 | T-046-102, T-046-145 |
| AC-046-11 | T-046-107 |
| AC-046-12 | T-046-035 |
| AC-046-13 | T-046-107 |
| AC-046-14 | T-046-007, T-046-053 |
| AC-046-15 | T-046-007, T-046-105 |
| AC-046-16 | T-046-103 |
| AC-046-17 | T-046-051 |
| AC-046-18 | T-046-146 |
| AC-046-19 | T-046-052 |
| AC-046-20 | T-046-145 |
| AC-046-21 | T-046-056 |
| AC-046-22 | T-046-057 |
| AC-046-23 | T-046-084 |
| AC-046-24 | T-046-085 |
| AC-046-25 | T-046-084 |
| AC-046-26 | T-046-074 |
| AC-046-27 | T-046-071 |
| AC-046-28 | T-046-072 |
| AC-046-29 | T-046-010 |
| AC-046-30 | T-046-010 |
| AC-046-31 | T-046-081, T-046-145 |
| AC-046-32 | T-046-081 |
| AC-046-33 | T-046-077 |
| AC-046-34 | T-046-108 |
| AC-046-35 | T-046-108 |
| AC-046-36 | T-046-039 |
| AC-046-37 | T-046-040 |
| AC-046-38 | T-046-105 |
| AC-046-39 | T-046-148 |
| AC-046-40 | T-046-148 |
| AC-046-41 | T-046-148 |
| AC-046-42 | T-046-004 |
| AC-046-43 | T-046-060 |
| AC-046-44 | T-046-103 |
| AC-046-45 | T-046-107 |
| AC-046-46 | T-046-111 |
| AC-046-47 | T-046-111 |
| AC-046-48 | T-046-154, T-046-155 |
| AC-046-49 | T-046-112 |
| AC-046-50 | T-046-149 |

## 5. Autoridad → requisito

| Fuente | Requisitos |
|---|---|
| **`ADR-D0-008` §Modelo conceptual** | FR-046-001, 002, 003, 020 |
| `ADR-D0-008` R-D0-08-1 · sin almacenamiento por módulo | Regla no negociable 1 |
| `ADR-D0-008` R-D0-08-2 · `storage_key` opaca | FR-046-040, R-046-3 |
| `ADR-D0-008` R-D0-08-3 · sin binarios en PostgreSQL | FR-046-033 |
| `ADR-D0-008` R-D0-08-4 · hash del servidor | FR-046-046 |
| `ADR-D0-008` R-D0-08-5 · versionado, no sustitución | FR-046-005, R-046-4 |
| `ADR-D0-008` R-D0-08-6 · autorización por la entidad | FR-046-050, 051 |
| `ADR-D0-008` R-D0-08-7 · auditoría | FR-046-084, 085 |
| `ADR-D0-008` R-D0-08-8 · adjunto inmutable no se desvincula | FR-046-024, 063 |
| `ADR-D0-008` R-D0-08-9 · validación en servidor | FR-046-043, 044, 045 |
| `ADR-008` · estrategia de archivos (volúmenes) | FR-046-031, 034 |
| `ADR-D0-001` · PostgreSQL 18.x | NFR-046-07 |
| `ADR-012` · auditoría transversal | FR-046-084 |
| `ADR-013` · idempotencia y concurrencia | FR-046-047, 086 |
| Constitución P5 · dato histórico | FR-046-005, 006, 063, 064, 067, 114 |
| Constitución P6 · backend es autoridad | FR-046-040..046, 082 |
| Constitución P8 · sin negocio en código | FR-046-010, 012, NFR-046-08 |
| Constitución P11 · accesibilidad | NFR-046-04, 05 |
| Constitución P13 · integridad transaccional | FR-046-036, 037 |
| **Constitución P17/P22 · autoridad única** | Regla no negociable 1; toda la Spec |
| Constitución P21 · paridad del motor | NFR-046-07 |
| Constitución P23 · captura temprana | FR-046-046 (el hash solo es verificable al recibir) |
| **Contrato de la Spec 045** (CL-045-10, CVG-045-04) | FR-046-100 |
| Encargo §10, §11 · vinculación sin polimórfica insegura | FR-046-022 |
| Encargo §15-18 · nombre y MIME | FR-046-040..044 |
| Encargo §48, §49 · análisis y estado | FR-046-070..073 |
| Encargo §110-115 · legado | FR-046-110..114 |
| Encargo §126 · modelo de amenazas | `risk-register.md` §1 |
| Encargo §142 · fronteras | FR-046-103 |

## 6. Cadena prevista: requisito → diseño → tarea → código → prueba → evidencia

| Bloque | Diseño | Tareas | Prueba prevista |
|---|---|---|---|
| Modelo documental | `data-model.md` §1-7 | T-046-001..011 | Integración sobre PostgreSQL |
| Almacenamiento | `plan.md` §3, `research.md` §8 | T-046-020..027 | Matriz por adaptador con proveedor real |
| Servicio | `research.md` §3 | T-046-030..041 | Unidad + suite de seguridad |
| Vinculación y autorización | `research.md` §5 | T-046-050..060 | Seguridad + multiempresa |
| Seguridad del archivo | `data-model.md` §7 | T-046-070..077 | Estados y entrega denegada |
| API | `contracts/api-contracts.md` | T-046-080..090 | Contrato OpenAPI |
| Frontend | `wireframes/` | T-046-120..131 | E2E, axe, responsive |
| Legado | `legacy-document-migration-matrix.md` | T-046-140..144 | Fixture de cinco casos |
| Contratos | `document-consumer-contract-matrix.md` | T-046-146, 147, 153 | E2E 045 ↔ 046 |

## 7. Delta dirigido CONC-046 — dos subidas simultáneas de versión (2026-09-15)

Detalle: `conc-046-concurrent-version-delta.md`. Pruebas en `tests/test_documents_security.py`
(sección «Concurrencia (CONC-046)»); mutaciones en `evidence/conc-046/`.

| Requisito | Criterio | Autoridad | Tareas | Código | Prueba | Mutación |
|---|---|---|---|---|---|---|
| FR-046-115 · una versión nueva, una vigente, la perdedora 409 | AC-046-51 | AC-046-11 · aceptación registrada de CONC-046 | T-C46-02, 05, 06 | `_create_version`: `SAVEPOINT` + `es_violacion_unica` → `VERSION_CONFLICT` | `test_dos_subidas_simultaneas_no_producen_dos_v2` (×3) · `test_la_primera_version_simultanea_tampoco_da_un_500` · `test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500` · `test_tres_subidas_simultaneas_crean_una_sola_version` | M046-CONC-01 · M046-CONC-02 |
| FR-046-116 · la perdedora no deja rastro | AC-046-52 | ADR-D0-008 · ADR-012 | T-C46-03, 06 | `upload_version`: borra el binario de la perdedora; auditoría transaccional | `_huella` en las pruebas de carrera: archivos, análisis, auditoría y binarios +1 | M046-CONC-05 |
| FR-046-117 · la misma clave en carrera recibe la ganadora | AC-046-53 | AC-046-13 · FR-046-047 | T-C46-04, 07 | ruta: relee el registro idempotente tras `VERSION_CONFLICT` | `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora` | M046-CONC-04 |
| FR-046-118 · el acierto es de la clave y del documento | AC-046-54 | AC-046-13 | T-C46-04, 07 | `_acierto_idempotente` por `response_payload.version_id` y documento | `test_un_reintento_devuelve_la_version_de_su_clave_aunque_haya_otra_despues` · `test_la_misma_clave_en_otro_documento_no_devuelve_una_version_ajena` · `test_subida_idempotente` | M046-CONC-03 |
| FR-046-119 · documentos distintos no se esperan; aislamiento intacto | AC-046-55 | ARCH-MC-001 · `ADR-013` | T-C46-06 | sin bloqueo nuevo; `_get_document` por contexto | `test_subidas_a_documentos_distintos_no_se_esperan` · `test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera` · suites AMZ | — |

Sin huérfanos: 5 requisitos, 5 criterios, 13 tareas y 5 mutaciones, todos enlazados.
