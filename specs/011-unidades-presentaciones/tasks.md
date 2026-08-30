# TAREAS — SPEC 011

Tareas concretas y trazables (§103). No se agrupa en «implementar backend».

## F1 · Modelo de unidades

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-001 | `UnitOfMeasure`: `rounding_mode`, `version`, `CHECK` de dimensión y decimales | FR-011-001, 002, 006 | M |
| T-011-002 | `UNIQUE (company_id, code)` admitiendo global y de empresa | FR-011-005 | S |
| T-011-003 | Ámbito global de solo lectura para la empresa | FR-011-003 | M |
| T-011-004 | Verificar que el catálogo global nace **vacío**, sin seed | FR-011-004, AC-011-01 | XS |
| T-011-005 | `UnitConversion.factor` de `Float` a `NUMERIC(18,6)` con `CHECK (> 0)` | FR-011-011 | S |
| T-011-006 | Validación de dimensión compartida; la conversión física **no** sustituye a la presentación | FR-011-010, 012, 013 | M |
| T-011-007 | Reglas de borrado y desactivación de unidad | FR-011-007 | S |

## F2 · Presentaciones versionadas

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-010 | `Presentation`: `code`, `status`, `company_id`, `dispatchable`, `version` | FR-011-030, 031, 037 | M |
| T-011-011 | Conservar `content` legado sin usarlo para calcular | FR-011-030, CL-011-11 | XS |
| T-011-012 | `ProductPresentationVersion` con factor, vigencia y `exact_in_base` | FR-011-032, 033, 034, 038 | L |
| T-011-013 | Índice único parcial: una sola versión abierta por presentación | FR-011-035 | M |
| T-011-014 | Validación de no solapamiento entre rangos cerrados, en transacción | FR-011-035 | M |
| T-011-015 | Inmutabilidad de versión cerrada o en uso | FR-011-036 | M |
| T-011-016 | `base_unit_id` obligatoria en productos; opcional en servicios; cambio libre sin movimientos; producto sin presentaciones válido | FR-011-020, 021, 022, 024 | M |
| T-011-017 | `base_unit_locked`, irreversible con el primer movimiento | FR-011-023 | M |
| T-011-018 | Migración `00XX_uom_model` | FR-011-001..038, NFR-011-03 | L |

## F3 · Motor de conversión — autoridad única (P22)

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-020 | `uom.py`: módulo único de conversión | FR-011-040 | M |
| T-011-021 | `resolve_conversion(product, presentation, date)` | FR-011-041 | M |
| T-011-022 | `to_base(...)` devolviendo cantidad, factor y versión; el backend recalcula siempre y nunca acepta `base_quantity` del cliente | FR-011-042, 043, 051 | M |
| T-011-023 | Cadena presentación → unidad declarada → unidad base; admite cantidades decimales | FR-011-062, CL-011-13 | M |
| T-011-024 | Redondeo único según `decimals` y `rounding_mode` | FR-011-045 | M |
| T-011-025 | Rechazo de fracción no declarada (`CONVERSION_NOT_EXACT`) | FR-011-038 | S |
| T-011-026 | Fecha efectiva = fecha del documento; `occurred_at` como alterno | FR-011-041, AC-011-14 | S |
| T-011-027 | `to_base_bulk(...)` sin N+1 | FR-011-046, NFR-011-01 | L |
| T-011-028 | Caché **por petición**, nunca entre peticiones | NFR-011-02 | M |
| T-011-029 | `freeze(line)`: congela al emitir; recalcula mientras es borrador; cambiar la presentación de una línea emitida se rechaza; cambiar un factor no altera documentos ni saldos | FR-011-052, 053, 054, 055, AC-011-15 | M |

