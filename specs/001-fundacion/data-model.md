# DATA MODEL — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Arquitecto de datos |
| Ruta | `specs/001-fundacion/data-model.md` |

## 1. Principios del modelo (heredados de DOC-03)

- Identificadores UUID internos; códigos de negocio separados.
- Multiempresa: `tenant_id`/`company_id` en cada agregado relevante.
- Códigos, RIF, teléfonos, cuentas, facturas, controles, seriales e IMEI son **texto**.
- Soft delete solo en maestros permitidos; documentos protegidos por estados.
- Campos de auditoría uniformes: `created_at`, `created_by`, `updated_at`, `updated_by` (fecha/hora del servidor).
- Versiones para reglas, perfiles, tasas y configuraciones (efecto histórico).
- Snapshots JSON solo como copia histórica, no como fuente primaria.
- Restricciones e índices implementan reglas críticas además del servicio.
- Outbox para integraciones y tareas asíncronas.

## 2. Entidades fundacionales

### 2.1 Organización y multiempresa

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `Installation` | id, installation_uuid (único), public_key, key_reference (volumen), state, created_at | Identidad persistente; par de claves local. **`key_reference`** (contrato ratificado el 2026-10-13, `INSTALACION-KEY-REFERENCE-120` / A3): referencia de almacenamiento al material criptográfico local; para las altas nuevas es **relativa al volumen de instalación** (`installation_private_key.pem`), generada por el producto, nunca por el usuario; las filas históricas con ruta absoluta siguen siendo válidas tal cual (sin migración, sin backfill, sin reescritura); resolución: `None` → ruta canónica por configuración, absoluta → tal cual, relativa → `installation_volume_path/ref`; nunca contra el directorio de trabajo; nunca se persiste material de clave |
| `Tenant` | id, installation_id, code, name, status, plan, created_at | 1:1 con Installation en 001 (CL-02) |
| `Company` | id, tenant_id, code, legal_name, trade_name, rif, legal_type, activity, fiscal_address, functional_currency, status | Entidad legal |
| `Branch` | id, company_id, code, name, address, manager, status | |
| `Establishment` | id, branch_id, code, name, fiscal_address, issuance_enabled, status | Lugar de emisión futuro |
| `Warehouse` | id, company_id, branch_id, code, name, type, policies, status | |
| `Location` | id, warehouse_id, code, zone, aisle, rack, capacity, restrictions, status | |

### 2.2 Seguridad

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `User` | id, tenant_id, username, person_id (opcional), email, password_hash (Argon2id), status, mfa_enabled, must_change_password, last_login, lockout_until | |
| `Role` | id, company_id/null global, code, name, protected, status | |
| `Permission` | id, resource, action, scope_type, constraints | Acciones más allá de CRUD |
| `RolePermission` | role_id, permission_id, constraints | |
| `UserRole` | user_id, role_id, company_id, validity | |
| `UserScope` | id, user_id, company_id, branch_id, establishment_id, warehouse_id, cost_center_id, validity | Alcance organizacional |
| `Session` | id, user_id, refresh_token_hash, ip, user_agent, expires_at, revoked_at, created_at | Rotación y revocación |
| `PasswordReset` | id, user_id, token_hash, expires_at, used_at, created_by | Token de un solo uso |

### 2.3 Licencia local

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `LicenseState` | id, installation_id, license_id, mode (FULL_ACCESS/RENEWAL_NOTICE/CRITICAL_RENEWAL_NOTICE/READ_ONLY/SECURITY_SUSPENSION), period_start, period_end, critical_warning_start, read_only_start, entitlements (JSON), minimum_version, verified_at, last_reliable_date, kid | Copia firmada verificada |
| `LicenseArtifact` | id, license_id, payload (firmado), signature, hash, kid, imported_at, replaced_at | Paquetes firmados |
| `LicenseEvent` | id, installation_id, event_type, detail, user_id, created_at | Bitácora inmutable local |
| `LicenseRenewalRequest` | id, installation_id, payment_proof_ref, status, notes, created_by, created_at | Carga de comprobante |

