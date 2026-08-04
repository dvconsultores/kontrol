# SPEC — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Código | 005-ventas-cuentas-por-cobrar |
| Nombre | Ventas y cuentas por cobrar: cotización, pedido, crédito, orden, reserva, picking, despacho, factura y CxC |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** + **002-maestros** (clientes con perfil de crédito/fiscal, catálogo) + **003-inventario-logistica** (reservas, picking, salida y costo) + **004-compras-cuentas-por-pagar** (motor de aplicaciones CxC). La implementación de 005 requiere 001 certificada, 002/003/004 implementados, y autorización expresa |
| Fuente | DOC-01 §4-5; DOC-02 §7, §9, §12; DOC-03 §8, §13; DOC-04 pantallas 11-14; DOC-08 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **005-ventas-cuentas-por-cobrar**.

---

## 1. Problema

Con los maestros (002), el motor de inventario (003) y el ciclo de compras con el motor de aplicaciones CxP (004), falta el **ciclo de ventas y las cuentas por cobrar**: cotización → pedido → crédito → orden aprobada → reserva → picking → despacho → factura de venta → CxC (cobros, anticipos, retenciones sufridas, aplicaciones, notas, aging, cobranza).

Sin este módulo no es posible formalizar ventas con control de crédito y aprobaciones, reservar/pickear/despachar usando el motor de 003, emitir facturas de venta comerciales (base fiscal VES y tasa snapshot), ni gestionar la cartera por cobrar (saldo, vencimientos, cobros multimoneda, aplicaciones) — todo ello exigido por la Constitución (P5 datos históricos protegidos, P8 no hardcodear, P13 integridad transaccional).

## 2. Objetivos

1. **Cotización y pedido**: cotizar sin reservar inventario; recibir pedido y validar datos del cliente.
2. **Crédito y aprobación**: analizar crédito, margen, precios y excepciones; aprobar orden con segregación (reglas versionadas).
3. **Reserva, picking y despacho**: invocar el motor de **003** (reserva, picking, salida a tránsito/entregado-no-facturado, costo de salida); validar documentos y bloquear el despacho si falta/venció/no coincide algo.
4. **Factura de venta**: documento comercial con líneas producto+servicio, base fiscal en VES, tasa snapshot y estados; inmutable (P5).
5. **CxC**: open items (RECEIVABLE), cobros multimoneda con idempotencia, aplicaciones atómicas (cobro/anticipo/nota/retención sufrida), anticipos, notas vinculadas, aging y cobranza — **reutilizando el motor de aplicaciones de 004**.
6. **Integración**: 003 provee reserva/picking/salida; 006 (tesorería) consumirá los cobros; 007 (fiscal) proveerá la emisión fiscal formal.

## 3. Fuera de alcance

- **Tesorería completa** (cajas, bancos, conciliación) — **Spec 006**. 005 registra el cobro (Payment IN) necesario para reducir CxC; la conciliación bancaria es de 006.
- **Núcleo fiscal** (numeración, correlativos, números de control, libros, cierres, contingencias, cálculo IVA/ISLR/IGTF) — **Spec 007**. 005 emite el documento comercial con **snapshot fiscal**; la emisión fiscal formal es de 007.
- **Regulación y traslados** (SICA/SIGESAI/SACS, permisos) — **Spec 008**. 005 registra el punto de validación/bloqueo del despacho.
- **Reportes** — Spec 009.

## 4. Actores

