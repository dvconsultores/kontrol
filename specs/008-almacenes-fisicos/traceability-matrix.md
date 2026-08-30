# MATRIZ DE TRAZABILIDAD — SPEC 008

Regenerada tras el Gate pre-implementación (Controles 1, 2 y 3).
Las columnas se **derivan de `tasks.md` y `acceptance-criteria.md`**, no se escriben a mano.

## 1. Cobertura — verificada por comando

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 75 |
| Requisitos no funcionales | 8 |
| Criterios de aceptación | 40 |
| Tareas | 96 |
| **Requisitos funcionales sin tarea** | **0** |
| **Requisitos no funcionales sin tarea** | **0** |
| **Criterios sin tarea que los cubra** | **0** |
| **Tareas sin requisito ni criterio** | **0** |

## 2. Requisito funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| FR-008-001 | `Warehouse` con empresa, sucursal opcional, código, nombre, tipo, dirección, responsable | T-008-002, T-008-010 |
| FR-008-002 | Código único por empresa | T-008-003, T-008-010 |
| FR-008-003 | Almacén central admitido: `branch_id` nulo es válido y significa alcance de empresa | T-008-002, T-008-010 |
| FR-008-004 | `structure_levels`: qué tramos usa este almacén (zona, pasillo, rack, nivel), configurab | T-008-002, T-008-010 |
| FR-008-005 | `location_managed`: si es `false`, el inventario opera a nivel de almacén (`ADR-D0-004`  | T-008-002, T-008-010 |
| FR-008-006 | Desactivación reversible; **borrado prohibido** con estructura o movimientos | T-008-010, T-008-035 |
| FR-008-007 | Retirar `cascade="all, delete-orphan"` de la relación con ubicaciones | T-008-004, T-008-010 |
| FR-008-010 | `WarehouseZone`: almacén, código, nombre, tipo, secuencia, estado, descripción | T-008-005, T-008-010, T-008-056 |
| FR-008-011 | `ZoneType` como **catálogo por empresa**, no enum del producto | T-008-001, T-008-010, T-008-040, T-008-077 |
| FR-008-012 | Distinción entre **tipo conceptual** y **nombre**: `type=QUARANTINE`, `name="Zona D"` | T-008-005, T-008-010 |
| FR-008-013 | `WarehouseAisle`: zona opcional, código, nombre, secuencia, estado | T-008-005, T-008-010 |
| FR-008-014 | `WarehouseRack`: pasillo opcional, código, nombre, secuencia, estado | T-008-005, T-008-010 |
| FR-008-015 | `WarehouseLevel`: rack opcional, código, orden vertical, secuencia, estado | T-008-005, T-008-010 |
| FR-008-016 | Código único dentro de su padre inmediato | T-008-007, T-008-010 |
| FR-008-017 | Un almacén sin racks o sin niveles es válido | T-008-005, T-008-010, T-008-055, T-008-068d |
| FR-008-020 | `WarehouseLocation` con almacén obligatorio y zona, pasillo, rack y nivel opcionales | T-008-006, T-008-010 |
| FR-008-021 | Código único por almacén | T-008-007, T-008-010, T-008-058 |
| FR-008-022 | Etiqueta legible **derivada** de la jerarquía, no una columna editable | T-008-010, T-008-032, T-008-051 |
| FR-008-023 | Política de código por almacén: **manual** o **generado** | T-008-010, T-008-031, T-008-051 |
| FR-008-024 | `location_type` de catálogo por empresa (almacenamiento, recepción, cuarentena, despacho | T-008-001, T-008-010, T-008-040, T-008-077 |
| FR-008-025 | `sequence` propia dentro de su padre | T-008-006, T-008-010 |
| FR-008-026 | Capacidad en unidades y peso máximo, ambos opcionales | T-008-006, T-008-010 |
| FR-008-027 | Restricciones declarativas por producto o categoría | T-008-006, T-008-010 |
| FR-008-028 | Campo para identificador de barras/QR, sin implementar impresión | T-008-006, T-008-010 |
| FR-008-029 | Creación masiva de ubicaciones a partir de un patrón de la jerarquía | T-008-010, T-008-038, T-008-046, T-008-051 |
| FR-008-030 | Cada tramo expone `sequence` entera, editable y con valor por defecto | T-008-033 |
| FR-008-031 | Orden físico determinista: `(zona, pasillo, rack, nivel, ubicación)`, con la ubicación c | T-008-033, T-008-052 |
| FR-008-032 | Consulta de ubicaciones ordenadas físicamente, con almacén y filtros | T-008-033 |
| FR-008-033 | El orden es **estable**: dos consultas idénticas devuelven el mismo orden | T-008-033, T-008-052 |
| FR-008-040 | Estados de nodo: `ACTIVE`, `INACTIVE`, `BLOCKED`, `MAINTENANCE` | T-008-034 |
| FR-008-041 | **`FULL` no se persiste**: la ocupación es derivable del saldo (Spec 023) | T-008-034 |
| FR-008-042 | El estado de la ubicación **no** determina el de la mercancía (`ADR-D0-010`) | T-008-034 |
| FR-008-043 | Desactivar un padre no desactiva a los hijos en cascada silenciosa: se rechaza si hay hi | T-008-034, T-008-053, T-008-059 |
| FR-008-050 | FK reales en toda la jerarquía; PostgreSQL es la autoridad | T-008-008 |
| FR-008-051 | Rechazo de jerarquía incoherente (R-008-2) por restricción, no solo por servicio | T-008-008, T-008-030, T-008-050 |
| FR-008-052 | Toda consulta y escritura filtra por empresa | T-008-057, T-008-093 |
| FR-008-053 | Referencia entre empresas rechazada | T-008-057 |
| FR-008-054 | `InventoryBalance.location_id` y `StockCountLine.location_id` pasan a **FK real**; `Inve | T-008-021, T-008-022, T-008-023, T-008-025, T-008-061 |
| FR-008-055 | Una ubicación con movimientos o saldo **no puede borrarse**; `can_delete` y `allowed_act | T-008-035, T-008-053 |
| FR-008-056 | Cambiar el padre estructural de una ubicación con stock o movimientos se **rechaza** (ve | T-008-036, T-008-068c |
| FR-008-060 | Endpoints de listado, detalle, creación, edición, activación y desactivación de los seis | T-008-041, T-008-043, T-008-054 |
| FR-008-061 | `GET /organization/warehouses/{id}/structure` con jerarquía y control de profundidad | T-008-042 |
| FR-008-062 | Búsqueda de ubicaciones paginada y filtrable | T-008-044 |
| FR-008-063 | `allowed_actions` calculado en backend para cada nodo | T-008-037, T-008-057 |
| FR-008-064 | Permisos del recurso `organization`, coherentes con la convención vigente | T-008-011, T-008-081 |
| FR-008-065 | Auditoría de creación, modificación, activación, desactivación, cambio de jerarquía e in | T-008-039 |
| FR-008-066 | Concurrencia optimista con `If-Match` sobre los nodos editables | T-008-048 |
| FR-008-070 | Lista de almacenes con búsqueda, filtros, paginación y acciones | T-008-070, T-008-071, T-008-090 |
| FR-008-071 | Alta y edición de almacén en **pantalla completa con URL propia** | T-008-072 |
| FR-008-072 | Detalle de almacén con navegación por su estructura | T-008-073 |
| FR-008-073 | Gestión de cada tramo en su nivel, con breadcrumb de la cadena | T-008-074 |
| FR-008-074 | Lista de ubicaciones con búsqueda por cualquier tramo | T-008-075 |
| FR-008-075 | Creación masiva por patrón (FR-008-029) en pantalla propia | T-008-076 |
| FR-008-076 | Protección de cambios sin guardar | T-008-079 |
| FR-008-077 | Estados Loading, Ready, Empty, Forbidden, NotFound, Error | T-008-080 |
| FR-008-078 | Un almacén sin tramos intermedios muestra una interfaz **simple**, no la jerarquía compl | T-008-073, T-008-091 |
| FR-008-080 | Contrato para **019/022**: consulta de ubicaciones válidas de destino, filtrables por es | T-008-098 |
| FR-008-081 | Contrato para **023**: la ubicación es dimensión de saldo y movimiento, con FK real | T-008-098 |
| FR-008-082 | Contrato para **025**: origen y destino de transferencia como ubicaciones | T-008-098 |
| FR-008-083 | Contrato para **031/032**: consulta ordenada físicamente | T-008-045, T-008-098 |
| FR-008-084 | Contrato para **036**: ubicaciones de devolución y cuarentena identificables por tipo | T-008-098 |
| FR-008-085 | Contrato para **046**: adjuntos vinculables al almacén sin cambiar el modelo | T-008-098 |
| FR-008-090 | `structure_levels` distingue régimen `INITIAL` (sin nodos ni ubicaciones) de `OPERATIONA | T-008-036a, T-008-068a, T-008-068d |
| FR-008-091 | En régimen `OPERATIONAL`, eliminar, reordenar, resemantizar o colapsar un **tramo utiliz | T-008-036b, T-008-036c, T-008-036d, T-008-068a |
| FR-008-092 | El modelo distingue **cambio de metadata** (nombre, descripción, etiquetas, `sequence` e | T-008-036e |
| FR-008-093 | Todo bloqueo estructural devuelve `code` estable, `reason`, `dependencies` y `allowed_ac | T-008-036f, T-008-047, T-008-068e, T-008-092 |
| FR-008-094 | Ningún nodo de la jerarquía con histórico —propio o heredado— puede borrarse físicamente | T-008-036g, T-008-068b |
| FR-008-095 | No existe desactivación en cascada silenciosa: un nodo con descendientes activos se rech | T-008-036h |
| FR-008-096 | La desactivación es reversible y auditada en ambos sentidos (R-008-10) | T-008-036g, T-008-068b |
| FR-008-097 | 008 **no implementa** reestructuración; deja la arquitectura preparada para un proceso c | T-008-036h |
| FR-008-100 | Toda referencia huérfana detectada por `0018` se **clasifica** en `VALID_REFERENCE`, `RE | T-008-024, T-008-024a, T-008-025, T-008-060, T-008-062, T-008-063 |
| FR-008-101 | Una referencia solo se anula si es reconstruiblemente imposible **y** el modelo históric | T-008-024b, T-008-060, T-008-064 |
| FR-008-102 | Una sola referencia `CRITICAL_NON_RECONSTRUCTIBLE` **aborta** `0018` de forma controlada | T-008-024c, T-008-060, T-008-065 |
| FR-008-103 | `0018` produce un reporte auditable con recuentos por clase y detalle por referencia mod | T-008-024d, T-008-024e, T-008-060, T-008-066 |
| FR-008-104 | El texto legacy `zone`/`aisle`/`rack` se conserva en `legacy_path` y **no** es fuente ad | T-008-020, T-008-024f, T-008-060, T-008-067 |

## 3. Requisito no funcional → tarea

| NFR | Tareas |
|---|---|
| NFR-008-01 | T-008-009, T-008-061a |
| NFR-008-02 | T-008-042 |
| NFR-008-03 | T-008-009, T-008-061a |
| NFR-008-04 | T-008-095, T-008-097 |
| NFR-008-05 | T-008-096, T-008-097 |
| NFR-008-06 | T-008-078 |
| NFR-008-07 | T-008-054, T-008-058, T-008-059 |
| NFR-008-08 | T-008-099 |

## 4. Criterio de aceptación → tarea

| Criterio | Tareas |
|---|---|
| AC-008-01 | T-008-090, T-008-091 |
| AC-008-02 | T-008-090 |
| AC-008-03 | T-008-050 |
| AC-008-04 | T-008-050 |
| AC-008-05 | T-008-093 |
| AC-008-06 | T-008-051 |
| AC-008-07 | T-008-051 |
| AC-008-08 | T-008-052 |
| AC-008-09 | T-008-053 |
| AC-008-10 | T-008-053 |
| AC-008-11 | T-008-092 |
| AC-008-12 | T-008-053 |
| AC-008-13 | T-008-053 |
| AC-008-14 | T-008-068c |
| AC-008-15 | T-008-068b |
| AC-008-16 | T-008-060 |
| AC-008-17 | T-008-067 |
| AC-008-18 | T-008-060 |
| AC-008-19 | T-008-042, T-008-061a |
| AC-008-20 | T-008-061a |
| AC-008-21 | T-008-057 |
| AC-008-22 | T-008-099 |
| AC-008-23 | T-008-051 |
| AC-008-24 | T-008-094 |
| AC-008-25 | T-008-062 |
| AC-008-26 | T-008-063 |
| AC-008-27 | T-008-064 |
| AC-008-28 | T-008-065 |
| AC-008-29 | T-008-066 |
| AC-008-30 | T-008-067 |
| AC-008-31 | T-008-068a |
| AC-008-32 | T-008-068a |
| AC-008-33 | T-008-068a |
| AC-008-34 | T-008-068b |
| AC-008-35 | T-008-068b |
| AC-008-36 | T-008-068c |
| AC-008-37 | T-008-068d |
| AC-008-38 | T-008-068d |
| AC-008-39 | T-008-068e |
| AC-008-40 | T-008-092 |

## 5. Autoridad → requisito

| Fuente | Requisitos |
|---|---|
| `ADR-D0-004` jerarquía y hoja | FR-008-020, R-008-1 |
| `ADR-D0-004` R-D0-04-1 sin zonas fijas | FR-008-011, 012 |
| `ADR-D0-004` R-D0-04-2 integración transaccional | FR-008-054, 080..085 |
| `ADR-D0-004` R-D0-04-3 `location_managed` | FR-008-005 |
| `ADR-D0-010` estados independientes | FR-008-042 |
| `ADR-D0-013` dimensiones organizacionales | FR-008-001, 003 |
| **`ADR-D0-001` PostgreSQL 18.x `CONFIRMED_BY_EXECUTION`** | **NFR-008-07** |
| `ADR-011` cadena organizacional | FR-008-001, 052 |
| `ADR-012` auditoría | FR-008-065 |
| `ADR-013` idempotencia y concurrencia | FR-008-066 |
| `ADR-015` / P18 sin modales | NFR-008-06, FR-008-071 |
| Constitución P5 dato histórico | FR-008-006, 007, 055, 056, **094, 100, 101, 102** |
| Constitución P6 backend es autoridad | FR-008-063, **093** |
| Constitución P8 sin negocio en código | NFR-008-08, FR-008-011 |
| Constitución P11 accesibilidad y responsive | NFR-008-04, 05 |
| Constitución P21 paridad del motor | NFR-008-07 |
| Constitución P23 captura temprana | FR-008-054 (F2 antes que F4), **100..104** |
| Proceso documentado §4 clasificación y ubicación | FR-008-010..025, 030..033 |
| Encargo §17 secuencia física | FR-008-030..033, 083 |
| Encargo §27, §59 borrado | FR-008-006, 043, 055 |
| Encargo §58 reubicación | FR-008-056 |
| Encargo §63..66 contratos | FR-008-080..084 |
| **Gate Control 1** — `migration-0018-policy.md` | **FR-008-100..104** |
| **Gate Control 2** — `structure-mutability-policy.md` | **FR-008-090..097** |
| **Gate Control 3** — `postgresql-version-validation.md` | **NFR-008-07** |

## 6. Requisitos añadidos por el Gate

| Bloque | Requisitos | Origen | Amplía alcance |
|---|---|---|---|
| Migración `0018` | FR-008-100..104 | Control 1 | **No** — restringe qué puede hacer `0018` |
| Mutabilidad estructural | FR-008-090..097 | Control 2 | **No** — prohíbe operaciones antes permitidas por omisión |

Ningún requisito del Gate añade funcionalidad nueva. Los trece son **restricciones**
sobre comportamiento que la Spec dejaba sin gobernar.

## 7. Requisito → código → prueba → evidencia

Cadena completa tras `/speckit.implement 008`.

| Bloque | Código | Prueba | Evidencia |
|---|---|---|---|
| FR-008-001..007 almacén | `organization/models.py::Warehouse` | `test_warehouse_structure.py::test_almacen_simple_*`, `test_borrar_almacen_no_destruye_ubicaciones` | `pg18-regression-final.log` |
| FR-008-010..017 tramos | `models.py::Warehouse{Zone,Aisle,Rack,Level}` | `test_almacen_complejo_cadena_completa`, `test_tramo_no_declarado_se_rechaza` | ídem |
| FR-008-020..029 ubicación | `models.py::WarehouseLocation`, `structure.py::generate_location_code` | `test_codigo_unico_por_almacen`, `test_creacion_masiva_con_vista_previa_obligatoria`, `test_codigo_generado_desde_el_patron_del_almacen` | ídem |
| FR-008-030..033 secuencia | `structure.py::physical_order_query` | `test_orden_fisico_determinista_y_estable` | ídem + E2E |
| FR-008-040..043 estados | `warehouse_api.py::_set_location_status` | `test_estados_sin_full_y_mercancia_independiente` | ídem |
| FR-008-050..056 integridad | `structure.py::validate_chain`, `assert_can_relocate` | `test_cadena_incoherente_y_entre_almacenes_rechazadas`, `test_caso_f_reubicacion_con_historial_bloqueada` | ídem |
| FR-008-060..066 API | `warehouse_api.py` (42 rutas) | `test_if_match_concurrencia_optimista`, `test_estructura_no_carga_ubicaciones_por_defecto` | contrato OpenAPI 18/18 |
| FR-008-070..078 frontend | `AlmacenesPage`, `AlmacenDetallePage`, `UbicacionesPage` | 218 unitarias + 15 E2E | `warehouse-structure.spec.ts` |
| FR-008-080..085 contratos futuros | `GET /locations/ordered`, FK reales | `test_las_dos_referencias_son_fk_reales` | §33 del closeout |
| **FR-008-090..097 mutabilidad** | `structure.py::validate_structure_levels_change`, `assert_can_deactivate_node` | `test_caso_b_y_c_*`, `test_desactivacion_en_cascada_silenciosa_no_existe`, `test_historico_heredado_*` | ídem + E2E |
| **FR-008-100..104 migración** | `0018_location_fk_and_legacy.py::_classify` | `test_warehouse_migration_0018.py` (7 casos) | reporte de `0018` |
| NFR-008-01..03 rendimiento | índices de `data-model.md` | conjunto de 50.000 ubicaciones | §28 del closeout |
| NFR-008-04..05 a11y y responsive | pantallas de 008 | `warehouse-a11y.spec.ts` | 3/3 verdes |
| NFR-008-07 PostgreSQL 18.x | toda la suite | 317/317 | `pg18-regression-final.log` |
| NFR-008-08 sin negocio en código | — | búsqueda de literales | 0 coincidencias |

**Requisitos sin implementación: 0. Tareas sin requisito: 0. Criterios sin evidencia: 0.**
