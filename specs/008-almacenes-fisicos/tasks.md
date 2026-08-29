# TAREAS — SPEC 008

Estado inicial: **ninguna ejecutada.** La implementación requiere autorización
expresa que mencione `008` (P2).

Estimación relativa XS · S · M · L · XL. Sin horas: no hay datos de velocidad.

## F1 · Modelo e integridad

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-001 | `ZoneType` y `LocationType` como catálogos por empresa | FR-008-011, 024 | S |
| T-008-002 | Extender `Warehouse`: dirección, responsable, `location_managed`, `structure_levels`, `structure_regime`, política de código; `branch_id` nulo = almacén central | FR-008-001, 003, 004, 005 | M |
| T-008-003 | `UNIQUE (company_id, code)` en almacenes | FR-008-002 | XS |
| T-008-004 | **Retirar `cascade="all, delete-orphan"`** de `Warehouse.locations` | FR-008-007 | XS |
| T-008-005 | `WarehouseZone`, `WarehouseAisle`, `WarehouseRack`, `WarehouseLevel` con secuencia, estado y tipo conceptual distinto del nombre; un almacén sin racks ni niveles es válido | FR-008-010, 012, 013, 014, 015, 017 | M |
| T-008-006 | `WarehouseLocation` sustituye a `Location`, conservando el `id`; `sequence` propia, capacidad y peso opcionales, restricciones declarativas y campo de código de barras | FR-008-020, 025, 026, 027, 028 | M |
| T-008-007 | Unicidad de código por padre y por almacén | FR-008-016, 021 | S |
| T-008-008 | Restricciones de coherencia de cadena y de almacén; FK reales en toda la jerarquía | FR-008-050, 051, R-008-2 | L |
| T-008-009 | Índices del modelo de datos, cada uno con su consulta justificante | NFR-008-01, NFR-008-03 | S |
| T-008-010 | Migración `0017_warehouse_structure` | FR-008-001..029, plan §6 | L |
| T-008-011 | Permisos del recurso `organization` en seed + migración de datos | FR-008-064 | S |

## F2 · Conversión de referencias — antes que la API (P23)

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-020 | `legacy_path` desde `zone`/`aisle`/`rack`, sin conversión automática | FR-008-104, CL-008-15 | M |
| T-008-021 | `InventoryBalance.location_id` → FK real | FR-008-054 | S |
| T-008-022 | Verificar que `InventoryMovement.location_id` (ya FK) apunta a `warehouse_locations` tras el renombrado | FR-008-054 | S |
| T-008-023 | `StockCountLine.location_id` → FK real | FR-008-054 | S |
| T-008-024 | **Clasificador de referencias**: `VALID_REFERENCE` / `RECONSTRUCTIBLE_ORPHAN` / `NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED` / `CRITICAL_NON_RECONSTRUCTIBLE`, sin escribir nada | FR-008-100 | L |
| T-008-024a | Reconstrucción determinista y unívoca de clase B; dos candidatas degradan la fila, nunca se elige «la más probable» | FR-008-100 | M |
| T-008-024b | Anulación de clase C con las tres condiciones evaluadas y `legacy_location_id` preservado | FR-008-101 | M |
| T-008-024c | **Bloqueo** de la migración ante una sola clase D, con reporte emitido y cero escrituras aplicadas | FR-008-102 | M |
| T-008-024d | Reporte de migración: cabecera con recuentos por clase, detalle por referencia modificada o crítica, datos mínimos | FR-008-103 | M |
| T-008-024e | Invariante `valid + reconstructed + nulled + critical = total_rows_checked` verificado en la propia migración | FR-008-103 | S |
| T-008-024f | `legacy_path` como dato inerte: no es fuente admisible de reconstrucción | FR-008-104 | S |
| T-008-025 | Migración `0018_location_fk_and_legacy`, idempotente, en el orden obligatorio de `migration-0018-policy.md` §3 | FR-008-054, 100..104 | L |

