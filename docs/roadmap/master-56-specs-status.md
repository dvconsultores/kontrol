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
| 007 | Organización | `PARTIALLY_IMPLEMENTED` | `organization` 13 tablas, 36 rutas. Delta dirigido recibido de la 013 (2026-09-11): la empresa publica su moneda funcional, que es el ancla de todo par de cotización | Centros de costo y unidades de negocio |
| 008 | Almacenes físicos | **`COMPLETE / CONVERGED`** | zonas, pasillos, racks, niveles, ubicaciones; `/locations/ordered` | — |
| 009 | Terceros | `PARTIALLY_IMPLEMENTED` | `parties`, `customers`, `suppliers`, empresa real tras ARCH-MC | — |
| 010 | Productos / servicios | `PARTIALLY_IMPLEMENTED` | `catalog_items`, `taxonomy_nodes` | — |
| 011 | UoM / presentación / conversión | **`COMPLETE / CONVERGED`** | `units_of_measure`, `presentations`, factor congelado en línea | — |
| 012 | Maestros comerciales | **`COMPLETE / CONVERGED`** | 11 tablas, 14 rutas, `resolve_price` con versión | — |
| 013 | Maestros financieros | **`COMPLETE / CONVERGED`** (2026-09-11) | par explícito, maestro de fuentes, política de resolución, corrección por sucesión, importación idempotente; migración `0056` | **ninguno**: la tasa tiene par, fuente y procedencia; falta de tasa no es tasa uno; invertir y triangular exigen política y quedan marcadas. El **proveedor automático** (BCV u otro) es de la **048** y no bloquea: la operación vive de alta manual e importación, con el contrato de proveedor ya definido. Endurecida el 2026-09-13 al instalar de cero: perder una carrera de alta es error de dominio y no 500, y la unicidad vive en modelos y migración por igual (deriva de la 013: 0; heredada del esquema: 21, con dueño) · 1401/1393/8/0 |
| 014 | Maestros fiscales / regulatorios | `PARTIALLY_IMPLEMENTED` | `fiscal` 13 tablas, `regulatory` 11 | — |
| 015 | Planificación / requisiciones | `PARTIALLY_IMPLEMENTED` | requisiciones en `purchasing` | Sin planificación de demanda |
| 016 | Cotización a proveedores | `PARTIALLY_IMPLEMENTED` | `supplier_quotes`, `quote_lines` | — |
| 017 | Órdenes de compra | `PARTIALLY_IMPLEMENTED` | `purchase_orders` + líneas, transiciones | — |
| 018 | Importaciones | **`NOT_STARTED`** | **0 tablas**: ninguna `import`/`customs`/`aduana` | — (dependencias satisfechas) |
| 019 | Recepción física | **`COMPLETE / CONVERGED`** (2026-09-03) | arribo, bultos, comparación documental, inspección, observación física, unidad y cantidad base, acta; migración `0044` | **ninguno** |
| 020 | Incidencias de recepción | **`COMPLETE / CONVERGED`** (2026-09-03) | `receipt_incidents`: cinco tipos, ciclo de cinco estados, tope de cantidad por tipo, resolución de conjunto cerrado, ajuste autorizado vía 045, evidencia vía 046; migración `0045` | **ninguno** |
| 021 | Confirmación de inventario | **`COMPLETE / CONVERGED`** (2026-09-04) | conteo por SKU en base, conciliación contra orden y recepción física, cinco tipos de diferencia, decisión por línea con resultado mixto, `receipt_confirmations`; migración `0047`. **Aceptar ya no libera** | **ninguno** |
| 022 | Put-away y ubicación | **`COMPLETE / CONVERGED / EVIDENCE SEALED`** (2026-09-04) | put-away manual con candidatas filtradas por el backend, procedencia de ubicación en el ledger, disponible del almacén agregado; migración `0048`. E2E 27/27 en tres navegadores | **ninguno** |
| 023 | Inventario / Kardex | `PARTIALLY_IMPLEMENTED` · capacidad multiestado **`COMPLETE / CONVERGED`** (2026-09-04) | `inventory` 13 tablas; autoridad única de estados (`states.py`), procedencia en el ledger, reclasificación canónica, reconstrucción fiel; migración `0046` | **ninguno** para la capacidad. La Spec sigue parcial por requisitos ajenos a ella (ubicación en la práctica, FEFO, valoración). Delta dirigido recibido de la 013 (2026-09-13): el alta automática del tipo de movimiento base ya no devuelve 500 cuando dos operaciones de una empresa nueva llegan a la vez |
| 024 | Lotes / seriales / vencimiento | `PARTIALLY_IMPLEMENTED` | `inventory_lots`, `product_serials` | — |
| 025 | Transferencias / conteos / ajustes | `PARTIALLY_IMPLEMENTED` | `transfers`, `stock_counts`, `inventory_adjustments` | — |
| 026 | Costos / valoración | `PARTIALLY_IMPLEMENTED` | `cost_layers`, `costing_profiles` | 018 para *landed cost* |
| 027 | Factura de proveedor / 3-way | `PARTIALLY_IMPLEMENTED` | conciliación a tres bandas en `purchasing` | — |
| 028 | CxP y pagos | `PARTIALLY_IMPLEMENTED` | `ap_payments`, `ap_open_items`; tipo documental cerrado en N9. **Delta dirigido convergido (2026-09-11)**: el motor compartido de saldos calcula en `Decimal` y no en `float` (`KQA-100`) | 040 retenciones |
| 029 | Cotización y pedido comercial | **`COMPLETE / CONVERGED`** (2026-09-01) | `sales_quotes`, `sales_orders` con origen comercial, ciclo de cotización, conversión 1:1 | **ninguno** |
| 030 | Crédito / aprobación / reserva | **`COMPLETE / CONVERGED`** (2026-09-02) | reserva al confirmar (`ORDER_CONFIRMATION`), bloqueo en PostgreSQL, crédito vía 045, `RELEASED` para 031; migración `0043` | **ninguno** |
| 031 | Cola y ruta de picking | **`COMPLETE / CONVERGED`** (2026-09-05) | 7 de 10 etapas | **ninguno**: cola por `released_at`, asignación por ubicación, ruta de la 008, cinco estados; migración `0049`. Las 3 etapas restantes son el recorrido físico, de la 032. Delta dirigido recibido de la 035 (2026-09-07): el selector de almacén ya no descarta opciones en silencio |
| 032 | Picking y consolidación | **`COMPLETE / CONVERGED`** (2026-09-05) | 12 de 12 etapas | **ninguno**: extracción con estado de custodia, cinco motivos de diferencia del proceso, consolidación al Área de Confirmación; migración `0050` |
| 033 | Confirmación independiente de pedido | **`COMPLETE / CONVERGED`** (2026-09-06) | 8 de 8 etapas · 2 tablas | **ninguno**: compara contra el pedido, segregación por defecto, compuerta única de facturación; migración `0051`. Delta dirigido recibido de la 038 (2026-09-11): `npm run build` llevaba roto desde `fe92cf3` por claves repetidas (`TS2783`) en su pantalla; corregido sin cambiar el comportamiento |
| 034 | Liberación y facturación | **`COMPLETE / CONVERGED`** (2026-09-06) | 8 de 8 etapas · factura atada al pedido | **ninguno**: compuerta de confirmación, snapshot comercial congelado, numeración de la 042; migración `0052`. La **homologación legal** de la emisión sigue en `D0-07`. Delta dirigido recibido de la 036 (2026-09-11): `issue_invoice` ya abre la cuenta por cobrar |
| 035 | Despacho / transporte / regulación | **`COMPLETE / CONVERGED`** (2026-09-07) | 6 de 6 etapas (¶101-107) · compuerta del ¶103 · 1226/1218/8/0 | **ninguno**: salida solo desde pedido facturado, validación real de las cuatro condiciones, salida en cantidad base desde `PREPARADO`, reserva consumida; migración `0053`. La validación regulatoria es contra lo registrado —**no se emite ni se verifica en línea**—, límite de la 044 en `BLOCKED_BY_EXTERNAL_SERVICE` |
| 036 | Devoluciones / NC / ND | **`COMPLETE / CONVERGED`** (2026-09-11) | 8 de 8 etapas del flujo normativo · 1279/1271/8/0 | **ninguno**: cuatro actos antes de tocar el inventario, los dos destinos que `D0-10` concede, nota proporcional con consecutivo propio, tope acumulativo, reserva intacta; migración `0054`. La **homologación legal** de las notas sigue en `D0-07` |
| 037 | Cuentas por cobrar | **`COMPLETE / CONVERGED`** (2026-09-11) | saldo canónico, aplicaciones con rastro, reversos; 1311/1303/8/0 | **ninguno**: el crédito es del cliente que lo tiene, cada aplicación deja su fila, el reverso no borra y el crédito se resta una sola vez. Delta dirigido recibido de la 038 (2026-09-11): «imputable» y «debido» son dos cifras distintas —lo reservado para devolver ya no se ofrece— y el reembolso, que entonces no tenía autoridad, ya la tiene |
| 038 | Tesorería | **`COMPLETE / CONVERGED`** (2026-09-11) | política cambiaria versionada, instantánea de tasa, conversión explícita y reembolso en tres actos; migración `0055` · 1344/1336/8/0. Deltas dirigidos recibidos de la 013 (2026-09-11): la instantánea dice si la tasa fue derivada, y el camino corto de registro ya escribe el par | **ninguno**: las dos preguntas materiales las respondió el owner (`OWNER-DECISION-038-01` y `-02`) y ninguna fuente las contradice. La tasa ya no se inventa, lo reservado no se imputa y la posición de caja no suma monedas distintas. El **IGTF** sigue siendo de la 041 y la **homologación legal** sigue en `D0-07` |
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
| `COMPLETE / CONVERGED` | 19 — 008, 011, 012, **013**, 019, 020, 021, 022, 029, 030, 031, 032, 033, 034, 035, 036, 037, 038, 045 |
| `RECONVERGED` | 1 — 046 |
| `READY_FOR_IMPLEMENTATION` | **0** |
| `PARTIALLY_IMPLEMENTED` | 26 |
| `NOT_STARTED` | 2 — 018, 047 |
| `BLOCKED_BY_DEPENDENCY` | **0** |
| `BLOCKED_BY_BUSINESS_DECISION` | 1 — 004 |
| `BLOCKED_BY_LEGAL_VALIDATION` | 6 — 039, 040, 041, 042, 043, 056 |
| `BLOCKED_BY_EXTERNAL_SERVICE` | 1 — 044 |
| **Sin estado** | **0** |

Suma: 17 + 1 + 0 + 28 + 2 + 0 + 1 + 6 + 1 = **56**. Sin estado: **0**.

El grupo dominante —28 de 56— es `PARTIALLY_IMPLEMENTED`, y conviene no leerlo
como una queja. KONTROL se construyó por módulos anchos antes de tener el
catálogo de 56, así que casi todo tiene algo hecho y casi nada está cerrado con
su propia convergencia. Lo que este checkpoint aporta no es descubrirlo sino
distinguir, dentro de ese 28, qué está a la espera de una decisión, qué de una
dependencia y qué solo de que alguien lo termine.
