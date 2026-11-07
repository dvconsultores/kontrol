# KONTROL Enterprise · línea base vigente

Ciclo `ENTERPRISE-REBASELINE-AND-NEXT-WORK-GATE-01` (P2), 2026-11-06, solo lectura. Reconciliado contra `develop` `dbcf510`.

Este documento **no sustituye** a ninguna fuente canónica: inventario en `../master-56-specs-status.md`, deuda en
`../technical-debt-matrix.md` y `../technical-debt-roadmap.md`, punteros en `../next-spec-decision.md`. Solo fija la lectura
Enterprise de esas fuentes en esta fecha. Matriz de trabajo: `ENTERPRISE_WORK_MATRIX_CURRENT.md`.

Marcas: **MEASURED** (visto en el árbol en este ciclo), **RECORDED** (evidencia versionada, no reejecutada aquí), **DERIVED**
(deducción), **NOT_MEASURED**.

## 1. Respuesta corta

| Pregunta | Respuesta |
|---|---|
| Estado real de Enterprise | 57 Specs maestras: 20 `COMPLETE/CONVERGED` técnicas más la 046 `RECONVERGED`, 26 parciales (contando la 023), 6 bloqueadas por validación legal, 1 por servicio externo, 1 por decisión de negocio, 2 sin iniciar (018 y 057). La completitud de producto Enterprise **no está medida** |
| ¿Qué afectó a Enterprise desde su baseline? | 30 commits, todos de Gobierno. Cambios aditivos en núcleo compartido, sin regresión registrada. Detalle en §3 |
| ¿Siguen válidos los cierres? | Sí: ninguna regresión reproducida ni contrato cambiado. Sin reejecución en este ciclo |
| ¿SPEC054? | `IMPLEMENTED_CERTIFICATION_PENDING`: falta la corrida oficial RC 0 en anfitrión dedicado |
| ¿T052 sigue HIGH? | Sí: OPEN, HIGH y aplicable a Enterprise. Exige decisiones de la dueña antes de implementar |
| ¿SPEC057 puede iniciarse? | Todavía no: `SPEC057_READY_TO_START = 0` |
| Siguiente ciclo P2 | `T052-RPO-DESIGN-AND-OWNER-DECISION-GATE` (diseño, sin implementación) |

## 2. Estado Git de entrada

| Campo | Valor |
|---|---|
| `ENTRY_HEAD` | `dbcf510f48aef78993f02607e4027cec5c199b69` |
| `ORIGIN_HEAD` | igual, **solo como referencia local**: `git fetch` y `ls-remote` fallaron por falta de credenciales |
| Rama / ramas remotas conocidas | `develop` / 1 |
| Último commit Enterprise o núcleo | `9eaf3d4` (2026-10-29) |
| Árbol | `scripts/install-deepseek-mcp.sh` sin seguimiento (herramienta local de este puesto, ajena a este ciclo) |

## 3. Reconciliación de commits `9eaf3d4..dbcf510`

| Grupo | Nº | Clasificación | Cambia |
|---|---|---|---|
| `feat(government)` | 12 | GOVERNMENT, con superficie SHARED_CORE | esquema (0063–0074), API `/gobierno/**`, frontend, pruebas, QA |
| `test(government)` | 2 | QA_ONLY con arnés compartido | pruebas y `playwright.config.ts` |
| `docs(government)` | 16 | DOC_ONLY | documentación |

Tras `b20e7b7` no cambió nada en `resources`, `qa`, `scripts`, `compose.yaml` ni `Dockerfile.backend` (MEASURED).

Núcleo compartido tocado (MEASURED, sobre el diff):

