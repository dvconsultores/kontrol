# TASKS · PROC-11

## Estado (2026-11-12)

Todas las tareas cerradas. Evidencia en `evidence/`; trazabilidad en `traceability.md`.

Traza: cada tarea declara el requisito y el criterio de aceptación que sirve.

## Datos y dominio

- [x] T01 Migración `0103_gov_proc11_sod_funciones`: tablas `gov_sod_role_rules` y `gov_sod_role_rule_history`, índices y
  checks (FR-002, FR-011).
- [x] T02 Modelos `GovernmentSoDRoleRule` y `GovernmentSoDRoleRuleHistory` en `government/models.py` (FR-002).
- [x] T03 Catálogo de funciones con etiqueta y fuente de ocupación, incluida `PAGADOR` no disponible (FR-001).

## Servicio

- [x] T04 Alta de regla en borrador, con validación de par y de no solapamiento (FR-002, FR-003).
- [x] T05 Activación y cierre con `If-Match`, MFA y auditoría (FR-003, FR-011, FR-012).
- [x] T06 Cálculo de ocupación por expediente con equivalencia de actor (FR-004).
- [x] T07 Detección por expediente y por período, con evidencia (FR-005, FR-007, FR-008).
- [x] T08 Guarda preventiva `verificar_antes_de_asumir_funcion` con evento REJECTION (FR-006, SC-002).
- [x] T09 CSV del listado con evento de exportación (FR-009, SC-005).

## Integración en el procedimiento

- [x] T10 Guarda en recepción de oferta (RECEPTOR) (FR-006).
- [x] T11 Guarda en asignación de responsable/requiriente (SOLICITANTE) (FR-006).
- [x] T12 Guarda en vinculación de comisión (EVALUADOR) (FR-006).
- [x] T13 Guarda en apertura de ofertas, aporte de evaluación y recomendación (EVALUADOR) (FR-006).
- [x] T14 Guarda en decisión (ADJUDICADOR) (FR-006, SC-002).

## API

- [x] T15 Esquemas Pydantic y rutas `/gobierno/sod/funciones/**` (FR-010).
- [x] T16 Ruta por expediente `/gobierno/contrataciones/expedientes/{id}/conflictos-funciones` (FR-008).
- [x] T17 Catálogo de auditoría: 5 acciones y versión (FR-012).

## Interfaz

- [x] T18 Cliente `api.ts`: catálogo, reglas, alta, activar, cerrar, conflictos y CSV (FR-013).
- [x] T19 Pantalla «Funciones incompatibles» con matriz, formulario y listado de conflictos (FR-013).
- [x] T20 Menú, ruta y registro de pantalla para la matriz de autoridad (FR-013).
- [x] T21 Bloque de conflictos en la ficha del expediente (FR-008, FR-013).

## Pruebas

- [x] T22 Backend: ciclo de vida de la regla, detección, bloqueo, aislamiento, permisos y CSV (SC-001..005).
- [x] T23 Frontend: pantalla y bloque del expediente (SC-006).
- [x] T24 E2E: SC-001, SC-002, SC-003 (E2E-07).

## Cierre

- [x] T25 Matrices, tarjeta de UAT, evidencia y Observaciones abiertas.
