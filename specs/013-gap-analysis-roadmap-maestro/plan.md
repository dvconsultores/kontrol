# PLAN — 013 GAP ANALYSIS Y ROADMAP MAESTRO

## Enfoque

Auditoría en 6 capas, cada una con evidencia verificable y sin modificar código productivo.

| Capa | Entrada | Técnica | Salida |
|---|---|---|---|
| L1 Documental | `requerimientos/`, Constitución, ADR | Extracción PDF/DOCX, lectura íntegra | `source-inventory.md`, `requirements-to-specs-map.md` |
| L2 Especificación | `specs/001..012` | Lectura de spec/convergence/tasks | `spec-equivalence-map.md` |
| L3 Frontend | `resources/frontend/src` | Extracción de rutas, menú, páginas, llamadas API | `screens-to-specs-map.md` |
| L4 Backend + DB | `resources/backend/app`, `alembic/` | Decoradores, modelos, máquinas de estado, cadena de migraciones | `code-to-specs-map.md`, `technical-dependencies.md` |
| L5 Procesos | DOCX de proceso + código | Contraste etapa por etapa | `processes-to-specs-map.md`, `false-completion-findings.md` |
| L6 Síntesis | L1-L5 | Clasificación, grafo, priorización | `56-specs-gap-analysis.md`, `roadmap-by-waves.md`, `master-backlog.md` |

## Regla de clasificación

Cada Spec maestra recibe **un** estado principal. El porcentaje técnico auxiliar
(ponderación de 12 dimensiones) es orientativo y **no** puede promover a `COMPLETE_100`
si falta una función crítica de la cadena.

## Restricciones de ejecución

- Prohibido `/speckit.implement` (P2 + prompt §3).
- Prohibido modificar código, migraciones, datos o Specs existentes.
- Permitido: builds, tests, linters, inspección de esquema, lectura E2E.
- Prohibido emitir documentos fiscales productivos.

## Riesgos del propio análisis

| Riesgo | Mitigación |
|---|---|
| Sobrevalorar por existencia de archivos | Verificación de cadena completa, no de presencia |
| Subvalorar por desconocer alcance diferido | Contraste con `convergence.md` de cada Spec y con P20 |
| Confundir infra caída con código roto | Separar estado de Spec de incidencia operativa (CL-013-08) |
| Sin PostgreSQL real, no hay evidencia de producción | Ninguna Spec puede alcanzar `COMPLETE_100`; se declara explícitamente |
