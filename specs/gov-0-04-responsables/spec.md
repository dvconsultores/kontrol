# Spec · GOV-0-04 Responsables por objeto institucional, con historia (ORG-05) — BLOQUEADA

Estado: **BLOCKED_BY_DOMAIN_DEPENDENCIES** (2026-11-01). La Spec se detiene en la prueba de dependencias; no hay plan ni tareas
porque la compuerta de la Constitución no puede pasar (`ORG05_FULL_PROCESS_IMPLEMENTABLE = 0`).

## 1. Lo que podrá hacer el usuario (cuando se desbloquee)

Cuando este proceso esté terminado, el responsable de la organización institucional podrá dejar registrado quién responde por cada
unidad, programa, proyecto, cuenta, almacén, caja, cuenta bancaria, contrato y bien público del ente, desde y hasta qué fecha, por
qué y con qué acto; al cambiar de responsable quedará el anterior en el historial, y el auditor podrá saber quién respondía por
cualquiera de esos objetos en una fecha dada.

## 2. Fuentes

- IR v1.0 §7.1 GOV-ORG-006 (N03, N18, N20, N21; P0); requisitos de los dominios dueños: GOV-BUD-003, GOV-ACC-002, GOV-WH-003,
  GOV-TRE-001, GOV-TRE-009, GOV-CNT-001/004, GOV-AST-001/006; relacionados: GOV-ORG-007 (ORG-06), GOV-CTL-006/011, GOV-AST-015.
- Biblioteca Normativa v1.0: N18, N20, N21 (clase A; controles derivados «responsables, actas de entrega, hallazgos y acciones
  correctivas»), N34 (actas de entrega). Las fichas no fijan artículos para esta regla; no se cita ninguno.
- Matriz canónica de procesos y línea base de arquitectura de Gobierno.

## 3. Resultado de la prueba de dependencias

- `evidence/ORG05_TARGET_RESOURCE_MATRIX.md`: 9 clases de objeto; 1 disponible (UNIT), 8 sin modelo en Gobierno.
- `evidence/ORG05_BLOCKER_REPORT.md`: proceso indivisible; bloqueos B-ORG05-01..03; preguntas materiales OQ-ORG05-01..03.

## 4. Compuerta de la Constitución

| Puerta | Valor |
|---|---|
| CURRENT_BRANCH = develop · DEFAULT_BRANCH = develop · REMOTE_BRANCH_COUNT = 1 · HEAD_EQUALS_ORIGIN | 1 |
| ORG05_REQUIREMENTS_COMPLETE · ORG05_TARGET_RESOURCE_MATRIX_COMPLETE | 1 · 1 |
| UNCLASSIFIED_TARGET_RESOURCES | 0 |
| ORG05_FULL_PROCESS_IMPLEMENTABLE | **0** |
| RESPONSIBLE_PARTY_CONTRACT_COMPLETE · RESOURCE_REFERENCE_CONTRACT_COMPLETE | 0 (OQ-ORG05-01) · 0 (B-ORG05-01) |
| HISTORY_CONTRACT_COMPLETE · OVERLAP_CONTRACT_COMPLETE | 0 · 0 (dependen del objeto y del tipo de responsabilidad) |
| MATERIAL_BLOCKER · MATERIAL_OQ | 3 · 3 |

Sin implementación de producto. Se reanuda cuando la dueña resuelva OQ-ORG05-01..03 y existan los objetos dueños, o cuando una
decisión suya autorice una descomposición explícita.
