# BLOQUEOS HISTÓRICOS RESUELTOS

Cada fila se comprobó contra el repositorio, no contra el informe que la
declaró resuelta.

| # | Bloqueo histórico | Resuelto por | Evidencia medida hoy |
|---|---|---|---|
| D-01 | 023 Inventario se construyó sin 008 completo | **Spec 008** | `inventory_movements.location_id` y `inventory_balances.location_id` son FK reales a `warehouse_locations` |
| D-02 | 029/030 Ventas se construyeron sin 012 | **Spec 012** | `resolve_price` devuelve precio **y** versión; 11 tablas comerciales; `price_precedence` configurable |
| D-05 | 015/017/025/030 con aprobaciones ad-hoc | **Spec 045** | 8 tablas de aprobación, 18 rutas, motor único; N10 corrigió además su elegibilidad |
| D-06 | 030 bloqueada por `D0-03` (¿se reserva al pedido o al crédito aprobado?) | **Checkpoint D0-03** (2026-09-02) | `ADR-D0-003` v2 ACTIVE con `RESERVATION TRIGGER = ORDER_CONFIRMATION`; política completa en `docs/governance/d0-foundational-decisions/d0-03-checkpoint/`; contrato FR-030-001..063 en `specs/005-…/spec.md`; 0 cambios de código |
| — | 019, 027, 035, 044, 056 sin capacidad documental | **Spec 046** | 23 `ResourceKind` en registro cerrado, con prueba por tipo |
| — | 028 y 038 bloqueadas por `REM-046-001` | **N9** | Los cuatro tipos que faltaban —`Payment`, `BankTransaction`, `CashSession`, `Reconciliation`— registrados y probados |
| — | Toda Spec con datos de empresa, bloqueada por ARCH-MC-001 | **ARCH-MC-001 N0–N10** | 0 alcances indeterminados, 0 fugas, 0 respaldos Tenant→Company, paridad ORM/base 0 |
| — | 012 bloqueada porque `parties.company_id` guardaba el tenant | **ARCH-MC-001 N7** | `parties.company_id` obligatoria con FK a `companies` |
| — | D-08 líneas sin unidad ni presentación | **Spec 011** | Factor congelado en línea de recepción, picking y venta |

## Specs que siguen bloqueadas por ARCH-MC-001

**Ninguna.** Es el resultado de N10 y se comprobó volviendo a medir: no queda
respaldo Tenant→Company, ni lectura o escritura dual, ni alcance indeterminado.

## Un bloqueo que no era el que parecía

`REM-046-001` recomendaba declarar en el registro documental si cada columna
contenía empresa o tenant. Esa recomendación **se quedó sin causa**: ARCH-MC-001
resolvió el problema en origen, normalizando las columnas en vez de documentar
su ambigüedad.

Se anota porque es el patrón que este checkpoint persigue: un bloqueo puede
desaparecer sin que nadie ejecute la tarea que se había escrito para él.
