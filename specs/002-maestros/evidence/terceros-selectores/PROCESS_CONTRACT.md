# Matriz de elegibilidad de terceros por proceso

## Fuentes

- Spec 002 §1 y FR-002-001: una entidad común `Party` con extensiones por rol (cliente, proveedor, transportista, conductor…).
  FR-002-004 define `Customer` (ventas) y FR-002-005 `Supplier` (compras). US-002-010 pide buscar un cliente o proveedor por RIF, nombre
  o código **en un catálogo grande**.
- Nombres de campo del backend: `customer_id` en ventas y `supplier_id` en compras. `register_payment` y `register_advance` llevan
  `direction` `OUT` (CxP) o `IN` (CxC).
- La propia UI actual filtra por `CLIENTE` en órdenes y facturas de venta, y por `PROVEEDOR` en órdenes y facturas de compra. Era la intención
  del producto, aplicada solo en el cliente y sobre la primera página.
- Spec 007: las retenciones de `/fiscal/withholdings/calculate` se crean en 004 (CxP) y se practican al proveedor. Las sufridas se registran
  en 005 (`/sales/withholdings-suffered`) y vienen del cliente.
- Spec 008 FR-008-004: «Vehículos y conductores: registro con identificación, capacidad y documentos». `TransportDriver` **es** el registro
  del conductor. Ninguna fuente exige que el tercero tenga antes el rol `CONDUCTOR`.

## Matriz

| PROCESS | FIELD | REQUIRED_PARTY_ROLE | MULTIROL | ACTIVE_REQUIRED | INACTIVE_HISTORICAL_DISPLAY | SELECTION_FILTER | BACKEND_INVARIANT |
|---|---|---|---|---|---|---|---|
| Cotización, orden y factura de venta | customer_id | CLIENTE | sí | **sí** (documento originario) | sí | `role=CLIENTE&status=ACTIVE` | rol + activo + empresa |
| Nota de crédito y débito de venta | customer_id | CLIENTE | sí | no (ajusta una factura existente) | sí | `role=CLIENTE` | rol + empresa |
| Cobro (CxC) | party_id, IN | CLIENTE | sí | no (liquida deuda existente) | sí | `role=CLIENTE` | rol + empresa |
| Anticipo de cliente (CxC) | party_id, IN | CLIENTE | sí | **sí** (dinero nuevo sin obligación previa) | sí | `role=CLIENTE&status=ACTIVE` | rol + activo + empresa |
| Retención sufrida | party_id | CLIENTE | sí | no | sí | sin selector en UI | rol + empresa |
| Cotización, orden y factura de proveedor | supplier_id | PROVEEDOR | sí | **sí** | sí | `role=PROVEEDOR&status=ACTIVE` | rol + activo + empresa |
| Nota de crédito de proveedor | supplier_id | PROVEEDOR | sí | no | sí | `role=PROVEEDOR` | rol + empresa |
| Pago y programación de pagos (CxP) | party_id, OUT | PROVEEDOR | sí | no (liquida o programa deuda existente) | sí | `role=PROVEEDOR` | rol + empresa |
| Anticipo a proveedor (CxP) | party_id, OUT | PROVEEDOR | sí | **sí** | sí | `role=PROVEEDOR&status=ACTIVE` | rol + activo + empresa |
| Retención practicada (CxP y fiscal) | party_id | PROVEEDOR | sí | no | sí | `role=PROVEEDOR` | rol + empresa |
| Registro de conductor | party_id | **ninguno** | — | **sí** | sí | `status=ACTIVE` | activo + empresa |
| Propietario de vehículo | owner_party_id | ninguno | — | sí | sí | sin selector en UI | activo + empresa |
| Saldo, estado de cuenta y créditos | customer_id | — (lectura) | — | no | sí | — | empresa (sin cambio) |

## Decisiones de Claude, con su motivo

- **Activo solo en documentos originarios.** Un tercero inactivo no abre una relación nueva: no recibe cotizaciones, órdenes, facturas ni
  anticipos. Las liquidaciones y ajustes de obligaciones ya existentes (cobros, pagos, programaciones, notas y retenciones) siguen
  permitidos, porque bloquearlos impediría cobrar o pagar una deuda real y cambiaría la historia (§25 del encargo). La regla es reversible
  y coherente con la del almacén de recepciones del ciclo anterior.
- **Conductor sin rol previo.** Spec 008 hace de `TransportDriver` el propio alta del conductor. Exigir antes un rol `CONDUCTOR` añadiría un
  paso que ninguna fuente define. Se mantiene el comportamiento actual y se cierra lo que sí es un defecto: la falta de validación de
  empresa y de estado.
- **Rol en mayúsculas.** La comparación normaliza a mayúsculas, porque `POST /maestros/terceros` no normaliza los roles al crear.

`MATERIAL_OWNER_DECISION_REQUIRED = 0`: ninguna regla quedó con dos opciones igual de legítimas después de revisar las fuentes.
