# SPEC — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Código | 004-compras-cuentas-por-pagar |
| Nombre | Compras y cuentas por pagar: requisición, cotización, orden, recepción, factura, conciliación triple, devolución y CxP |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** + **002-maestros** (terceros/proveedores con perfil fiscal y retenciones, catálogo) + **003-inventario-logistica** (motor de movimientos/costos para recepción). La implementación de 004 requiere 001 certificada, 002 y 003 implementados, y autorización expresa |
| Fuente | DOC-01 §4-5; DOC-02 §6, §9, §12; DOC-03 §8-9, §12-13; DOC-04 pantallas 09, 10 y 15; DOC-08 |
| Ruta | `specs/004-compras-cuentas-por-pagar/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **004-compras-cuentas-por-pagar**.

---

## 1. Problema

Con los maestros (002) y el motor de inventario (003) disponibles, falta el **ciclo de compra y las cuentas por pagar**: requisición → cotización → comparación → orden → aprobación → recepción → factura del proveedor → conciliación triple → devolución → CxP (open items, programación, pagos, anticipos, retenciones, aging).

Sin este módulo no es posible formalizar compras con control de aprobaciones y segregación, recibir contra órdenes registrando lotes/seriales/calidad (usando el motor de 003), validar la duplicidad de facturas del proveedor, conciliar orden-recepción-factura, ni gestionar la deuda con proveedores (saldo, vencimientos, aplicaciones) — todo ello exigido por la Constitución (P5 datos históricos protegidos, P8 no hardcodear, P13 integridad transaccional).

## 2. Objetivos

1. **Requisición**: identificar necesidades con líneas, centro de costo y aprobación.
2. **Cotización y comparación**: solicitar ofertas, registrar ofertas (vigencia, moneda, condiciones) y comparar por precio/impuesto/disponibilidad/plazo/calidad.
3. **Orden de compra**: emitir y aprobar según monto/categoría/excepción (segregación); máquina de estados.
4. **Recepción**: recibir parcial o totalmente con lotes/seriales/vencimientos y calidad, **invocando el motor de 003** (sin duplicar saldos/costos).
5. **Factura del proveedor**: registro con **validación de duplicidad**, vínculo a orden/recepción y estados.
6. **Conciliación triple**: orden ↔ recepción ↔ factura con diferencias explícitas y resolución auditada.
7. **Devoluciones y notas**: devolución física y nota de crédito del proveedor (la nota reduce CxP).
8. **CxP**: open items (PAYABLE), programación de pagos, pagos con medios e idempotencia, aplicaciones (pago/anticipo/nota/retención), anticipos, retenciones en pago y aging.
9. **Integración**: 003 provee recepción/costos; 006 (tesorería) tomará los pagos para conciliación; 007 (fiscal) proveerá el motor de retenciones.

## 3. Fuera de alcance

- **Tesorería completa** (cajas, bancos, conciliación bancaria, flujo de caja) — **Spec 006**. 004 registra el pago OUT necesario para reducir el saldo de CxP; la conciliación bancaria/física es de 006.
- **Ventas/CxC** — Spec 005.
- **Núcleo fiscal** (IVA/ISLR/IGTF, emisión de comprobantes, libros, cierres, contingencias) — **Spec 007**. 004 estructura las retenciones y las refiere a reglas versionadas; el cálculo fiscal completo vive en 007.
- **Regulación y traslados** — Spec 008.
- **Reportes** ejecutivos/fiscales — Spec 009.

## 4. Actores

| Actor | Uso |
|---|---|
| Solicitante | Crea requisiciones |
| Comprador | Revisa requisiciones, solicita cotizaciones, compara y emite órdenes |
| Aprobador (según monto/categoría) | Aprueba compras |
| Almacén | Recibe contra orden (lotes/seriales/calidad) |
| Control de calidad | Revisa recepción |
| Contador | Registra factura del proveedor, conciliación triple y retenciones |
| CxP | Programa pagos, aplica pagos/anticipos/notas, gestiona aging |
| Tesorería / Aprobador de pago | Revisa/aprueba pagos |
| Auditor | Consulta trazabilidad del ciclo de compra |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-004-001 | Como solicitante, quiero crear una requisición con líneas y centro de costo para formalizar una necesidad. |
| US-004-002 | Como comprador, quiero solicitar cotizaciones y registrar ofertas para comparar proveedores. |
| US-004-003 | Como comprador, quiero comparar ofertas por precio, impuesto, disponibilidad, plazo y calidad para seleccionar proveedor. |
| US-004-004 | Como comprador, quiero emitir una orden de compra y aprobarla según monto, categoría y excepción. |
| US-004-005 | Como almacén, quiero recibir parcial o totalmente registrando lotes, seriales, vencimientos y calidad. |
| US-004-006 | Como contador, quiero registrar la factura del proveedor validando duplicidad y requisitos. |
| US-004-007 | Como contador, quiero conciliar orden, recepción y factura (triple) con diferencias explícitas. |
| US-004-008 | Como compras, quiero gestionar devoluciones y notas del proveedor. |
| US-004-009 | Como CxP, quiero crear open items, programar pagos y evitar duplicidad. |
| US-004-010 | Como CxP, quiero aplicar pagos, anticipos, notas y retenciones al saldo de CxP. |
| US-004-011 | Como contador, quiero ver el aging de CxP para gestionar vencimientos. |
| US-004-012 | Como sistema, quiero que la factura del proveedor no se duplique (clave de duplicidad). |
| US-004-013 | Como auditor, quiero la trazabilidad completa del ciclo de compra (requisición → pago). |

## 6. Requisitos funcionales

Convención: `FR-004-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Requisición

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-001 | `PurchaseRequisition`: solicitante, centro de costo, fecha necesidad, líneas, aprobación y estado. | DOC-03 §8 | P0 | Solicitante |
| FR-004-002 | Flujo de requisición: DRAFT → SUBMITTED → APPROVED/REJECTED. | DOC-02 §6 paso 1-2 | P0 | Sistema |

