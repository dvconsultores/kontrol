# CLARIFICACIONES — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/004-compras-cuentas-por-pagar/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-004-01 | Alcance del pago vs. 006 | ¿004 incluye el pago o lo deja a tesorería? | 004 **registra el pago OUT** contra CxP (necesario para reducir el saldo, DOC-02 §6 paso 13) con instrumentos e idempotencia. La **conciliación bancaria/caja física** y el flujo de tesorería completo son de 006, que consumirá los pagos de 004 | Producto | Resuelto |
| CL-004-02 | Retenciones | ¿004 calcula retenciones? | 004 estructura la retención (estados) y la **refiere a reglas versionadas** (perfil del proveedor 002, regla de referencia). El **motor fiscal** completo (IVA/ISLR/IGTF, comprobantes, libros) es de **007** | Contador/fiscal | Resuelto |
| CL-004-03 | Recepción e inventario | ¿004 duplica el motor de inventario? | **No.** 004 invoca el servicio `receive` de **003** (entrada + lotes/seriales + capas de costo) y no duplica saldos ni costos (Constitución P4/FR-004-104) | Arquitecto | Resuelto |
| CL-004-04 | Conciliación previa a POSTED | ¿La factura puede postarse sin conciliar? | No por defecto: la conciliación triple es previa a POSTED. Excepción documentada y aprobada (diferencias toleradas) | Contador | Resuelto |
| CL-004-05 | Anticipos | ¿Cómo se tratan los anticipos a proveedor? | `Advance` (OUT) con disponible sin aplicar; imputación posterior mediante aplicaciones (parciales/múltiples) | CxP | Resuelto |
| CL-004-06 | Dependencias | ¿Se implementa 004 sin 003? | Requiere **001 certificada**, **002 y 003 implementados** y autorización expresa. La fase documental no requiere nada | Producto | Resuelto |
| CL-004-07 | Devolución vs. nota | ¿La devolución física reduce la CxP? | No por sí sola: la **nota de crédito del proveedor** reduce CxP; la devolución física actualiza inventario vía 003 (DOC-01 §5) | Compras | Resuelto |
| CL-004-08 | Duplicidad de factura | ¿Siempre se rechaza el duplicado? | Sí, con clave `(company, supplier, invoice, control)`; excepciones documentadas (p. ej. notas/reemisiones) con aprobación | Contador | Resuelto |
| CL-004-09 | Pagos parciales | ¿Se permiten pagos parciales y múltiples medios? | Sí: pagos parciales, múltiples instrumentos y monedas; aplicación atómica que no excede el saldo | CxP | Resuelto |
| CL-004-10 | Aprobación de compra | ¿Reglas hardcodeadas por monto? | No: reglas de aprobación **versionadas** por empresa (monto, categoría, excepción), P8 | Arquitecto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-004-01 | El cálculo de retención usa reglas de referencia hasta que 007 provea el motor fiscal | Retención incompleta | Estados de retención trazables; migración sin reescritura |
| SU-004-02 | 006 consumirá los pagos de 004 para conciliación; 004 no concilia bancos | Acoplamiento con 006 | Contrato de API versionado para `Payment`/`Application` |
| SU-004-03 | Cada línea de documento conserva **snapshot** de producto/precio/impuesto/tasa | Cambios de catálogo no alteran histórico | Snapshot por línea (P4/P8) |
| SU-004-04 | Las líneas de servicio de una OC no requieren recepción de inventario | OC mixta | Líneas sin recepción no afectan 003 |
| SU-004-05 | La recepción en exceso/defecto sigue política de tolerancia configurable | Diferencias | Tolerancias por empresa (pendiente CL-004-12) |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-004-11 | Umbrales de aprobación de compra por monto/categoría por empresa | Aprobaciones | No la fase documental |
| CL-004-12 | Tolerancias de recepción y sobrefacturación por empresa | Conciliación triple | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
