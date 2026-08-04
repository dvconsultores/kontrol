# CRITERIOS DE ACEPTACIÓN — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/acceptance-criteria.md` |

## Criterios globales

| ID | Criterio | Verificación |
|---|---|---|
| AC-004-001 | La OC recorre DRAFT → … → CLOSED con aprobación por regla versionada y segregación | Test de máquina de estados |
| AC-004-002 | La recepción registra lotes/seriales/vencimientos/calidad y actualiza inventario **vía 003** sin duplicar saldos | Test de integración |
| AC-004-003 | La factura del proveedor valida duplicidad `(company, supplier, invoice, control)` y no se posta sin conciliación (o excepción) | Test de duplicidad/conciliación |
| AC-004-004 | El saldo de CxP se calcula desde documentos y aplicaciones; nunca se edita | Test de saldo |
| AC-004-005 | Ninguna aplicación excede el saldo de origen ni destino; operación atómica | Test de aplicación/concurrencia |
| AC-004-006 | Los pagos son idempotentes y no se duplican | Test de idempotencia |
| AC-004-007 | La retención se rige por regla versionada (referencia a 007), no por porcentaje hardcodeado | Test de retención |
| AC-004-008 | 006 puede consumir `Payment`/`Application` para conciliación | Contract test |
| AC-004-009 | Aislamiento multiempresa probado con pruebas negativas | Pytest negativo |
| AC-004-010 | Cada línea conserva snapshot (producto, precio, impuesto, tasa) | Test de snapshot |
| AC-004-011 | Cada requisito tiene identificador, fuente, dueño, criterio y prueba | Trazabilidad |
| AC-004-012 | No se hardcodean umbrales de aprobación ni tasas de retención | Revisión de código |

## Criterios por historia (US)

| Historia | Criterio |
|---|---|
| US-004-001 | La requisición se crea con líneas y centro de costo y pasa por aprobación |
| US-004-002 | Se solicitan/registran ofertas de varios proveedores con vigencia y moneda |
| US-004-003 | La comparación considera precio, impuesto, disponibilidad, plazo y calidad |
| US-004-004 | La OC se emite y aprueba según regla de monto/categoría con segregación |
| US-004-005 | La recepción parcial/total registra lotes, seriales, vencimientos y calidad |
| US-004-006 | La factura del proveedor se registra validando duplicidad y requisitos |
| US-004-007 | La conciliación triple muestra diferencias explícitas y resolución auditada |
| US-004-008 | La devolución física y la nota de crédito se gestionan; la nota reduce CxP |
| US-004-009 | Se crean open items y programación de pagos sin duplicidad |
| US-004-010 | Pagos/anticipos/notas/retenciones se aplican al saldo sin excederlo |
| US-004-011 | El aging de CxP muestra buckets de vencimiento |
| US-004-012 | Una factura duplicada del proveedor se rechaza (o excepción documentada) |
| US-004-013 | La auditoría cubre requisición → pago con quién/cuándo/qué |

## Criterios de la fase documental

| ID | Criterio | Estado |
|---|---|---|
| AC-004-DOC-001 | Spec 004 completa | ✔ |
| AC-004-DOC-002 | Ambigüedades resueltas o bloqueadas | ✔ (pendientes registrados) |
| AC-004-DOC-003 | Plan pasa la Constitución | ✔ |
| AC-004-DOC-004 | Modelo de datos documentado | ✔ |
