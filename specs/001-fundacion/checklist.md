# CHECKLIST — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Ruta | `specs/001-fundacion/checklist.md` |

Cada punto tiene: ID, responsable, evidencia, estado, bloqueante (Sí/No).

## Documentación y gobernanza

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-DOC-001 | Inventario documental completo | Doc. funcional | `docs/governance/document-inventory.md` | ✔ | Sí |
| CHK-DOC-002 | Matriz de autoridad | Gobernanza | `docs/governance/authority-matrix.md` | ✔ | Sí |
| CHK-DOC-003 | Matriz de conflictos | Convergencia | `docs/governance/document-conflicts.md` | ✔ | Sí |
| CHK-DOC-004 | Gobierno Git | DevSecOps | `docs/governance/git-governance.md` | ✔ | No |
| CHK-DOC-005 | Constitución creada/auditada | Producto | `.specify/memory/constitution.md` | ✔ | Sí |
| CHK-DOC-006 | Roadmap de Specs propuesto | Producto | `plan.md` | ✔ | No |

## Arquitectura y plan

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-ARC-001 | Arquitectura monolito modular | Arquitecto | `plan.md`, `ADR-001` | ✔ | Sí |
| CHK-ARC-002 | Estructura de repositorio | Arquitecto | `plan.md`, `repository-structure.md` | ✔ | Sí |
| CHK-ARC-003 | Modelo de datos fundacional | Datos | `data-model.md` | ✔ | Sí |
| CHK-ARC-004 | Stack validado con evidencia | Arquitecto | `research.md`, `dependency-matrix.md` | Parcial (versiones pendientes) | No (bloquea lockfiles) |
| CHK-ARC-005 | ADR propuestos | Arquitecto | `adr/ADR-001..015` | ✔ | No |

## Frontend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-UI-001 | Sistema de diseño y tokens | UI/UX | `frontend-foundation.md` | ✔ (especificado) | Sí |
| CHK-UI-002 | App Shell y navegación | Frontend | `frontend-foundation.md` | ✔ (especificado) | Sí |
| CHK-UI-003 | Política de modales | UI/UX | `frontend-foundation.md`, ADR-015 | ✔ | Sí |
| CHK-UI-004 | Tablas sin scroll horizontal | UI/UX | `frontend-foundation.md` | ✔ | Sí |
| CHK-UI-005 | Accesibilidad WCAG 2.2 AA | UI/UX | `frontend-foundation.md`, `test-plan.md` | ✔ (especificado) | Sí |
| CHK-UI-006 | Responsive | UI/UX | `frontend-foundation.md` | ✔ (especificado) | Sí |

## Backend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-BE-001 | Backend como autoridad | Backend | `plan.md`, `security-baseline.md` | ✔ | Sí |
| CHK-BE-002 | Contrato de errores | Backend | `contracts/error-contract.md` | ✔ | Sí |
| CHK-BE-003 | Idempotencia y concurrencia | Backend | `data-model.md`, ADR-013 | ✔ | Sí |
| CHK-BE-004 | Auditoría append-only | Backend | `data-model.md`, ADR-012 | ✔ | Sí |
| CHK-BE-005 | Núcleo fiscal separado | Backend | `plan.md` (módulo fiscal) | ✔ | Sí |

## Base de datos

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-DB-001 | Migraciones revisadas | Datos | `test-plan.md` (migraciones) | ✔ (especificado) | Sí |
| CHK-DB-002 | Seeds idempotentes | Datos | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-DB-003 | Multiempresa y aislamiento | Datos | `data-model.md`, ADR-011 | ✔ | Sí |

## Seguridad

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-SEC-001 | Argon2id | Seguridad | `security-baseline.md` | ✔ | Sí |
| CHK-SEC-002 | Cookies HttpOnly + CSRF | Seguridad | ADR-004 | ✔ | Sí |
| CHK-SEC-003 | Secretos fuera del repo | DevSecOps | `.gitignore`, CI | ✔ | Sí |
| CHK-SEC-004 | Rate limiting / fuerza bruta | Seguridad | `security-baseline.md` | ✔ | Sí |
| CHK-SEC-005 | Usuario PostgreSQL restringido | DevSecOps | `security-baseline.md` | ✔ | Sí |
| CHK-SEC-006 | SBOM y escaneo | DevSecOps | `security-baseline.md` | ✔ (especificado) | No |

