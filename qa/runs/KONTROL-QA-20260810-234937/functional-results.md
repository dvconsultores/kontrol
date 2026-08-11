# RESULTADOS FUNCIONALES — RUN `KONTROL-QA-20260810-234937`

Estado: **BLOQUEADO POR KQA-001** (backend 502). No se pudo autenticar; ninguna fase funcional pudo ejecutarse.

## Fases / casos
| # | Fase | Caso | Resultado | Observación |
|---|---|---|---|---|
| 0 | Preflight | Disponibilidad | **FAIL** | SPA OK; API 502 |
| 1 | Login | Autenticación | **FAIL** | KQA-001 (502) |
| 2 | Menú y rutas | Recorrido menú | **BLOCKED** | Requiere login |
| 3 | GLOBAL DV | Crear/usar empresa | **BLOCKED** | Requiere login |
| 4 | Sucursales | Crear/listar/editar | **BLOCKED** | Requiere login |
| 5 | Almacenes | Crear/usar | **BLOCKED** | Requiere login |
| 6 | Config fiscal QA | Perfil/series/control | **BLOCKED** | Requiere login |
| 7 | Monedas/tasas | VED/USD/BCV | **BLOCKED** | Requiere login |
| 8 | Proveedores | ALFA/BETA | **BLOCKED** | Requiere login |
| 9 | Clientes | ORION/NOVA | **BLOCKED** | Requiere login |
| 10 | Productos | QA-MONITOR-24 etc. | **BLOCKED** | Requiere login |
| 11 | Servicios | QA-SOPORTE | **BLOCKED** | Requiere login |
| 12 | Precios | Lista QA | **BLOCKED** | Requiere login |
| 13-18 | Compra PO / Recepción / Factura / Conciliación / CxP / Pago | | **BLOCKED** | |
| 19 | Compra sin PO | | **BLOCKED** | |
| 20 | Inventario | | **BLOCKED** | |
| 21 | Transferencia | | **BLOCKED** | |
| 22 | Conteo/ajuste | | **BLOCKED** | |
| 23-31 | Cotización→Orden→Reserva→Picking→Despacho→Factura | | **BLOCKED** | |
| 32 | CxC / Cobro | | **BLOCKED** | |
| 33-41 | Venta directa / Devolución / NC / ND / Dev. proveedor / Anticipos / Retenciones / IGTF / Tesorería | | **BLOCKED** | |
| 42-43 | Reportes / PDF | | **BLOCKED** | |
| 44 | Auditoría | | **BLOCKED** | |
| 45-46 | Permisos / Seguridad | | **BLOCKED** | |
| 47 | Recorrido total menú | | **BLOCKED** | |
| 48-55 | Cross-browser | Login público | Chromium **PASS**; Firefox/WebKit **NOT_EXECUTED** | Ver browser-results |
| 56 | Responsive | Login público | **PASS** (5 viewports) | Ver responsive-results |
| 57 | Accesibilidad | Login público | **PARCIAL** | Campos con labels; axe completo NOT_EXECUTED |
| 58 | API | Contrato | **FAIL** (502) | KQA-001 |
| 59 | DB | Validación directa | **NOT_EXECUTED** | Sin acceso DB |
| 60 | Conciliación resultados | | **FAIL** | Ver resumen |

## Resumen
- PASS: 2 (responsive login, Chromium login render)
- FAIL: 4 (preflight disponibilidad, login, API, conciliación general)
- BLOCKED: 50+ (todas las fases funcionales autenticadas)
- NOT_EXECUTED: 2 (Firefox/WebKit, DB)
- NOT_IMPLEMENTED / EXPECTED_VALIDATION: 0 (no se pudo evaluar)
