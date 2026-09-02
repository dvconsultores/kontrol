# SPEC — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Código | 003-inventario-logistica |
| Nombre | Inventario y logística: existencias, movimientos, lotes, seriales, reservas, transferencias, conteos, ajustes y costos |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** (org/seguridad/licencia/auditoría) + **002-maestros** (productos con perfiles de inventario/trazabilidad). La implementación de 003 requiere 001 certificada, 002 implementado y autorización expresa |
| Fuente | DOC-01 §2-5, §8; DOC-02 §3, §5, §8, §12-13; DOC-03 §5, §12-13; DOC-04 pantallas 04 y 12; DOC-08 |
| Ruta | `specs/003-inventario-logistica/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **003-inventario-logistica**.

---

## 1. Problema

Los maestros (002) dejan productos con perfiles de inventario y trazabilidad (lote, serial, vencimiento, variantes), pero no existe aún el **núcleo de inventario y logística** que da soporte físico a compras (004) y ventas (005): existencias, movimientos balanceados, lotes, seriales, ubicaciones, reservas, picking, transferencias, conteos, ajustes y costos.

Sin este módulo no es posible: conocer disponibilidad real, trazabilidad por lote/serial/vencimiento, reservar contra órdenes aprobadas, trasladar mercancía entre almacenes, conciliar existencias por conteos, ajustar con evidencia y aprobación, ni valorar el inventario (costo de venta) — todo ello exigido por los principios de la Constitución (P5 datos históricos protegidos, P8 no hardcodear, P13 integridad transaccional).

## 2. Objetivos

1. **Existencias**: balance reconstruible por producto, almacén, ubicación, lote, serial y estado, consultable con filtros y paginación.
2. **Movimientos**: motor de movimientos balanceados (`quantity != 0`), inmutables, con reverso vinculado y tipos versionados (no hardcodeados).
3. **Lotes, seriales y vencimientos**: control de caducidad (FEFO), unicidad de lote/serial/IMEI según política, historial completo.
4. **Reservas**: reservar desde órdenes aprobadas sin alterar la existencia física; liberación y expiración controladas.
5. **Transferencias**: solicitud → aprobación → picking → tránsito → recepción → diferencias, con máquina de estados.
6. **Conteos y ajustes**: conteos cíclicos/físicos con congelamiento, diferencias, aprobación y ajuste — nunca edición directa del saldo.
7. **Costos**: capas de costo (costo unitario, moneda, tasa histórica, landed cost) y valoración según perfil versionado.
8. **Integración**: API de servicios de inventario que 004/005 invocarán (recibir, reservar, liberar, salida) sin duplicar lógica.
9. Frontend con pantallas completas (existencias, kardex, transferencias, conteos, ajustes) respetando el estándar (ADR-015, DataTable sin scroll, búsqueda asíncrona).

## 3. Fuera de alcance

- **Compras** (requisición, cotización, orden, recepción con inspección completa, factura, conciliación triple, CxP) — **Spec 004**. 003 expone el servicio de movimientos que la recepción de 004 invocará.
- **Ventas** (cotización, pedido, crédito, orden, despacho con documentos regulatorios, factura, CxC) — **Spec 005**. 003 expone reserva/picking/salida que 005 invocará.
- **Tesorería** — Spec 006. **Núcleo fiscal** (IVA, retenciones, numeración, libros) — Spec 007.
- **Regulación funcional** (SICA/SIGESAI/SACS, permisos de despacho) — **Spec 008**; 003 solo registra el punto de validación previa a la salida.
- **Reportes ejecutivos/fiscales** de inventario — Spec 009.
- Valoración contable integral (asientos, costos contables formales) fuera del scope: 003 registra capas de costo de inventario.

## 4. Actores

| Actor | Uso |
|---|---|
| Almacén | Existencias, movimientos, picking, transferencias, conteos, recepción física |
| Ventas | Reservas contra órdenes aprobadas |
| Compras | Recepción que dispara entradas y lotes |
| Costos / auditor | Revisa ajustes y valoración de capas |
| Aprobador | Aprueba ajustes, transferencias y diferencias |
| Contador | Consulta valoración de inventario y costos |
| Auditor | Consulta kardex, trazabilidad y auditoría de movimientos |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-003-001 | Como almacén, quiero consultar existencias por producto/almacén/ubicación/lote/serial/estado para conocer la disponibilidad real. |
| US-003-002 | Como auditor, quiero ver el kardex (historial de movimientos) de un producto o lote para trazabilidad completa. |
| US-003-003 | Como almacén, quiero registrar lotes con fecha de vencimiento al recibir para controlar la caducidad (FEFO). |
| US-003-004 | Como usuario, quiero registrar seriales/IMEI únicos con historial para trazabilidad unitaria. |
| US-003-005 | Como ventas, quiero reservar inventario desde una orden aprobada sin alterar la existencia física. |
| US-003-006 | Como almacén, quiero ejecutar transferencias entre almacenes/ubicaciones con estados y diferencias controladas. |
| US-003-007 | Como almacén, quiero realizar conteos cíclicos/físicos con congelamiento y diferencias que deriven en ajustes aprobados. |
| US-003-008 | Como costos/auditor, quiero registrar ajustes de inventario con motivo, evidencia, costo y aprobación (nunca edición del saldo). |
| US-003-009 | Como contador, quiero valorar el inventario por capas de costo (costo unitario, moneda, landed cost) para el costo de venta. |
| US-003-010 | Como logística, quiero confirmar el picking con ubicación/lote/serial para preparar salidas. |
| US-003-011 | Como usuario, quiero que los movimientos sean balanceados e inmutables; toda corrección mediante reverso vinculado. |
| US-003-012 | Como usuario, quiero estados explícitos en lotes/seriales (disponible, reservado, tránsito, cuarentena, vencido, desecho) con transiciones autorizadas. |
| US-003-013 | Como auditor, quiero la auditoría completa de movimientos, lotes, seriales, reservas, conteos y ajustes. |

## 6. Requisitos funcionales

Convención: `FR-003-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Almacenes y ubicaciones (maestros de custodia)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-001 | `Warehouse`: custodia de inventario; tipo; políticas (permitir negativos, conteo, ubicaciones); estados permitidos. | DOC-02 §3 | P0 | Administrador |
| FR-003-002 | `Location`: pasillo, estante, zona, capacidad, restricciones y bandera de picking. | DOC-02 §3 | P0 | Administrador |
| FR-003-003 | Almacén y ubicación pertenecen a empresa/sucursal/establecimiento (multiempresa). Un almacén no se comparte entre empresas. | DOC-03 §12 | P0 | Sistema |
| FR-003-004 | Los almacenes/ubicaciones son maestros (DRAFT → ACTIVE → INACTIVE) sin eliminación física si tienen movimientos. | DOC-03 §13 | P0 | Sistema |

