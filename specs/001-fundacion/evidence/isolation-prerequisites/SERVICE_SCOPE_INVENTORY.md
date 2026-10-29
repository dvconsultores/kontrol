# SERVICE_SCOPE_INVENTORY — ciclo 07

Ayudantes y servicios que cargan por id, medidos por AST en `app/modules` (§21).
- «Aplica el alcance» = recibe empresa, tenant o contexto y lo compara.
- «Llamador» = confía en que el llamador ya validó el padre.

| Módulo | Función | Parámetros | Aplica el alcance | Estado tras el ciclo 07 |
|---|---|---|---|---|
| commercial/service.py | `_de_la_empresa` | db,modelo,ident,company_id,code,mensaje | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_moneda` | db,company_id,currency_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_articulo` | db,company_id,item_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_categoria` | db,company_id,category_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_presentacion` | db,company_id,presentation_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_unidad` | db,company_id,uom_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_exige_vendedor` | db,company_id,user_id | SI | aplica (empresa/tenant/contexto) |
| commercial/service.py | `_cliente_de_la_empresa` | db,company_id,customer_id | SI | aplica (empresa/tenant/contexto) |
| documents/api.py | `_get_type` | db,ctx,type_id | SI | aplica (empresa/tenant/contexto) |
| fiscal/api.py | `_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| homologation/service.py | `_owned_record` | db,record_id | NO | instalación (homologación, por diseño) |
| homologation/service.py | `_owned_release` | db,release_id | NO | instalación (homologación, por diseño) |
| identity_access/mfa_service.py | `_require_reauth` | session | NO | sin datos de empresa (utilidad) |
| identity_access/service.py | `get_user_in_tenant` | db,user_id,tenant_id | SI | aplica (empresa/tenant/contexto) |
| inventory/api.py | `_get_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| inventory/service.py | `_require_warehouse` | db,company_id,warehouse_id | SI | aplica (empresa/tenant/contexto) |
| inventory/service.py | `_require_product` | db,company_id,product_id | SI | aplica (empresa/tenant/contexto) |
| inventory/service.py | `_require_candidate_location` | db,company_id,warehouse_id,location_id | SI | aplica (empresa/tenant/contexto) |
| master_data/api.py | `_unidad_visible` | db,ctx,unit_id | SI | aplica (empresa/tenant/contexto) |
| master_data/uom_api.py | `_get_unit` | db,ctx,unit_id | SI | aplica (empresa/tenant/contexto) |
| organization/structure.py | `_load_node` | db,level,node_id | NO | carga sin alcance; el llamador `validate_chain` compara almacén y, desde el ciclo 07, empresa (G-WH-01) |
| organization/warehouse_api.py | `_get_warehouse` | db,ctx,warehouse_id | SI | aplica (empresa/tenant/contexto) |
| organization/warehouse_api.py | `_exige_sucursal_propia` | db,ctx,branch_id | SI | aplica (empresa/tenant/contexto) |
| organization/warehouse_api.py | `_exige_tipo_propio` | db,ctx,modelo,tipo_id,code,message | SI | aplica (empresa/tenant/contexto) |
| purchasing/api.py | `_owned_incident` | db,receipt_id,incident_id,company_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/api.py | `_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| purchasing/service.py | `_require_party` | db,company_id,party_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_product` | db,company_id,product_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_order` | db,company_id,order_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_quote` | db,company_id,quote_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_receipt` | db,company_id,receipt_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_return` | db,company_id,return_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_incident` | db,company_id,incident_id | SI | aplica (empresa/tenant/contexto) |
| purchasing/service.py | `_require_source` | db,company_id,source_type,source_id | SI | aplica (empresa/tenant/contexto) |
| regulatory/api.py | `_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| regulatory/service.py | `_require_authority` | db,company_id,authority_id | SI | aplica (empresa/tenant/contexto) |
| regulatory/service.py | `_required_kinds` | profiles | NO | sin datos de empresa (utilidad) |
| sales/api.py | `_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| sales/service.py | `_require_party` | db,company_id,party_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_warehouse` | db,company_id,warehouse_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_order` | db,company_id,order_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_quote` | db,company_id,quote_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_return` | db,company_id,return_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_plan` | db,company_id,plan_id,lock | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_vehicle` | db,company_id,vehicle_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_driver` | db,company_id,driver_id | SI | aplica (empresa/tenant/contexto) |
| sales/service.py | `_require_return_036` | db,company_id,return_id,lock | SI | aplica (empresa/tenant/contexto) |
| treasury/api.py | `_owned` | db,model,obj_id,tenant,code,message | SI | **fallaba abierto (G-HLP-01)** → corregido: TypeError si el modelo no tiene `company_id` |
| treasury/service.py | `_require_cashbox` | db,company_id,cashbox_id | SI | aplica (empresa/tenant/contexto) |
| treasury/service.py | `_require_account` | db,company_id,account_id | SI | aplica (empresa/tenant/contexto) |
| treasury/service.py | `_require_session` | db,company_id,session_id | SI | aplica (empresa/tenant/contexto) |
| treasury/service.py | `_require_currency` | db,company_id,currency_id | SI | aplica (empresa/tenant/contexto) |
| treasury/service.py | `_require_refund` | db,company_id,refund_id,lock | SI | aplica (empresa/tenant/contexto) |

**Servicios corregidos en el ciclo 07** (aplican ahora el alcance ellos mismos, con la empresa del documento padre):
- `inventory.record_count_line`;
- `purchasing.add_requisition_line`, `add_order_line`, `add_invoice_line`, `add_quote_line` y `confirmar_inventario` (incidencias);
- `sales.add_invoice_line`, `confirm_order` (líneas sobrantes) y `request_return` (lote y serie);
- `treasury.add_session_movement`, `_find_execution` (idempotencia por empresa) y `add_reconciliation_line`;
- `identity_access.list_roles`, `create_role`, `assign_role_to_user` (`_roles_visibles`) y `revoke_session`;
- `notifications.crear_regla`.

`SERVICE_SCOPE_INVENTORY_COMPLETE = 1`.
