# Spec 018 · plan

## Arquitectura

Módulo `app/modules/imports`. Reutiliza `Party`, `PurchaseOrder`, `Document`/`DocumentLink` (registro de recursos de la Spec 046), `AuditEvent`. No duplica proveedores, órdenes, documentos ni recepciones.

Tablas: `import_files`, `import_documents`.

## IMPORT_STATE_MACHINE_CONTRACT

| STATE | MEANING | USER_ACTION | ENTRY | EXIT | REQUIRED | DOWNSTREAM | REVERSIBLE | AUDIT_EVENT |
|---|---|---|---|---|---|---|---|---|
| NEGOTIATING | Se negocian condiciones | Completar negociación y vincular orden | Alta | ORDERED, CANCELLED | Proveedor | — | Cancelar | IMPORT_FILE_CREATED |
| ORDERED | Orden aprobada vinculada; se reúne documentación | Recibir y validar documentos | Vincular orden | DOCUMENTS_COMPLETE, CANCELLED | INCOTERM, pago, entrega y orden aprobada | Habilita documentación | Cancelar | IMPORT_ORDER_LINKED |
| DOCUMENTS_COMPLETE | Documentación validada | Ciclo 2: seguimiento y despacho | Confirmar | Ciclo 2 | Obligatorios validados | Habilita embarque | No | IMPORT_DOCUMENTS_CONFIRMED |
| CANCELLED | Cancelada | Solo consulta | Cancelar | — | Motivo | Libera la orden | No | IMPORT_FILE_CANCELLED |

Previstos, sin construir: DISPATCHED, ARRIVED, RECEIVING, RECEIVED, CLOSED.

Documento: `PENDING → RECEIVED → VALIDATED`; `RECEIVED | VALIDATED → OBSERVED → RECEIVED`.

## Permisos

Consultar `compras:view`. Crear, editar, vincular, añadir y recibir `compras:create`. Validar, observar, confirmar y cancelar `compras:approve`.
