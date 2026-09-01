# MATRIZ DE CONSUMIDORES DE LA SPEC 046 — N9

Rehecha contra el maestro de Specs y contra el registro vigente, no copiada de
la versión histórica.

## 1. Estado tras N9

| Spec | Qué necesita de 046 | Contrato implementado | ¿Resuelto? | Otros impedimentos | Estado |
|---|---|---|:--:|---|---|
| **019 · Recepción física** | Evidencia y fotografía | `GoodsReceipt` registrado **y probado** | Sí | Su fase física: arribo, descarga, bultos, inspección | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **027 · Factura de proveedor** | Expediente fiscal | `SupplierInvoice` registrado **y probado** | Sí | Conciliación y flujo fiscal | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **035 · Despacho y transporte** | Guía, documentos de vehículo y conductor | `Shipment`, `TransportVehicle`, `TransportDriver` **probados** | Sí | Empaquetado físico y ruta | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **044 · SICA / SIGESAI / SACS** | Permisos y certificados | `PermitInstance`, `OfficialDocument` **probados** | Sí | Matrices oficiales por rubro sin cargar | `PARTIALLY_UNLOCKED` |
| **056 · Homologación fiscal** | Evidencia del acto formal | `HomologationRecord` **probado** | Sí | **`LEGAL_BLOCKER`**: acto formal no ejecutado | `PARTIALLY_UNLOCKED` |
| **018 · Importaciones** | Proforma, embarque, certificados | Capacidad completa; **no hay entidad que vincular** | En capacidad | Su expediente no existe | `DOCUMENT_CAPABILITY_SATISFIED` |
| **020 · Incidencias de recepción** | Foto del daño | Ídem | En capacidad | No existe entidad de incidencia | `DOCUMENT_CAPABILITY_SATISFIED` |
| **040 · Retenciones IVA e ISLR** | Comprobante de retención | Se adjunta a facturas, ambas **probadas** | Sí | **`LEGAL_BLOCKER`**: Decreto 1.808 sin conceptos | `DOCUMENT_CAPABILITY_SATISFIED` |
| **028 · Cuentas por pagar y pagos** | Comprobante de pago | **`Payment` registrado y probado** | **Sí** | Pendiente de auditoría propia | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **038 · Tesorería** | Soporte de conciliación y de caja | **`BankTransaction`, `CashSession`, `Reconciliation` registrados y probados** | **Sí** | Pendiente de auditoría propia | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |

## 2. Recuento

| Estado | Specs | Nº |
|---|---|---:|
| `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | 019, 027, 035, **028**, **038** | 5 |
| `PARTIALLY_UNLOCKED` | 044, 056 | 2 |
| `DOCUMENT_CAPABILITY_SATISFIED` | 018, 020, 040 | 3 |
| **`STILL_BLOCKED_BY_046`** | — | **0** |
| `FULLY_UNLOCKED` | — | **0** |

## 3. Por qué 028 y 038 no pasan a `FULLY_UNLOCKED`

Porque la dependencia documental resuelta no es lo mismo que la Spec terminada.
Ninguna de las dos ha pasado su propia auditoría, y declararlas desbloqueadas
sería repetir el error que `REM-046-001` corrigió: *«registré dieciséis tipos y
probé uno»* — dar por hecha una capacidad porque su prerrequisito existe.

**`FULLY_UNLOCKED` sigue en cero**, y eso es un dato honesto, no un fallo.

## 4. Corrección de la matriz histórica

`SPEC_046_FINAL_CLOSEOUT.md` §17 y `046-dependency-closeout.md` §2 declararon
desbloqueadas 019, 027, 035, 044 y 056 «con el tipo registrado y probado». El
propio `REM-046-001` corrigió la afirmación: probado estaba uno.

Ahora sí lo están los 23, y el enunciado pasa a ser cierto — pero se corrige el
texto en vez de dejar que la realidad lo alcance por su cuenta.

## 5. Números de Spec verificados

Los diez identificadores se contrastaron con el maestro de 56 Specs. Sin
desajustes.