## F4 · Columnas transaccionales — antes que la API de consumo (P23)

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-030 | Migración `00XX_quantity_numeric`: 31 columnas `Float → NUMERIC` | FR-011-060, 061 | L |
| T-011-031 | Reporte de filas cuyo valor cambia al convertir el tipo | FR-011-063 | M |
| T-011-032 | 4 columnas + `uom_source` en las 6 tablas de `inventory` | FR-011-050, 056 | L |
| T-011-033 | Ídem en las 6 tablas de `purchasing`, con cantidades múltiples | FR-011-050 | L |
| T-011-034 | Ídem en las 6 tablas de `sales` | FR-011-050 | L |
| T-011-035 | `uom_id` en `permit_instances` (solo contrato) | FR-011-050, matriz §2 | XS |
| T-011-036 | Símbolo y etiqueta congelados en las 4 tablas de documento emitido | FR-011-057 | M |
| T-011-037 | Verificar que `inventory_balances`, `cost_layers` y `triple_matches` **no** los reciben | AC-011-23, CL-011-18 | XS |
| T-011-038 | Migración `00XX_line_uom_columns`, todas *nullable* | FR-011-050, 056, AC-011-23 | L |
| T-011-039 | Validación de coherencia `base = quantity × factor` | FR-011-064, AC-011-25 | M |

## F5 · Backfill clasificado

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-040 | Clasificador de las cuatro clases, sin escribir nada | FR-011-070 | L |
| T-011-041 | Clase A: unidad base del producto, factor 1 demostrado | FR-011-071 | M |
| T-011-042 | Clase B: reconstrucción con candidata **única** | FR-011-072 | M |
| T-011-043 | Clase C: `uom_id` nulo y marcada; **sin adivinar** | FR-011-073 | M |
| T-011-044 | Clase D: cero escrituras sobre líneas fiscales | FR-011-074 | M |
| T-011-045 | Bloqueo por umbral configurable | FR-011-075, ESC-011-01 | M |
| T-011-046 | Reporte con los once recuentos y su invariante | FR-011-076 | M |
| T-011-047 | Garantizar que `quantity` original nunca se modifica | FR-011-077 | S |
| T-011-048 | Migración `00XX_uom_backfill`, idempotente | FR-011-070..077, AC-011-32 | L |
| T-011-049 | `NOT NULL` diferido, condicionado a reporte limpio | FR-011-050, plan §9 | M |

## F6 · API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-050 | Endpoints de unidad, con ámbito global de solo lectura | FR-011-080 | M |
| T-011-051 | Endpoints de conversión física | FR-011-010 | S |
| T-011-052 | Endpoints de presentación por producto | FR-011-081 | M |
| T-011-053 | Endpoint de creación de versión; **sin** `PATCH` de versión | FR-011-081, 036 | M |
| T-011-054 | Previsualización de conversión, informativa; su resultado no vincula | FR-011-082, 044, AC-011-18 | S |
| T-011-055 | `allowed_actions` y `can_delete` en backend | FR-011-083 | M |
| T-011-056 | Los 15 códigos de error con `reason` y `dependencies`; factor inválido rechazado | FR-011-032, AC-011-09 | M |
| T-011-057 | Permisos con la convención vigente | FR-011-084 | S |
| T-011-058 | Auditoría transversal de los 9 eventos, incluidos los intentos denegados | FR-011-085, AC-011-39 | S |
| T-011-059 | `If-Match` con el mecanismo existente | FR-011-086 | S |
| T-011-060 | Aislamiento multiempresa en toda consulta y escritura | FR-011-087 | M |

