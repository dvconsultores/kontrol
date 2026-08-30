# KONTROL — MATRIZ MAESTRA DE LAS 56 SPECS

> Auditoría `develop @ def2b52` · 2026-08-29 · Sin implementación.
> Columnas Front/Back/DB/Integración/E2E en escala 0-100 (evidencia, no intención).
> **Actualizado 2026-08-29:** la Spec 045 alcanza `COMPLETE_100` — la primera del
> proyecto — tras validarse sobre PostgreSQL real. Las 55 restantes siguen sin esa
> validación, condición de "operativo E2E" (Constitución P21).

| # | Spec | Documentada | Spec actual | Front | Back | DB | Integr. | E2E | % | Estado | Brecha principal |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 001 | Fundación de KONTROL | Sí | 001 | 90 | 90 | 90 | 70 | 70 | 85 | SUBSTANTIALLY_COMPLETE | Docker/PG nunca validados E2E |
| 002 | Seguridad, autenticación y sesiones | Sí | 001 | 90 | 90 | 90 | 80 | 80 | 86 | SUBSTANTIALLY_COMPLETE | MFA solo campo `mfa_enabled`, sin flujo |
| 003 | Usuarios, roles, permisos y alcance | Sí | 001 + 012 | 70 | 85 | 90 | 60 | 60 | 72 | PARTIAL | Sin UI de alcances; `user_scopes` sin gestión |
| 004 | Licenciamiento e instalación independiente | Sí | 001 + 010 | 90 | 90 | 90 | 60 | 70 | 82 | SUBSTANTIALLY_COMPLETE | Servidor central real inexistente |
| 005 | Design System, navegación y componentes | Sí | 001 | 95 | — | — | 90 | 85 | 89 | SUBSTANTIALLY_COMPLETE | Sin `unsaved changes`; navegadores reales |
| 006 | Auditoría, observabilidad y operación | Sí | 001 + 009 | 70 | 65 | 90 | 50 | 55 | 66 | PARTIAL | `organization` y `master_data` sin auditoría; sin métricas |
| 007 | Organización | Sí | 001 | 70 | 70 | 65 | 60 | 65 | 66 | PARTIAL | **Centros de costo y unidades de negocio ausentes** |
| 008 | Estructura física de almacenes | Sí | 001 | 100 | 100 | 100 | 100 | 100 | 100 | **COMPLETE_100** | Cerrada 2026-08-30 sobre PostgreSQL 18.6 · jerarquía opcional por almacén · FK reales |
| 009 | Terceros | Sí | 002 | 80 | 85 | 90 | 65 | 70 | 79 | SUBSTANTIALLY_COMPLETE | Vendedor/beneficiario sin entidad propia |
| 010 | Productos y servicios | Sí | 002 | 80 | 85 | 90 | 65 | 70 | 79 | SUBSTANTIALLY_COMPLETE | Marcas/modelos como nodos genéricos |
| 011 | Unidades, presentaciones y conversiones | Sí | 002 | 100 | 100 | 100 | 100 | 100 | 100 | **COMPLETE_100** | Cerrada 2026-08-30 sobre PostgreSQL 18.6 · 17 líneas con snapshot · 30 columnas a NUMERIC |
| 012 | Maestros comerciales | Sí | **ninguna** | 0 | 0 | 5 | 0 | 0 | 2 | NOT_STARTED | **Rama completa sin spec ni modelo** |
| 013 | Maestros financieros | Sí | 006 | 85 | 90 | 90 | 70 | 75 | 84 | SUBSTANTIALLY_COMPLETE | Tasas sin fuente automática (BCV) |
| 014 | Maestros fiscales y regulatorios | Sí | 007 + 008 | 80 | 85 | 90 | 55 | 65 | 77 | SUBSTANTIALLY_COMPLETE | Valores oficiales no cargados |
| 015 | Planificación de abastecimiento y requisiciones | Sí | 004 | 60 | 60 | 70 | 30 | 55 | 55 | PARTIAL | **Sin rotación, demanda ni punto de reorden** |
| 016 | Cotización y selección de proveedores | Sí | 004 | 70 | 85 | 90 | 55 | 65 | 74 | SUBSTANTIALLY_COMPLETE | Selección sin criterios ponderados |
| 017 | Orden de compra | Sí | 004 | 85 | 90 | 90 | 70 | 80 | 85 | SUBSTANTIALLY_COMPLETE | Entregas parciales sin calendario |
| 018 | Importaciones | Sí (DOCX) | **ninguna** | 0 | 0 | 0 | 0 | 0 | 0 | NOT_STARTED | **INCOTERM/proforma/packing/embarque inexistentes** |
| 019 | Recepción física | Sí (DOCX) | 004 | 50 | 55 | 60 | 25 | 60 | 50 | PARTIAL | Sin arribo, bultos, pallets ni evidencia |
| 020 | Incidencias de recepción | Sí (DOCX) | **ninguna** | 0 | 10 | 10 | 0 | 0 | 5 | NOT_STARTED | **Sin entidad de incidencia ni escalamiento** |
| 021 | Confirmación y conciliación de inventario recibido | Sí (DOCX) | parcial 003 | 20 | 35 | 55 | 20 | 20 | 32 | SKELETON_ONLY | Recepción entra directo a DISPONIBLE |
| 022 | Put-away y ubicación por zonas | Sí (DOCX) | parcial 003 | 15 | 20 | 45 | 10 | 10 | 22 | SKELETON_ONLY | `GoodsReceiptLine` sin `location_id` |
| 023 | Núcleo de inventario y Kardex | Sí | 003 | 85 | 92 | 92 | 80 | 85 | 88 | SUBSTANTIALLY_COMPLETE | Sin dimensión de ubicación en la práctica |
| 024 | Lotes, seriales y vencimientos | Sí | 003 | 80 | 90 | 90 | 70 | 80 | 84 | SUBSTANTIALLY_COMPLETE | Cadena de frío/garantía sin perfil |
| 025 | Transferencias, conteos y ajustes | Sí | 003 | 85 | 90 | 90 | 75 | 85 | 86 | SUBSTANTIALLY_COMPLETE | Tránsito sin control de vehículo |
| 026 | Costos y valoración | Sí | 003 | 60 | 70 | 75 | 40 | 55 | 62 | PARTIAL | **Sin landed cost ni distribución de gastos de importación** |
| 027 | Factura proveedor y conciliación | Sí | 004 | 80 | 90 | 90 | 75 | 85 | 85 | SUBSTANTIALLY_COMPLETE | Tolerancias no configurables por empresa |
| 028 | Cuentas por pagar y pagos | Sí | 004 | 85 | 90 | 90 | 75 | 85 | 86 | SUBSTANTIALLY_COMPLETE | Programación sin calendario de tesorería |
| 029 | Cotizaciones y pedido comercial | Sí | 005 | 60 | 60 | 65 | 35 | 60 | 57 | PARTIAL | **Sin pedido distinto de orden; precio sin maestro** |
| 030 | Crédito, aprobación y reserva | Sí | 005 + 003 | 70 | 85 | 85 | 60 | 75 | 76 | SUBSTANTIALLY_COMPLETE | Momento de reserva en disputa (CL-013-06) |
| 031 | Cola y ruta de picking | Sí (DOCX) | esqueleto 005 | 10 | 15 | 25 | 5 | 10 | 14 | SKELETON_ONLY | **`PickListLine` sin ubicación ni secuencia** |
| 032 | Picking y consolidación | Sí (DOCX) | esqueleto 005 | 20 | 30 | 35 | 10 | 25 | 25 | SKELETON_ONLY | Sin almacenista, diferencia, daño ni consolidación |
| 033 | Confirmación independiente de pedido | Sí (DOCX) | **ninguna** | 0 | 0 | 0 | 0 | 0 | 0 | NOT_STARTED | **Etapa completa ausente del modelo** |
| 034 | Liberación para facturación y facturación | Sí (DOCX) | 005 + 007 | 55 | 55 | 50 | 45 | 60 | 54 | PARTIAL | **`SalesInvoice` sin `order_id`; sin compuerta de liberación** |
| 035 | Despacho, transporte y regulación | Sí | 005 + 008 | 65 | 70 | 70 | 55 | 65 | 66 | PARTIAL | Sin evidencia de entrega ni dirección estructurada |
| 036 | Devoluciones, NC y ND | Sí | 004 + 005 | 75 | 80 | 85 | 65 | 75 | 77 | SUBSTANTIALLY_COMPLETE | Inspección de devolución sin etapa propia |
| 037 | Cuentas por cobrar | Sí | 005 | 85 | 90 | 90 | 75 | 85 | 86 | SUBSTANTIALLY_COMPLETE | Gestión de cobranza sin flujo de promesas |
| 038 | Tesorería | Sí | 006 | 85 | 88 | 90 | 70 | 80 | 84 | SUBSTANTIALLY_COMPLETE | Diferencia cambiaria sin asiento explícito |
| 039 | Motor fiscal venezolano | Sí | 007 | 70 | 80 | 85 | 45 | 60 | 70 | PARTIAL | **LEGAL_BLOCKER**: alícuotas y vigencias no cargadas ni validadas |
| 040 | Retenciones IVA e ISLR | Sí | 007 + 004 | 65 | 75 | 85 | 40 | 55 | 65 | PARTIAL | **LEGAL_BLOCKER**: Decreto 1.808 sin conceptos cargados |
| 041 | IGTF | Sí | 006 + 007 | 70 | 80 | 85 | 45 | 60 | 70 | SUBSTANTIALLY_COMPLETE | **LEGAL_BLOCKER**: regla sin validación normativa |
| 042 | Documentos fiscales, controles y contingencia | Sí | 007 | 70 | 85 | 90 | 50 | 65 | 73 | PARTIAL | **Contingencia de facturación sin UI ni flujo** |
| 043 | Libros fiscales y cierres | Sí | 007 | 75 | 85 | 90 | 50 | 65 | 75 | SUBSTANTIALLY_COMPLETE | **LEGAL_BLOCKER**: formato de libro sin plantilla oficial |
| 044 | SICA / SIGESAI / SACS y movilización | Sí | 008 | 75 | 80 | 85 | 50 | 65 | 73 | SUBSTANTIALLY_COMPLETE | Matrices oficiales por rubro no cargadas |
| 045 | Motor de aprobaciones y segregación | Sí | **045** | 100 | 100 | 100 | 100 | 100 | 100 | **COMPLETE_100** | — (cerrada 2026-08-29, validada sobre PostgreSQL real) |
| 046 | Gestión documental y archivos | Sí | **046** | 100 | 100 | 100 | 100 | 100 | 100 | **COMPLETE_100** | — (cerrada 2026-08-30, validada sobre PostgreSQL 18.6 con ClamAV real) |
| 047 | Notificaciones y tareas | Sí | **ninguna** | 10 | 5 | 0 | 0 | 0 | 5 | NOT_STARTED | Sin alertas, tareas ni envío de correo |
| 048 | Integraciones | Sí | 010 parcial | 20 | 30 | 30 | 20 | 20 | 25 | PARTIAL | Solo licencia central; BCV/correo/storage/bancos ausentes |
| 049 | Dashboard y analítica | Sí | 009 | 60 | 60 | 60 | 40 | 50 | 56 | PARTIAL | Sin rotación, tendencias ni analítica real |
| 050 | Reportes empresariales | Sí | 009 | 75 | 80 | 80 | 60 | 70 | 74 | SUBSTANTIALLY_COMPLETE | Sin Excel; parametrización limitada |
| 051 | Auditoría empresarial avanzada | Sí | 009 + 001 | 70 | 65 | 85 | 50 | 55 | 66 | PARTIAL | Dos módulos sin instrumentar (ver TOP-10) |
| 052 | Instalador, actualización y migración | Sí | 001 | 50 | 65 | 70 | 50 | 40 | 57 | PARTIAL | Nunca ejecutado; sin rollback probado |
| 053 | Backup, recuperación y continuidad | Sí | 001 | 20 | 40 | 50 | 30 | 15 | 32 | SKELETON_ONLY | Scripts solo validados con `bash -n` |
| 054 | QA integral automatizado | Sí | 012 | 85 | 80 | 75 | 65 | 80 | 78 | SUBSTANTIALLY_COMPLETE | Sin dispositivos reales ni carga |
| 055 | Seguridad y hardening | Sí | 001 + 012 | 65 | 70 | 70 | 55 | 65 | 66 | PARTIAL | Sin SBOM, sin rate limiting global, sin política de uploads |
| 056 | Homologación fiscal y release | Sí | 011 | 75 | 80 | 85 | 50 | 60 | 73 | SUBSTANTIALLY_COMPLETE | **LEGAL_BLOCKER**: acto formal no ejecutado |

