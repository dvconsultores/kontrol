# GOV-CTL-10 · ANALYZE_REPORT

Ejecutado con `/speckit-analyze` el 2026-11-06 sobre `spec.md`, `plan.md`, `tasks.md` (41 tareas), `data-model.md`, `contracts/api.md`, `research.md` y las matrices de `evidence/`. Solo lectura, salvo la corrección de A1 descrita abajo, hecha por el autor de los artefactos antes de dar el informe por cerrado.

## Hallazgos

| ID | Categoría | Severidad | Ubicación | Resumen | Resolución |
|---|---|---|---|---|---|
| I1 | Inconsistencia | HIGH | spec FR-008, US3-2, data-model (Estados) vs DISENO («activate SENSITIVE (MFA) para activar y retirar») | El borrador del plan decía que retirar un BORRADOR no exige MFA y que el motivo era opcional; contradecía la capacidad única `activate` SENSITIVE | CORREGIDO en spec, data-model y tasks: retirar exige MFA y motivo 10–500 desde BORRADOR y VIGENTE |
| I2 | Inconsistencia | MEDIUM | DISENO §Guarda («DESPUÉS de estado y SoD») vs `service_estructura.cerrar` | ORG-02 no está en `CATALOGO_SOD` y su cierre no llama a SoD; CTL-10 no añade ORG-02 al catálogo (fuera de alcance) | Documentado en `CTL10_CLOSE_ACTION_INTEGRATION_MATRIX.md`: SoD «no aplica» en ORG-02; la guarda va tras estado y ejercicio terminado. No cambia el diseño |
| U1 | Subespecificación | MEDIUM | DISENO (`objeto_codigo`) vs modelo `gov_structures` (sin código) | La estructura no tiene código propio | Se fija `EST-<ejercicio>` derivado, en la matriz y en la tarea de integración. Puntual y reversible; se informa a la dueña |
| C1 | Alcance | LOW | OD-CTL10-01 (lista de ficheros compartidos) vs tareas que editan `service_sod.py`, `service_auditoria.py`, `schemas_sod.py`, `service_estructura.py`, `service_caja.py`, `models.py` | Esos ficheros no están en la lista literal, pero son del módulo Gobierno y el propio DISENO ordena esas ediciones (CTL-04, CTL-01, guarda) | Sin acción. SHARED_CORE_CHANGE_REQUIRED = 0 se mantiene con la nota del plan |
| P1 | Orden | LOW | tasks T001–T003 (registro) antes de los RED de las historias | Ediciones de registro preceden al primer RED | Cubiertas por pruebas de recuento existentes que se actualizan; los RED de cada historia preceden a su código. Sin acción |
| P2 | Procedimiento | LOW | Constitución P2 | `implement` aún no tiene la autorización expresa que nombra la iniciativa | Pendiente de la dueña; no es parte de esta fase |

## Resumen por severidad

| Severidad | Abiertos | Corregidos |
|---|---|---|
| CRITICAL | 0 | 0 |
| HIGH | 0 | 1 (I1) |
| MEDIUM | 2 (I2, U1: documentados, no bloquean) | 0 |
| LOW | 3 (C1, P1, P2) | 0 |

## Cobertura

- Requisitos: 26 FR y 7 SC. FR con al menos una tarea: 26/26 (FR-025 es NOT_APPLICABLE y queda declarado, sin tarea). Cobertura 100 %.
- Tareas sin requisito: 0 (las tareas de certificación mapean a SC-001..SC-007 y a la norma de completitud).
- Tareas totales: 41. CLAUDE: 7 (certificación, mutaciones, evidencia, métricas, UAT, Git). DEEPSEEK: 34. MANUAL/OWNER: 0.
- Cada tarea lleva EXECUTOR, MODEL, SECURITY_SENSITIVE, EGRESS_SAFE, RETRY_MAX 2, FILES, TEST y DONE_WHEN.
- Pantallas: 4 más un panel, todas en la matriz. Inventario de cierres: 2 integrados, 3 no integrados más 2 que no son cierre.

## Compuertas

BLOCKER = 0 · CRITICAL = 0 · CONTRADICTIONS = 0 · OWNER CONFLICT = 0 · ORPHANS = 0 · MATERIAL OQ = 0 · UNKNOWN = 0 · trazabilidad 100 %.

Contradicciones reales con el diseño cerrado: ninguna. I2 y U1 son huecos del diseño frente al código existente, resueltos sin reabrir decisiones; se reportan para conocimiento de la dueña.