## F7 · Pruebas de backend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-070 | Unidad: conversión, factor decimal, precisión, redondeo | AC-011-06, 07, 19 | L |
| T-011-071 | Unidad: selección de versión por fecha, incluidos los bordes | AC-011-13, 14 | M |
| T-011-072 | Unidad: inmutabilidad de versión y de snapshot | AC-011-22, 16 | M |
| T-011-073 | Unidad: unidad base bloqueada con movimientos | AC-011-20 | M |
| T-011-074 | Integración: los 10 casos del §87 **sobre PostgreSQL** | AC-011-02..05, NFR-011-07 | L |
| T-011-075 | Integración: producto simple y producto complejo | AC-011-05, 06 | M |
| T-011-076 | Integración: servicio sin unidad base | AC-011-04 | S |
| T-011-077 | **El histórico no cambia** al cambiar el factor | AC-011-11 | M |
| T-011-078 | Reimpresión fiel sin consultar el maestro | AC-011-17 | M |
| T-011-079 | Concurrencia: versión, edición, emisión, alta de código | AC-011-12, 40 | L |
| T-011-080 | Migración casos 1-3: determinista, reconstruible, ambigua | AC-011-26, 27, 28 | L |
| T-011-081 | Migración caso 4: fiscal irreconstruible **bloquea** | AC-011-29 | M |
| T-011-082 | Migración casos 5-6: idempotencia y base real pre-011 | AC-011-30, 32 | L |
| T-011-083 | Conversión de tipo: valor exacto, valor con error, sumas | AC-011-24, 31 | M |
| T-011-084 | Aislamiento multiempresa, invocando la API directamente | AC-011-33 | M |
| T-011-085 | Contrato: OpenAPI ↔ frontend, con serialización decimal | FR-011-080, 081, AC-011-08 | M |
| T-011-086 | Rendimiento: 1.000 líneas, **contando consultas** | AC-011-36, NFR-011-01 | M |
| T-011-087 | Caché que no sirve factores obsoletos | AC-011-37 | S |
| T-011-088 | Regresión de `inventory`, `purchasing`, `sales`, `maestros`, `fiscal` | FR-011-060, plan §7 | L |
| T-011-089 | Verificar autoridad única: 0 cálculos de conversión duplicados | AC-011-34 | S |

## F8 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-090 | Tipos TypeScript de unidad, presentación y versión | FR-011-090 | S |
| T-011-091 | Pantalla de unidades con búsqueda y filtros | FR-011-090 | L |
| T-011-092 | Alta y edición de unidad, con numéricos vacíos | FR-011-095 | M |
| T-011-093 | Presentaciones del producto, en página completa | FR-011-091 | L |
| T-011-094 | Formulario «Una CAJA equivale a ___ UND» | FR-011-092 | M |
| T-011-095 | Vista previa de conversión, informativa | FR-011-093 | M |
| T-011-096 | Historial de versiones, sin edición | FR-011-094 | M |
| T-011-097 | Producto sin presentaciones: pantalla limpia | FR-011-097 | S |
| T-011-098 | Selectores con búsqueda asíncrona | FR-011-096 | M |
| T-011-099 | Bloqueo de unidad base con el motivo del backend | FR-011-083 | S |
| T-011-100 | Protección de cambios sin guardar | NFR-011-06 | S |

## F9 · E2E y cierre

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-011-110 | E2E: los 11 pasos del §89 | AC-011-10, 11, 21 | L |
| T-011-111 | E2E: producto simple sin presentaciones | AC-011-05 | M |
| T-011-112 | E2E: el histórico conserva la versión anterior | AC-011-11 | M |
| T-011-113 | E2E: multiempresa | AC-011-33 | S |
| T-011-114 | Cross-browser en Chromium, Firefox y WebKit | AC-011-38 | M |
| T-011-115 | axe WCAG 2.2 AA sobre las pantallas de 011 | NFR-011-04 | S |
| T-011-116 | Responsive en 6 viewports | NFR-011-05 | S |
| T-011-117 | Puertas G1-G4 con las rutas nuevas | NFR-011-04, 05 | XS |
| T-011-118 | Verificación de contratos para las 14 Specs consumidoras | FR-011-100..105 | M |
| T-011-119 | Verificación de NFR-011-08: 0 literales de unidad | NFR-011-08, AC-011-35 | S |
| T-011-120 | `/speckit.converge 011`, verificación de NFR-011-08 y artefactos de cierre | NFR-011-08, AC-011-35 | M |

## Resumen

| Fase | Tareas | Carga | Nota |
|---|---:|---|---|
| F1 Unidades | 7 | M | Base de todo lo demás |
| F2 Presentaciones | 9 | **L** | El versionado es lo delicado |
| F3 Motor | 10 | **L** | Donde vive el valor |
| F4 Columnas | 10 | **XL** | 17 tablas + 31 columnas de tipo; va antes que el consumo por P23 |
| F5 Backfill | 10 | **XL** | La migración de mayor riesgo del proyecto |
| F6 API | 11 | L | — |
| F7 Pruebas | 20 | **XL** | Antes del frontend |
| F8 Frontend | 11 | L | 2 pantallas |
| F9 E2E y cierre | 11 | L | — |
| **Total** | **99** | — | — |