### 6.2 Existencias y balance

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-010 | `InventoryBalance`: proyección/cache por producto, almacén, ubicación, lote, serial y estado; **reconstruible** desde movimientos. | DOC-03 §5 | P0 | Sistema |
| FR-003-011 | Los saldos **no se editan**; se calculan desde movimientos y aplicaciones. | DOC-01 §5 | P0 | Sistema |
| FR-003-012 | Consulta de existencias con filtros (producto, almacén, ubicación, lote, serial, estado, vencimiento) y paginación. | DOC-01 §4 | P0 | Almacén |
| FR-003-013 | Disponible = existencia física − reservas (salvo política aprobada de sobreadjudicación). | DOC-02 §8, DOC-03 §12 | P0 | Sistema |

### 6.3 Movimientos

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-020 | `InventoryMovement`: empresa, almacén, ubicación, producto, tipo, cantidad, unidad, costo, referencia de documento, fecha y estado. | DOC-03 §5 | P0 | Sistema |
| FR-003-021 | Movimiento **balanceado** y `quantity != 0`. | DOC-03 §12 | P0 | Sistema |
| FR-003-022 | No existe eliminación física de movimientos de inventario; corrección mediante **reverso vinculado** (Constitución P5). | DOC-01 §5 | P0 | Sistema |
| FR-003-023 | Tipos de movimiento **versionados y configurables** (entrada, salida, tránsito, ajuste+, ajuste−, transferencia, devolución, conteo) — no hardcodeados (P8). | DOC-01 §4 | P0 | Administrador |
| FR-003-024 | Idempotencia: reintentos no duplican movimientos (`Idempotency-Key`). | DOC-01 §3 | P0 | Sistema |

