# CLARIFICACIONES — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-005-01 | Motor de CxC | ¿005 duplica el motor de aplicaciones de 004? | **No.** 005 **reutiliza** `ap_open_items` (item_type RECEIVABLE), `ap_applications`, `ap_advances`, `ap_withholdings` y el motor atómico de 004. No se duplica lógica (Constitución P4, FR-005-042) | Arquitecto | Resuelto |
| CL-005-02 | Emisión fiscal | ¿005 emite la factura fiscal? | 005 emite el **documento comercial** con **snapshot fiscal** (base VES, tasa). La **emisión fiscal formal** (correlativos, números de control, libros, cálculo IVA/ISLR/IGTF) es de **007** | Contador/fiscal | Resuelto |
| CL-005-03 | Reserva/picking/despacho | ¿005 duplica el motor de inventario? | **No.** 005 invoca el motor de **003** (`reserve`, `pick`, `ship` + costo de salida) y no duplica saldos | Arquitecto | Resuelto |
| CL-005-04 | Regulación del despacho | ¿005 valida SICA/SIGESAI/SACS? | 005 registra el **punto de validación/bloqueo**; la regulación funcional completa (permisos, guías) es de **008** (DOC-01 §5) | Logística | Resuelto |
| CL-005-05 | Cobros multimoneda | ¿Se permiten varios medios y monedas por cobro? | Sí: cobro IN con múltiples instrumentos y monedas; aplicación independiente del documento (DOC-04 pantalla 14) | CxC | Resuelto |
| CL-005-06 | Aprobación de crédito | ¿Reglas hardcodeadas? | No: límites y reglas de crédito/aprobación **versionadas** por empresa (P8) | Crédito | Resuelto |
| CL-005-07 | Dependencias | ¿Se implementa 005 sin 004? | Requiere **001 certificada**, **002/003/004 implementados** y autorización expresa. La fase documental no requiere nada | Producto | Resuelto |
| CL-005-08 | Devolución vs. nota | ¿La devolución de cliente reduce CxC? | No por sí sola: la **nota de crédito** reduce CxC; la devolución física actualiza inventario vía 003 (DOC-01 §5) | CxC | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-005-01 | La factura de venta comercial no requiere emisión fiscal hasta 007 | Documento sin numeración fiscal | Snapshot fiscal por línea; migración sin reescritura |
| SU-005-02 | 006 consumirá los cobros de 005 para conciliación; 005 no concilia bancos | Acoplamiento con 006 | Contrato de API versionado para cobros/aplicaciones |
| SU-005-03 | Cada línea de factura conserva snapshot (producto, precio, impuesto, tasa) | Cambios de catálogo no alteran histórico | Snapshot por línea (P4/P8) |
| SU-005-04 | Las líneas de servicio de una OV no reservan inventario | OV mixta | Líneas sin inventario no invocan 003 |
| SU-005-05 | Política de crédito (límites/días) por empresa | Exposición crediticia | Reglas versionadas; pendiente CL-005-09 |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-005-09 | Política de crédito y límites por empresa | Aprobación de crédito | No la fase documental |
| CL-005-10 | Días de vencimiento por condición de pago | Aging y CxC | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
