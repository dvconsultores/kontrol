# CHECKLIST — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Ruta | `specs/002-maestros/checklist.md` |

Formato: | ID | Punto | Responsable | Evidencia | Estado | Bloqueante |

## Documentación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-002-DOC-001 | Spec 002 completa | Producto | `spec.md` | ✔ | Sí |
| CHK-002-DOC-002 | Clarificaciones | Funcional | `clarifications.md` | ✔ | Sí |
| CHK-002-DOC-003 | Research técnico | Arquitecto | `research.md` | ✔ | No |
| CHK-002-DOC-004 | Plan y modelo de datos | Arquitecto/Datos | `plan.md`, `data-model.md` | ✔ | Sí |
| CHK-002-DOC-005 | Trazabilidad | Convergencia | `traceability-matrix.md` | ✔ | Sí |

## Datos y modelo

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-002-DB-001 | Party común + extensiones | Datos | `data-model.md` | ✔ | Sí |
| CHK-002-DB-002 | Atributos gobernados (sin EAV libre para datos críticos) | Datos | `data-model.md`, `research.md` | ✔ | Sí |
| CHK-002-DB-003 | Taxonomía jerárquica configurable | Datos | `data-model.md` | ✔ | Sí |
| CHK-002-DB-004 | Perfiles versionados | Datos | `data-model.md` | ✔ | Sí |
| CHK-002-DB-005 | Migración `0002_maestros` (upgrade/downgrade) | Datos | Alembic | Pendiente (implementación) | Sí |

## Backend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-002-BE-001 | Duplicidad de RIF por empresa/rol | Backend | constraints + servicio | ✔ (especificado) | Sí |
| CHK-002-BE-002 | `allowed_actions` en maestros | Backend | contratos | ✔ | Sí |
| CHK-002-BE-003 | Aprobación de proveedor antes de pagar | Backend | `data-model.md` | ✔ | Sí |
| CHK-002-BE-004 | Búsqueda asíncrona backend | Backend | `api-contracts.md` | ✔ | Sí |
| CHK-002-BE-005 | Aislamiento multiempresa | Backend | pruebas negativas | ✔ (especificado) | Sí |

## Frontend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-002-UI-001 | Asistente de producto (pantalla completa) | Frontend | WF-002-A | ✔ (especificado) | Sí |
| CHK-002-UI-002 | Maestro de tercero (pantalla completa) | Frontend | WF-002-B | ✔ (especificado) | Sí |
| CHK-002-UI-003 | Listados sin scroll horizontal | Frontend | hereda 001 | ✔ | Sí |
| CHK-002-UI-004 | AsyncCombobox para catálogos grandes | Frontend | `research.md` | ✔ | Sí |
| CHK-002-UI-005 | Servicio sin lote/serial/almacén | Frontend | `spec.md` FR-002-022 | ✔ | Sí |
| CHK-002-UI-006 | WCAG 2.2 AA y responsive | QA | hereda 001 | ✔ (especificado) | Sí |

## QA y operación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-002-QA-001 | Plan de pruebas 002 | QA | `test-plan.md` | ✔ | Sí |
| CHK-002-QA-002 | Pruebas de aislamiento negativo | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-002-QA-003 | Pruebas de duplicidad y conversiones | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-002-OP-001 | Seeds idempotentes (unidades, rubros opcional) | Datos | `plan.md` | ✔ (especificado) | No |

## Estado global

| Métrica | Valor |
|---|---|
| Puntos totales | 27 |
| Cumplidos (fase documental) | 27 (especificados) |
| Bloqueantes sin evidencia en fase documental | Ninguno |
| Implementación | Pendiente — requiere 001 certificada y autorización |