## Recuento de control

| Estado | Cantidad | Specs |
|---|---:|---|
| COMPLETE_100 | **1** | **045** |
| SUBSTANTIALLY_COMPLETE | **25** | 001,002,004,005,009,010,013,014,016,017,023,024,025,027,028,030,036,037,038,041,043,044,050,054,056 |
| PARTIAL | **17** | 003,006,007,015,019,026,029,034,035,039,040,042,048,049,051,052,055 |
| SKELETON_ONLY | **5** | 021,022,031,032,053 |
| FRONTEND_ONLY | **0** | — |
| BACKEND_ONLY | **0** | — |
| DATABASE_ONLY | **1** | 046 |
| BROKEN | **0** | — |
| NOT_STARTED | **5** | 012,018,020,033,047 |
| FUTURE_SCOPE | **0** | — |
| BLOCKED | **0** | — |
| OUT_OF_SCOPE | **0** | — |
| **TOTAL** | **56** | ✔ suma correcta (1+25+19+5+1+5 = 56) |

### Bandera secundaria `IMPLEMENTED_WITHOUT_SPEC` (5)

| Spec | Código sin trazabilidad documental |
|---|---|
| 007 | `cost_center_id` como `String(36)` en `purchase_requisitions` y `user_scopes`, sin tabla ni FK |
| 012 | `price_list`, `zone`, `payment_term` como texto libre en `customers` y `sales_quotes` |
| 045 | `approval_requests` (regulatorio) y aprobaciones ad-hoc por módulo sin Spec de motor |
| 046 | `file_metadata` sin Spec de gestión documental |
| 048 | Cliente HTTP `urllib.request` en `licensing/service.py:375` sin Spec de integraciones |

### Índice de madurez

| Nivel | Specs | Cantidad |
|---|---|---:|
| M0 — Documentada | 012, 018, 020, 033, 047 | 5 |
| M1 — Skeleton | 021, 022, 031, 032, 046, 053 | 6 |
| M2 — Funcionalidad aislada | 008, 011, 026, 045, 048, 049, 052, 055 | 8 |
| M3 — Integrada | 003, 006, 007, 015, 019, 029, 034, 035, 039, 040, 042, 051 | 12 |
| M4 — E2E probada | 001,002,004,005,009,010,013,014,016,017,023,024,025,027,028,030,036,037,038,041,043,044,050,054,056 | 25 |
| M5 — Production-ready | **ninguna** | 0 |
