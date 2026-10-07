# Aclaraciones — Autoridad Central Fase 1

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC004; `ISSUER_OWNER` = la propia autoridad (este componente); 052 apoyo de despliegue; 054 QA; `OWNER_IDENTITY_CONFLICT = 0` |
| 2 | Ubicación del código | `resources/backend/central_authority/` (paquete hermano de `app/`, mismo entorno, lockfile y base de imagen; entrypoint, settings, Alembic, compose e imagen **propios**). Frontera por importación: solo `app.core.license_contract` |
| 3–5 | Convenciones, versiones | FastAPI 0.115, SQLAlchemy 2.0, Alembic 1.14, pydantic-settings 2.7, cryptography 44, PostgreSQL 16; sin dependencias nuevas (CLI con `argparse`) |
| 6 | Alembic central | `central_authority/alembic.ini` + `central_authority/alembic/`, tabla de versión `cla_alembic_version`, una cabeza |
| 7 | Frontera de despliegue | `Dockerfile.central` (copia solo `app/__init__`, `app/core/__init__`, `app/core/license_contract.py` y `central_authority/`) y `compose.central.yaml` (postgres propio + api), red y volúmenes propios; no toca `compose.yaml` |
| 8 | Configuración de la clave | prefijo `KONTROL_CENTRAL_`: `KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM` (par de `KONTROL_LICENSE_PUBLIC_KEY_PEM` del cliente), `KONTROL_CENTRAL_SIGNING_KID`, `KONTROL_CENTRAL_DB_URL`, `KONTROL_CENTRAL_ENVIRONMENT` |
| 9 | Clave ausente en producción | `Settings` no carga (mismo contrato que `secret_key` y que el ancla del cliente); en cualquier entorno emitir sin clave → `SIGNING_KEY_MISSING`, nunca se genera |
| 10 | `kid` | configurado, por defecto `kontrol-lic-2026-01`; identifica la clave; no ordena |
| 11–12 | Paquete y canonicalizador | DOC-07 §10.2 + `revision`; `json.dumps(payload, sort_keys=True, ensure_ascii=False)` sobre el dict; `revision` dentro del dict firmado; legacy sin la clave |
| 13 | Firmante | Ed25519 `sign(canonical_bytes)`; clave privada cargada de la configuración, nunca registrada |
| 14–15 | Identidad y registro | `installation_uuid` (la que el cliente genera y envía en la solicitud de activación), clave pública de la instalación, `customer_id`, `contract_id`, `company_tax_id`, operador, fecha; único por `installation_uuid`; misma identidad con los mismos datos → idempotente; con datos distintos → `INSTALLATION_CONFLICT` |
| 16–21 | Sync | cliente anónimo (§6 de la spec): **bloqueado**; sin endpoint |
| 22–23 | Aislamiento e instalación desconocida | aplican al CLI: `INSTALLATION_NOT_FOUND` sin listar otras |
| 24–26 | Superficie y operador | CLI `python -m central_authority.cli`, `--operator` obligatorio (etiqueta operativa; **no** es autenticación remota; queda en libro y auditoría) |
| 27–28 | Libro | `cla_issuances` append-only: instalación, período, `revision`, `license_id`, `kid`, payload exacto, firma, hash, `issued_at` UTC, operador; sin API de edición ni borrado |
| 29–33 | Linaje y asignación | `cla_period_lineages` único por (instalación, inicio, fin) con `last_revision`; transacción: bloquear la fila de instalación (`FOR UPDATE`) → obtener/crear linaje → `last_revision + 1` → payload → firma → libro → linaje → auditoría → `commit`. Fallo de firma o persistencia → `rollback` completo: el número no se consideró emitido y puede volver a usarse (semántica documentada: sin huecos por fallo; huecos imposibles). Dos reemisiones concurrentes → N+1 y N+2 |
| 34–35 | Constraints e índices | `UNIQUE(installation_uuid)`, `UNIQUE(lineage: installation_id, period_start, period_end)`, `UNIQUE(issuance: lineage_id, revision)`, `UNIQUE(license_id)`, índices por instalación |
| 36–40 | Instalaciones, períodos, derechos | contadores independientes; `revision` reinicia por período; derechos libres |
| 41–42 | Fechas | `issued_at` UTC técnico; período anual DOC-07 en `-04:00` (Venezuela no tiene horario de verano) |
| 43 | Health | `/health/live` `{status, service}`, `/health/ready` `{status, service, database}` |
| 44–45 | Registro y auditoría | `cla_audit_events` (operador, operación, instalación, período, `revision`, `issuance_id`, resultado, fecha); sin PEM, firma ni URL |
| 46 | Código compartido | `app/core/license_contract.py` puro (constantes, `LicenseData` con `revision` opcional, `parse`, `canonical_bytes`, `payload_hash`, `sign`, `verify`, `compare_period`); `app/core/license.py` lo reexporta |
| 47–48 | Aislamiento del cliente | esquema y Compose del cliente intactos; prueba de grafo de importación |
| 49–50 | Compatibilidad del cliente | caso **A**: el cliente parsea un paquete con `revision` (clave extra en el dict; firma sobre el mismo dict) y lo acepta como reemisión; aún no compara `revision`. Despliegue **no** gatillado por parseo; el orden intra-período llega con el ciclo cliente |
| 51–57 | Pruebas | unitarias SQLite; instalación limpia y actualización de migraciones en PostgreSQL; carrera de emisión en PostgreSQL; contrato con el verificador y el `import_license` del cliente; contenedor por `docker compose config`/`bash -n`; mutaciones ≥ 8; regresión E2E del cliente |
| 58 | DeepSeek | pruebas puras del claim `revision` (T-DS) |

`MATERIAL OQ = 1` (sync), **separado** y sin bloquear el núcleo del emisor.