### 6.2 Cotización y comparación

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-010 | `SupplierQuote`: proveedor, vigencia, moneda, condiciones, líneas y anexos. | DOC-03 §8 | P0 | Comprador |
| FR-004-011 | Solicitar cotizaciones a varios proveedores para la misma necesidad. | DOC-02 §6 paso 3 | P1 | Comprador |
| FR-004-012 | Comparación por precio, impuesto, disponibilidad, plazo y calidad (no solo precio). | DOC-02 §6 paso 5 | P1 | Comprador |

### 6.3 Orden de compra

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-020 | `PurchaseOrder`: proveedor, condiciones, fechas esperadas, líneas, aprobaciones y estado. | DOC-03 §8 | P0 | Comprador |
| FR-004-021 | Máquina de estados OC: DRAFT → SUBMITTED → APPROVED → PARTIALLY_RECEIVED → RECEIVED → CLOSED; CANCELLED. | DOC-03 §13 | P0 | Sistema |
| FR-004-022 | Aprobación según monto, categoría y excepción (segregación: Solicitante crea, Comprador revisa, Aprobador aprueba). | DOC-02 §12 | P0 | Aprobador |
| FR-004-023 | La OC **no sustituye** la recepción ni la factura del proveedor. | DOC-04 pantalla 09 | P0 | Sistema |

### 6.4 Recepción (integración con 003)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-030 | `GoodsReceipt`: orden, almacén, líneas aceptadas/rechazadas, lote/serial, calidad y estado. | DOC-03 §8 | P0 | Almacén |
| FR-004-031 | Máquina de estados recepción: DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED/PARTIALLY_ACCEPTED/REJECTED → CLOSED. | DOC-03 §13 | P0 | Sistema |
| FR-004-032 | Recibir parcial o totalmente; registrar lotes, seriales, vencimientos y calidad. | DOC-02 §6 paso 8 | P0 | Almacén |
| FR-004-033 | La recepción **invoca el servicio `receive` de 003** (entrada + lotes/seriales + capas de costo) sin duplicar lógica de saldos. | DOC-01 §1, 003 | P0 | Sistema |
| FR-004-034 | Recepción en exceso/defecto respecto a la OC con política y aprobación. | DOC-02 §6 | P1 | Sistema |

### 6.5 Factura del proveedor

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-040 | `SupplierInvoice`: proveedor, número de factura/control, fechas, impuestos, vínculo orden/recepción y estado. | DOC-03 §8 | P0 | Contador |
| FR-004-041 | Validación de duplicidad: `Unique(company, supplier, invoice_number, control_number)` con excepciones documentadas. | DOC-03 §12 | P0 | Sistema |
| FR-004-042 | Máquina de estados: DRAFT → VALIDATED → MATCHED/EXCEPTION → APPROVED → POSTED → PARTIALLY_PAID → PAID; REVERSED. | DOC-03 §13 | P0 | Sistema |
| FR-004-043 | No existe eliminación física de facturas del proveedor postadas; corrección mediante **reverso vinculado** (P5). | DOC-01 §5 | P0 | Sistema |

### 6.6 Conciliación triple

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-050 | `TripleMatch`: orden_line, recepción_line, factura_line, variaciones, resolución y aprobación. | DOC-03 §8 | P0 | Contador |
| FR-004-051 | Diferencias explícitas y resolución auditada (precio, cantidad, impuesto). | DOC-04 pantalla 10 | P0 | Sistema |
| FR-004-052 | La factura no pasa a POSTED sin conciliación (o excepción documentada y aprobada). | DOC-02 §6 paso 10 | P0 | Sistema |

