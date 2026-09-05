# MASTER 56 SPECS — ESTADO AUTORITATIVO

> Medido el 2026-09-02 contra el repositorio en `3027da6`. Ningún estado procede
> de un informe anterior: los informes son entrada, el repositorio es la
> evidencia.
>
> Numeración de `56-specs-gap-analysis.md`, inmutable. La correspondencia con
> las carpetas reales de `specs/` está en `spec-equivalence-map.md`: una carpeta
> puede cubrir varias maestras y una maestra puede vivir repartida.

## Baseline

PostgreSQL 18.6 · 177 modelos · 177 tablas · 41 migraciones · 356 FK ·
308 rutas · 426 operaciones · 364 con contrato de empresa ·
backend 0 fallos / 8 saltos S3 · frontend 282/282.

## Regla de clasificación

Tener modelo, endpoint o pantalla **no** es `COMPLETE`. Solo lo es lo que tiene
requisitos, implementación, pruebas, trazabilidad y convergencia. Y no tener
carpeta propia **no** es `NOT_STARTED`: puede vivir dentro de otra Spec.

| # | Spec | Estado | Evidencia | Bloqueo activo |
|---|---|---|---|---|
| 001 | Fundación | `PARTIALLY_IMPLEMENTED` | `specs/001-fundacion`, arranque real, 41 migraciones | Validación Docker/PG de despliegue |
| 002 | Seguridad / sesiones | `PARTIALLY_IMPLEMENTED` | `/auth` 9 rutas, rotación de sesión probada | MFA declarado y no construido |
| 003 | Usuarios / roles / alcance | `PARTIALLY_IMPLEMENTED` | `identity_access` 8 tablas; N10 corrigió tres cruces de tenant | Sin UI de alcances |
| 004 | Licenciamiento | `BLOCKED_BY_BUSINESS_DECISION` | `licensing` 7 tablas, `/licensing` 10 rutas | D0-06 hosting/licencia central |
| 005 | Design System / navegación | `PARTIALLY_IMPLEMENTED` | 282 pruebas de frontend, axe y responsive verificados | Deuda responsive residual (ver 054) |
| 006 | Auditoría / observabilidad | `PARTIALLY_IMPLEMENTED` | `audit_events`, `/audit` | Instrumentación incompleta |
| 007 | Organización | `PARTIALLY_IMPLEMENTED` | `organization` 13 tablas, 36 rutas | Centros de costo y unidades de negocio |
| 008 | Almacenes físicos | **`COMPLETE / CONVERGED`** | zonas, pasillos, racks, niveles, ubicaciones; `/locations/ordered` | — |
| 009 | Terceros | `PARTIALLY_IMPLEMENTED` | `parties`, `customers`, `suppliers`, empresa real tras ARCH-MC | — |
| 010 | Productos / servicios | `PARTIALLY_IMPLEMENTED` | `catalog_items`, `taxonomy_nodes` | — |
| 011 | UoM / presentación / conversión | **`COMPLETE / CONVERGED`** | `units_of_measure`, `presentations`, factor congelado en línea | — |
| 012 | Maestros comerciales | **`COMPLETE / CONVERGED`** | 11 tablas, 14 rutas, `resolve_price` con versión | — |
| 013 | Maestros financieros | `PARTIALLY_IMPLEMENTED` | `treasury` 15 tablas, monedas y tasas de empresa | Tasa BCV depende de 048 |
| 014 | Maestros fiscales / regulatorios | `PARTIALLY_IMPLEMENTED` | `fiscal` 13 tablas, `regulatory` 11 | — |
| 015 | Planificación / requisiciones | `PARTIALLY_IMPLEMENTED` | requisiciones en `purchasing` | Sin planificación de demanda |
| 016 | Cotización a proveedores | `PARTIALLY_IMPLEMENTED` | `supplier_quotes`, `quote_lines` | — |
| 017 | Órdenes de compra | `PARTIALLY_IMPLEMENTED` | `purchase_orders` + líneas, transiciones | — |
| 018 | Importaciones | **`NOT_STARTED`** | **0 tablas**: ninguna `import`/`customs`/`aduana` | — (dependencias satisfechas) |
| 019 | Recepción física | **`COMPLETE / CONVERGED`** (2026-09-03) | arribo, bultos, comparación documental, inspección, observación física, unidad y cantidad base, acta; migración `0044` | **ninguno** |
| 020 | Incidencias de recepción | **`COMPLETE / CONVERGED`** (2026-09-03) | `receipt_incidents`: cinco tipos, ciclo de cinco estados, tope de cantidad por tipo, resolución de conjunto cerrado, ajuste autorizado vía 045, evidencia vía 046; migración `0045` | **ninguno** |
| 021 | Confirmación de inventario | **`COMPLETE / CONVERGED`** (2026-09-04) | conteo por SKU en base, conciliación contra orden y recepción física, cinco tipos de diferencia, decisión por línea con resultado mixto, `receipt_confirmations`; migración `0047`. **Aceptar ya no libera** | **ninguno** |
| 022 | Put-away y ubicación | **`COMPLETE / CONVERGED / EVIDENCE SEALED`** (2026-09-04) | put-away manual con candidatas filtradas por el backend, procedencia de ubicación en el ledger, disponible del almacén agregado; migración `0048`. E2E 27/27 en tres navegadores | **ninguno** |
| 023 | Inventario / Kardex | `PARTIALLY_IMPLEMENTED` · capacidad multiestado **`COMPLETE / CONVERGED`** (2026-09-04) | `inventory` 13 tablas; autoridad única de estados (`states.py`), procedencia en el ledger, reclasificación canónica, reconstrucción fiel; migración `0046` | **ninguno** para la capacidad. La Spec sigue parcial por requisitos ajenos a ella (ubicación en la práctica, FEFO, valoración) |
| 024 | Lotes / seriales / vencimiento | `PARTIALLY_IMPLEMENTED` | `inventory_lots`, `product_serials` | — |
| 025 | Transferencias / conteos / ajustes | `PARTIALLY_IMPLEMENTED` | `transfers`, `stock_counts`, `inventory_adjustments` | — |
| 026 | Costos / valoración | `PARTIALLY_IMPLEMENTED` | `cost_layers`, `costing_profiles` | 018 para *landed cost* |
| 027 | Factura de proveedor / 3-way | `PARTIALLY_IMPLEMENTED` | conciliación a tres bandas en `purchasing` | — |
| 028 | CxP y pagos | `PARTIALLY_IMPLEMENTED` | `ap_payments`, `ap_open_items`; tipo documental cerrado en N9 | 040 retenciones |
| 029 | Cotización y pedido comercial | **`COMPLETE / CONVERGED`** (2026-09-01) | `sales_quotes`, `sales_orders` con origen comercial, ciclo de cotización, conversión 1:1 | **ninguno** |
| 030 | Crédito / aprobación / reserva | **`COMPLETE / CONVERGED`** (2026-09-02) | reserva al confirmar (`ORDER_CONFIRMATION`), bloqueo en PostgreSQL, crédito vía 045, `RELEASED` para 031; migración `0043` | **ninguno** |
| 031 | Cola y ruta de picking | **`READY TO RESUME IMPLEMENTATION`** (2026-09-05) | 0 proceso | **ninguno**: `D0-15` cerró las tres OQ con 22 reglas `R-D0-15-*`. Implementación **no iniciada** |
| 032 | Picking y consolidación | `BLOCKED_BY_DEPENDENCY` | esqueleto en `sales`; reservas de 030, lotes/seriales de 024 y **ubicación de origen (022)** satisfechos; `D0-15` le fija ya el contrato de entrada: solo consume un plan `CONFIRMED` válido y lo revalida | **cola y ruta (031)** hasta que converja |
| 033 | Confirmación independiente de pedido | **`NOT_STARTED`** | 0 tablas | 032 |
| 034 | Liberación y facturación | `PARTIALLY_IMPLEMENTED` | `sales_invoices` con transiciones | 033; snapshot comercial ausente |
| 035 | Despacho / transporte / regulación | `PARTIALLY_IMPLEMENTED` | `shipments`, `regulatory` 11 tablas | 034 |
| 036 | Devoluciones / NC / ND | `PARTIALLY_IMPLEMENTED` | devoluciones en compras y ventas, notas de crédito | — |
| 037 | Cuentas por cobrar | `PARTIALLY_IMPLEMENTED` | `ar_open_items`, aplicaciones | — |
| 038 | Tesorería | `PARTIALLY_IMPLEMENTED` | `treasury` 15 tablas, conciliación bancaria | — |
| 039 | Motor fiscal venezolano | `BLOCKED_BY_LEGAL_VALIDATION` | `fiscal` 13 tablas, versionado de reglas | D0-07 |
| 040 | Retenciones IVA / ISLR | `BLOCKED_BY_LEGAL_VALIDATION` | comprobantes en `fiscal`/`purchasing` | D0-07 |
| 041 | IGTF | `BLOCKED_BY_LEGAL_VALIDATION` | cálculo en tesorería/fiscal | D0-07 |
| 042 | Documentos fiscales / contingencia | `BLOCKED_BY_LEGAL_VALIDATION` | series, números de control, rangos | D0-07; contingencia sin UI |
| 043 | Libros y cierres | `BLOCKED_BY_LEGAL_VALIDATION` | libros de compra y venta | D0-07 |
| 044 | SICA / SIGESAI / SACS | `BLOCKED_BY_EXTERNAL_SERVICE` | `regulatory` registra, valida, adjunta y bloquea | Sin API oficial: v1 no emite permiso |
| 045 | Motor de aprobaciones / SoD | **`COMPLETE / CONVERGED`** | 8 tablas, 18 rutas; N10 corrigió su elegibilidad | — |
| 046 | Gestión documental | **`RECONVERGED`** | 8 tablas, 23 `ResourceKind`, ClamAV real | S3 real (P1 externa) |
| 047 | Notificaciones y tareas | **`NOT_STARTED`** | 0 tablas | 048 |
| 048 | Integraciones | `PARTIALLY_IMPLEMENTED` | licenciamiento central | — |
| 049 | Dashboard | `PARTIALLY_IMPLEMENTED` | `reporting` 3 tablas | 023, 034, 037, 038 |
| 050 | Reportes | `PARTIALLY_IMPLEMENTED` | `/reporting` 8 rutas | — |
| 051 | Auditoría empresarial avanzada | `PARTIALLY_IMPLEMENTED` | bitácora con actor, tenant y empresa | 006 |
| 052 | Instalador / actualización | `PARTIALLY_IMPLEMENTED` | `scripts/`, `alembic` a cabeza | Planificador de retención (P1) |
| 053 | Copia de seguridad / continuidad | `PARTIALLY_IMPLEMENTED` | `scripts/backup.sh`, `restore.sh` | Sin verificación de restauración |
| 054 | QA integral | `PARTIALLY_IMPLEMENTED` | `specs/012-auditoria-integral-e2e`, suites vigentes | Deuda responsive |
| 055 | Seguridad y *hardening* | `PARTIALLY_IMPLEMENTED` | barridos de N5/N10, sin fugas | Sin Spec propietaria |
| 056 | Homologación fiscal y release | `BLOCKED_BY_LEGAL_VALIDATION` | `homologation` 3 tablas | D0-07, 039–043 |

