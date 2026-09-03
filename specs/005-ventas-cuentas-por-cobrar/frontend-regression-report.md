# SPEC 030 — INFORME DE REGRESIÓN DEL FRONTEND

| Compuerta | Resultado | Comando |
|---|---|---|
| `tsc -b --noEmit` | PASS | `npx tsc -b --noEmit` |
| ESLint (`--max-warnings 0`) | PASS | `npm run lint` |
| Vitest | **283/283** (12 archivos), incl. `audit-completeness` (fixture OpenAPI regenerado: 364 → 437 rutas) y `architecture-company` | `npx vitest run` |
| Build | PASS (`OrdenesVentasPage` 12.41 kB · gzip 4.01 kB; bundle principal 391.92 kB · gzip 119.41 kB) | `npm run build` |
| Playwright `e2e/sales-orders.spec.ts` | **12/12** — 4 casos × Chromium, Firefox, WebKit, contra backend real sobre PostgreSQL 18.6. Reejecutado tras corregir la serialización por lotes del listado, para que la evidencia corresponda al código entregado | `npx playwright test e2e/sales-orders.spec.ts --project=chromium --project=firefox --project=webkit` |
| Playwright `e2e/route-crawl.spec.ts` | **1/1** (todas las rutas del menú sin 404, sin errores de consola, con H1) | `--project=chromium` |
| Playwright `e2e/accessibility.spec.ts` (axe WCAG 2.2 AA) | **22/22** | `--project=chromium` |
| Crawler responsive (36 rutas × 6 viewports) | **194/216**; 22 casos de scroll horizontal **idénticos a la auditoría del 2026-08-12** (`KONTROL-AUDIT-20260812-RESPONSIVE`): 15 a 320×568, 4 a 375×667, 3 a 412×915. `/ventas/ordenes` y `/inventario/reservas` solo a 320×568, igual que entonces | `node e2e/audit-responsive-crawler.mjs http://localhost:5173 KONTROL-AUDIT-20260902-SPEC030` |

## Casos E2E de la Spec 030

1. Confirmar un pedido de contado → «Liberado a preparación», «4 en base»; el backend responde
   `RELEASED`, `eligible_for_picking`, reserva `ACTIVE` con `trigger = ORDER_CONFIRMATION`; el botón
   «Confirmar» desaparece.
2. Sin disponible → notificación «No hay disponible suficiente» con el detalle por línea (`pedido
   8.000000, disponible 3.000000`); el pedido sigue «Borrador» y `DRAFT` en el backend.
3. Cancelar → diálogo con motivo obligatorio → «Cancelado» con el motivo en la fila; la reserva queda
   `RELEASED` con `ORDER_CANCELLED`.
4. Política de reserva → «Disparador: ORDER_CONFIRMATION (fijo)»; guardar vigencia 3 días →
   `reservation_ttl_days = 3`, `trigger_configurable = false`; se restablece a nulo.

## Hallazgo corregido durante el ciclo

axe `scrollable-region-focusable` (serio) en `/inventario/reservas`: con más columnas, la tabla se
volvía desplazable y el contenedor `overflow-x-auto` no era enfocable. Se corrigió en el componente
compartido `DataTable` (`tabIndex=0`, `role="region"`, `aria-label`) y en la tabla de líneas de
`OrdenesVentasPage`. Beneficia a toda tabla ancha. 22/22 tras la corrección.

## Pantallas

- `OrdenesVentasPage`: almacén al crear; presentación y precio opcional en la línea; acciones
  dictadas por `allowed_actions` (`Confirmar`, `Liberar`, `Rechazar`, `Revertir`, `Cancelar`,
  `Cerrar`); motivo en diálogo; detalle de líneas con base y reserva; política de reserva; vencimientos.
- `ReservasPage`: origen (pedido/manual) y disparador; base; motivo de liberación; «Liberar» solo
  para manuales y con motivo; filtro con `FULFILLED`; sin `RESERVED`.
- `DespachoPage`: `RESERVED → RELEASED` en los filtros.
- `types.ts`: `SalesOrderStatus`, `OrderLineReservation`, `ReservationPolicy`, `InsufficientLine`,
  campos nuevos de `Reservation` y `SalesOrderLine`.

Deuda residual (no de esta Spec): los 22 casos responsive a viewports ≤ 412 px ya figuraban en
`docs/roadmap/active-blockers.md` («Deuda responsive residual · P1 · 005, 054»).
