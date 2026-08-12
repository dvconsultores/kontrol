# Matriz de Procesos E2E — Spec 012 (pasada 2)

> Base: E2E funcional in-process (`qa/functional-e2e-inprocess.py`, 20 pasos) + `tests/test_process_flows.py` + `tests/test_security_integration.py` + `tests/test_qa_fixes.py`. Evidencia ejecutada el 2026-08-12 sobre la app real (TestClient in-process, SQLite, licencia FULL_ACCESS QA).
> Resultado global: **19/20 PASS** (único FAIL: auditoría — ver KAUD-001).

| Proceso | Inicio | Final esperado | Front | API | Backend | DB | Efecto verificado | E2E | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| Login | /login | Dashboard | LoginPage | POST /auth/login | identity authenticate | users/sessions | token + sesión | ✅ | PASS |
| Empresa | Setup/crear | Empresa activa | EmpresasPage | POST /organization/companies | organization | companies | empresa creada | ✅ | PASS |
| Sucursales | Empresa activa | Sucursal creada | SucursalesPage | POST /organization/branches | organization | branches | 2 sucursales | ✅ | PASS |
| Almacenes | Sucursal | Almacén creado | AlmacenesPage | POST /organization/warehouses | organization | warehouses | 2 almacenes | ✅ | PASS |
| Terceros | Maestros | Proveedores/clientes | TercerosPage | POST /maestros/terceros | master_data | parties | 2 prov + 2 clientes | ✅ | PASS |
| Productos/Servicios | Maestros | Item + inventario | ProductosPage | POST /maestros/catalogos/items | master_data | catalog_items | items QA + servicio | ✅ | PASS |
| Compra (PO) | Proveedor | OC aprobada | OrdenesComprasPage | POST /purchasing/orders + lines + transition | purchasing | purchase_orders | OC-…-0001 aprobada | ✅ | PASS |
| Recepción | OC | Recepción confirmada | RecepcionesPage | POST /purchasing/receipts + confirm/quality/accept | purchasing | receipts | RC-…-0001 | ✅ | PASS |
| Factura proveedor | Recepción | POSTED | FacturasProveedorPage | POST /purchasing/supplier-invoices + transition | purchasing | supplier_invoices | FAC-…-0001 POSTED | ✅ | PASS |
| Conciliación triple-match | OC vs recepción vs factura | Consultable | — | GET /purchasing/triple-match | purchasing | — | 200 OK | ✅ | PASS |
| CxP + pago | Factura POSTED | Saldo 0 | CuentasPorPagarPage | POST /purchasing/payments + applications | purchasing | ap_payments/open_items | Saldo 0 | ✅ | PASS |
| Inventario (entrada) | Recepción | Existencias | ExistenciasPage | GET /inventory/balances | inventory | inventory_balances | MONITOR=10 TECLADO=20 | ✅ | PASS |
| Cotización | Cliente | COT | CotizacionesPage | POST /sales/quotes + lines | sales | quotes | COT-…-0001 | ✅ | PASS |
| Orden venta | Cotización | RESERVED | OrdenesVentasPage | POST /sales/orders + lines + transition | sales | sales_orders | OV-…-0001 RESERVED | ✅ | PASS |
| Picking/despacho | Orden RESERVED | Shipment validate | DespachoPage | POST /sales/pick-lists + shipments + validate | sales | pick_lists/shipments | PK/DESP-…-0001 | ✅ | PASS |
| Factura venta | Despacho | EMITTED + CxC | FacturasVentasPage | POST /sales/invoices + lines + transition | sales | sales_invoices/open_items | EMITTED | ✅ | PASS |
| CxC + cobro | Factura | Saldo 0 | CuentasPorCobrarPage | POST /sales/collections + applications | sales | ar_open_items | Saldo 0 | ✅ | PASS |
| Devolución venta | Factura | Devolución física | DevolucionesVentasPage | POST /sales/returns + lines | sales | returns | DEV-…-0001 | ✅ | PASS |
| Nota de crédito | Factura original | NC post | NotasVentasPage | POST /sales/credit-notes + post | sales/fiscal | credit_notes | NC-…-0001 post | ✅ | PASS |
| Transferencia | Almacén origen | Destino recibido | TransferenciasPage | POST /inventory/transfers + transition | inventory | transfers | TR-…-0001 | ✅ | PASS |
| Auditoría | Operaciones | Timeline | ReportesAuditoriaPage | GET /reporting/audit/timeline | reporting | audit_events | solo 2 eventos | ❌ | **FAIL (KAUD-001)** |

## Procesos con E2E de alcance parcial o pendiente de ambiente autorizado

| Proceso | Estado | Nota |
|---|---|---|
| Establecimiento / Ubicación | UI + API presentes | Sin paso E2E específico esta pasada |
| Usuarios / Roles / Sesiones | UI + API + enforcement probado | `test_process_flows` cubre asignación de rol |
| Licencia (modos) | Enforcement probado | READ_ONLY → 423 en escritura (test) |
| Multiempresa / tenant | Aislamiento probado | `test_security_integration` (8 tests) |
| Fiscal (emisión con correlativo/control) | Implementado; validación normativa pendiente | `fiscal-audit-checklist.md` (requiere ambiente homologación) |
| SICA / SIGESAI / SACS | Perfiles/permisos/traslados implementados | Validación regulatoria pendiente (no destructiva) |
| Reportes/exportación | Ver KAUD-002/003 | Exportación sin archivo real |
| Concurrencia / idempotencia | Parcial | Pruebas específicas no ejecutadas esta pasada (requiere dataset QA multi-usuario) |
| Backup/Restore real | Pendiente | Requiere PostgreSQL real + entorno aislado |
| Rendimiento P50/P95 | Pendiente | Sin dataset representativo autorizado |
| Navegadores reales (Edge/Opera/Safari) | Pendiente | Crawler chromium ejecutado; firefox/webkit simulados |

## Conclusión de procesos

Los **procesos maestros y operativos de extremo a extremo están conectados y funcionan** (compra→CxP→pago, venta→CxC→cobro, inventario→transferencia, devolución, NC). El único eslabón roto de la cadena es la **auditoría de negocio (KAUD-001)** y la **exportación (KAUD-002/003)**. Los procesos fiscales/regulatorios requieren validación normativa en ambiente de homologación.
