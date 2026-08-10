# Spec 012 — Validación de Seguridad (T-13)

**Estado: RESUELTO** (suite automatizada + correcciones de aislamiento).

## Correcciones aplicadas
1. **Fuga de datos entre tenants en el módulo de organización** (hallazgo crítico):
   - `GET /organization/companies`, `/branches`, `/establishments`, `/warehouses`, `/locations`
     NO filtraban por tenant → cualquier usuario autenticado enumeraba empresas/RIFs y datos
     de otros tenants. Ahora todos filtran por `Company.tenant_id == user.tenant_id`
     (joins en cascada Branch/Warehouse/Establishment/Location → Company).
   - Escrituras (`POST /branches|establishments|warehouses|locations`) aceptaban IDs de
     otros tenants → ahora validan pertenencia (`company_in_tenant`, `branch_in_tenant`,
     `warehouse_in_tenant`) → 404 si no es del tenant.
2. **Referencia cruzada de almacén en tesorería**: `create_cashbox` guardaba `warehouse_id`
   sin validar → ahora valida con `warehouse_in_tenant_scope` (404 si no pertenece).

## Cobertura automatizada (`tests/test_security_integration.py`, 8 tests)
- Sin token → 401 (GET/POST en ventas, organización, maestros, inventario).
- Token inválido → 401.
- RBAC: usuario sin rol → 403 en escritura (`ventas:create`).
- Aislamiento: B no ve listas de A (órdenes, facturas, terceros, movimientos).
- IDOR: B lee orden de A por ID → 404; B agrega línea a orden de A → 404.
- Escritura cruzada: B crea orden con cliente de A → 404 (PARTY_NOT_FOUND).
- Organización: B no ve empresas/almacenes de A; B crea almacén en empresa de A → 404.
- Inyección (SQLi/XSS): payloads como datos (200/400, nunca 500; sin exfiltración).

## Pendiente (ambiente controlado, no contra producción)
- Ejecutar la suite contra una instancia real (PG + varios tenants con datos).
- Revisión manual: CSRF/headers/secretos en logs, subida de archivos (MIME/tamaño/hash).
