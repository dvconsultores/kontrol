# PLAN — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/009-reportes-auditoria/plan.md` |

## 1. Resumen ejecutivo

Implementar el **centro de información**: dashboard (indicadores, alertas, vencimientos), reportes ejecutivos/operativos/financieros/fiscales/regulatorios, **exportación auditada** (CSV/PDF) y **auditoría consolidada** (timeline). 009 **consume** los datos de 003-008 en lectura (no duplica lógica) y reutiliza `AuditEvent` de 001 y los libros de 007. Backend `app/modules/reporting/`, migración `0009_reportes`, tests, frontend `src/modules/reportes/`.

## 2. Estrategia técnica

- **Backend** (`app/modules/reporting/`): patrón `models.py` / `service.py` / `api.py` / `__init__.py`, registrado en `init_models` y `app/main.py`. Prefijo `/reporting`.
- **Migración**: Alembic `0009_reportes`. Actualizar head.
- **Entidades nuevas**: `report_exports` (auditoría de exportación), `report_jobs` (trabajos asíncronos), `report_definitions` (catálogo opcional). Auditoría reutiliza `AuditEvent` de 001.
- **Reportes**: endpoints agregados de solo lectura sobre 003-008 (inventario, órdenes, despachos, CxC/CxP aging, tesorería, libros 007, regulatorio).
- **Exportación**: CSV/PDF; cada exportación registra `report_exports` (quién/cuándo/qué/filtros).
- **Dashboard**: endpoint agregado de indicadores y vencimientos.
- **Tests**: fixture `conftest.py` (sqlite in-memory). Cobertura de agregados, exportación auditada, jobs y aislamiento.
- **Frontend** (`src/modules/reportes/`): dashboard y centro de reportes con `DataTable`, filtros y botones de exportación.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Agregados de dashboard y vencimientos | Servicio + API | pytest/ruff/mypy |
| F2 | Reportes ejecutivos/operativos/financieros | Servicio + API | pytest |
| F3 | Reportes fiscales (libros 007) y regulatorios | Servicio + API | pytest |
| F4 | Exportación auditada (CSV/PDF) + `report_exports` | Modelos + servicio + API | pytest |
| F5 | Trabajos asíncronos (`report_jobs`) | Modelos + servicio | pytest |
| F6 | Migración `0009_reportes` | Migración | alembic upgrade head |
| F7 | Frontend: dashboard y centro de reportes | Páginas + tipos | tsc/eslint/vitest/build |
| F8 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

No hay datos legacy; migración estructural `0009_reportes` (exportaciones, jobs y definiciones). No se alteran tablas de 003-008.

## 5. Coordinación y riesgos clave

- Solo lectura sobre 003-008; no duplicar lógica (CL-009-01/SU-009-05).
- Exportaciones auditadas (P5); jobs sin cola externa (CL-009-06).
- Reconstrucción desde eventos; sin tablas editables (CL-009-08).
- Permisos por campo y retención (CL-009-09).