## F3 · Reglas de dominio

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-030 | `StructureService`: validación de cadena y de tramos declarados | FR-008-051, R-008-1 | L |
| T-008-031 | Generación de código según política y patrón del almacén | FR-008-023 | M |
| T-008-032 | Etiqueta legible derivada de la cadena | FR-008-022 | S |
| T-008-033 | Secuencia física y consulta ordenada determinista | FR-008-030..033 | M |
| T-008-034 | Estados de nodo `ACTIVE`/`INACTIVE`/`BLOCKED`/`MAINTENANCE`; sin `FULL` persistido; estado de ubicación independiente del de la mercancía; desactivación sin cascada silenciosa | FR-008-040, 041, 042, 043 | M |
| T-008-035 | `can_delete`: sin movimientos, saldo ni reservas; desactivación reversible y borrado prohibido con estructura o movimientos | FR-008-006, 055 | M |
| T-008-036 | Rechazo de reubicación estructural con historial | FR-008-056 | M |
| T-008-036a | Régimen `INITIAL` / `OPERATIONAL` de `structure_levels`; el paso a operativo es irreversible | FR-008-090 | M |
| T-008-036b | Rechazo de eliminar un tramo **utilizado**; un tramo declarado sin nodos sí puede retirarse | FR-008-091 | M |
| T-008-036c | Rechazo de reordenar o resemantizar tramos utilizados | FR-008-091 | M |
| T-008-036d | Rechazo de cambiar la profundidad con ubicaciones existentes | FR-008-091 | S |
| T-008-036e | Separación **metadata** frente a **estructural**; `sequence` entre hermanos es metadata | FR-008-092 | M |
| T-008-036f | Respuestas de bloqueo con `code`, `reason`, `dependencies` y `allowed_actions` | FR-008-093 | M |
| T-008-036g | Política de borrado y desactivación por entidad para los seis nodos, con histórico heredado | FR-008-094, FR-008-096 | L |
| T-008-036h | Verificación de que no queda ningún `cascade` destructivo ni desactivación en cascada, y de que **no** existe endpoint ni ruta de reestructuración | FR-008-095, 097, R-008-8 | S |
| T-008-037 | `allowed_actions` por nodo, en backend | FR-008-063 | S |
| T-008-038 | Creación masiva por patrón con vista previa | FR-008-029 | M |
| T-008-039 | Auditoría de todo cambio vía `record_audit` | FR-008-065 | S |

## F4 · API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-040 | Endpoints de los catálogos | FR-008-011, 024 | S |
| T-008-041 | Endpoints de almacén: listado, detalle, alta, edición, activación, borrado | FR-008-060 | M |
| T-008-042 | `GET /warehouses/{id}/structure` con `depth` y paginación; la estructura no se carga entera | FR-008-061, NFR-008-02, AC-008-19 | M |
| T-008-043 | Endpoints de zona, pasillo, rack y nivel | FR-008-060 | L |
| T-008-044 | Endpoints de ubicación, con búsqueda filtrable | FR-008-062 | M |
| T-008-045 | `GET /locations/ordered` — contrato para la Spec 031 | FR-008-083 | M |
| T-008-046 | `POST /locations/bulk` | FR-008-029 | S |
| T-008-047 | Los 14 códigos de error del contrato, con `reason`, `dependencies` y `allowed_actions` en los estructurales | FR-008-093, contratos | S |
| T-008-048 | `If-Match` en nodos editables | FR-008-066 | S |

## F5 · Pruebas de backend — antes del frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-050 | Unidad: coherencia de cadena, incluidos los casos incoherentes y los tramos de otro almacén | FR-008-051, AC-008-03, AC-008-04 | M |
| T-008-051 | Unidad: generación de código, etiqueta derivada no persistida, colisiones y vista previa de creación masiva | FR-008-022, 023, 029, AC-008-06, AC-008-07, AC-008-23 | M |
| T-008-052 | Unidad: orden físico determinista y estable con tramos nulos | FR-008-031, 033, AC-008-08 | M |
| T-008-053 | Unidad: desactivación reversible, `can_delete` por nodo, ausencia de `FULL` e independencia del estado de la mercancía | FR-008-043, 055, AC-008-09, AC-008-10, AC-008-12, AC-008-13 | M |
| T-008-054 | Integración: los 12 casos del §47 **sobre PostgreSQL 18.x** | FR-008-060, NFR-008-07, §47 | L |
| T-008-055 | Integración: almacén **simple** de extremo a extremo | FR-008-017, HU-008-01 | M |
| T-008-056 | Integración: almacén **complejo** de extremo a extremo | FR-008-010, HU-008-02 | M |
| T-008-057 | Integración: aislamiento multiempresa, IDOR y `allowed_actions` en tres estados de permiso | FR-008-052, 053, 063, AC-008-21 | M |
| T-008-058 | **Concurrencia sobre PostgreSQL**: mismo código simultáneo | FR-008-021, NFR-008-07, §55 | M |
| T-008-059 | Concurrencia: desactivación mientras otra operación usa la ubicación | FR-008-043, NFR-008-07, §55 | M |
| T-008-060 | Migraciones `0017` y `0018` sobre base limpia y sobre base pre-008; las 2 referencias quedan como FK reales | FR-008-100..104, AC-008-16, AC-008-18, plan §6 | L |
| T-008-062 | Migración caso 1: todas las referencias válidas → PASS sin modificar filas | FR-008-100, AC-008-25 | M |
| T-008-063 | Migración caso 2: huérfana reconstruible → reparada con evidencia; dos candidatas degradan | FR-008-100, AC-008-26 | M |
| T-008-064 | Migración caso 3: no reconstruible con nulo legítimo → `NULL` + legacy + incidencia | FR-008-101, AC-008-27 | M |
| T-008-065 | Migración caso 4: huérfana crítica → **migración bloqueada**, cero escrituras | FR-008-102, AC-008-28 | M |
| T-008-066 | Migración caso 5: ejecución repetida → idempotente y no destructiva | FR-008-103, AC-008-29 | S |
| T-008-067 | Migración caso 6: upgrade desde base real pre-008 con datos → integridad comprobada y `legacy_path` con el texto original | FR-008-104, AC-008-17, AC-008-30 | L |
| T-008-068a | Estructural caso A/B/C: `INITIAL` permitido; eliminar y reordenar tramo utilizado bloqueados | FR-008-090, 091, AC-008-31..33 | M |
| T-008-068b | Estructural caso D/E: desactivar sin dependencias permitido; borrar con histórico bloqueado; sin `cascade` destructivo | FR-008-094, 096, AC-008-15, AC-008-34, 35 | M |
| T-008-068c | Estructural caso F: cambiar padre de ubicación con histórico bloqueado; sin histórico, permitido | FR-008-056, AC-008-14, AC-008-36 | S |
| T-008-068d | Estructural caso G/H: almacén simple y almacén complejo de extremo a extremo | FR-008-017, 090, AC-008-37, 38 | M |
| T-008-068e | El bloqueo estructural se produce en backend aunque se invoque saltándose la UI | FR-008-093, AC-008-39 | S |
| T-008-061 | Regresión de `inventory`, `purchasing`, `sales`, `regulatory` y procesos | FR-008-054, plan §7 | L |
| T-008-061a | **Rendimiento**: 50.000 ubicaciones; búsqueda por código P95 ≤ 200 ms; consulta ordenada resuelta por índice verificado con `EXPLAIN` | NFR-008-01, NFR-008-03, AC-008-19, AC-008-20 | M |