### 6.4 Lotes, seriales y vencimiento

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-030 | `InventoryLot`: producto, lote, fabricación, vencimiento, proveedor, recepción y estado. | DOC-03 §5 | P0 | Sistema |
| FR-003-031 | `ProductSerial`: producto, serial, imei1/imei2/mac según aplique, lote, estado, almacén, purchase_line/sale_line, garantía. | DOC-03 §5 | P0 | Sistema |
| FR-003-032 | Lote **único** por producto/proveedor/fabricante según política; vencimiento coherente. | DOC-03 §12 | P0 | Sistema |
| FR-003-033 | Serial/IMEI **único** por tenant/producto o global según definición; historial completo. | DOC-03 §12 | P0 | Sistema |
| FR-003-034 | Política **FEFO** (primero en expirar, primero en salir) cuando el perfil de trazabilidad lo exige. | DOC-02 §5 | P1 | Sistema |
| FR-003-035 | Estados explícitos de lote/serial (DISPONIBLE, RESERVADO, TRANSITO, CUARENTENA, VENCIDO, RECHAZADO, DESECHO) con transiciones autorizadas. | DOC-02 §8 | P0 | Sistema |
| FR-003-036 | Datos críticos (lotes, seriales, vencimientos) **no** en JSON/EAV libre (estructura columnar). | DOC-01 §8 | P0 | Sistema |

### 6.5 Reservas

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-040 | `Reservation`: documento origen, producto, almacén, lote/serial, cantidad, estado y vencimiento. | DOC-03 §5 | P0 | Sistema |
| FR-003-041 | Reserva: orden aprobada → cantidad reservada → disponible reducido, **existencia física sin cambio**. | DOC-02 §8 | P0 | Sistema |
| FR-003-042 | Las reservas **no superan** el disponible salvo política aprobada. | DOC-03 §12 | P0 | Sistema |
| FR-003-043 | Liberación y expiración de reservas (cancelación de orden, vencimiento, política). | DOC-02 §8 | P1 | Sistema |

### 6.6 Picking y salida (integración con ventas 005)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-050 | `PickList`: lista → confirmación de ubicación/lote/serial → preparación. | DOC-02 §8 | P1 | Almacén |
| FR-003-051 | La confirmación de salida mueve inventario a **tránsito** o **entregado-no-facturado**. | DOC-02 §7 | P1 | Sistema |
| FR-003-052 | El picking no ampara el traslado físico; la validación regulatoria del despacho se evalúa en Spec 008 antes de la salida. | DOC-01 §5 | P1 | Sistema |

### 6.7 Transferencias

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-060 | `Transfer`: origen, destino, solicitud, envío, recepción, diferencias y estado. | DOC-03 §5 | P1 | Almacén |
| FR-003-061 | Máquina de estados: DRAFT → SUBMITTED → APPROVED → PICKING → IN_TRANSIT → PARTIALLY_RECEIVED/RECEIVED → CLOSED. | DOC-03 §13 | P1 | Sistema |
| FR-003-062 | Diferencias en recepción de transferencia con destino definido (cuarentena/ajuste) y aprobación. | DOC-02 §8 | P1 | Sistema |

### 6.8 Conteos y ajustes

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-070 | `StockCount`: plan, alcance, política de congelamiento, líneas, conteo, diferencia y aprobación. | DOC-03 §5 | P1 | Almacén |
| FR-003-071 | Flujo de conteo: plan → congelamiento/lectura → conteo → diferencias → aprobación → ajuste. | DOC-02 §8 | P1 | Almacén |
| FR-003-072 | Ajuste: motivo, evidencia, costo, aprobación y movimiento; **nunca edición directa del saldo**. | DOC-02 §8 | P0 | Sistema |
| FR-003-073 | Segregación de funciones: ajuste — crea **Almacén**, revisa **Costos/auditor**, aprueba **Aprobador**. | DOC-02 §12 | P0 | Sistema |

### 6.9 Costos

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-080 | `CostLayer`: recepción/producto/almacén, cantidad_in, cantidad_remaining, costo unitario, moneda, tasa fiscal y landed cost. | DOC-03 §5 | P0 | Sistema |
| FR-003-081 | Valoración del inventario por **capas** según método versionado del perfil (promedio ponderado o FIFO) — no hardcodeado (P8). | DOC-01 §8 | P0 | Sistema |
| FR-003-082 | El costo se registra en moneda y tasa **histórica**; decimal exacto (no se altera por revalorizaciones arbitrarias). | DOC-01 §3 | P0 | Sistema |
| FR-003-083 | El costo de salida se calcula desde las capas al momento de la salida (integración con 005). | DOC-03 §5 | P1 | Sistema |

