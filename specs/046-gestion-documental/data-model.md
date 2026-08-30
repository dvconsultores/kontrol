# MODELO DE DATOS — SPEC 046

Toda entidad con `company_id` y filtro de alcance. Fechas con zona horaria.
Ningún binario en PostgreSQL (R-D0-08-3). Ningún tipo documental en el esquema (P8).

---

## 1. `document_categories` — catálogo por empresa

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `code` | String(32) | `COMERCIAL`, `REGULATORIO`… lo elige la empresa |
| `name` | String(120) | |
| `description` | Text? | |
| `status` | String(32) | |

`UNIQUE (company_id, code)`. **Nace vacío**: KONTROL no entrega categorías.

## 2. `document_types` — donde vive la política

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `category_id` | FK document_categories? | |
| `code`, `name` | String(32) / String(120) | `PACKING_LIST`, `PERMISO_SANITARIO`… |
| `allowed_mime_types` | JSON | Lista blanca. **Vacía = ninguno**, no «todos» |
| `allowed_extensions` | JSON | Coherencia con el MIME; ninguna es autoridad por sí sola |
| `max_size_bytes` | BigInteger? | Nulo = usa el máximo global |
| `versioning_policy` | String(16) | `VERSIONED` · `SINGLE` (§24) |
| `requires_expiration` | Boolean | Si el tipo exige vigencia |
| `metadata_schema` | JSON? | Esquema que valida la metadata extensible |
| `metadata_schema_version` | Integer | Versionable (§34) |
| `retention_policy` | JSON? | **Capacidad**; sin plazos por defecto (ESC-046-03) |
| `audit_downloads` | Boolean def. `false` | Política de auditoría de descarga (§61) |
| `scan_required` | Boolean def. `false` | Política de análisis por tipo (ESC-046-01) |
| `status`, `version` | | |

`UNIQUE (company_id, code)`.

> `allowed_mime_types` vacío significa **ningún tipo admitido**, no todos. Un
> valor por defecto permisivo sería la clase de decisión que abre un repositorio
> de malware sin que nadie lo note.

## 3. `stored_files` — evolución de `file_metadata`

| Campo | Estado | Notas |
|---|---|---|
| `id`, `company_id`, `original_name`, `mime_type`, `size`, `sha256`, `storage_key`, `uploaded_at`, `expires_at` | **Existen** en `file_metadata` | Se conservan |
| `declared_mime` | **Nuevo** String(120) | Lo que dijo el cliente |
| `detected_mime` | **Nuevo** String(120) | Lo que dicen los bytes (§17) |
| `extension` | **Nuevo** String(16)? | Normalizada |
| `storage_provider` | **Nuevo** String(32) | `FILESYSTEM` · `S3_COMPATIBLE` |
| `security_status` | **Nuevo** String(24) def. `SKIPPED` | `PENDING_SCAN` · `CLEAN` · `INFECTED` · `SCAN_FAILED` · `SKIPPED` |
| `uploaded_by` | **Nuevo** String(36)? | |
| `status` | **Nuevo** String(32) | `AVAILABLE` · `QUARANTINED` · `PURGED` |

`mime_type` se conserva como el **efectivo** (el detectado si hay discrepancia
aceptada). `UNIQUE (storage_key)` ya existe y se mantiene.

**`storage_key` es opaca** (R-D0-08-3, §55): se deriva de un identificador
aleatorio y de la fecha, **nunca** del nombre de empresa, tercero o archivo.

## 4. `documents` — el documento lógico

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `document_type_id` | FK document_types | |
| `title` | String(200) | |
| `description` | Text? | |
| `document_number` | String(120)? | Número externo; **sin unicidad global** (§70) |
| `issuer` | String(200)? | Emisor, opcional (§71) |
| `issued_at` | Date? | |
| `effective_from` | Date? | |
| `expiration_date` | Date? | Base de `EXPIRED` **derivado** (§38) |
| `metadata` | JSON? | Validado contra `metadata_schema` del tipo |
| `metadata_schema_version` | Integer? | La versión con la que se validó |
| `external_url` | String(500)? | Referencia **no administrada** (§112) |
| `is_managed` | Boolean def. `true` | `false` = solo referencia externa |
| `current_version_id` | String(36)? | Atajo de lectura a la versión vigente |
| `status` | String(32) | `DRAFT` · `ACTIVE` · `SUPERSEDED` · `ARCHIVED` · `REVOKED` |
| `created_by`, `created_at`, `updated_at`, `version` | | |

**Restricciones:**
- `UNIQUE (company_id, document_type_id, document_number)` **parcial**, solo
  cuando `document_number` no es nulo: dos documentos sin número no colisionan.
- `CHECK`: `is_managed = false` exige `external_url`; `is_managed = true` lo prohíbe.
- `EXPIRED` **no** es un valor de `status` (§38).

