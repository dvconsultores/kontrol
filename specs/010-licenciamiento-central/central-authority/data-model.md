# Modelo de datos — Autoridad Central Fase 1 (PostgreSQL propio)

| Tabla | Columnas | Claves y restricciones | Ciclo de vida |
|---|---|---|---|
| `cla_installations` | `id` (uuid texto, PK), `installation_uuid` (texto 64), `public_key_pem` (texto), `customer_id`, `contract_id`, `company_tax_id` (texto), `registered_by` (operador), `created_at` (UTC) | `UNIQUE(installation_uuid)` | insert idempotente; sin update por flujos de Fase 1 |
| `cla_period_lineages` | `id` (PK), `installation_id` (FK → `cla_installations.id`), `period_start`, `period_end` (timestamptz), `last_revision` (int ≥ 0), `created_at`, `updated_at` | `UNIQUE(installation_id, period_start, period_end)`; índice por `installation_id` | se crea con la primera emisión del período; `last_revision` solo crece, bajo `FOR UPDATE` de la instalación |
| `cla_issuances` | `id` (PK), `installation_id` (FK), `lineage_id` (FK), `license_id` (texto 64), `revision` (int ≥ 1), `period_start`, `period_end`, `kid`, `payload` (JSON exacto firmado), `payload_hash` (sha256 hex), `signature_hex`, `issued_at` (UTC técnico), `issued_by` (operador) | `UNIQUE(license_id)`, `UNIQUE(lineage_id, revision)`; índices por `installation_id`, `lineage_id` | **append-only**: ninguna operación actualiza ni borra |
| `cla_audit_events` | `id` (PK), `operation` (REGISTER_INSTALLATION, ISSUE_LICENSE, …), `operator`, `installation_uuid`, `period_start`, `period_end`, `revision`, `issuance_id`, `outcome` (OK / código de error), `detail` (JSON sin material), `created_at` | índice por `installation_uuid` | append-only |

Fronteras de transacción: una por operación del CLI; la emisión entera en una transacción con la
instalación bloqueada. Inmutable: libro y auditoría. Mutable: `last_revision` del linaje.
Sin tablas del cliente. Tabla de versión Alembic: `cla_alembic_version`.
