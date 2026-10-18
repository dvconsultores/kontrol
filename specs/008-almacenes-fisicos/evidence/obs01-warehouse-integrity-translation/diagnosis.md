# Diagnóstico OBS-01 (sonda desechable fuera del repositorio; app real por HTTP; sin dobles)

## Identidad (fuentes autoritativas)
| Campo | Valor |
|---|---|
| OBS01_AUTHORITATIVE_DESCRIPTION | `evidence/almacenes-carrera-sqlite-hilos/OBSERVACIONES.md`: `_integrity()` convierte cualquier `IntegrityError` en el 409 pedido sin `es_violacion_unica`; en SQLite el helper devuelve siempre `False` |
| OBS01_OWNER_SPEC | 008 (almacenes físicos); apoyo 001 por `app/core/integrity.py` |
| OBS01_ROUTE | `POST /organization/{zone-types,location-types}`, `POST /organization/warehouses`, `POST /organization/warehouses/{id}/{zones,aisles,racks,levels}`, `POST /organization/locations`, `POST /organization/locations/bulk` |
| OBS01_SERVICE | `app/modules/organization/warehouse_api.py` (la lógica vive en el router): `_catalog_create`, `create_warehouse_full`, `_create` (nodos), `create_location_full`, `bulk_locations` |
| OBS01_CONSTRAINT | `uq_zone_types_company_code`, `uq_location_types_company_code`, `uq_warehouses_company_code (company_id, code)`, `uq_warehouse_{zones,aisles,racks,levels}_wh_code`, `uq_warehouse_locations_wh_code (warehouse_id, code)`; nombres idénticos en modelos y migración 0017 |
| OBS01_DUPLICATE_ERROR_CODE | `ZONE_TYPE_/LOCATION_TYPE_/WAREHOUSE_/ZONE_/AISLE_/RACK_/LEVEL_/LOCATION_CODE_DUPLICATE`, 409, mensaje fijo |
| OBS01_INTEGRITY_HELPER | `app/core/integrity.py::es_violacion_unica` (solo PostgreSQL: `pgcode 23505` + `diag.constraint_name`); 7 módulos hermanos lo usan con `raise` del resto |
| Manejador genérico | `app/core/errors.py::_unhandled_handler` → 500 `INTERNAL_ERROR` «Ocurrió un error interno. Intente nuevamente.», sin detalle |

## Mediciones (mismo guion en los dos motores; SQLite con `PRAGMA foreign_keys=ON` solo en la sonda)
| Id | Escenario | PostgreSQL | SQLite |
|---|---|---|---|
| D1 | código de almacén repetido | 409 `WAREHOUSE_CODE_DUPLICATE` | 409 ídem |
| D1 | código de ubicación repetido | 409 `LOCATION_CODE_DUPLICATE` | 409 ídem |
| **D2** | almacén con `branch_id` inexistente (`ForeignKeyViolation` 23503 `fk_warehouses_branch_id_branches` / `SQLITE_CONSTRAINT_FOREIGNKEY` 787) | **409 `WAREHOUSE_CODE_DUPLICATE` «Ya existe un almacén con ese código»** | **409 ídem** |
| **D2** | ubicación con `location_type_id` inexistente | **409 `LOCATION_CODE_DUPLICATE`** | **409 ídem** |
| D3 | fuga en el cuerpo (constraint, SQL, driver, tabla, traza) | 0 | 0 |
| D4 | petición siguiente tras el 409 legítimo y tras el falso | 200 / 200 | 200 / 200 |
| D4 | persistencia del rechazado | 0 filas | 0 filas |
| D5 | 401/403/404 | dependencias `require_permission` y `_get_warehouse` corren antes del `INSERT` (estructural); se cubre en las dirigidas | ídem |

Firmas del driver: PostgreSQL `UniqueViolation 23505 uq_warehouses_company_code` y `ForeignKeyViolation 23503`;
SQLite 3.53.1 / Python 3.11.16 `sqlite3.IntegrityError` con `sqlite_errorcode 2067 SQLITE_CONSTRAINT_UNIQUE` y mensaje
`UNIQUE constraint failed: warehouses.company_id, warehouses.code`, frente a `787 SQLITE_CONSTRAINT_FOREIGNKEY`
«FOREIGN KEY constraint failed». SQLite no aporta nombre de restricción: su única señal es el código extendido y la lista
de columnas, cuyo formato fija SQLite.

Nota: en la configuración por defecto SQLite no aplica claves foráneas, de modo que fuera de la sonda D2 solo se
manifiesta en PostgreSQL (el motor de producción). Sigue siendo defecto: se contesta «ya existe» a un error que no lo es.