## 5. `document_versions`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `document_id` | FK documents | |
| `company_id` | FK companies | |
| `version_number` | Integer | Correlativo, **asignado por el servidor** (§101) |
| `stored_file_id` | FK stored_files | |
| `replacement_reason` | Text? | Por qué se reemplazó la anterior |
| `sha256` | String(64) | Copia del hash del archivo, para que la versión sea autosuficiente |
| `metadata_snapshot` | JSON? | La metadata tal como estaba al crearse |
| `status` | String(32) | `ACTIVE` · `SUPERSEDED` |
| `created_by`, `created_at` | | |

**Restricciones:**
- `UNIQUE (document_id, version_number)` — impide dos V2 en concurrencia (§101).
- **Índice único parcial** `(document_id) WHERE status = 'ACTIVE'` — una sola
  versión vigente.
- **Inmutable**: una versión `SUPERSEDED`, o referenciada por un vínculo
  congelado, no se edita ni se borra (R-D0-08-5, §26).

> `sha256` se **copia** aquí a propósito. Si el archivo se purgara por retención,
> la versión conservaría la prueba de qué contenía. Es duplicación deliberada
> con una razón, no redundancia.

## 6. `document_links` — la carencia central que 046 resuelve

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `document_id` | FK documents | |
| `company_id` | FK companies | Aislamiento sin join |
| `resource_type` | String(64) | **Validado contra el registro** (§5 de `research.md`) |
| `resource_id` | String(36) | |
| `role` | String(32)? | `EVIDENCE`, `SUPPORT`, `ATTACHMENT`… |
| `document_type_id` | FK document_types? | El rol documental en ese vínculo |
| `frozen_version_id` | String(36)? | **Versión congelada** cuando la entidad se vuelve inmutable |
| `is_frozen` | Boolean def. `false` | |
| `created_by`, `created_at` | | |

**Restricciones:**
- `UNIQUE (document_id, resource_type, resource_id, role)` — sin vínculos duplicados.
- Un vínculo con `is_frozen = true` **no se elimina** (R-D0-08-8).

> `frozen_version_id` es lo que satisface el contrato de la Spec 045: cuando una
> solicitud se aprueba, el vínculo **congela la versión usada**. Crear una V2
> después no altera la decisión de ayer (§26, §123).

## 7. `file_security_scans` — opcional por despliegue

| Campo | Tipo |
|---|---|
| `id`, `stored_file_id` FK, `scanner`, `result`, `details` JSON?, `scanned_at` |

Existe solo si hay analizador. Sin él, `stored_files.security_status = SKIPPED`
y **queda declarado**: nunca se afirma que un archivo fue analizado si no lo fue.

## 8. Registro de tipos de recurso — configuración, no tabla

`resource_type` se valida contra un registro declarado en código que, para cada
tipo admitido, indica el modelo, la columna de empresa y cómo comprobar el
permiso. No es dato de negocio: es el **mapa de integridad** entre 046 y sus
consumidores.

| Entrada | Ejemplo conceptual |
|---|---|
| `resource_type` | `ApprovalRequest` |
| Modelo | `approvals.models.ApprovalRequest` |
| Columna de empresa | `company_id` |
| Permiso requerido | `aprobaciones:view` |

Un `resource_type` ausente del registro se **rechaza**: no hay texto libre.

## 9. Índices — cada uno con su consulta

| Índice | Justifica |
|---|---|
| `documents (company_id, status)` | Biblioteca por empresa |
| `documents (company_id, document_type_id)` | Filtro por tipo |
| `documents (company_id, expiration_date)` | **Vencimientos** para 044 y 047 (§135) |
| `documents (company_id, document_type_id, document_number)` UNIQUE parcial | Número externo |
| `document_versions (document_id, version_number)` UNIQUE | Correlativo |
| `document_versions (document_id) WHERE status='ACTIVE'` UNIQUE | Una versión vigente |
| `document_links (resource_type, resource_id)` | **Documentos de una entidad** — la consulta de todos los consumidores |
| `document_links (document_id)` | Entidades de un documento |
| `stored_files (sha256)` | Solo para registrar coincidencias (§56, §134) |
| `document_types (company_id, code)` UNIQUE | — |

Se rechaza todo índice sin consulta que lo justifique. **No** se indexa
`storage_key` más allá de su unicidad ya existente.

## 10. Borrado, archivado y retención

| Entidad | Se borra si… | Se archiva |
|---|---|---|
| `Document` | Sin vínculos, sin versiones y en `DRAFT` | Siempre |
| `DocumentVersion` | Nunca si está `SUPERSEDED` o congelada | Se marca `SUPERSEDED` |
| `StoredFile` | Solo por retención declarada, y **nunca** si alguna versión lo referencia | `PURGED` conservando metadata y hash |
| `DocumentLink` | Solo si `is_frozen = false` | — |

Sin `cascade` destructivo en ninguna relación. `can_delete` y `allowed_actions`
los calcula el backend (FR-046-082).

## 11. Lo que 046 **no** modela

- Qué documentos exige cada proceso: lo declara el consumidor (§29, §142).
- Reglas regulatorias: son de la Spec 044.
- Notificaciones: son de la 047; 046 solo emite contratos de evento.
- Exportaciones de reportes: siguen en `reporting` (Spec 050).
