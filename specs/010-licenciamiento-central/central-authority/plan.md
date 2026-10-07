# Plan — Autoridad Central Fase 1

## Componentes

1. **Contrato puro compartido** `app/core/license_contract.py`: constantes de modo y de período,
   `LicenseData(revision: int | None)`, `parse_license_payload` (valida `revision` si viene: entero
   ≥ 1, ni booleano ni cadena → `LicenseContractError`), `canonical_bytes`, `payload_hash`,
   `load_public_key`, `verify_license_signature`, `sign_license_payload`, `compare_period`,
   `_as_utc`. Sin importar `app.core.config` ni `app.core.errors`. `app/core/license.py` reexporta
   y conserva `compute_mode`, `ensure_write_allowed`, `public_key_from_settings`.
2. **`central_authority/config.py`**: `Settings` (`KONTROL_CENTRAL_*`), validador de clave en `prod`.
3. **`central_authority/models.py`**: `Base` propia; `cla_installations`, `cla_period_lineages`,
   `cla_issuances`, `cla_audit_events`.
4. **`central_authority/alembic/`** + `alembic.ini`: una migración `0001_cla_fase1`.
5. **`central_authority/service.py`**: `register_installation`, `issue_license` (emisión y
   reemisión: misma función, el linaje decide), `get_issuance`, `list_issuances`; errores
   `CentralError(code, message)`.
6. **`central_authority/cli.py`**: `register-installation`, `issue-license`, `reissue-license`,
   `show-issuance`, `list-issuances`; `--operator` obligatorio; salida JSON.
7. **`central_authority/main.py`**: FastAPI con `/health/live`, `/health/ready`. Sin sync.
8. **Despliegue**: `Dockerfile.central`, `compose.central.yaml`, `central_authority/entrypoint.sh`,
   `central_authority/README.md` (agnóstico de proveedor).
9. **Pruebas** `tests/central/`; **evidencia** `evidence/central-licensing-authority-phase1/`.

## Transacción de emisión

`BEGIN` → `SELECT … FOR UPDATE` sobre `cla_installations` (existe siempre; serializa también la
primera `revision` de un período) → `SELECT` linaje (`installation_id, period_start, period_end`) o
`INSERT` → `siguiente = last_revision + 1` → construir payload (DOC-07 §10.2 + `revision` + `kid`)
→ `canonical_bytes` → `sign` → `INSERT cla_issuances` → `UPDATE linaje.last_revision` → `INSERT
cla_audit_events` → `COMMIT`. Cualquier excepción → `ROLLBACK` total: el número nunca se consideró
emitido. Garantías: monotonicidad y unicidad por constraint (`UNIQUE(lineage_id, revision)`), sin
reutilización para payloads distintos (la fila del libro guarda el payload exacto).

## Compuerta constitucional

P1 Spec antes que código ✅ · P2 autorización expresa ✅ (encargo) · P3 trazabilidad ✅ · P6
seguridad en backend ✅ · P9 instalación independiente ✅ (la autoridad no vive en el cliente) ·
P13 integridad transaccional ✅ · P14 infraestructura reproducible ✅ (imagen, compose,
migraciones) · P15 datos del cliente protegidos ✅ (la autoridad no guarda datos de negocio) · P21
paridad ✅ (concurrencia y migraciones en PostgreSQL) · P24 instalación limpia ✅ · P25 las altas
concurrentes las gobierna la base ✅ · P26 paridad modelos/migraciones ✅ · P27 mutaciones ✅.
G01–G40: todos ✅ salvo **G24 autenticación del sync: ❌ → bloqueo separado** (no detiene el núcleo
por regla del encargo). `MATERIAL OQ = 1` (sync), `UNKNOWN = 0`.
