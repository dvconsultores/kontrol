# SPEC 046 · Delta dirigida — OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER

Dueña: 046 (Gestión Documental). Apoyo: 052 (instalación y composición; enlace en
`specs/001-fundacion/spec052-obs09-production-image-scanner-delta.md`) y 054 (QA; enlace en
`specs/012-auditoria-integral-e2e/spec054-obs09-production-image-scanner-delta.md`). Fecha: 2026-10-18. HEAD de partida
`6779f96`. Decisión `[x] OBS-09` con la **opción B ratificada**: `clamd` como servicio separado en Compose, streaming
INSTREAM, sin rutas ni almacén compartido, puerto interno, falso seguro sin alternativa implícita; cambio mínimo de producto
autorizado (adaptador). Evidencia en `evidence/obs09-production-image-scanner/`. Producción fuera de alcance.

## 1. Checkpoint — `checkpoint.md`
Sin runtime de contenedores en el equipo (`COMPOSE_RUNTIME_UNAVAILABLE`); PostgreSQL de QA reprovisionado tras el reinicio.
## 2. SOLICITUD/CAMBIO — `/speckit.specify`
La composición de producción no proporciona el analizador que el producto exige por defecto: una subida documental falla
cerrada con `SCAN_FAILED`. Integrar `clamd` como servicio propio (red interna, firmas en su dominio), un adaptador de
producto que transmite el contenido por INSTREAM (nunca rutas), selección explícita del analizador por configuración, sin
alternativa implícita ni fail-open, contrato de tamaño compatible con los 50 MiB de KONTROL, QA reproducible y contrato de
imagen/composición verificable. Requisitos: §9–§20 del encargo (arquitectura, abstracción, protocolo, tamaño, configuración,
falso seguro, composición, firmas, healthcheck, QA, pruebas O09, mutaciones).
## 3. `/speckit.clarify`
| Paso | Resultado | Evidencia |
|---|---|---|
| Estado actual | `ClamAVScanner` por proceso; selección por `KONTROL_DOCUMENT_SCAN`; sin analizador en `compose.yaml` ni en `Dockerfile.backend`; `GLOBAL_MAX_SIZE` 50 MiB; timeout 120 s; falso seguro en servicio | `current-state-inventory.md` |
| Causa raíz | `PRODUCTION_COMPOSITION_MISSING_SCANNER` + `BACKEND_SCANNER_CONTRACT_DEPLOYMENT_MISMATCH` (+ brechas de contrato de imagen y de cobertura QA) | `root-cause.md` |
| Demonio real | `clamd` 1.4.3 del paquete Debian arranca sin privilegios solo por TCP; INSTREAM con trozos y EOF; límites por defecto 25M < 50 MiB → el servicio debe configurar 60M; errores reconocibles | `clamd-control-measurements.md` |
| Imagen oficial | `clamav/clamav:<versión>` trae firmas y ejecuta `freshclam` como demonio (actualización en el dominio del analizador); `_base` sin firmas; configuración en `/etc/clamav`; puerto 3310; `/init-unprivileged`; healthcheck por `PING` | documentación oficial (docs.clamav.net) |
| Abstracción mínima | el contrato `FileSecurityScanner.scan(path)` se conserva: el adaptador `clamd` **lee** el temporal local y transmite bytes; la decisión CLEAN/INFECTED/SCAN_FAILED sigue en `service.upload_version` | `architecture.md` |
## 4. `/speckit.plan`
P1 configuración (`Settings.document_scanner`, `clamd_host`, `clamd_port`, validados) · P2 adaptador `ClamdScanner` (INSTREAM,
trozos de 64 KiB, EOF, respuesta terminada en `\0`, traducción `OK`/`FOUND`/`ERROR`/malformada/truncada/timeout/rechazo/
interrupción → SCAN_FAILED) y `get_scanner()` con selección explícita sin alternativa · P3 `Dockerfile.clamd` +
`deploy/clamd/clamd.conf` (60M/60M/100M, `AlertExceedsMax`) + servicio `clamd` en `compose.yaml` (sin `ports`, sin
almacén, healthcheck por `PING`, volumen de firmas) + variables del backend · P4 `qa/clamd_qa.py` (demonio real del paquete
Debian con la **misma** `clamd.conf` del despliegue adaptada, sondas CLEAN/EICAR/multi-trozo/máximo/demonio caído/timeout/
protocolo, comprobaciones estáticas de composición, informe de runtime) · P5 pruebas O09-01…25 (clamd falso programable) y
del QA · P6 mutaciones ≥ 10 · P7 certificación (dirigidas, SQLite ×2, PostgreSQL, E2E, OpenAPI) · P8 documentación y cierre.
## 5. CONSTITUTION GATE
HEAD 6779f96 · develop · opción B ratificada · dueña 046 (apoyo 052, 054) · inventario y causa raíz probados · contrato de
tamaño medido · diseño sin fail-open ni alternativa implícita · sin migración ni esquema · sin cambio de timeout (120 s se
conserva) · sin sleep/retry/skip/xfail/reorden/paralelismo · producción intacta · BLOCKER 0 para implementar en el repositorio
(**la demostración de la composición en contenedores queda condicionada al runtime**: ver `implementation-decision.md`) ·
CRITICAL 0 · CONTRADICTIONS 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 %.
## 6. `/speckit.checklist` — marcada con §3–§5 (inventario, causa raíz, límites, imagen oficial, abstracción, prohibiciones).
## 7. `/speckit.tasks`
| ID | Alcance | Ejecutor | Sensible | Ficheros | DONE_WHEN | Prueba |
|---|---|---|---|---|---|---|
| T01 | inventario + causa raíz + control del demonio | CLAUDE | — | ninguno | registros completos | — |
| T02 | configuración explícita del analizador | CLAUDE (CLAUDE_ONLY: seguridad) | sí | `app/core/config.py` | valores validados; defaults seguros | O09-12, 17, 18, 23 |
| T03 | adaptador `ClamdScanner` + selección | CLAUDE (CLAUDE_ONLY) | sí | `app/modules/documents/scanning.py` | INSTREAM; falso seguro en todas las ramas | O09-01…11, 14…16, 19…22, 24, 25 |
| T04 | imagen y composición | CLAUDE (CLAUDE_ONLY: despliegue) | sí | `Dockerfile.clamd`, `deploy/clamd/clamd.conf`, `compose.yaml`, `.env.example`, `docs/evidence/docker-validation-checklist.md` | contrato estático verificable | sondas estáticas |
| T05 | QA del demonio real | CLAUDE | sí | `qa/clamd_qa.py`, `tests/test_clamd_qa.py` | demonio real CLEAN/EICAR/multi-trozo/máximo/caído/timeout/protocolo | CLAMD-QA |
| T06 | mutaciones ≥ 10 | CLAUDE | — | — | todas detectadas | — |
| T07 | certificación | CLAUDE | — | — | suites 0 rojos | — |
| T08 | documentación, roadmap, cierre | CLAUDE | — | delta, enlaces 052/054, roadmap | — | — |
`RETRY_MAX: 2`; `DEEPSEEK CALLS = 0` (todo toca seguridad documental, despliegue o falso seguro).
## 8. `/speckit.analyze` (pre-implementación)
OBS09_SELECTED YES · OPTION B RATIFIED · OWNER 046 PROVEN · INVENTORY COMPLETE · ROOT_CAUSE PROVEN · SIZE_CONTRACT MEASURED ·
DESIGN FROZEN · PRODUCT_CHANGE_AUTHORIZED YES (solo adaptador y configuración) · MIGRATION/SCHEMA/TIMEOUT/RETRY/SLEEP/SKIP/
XFAIL/REORDER/PARALLELIZATION 0 · PRODUCTION_TOUCHED 0 · BLOCKER 0 (repositorio) · CRITICAL 0 · CONTRADICTIONS 0 · MATERIAL OQ 0 ·
UNKNOWN 0 · TRACEABILITY 100 %. **Autorización de implementación: la del encargo (opción B).**
## 9. Implementación — `implementation.md`, `configuration-contract.md`, `scanner-protocol.md`, `size-contract.md`, `compose-contract.md`
## 10. Pruebas y evidencia
O09-01…25 y CLAMD-QA-01…11 (`directed-tests.md`), demonio real (`clamd-qa-report.json`), 16/16 mutaciones
(`mutation-campaign.md`), dirigidas SQLite 278/0/54 y PostgreSQL 342/0/9, SQLite 1783/0/1046 ×2 (`sqlite-full-1.md`,
`sqlite-full-2.md`), PostgreSQL 2803/0/26 (`postgres-full.md`), E2E 284/0/0 (`global-e2e.md`), OpenAPI 544/533/11 (`openapi.md`).
## 11. Orquestación
Regla mandatoria desde el 2026-10-18 (DeepSeek escribe, Claude audita): T08-DOC (fila del README) por `deepseek-v4-flash`,
AUDIT_PASS, aplicado tal cual; el resto del código de este ciclo lo escribió Claude antes de la regla y se conservó (opción A).
## 12. Analyze final, trazabilidad y convergencia
`final-analyze.md`, `traceability-matrix.md`, `convergence.md`: **IMPLEMENTATION IN PROGRESS — BLOCKED BY ENVIRONMENT**
(`COMPOSE_RUNTIME_UNAVAILABLE`); pendiente la evidencia de composición en un equipo con Docker.
