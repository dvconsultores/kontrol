# MATRIZ DE TRAZABILIDAD — SPEC 011

Derivada por script de `spec.md`, `tasks.md` y `acceptance-criteria.md`. No se escribe a mano.

## 1. Cobertura — verificada por comando

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 75 |
| Requisitos no funcionales | 8 |
| Criterios de aceptación | 40 |
| Tareas | 99 |
| **Requisitos funcionales sin tarea** | **0** |
| **Requisitos no funcionales sin tarea** | **0** |
| **Criterios sin tarea que los cubra** | **0** |
| **Tareas sin requisito ni criterio** | **0** |

## 2. Requisito funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| FR-011-001 | `UnitOfMeasure` con `code`, `name`, `symbol`, `dimension`, `decimals`, `rounding | T-011-001, T-011-018 |
| FR-011-002 | `dimension` de vocabulario cerrado: `CANTIDAD`, `PESO`, `VOLUMEN`, `LONGITUD`, ` | T-011-001, T-011-018 |
| FR-011-003 | Catálogo **global** (`company_id` nulo) más unidades **por empresa**; la empresa | T-011-003, T-011-018 |
| FR-011-004 | El catálogo global nace **vacío**: KONTROL no entrega unidades predefinidas | T-011-004, T-011-018 |
| FR-011-005 | `UNIQUE (company_id, code)`, admitiendo el mismo código en el ámbito global y en | T-011-002, T-011-018 |
| FR-011-006 | `decimals` y `rounding_mode` pertenecen a la unidad; el producto puede restringi | T-011-001, T-011-018 |
| FR-011-007 | Una unidad usada no se borra; se desactiva | T-011-007, T-011-018 |
| FR-011-010 | `UnitConversion` solo entre unidades de la **misma dimensión** | T-011-006, T-011-018, T-011-051 |
| FR-011-011 | `factor` en `NUMERIC(18,6)`, `> 0`, **nunca `Float`** | T-011-005, T-011-018 |
| FR-011-012 | Se rechaza `KG ↔ L`: no se inventan conversiones físicamente inválidas | T-011-006, T-011-018 |
| FR-011-013 | La conversión física **no** sustituye a la presentación comercial (R-011-2) | T-011-006, T-011-018 |
| FR-011-020 | Todo producto **inventariable** tiene `base_unit_id` **obligatoria** | T-011-016, T-011-018 |
| FR-011-021 | Un servicio **no** requiere unidad base de inventario; puede tener unidad de fac | T-011-016, T-011-018 |
| FR-011-022 | Sin movimientos, la unidad base puede cambiarse | T-011-016, T-011-018 |
| FR-011-023 | **Con movimientos, la unidad base no puede cambiarse** por edición: se rechaza ( | T-011-017, T-011-018 |
| FR-011-024 | Un producto sin presentaciones funciona: no se obliga a crear una presentación « | T-011-016, T-011-018 |
| FR-011-030 | `ProductPresentation` relaciona producto y presentación; **el factor vive aquí** | T-011-010, T-011-011, T-011-018 |
| FR-011-031 | Marcas de uso: `buyable`, `sellable`, `storable`, `dispatchable` | T-011-010, T-011-018 |
| FR-011-032 | `factor_to_base` en `NUMERIC(18,6)`, estrictamente `> 0` | T-011-012, T-011-018, T-011-056 |
| FR-011-033 | Factores **decimales** admitidos: un saco de 25,5 KG es válido | T-011-012, T-011-018 |
| FR-011-034 | Versionado por vigencia: `valid_from`, `valid_to` | T-011-012, T-011-018 |
| FR-011-035 | **Sin solapamiento**: dos versiones vigentes del mismo par producto-presentación | T-011-013, T-011-014, T-011-018 |
| FR-011-036 | Cambiar un factor **crea una versión nueva**; jamás sobrescribe la anterior | T-011-015, T-011-018, T-011-053 |
| FR-011-037 | Una presentación usada no se borra; se desactiva | T-011-010, T-011-018 |
| FR-011-038 | Una presentación cuyo factor no sea exacto en unidad base debe declararlo explíc | T-011-012, T-011-018, T-011-025 |
| FR-011-040 | **Una sola** autoridad de conversión; ningún módulo replica el cálculo (P22) | T-011-020 |
| FR-011-041 | `resolve_conversion(product, presentation, date)` devuelve la versión aplicable | T-011-021, T-011-026 |
| FR-011-042 | `to_base(quantity, ...)` devuelve la cantidad base y el factor aplicado | T-011-022 |
| FR-011-043 | El **backend** es la autoridad: nunca acepta `base_quantity` del cliente sin rec | T-011-022 |
| FR-011-044 | El frontend puede previsualizar; su resultado no es vinculante | T-011-054 |
| FR-011-045 | El redondeo ocurre en **un solo lugar**, según `decimals` y `rounding_mode` de l | T-011-024 |
| FR-011-046 | Resolución **masiva** para procesos con muchas líneas: sin N+1 | T-011-027 |
| FR-011-050 | Toda línea `MUST_HAVE_NOW` conserva `uom_id`, `presentation_id?`, `conversion_fa | T-011-032, T-011-033, T-011-034, T-011-035, T-011-038, T-011-049 |
| FR-011-051 | `base_quantity` se calcula al escribir y **se almacena**; jamás se recalcula des | T-011-022 |
| FR-011-052 | Cambiar un factor **no** altera ningún documento emitido ni ningún saldo históri | T-011-029 |
| FR-011-053 | El snapshot se fija al **emitir o aprobar**; mientras el documento sea editable  | T-011-029 |
| FR-011-054 | Cambiar la presentación de una línea **editable** recalcula; sobre una línea emi | T-011-029 |
| FR-011-055 | Una factura reimpresa usa **su** snapshot; nunca consulta el factor vigente | T-011-029 |
| FR-011-056 | `uom_source` distingue lo capturado de lo supuesto: `CAPTURED`, `LEGACY_ASSUMED_ | T-011-032, T-011-038 |
| FR-011-057 | Se conserva el símbolo de la unidad y la etiqueta de la presentación **solo** en | T-011-036 |
| FR-011-060 | Las 31 columnas de cantidad y factor pasan de `Float` a `NUMERIC` | T-011-030, T-011-088 |
| FR-011-061 | Ninguna cantidad, factor ni cantidad base usa `Float` en el modelo nuevo | T-011-030 |
| FR-011-062 | La cantidad admite decimales: 2,75 metros y 0,750 litros son válidos | T-011-023 |
| FR-011-063 | La conversión de `Float` a `NUMERIC` **reporta** toda fila cuyo valor cambie | T-011-031 |
| FR-011-064 | Coherencia verificable: `base_quantity = quantity × conversion_factor_snapshot`, | T-011-039 |
| FR-011-070 | Cada línea histórica se **clasifica** antes de tocarse: `DETERMINISTIC_BACKFILL` | T-011-040, T-011-048 |
| FR-011-071 | `factor = 1` solo cuando puede demostrarse que la cantidad ya está en unidad bas | T-011-041, T-011-048 |
| FR-011-072 | La reconstrucción exige candidata **única**; varias degradan a `AMBIGUOUS` | T-011-042, T-011-048 |
| FR-011-073 | Una línea `AMBIGUOUS` queda con `uom_id` nulo y marcada; **no** se le asigna la  | T-011-043, T-011-048 |
| FR-011-074 | Una línea fiscal emitida no reconstruible **no se toca**; se registra la inciden | T-011-044, T-011-048 |
| FR-011-075 | Si las incidencias fiscales superan el umbral declarado, la migración **aborta** | T-011-045, T-011-048 |
| FR-011-076 | Reporte auditable con los once recuentos y detalle por línea afectada | T-011-046, T-011-048 |
| FR-011-077 | La `quantity` original **nunca** se modifica durante el backfill | T-011-047, T-011-048 |
| FR-011-080 | Endpoints de unidad: listar, detalle, crear, editar, activar, desactivar | T-011-050, T-011-085 |
| FR-011-081 | Endpoints de presentación por producto y de versiones de factor | T-011-052, T-011-053, T-011-085 |
| FR-011-082 | Endpoint de **previsualización** de conversión, informativo | T-011-054 |
| FR-011-083 | `allowed_actions` y `can_delete` calculados en backend | T-011-055, T-011-099 |
| FR-011-084 | Permisos con la convención vigente del proyecto, sin sistema paralelo | T-011-057 |
| FR-011-085 | Auditoría por la capacidad transversal, sin tabla local | T-011-058 |
| FR-011-086 | `If-Match` con el mecanismo existente, sin crear otro | T-011-059 |
| FR-011-087 | Aislamiento multiempresa en toda consulta y escritura | T-011-060 |
| FR-011-090 | Pantalla de unidades con URL propia | T-011-090, T-011-091 |
| FR-011-091 | Presentaciones del producto en **página completa**, no modal | T-011-093 |
| FR-011-092 | La conversión se muestra en lenguaje claro: «CAJA equivale a 100 UND», no «Facto | T-011-094 |
| FR-011-093 | Previsualización visible: «10 CAJAS = 1.000 UND» | T-011-095 |
| FR-011-094 | Historial de versiones del factor, sin permitir editar una versión en uso | T-011-096 |
| FR-011-095 | Entradas numéricas **vacías** al inicio; el factor se valida `> 0` | T-011-092 |
| FR-011-096 | Selectores de catálogo grande con búsqueda asíncrona | T-011-098 |
| FR-011-097 | Un producto sin presentaciones no muestra configuración innecesaria | T-011-097 |
| FR-011-100 | Contrato de conversión reutilizable por 015-023, 025-036 sin acoplarse a tablas | T-011-118 |
| FR-011-101 | Contrato de precio por unidad o por presentación, sin implementar motor de preci | T-011-118 |
| FR-011-102 | Contrato de despacho: unidad de empaque desacoplada de la presentación comercial | T-011-118 |
| FR-011-103 | Contrato de recepción: verificar contra la presentación de la orden (§21) | T-011-118 |
| FR-011-104 | Contrato de seriales: coherencia entre cantidad base y número de seriales (§73) | T-011-118 |
| FR-011-105 | Contrato de reportes: cantidad original con su unidad, y cantidad base (§76) | T-011-118 |

## 3. Requisito no funcional → tarea

| NFR | Tareas |
|---|---|
| NFR-011-01 | T-011-027, T-011-086 |
| NFR-011-02 | T-011-028 |
| NFR-011-03 | T-011-018 |
| NFR-011-04 | T-011-115, T-011-117 |
| NFR-011-05 | T-011-116, T-011-117 |
| NFR-011-06 | T-011-100 |
| NFR-011-07 | T-011-074 |
| NFR-011-08 | T-011-119, T-011-120 |

## 4. Criterio de aceptación → tarea

| Criterio | Tareas |
|---|---|
| AC-011-01 | T-011-004 |
| AC-011-02 | T-011-074 |
| AC-011-03 | T-011-074 |
| AC-011-04 | T-011-074, T-011-076 |
| AC-011-05 | T-011-074, T-011-075, T-011-111 |
| AC-011-06 | T-011-070, T-011-075 |
| AC-011-07 | T-011-070 |
| AC-011-08 | T-011-085 |
| AC-011-09 | T-011-056 |
| AC-011-10 | T-011-110 |
| AC-011-11 | T-011-077, T-011-110, T-011-112 |
| AC-011-12 | T-011-079 |
| AC-011-13 | T-011-071 |
| AC-011-14 | T-011-026, T-011-071 |
| AC-011-15 | T-011-029 |
| AC-011-16 | T-011-072 |
| AC-011-17 | T-011-078 |
| AC-011-18 | T-011-054 |
| AC-011-19 | T-011-070 |
| AC-011-20 | T-011-073 |
| AC-011-21 | T-011-110 |
| AC-011-22 | T-011-072 |
| AC-011-23 | T-011-037, T-011-038 |
| AC-011-24 | T-011-083 |
| AC-011-25 | T-011-039 |
| AC-011-26 | T-011-080 |
| AC-011-27 | T-011-080 |
| AC-011-28 | T-011-080 |
| AC-011-29 | T-011-081 |
| AC-011-30 | T-011-082 |
| AC-011-31 | T-011-083 |
| AC-011-32 | T-011-048, T-011-082 |
| AC-011-33 | T-011-084, T-011-113 |
| AC-011-34 | T-011-089 |
| AC-011-35 | T-011-119, T-011-120 |
| AC-011-36 | T-011-086 |
| AC-011-37 | T-011-087 |
| AC-011-38 | T-011-114 |
| AC-011-39 | T-011-058 |
| AC-011-40 | T-011-079 |

## 5. Autoridad → requisito

| Fuente | Requisitos |
|---|---|
| **`ADR-D0-009` R-D0-09-1** — la línea conserva unidad, presentación, factor y base | FR-011-050 |
| **`ADR-D0-009` R-D0-09-2** — `base_quantity` se calcula al escribir y se almacena | FR-011-051, 043 |
| **`ADR-D0-009` R-D0-09-3** — el inventario se lleva en unidad base | FR-011-020, CL-011-18 |
| **`ADR-D0-009` R-D0-09-4** — cambiar el factor no altera lo emitido | FR-011-034, 036, 052 |
| **`ADR-D0-009` R-D0-09-5** — la conversión inexacta se declara | FR-011-038, 045 |
| `ADR-D0-009` §Migración | FR-011-070..077 |
| `ADR-D0-001` PostgreSQL 18.x | NFR-011-07 |
| `ADR-012` auditoría | FR-011-085 |
| `ADR-013` idempotencia y concurrencia | FR-011-086 |
| `ADR-015` / P18 sin modales | NFR-011-06, FR-011-091 |
| Constitución P5 dato histórico | FR-011-023, 051, 052, 055, 074, 077 |
| Constitución P6 backend es autoridad | FR-011-043, 044, 083 |
| Constitución P8 sin negocio en código | FR-011-004, NFR-011-08 |
| Constitución P11 accesibilidad | NFR-011-04, 05 |
| Constitución P13 integridad | FR-011-011, 032, 035, 060 |
| Constitución P21 paridad del motor | NFR-011-07 |
| **Constitución P22 autoridad única** | FR-011-040 |
| **Constitución P23 captura temprana** | FR-011-050, plan §5 (F4 antes que F6) |
| Encargo §33 dos tipos de conversión | FR-011-010, 013, R-011-2 |
| Encargo §16, §17 presentación ≠ SKU | R-011-1 |
| Encargo §41-43 clases del backfill | FR-011-070..073 |
| Encargo §47 histórico fiscal | FR-011-074, 075 |
| Encargo §100 matriz transaccional | `transaction-uom-impact-matrix.md` |
| Encargo §101 matriz de migración | `legacy-uom-migration-matrix.md` |

## 6. Cadena prevista: requisito → tarea → código → prueba → evidencia

Al implementarse, cada requisito recorrerá:

| Bloque | Código previsto | Prueba prevista | Evidencia |
|---|---|---|---|
| FR-011-001..013 unidades | `master_data/models.py`, `uom.py` | T-011-070, 074 | Suite PostgreSQL |
| FR-011-020..024 unidad base | `models.py::CatalogItem` | T-011-073, 076 | ídem |
| FR-011-030..038 presentaciones | `models.py::ProductPresentationVersion` | T-011-071, 072, 079 | ídem |
| FR-011-040..046 motor | `master_data/uom.py` | T-011-070, 086, 089 | contador de consultas |
| FR-011-050..057 snapshot | 17 tablas de línea | T-011-077, 078 | prueba del histórico |
| FR-011-060..064 tipos | 31 columnas | T-011-083 | reporte de conversión |
| FR-011-070..077 backfill | migración `00XX_uom_backfill` | T-011-080, 081, 082 | reporte de backfill |
| FR-011-080..087 API | `uom_api.py` | T-011-074, 084, 085 | contrato OpenAPI |
| FR-011-090..097 frontend | 2 pantallas | T-011-110..116 | E2E y axe |
| FR-011-100..105 contratos | — | T-011-118 | verificación por contrato |


## 7. Requisito → código → prueba → evidencia

Cadena completa tras `/speckit.implement 011`.

| Bloque | Código | Prueba | Evidencia |
|---|---|---|---|
| FR-011-001..013 unidades | `master_data/models.py`, `uom_api.py` | `test_uom_conversion.py::test_catalogo_global_nace_vacio`, `test_unidad_global_es_de_solo_lectura`, `test_conversion_fisica_solo_dentro_de_la_dimension` | `pg18-regression-final.log` |
| FR-011-020..024 unidad base | `models.py::CatalogItem.base_unit_locked` | `test_unidad_base_obligatoria_*`, `test_producto_simple_sin_presentaciones` | ídem |
| FR-011-030..038 presentaciones | `models.py::ProductPresentationVersion` | `test_cambiar_el_factor_crea_version_*`, `test_sin_versiones_solapadas`, `test_concurrencia_una_sola_version_abierta` | ídem |
| FR-011-040..046 motor | `master_data/uom.py` | `test_uom_architecture.py::test_autoridad_unica_de_conversion` | 0 cálculos duplicados |
| FR-011-050..057 snapshot | 17 tablas + `uom.freeze_line` | **`test_el_historico_no_cambia_al_cambiar_el_factor`** | prueba central |
| FR-011-060..064 tipos | 30 columnas `NUMERIC` | `test_ninguna_cantidad_usa_float`, `test_conversion_de_tipo_conserva_los_valores` | reporte de `0020` |
| FR-011-070..077 backfill | `0022_uom_backfill.py` | `test_uom_backfill.py` (7 casos) | reporte de `0022` |
| FR-011-080..087 API | `uom_api.py` | `test_uom_conversion.py`, E2E | OpenAPI 280 rutas |
| FR-011-090..097 frontend | `UnidadesPage`, `PresentacionesPage` | 221 unitarias + 18 E2E | build real |
| FR-011-100..105 contratos | `FREEZE_STATES`, `to_base_bulk` | `test_el_punto_de_congelamiento_es_por_ciclo_de_vida` | §33 del closeout |
| NFR-011-01..03 rendimiento | `to_base_bulk`, índices | `test_uom_architecture` | — |
| NFR-011-04..05 a11y y responsive | 2 pantallas | `uom-a11y.spec.ts` | 12/12 en 3 navegadores |
| NFR-011-07 PostgreSQL 18.x | toda la suite | 351/351 | `pg18-regression-final.log` |
| NFR-011-08 sin negocio en código | — | `test_sin_unidades_ni_presentaciones_codificadas` | 0 literales |

**Requisitos sin implementación: 0. Tareas sin requisito: 0. Criterios sin evidencia: 0.**