### 2.4 Auditoría

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `AuditEvent` | id, tenant_id, company_id, user_id, session_id, request_id, action, entity_type, entity_id, before, after, source, reason, evidence, ip, created_at | Append-only; partición por fecha/tenant |

### 2.5 Sistema

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `SystemSetting` | id, tenant_id, key, value, updated_by, updated_at | Configuración persistente |
| `FeatureFlag` | id, key, enabled, audience, updated_by, updated_at | |
| `IdempotencyRecord` | id, key (único), method, path, user_id, company_id, response_status, response_hash, created_at, expires_at | Idempotency-Key |
| `OutboxEvent` | id, aggregate_type, aggregate_id, event_type, payload, occurred_at, published_at, attempts, error | Integraciones futuras |
| `FileMetadata` | id, company_id, original_name, mime_type, size, sha256, storage_key, uploaded_by, uploaded_at, expires_at | Hash y metadatos |

### 2.6 Núcleo fiscal (preparación, sin emisión)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `LegalSource` | id, authority, type, number, gazette, publication_date, effective_from, effective_to, file_id, hash, status | Norma con fuente |
| `TaxRuleVersion` | id, tax_code, legal_source_id, effective_from, effective_to, rate/formula, conditions, approval, fiscal_release, status | Regla versionada |
| `FiscalNumberSeries` | id, company_id, establishment_id, document_type, prefix, next_number, lock_version, validity | Numeración futura |
| `ControlNumberBatch` | id, company_id, establishment_id, printer, range_from, range_to, received_at, status | Lotes de control futuros |

## 3. Reglas de integridad críticas

| Regla | Restricción |
|---|---|
| Identidad de instalación | `installation_uuid` único; clave privada local fuera de Git/imágenes |
| Licencia | Un solo `LicenseState` activo por instalación; firma verificada; `installation_id` debe coincidir |
| Modo de acceso | Derivado de fechas contractuales + última fecha confiable; nunca del reloj del navegador |
| Multiempresa | FK críticas confirman misma empresa/tenant; pruebas de aislamiento negativo |
| Auditoría | Append-only; sin UPDATE/DELETE físico |
| Idempotencia | `key` único por operación; reintento devuelve resultado previo |
| Concurrencia | `version`/ETag en maestros editables; 409 en conflicto |
| Usuario | `password_hash` nunca en texto plano; `must_change_password` al primer acceso |

## 4. Estados (máquinas de estado)

| Objeto | Estados |
|---|---|
| `Installation` | PENDING → ACTIVE → OFFLINE → REPLACED → REVOKED → COMPROMISED |
| `LicenseState.mode` | FULL_ACCESS → RENEWAL_NOTICE → CRITICAL_RENEWAL_NOTICE → READ_ONLY; SECURITY_SUSPENSION (firma inválida) |
| `Company` | DRAFT → PENDING_APPROVAL → ACTIVE → INACTIVE |
| `User` | PENDING → ACTIVE → DISABLED → LOCKED |
| `Session` | ACTIVE → EXPIRED → REVOKED |
| `LicenseRenewalRequest` | NOT_REPORTED → REPORTED → UNDER_REVIEW → CONFIRMED → REJECTED → REFUNDED |

## 5. Convenciones técnicas

- Timestamps ISO 8601 con zona; servidor como autoridad.
- Decimales exactos para montos/tasas; sin flotantes para dinero.
- Índices: FK multiempresa, `installation_uuid`, `user.username` (tenant), `audit_event(request_id)`, `idempotency(key)`.
- Partición sugerida para `AuditEvent` (por mes/tenant).
- Migraciones Alembic revisadas; seeds idempotentes.

## 6. Estado de aprobación

| Elemento | Estado |
|---|---|
| Entidades fundacionales | ✔ |
| Reglas de integridad | ✔ |
| Máquinas de estado | ✔ |
| Aprobación | Pendiente |
