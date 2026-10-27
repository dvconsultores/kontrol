# READ_AUTHORIZATION_SURFACE_MATRIX (generada desde la aplicación en fb8ead1; 227 GET)

Generador de Claude fuera del árbol: recorre `app.routes` y cada árbol de dependencias; la clase y la capacidad final salen del diseño del delta (AD-1..AD-6). Columnas omitidas por ser constantes: TENANT_SCOPED = sí en todas (el usuario y la empresa son del tenant autenticado); TEST_REQUIRED = la puerta de completitud (T02) para todas, más RPE-01..12 para las representativas.

| # | Módulo | GET | Alcance | Clase | Capacidad declarada (final) | Cambio |
|---|---|---|---|---|---|---|
| R001 | app | / | GLOBAL | PUBLIC_REFERENCE_DATA | — (raíz técnica sin datos) | NO (clasificada) |
| R002 | approvals | /approvals/delegations | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R003 | approvals | /approvals/inbox | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:approve | NO (ya declarada) |
| R004 | approvals | /approvals/policies | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R005 | approvals | /approvals/policies/{policy_id} | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R006 | approvals | /approvals/process-types | GLOBAL | GLOBAL_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R007 | approvals | /approvals/requests | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R008 | approvals | /approvals/requests/by-document | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R009 | approvals | /approvals/requests/{request_id} | COMPANY | COMPANY_PROTECTED_DATA | aprobaciones:view | NO (ya declarada) |
| R010 | audit | /audit/events | GLOBAL | GLOBAL_PROTECTED_DATA | audit:view | NO (ya declarada) |
| R011 | commercial | /comercial/canales | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R012 | commercial | /comercial/condiciones-pago | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R013 | commercial | /comercial/listas-precio | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R014 | commercial | /comercial/listas-precio/{price_list_id} | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R015 | commercial | /comercial/listas-precio/{price_list_id}/versiones/{version_id}/items | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R016 | commercial | /comercial/politicas-credito | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R017 | commercial | /comercial/politicas-descuento | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R018 | commercial | /comercial/precedencia | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R019 | commercial | /comercial/zonas | COMPANY | COMPANY_PROTECTED_DATA | comercial:view | NO (ya declarada) |
| R020 | documents | /documentos | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R021 | documents | /documentos/categorias | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R022 | documents | /documentos/por-recurso/{resource_type}/{resource_id} | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R023 | documents | /documentos/salud/almacenamiento | GLOBAL | GLOBAL_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R024 | documents | /documentos/tipos | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R025 | documents | /documentos/{document_id} | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R026 | documents | /documentos/{document_id}/descargar | COMPANY | COMPANY_PROTECTED_DATA | documentos:download | NO (ya declarada) |
| R027 | documents | /documentos/{document_id}/preview | COMPANY | COMPANY_PROTECTED_DATA | documentos:download | NO (ya declarada) |
| R028 | documents | /documentos/{document_id}/versiones | COMPANY | COMPANY_PROTECTED_DATA | documentos:view | NO (ya declarada) |
| R029 | documents | /documentos/{document_id}/versiones/{version_id}/descargar | COMPANY | COMPANY_PROTECTED_DATA | documentos:download | NO (ya declarada) |
| R030 | fiscal | /fiscal/books/{tax_type} | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R031 | fiscal | /fiscal/control-batches | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R032 | fiscal | /fiscal/control-numbers | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R033 | fiscal | /fiscal/credit-debit-notes | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R034 | fiscal | /fiscal/documents | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R035 | fiscal | /fiscal/documents/{document_id} | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R036 | fiscal | /fiscal/legal-sources | GLOBAL | GLOBAL_PROTECTED_DATA | fiscal:view | SÍ |
| R037 | fiscal | /fiscal/number-series | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R038 | fiscal | /fiscal/periods | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R039 | fiscal | /fiscal/tax-calculations | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R040 | fiscal | /fiscal/tax-return-batches | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R041 | fiscal | /fiscal/tax-rule-versions | GLOBAL | GLOBAL_PROTECTED_DATA | fiscal:view | SÍ |
| R042 | fiscal | /fiscal/withholding-rules | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R043 | fiscal | /fiscal/withholdings | COMPANY | COMPANY_PROTECTED_DATA | fiscal:view | SÍ |
| R044 | homologation | /homologation/records | GLOBAL | GLOBAL_PROTECTED_DATA | homologacion:view | SÍ |
| R045 | homologation | /homologation/records/{record_id} | GLOBAL | GLOBAL_PROTECTED_DATA | homologacion:view | SÍ |
| R046 | homologation | /homologation/releases | GLOBAL | GLOBAL_PROTECTED_DATA | homologacion:view | SÍ |
| R047 | homologation | /homologation/timeline | GLOBAL | GLOBAL_PROTECTED_DATA | homologacion:view | SÍ |
| R048 | identity_access | /auth/me | GLOBAL | SELF_SCOPED_DATA | — (identidad y autoridad propias) | NO (clasificada) |
| R049 | identity_access | /auth/mfa | GLOBAL | SELF_SCOPED_DATA | — (estado MFA propio) | NO (clasificada) |
| R050 | identity_access | /auth/operations | GLOBAL | AUTHENTICATED_GLOBAL_REFERENCE_DATA | — (metadato de la API, igual para todos (ADR-018)) | NO (clasificada) |
| R051 | identity_access | /auth/sessions | GLOBAL | SELF_SCOPED_DATA | — (sesiones propias) | NO (clasificada) |
| R052 | identity_access | /authority/company | COMPANY | SELF_SCOPED_DATA | — (autoridad propia en la empresa activa (ADR-018)) | NO (clasificada) |
| R053 | identity_access | /roles | GLOBAL | GLOBAL_PROTECTED_DATA | roles:view | NO (ya declarada) |
| R054 | identity_access | /users | GLOBAL | GLOBAL_PROTECTED_DATA | users:view | NO (ya declarada) |
| R055 | inventory | /inventory/adjustments | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R056 | inventory | /inventory/balances | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R057 | inventory | /inventory/balances/{balance_id} | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R058 | inventory | /inventory/cost-layers | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R059 | inventory | /inventory/costing-profiles | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R060 | inventory | /inventory/counts | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R061 | inventory | /inventory/lots | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R062 | inventory | /inventory/movement-types | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R063 | inventory | /inventory/movements | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R064 | inventory | /inventory/movements/{movement_id} | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R065 | inventory | /inventory/putaway/pendientes | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R066 | inventory | /inventory/putaway/ubicaciones | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R067 | inventory | /inventory/reservations | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R068 | inventory | /inventory/serials | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R069 | inventory | /inventory/transfers | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R070 | inventory | /inventory/valuation | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R071 | licensing | /license/detail | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R072 | licensing | /license/history | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R073 | licensing | /license/installation-request | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R074 | licensing | /license/status | GLOBAL | PUBLIC_REFERENCE_DATA | — (modo de licencia, necesario antes de iniciar sesión (FR-001-052)) | NO (clasificada) |
| R075 | licensing | /licensing/central-config | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R076 | licensing | /licensing/entitlement-snapshots | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R077 | licensing | /licensing/entitlements | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R078 | licensing | /licensing/offline-status | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R079 | licensing | /licensing/overview | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R080 | licensing | /licensing/renewal-requests | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R081 | licensing | /licensing/sync-runs | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R082 | master_data | /maestros/catalogos/atributos | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R083 | master_data | /maestros/catalogos/items | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R084 | master_data | /maestros/catalogos/items/search | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R085 | master_data | /maestros/catalogos/items/{item_id} | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R086 | master_data | /maestros/catalogos/taxonomia | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R087 | master_data | /maestros/catalogos/unidades | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R088 | master_data | /maestros/perfiles | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R089 | master_data | /maestros/presentaciones/{presentation_id} | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R090 | master_data | /maestros/presentaciones/{presentation_id}/versiones | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R091 | master_data | /maestros/productos/{product_id}/presentaciones | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R092 | master_data | /maestros/terceros | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R093 | master_data | /maestros/terceros/{party_id} | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | SÍ |
| R094 | master_data | /maestros/unidades | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R095 | master_data | /maestros/unidades/{unit_id} | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R096 | master_data | /maestros/unidades/{unit_id}/conversiones | COMPANY | COMPANY_PROTECTED_DATA | maestros:view | NO (ya declarada) |
| R097 | notifications | /alerts | COMPANY | COMPANY_PROTECTED_DATA | alertas:view | NO (ya declarada) |
| R098 | notifications | /notifications | COMPANY | SELF_SCOPED_DATA | — (fila de destinatario + tipos prohibidos por capacidad (CL-047-05)) | NO (clasificada) |
| R099 | notifications | /notifications/counts | COMPANY | SELF_SCOPED_DATA | — (contadores propios (CL-047-05)) | NO (clasificada) |
| R100 | notifications | /notifications/preferences | COMPANY | SELF_SCOPED_DATA | — (preferencias propias (CL-047-05)) | NO (clasificada) |
| R101 | notifications | /notifications/rules | COMPANY | COMPANY_PROTECTED_DATA | notificaciones:configure | NO (ya declarada) |
| R102 | notifications | /notifications/sources | COMPANY | COMPANY_PROTECTED_DATA | notificaciones:configure | NO (ya declarada) |
| R103 | notifications | /notifications/{notification_id} | COMPANY | SELF_SCOPED_DATA | — (fila de destinatario (CL-047-05)) | NO (clasificada) |
| R104 | notifications | /tasks | COMPANY | SELF_SCOPED_DATA | — (candidato/asignado; scope=all exige tareas:view (CL-047-05)) | NO (clasificada) |
| R105 | notifications | /tasks/priorities | COMPANY | COMPANY_REFERENCE_DATA | — (catálogo de prioridades que necesita todo participante de una tarea) | NO (clasificada) |
| R106 | notifications | /tasks/{task_id} | COMPANY | SELF_SCOPED_DATA | — (candidato/asignado o tareas:view (CL-047-05)) | NO (clasificada) |
| R107 | organization | /organization/aisles/{node_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R108 | organization | /organization/branches | COMPANY | COMPANY_PROTECTED_DATA | organization:view | SÍ |
| R109 | organization | /organization/companies | GLOBAL | SELF_SCOPED_DATA | — (empresas a las que el usuario accede: autoridad del selector (regla 5)) | NO (clasificada) |
| R110 | organization | /organization/establishments | COMPANY | COMPANY_PROTECTED_DATA | organization:view | SÍ |
| R111 | organization | /organization/levels/{node_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R112 | organization | /organization/location-types | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R113 | organization | /organization/locations | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R114 | organization | /organization/locations/ordered | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R115 | organization | /organization/locations/{location_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R116 | organization | /organization/racks/{node_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R117 | organization | /organization/warehouses | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R118 | organization | /organization/warehouses/{warehouse_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R119 | organization | /organization/warehouses/{warehouse_id}/aisles | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R120 | organization | /organization/warehouses/{warehouse_id}/levels | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R121 | organization | /organization/warehouses/{warehouse_id}/racks | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R122 | organization | /organization/warehouses/{warehouse_id}/structure | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R123 | organization | /organization/warehouses/{warehouse_id}/zones | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R124 | organization | /organization/zone-types | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R125 | organization | /organization/zones/{node_id} | COMPANY | COMPANY_PROTECTED_DATA | organization:view | NO (ya declarada) |
| R126 | purchasing | /purchasing/aging | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R127 | purchasing | /purchasing/credit-notes | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R128 | purchasing | /purchasing/incidencias | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R129 | purchasing | /purchasing/open-items | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R130 | purchasing | /purchasing/orders | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R131 | purchasing | /purchasing/orders/{order_id} | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R132 | purchasing | /purchasing/payments | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R133 | purchasing | /purchasing/quotes | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R134 | purchasing | /purchasing/receipts | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R135 | purchasing | /purchasing/receipts/{receipt_id} | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R136 | purchasing | /purchasing/receipts/{receipt_id}/conciliacion | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R137 | purchasing | /purchasing/receipts/{receipt_id}/confirmacion-inventario | COMPANY | COMPANY_PROTECTED_DATA | inventario:view | SÍ |
| R138 | purchasing | /purchasing/receipts/{receipt_id}/incidencias | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R139 | purchasing | /purchasing/receipts/{receipt_id}/incidencias/resultado | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R140 | purchasing | /purchasing/receipts/{receipt_id}/incidencias/{incident_id} | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R141 | purchasing | /purchasing/requisitions | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R142 | purchasing | /purchasing/returns | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R143 | purchasing | /purchasing/supplier-invoices | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R144 | purchasing | /purchasing/supplier-invoices/{invoice_id} | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R145 | purchasing | /purchasing/triple-match | COMPANY | COMPANY_PROTECTED_DATA | compras:view | SÍ |
| R146 | regulatory | /regulatory/approval-requests | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R147 | regulatory | /regulatory/authorities | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R148 | regulatory | /regulatory/contingencies | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R149 | regulatory | /regulatory/drivers | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R150 | regulatory | /regulatory/evaluations | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R151 | regulatory | /regulatory/official-documents | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R152 | regulatory | /regulatory/official-registrations | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R153 | regulatory | /regulatory/permit-types | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R154 | regulatory | /regulatory/permits | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R155 | regulatory | /regulatory/profiles | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R156 | regulatory | /regulatory/vehicles | COMPANY | COMPANY_PROTECTED_DATA | regulatorio:view | SÍ |
| R157 | reporting | /reporting/audit/timeline | COMPANY | COMPANY_PROTECTED_DATA | audit:view | SÍ |
| R158 | reporting | /reporting/dashboard | COMPANY | COMPANY_PROTECTED_DATA | dashboard:view + capacidad de cada indicador | SÍ |
| R159 | reporting | /reporting/exports | COMPANY | COMPANY_PROTECTED_DATA | reportes:view | SÍ |
| R160 | reporting | /reporting/exports/{export_id}/download | COMPANY | COMPANY_PROTECTED_DATA | reportes:export + capacidad del reporte | SÍ |
| R161 | reporting | /reporting/jobs | COMPANY | COMPANY_PROTECTED_DATA | reportes:view | SÍ |
| R162 | reporting | /reporting/jobs/{job_id} | COMPANY | COMPANY_PROTECTED_DATA | reportes:view | SÍ |
| R163 | reporting | /reporting/reports/{key} | COMPANY | COMPANY_PROTECTED_DATA | reportes:view + capacidad del reporte | SÍ |
| R164 | sales | /sales/aging | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R165 | sales | /sales/collections | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R166 | sales | /sales/confirmacion/pendientes | COMPANY | COMPANY_PROTECTED_DATA | ventas:quality | NO (ya declarada) |
| R167 | sales | /sales/confirmacion/{order_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:quality | NO (ya declarada) |
| R168 | sales | /sales/confirmacion/{order_id}/facturable | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R169 | sales | /sales/credit-notes | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R170 | sales | /sales/cxc/clientes/{customer_id}/creditos | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R171 | sales | /sales/cxc/clientes/{customer_id}/estado-de-cuenta | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R172 | sales | /sales/cxc/clientes/{customer_id}/saldo | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R173 | sales | /sales/cxc/documentos/{open_item_id}/aplicaciones | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R174 | sales | /sales/debit-notes | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R175 | sales | /sales/despacho/pendientes | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R176 | sales | /sales/despacho/{order_id}/despacho | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R177 | sales | /sales/devoluciones | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R178 | sales | /sales/devoluciones/elegibles/{invoice_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R179 | sales | /sales/devoluciones/{return_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R180 | sales | /sales/facturacion/pendientes | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R181 | sales | /sales/facturacion/{order_id}/factura | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R182 | sales | /sales/invoices | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R183 | sales | /sales/notas/acreditable/{invoice_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R184 | sales | /sales/notas/credito/{note_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R185 | sales | /sales/notas/debito/{note_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R186 | sales | /sales/open-items | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R187 | sales | /sales/orders | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R188 | sales | /sales/orders/{order_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R189 | sales | /sales/pick-lists | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R190 | sales | /sales/picking/cola | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R191 | sales | /sales/picking/{plan_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R192 | sales | /sales/picking/{plan_id}/candidatas | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R193 | sales | /sales/picking/{plan_id}/preparacion | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | NO (ya declarada) |
| R194 | sales | /sales/quotes | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R195 | sales | /sales/quotes/{quote_id} | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R196 | sales | /sales/returns | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R197 | sales | /sales/settings/reservation | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R198 | sales | /sales/shipments | COMPANY | COMPANY_PROTECTED_DATA | ventas:view | SÍ |
| R199 | setup | /setup/status | GLOBAL | PUBLIC_REFERENCE_DATA | — (estado de inicialización, necesario antes de existir usuarios) | NO (clasificada) |
| R200 | system | /health/live | GLOBAL | PUBLIC_REFERENCE_DATA | — (sonda de vida sin datos) | NO (clasificada) |
| R201 | system | /health/ready | GLOBAL | PUBLIC_REFERENCE_DATA | — (sonda de disponibilidad sin datos de negocio) | NO (clasificada) |
| R202 | system | /system/diagnostics | GLOBAL | GLOBAL_PROTECTED_DATA | license:view | NO (ya declarada) |
| R203 | treasury | /treasury/accounts | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R204 | treasury | /treasury/accounts/{account_id}/balance | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R205 | treasury | /treasury/bank-transactions | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R206 | treasury | /treasury/banks | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R207 | treasury | /treasury/cash-position | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R208 | treasury | /treasury/cash-sessions | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R209 | treasury | /treasury/cash-sessions/{session_id} | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R210 | treasury | /treasury/cashboxes | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R211 | treasury | /treasury/currencies | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R212 | treasury | /treasury/exchange-rates/import-batches | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R213 | treasury | /treasury/exchange-rates/observations | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R214 | treasury | /treasury/exchange-rates/resolve | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R215 | treasury | /treasury/fiscal-rules | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R216 | treasury | /treasury/fx-conversions | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R217 | treasury | /treasury/fx-policies | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R218 | treasury | /treasury/igft-events | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R219 | treasury | /treasury/instruments | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R220 | treasury | /treasury/payment-methods | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R221 | treasury | /treasury/rate-policies | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R222 | treasury | /treasury/rate-sources | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R223 | treasury | /treasury/reconciliations | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R224 | treasury | /treasury/reconciliations/{reconciliation_id} | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
| R225 | treasury | /treasury/refunds | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R226 | treasury | /treasury/refunds/{refund_id} | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | NO (ya declarada) |
| R227 | treasury | /treasury/transfers | COMPANY | COMPANY_PROTECTED_DATA | tesoreria:view | SÍ |