| Actor | Uso |
|---|---|
| Vendedor | Cotiza, recibe pedidos, emite órdenes |
| Crédito / gerencia | Analiza crédito, margen y excepciones |
| Aprobador comercial | Aprueba órdenes y cobros con excepción |
| Almacén / logística | Picking, preparación y confirmación de salida |
| Contador / fiscal | Factura de venta, retenciones sufridas, notas |
| CxC / cobranza | Cobros, aplicaciones, aging, gestión de cobranza |
| Auditor | Trazabilidad del ciclo de venta |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-005-001 | Como vendedor, quiero emitir una cotización sin reservar inventario. |
| US-005-002 | Como vendedor, quiero recibir un pedido y validar los datos del cliente. |
| US-005-003 | Como crédito, quiero analizar crédito, margen, precios y excepciones. |
| US-005-004 | Como aprobador, quiero aprobar una orden de venta y que se reserve inventario. |
| US-005-005 | Como almacén, quiero generar el picking y preparar la orden. |
| US-005-006 | Como logística, quiero validar documentos de traslado y permisos regulatorios antes de la salida. |
| US-005-007 | Como almacén, quiero confirmar la salida y mover inventario a tránsito o entregado-no-facturado. |
| US-005-008 | Como contador, quiero emitir la factura de venta (producto + servicio, base fiscal VES, tasa snapshot). |
| US-005-009 | Como CxC, quiero crear la CxC y registrar cobros, anticipos y retenciones sufridas. |
| US-005-010 | Como CxC, quiero aplicar notas, devoluciones y diferencias cambiarias al saldo. |
| US-005-011 | Como cobranza, quiero ver el aging de CxC y gestionar la cartera. |
| US-005-012 | Como usuario, quiero conciliar y cerrar el ciclo de venta. |

## 6. Requisitos funcionales

