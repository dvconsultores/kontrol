# SPECS DESBLOQUEADAS POR EL CIERRE DE 045 — VERIFICACIÓN

No se asume el resultado del análisis anterior: se demuestra que el contrato
transversal **ya existe en el código** y qué consume cada Spec.

## Contrato disponible

`app/modules/approvals/integration.py` expone la fachada única:

```
require_for_document(...)    solicita aprobación si la política lo exige
ensure_approved(...)         impide avanzar mientras haya solicitud viva
notify_document_changed(...) invalida solicitudes que ya no corresponden
```

Tipos de proceso registrados (catálogo extensible por datos, no por código):

```
PROCESS_PURCHASE_REQUISITION   PROCESS_PURCHASE_ORDER
PROCESS_SALES_CREDIT           PROCESS_INVENTORY_ADJUSTMENT
PROCESS_INVENTORY_COUNT        PROCESS_REGULATORY_APPROVAL
```

Eventos emitidos: `approval.requested`, `approval.step_opened`,
`approval.decided`, `approval.resolved`, `approval.obsolete`, `approval.step_expired`.

## Verificación por Spec

| Spec | Qué necesitaba de 045 | Prueba de que existe | ¿Desbloqueada? |
|---|---|---|---|
| **015** Requisiciones | Aprobación de la requisición con niveles y segregación | `PROCESS_PURCHASE_REQUISITION`; `purchasing/service.py` con 7 llamadas a la integración; `transition_requisition` consulta el motor | **Sí** |
| **017** Orden de compra | Aprobación por monto con política versionada | `PROCESS_PURCHASE_ORDER`; `transition_order` exige resolución antes de `APPROVED` | **Sí** |
| **025** Transferencias, conteos y ajustes | Segregación configurable en lugar de codificada | `PROCESS_INVENTORY_ADJUSTMENT` y `PROCESS_INVENTORY_COUNT`; `inventory/service.py` con 7 llamadas | **Sí** |
| **030** Crédito y reserva | Aprobación de crédito con niveles | `PROCESS_SALES_CREDIT`; `sales/service.py` con 4 llamadas; `CREDIT_PENDING` consulta el motor | **Sí** |
| **033** Confirmación de pedido | Motor con segregación para el segundo control | La fachada es genérica y `process_type` es dato: 033 registra el suyo sin tocar el motor (FR-045-006, verificado con `E2E_*` en las pruebas) | **Sí** |
| **047** Notificaciones y tareas | Eventos de dominio que consumir | Tabla `approval_events` con 6 tipos, verificados en `test_domain_events_are_emitted` y en E2E | **Sí** |

**Las 6 quedan desbloqueadas, demostrado por contrato en código, no por análisis.**

## Lo que 045 NO resuelve para ellas

Cada Spec conserva su propio alcance:

- **015** necesita costo estimado por línea si el negocio quiere aprobar por monto:
  `PurchaseRequisition` no lleva importe, así que su política se configura hoy
  sobre cantidad, centro de costo o solicitante.
- **025** podrá condicionar por ubicación cuando exista la Spec 008/022. El motor
  ya admite la dimensión.
- **033** debe construir la entidad de confirmación y su máquina de estados; 045
  aporta la aprobación, no el control físico.
- **047** debe construir el consumidor: 045 emite, no notifica.