### 6.7 Devoluciones y notas del proveedor

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-060 | `Return`: documento origen, motivo, condición y destino de inventario (via 003). | DOC-03 §8 | P1 | Compras |
| FR-004-061 | La **nota de crédito del proveedor reduce CxP**; la devolución física no la sustituye (DOC-01 §5). | DOC-01 §5 | P1 | Sistema |

### 6.8 CxP (open items, pagos, aplicaciones, anticipos, retenciones)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-070 | `OpenItem` (PAYABLE): parte, documento origen, moneda, original, aplicado, saldo, vencimiento y estado. | DOC-03 §9 | P0 | CxP |
| FR-004-071 | Saldo CxP = facturas + débitos − pagos − retenciones − créditos (se calcula, no se edita; P5). | DOC-02 §9 | P0 | Sistema |
| FR-004-072 | `Payment` (OUT) + `PaymentInstrument`: registro de pago con medios/monedas; **idempotencia**; evita duplicidad. | DOC-03 §9, DOC-01 §3 | P0 | CxP |
| FR-004-073 | `Application`: relaciona origen (pago/anticipo/nota/retención) con destino (open item), montos origen/destino/fiscal, tasa y fecha; **no excede saldo**; operación atómica. | DOC-03 §9/§12 | P0 | Sistema |
| FR-004-074 | `Advance` (anticipo a proveedor): dirección OUT, moneda, monto, disponible e imputación posterior. | DOC-03 §9 | P1 | CxP |
| FR-004-075 | Programación de pagos y **aging** de CxP. | DOC-02 §9 | P1 | CxP |
| FR-004-076 | Retención en pago o abono en cuenta: calculada por **regla versionada** (referencia a 007); estados CALCULADA → PRACTICADA → EMITIDA → DECLARADA → PAGADA → CONCILIADA; REVERSADA. | DOC-02 §6/§11, DOC-03 §13 | P0 | Contador |
| FR-004-077 | Segregación: **Pago** — crea CxP, revisa Tesorería, aprueba Aprobador de pago. | DOC-02 §12 | P0 | Sistema |
| FR-004-078 | La moneda de pago no modifica por sí sola el IVA causado (DOC-01 §5). | DOC-01 §5 | P0 | Sistema |

### 6.9 Transversales (NFR)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-004-100 | Aislamiento multiempresa en todos los agregados. | DOC-03 §12 | P0 | Sistema |
| FR-004-101 | Idempotencia en POST críticos (recepción, factura, pago, aplicación). | DOC-01 §3 | P0 | Sistema |
| FR-004-102 | Decimal exacto; **snapshot** por línea (producto, precio, impuesto, tasa) (P4/P8). | DOC-01 §3 | P0 | Sistema |
| FR-004-103 | Frontend: pantallas completas (orden de compra WF-04, conciliación triple WF-05, pago/retenciones), sin scroll horizontal, búsqueda asíncrona. | DOC-08, DOC-04 | P0 | Sistema |
| FR-004-104 | Los saldos de CxP se calculan desde documentos y aplicaciones; nunca se editan (P5). | DOC-01 §5 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5)

- No existe eliminación física de facturas postadas, pagos aprobados ni retenciones; toda corrección es un reverso vinculado (P5).
- Los saldos de CxP se calculan desde documentos y aplicaciones; no se editan.
- La factura del proveedor valida duplicidad (`company, supplier, invoice, control`) antes de postarse.
- La conciliación triple es previa a POSTED salvo excepción documentada y aprobada.
- Aplicaciones atómicas con bloqueo; ninguna aplicación excede el saldo de origen ni destino.
- Retenciones y aprobaciones de compra se rigen por reglas **versionadas** (P8), no por porcentajes hardcodeados.
- El motor de saldos de inventario es de 003: 004 lo invoca y no duplica lógica.
- La moneda de pago no altera el IVA causado por sí sola (DOC-01 §5).

## 8. Criterios de éxito (resumen)

- Una necesidad recorre requisición → cotización → comparación → orden aprobada con segregación.
- La recepción parcial/total registra lotes/seriales/vencimientos/calidad y actualiza el inventario **vía 003** (sin duplicar saldos).
- La factura del proveedor no se duplica; exige conciliación triple (o excepción) antes de postarse.
- El saldo de CxP se calcula y refleja pagos, anticipos, notas y retenciones aplicadas.
- Los pagos son idempotentes y no sobrededucen el saldo; retenciones referidas a reglas versionadas.
- El aging de CxP permite gestionar vencimientos.
- 006 (tesorería) podrá consumir los pagos de 004 para conciliación.
