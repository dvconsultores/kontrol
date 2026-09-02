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

---

# SPEC 029 — REQUISITOS DE ORIGEN COMERCIAL

Añadidos en el ciclo de implementación de la Spec 029, posterior a la Spec 012.

## Captura temprana (`P23`)

| Id | Requisito | Prioridad |
|---|---|---|
| FR-029-017 | El precio se obtiene de la autoridad comercial de la Spec 012 | P0 |
| FR-029-018 | 029 **no** crea un segundo resolutor de precio | P0 |
| FR-029-019..022 | La línea guarda versión, ítem, origen y política del descuento | P0 |
| FR-029-023 | La unidad y la presentación se conservan como en la Spec 011 | P0 |
| FR-029-024 | 029 **no** redefine la conversión física | P0 |
| FR-029-031/032 | Todo importe en `Numeric`; jamás `float` | P0 |
| FR-029-060 | El histórico no consulta maestros actuales para reconstruirse | P0 |

## Invariancia histórica

| Id | Requisito | Prioridad |
|---|---|---|
| FR-029-025/026 | Cotización y pedido no se recalculan con maestros nuevos | P0 |
| FR-029-027 | La conversión preserva la evidencia comercial | P0 |
| FR-029-028 | La conversión **no** vuelve a resolver el precio | P0 |
| FR-029-029 | Un cambio manual es acción auditable, con motivo | P0 |

## Ciclo y conversión

| Id | Requisito | Prioridad |
|---|---|---|
| FR-029-041 | La vigencia se comprueba al enviar, aceptar y convertir | P0 |
| FR-029-042 | Una cotización vencida no se convierte | P0 |
| FR-029-043 | La conversión está protegida contra doble conversión | P0 |
| FR-029-044 | Una cotización produce **un** pedido | P0 |
| FR-029-046 | El pedido conserva el vínculo con su cotización | P0 |
| FR-029-047 | Un pedido directo resuelve con la misma autoridad y captura origen | P0 |

## Frontera con la Spec 030

| Id | Requisito | Prioridad |
|---|---|---|
| FR-029-035 | 029 **no** implementa reserva | P0 |
| FR-029-036 | 029 **no** decide `D0-03` | P0 |
| FR-029-037 | 029 **no** implementa crédito | P0 |
| FR-029-038..040 | 029 **no** hace picking, ni factura, ni despacha | P0 |

## Multiempresa

| Id | Requisito | Prioridad |
|---|---|---|
| FR-029-001..005 | Empresa real; el contexto es la autoridad; ni el cuerpo ni la URL lo son | P0 |
| FR-029-008..010 | Las líneas derivan su empresa y no la duplican | P0 |
| FR-029-011..016 | Las rutas hijas validan el padre; entre empresas y tenants, bloqueado | P0 |
| FR-029-053 | Tener permiso no es tener acceso a una empresa | P0 |

---

# SPEC 030 — CRÉDITO / APROBACIÓN / RESERVA · CONTRATO DOCUMENTAL

| Campo | Valor |
|---|---|
| Estado | `READY_FOR_IMPLEMENTATION` (2026-09-02) — **no implementada**; requiere autorización expresa |
| Origen del contrato | `D0-03 — CLOSED` · `ADR-D0-003` v2 (ACTIVE) · `POL-D0-002` v2 · `docs/governance/d0-foundational-decisions/d0-03-checkpoint/` |
| Depende de | 011 ✔ · 012 ✔ · 023/003 ✔ (motor de reservas) · 029 ✔ · 045 ✔ |
| Enmienda | FR-005-011 y FR-005-020 de esta Spec; FR-003-041 y FR-003-043 de la Spec 003 |