## Recuento

| Estado | Specs |
|---|---:|
| `COMPLETE / CONVERGED` | 10 — 008, 011, 012, 019, 020, 021, **022**, 029, 030, 045 |
| `RECONVERGED` | 1 — 046 |
| `READY_FOR_IMPLEMENTATION` | **1 — 031** (`READY TO RESUME IMPLEMENTATION`) |
| `PARTIALLY_IMPLEMENTED` | 32 |
| `NOT_STARTED` | 3 — 018, 033, 047 |
| `BLOCKED_BY_DEPENDENCY` | 1 — 032 |
| `BLOCKED_BY_BUSINESS_DECISION` | 1 — 004 |
| `BLOCKED_BY_LEGAL_VALIDATION` | 6 — 039, 040, 041, 042, 043, 056 |
| `BLOCKED_BY_EXTERNAL_SERVICE` | 1 — 044 |
| **Sin estado** | **0** |

Suma: 4 + 1 + 1 + 34 + 5 + 2 + 2 + 6 + 1 = **56**. Sin estado: **0**.

El grupo dominante —34 de 56— es `PARTIALLY_IMPLEMENTED`, y conviene no leerlo
como una queja. KONTROL se construyó por módulos anchos antes de tener el
catálogo de 56, así que casi todo tiene algo hecho y casi nada está cerrado con
su propia convergencia. Lo que este checkpoint aporta no es descubrirlo sino
distinguir, dentro de ese 34, qué está a la espera de una decisión, qué de una
dependencia y qué solo de que alguien lo termine.
