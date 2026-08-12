# Spec 012 — Clasificación de Endpoints Huérfanos (T-07 / T-211)

> **Actualizado pasada 2 (2026-08-12):** con extracción robusta de `apiFetch`
> (parseo de genéricos anidados `PagedResult<...>`) quedan **53 endpoints sin
> consumidor frontend** (4 sistema · 8 auth/licencia · **41 de negocio sin UI**).
> Fuente: `evidence/backend-orphan-endpoints.json` (recalculado).
>
> **Actualizado Ola T-211 (2026-08-12):** 6 páginas nuevas cierran los GAP de
> prioridad alta. Estado por categoría más abajo.

## A. Sistema / soporte — sin UI requerida (`DOCUMENTED_FUTURE_SCOPE` / N/A)
`/`, `/health/live`, `/health/ready`, `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json`
— infraestructura/OpenAPI.

## B. Auth / licencia — backend-only o sin UI por ahora
- `/auth/password-reset/request|confirm` → **KAUD-012** (sin UI; admin-only o pendiente de página).
- `/license/installation-request`, `/license/activate`, `/license/import` → flujo de licencia (setup/operaciones).
- `/licensing/sync-runs`, `/licensing/offline-status`, `/licensing/mode-transition` → operaciones/soporte.

## C. Negocio sin UI — GAP candidatos a tarea (41)

### C.1 Maestros (7)
- `GET/POST /maestros/catalogos/atributos` → **RESUELTO** (Ola T-211): `AtributosPage` (`/maestros/atributos`).
- `GET /maestros/catalogos/items/search`, `GET /maestros/catalogos/items/{id}` → búsqueda/detalle (los listados usan `?status=`; detalle por ID puede agregarse a Productos).
- `POST /maestros/catalogos/unidades/{id}/conversiones` → **RESUELTO** (Ola T-211): formulario de conversiones en `CatalogosPage`.
- `GET /maestros/terceros/{id}`, `POST /maestros/terceros/{id}/deactivate`, `POST /maestros/terceros/{id}/roles/{role}` → detalle/desactivar/roles de tercero sin UI (GAP pendiente, baja prioridad).

### C.2 Inventario (13)
- `GET/POST /inventory/movement-types` → **RESUELTO** (Ola T-211): `TiposMovimientoPage` (`/inventario/tipos-movimiento`).
- `GET /inventory/balances/{id}`, `POST /inventory/balances/recompute` → detalle/recalcular sin UI (GAP pendiente, baja prioridad).
- `GET /inventory/movements/{id}` → detalle de movimiento sin UI (GAP pendiente).
- `GET/POST /inventory/serials`, `GET/POST /inventory/reservations`,
  `POST /inventory/reservations/{id}/release`, `POST /inventory/reservations/expire` → **RESUELTO** (Ola T-211): `SerialesPage` (`/inventario/seriales`) y `ReservasPage` (`/inventario/reservas`).
- `POST /inventory/operations/receive`, `POST /inventory/operations/ship` → operaciones directas (resueltas vía UI de recepciones/despacho; candidatos a FUTURE_SCOPE).

### C.3 Compras / CxP (11)
- `GET /purchasing/requisitions`, `POST /purchasing/requisitions`, `POST /purchasing/requisitions/{id}/lines` → UI de requisiciones existe pero con llamadas que la extracción marcó huérfanas (revalidar tras el contrato G3/G4); revisar en la implementación.
- `GET/POST /purchasing/quotes`, `POST /purchasing/quotes/{id}/lines` → **RESUELTO** (Ola T-211): `CotizacionesComprasPage` (`/compras/cotizaciones`).
- `GET /purchasing/orders/{id}`, `GET /purchasing/supplier-invoices/{id}`, `GET /purchasing/triple-match` → detalle sin UI (GAP pendiente, baja prioridad).
- `POST /purchasing/withholdings`, `POST /purchasing/withholdings/{id}/transition` → **CUBIERTO** por la página fiscal `RetencionesPage` (gestión central de reglas/cálculo/listado); los POST se usan en procesos de negocio.

### C.4 Ventas / CxC (4)
- `GET /sales/orders/{id}` → detalle de orden sin UI (GAP pendiente, baja prioridad).
- `POST /sales/withholdings-suffered`, `POST /sales/withholdings-suffered/{id}/transition` → **CUBIERTO** por la página fiscal `RetencionesPage` (gestión central).

### C.5 Tesorería (2)
- `GET /treasury/cash-sessions/{id}`, `GET /treasury/reconciliations/{id}` → detalle sin UI (GAP).

### C.6 Fiscal (5)
- `POST /fiscal/tax-profiles` → creación de perfil sin UI (listado sí; `PerfilesFiscalesPage` usa `/maestros/perfiles`, concepto distinto — GAP pendiente, baja prioridad).
- `GET /fiscal/documents/{id}` → detalle de documento sin UI (GAP pendiente).
- `POST /fiscal/tax-return-batches`, `GET /fiscal/tax-return-batches` → **RESUELTO** (Ola T-211): `LotesDeclaracionPage` (`/fiscal/lotes-declaracion`).
- `GET /fiscal/books/{tax_type}` → libros (consumido vía reporte; candidato).

### C.7 Reportes (2)
- `GET /reporting/jobs/{id}` → detalle de job (la lista ahora existe — T-206).
- `GET /reporting/reports/{key}` → consumido por el centro de reportes (falso positivo de la extracción).

### C.8 Homologación (1)
- `GET /homologation/records/{id}` → detalle sin UI (GAP).

## Recomendación
Los GAP reales (atributos/conversiones, seriales/reservas, cotización de compras,
retenciones, lotes de declaración, detalles por ID, withholding-suffered) se
consolidan como tareas en `remediation-plan.md` (Ola 2) y requieren decisión de
alcance (GAP → implementar, o `FUTURE_SCOPE` documentado).

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
