# Matriz de Permisos — Spec 012 (pasada 2)

Backend: `require_permission(resource, action)` resuelve permisos del rol del usuario (deny by default).
Frontend: enforcement fino por `allowed_actions` por registro (varias pantallas); **NO** hay ocultamiento por rol en menú/página (KAUD-004).
Multi-empresa: aislamiento por `tenant_id` probado (test_security_integration: 401/403/IDOR/escritura cruzada → 404).
Licencia: READ_ONLY → 423 en escritura de negocio (middleware).

| Recurso | Acciones (catálogo rol ADMIN) | Frontend oculta por rol |
|---|---|---|
| dashboard | view | No (KAUD-004) |
| organization | view, create, edit, deactivate, activate | No (KAUD-004) |
| users | view, create, edit, deactivate, activate | No (KAUD-004) |
| roles | view, create, edit | No (KAUD-004) |
| audit | view | No (KAUD-004) |
| license | view, create, edit, approve | No (KAUD-004) |
| homologacion | view, create, edit, approve | No (KAUD-004) |
| maestros | view, create, edit, deactivate | No (KAUD-004) |
| compras | view, create, approve, quality, apply | No (KAUD-004) |
| ventas | view, create, approve, quality, apply | No (KAUD-004) |
| inventario | view, create, approve, transition, reserve | No (KAUD-004) |
| tesoreria | view, create, approve | No (KAUD-004) |
| fiscal | view, create, approve | No (KAUD-004) |
| regulatorio | view, create, approve | No (KAUD-004) |
| reportes | view, export | No (KAUD-004) |

## Puntos a validar en pasadas futuras
- Usuario con permiso 'view' pero sin 'create' → verifica 403 al crear y botón habilitado (no ocultado).
- Sucursal/almacén no autorizado: los módulos validan tenant (warehouse_in_tenant_scope); probar restricción por sucursal específica.
- Enforcement de estado del documento (allowed_actions por estado) ya cubierto en varias pantallas (Cajas, Conciliación, Conteos).
