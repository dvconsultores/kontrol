# allowed_actions de Party

Listado: cálculo ligero, solo por estado (`view`, `edit`, `activate`, `deactivate`, `audit`). Detalle: añade las acciones que dependen de relaciones (`delete`, `approve`, `reject`, `resubmit`) y `blocking_documents`.

| Acción | Verdadera cuando | Backend | Frontend | Permiso | Requisito |
|---|---|---|---|---|---|
| view | siempre | GET /terceros/{id} | Detalle | maestros:view | FR-002-001 |
| edit | ACTIVE | PATCH /terceros/{id} | Editar | maestros:edit | FR-002-001 |
| activate | INACTIVE | POST .../activate | Detalle | maestros:edit | FR-002-044 |
| deactivate | ACTIVE; en detalle, además sin documentos activos | POST .../deactivate | Detalle | maestros:deactivate | FR-002-044, EDGE-002-02 |
| delete | solo detalle: sin relaciones | DELETE /terceros/{id} | Detalle | maestros:deactivate (`maestros:delete` no existe en el catálogo de permisos) | FR-002-044 |
| approve | solo detalle: PROVEEDOR en PENDING_APPROVAL | POST .../roles/PROVEEDOR/approve | Detalle | compras:approve | US-002-011 |
| reject | solo detalle: PROVEEDOR en PENDING_APPROVAL o APPROVED | POST .../roles/PROVEEDOR/reject | Detalle | compras:approve | CL-002-08 |
| resubmit | solo detalle: PROVEEDOR en REJECTED | POST .../roles/PROVEEDOR/resubmit | Detalle | maestros:edit | CL-002-08 |
| audit | siempre | GET .../audit | Timeline | audit:view | FR-002-045 |

`ALLOWED_ACTIONS_WITHOUT_REAL_OPERATION = 0`.

## Aprobación de proveedor

Aprobar exige: tercero ACTIVE, RIF, y al menos una cuenta bancaria vigente **verificada** (aprobación bancaria y fiscal, DOC-04 pantalla 08). Si falta algo: 409 `SUPPLIER_APPROVAL_PRECONDITION` con `details.missing`. Crear o cambiar una cuenta quita su verificación y, si el proveedor estaba APPROVED, lo devuelve a PENDING_APPROVAL: cambiar los datos bancarios de un proveedor aprobado no puede conservar la aprobación.

Puerta de pago (EDGE-002-11): `register_payment`, `register_advance` y `transition_payment` a APPROVED o POSTED con `direction=OUT` exigen `Supplier.approval_status == APPROVED`: 409 `SUPPLIER_NOT_APPROVED`. Sin fila de `Supplier`, no está aprobado. La programación de pagos (`create_schedule`) no mueve dinero y no se bloquea.

Bloqueo de cliente (FR-002-004): `Customer.blocked` rechaza documentos originarios de venta con 409 `CUSTOMER_BLOCKED`. Cobros y notas siguen permitidos.