| Superficie | Cambio | Impacto Enterprise |
|---|---|---|
| `core/dependencies.py` | `require_module`, denegación por defecto | Nulo fuera de `/gobierno`: los 12 routers de Gobierno lo aplican |
| `core/database.py`, `main.py` | registro de modelos y routers | Aditivo. El OpenAPI de una instalación Enterprise publica también `/gobierno/**`, denegado por licencia |
| `licensing/service.py` | módulo `gobierno` | Aditivo |
| `setup/api.py`, `mfa_policy.py`, `audit_catalog_entries.py` | catálogos `gobierno_*` | Aditivo. Existen en todas las instalaciones |
| `documents/{api,resources,service}.py` | se mueve la comprobación de acceso por vínculo a `service` y se añaden tipos de recurso | Refactor en superficie Enterprise, cubierto por las suites registradas |
| `Sidebar.tsx` | sección Gobierno condicionada a la licencia | Sin cambio con licencia Enterprise |
| `CompanySelector`, `EstadoDeEmpresa`, `NotificationContext`, `AdjuntosPanel`, `fecha-de-negocio` | ajustes de texto y parámetros para ente/empresa | Revisar con la dueña si el vocabulario Enterprise se conserva (NOT_MEASURED) |
| `playwright.config.ts`, `e2e/auditoria-sobre.spec.ts` | Firefox aislado de cambios de red; eventos sin consumir pasos TOTP | Mejora del arnés |
| `tests/test_audit_immutability.py` | IMM-04 reforzada (`TRUNCATE` y `CASCADE`) | Refuerza un cierre |

**Última evidencia sobre el árbol de producto vigente (RECORDED, `specs/gov-tre-02-programacion-financiera/evidence/REQUIRED_SUITE_INVENTORY.md`):**
PostgreSQL 4463/0/18, SQLite 2792/0/1689, vitest 1235/1235, tsc 0, eslint 0, build correcto, ruff limpio, mypy 154 (línea base),
E2E canónica 448/448 sin reintentos, `scope_scan` 0. Son corridas de P1 en la estación multiproyecto: **no** son la certificación
oficial de release.

## 4. Cierres preservados

`EXISTING_CLOSURE_PRESERVED = 1` para los cierres siguientes: `REGRESSION_REPRODUCED = 0` y `AUTHORITATIVE_CONTRACT_CHANGED = 0`.

MFA/TOTP de roles sensibles (`d39f820`) · reset de contraseña (`464c913`) · techo de delegación (`021c1c6`) · autoridad por empresa
(`56f0f5e`, `fb8ead1`) · permisos de lectura declarados (`36f076c`) · aislamiento tenant/empresa (`9eaf3d4`) · America/Caracas e
instantes UTC (`b24b121`) · catálogo y append-only de auditoría, incluido el rechazo por malware (`49540a6`) · contrato estricto:
422 por parámetro no declarado y por datetime naive (`f24e74e`) · copia y restauración verificadas (`0dbe632`) · S3 fail-closed
(`91eae11`) · separación runtime/certificación de la imagen (`3300183`).

## 5. Estado maestro

`MASTER_SPEC_COUNT = 57`. `MASTER57_STATUS`: vigente desde 2026-10-07; Gobierno queda fuera de la numeración.
`NEXT_MASTER_SPEC = NOT YET PRIORITIZED` (decisión de la dueña, 2026-10-07, sin cambio posterior).

| Estado | Specs |
|---|---|
| `COMPLETE / CONVERGED` | 008, 011, 012, 013, 019, 020, 021, 022, 029, 030, 031, 032, 033, 034, 035, 036, 037, 038, 045, 047 |
| `RECONVERGED` | 046 |
| `PARTIALLY_IMPLEMENTED` | 001, 002, 003, 005, 006, 007, 009, 010, 014, 015, 016, 017, 023 (multiestado cerrado), 024, 025, 026, 027, 028, 048, 049, 050, 051, 052, 053, 054, 055 |
| `BLOCKED_BY_LEGAL_VALIDATION` | 039, 040, 041, 042, 043, 056 |
| `BLOCKED_BY_EXTERNAL_SERVICE` | 044 |
| `BLOCKED_BY_BUSINESS_DECISION` | 004 |
| `NOT_STARTED` | 018 |
| `PLANNED / NOT_STARTED` | 057 |

Esa tabla es técnica. Las tres métricas Enterprise (fundamento, producto funcional, listo para la dueña) son **NOT_MEASURED**: no
existe cálculo canónico reproducible, y la retrospectiva privada depende de `MOQ-RETRO-01`. Las cifras de Gobierno no se trasladan.

## 6. SPEC054

`SPEC054_STATUS = IMPLEMENTED_CERTIFICATION_PENDING`. Orden `qa/certificar-release.py` implementada; decisión OD-CERT-30 sin
cierre posterior. `qa/certificaciones/` no existe en este puesto y ningún documento registra una corrida oficial RC 0. Falta
anfitrión dedicado: Debian 13 amd64, 12 CPU lógicas o más, 16–24 GB, 25–50 GB SSD, swap ≥ 4 GiB (CERTIFICATION-HOST-INFRASTRUCTURE,
`BLOCKED_BY_PROVIDER_ACCESS`). El hash del árbol hará que esa corrida certifique también todo el trabajo posterior, incluido Gobierno.

