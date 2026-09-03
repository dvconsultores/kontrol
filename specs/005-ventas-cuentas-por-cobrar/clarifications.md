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

---

# CLARIFICACIONES — SPEC 030 (tras `D0-03 — CLOSED`, 2026-09-02)

| ID | Pregunta | Respuesta | Fuente |
|---|---|---|---|
| CL-030-01 | ¿Cuándo se reserva? | Al confirmar el pedido (`DRAFT → SUBMITTED`). Fijo | ADR-D0-003 v2 R-1 |
| CL-030-02 | ¿Contado y crédito difieren? | En el trigger, no. Difieren después: sin solicitud de 045 el pedido queda `RELEASED` en la misma transacción; con solicitud, `CREDIT_PENDING` | R-2 |
| CL-030-03 | ¿Qué pasa si no hay stock? | `409` por línea; nada persiste; el vendedor edita el borrador. Sin parcial, sin backorder | R-4 |
| CL-030-04 | ¿Sobreventa? | Solo `policies.allow_negative` del almacén; marcada y auditada | R-4 |
| CL-030-05 | ¿Qué cantidad? | Base con snapshot de la línea (Spec 011); se persiste también la tecleada | R-4 |
| CL-030-06 | ¿Qué almacén? | El del pedido, obligatorio; sin abastecimiento cruzado | R-5 |
| CL-030-07 | ¿Ubicación, lote, serial? | Ubicación nunca; lote/serial solo si la línea los exige; lo demás es de 031/032 | R-5, R-9 |
| CL-030-08 | ¿Cómo se modifica un pedido emitido? | `REVERT_TO_DRAFT` con motivo: libera todo, obsoleta el crédito, reemitir re-reserva | R-7 |
| CL-030-09 | ¿Cancelar libera? | Sí, atómico, desde cualquier estado vivo, con motivo | R-6 |
| CL-030-10 | ¿Rechazo de crédito? | `REJECTED` + liberación atómica | R-2, R-6 |
| CL-030-11 | ¿Expira? | Solo con `reservation_ttl_days` (defecto `NULL`) y solo mientras espera crédito; expira el pedido también. Planificador: Spec 047; 030 no hace worker | R-8 |
| CL-030-12 | ¿Liberación manual? | Solo reservas `MANUAL`, con motivo | R-6 |
| CL-030-13 | ¿Concurrencia? | `FOR UPDATE` + unicidad de saldo + índice parcial por línea + prueba de carrera | R-3 |
| CL-030-14 | ¿Idempotencia? | Máquina de estados + índice parcial; liberar dos veces no resta | R-3 |
| CL-030-15 | ¿Qué habilita 031? | `RELEASED` (renombra a `RESERVED`) | R-11 |
| CL-030-16 | ¿Despacho? | Consume → `FULFILLED` | R-6, R-9 |
| CL-030-17 | ¿Permisos? | `ventas:submit` nuevo para emitir/revertir/cancelar; `ventas:approve` para crédito | R-10 |
| CL-030-18 | ¿Histórico? | Reservas legadas `LEGACY_CREDIT_APPROVAL`, sin reinterpretar; pedidos en vuelo → revisión manual | ADR §Migración |
| CL-030-19 | ¿Configurable? | Solo TTL (empresa), sobreventa (almacén), política de crédito (045) | ADR §Configuración |
| CL-030-20 | ¿Pendiente de negocio? | Ninguno. CL-005-09 (política de crédito) es configuración de 045 y no bloquea | — |

Pendientes de esta Spec que **no** bloquean su implementación: CL-005-09, CL-005-10 (configuración
de implantación).

## Estado tras la implementación (2026-09-02)

| ID | Precisión al implementar |
|---|---|
| CL-030-21 | `CREDIT_PENDING` desaparece de la máquina: el pedido a crédito espera en `SUBMITTED` (IMP-030-025). Las filas históricas pasan a `SUBMITTED` con revisión manual (sin reserva) |
| CL-030-22 | `APPROVED` tampoco es estado: la aprobación de 045 se materializa con `POST /orders/{id}/release` (`ensure_approved`), siguiendo el patrón de compras |
| CL-030-23 | `reservation_ttl_days` vive en `companies`; `GET/PUT /sales/settings/reservation` bajo contexto |
| CL-030-24 | Las líneas capturan la unidad base al nacer (`to_base`); una línea anterior sin base la recibe al confirmar (primera captura) |
| CL-030-25 | `Reservation.quantity` = cantidad tecleada; `base_quantity` = la que compromete el saldo (misma semántica que los movimientos) |
| CL-030-26 | El endpoint de inventario `POST /reservations/expire` solo vence manuales; el de ventas `POST /orders/expire-reservations` vence las de pedido y cierra el pedido |
| CL-030-27 | No existe outbox transversal: la auditoría (`audit_events`) es la fuente de los eventos de reserva (T-030-I-029) |
| CL-030-28 | `SalesOrderLine` aún no modela lote/serial exigidos; la reserva es genérica por producto (FR-030-018 queda satisfecho por ausencia; cuando 024 añada el dato, la reserva lo transportará) |