## F6 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-070 | Tipos TypeScript de los 6 nodos y los 2 catálogos | FR-008-070 | S |
| T-008-071 | Lista de almacenes con búsqueda, filtros y resumen de estructura | FR-008-070 | M |
| T-008-072 | Alta y edición de almacén en pantalla completa | FR-008-071 | L |
| T-008-073 | Detalle con pestañas **solo de los tramos declarados** | FR-008-072, 078 | L |
| T-008-074 | Gestión de cada tramo con breadcrumb de la cadena | FR-008-073 | L |
| T-008-075 | Ubicaciones con búsqueda y vista de orden físico | FR-008-074 | L |
| T-008-076 | Creación masiva con vista previa | FR-008-075 | M |
| T-008-077 | Catálogos de tipos de zona y de ubicación | FR-008-011, 024 | M |
| T-008-078 | Sustituir `AlmacenesPage` y `UbicacionesPage` por páginas completas con URL propia | NFR-008-06, CL-008-14 | M |
| T-008-079 | Protección de cambios sin guardar | FR-008-076 | S |
| T-008-080 | Los 6 estados de UI con textos con sentido | FR-008-077 | S |
| T-008-081 | Rutas y entradas de menú con guardas de permiso | FR-008-064 | S |

## F7 · E2E y cierre

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-008-090 | E2E: los 12 casos del §48, con tramos opcionales | FR-008-070, AC-008-01..02, §48 | L |
| T-008-091 | E2E: almacén simple, sin tramos intermedios | FR-008-078, AC-008-01, HU-008-01 | M |
| T-008-092 | E2E: borrado protegido con referencia y bloqueo estructural visible | FR-008-093, AC-008-11, AC-008-40, HU-008-06 | S |
| T-008-093 | E2E: multiempresa | FR-008-052, AC-008-05, HU-008-09 | S |
| T-008-094 | Cross-browser en Chromium, Firefox y WebKit; WebKit no se reporta como Safari | AC-008-24, §49 | M |
| T-008-095 | axe WCAG 2.2 AA sobre las pantallas de 008 | NFR-008-04 | S |
| T-008-096 | Responsive 6 viewports sobre las pantallas de 008 | NFR-008-05 | S |
| T-008-097 | Puertas G1-G4 actualizadas con las rutas nuevas | NFR-008-04, NFR-008-05 | XS |
| T-008-098 | Verificación de contratos para 019, 022, 023, 025, 031, 032, 036 | FR-008-080..085 | M |
| T-008-099 | `/speckit.converge 008`, verificación de NFR-008-08 (0 literales de negocio) y artefactos de cierre | NFR-008-08, AC-008-22 | M |

## Resumen

| Fase | Tareas | Carga | Nota |
|---|---:|---|---|
| F1 Modelo | 11 | **L** | La coherencia de cadena es lo más delicado |
| F2 Conversión | 12 | **XL** | Va antes que la API por P23; incluye la clasificación de huérfanas (Control 1) |
| F3 Dominio | 18 | **XL** | Donde vive el valor; incluye el régimen de mutabilidad estructural (Control 2) |
| F4 API | 9 | L | — |
| F5 Pruebas | 24 | **XL** | Antes del frontend; 6 casos de migración, 5 estructurales y 1 de rendimiento, sobre PostgreSQL 18.x |
| F6 Frontend | 12 | **XL** | La jerarquía usable es el mayor riesgo de UX |
| F7 E2E y cierre | 10 | L | — |
| **Total** | **96** | — | +26 sobre el ciclo documental inicial: 25 de los dos controles y 1 de rendimiento que faltaba |