### 6.10 Trazabilidad, kardex y auditoría

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-090 | Kardex: historial consultable de movimientos por producto/lote/serial con saldos acumulados. | DOC-01 §4 | P0 | Auditor |
| FR-003-091 | Trazabilidad origen/destino cuando el perfil lo exige (cadena de frío, garantía, FEFO). | DOC-02 §5 | P1 | Sistema |
| FR-003-092 | Auditoría completa de movimientos, lotes, seriales, reservas, conteos y ajustes. | DOC-01 §3 | P0 | Sistema |

### 6.11 Transversales (NFR)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-003-100 | Aislamiento multiempresa en todos los agregados (FK críticas confirman misma empresa). | DOC-03 §12 | P0 | Sistema |
| FR-003-101 | Concurrencia: reservas/salidas **atómicas** con bloqueo de fila y versión/ETag; sin sobreadjudicación. | DOC-03 §12, DOC-03 §14 | P0 | Sistema |
| FR-003-102 | Rendimiento: índices en (producto, almacén, lote, serial, estado); listados paginados; balance reconstruible. | DOC-03 §5 | P1 | Sistema |
| FR-003-103 | Frontend: pantallas completas (ADR-015), DataTable sin scroll horizontal, búsqueda asíncrona, estados vacíos/errores, `allowed_actions` del backend. | DOC-08, DOC-04 | P0 | Sistema |
| FR-003-104 | Los servicios de inventario son invocables por 004/005 vía API versionada; no se duplica lógica de saldos en otros módulos. | DOC-01 §1 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5)

- No existe eliminación física de movimientos de inventario (P5).
- Los saldos no se editan; se calculan desde movimientos (P5/DOC-01 §5).
- Toda corrección de movimiento es un **reverso vinculado**, no un borrado ni una edición.
- Reservas y salidas se ejecutan en transacciones atómicas con bloqueo; prohibida la sobreadjudicación sin política aprobada.
- Tipos de movimiento, métodos de costeo, políticas FEFO y estados: **versionados y configurables**, nunca hardcodeados (P8).
- Datos críticos (lotes, seriales, vencimientos, costos) en estructura columnar; prohibido JSON/EAV libre (DOC-01 §8).
- Multiempresa: un movimiento pertenece a una sola empresa; FK críticas validan la misma empresa (DOC-03 §12).

## 8. Criterios de éxito (resumen)

- Una orden aprobada reserva inventario sin cambiar la existencia física; el disponible refleja la reserva.
- Los movimientos son balanceados e inmutables; un ajuste o conteo genera movimientos con motivo, evidencia y aprobación.
- El kardex reconstruye saldos desde movimientos en cualquier momento.
- Lotes con vencimiento se consumen por FEFO cuando el perfil lo exige; vencidos se bloquean para salida.
- Las capas de costo valoran el inventario y calculan el costo de salida según el método del perfil.
- 004/005 integran mediante la API de 003 sin duplicar lógica de saldos.
- Frontend respeta el estándar (ADR-015, sin scroll horizontal, búsqueda asíncrona).

---

## Enmienda D0-03 (2026-09-02) — `ADR-D0-003` v2

| FR | Redacción anterior | Redacción vigente |
|---|---|---|
| FR-003-041 | Reserva: orden aprobada → cantidad reservada → disponible reducido, existencia física sin cambio | Reserva: pedido **confirmado** (`SUBMITTED`) → cantidad **base** reservada → disponible reducido, existencia física sin cambio. Aprobar el crédito no reserva; libera a preparación |
| FR-003-043 | Liberación y expiración de reservas (cancelación de orden, vencimiento, política) — P1 | Liberación atómica por cancelación, rechazo de crédito, reversión a borrador y expiración por TTL opcional; consumo (`FULFILLED`) en despacho — **P0 para la Spec 030** |
| FR-003-042 | Las reservas no superan el disponible salvo política aprobada | Se mantiene; la garantía pasa a ser de base de datos (`FOR UPDATE` + unicidad), no de una comprobación sin bloqueo |
| CVG-003-04 | Expiración por job pendiente | TTL opcional por empresa con defecto desactivado; ejecución por el endpoint existente; planificador de plataforma = Spec 047 |

El motor (`reserve`, `release_reservation`, `expire_reservations`, `get_available`) sigue siendo
único y de esta Spec; la Spec 030 lo consume y lo endurece.