## Disparador y máquina de estados

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-001 | `RESERVATION TRIGGER = ORDER_CONFIRMATION`: la reserva nace en `DRAFT → SUBMITTED`, síncrona, en la misma transacción. Fija; no configurable | P0 |
| FR-030-002 | Máquina de estados (sustituye a FR-005-011): `DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RELEASED → PREPARING → SHIPPED → CLOSED`; terminales `CANCELLED`, `REJECTED`, `EXPIRED`; `REVERT_TO_DRAFT` desde `SUBMITTED/CREDIT_PENDING/APPROVED/RELEASED`; `CANCELLED` desde cualquier estado vivo. `RELEASED` renombra al actual `RESERVED` | P0 |
| FR-030-003 | `APPROVED` no reserva (sustituye a FR-005-020). Aprobar libera a preparación: `APPROVED → RELEASED` en la misma transacción; sin política de crédito, `SUBMITTED → APPROVED → RELEASED` en la transacción de confirmación | P0 |
| FR-030-004 | Pedido sin solicitud de crédito (045 no abre) reserva y queda `RELEASED` al confirmar | P0 |
| FR-030-005 | Crédito vía motor 045 (`SALES_CREDIT`); ningún estado ni motor de aprobación propio | P0 |
| FR-030-006 | La aprobación no toca la reserva salvo `expires_at := NULL` | P0 |
| FR-030-007 | Rechazo de crédito → `REJECTED` y liberación de toda la reserva en la misma transacción | P0 |

## Cantidad, insuficiencia, sobreventa

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-010 | Insuficiencia en cualquier línea → `409 INSUFFICIENT_AVAILABLE` con detalle `{line_id, requested_base, available_base}`; nada persiste; el pedido sigue `DRAFT`. Excepción: almacén con `policies.allow_negative = true` → reserva íntegra marcada `oversell = true` | P0 |
| FR-030-011 | Sin reserva parcial: todo-o-nada por pedido | P0 |
| FR-030-012 | Backorder, sustitución y prioridad entre pedidos: **OUT_OF_SCOPE**; prohibido introducir estados o colas que los insinúen | P0 |
| FR-030-013 | `warehouse_id` obligatorio para confirmar con líneas de inventario → `422 WAREHOUSE_REQUIRED`; almacén de la empresa del pedido → `404` si no | P0 |
| FR-030-014 | Un almacén por pedido; sin abastecimiento automático desde otro almacén | P0 |
| FR-030-015 | Reserva y comparación en **cantidad base** de la línea (Spec 011); la reserva copia `quantity`, `uom_id`, `presentation_id`, `conversion_factor_snapshot`, `base_quantity`, `uom_source`; sin base → `422 UOM_NOT_RESOLVED` | P0 |
| FR-030-016 | La reserva nunca recalcula con el factor vigente del catálogo | P0 |
| FR-030-017 | Solo consume saldo `DISPONIBLE`; no cambia el estado de custodia | P0 |
| FR-030-018 | Lote/serial en la reserva solo si la línea los exige; ubicación nunca | P0 |

## Modificación, cancelación, expiración, liberación

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-020 | Pedido editable solo en `DRAFT`; `add_order_line` sobre otro estado → `409 ORDER_NOT_EDITABLE` | P0 |
| FR-030-021 | `REVERT_TO_DRAFT` con motivo: libera toda la reserva y declara obsoleta la solicitud de crédito (045 `document_changed`); reemitir vuelve a reservar con la disponibilidad actual | P0 |
| FR-030-022 | Sin ajuste por diferencias (aumento, disminución, línea, producto, almacén: todo por reversión) | P0 |
| FR-030-023 | Cancelar libera todo lo `ACTIVE` en la misma transacción, con motivo; idempotente; en `PREPARING`, 032 deshace lo apartado | P0 |
| FR-030-024 | `reservation_ttl_days` por empresa, defecto `NULL`; con valor, `expires_at` solo en `SUBMITTED/CREDIT_PENDING` | P1 |
| FR-030-025 | Expirar → reserva `EXPIRED` y pedido `EXPIRED` en la misma transacción; el endpoint de expiración existente se hace consciente del pedido; sin worker propio (planificador = Spec 047) | P1 |
| FR-030-026 | Invariante: nunca un pedido vivo sin reserva | P0 |
| FR-030-027 | Liberación manual solo de reservas `MANUAL`, con `inventario:reserve`, motivo obligatorio y auditoría; reservas de pedido no se liberan a mano | P0 |

