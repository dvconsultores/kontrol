# MATRIZ FUNCIONAL / CERTIFICACIÓN — RUN `KONTROL-QA-20260810-234937`

## Matriz funcional (resumen)
| Módulo | Proceso | Caso | UI | API | DB | Efecto | E2E | Resultado |
|---|---|---|---|---|---|---|---|---|
| Global | Login | Autenticación | Render OK | **502** | — | — | — | **FAIL (KQA-001)** |
| Organización | Empresa/Sucursales/Almacenes | CRUD | — | 502 | — | — | — | BLOCKED |
| Maestros | Proveedores/Clientes/Productos/Servicios | CRUD | — | 502 | — | — | — | BLOCKED |
| Compras | PO/Recepción/Factura/Conciliación/CxP/Pago | Flujo | — | 502 | — | — | — | BLOCKED |
| Inventario | Recepción/Transferencia/Conteo/Kardex | Flujo | — | 502 | — | — | — | BLOCKED |
| Ventas | Cotización/Orden/Despacho/Factura | Flujo | — | 502 | — | — | — | BLOCKED |
| CxC/CxP | Cobros/Pagos | Flujo | — | 502 | — | — | — | BLOCKED |
| Fiscal | Notas/Retenciones/IGTF | Flujo | — | 502 | — | — | — | BLOCKED |
| Tesorería | Cajas/Pagos/Conciliación | Flujo | — | 502 | — | — | — | BLOCKED |
| Reportes/Auditoría | Reportes + traza | Flujo | — | 502 | — | — | — | BLOCKED |

## Criterio de proceso completo
Todos los procesos: **COMPLETE = FALSE** (bloqueados por KQA-001 antes del login).

## Ruta de evidencias
`qa/runs/KONTROL-QA-20260810-234937/` (preflight, findings, functional-results, process-results, test-data, cleanup-plan, summary, certification; screenshots/ del login).

## Screenshots
- `screenshots/login-responsive-*.png` (5 viewports, generados con Chromium real del navegador integrado; los del script Playwright no se pudieron escribir por límites del sandbox).