## 7. SPEC057

`SPEC057_STATUS_CURRENT = PLANNED / NOT_STARTED`; sin carpeta en `specs/`. `SPEC057_READY_TO_START = 0`:

1. Hay un HIGH Enterprise de continuidad abierto (T052).
2. `NEXT MASTER SPEC` no está priorizada por la dueña.
3. De las dependencias del PDF §33.1, siguen parciales 007, 009, 017, 026 y 027; 018 no ha empezado.

Sí están convergidas 013, 019, 045 y 046, y ya hay ingeniería de requisitos propia con ciclos AF-1..AF-5 (18–27 días laborables).
Primer ciclo cuando se autorice: `SPEC057_DISCOVERY_AND_SPECIFY`.

**Contradicción de orden, a decidir por la dueña:** el PDF §33.2 sitúa «Release / backup / DR / hardening» después de la 057,
mientras que el orden de impacto de este encargo pone backup/RPO antes de la funcionalidad nueva. Se aplica el segundo por ser
posterior.

## 8. Copia, restauración y RPO (MEASURED salvo indicación)

| Hecho | Consecuencia |
|---|---|
| FR-001-083 es P0 y fija RPO ≤15 min y RTO ≤4 h **como objetivo** | El requisito sigue vigente en Enterprise |
| T052..T055 siguen sin marcar en `specs/001-fundacion/tasks.md` | Abiertas |
| No hay planificación de copias ni manejador de backup en el planificador | RPO `DEPENDS_ON_BACKUP_SCHEDULE` |
| `compose.yaml` no incluye PostgreSQL: `KONTROL_DB_URL` apunta a una base externa | KONTROL no controla WAL ni `archive_mode` |
| `Dockerfile.backend` no instala `pg_dump`/`pg_restore` | `kontrol.py backup` falla en la composición con `PG_TOOLS_MISSING` (T053) |
| `check_tool_compatible` exige cliente ≥ versión mayor del servidor | La versión del cliente depende de la base externa de cada instalación |
| `cmd_scheduler_tick` no pasa `KONTROL_BACKUP_KEY`, y `compose.yaml` no la declara en `backend` | Una copia lanzada desde el tick no tendría clave |
| OD-BK-09: sin retención ni borrado | Copias cada 15 min sin retención crecen sin límite |
| El volumen `kontrol-backups` vive en el mismo anfitrión | No protege de la pérdida del anfitrión |
| RTO 5,1 s sobre datos sintéticos (RECORDED) | No extrapolable (T054) |

## 9. Hallazgos nuevos, registrados y no corregidos

| ID propuesto | Severidad propuesta | Hecho |
|---|---|---|
| KONTROL-PY-UPDATE-NO-OP | MEDIUM | `kontrol.py update` imprime los pasos y devuelve 0 sin ejecutar nada; `scripts/update.sh` sí actúa, pero ignora el fallo del preflight (`\|\| true`) |
| DOC-ESTADO-OBSOLETO-TRAS-HARDENING | LOW | Filas sin actualizar: la 002 dice «MFA declarado y no construido»; `API-QUERY-SILENCIOSA` y `ROLES-SIN-TECHO-DE-DELEGACION` constan como OPEN pese a su cierre posterior; la 001 cita 57 migraciones y hay 74 |
| ORCH-READINESS-FALSO-NEGATIVO | LOW | `orchestration_readiness.py` busca `Solo \`develop\`` y `CLAUDE.md` dice «solo `develop`»: 11/12 con la orquestación certificada 10/10 |
| ESTACION-SIN-CREDENCIAL-GIT | Operativo | Este puesto no tiene credencial para `github.com`: sin `fetch` ni `push` |

## 10. Contradicción de gobierno para la dueña

`.claude/CLAUDE.md` y la política de orquestación reservan a Claude migraciones, seguridad, aislamiento de tenant y reglas fiscales
(`CLAUDE_ONLY`). La regla mandatoria de 2026-10-18, los ciclos de Gobierno y este encargo piden que DeepSeek escriba **todo** el
código, incluidas migraciones. No bloquea este ciclo, pero debe resolverse antes de implementar: es decisión de la dueña.
