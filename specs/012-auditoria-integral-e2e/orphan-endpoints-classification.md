# Spec 012 — Clasificación de Endpoints Huérfanos (T-07)

Fuente: `evidence/backend-orphan-endpoints.json` (117 endpoints sin consumidor frontend detectado).
Método: agrupación por módulo + revisión manual. La extracción es estática; algunos pueden ser
falsos negativos (llamadas frontend con patrones complejos), por lo que la clasificación se marca
como "candidato" y debe confirmarse al construir cada interfaz.

## A. Sistema / soporte — sin UI requerida (`DOCUMENTED_FUTURE_SCOPE` / N/A)
`/`, `/health/live`, `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json` — infraestructura/OpenAPI.

## B. Resueltas en Ola 1 (ya tienen UI)
- `/organization/establishments` (GET/POST) → `EstablecimientosPage`.
- `/organization/locations` (GET/POST) → `UbicacionesPage`.
- `/users` (GET/POST) → `UsuariosPage`.

## C. Backend-only / operativo — sin UI esperada
- `/license/activation-request`, `/license/activate`, `/license/import` → flujo de licencia (setup/operaciones), no UI de negocio.
- `/licensing/offline-status`, `/licensing/sync-runs`, `/licensing/mode-transition` → operaciones/soporte.
- `/auth/password-reset/request|confirm` → recuperación (flujo demo; en producción vía correo).

## D. GAP — API sin interfaz (candidatos a UI en olas futuras)
| Módulo | Endpoints | Nota |
|---|---|---|
| Inventario (31) | `/inventory/movements`, `/balances`, `/movement-types`, `/cost-layers`, `/lots`, `/transfers`, `/counts`, `/adjustments`, `/reservations`, `/serials`, `/valuation`, `/costing-profiles`, recompute/reverse | Módulo inventario tiene UI de existencias/kardex/transferencias/conteos/ajustes, pero **no consume estos endpoints de detalle/gestión** → UI parcial |
| Maestros (10) | `/maestros/perfiles` (GET/POST), `/catalogos/atributos` (GET/POST), `/catalogos/items/search`, `/terceros/{id}` (detalle), `/terceros/{id}/deactivate`, `/terceros/{id}/roles/{role}` | **Perfiles fiscales sin UI**; atributos y detalle de terceros sin UI |
| Sales (19) | detail/GET + `applications`, `customer-advances`, `credit-notes/*/post|apply`, `debit-notes`, `returns`, `pick-lists`, `invoices/{id}/lines`, `orders/{id}/lines`, `quotes/{id}/lines` | UI de ventas cubre listados/creación básicos; **acciones de negocio (aplicar, post, líneas, devoluciones, picking) sin UI** |
| Purchasing (24) | detail/GET + `advances`, `applications`, `credit-notes/*/post`, `payment-schedules`, `orders/{id}/lines`, etc. | Igual que ventas: **proceso completo de compras sin UI** |
| Auth (4) | `/auth/sessions` (GET/DELETE) | **Gestión de sesiones sin UI** |
| Fiscal (4) | `/fiscal/tax-profiles` (POST), `/fiscal/tax-return-batches` (GET/POST), `/fiscal/documents/{id}` | **Perfiles fiscales y lotes de declaración sin UI** |
| Regulatory (3) | `/regulatory/approval-requests` (GET/POST), `/{id}/transition` | Aprobaciones sin UI de transición |
| Treasury (2) | `/treasury/cash-sessions/{id}`, `/reconciliations/{id}` | Detalle sin UI |
| Reporting (1) | `/reporting/jobs/{id}` | Detalle de jobs sin UI |
| Homologation (1) | `/homologation/records/{id}` | Detalle sin UI |

## E. Recomendación
- **Prioridad alta (procesos de negocio)**: acciones de VENTAS y COMPRAS (aplicar/posts/líneas/devoluciones/picking) y
  PERFILES FISCALES (`/maestros/perfiles`, `/fiscal/tax-profiles`) → sin ellas los procesos completos no son operables por UI.
- **Prioridad media**: inventario de detalle, sesiones, aprobaciones.
- **Confirmar** cada "candidato" al construir la UI (evitar falsos negativos de la extracción estática).
- Los de categorías A y C no requieren UI.
