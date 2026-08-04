# PLAN — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/006-tesoreria/plan.md` |

## 1. Resumen ejecutivo

Implementar el módulo de **tesorería** (cajas, bancos, ingresos/egresos, transferencias/depósitos, conciliaciones, arqueos, IGTF por regla/evento y maestros financieros). 006 **consume** los pagos de 004 y cobros de 005 (no duplica su lógica). Backend `app/modules/treasury/`, migración `0006_tesoreria`, tests, frontend `src/modules/tesoreria/`.

## 2. Estrategia técnica

- **Backend** (`app/modules/treasury/`): patrón `models.py` / `service.py` / `api.py` / `__init__.py`, registrado en `app/core/database.py` (init_models) y `app/main.py`. Prefijo de rutas `/treasury`.
- **Migración**: Alembic `0006_tesoreria` (maestros financieros + cajas + bancos + tesorería + conciliaciones). Actualizar head.
- **Reutilización**: `Payment`/`PaymentInstrument`/`Application`/`Advance` (004) para ejecución; `OpenItem` (004/005) para aplicar; `rates/moneda` para snapshot. No redefinir tablas ya existentes.
- **IGTF**: tablas `fiscal_rules` (versionadas, por ahora maestra) + evaluación `igft_events` por regla; el cálculo completo queda en 007.
- **Tests**: fixture `conftest.py` (sqlite in-memory). Cobertura de cajas, conciliación, ejecución de ingresos/egresos, IGTF, idempotencia.
- **Frontend** (`src/modules/tesoreria/`): páginas por dominio con patrón `DataTable` + `AsyncButton` + `useNotifications` + `invalidateQueries`; sidebar en `src/layout/Sidebar.tsx`; tipos en `src/api/types.ts`.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Maestros financieros (bancos, cuentas, cajas, métodos/instrumentos, monedas/tasas) | Modelos + API | pytest/ruff/mypy |
| F2 | Cajas: sesiones, movimientos, arqueo, pre-cierre, cierre, diferencias | Modelos + servicio + API | pytest |
| F3 | Bancos: `BankTransaction`, ingresos/egresos, transferencias/depósitos | Modelos + servicio + API | pytest |
| F4 | Conciliación asistida (reglas) + resolución manual auditada | Modelos + servicio + API | pytest |
| F5 | IGTF por regla/evento (reglas versionadas) | Modelos + servicio | pytest |
| F6 | Migración `0006_tesoreria` + integración 004/005 | Migración + contract tests | alembic upgrade head |
| F7 | Frontend tesorería (cajas, arqueo, conciliación, ingreso/egreso, IGTF) | Páginas + tipos | tsc/eslint/vitest/build |
| F8 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

No hay datos legacy; migración estructural `0006_tesoreria` que crea las tablas nuevas. No se alteran tablas de 004/005 (solo se leen/consumen).

## 5. Coordinación y riesgos clave

- Acoplamiento con 004/005: consumir vía contrato (CL-006-05/SU-006-05).
- IGTF dependiente de 007: estructura por regla/evento sin reescritura (CL-006-02).
- Confirmar que la caja no se cierra con diferencia sin aprobación (FR-006-003).