Convención: `FR-005-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Cotización y pedido

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-001 | `SalesQuote`: cliente, lista de precios, vigencia, líneas y estado; **no reserva inventario** (DOC-02 §7 paso 2). | DOC-03 §8 | P0 | Vendedor |
| FR-005-002 | `SalesOrder` (pedido): cliente, datos validados, líneas y estado (DOC-02 §7 paso 3). | DOC-03 §8 | P0 | Vendedor |

### 6.2 Crédito y aprobación

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-010 | Análisis de crédito: límite, bloqueo, saldo CxC, aging, margen y precios (separados: crédito/margen/reserva). | DOC-04 pantalla 11 | P0 | Crédito |
| FR-005-011 | Máquina de estados OV: DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED → PREPARING → SHIPPED → CLOSED; CANCELLED. | DOC-03 §13 | P0 | Sistema |
| FR-005-012 | Aprobación con excepción (segregación: Vendedor crea, Crédito/gerencia revisa, Aprobador comercial aprueba). | DOC-02 §12 | P0 | Aprobador |

### 6.3 Reserva, picking y despacho (integración con 003)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-020 | Aprobar la OV → **reservar inventario vía 003** (reserva; disponible sin cambio físico). | DOC-02 §7 paso 5 | P0 | Sistema |
| FR-005-021 | `PickList`: lista → confirmación de ubicación/lote/serial → preparación (vía 003). | DOC-02 §8 | P1 | Almacén |
| FR-005-022 | Confirmar salida → mover a **tránsito** o **entregado-no-facturado** (vía 003 `ship`; costo de salida). | DOC-02 §7 paso 8 | P0 | Sistema |
| FR-005-023 | El despacho se **bloquea** si falta un documento obligatorio, está vencido o no coincide producto/lote/cantidad/origen/destino. | DOC-01 §5 | P0 | Sistema |
| FR-005-024 | La regulación del despacho (SICA/SIGESAI/SACS) se evalúa en **Spec 008**; 005 registra el punto de validación. | DOC-01 §5 | P1 | Sistema |

### 6.4 Factura de venta

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-030 | Factura de venta: cliente, líneas producto/servicio, base fiscal en **VES**, **tasa snapshot**, estados. | DOC-03 §8, DOC-04 pantalla 13 | P0 | Contador |
| FR-005-031 | Máquina de estados: DRAFT → VALIDATED → APPROVED → EMITTED → DELIVERED → PARTIALLY_PAID → PAID; CREDITED/VOIDED. | DOC-03 §13 | P0 | Sistema |
| FR-005-032 | Factura emitida **inmutable**; corrección mediante nota de crédito/débito o anulación vinculada (P5). | DOC-01 §5 | P0 | Sistema |
| FR-005-033 | La **emisión fiscal formal** (correlativos, números de control, libros) es de **007**; 005 emite el documento comercial con snapshot fiscal. | DOC-01 §1, DOC-04 pantalla 13 | P0 | Sistema |
| FR-005-034 | Líneas mixtas producto+servicio; el servicio no afecta inventario. | DOC-01 §8 | P0 | Sistema |

### 6.5 CxC

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-040 | OpenItem (**RECEIVABLE**) al emitir factura; saldo = documentos + débitos − cobros − retenciones − créditos. | DOC-02 §9 | P0 | CxC |
| FR-005-041 | Cobros: pago **IN** con medios/monedas e idempotencia; cobros separados de la obligación. | DOC-02 §9, DOC-04 pantalla 14 | P0 | CxC |
| FR-005-042 | Aplicaciones (cobro/anticipo/nota/retención sufrida) → open item; **atómicas**, no exceden saldo; **reutiliza el motor de 004**. | DOC-03 §9/§12 | P0 | Sistema |
| FR-005-043 | Anticipos de clientes con imputación posterior. | DOC-02 §9 | P1 | CxC |
| FR-005-044 | Retenciones **sufridas** (ISLR/IVA) registradas y aplicadas. | DOC-02 §9 | P0 | Contador |
| FR-005-045 | Notas de crédito/débito vinculadas; diferencias cambiarias sin alterar el IVA original. | DOC-02 §9 | P1 | Contador |
| FR-005-046 | Aging de CxC y **gestión de cobranza** (promesas, bloqueos). | DOC-02 §9 | P1 | CxC |
| FR-005-047 | Devolución de cliente (destino de inventario vía 003) **no sustituye** la nota de crédito. | DOC-01 §5 | P1 | Sistema |
| FR-005-048 | Segregación del cobro: crea, revisa, aprueba (Aprobador comercial). | DOC-02 §12 | P0 | Sistema |

### 6.6 Transversales (NFR)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-005-100 | Aislamiento multiempresa; idempotencia en POST críticos; decimal exacto; snapshot por línea. | DOC-03 §12, DOC-01 §3 | P0 | Sistema |
| FR-005-101 | Frontend: pantallas completas (OV WF-04, despacho WF-04, factura WF-04, cobro multimoneda WF-02), sin scroll horizontal, búsqueda asíncrona. | DOC-08, DOC-04 | P0 | Sistema |
| FR-005-102 | La moneda de pago no modifica por sí sola el IVA causado. | DOC-01 §5 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5)

- No existe eliminación física de facturas emitidas, cobros aplicados ni retenciones; corrección por nota/anulación/reverso vinculado (P5).
- Los saldos de CxC se calculan desde documentos y aplicaciones; no se editan.
- La cotización no reserva inventario; la reserva se hace al aprobar la orden (via 003).
- El despacho se bloquea si falta documento, vence o no coincide (DOC-01 §5).
- Las aplicaciones son atómicas y no exceden el saldo de origen ni destino.
- Crédito, límites y reglas de aprobación: versionados, no hardcodeados (P8).
- El motor de inventario es de 003 y el motor de aplicaciones de 004: 005 los invoca, no duplica lógica.
- La moneda de pago no altera el IVA causado por sí sola (DOC-01 §5).

## 8. Criterios de éxito (resumen)

- Una venta recorre cotización → pedido → crédito/aprobación → orden reservada.
- El picking/despacho usa el motor de 003; la salida mueve inventario y calcula el costo; el despacho se bloquea si falta/venció/no coincide.
- La factura de venta es inmutable, con líneas mixtas, base fiscal VES y tasa snapshot.
- La CxC se calcula y refleja cobros, anticipos, notas y retenciones sufridas aplicadas.
- Los cobros multimoneda son idempotentes y no sobrededucen el saldo.
- El aging de CxC permite gestionar la cartera.
- 006 (tesorería) podrá consumir los cobros de 005 para conciliación.
