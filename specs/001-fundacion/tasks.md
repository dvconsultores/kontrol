# TASKS — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Ruta | `specs/001-fundacion/tasks.md` |

## Convención

- Tareas atómicas, ordenadas, con dependencias, verificables y trazadas a requisitos y pruebas.
- Se ejecutan únicamente tras autorización expresa (`/speckit.implement`).
- Formato: | ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |

## Tareas

| ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |
|---|---|---|---|---|---|---|
| T-001 | NFR-001-010 | Crear estructura del repositorio (recursos, specs, docs, scripts, storage, backups) | — | estructura de `plan.md` | Build reproducible | Arquitecto |
| T-002 | NFR-001-010 | Crear `.gitignore` y `.dockerignore` (verificar no inclusión de secretos) | T-001 | `.gitignore`, `.dockerignore` | Escaneo de secretos | DevSecOps |
| T-003 | CHK-DOC-001 | Registrar hashes SHA-256 de `requerimientos/` en evidencia | — | `docs/evidence/hashes-documental.txt` | sha256sum | Doc. funcional |
| T-004 | FR-001-001 | Crear `compose.yaml` y `compose.dev.yaml` (frontend, backend, db, reverse-proxy) | T-001 | `compose.yaml`, `compose.dev.yaml` | `docker compose config` | Infraestructura |
| T-005 | FR-001-001 | Crear `.env.example` con variables `KONTROL_*` documentadas (sin secretos) | T-004 | `.env.example` | Validación de variables | DevSecOps |
| T-006 | FR-001-005 | Implementar validación de variables obligatorias y falla segura al inicio | T-004 | `backend/app/core/config.py` | Test de arranque | Backend |
| T-007 | FR-001-001 | Crear Dockerfiles multi-stage (backend Python 3.13, frontend Node→Nginx) no root | T-004 | `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf` | Build + scan | DevSecOps |
| T-008 | FR-001-080 | Implementar health endpoints liveness/readiness | T-004 | `backend/app/main.py` | Test de health | Backend |
| T-009 | FR-001-081 | Implementar logging JSON con request ID y correlation ID | T-004 | `backend/app/core/logging.py` | Test de logs | Backend |
| T-010 | FR-001-090 | Crear CLI `kontrol` (install, preflight, backup, restore, update, diagnose) | T-001 | `kontrol.py`, `scripts/*` | Pruebas de CLI | Infraestructura |
| T-011 | FR-001-002 | Generar identidad de instalación (uuid + par de claves) persistida en volumen | T-004 | `backend/app/modules/licensing/installation.py` | Test de persistencia | Backend |
| T-012 | FR-001-003 | Garantizar persistencia de identidad ante recreación de contenedores | T-011 | volúmenes `kontrol-license-state` | E2E recreación | Infraestructura |
| T-013 | FR-001-050 | Implementar verificación de firma de licencia (Ed25519) y `installation_id` | T-011 | `backend/app/modules/licensing/crypto.py` | Test de firma | Seguridad |
| T-014 | FR-001-051 | Implementar `LicenseState` y `LicenseArtifact` con copia firmada persistente | T-013 | modelos + migración | Test de estado | Datos |
| T-015 | FR-001-052 | Implementar cálculo de modo de acceso con fecha confiable (America/Caracas) | T-014 | `backend/app/modules/licensing/mode.py` | Test calendario | Backend |
| T-016 | FR-001-053 | Implementar middleware de licencia que bloquea escrituras en READ_ONLY | T-015 | `backend/app/core/license_middleware.py` | Test de bloqueo | Backend |
| T-017 | FR-001-054 | Implementar endpoints de licencia (status, activate, import, renewal-request, history, sync) | T-014 | `contracts/api-contracts.md` | Contract test | Backend |
| T-018 | FR-001-012 | Implementar hashing Argon2id y política de contraseñas | T-004 | `backend/app/core/security.py` | Test de contraseñas | Seguridad |
| T-019 | FR-001-020 | Implementar login/refresh/logout con cookies HttpOnly y rotación de refresh | T-018 | `backend/app/modules/identity_access/auth.py` | Test de autenticación | Seguridad |
| T-020 | FR-001-022 | Implementar sesiones visibles, revocables y cierre en todas las pestañas | T-019 | `Session` + endpoint | Test de sesiones | Backend |
| T-021 | FR-001-023 | Implementar rate limiting y bloqueo por fuerza bruta | T-019 | middleware | Test de límites | Seguridad |
| T-022 | FR-001-013 | Implementar recuperación de contraseña con token de un solo uso | T-019 | `PasswordReset` + endpoints | Test de recuperación | Backend |
| T-023 | FR-001-011 | Implementar cambio obligatorio de contraseña en primer acceso | T-019 | `must_change_password` | E2E | Backend |
| T-024 | FR-001-010 | Implementar asistente seguro de inicialización (empresa inicial + administrador) | T-011, T-019 | módulo setup | E2E | Backend |
| T-025 | FR-001-030 | Crear modelo Installation/Tenant/Company/Branch/Establishment/Warehouse/Location | T-014 | modelos + migraciones | Test de multiempresa | Datos |
| T-026 | FR-001-040 | Crear modelo Role/Permission/RolePermission/UserRole/UserScope | T-025 | modelos + migraciones | Test de permisos | Datos |
| T-027 | FR-001-041 | Implementar `allowed_actions` calculadas en backend | T-026 | endpoints | Contract test | Backend |
| T-028 | FR-001-042 | Implementar guards de ruta y permisos en frontend | T-030 | `frontend-foundation.md` | Component test | Frontend |
| T-029 | FR-001-070 | Implementar `AuditEvent` append-only y registro de eventos obligatorios | T-025 | modelos + servicio | Test de auditoría | Backend |
| T-030 | FR-001-060 | Crear sistema de diseño (tokens) y componentes base compartidos | — | `src/design-system`, `src/components` | Vitest componentes | UI/UX |
| T-031 | FR-001-060 | Implementar App Shell (Sidebar, Topbar, PageLayout, PageHeader, Breadcrumbs) | T-030 | `src/app` | Component test | Frontend |
| T-032 | FR-001-061 | Implementar router con rutas completas y estados (loading/empty/error/forbidden/not-found) | T-031 | `src/app/router` | E2E | Frontend |
| T-033 | FR-001-062 | Implementar pantalla completa para formularios complejos; sin modales de edición | T-030 | patrón WF-02 | Regresión visual | Frontend |
| T-034 | FR-001-063 | Implementar AsyncButton con loader, doble envío, éxito/error persistente y request ID | T-030 | `src/components/AsyncButton` | Vitest | Frontend |
| T-035 | FR-001-064 | Implementar UnsavedChangesGuard | T-031 | `src/components` | Component test | Frontend |
| T-036 | FR-001-065 | Implementar DataTable sin scroll horizontal, búsqueda, filtro, paginación | T-030 | `src/components/DataTable` | Vitest + visual | Frontend |
| T-037 | FR-001-066 | Aplicar WCAG 2.2 AA y responsive (móvil/tablet/laptop/desktop/zoom) | T-030 | componentes + rutas | axe + Playwright | QA |
| T-038 | FR-001-067 | Implementar contexto global de licencia, banner y bloqueo visual en READ_ONLY | T-015, T-031 | `src/app/license` | Component test | Frontend |
| T-039 | FR-001-054 | Implementar pantalla Mi licencia (ruta completa) | T-038 | WF-09 | E2E | Frontend |
| T-040 | FR-001-017 | Implementar páginas de inicio (dashboard fundacional) | T-032 | WF-07 | E2E | Frontend |
| T-041 | FR-001-082 | Implementar migraciones Alembic y seeds idempotentes | T-025 | `backend/alembic` | Test migraciones | Datos |
| T-042 | FR-001-083 | Implementar scripts de backup y restauración verificados | T-004 | `scripts/backup.sh`, `scripts/restore.sh` | Test restore | Infraestructura |
| T-043 | FR-001-084 | Implementar diagnóstico de instalación | T-011 | `scripts/diagnose.sh` | Prueba de diagnóstico | Infraestructura |
| T-044 | FR-001-091 | Crear estructura del núcleo fiscal (LegalSource, TaxRuleVersion, series, lotes) sin emisión | T-041 | `backend/app/modules/fiscal` | Test de modelo | Datos |
| T-045 | FR-001-082 | Configurar CI/CD (lint, type, test, build, migraciones, contratos, E2E, secretos, SBOM) | T-002 | `.github/workflows` | Pipeline verde | DevSecOps |
| T-046 | NFR-001-007 | Configurar observabilidad mínima (métricas, alertas) | T-009 | core | Test | Operación |
| T-047 | FR-001-080 | Crear evidencia de E2E de trayectoria fundacional | T-024..T-043 | `evidence/` | Playwright | QA |
| T-048 | CHK-LEG-002 | Revisión legal/contable de matriz normativa | — | `authority-matrix.md` | Revisión firmada | Legal |
| T-049 | NFR-001-010 | Fijar lockfiles y versiones con evidencia (resolver CL-11/12/13) | T-002 | lockfiles, `dependency-matrix.md` | Build + CVE | DevSecOps |