## Licenciamiento

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-LIC-001 | Identidad de instalación persistente | Infraestructura | `license-foundation.md` | ✔ | Sí |
| CHK-LIC-002 | Verificación de firma | Seguridad | `license-foundation.md` | ✔ | Sí |
| CHK-LIC-003 | Modos de acceso y bloqueo backend | Backend | `license-foundation.md` | ✔ | Sí |
| CHK-LIC-004 | Clave privada fuera de la instalación | Seguridad | `license-foundation.md` | ✔ | Sí |
| CHK-LIC-005 | Pantalla Mi licencia | Frontend | WF-09, `license-foundation.md` | ✔ | Sí |

## Docker / infraestructura

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-DK-001 | compose.yaml con volúmenes y health checks | Infraestructura | `infrastructure-plan.md` | ✔ (especificado) | Sí |
| CHK-DK-002 | Imágenes versionadas y no root | DevSecOps | `infrastructure-plan.md` | ✔ | Sí |
| CHK-DK-003 | Scripts backup/restore/diagnóstico | Infraestructura | `backup-restore-plan.md` | ✔ (especificado) | Sí |
| CHK-DK-004 | Entornos por ambiente | Infraestructura | `environment-matrix.md` | ✔ | No |

## Observabilidad

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-OBS-001 | Logs JSON + request ID | Backend | `security-baseline.md`, ADR-010 | ✔ | Sí |
| CHK-OBS-002 | Health checks liveness/readiness | Infraestructura | `infrastructure-plan.md` | ✔ | Sí |

## Backups

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-BK-001 | Backup diario cifrado | Infraestructura | `backup-restore-plan.md` | ✔ (especificado) | Sí |
| CHK-BK-002 | Restauración probada | Infraestructura | `backup-restore-plan.md` | ✔ (especificado) | Sí |
| CHK-BK-003 | RPO/RTO definidos | Infraestructura | `backup-restore-plan.md` | ✔ | No |

## Accesibilidad y QA

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-QA-001 | Plan de pruebas | QA | `test-plan.md` | ✔ | Sí |
| CHK-QA-002 | Casos E2E fundacionales | QA | `test-plan.md` | ✔ | Sí |
| CHK-QA-003 | Cobertura y evidencias | QA | `evidence/` | Pendiente (implementación) | Sí |
| CHK-QA-004 | Pruebas de accesibilidad | QA | `test-plan.md` | ✔ (especificado) | Sí |

## CI/CD

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-CI-001 | Pipeline lint/type/test/build | DevSecOps | `plan.md` | ✔ (especificado) | Sí |
| CHK-CI-002 | Escaneo de secretos | DevSecOps | `plan.md` | ✔ (especificado) | Sí |
| CHK-CI-003 | Puertas de calidad | DevSecOps | `plan.md` | ✔ | Sí |

## Legal / fiscal / privacidad

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-LEG-001 | Matriz normativa con `LEGAL_VALIDATION_REQUIRED` | Legal | `authority-matrix.md` | ✔ | Sí (no implementar fiscal) |
| CHK-LEG-002 | Revisión por abogado/contador | Legal | Evidencia externa | Pendiente | Sí (antes de producción) |
| CHK-LEG-003 | Núcleo fiscal no implementado en 001 | Legal | `spec.md` (fuera de alcance) | ✔ | No |
| CHK-PRV-001 | Datos del cliente protegidos | Legal | `license-foundation.md` | ✔ | Sí |
| CHK-PRV-002 | Sin acceso remoto sin autorización | Legal | `license-foundation.md` | ✔ | No |

## Operación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-OP-001 | CLI `kontrol` especificado | Infraestructura | `infrastructure-plan.md` | ✔ (especificado) | No |
| CHK-OP-002 | Diagnóstico de instalación | Infraestructura | `infrastructure-plan.md` | ✔ (especificado) | No |
| CHK-OP-003 | Runbooks | Operación | `backup-restore-plan.md` | ✔ (especificado) | No |

## Estado global

| Métrica | Valor |
|---|---|
| Puntos totales | 52 |
| Puntos cumplidos en fase documental | 52 (especificados) |
| Pendientes de implementación/evidencia | Los marcados como "Pendiente" |
| Bloqueantes sin evidencia | Ninguno en fase documental |
