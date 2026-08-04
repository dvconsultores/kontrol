# CONVERGENCIA — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Ruta | `specs/009-reportes-auditoria/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-009-01 | Plantillas PDF definitivas y marca | Decisión (CL-009-11) | Producto | Pendiente |
| CVG-009-02 | Política de retención de exportaciones por empresa | Decisión (CL-009-12) | Producto | Pendiente |
| CVG-009-03 | Jobs asíncronos con cola externa (celery/worker) | Esfuerzo de infraestructura | Arquitecto | Pendiente |
| CVG-009-04 | Contabilidad formal (mayor, partidas dobles, cierre) | Fuera de roadmap actual | Producto | Pendiente |
| CVG-009-05 | Listado persistente de jobs en UI (GET /reporting/jobs) | Frontend de jobs | Reportes | Pendiente |

## 3. Implementado (009)

| Elemento | Estado |
|---|---|
| Dashboard con indicadores y vencimientos por módulo | ✔ |
| Reportes ejecutivos/operativos/financieros (solo lectura sobre 003-008) | ✔ |
| Reportes fiscales reutilizando libros de 007 | ✔ |
| Reportes regulatorios (evaluaciones/permisos de 008) | ✔ |
| Exportación auditada (CSV/PDF) con `report_exports` (quién/cuándo/qué/filtros) | ✔ |
| Trabajos asíncronos (`report_jobs`) con estado/error | ✔ |
| Timeline de auditoría (reutiliza `AuditEvent` de 001) | ✔ |
| Migración Alembic `0009_reportes` (head) | ✔ |
| API `/reporting/*` (7 endpoints) | ✔ |
| Frontend: dashboard enriquecido, centro de reportes, exportaciones, auditoría | ✔ |
| **Fix estructural**: `init_models()` ahora importa los `models.py` de todos los módulos | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 158/158 (145 previos + 13 de reportes) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 88 archivos, 0 issues |
| Alembic | ✔ head `0009_reportes` (0001→0009; ALTER de 0004 requiere PostgreSQL, igual que CI) |
| OpenAPI | ✔ 7 endpoints `/reporting/*` (195 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Notas de arquitectura

- **`init_models()` corregido**: ahora importa explícitamente cada `models.py`, garantizando que `Base.metadata` registre todas las tablas (antes dependía de imports implícitos en cada suite de tests).
- Los reportes son consultas de **solo lectura**; las exportaciones quedan auditadas (`report_exports`).
- La auditoría reutiliza `AuditEvent` de 001 (append-only).

## 6. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 003-008 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 010/011) | Pendiente — depende de 001 certificada y de Specs 010/011 |