## Notas

- T-048 y T-049 son prerrequisitos de producción; no bloquean la fase documental.
- No existen tareas genéricas tipo "hacer backend"; todas son atómicas y verificables.

## Phase 1: Convergence

- [x] T050 Leer el estado de licencia del manifiesto por `installation_uuid` (no por `installations.id`) y probarlo con un estado de licencia sembrado per AD-B4 · NFR-001-008 (contradicts)
- [x] T051 Certificar EDGE-21 en el destino restaurado: estado de licencia idéntico al del punto de copia (C-12) y rechazo `LICENSE_PERIOD_DOWNGRADE` de una licencia de período anterior (C-13) per AD-B9 · EDGE-21 (partial)
- [ ] T052 Cumplir el RPO objetivo ≤15 min con planificación de copias o archivado continuo (BACKUP-SCHEDULE-RPO) per FR-001-083 (partial). Diseño: `spec001-backup-rpo-delta.md`; prerrequisitos: T053 y `T052_PREREQUISITE_AUDIT_TRUTHFULNESS`
- [ ] T053 Incluir `pg_dump`/`pg_restore` en la imagen de operaciones para que `kontrol.py backup` funcione en la composición (BACKUP-PG-TOOLS-IN-OPS-IMAGE) per T-010 · Principio 14 (partial). `T053_REQUIRED_FOR_T052 = 1`
- [ ] T054 Medir el RTO con el volumen real en el anfitrión de destino (BACKUP-RTO-DATOS-REALES) per NFR-001-008 (partial)
- [ ] T055 Humo de navegador sobre el destino restaurado (BACKUP-RESTORED-UI-SMOKE) per §84 del encargo 06 (partial)

## Phase 2: Convergence

- [ ] T056 Separar la autoridad de instalación (licencia, homologación, fuentes legales) de la del tenant, para que un administrador de un tenant no mute la configuración de la instalación (INSTALLATION-AUTHORITY-FROM-ANY-TENANT, BLOCKING_FINAL_GOV) per FR-001-040 (partial)
- [ ] T057 Implementar el alcance de usuario por sucursal/establecimiento/almacén (escritor de `UserScope.branch_id` y consumo de `CompanyContext.branch_ids`) o registrar la decisión de la dueña que lo descarte (WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO) per FR-001-040 (partial)
- [ ] T058 Plan de reparación, con OD y por instalación, de los roles personalizados heredados con `tenant_id` nulo; sin relleno sin autorización (ROLES-HEREDADOS-SIN-TENANT) per FR-001-040 / OD-ISO-11 (partial)
- [ ] T059 Rechazar con 422 o aplicar los campos declarados que hoy se ignoran (`traceability_profile_id`, `regulatory_profile_id`, `lot_ids`, `from_unit_id`, `source_id`) con prueba (CAMPOS-IGNORADOS-EN-ESQUEMA) per FR-001-032 (partial)