## Multiempresa y permisos

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-030 | La empresa de la reserva es la del pedido bajo `CompanyContext` y coincide con la del almacén | P0 |
| FR-030-031 | Pedido de otra empresa → `404` | P0 |
| FR-030-032 | Usuario AB, contexto A, pedido de B → `404` | P0 |
| FR-030-033 | Cross-tenant → `404` | P0 |
| FR-030-034 | Almacén de B bajo pedido A → `404 WAREHOUSE_NOT_FOUND` | P0 |
| FR-030-035 | Permiso `ventas:submit` (nuevo) para confirmar/revertir/cancelar; `ventas:approve` para crédito; la reserva es efecto del sistema; ningún permiso sustituye al contexto | P0 |

## Concurrencia e idempotencia

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-040 | `SELECT … FOR UPDATE` sobre la fila de saldo antes de leer el disponible, dentro de la transacción de confirmación; bloqueos en orden determinista por producto | P0 |
| FR-030-041 | Unicidad sobre la clave de `inventory_balances` (con `COALESCE` en dimensiones nulas), en ORM (`ddl_if postgresql`) y migración; `CHECK (qty_reserved >= 0)` | P0 |
| FR-030-042 | Índice único parcial `(source_line_id) WHERE status = 'ACTIVE'` en `reservations` | P0 |
| FR-030-043 | Liberar/expirar/consumir dos veces es no-op; `qty_reserved` nunca negativo | P0 |
| FR-030-044 | Prueba de carrera sobre PostgreSQL: dos sesiones, última unidad, exactamente una gana; segunda variante con `allow_negative` | P0 |

## Handoff y fronteras

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-050 | `RELEASED` habilita la cola de 031; se entregan pedido, almacén, líneas con base/presentación/lote-serial exigidos y reservas `ACTIVE` por `source_line_id` | P0 |
| FR-030-051 | 030 no crea `PickList`, no asigna ubicación, no elige lote/serial | P0 |
| FR-030-052 | 030 no escribe estados de custodia (`RESERVADO`, `PICKING`) | P0 |
| FR-030-053 | La facturación no toca la reserva | P0 |
| FR-030-054 | El despacho (035) consume → `FULFILLED`, no `RELEASED` | P0 |

## Auditoría y modelo

| Id | Requisito | Prioridad |
|---|---|---|
| FR-030-060 | Eventos `RESERVATION_CREATED / RELEASED / EXPIRED / FULFILLED` en el módulo de inventario con el contrato de `d0-03-reservation-decision.md` §7 | P0 |
| FR-030-061 | `SALES_ORDER_TRANSITIONED` y `SALES_ORDER_REVERTED` llevan motivo cuando lo hay | P0 |
| FR-030-062 | `reservations` gana `source_type`, `source_id`, `source_line_id`, `trigger` (`ORDER_CONFIRMATION`/`MANUAL`/`LEGACY_CREDIT_APPROVAL`), `oversell`, `released_at`, `released_by`, `release_reason`; `source_document` texto se conserva | P0 |
| FR-030-063 | Migración `SAFE_MIGRATION` (columnas, backfill, rename de estado) + `MANUAL_REVIEW_REQUIRED` (pedidos en `SUBMITTED/CREDIT_PENDING` sin reserva); las reservas legadas conservan su semántica | P0 |

## Frontera con 029 (preservada)

FR-029-035..040 siguen vigentes: la conversión de cotización no reserva; 030 reserva **después**, al confirmar.

## Criterios de aceptación y pruebas exigidas

Los trece criterios de `ADR-D0-003` v2 §«Implicaciones de prueba», sobre PostgreSQL, más: la
regresión completa sin retroceso; `test_convertir_no_reserva_inventario` sigue verde; el guardia de
rutas anidadas y el contrato `__scope__` sin cambios.
