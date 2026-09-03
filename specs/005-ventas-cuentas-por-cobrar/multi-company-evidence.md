# SPEC 030 — EVIDENCIA MULTIEMPRESA (ARCH-MC-001)

Cadena de toda operación: `Request → User → CompanyContext → Order under Company (_owned) →
Warehouse under Company (_require_warehouse) → permission → acción`.

| Caso | Esperado | Prueba | Resultado |
|---|---|---|---|
| Usuario A, contexto A, pedido A | opera | todas las funcionales | ✔ |
| Usuario AB, contexto A, pedido de B (`submit`, `cancel`, `revert`, `reject`, `release`) | `404` en las cinco; B intacto; bajo contexto B sí opera | `test_usuario_ab_bajo_contexto_a_no_confirma_ni_cancela_el_pedido_de_b` | ✔ |
| Cross-tenant (`uc`/T2 sobre pedido de A) | `404` | `test_cross_tenant_bloqueado` | ✔ |
| Almacén de B colado en el pedido de A (por SQL) | `404 WAREHOUSE_NOT_FOUND` al confirmar; sin reserva en B | `test_el_almacen_de_otra_empresa_no_sirve_ni_por_debajo` | ✔ |
| Cuerpo con `company_id` en `cancel` y en `PUT /settings/reservation` | `422` (cuerpo estricto); la política de B no cambia | `test_el_cuerpo_no_elige_la_empresa` | ✔ |
| Permiso ≠ empresa | `ventas:submit` en el rol no abre B bajo contexto A | mismo caso AB | ✔ |
| Auditoría con empresa y tenant correctos | `company_id = A`, `tenant_id = T1` | `test_la_auditoria_de_la_reserva_dice_quien_que_cuanto_y_por_que` | ✔ |
| Guardias estructurales existentes (rutas anidadas, cuerpo, scope) | sin regresión | `test_architecture_scope.py`, `test_n7_structure.py` | ✔ (regresión dirigida) |

`Reservation.company_id` es siempre el del pedido y el del almacén: `reserve` recibe la empresa del
pedido cargado bajo contexto y `_require_warehouse` la valida antes de bloquear nada.
