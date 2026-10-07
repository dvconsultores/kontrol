# Tareas — Autoridad Central Fase 1

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, artefactos Spec Kit | todos | CLAUDE | YES | n-a | este directorio |
| T02 | Contrato puro `app/core/license_contract.py`; `license.py` reexporta; cliente mapea `LicenseContractError` → 423 | 312, 313, 317 | CLAUDE | **YES** | n-a | `app/core/`, `licensing/service.py` |
| T03 | `central_authority/`: config, modelos, Alembic, servicio, CLI, main | 267–311 | CLAUDE | **YES** | n-a | `central_authority/` |
| T04 | `Dockerfile.central`, `compose.central.yaml`, `entrypoint.sh`, `README.md` | 302, 303 | CLAUDE | YES | n-a | raíz, `central_authority/` |
| T05 | Pruebas `tests/central/`: settings, registro, emisión, contrato, compatibilidad, legacy, libro, health, grafo de importación, migraciones (PG), carrera (PG), CLI | 279–318 | CLAUDE | **YES** | n-a | `tests/central/` |
| T06 | Pruebas puras del claim `revision` (parser) | 281, 282 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `tests/central/test_revision_claim.py` |
| T07 | Auditar T06; mutaciones M-01..M-10 | — | CLAUDE | NO | n-a | — |
| T08 | Suites completas (cliente, dos motores); E2E dirigido y global; ADR-D0-006, D0-06, hoja de ruta, Git | 319–321 | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T06. `analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`;
huérfanos = 0; `MATERIAL OQ = 1` (sync, separado del núcleo); `UNKNOWN = 0`; trazabilidad 100 %.
**Autorización de `implement`:** la del encargo, para el núcleo del emisor; la API de sync queda fuera.
