# Spec 018 · plan

## Arquitectura

Módulo `app/modules/imports`. Reutiliza `Party`, `PurchaseOrder`, `Document`/`DocumentLink` (registro de recursos de la Spec 046), `AuditEvent`. No duplica proveedores, órdenes, documentos ni recepciones.

Tablas: `import_files`, `import_documents`, `import_tracking_events`, `import_corrections`, `import_financial_links`.

## IMPORT_STATE_MACHINE_CONTRACT

La secuencia del sponsor está en `SPONSOR_IMPORT_PROCESS_SEQUENCE.md`. Esta máquina es de ingeniería: **el sponsor no define estados de importación**.

| STATE | Origen | MEANING | USER_ACTION | ENTRY | EXIT | REQUIRED | DOWNSTREAM | REVERSIBLE | AUDIT_EVENT |
|---|---|---|---|---|---|---|---|---|---|
| NEGOTIATING | DERIVED (de IMP-06) | Se negocian condiciones | Completar y vincular orden | Alta | ORDERED, CANCELLED | Proveedor | — | Cancelar | IMPORT_FILE_CREATED |
| ORDERED | DERIVED (de IMP-07) | Orden aprobada; se reúne documentación, se paga y se sigue el embarque | Documentos, pagos, seguimiento, correcciones | Vincular orden | DOCUMENTS_COMPLETE, CANCELLED | INCOTERM, pago, entrega y orden aprobada | — | Cancelar | IMPORT_ORDER_LINKED |
| DOCUMENTS_COMPLETE | DERIVED (mitad documental de IMP-11) | Documentación validada | Registrar salida y confirmar despacho | Confirmar | DISPATCHED, ORDERED, CANCELLED | Obligatorios validados y sin correcciones abiertas | Habilita despacho | Una observación o corrección la devuelve a ORDERED | IMPORT_DOCUMENTS_CONFIRMED |
| DISPATCHED | DERIVED (mitad física de IMP-11) | Mercancía despachada | Seguimiento y correcciones; ciclo 3: arribo | Confirmar despacho | Ciclo 3 | Documentación completa y fecha de salida real | Prepara recepción | No | IMPORT_DISPATCH_CONFIRMED |
| CANCELLED | DERIVED (patrón Volumen 3, sin mención en el DOCX) | Cancelada | Consulta | Cancelar | — | Motivo | Libera la orden | No | IMPORT_FILE_CANCELLED |

Todos los estados son `DERIVED_IMPLEMENTATION_DECISION`: representan pasos del sponsor pero sus nombres y separación los decidió ingeniería. Previstos, sin construir: ARRIVED, RECEIVING, RECEIVED, CLOSED.

**Corrección respecto al ciclo 1:** se quitó la implicación de que el seguimiento y el pago esperan a la documentación. Documentos, pagos y seguimiento conviven desde ORDERED. Una observación o corrección posterior a DOCUMENTS_COMPLETE devuelve a ORDERED; tras DISPATCHED no se revierte el hecho físico.

Documento: `PENDING → RECEIVED → VALIDATED`; `RECEIVED | VALIDATED → OBSERVED → RECEIVED`. Corrección: `OPEN → RESOLVED | CANCELLED`.

## Finanzas (IMP-09)

El dinero vive solo en CxP. El expediente guarda un vínculo a `Payment` o `Advance` existentes y lee de allí monto, moneda, estado y fecha. Registrar desde el expediente llama a los servicios de CxP, con su puerta de proveedor aprobado. La aprobación y ejecución siguen en CxP.

## Agente (IMP-12)

Sin rol nuevo. `agent_party_id` apunta a un `Party` activo de la empresa. Transportista: `Party` con rol TRANSPORTISTA.

## Correcciones (IMP-12)

Spec 020 no sirve antes del arribo: `ReceiptIncident.receipt_id` es obligatorio. Se añade `import_corrections`, sin tratamiento ni efecto sobre inventario. Responsable, literal de la fuente: PROVEEDOR, AGENTE o IMPORTACION. Tipos: FALTANTE y CORRECCION_DOCUMENTAL. Evidencia con la Spec 046.

## Permisos

Consultar `compras:view`. Crear, editar, vincular, añadir y recibir `compras:create`. Validar, observar, confirmar y cancelar `compras:approve`.
Registrar pago o anticipo y vincular: `compras:create`. Confirmar despacho y anular corrección: `compras:approve`.

## Ciclo 3

Sin tablas ni migración. `DISPATCHED` sigue siendo el último estado guardado. La continuidad la da `_logistics_detail`, y `next_action` depende de su etapa. Escrituras: una ruta propia, `POST /importaciones/{id}/receipts`; arribo y put-away van a sus dueñas, y lo demás se opera en las pantallas de 019, 020 y 021 con contexto de vuelta.

