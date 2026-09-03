# MATRIZ DE TRAZABILIDAD — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-004-001 | FR-004-001, FR-004-002 |
| US-004-002 | FR-004-010, FR-004-011 |
| US-004-003 | FR-004-012 |
| US-004-004 | FR-004-020, FR-004-021, FR-004-022, FR-004-023 |
| US-004-005 | FR-004-030, FR-004-031, FR-004-032, FR-004-033, FR-004-034 |
| US-004-006 | FR-004-040, FR-004-041, FR-004-042, FR-004-043 |
| US-004-007 | FR-004-050, FR-004-051, FR-004-052 |
| US-004-008 | FR-004-060, FR-004-061 |
| US-004-009 | FR-004-070, FR-004-071, FR-004-072, FR-004-075 |
| US-004-010 | FR-004-073, FR-004-074, FR-004-076 |
| US-004-011 | FR-004-075 |
| US-004-012 | FR-004-041 |
| US-004-013 | FR-004-104, FR-004-100 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-004-001/002 | T-004-001 | Test de flujo |
| FR-004-010/011/012 | T-004-002 | Test de comparación |
| FR-004-020/021/022/023 | T-004-003 | Test de máquina/aprobación |
| FR-004-030/031/032/033/034 | T-004-004 | Test de integración 003 |
| FR-004-040/041/042/043 | T-004-005 | Test de duplicidad |
| FR-004-050/051/052 | T-004-006 | Test de diferencias |
| FR-004-060/061 | T-004-007 | Test de nota/CxP |
| FR-004-070/071/104 | T-004-008 | Test de saldo |
| FR-004-072/101 | T-004-009 | Test de pago/idempotencia |
| FR-004-073 | T-004-010 | Test de aplicación/saldo |
| FR-004-074/075 | T-004-011 | Test de aging/anticipo |
| FR-004-076/078 | T-004-012 | Test de retención |
| FR-004-077 | T-004-013 | Test de permisos |
| FR-004-103 | T-004-014/015 | Contract test |
| FR-004-100 | T-004-023 | Pytest negativo |
| NFR concurrencia | T-004-024 | Pytest de concurrencia |
| NFR accesibilidad | T-004-025 | axe |
| CHK-004-DB-007 | T-004-026 | CI migración |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |

---

# TRAZABILIDAD — SPEC 019 · RECEPCIÓN FÍSICA

Formato: `| Requirement | Stage | P23/Normal | Plan | Task | Schema/Code | Test | Evidence | Status |`.
Abreviaturas: **M** `0044_spec019_receipt` · **SVC** `purchasing/service.py` · **INV**
`inventory/service.py` · **API** `purchasing/api.py` · **FE** `RecepcionesPage.tsx` · **T-R**
`test_spec019_receipt.py` · **T-A** `test_spec019_architecture.py` · **T-M**
`test_spec019_migration_0044.py`.

## Dato por dato

| Requirement | Stage | P23 | Plan | Task | Schema/Code | Test | Status |
|---|---|---|---|---|---|---|---|
| Cantidad tecleada | 3 | normal | ola 5 | I-009 | `quantity_received/accepted/rejected` | T-R cajas | ✔ |
| Unidad | 3 | **P23** | ola 5 | I-009 | `uom_id`, SVC `_unidad_recibida` | T-R cajas · T-A unidad | ✔ |
| Presentación | 3 | **P23** | ola 5 | I-010 | `presentation_id`, API, FE | T-R cajas | ✔ |
| Factor congelado | 3 | **P23** | ola 6 | I-011 | `conversion_factor_snapshot` | T-R invariancia | ✔ |
| Cantidad base | 3 | **P23** | ola 6 | I-012 | tres `base_quantity_*`; INV saldo en base | T-R cajas · T-A saldo | ✔ |
| Bultos | 6 | **P23** | ola 7 | I-013 | `packages_declared/received` | T-R arribo · T-R negativos | ✔ |
| Observación de daño | 6 | **P23** | ola 7 | I-015 | `physical_condition`, `damaged_quantity`, `damage_notes` | T-R muelle · T-R daño máximo | ✔ |
| Identificación y referencia | 6 | **P23** | ola 7 | I-014 | `identification_ok`, `reference_ok` | T-R muelle | ✔ |
| Sobrante observado | 6, 8 | **P23** | ola 7 | I-028 | `overage_base_quantity`, SVC `_sobrante_observado` | T-R sobrante | ✔ |
| Lote | 3 | **P23** | ola 8 | I-016 | `lot_number` → `InventoryLot` | T-R lote | ✔ |
| Serial | 3 | **P23** | ola 8 | I-017 | `serials` normalizado → `ProductSerial` | T-R lote · T-A seriales | ✔ |
| Vencimiento | 3 | **P23** | ola 8 | I-018 | `expiry_date` → lote | T-R lote | ✔ |
| Arribo | 1 | **P23** | ola 3 | I-023 | `arrival_at`, `arrival_confirmed_by`, API `/arrival` | T-R arribo | ✔ |
| Descarga programada | 2 | normal | ola 3 | I-023 | `unloading_scheduled_at` | T-R arribo | ✔ |
| Comparación documental | 4 | normal | ola 3 | I-023 | 2 referencias + 4 resultados, API `/inspection` | T-R inspección | ✔ |
| Inspección | 5 | **P23** | ola 3 | I-023 | `inspected_at/by`, `inspection_notes` | T-R inspección | ✔ |
| Conformidad | 7 | normal | ola 3 | I-006 | `quality_status` (sin duplicar) | T-A sin duplicado | ✔ |
| Acta | 11 | normal | ola 12 | I-025 | `record_issued_at/by` | T-R acta | ✔ |
| Aceptación | — | normal | ola 12 | I-025/026 | SVC `accept_receipt` | T-R acta · T-R doble | ✔ |
| Movimiento en base | — | normal | ola 12 | I-026 | INV `record_movement` | T-R cajas · T-A saldo | ✔ |
| Empresa | — | normal | ola 18 | I-039 | cadena `_owned` | T-R AB · T-R tenant | ✔ |
| Almacén | — | normal | ola 18 | I-039 | `warehouse_belongs_to` | T-R almacén ajeno | ✔ |
| Ubicación nula | — | normal | ola 21 | I-044 | `location_id=None` en el asiento | T-R cajas · T-A frontera | ✔ |
| Frontera 020 | — | — | ola 21 | I-046 | sin flujo de incidencias | T-A frontera | ✔ |
| Frontera 021 | — | — | ola 21 | I-047 | sin estados de mercancía nuevos | T-R acta · T-A frontera | ✔ |
| Frontera 022 | — | — | ola 21 | I-045 | sin ubicación ni preparación | T-R acta | ✔ |
| Idempotencia de aceptar | — | normal | ola 13 | I-027 | máquina de estados | T-R doble | ✔ |
| Concurrencia de acumulación | — | normal | ola 13 | I-027 | `with_for_update()` | T-A bloqueo | ✔ |
| Migración sin inventar | — | **P23** | ola 9 | I-021 | M | T-M (6 casos) | ✔ |
| Paridad ORM = Alembic = PostgreSQL | — | normal | ola 10 | I-022 | `CheckConstraint` en ambos | T-A restricciones · T-M nombres | ✔ |
| OpenAPI | — | normal | ola 16 | I-034 | 3 rutas nuevas | fixture regenerado | ✔ |
| Frontend | — | normal | ola 17 | I-035..038 | FE | `tsc`, ESLint, build, 283/283 | ✔ |

## Los siete proveedores, al cerrar

| Proveedor | Capacidad | ¿Sigue satisfecha? |
|---|---|---|
| 017 órdenes de compra | orden aprobada con líneas | sí |
| 010 productos | catálogo | sí |
| 008 almacenes | almacén de la empresa | sí |
| 023 inventario | motor de entrada | sí, **con una corrección mínima**: el saldo acumula la cantidad base |
| 024 lotes y seriales | materialización | sí |
| 011 unidades | `to_base` | sí, **y ahora consumida** |
| 046 documentos | evidencia | sí, disponible; ninguna etapa de 019 la exige como obligatoria |

**Cobertura: 100 %. Huérfanos: 0.**

---

# TRAZABILIDAD — SPEC 020 · INCIDENCIAS DE RECEPCIÓN

Formato: `| Requirement | Process Stage | Type/Resolution | Plan | Task | Code | Test | Evidence | Status |`.
Abreviaturas: **M** `0045_spec020_incidents` · **SVC** `purchasing/service.py` · **API**
`purchasing/api.py` · **FE** `IncidenciasPage.tsx` · **T-F** `test_spec020_incidents.py` · **T-A**
`test_spec020_architecture.py` · **T-M** `test_spec020_migration_0045.py`.

## Elemento por elemento

| Elemento | Etapa | Tipo / Tratamiento | Código | Prueba | Status |
|---|---|---|---|---|---|
| Identidad de la incidencia | 8 | — | `ReceiptIncident`, código único por empresa | T-M código único | ✔ |
| Recepción padre | 8 | — | FK + `_owned` | T-F cadena · T-A api | ✔ |
| Línea de recepción | 8 | los cuatro de mercancía | FK, validada contra la recepción | T-F línea ajena · T-M FK | ✔ |
| Producto | 8 | — | **no se duplica**: sale de la línea | T-A sin duplicados | ✔ |
| Tipo de incidencia | 8 | los cinco literales | enumerado + `CHECK` | T-F cinco tipos · T-M tipo inventado | ✔ |
| Cantidad afectada | 8 | mercancía | `Numeric(18,6)`, en base | T-F topes · T-M no positiva | ✔ |
| Unidad y cantidad base | 8 | — | del snapshot de la línea; no se recalcula | T-F P23 | ✔ |
| Tope por tipo | 8 | faltante ≠ resto | `_tope_de_cantidad` | T-F faltante · T-F tope | ✔ |
| Acumulado por línea y tipo | 8 | — | `_afectado_vivo` bajo bloqueo | T-F acumulación · T-A bloqueo | ✔ |
| Evidencia | 9 | — | Spec 046, recurso `ReceiptIncident` | T-F evidencia · T-A registro | ✔ |
| Escalamiento | 10 | — | `escalar_incidencia` | T-F escalar | ✔ |
| Ciclo de vida | — | — | `INCIDENT_TRANSITIONS` | T-A ciclo · T-F doble resolución | ✔ |
| Tratamiento | §3 | los cuatro literales | enumerado + `CHECK` | T-F tratamiento · T-M inventado | ✔ |
| Motivo | §3 | — | obligatorio en resolver y anular | T-F sin motivo | ✔ |
| Aprobación | control 115 | solo `AJUSTE_AUTORIZADO` | Spec 045, `RECEIPT_INCIDENT` | T-F ajuste · T-A un solo punto | ✔ |
| Sin política de aprobación | — | — | el motor no exige nada | T-F sin política | ✔ |
| Resolución idempotente | — | — | máquina de estados + bloqueo | T-F doble resolución | ✔ |
| Anulación | — | — | libera la cantidad | T-F anular | ✔ |
| Resultado para la 021 | §3 | — | `resultado_de_incidencias` | T-F resultado · T-A estructurado | ✔ |
| Camino feliz sin incidencia | 16 del encargo | — | ninguna creación automática | T-F camino feliz | ✔ |
| Sin efecto en inventario | — | — | ninguna llamada al motor | T-F sin inventario · T-A fronteras | ✔ |
| Empresa | — | — | `company_id` directo, no anulable | T-A alcance · T-F AB | ✔ |
| Usuario AB · cross-tenant · cadena cruzada | — | — | `_owned_incident` | T-F tres pruebas | ✔ |
| Cuerpo estricto | — | — | `extra="forbid"` | T-F cuerpo | ✔ |
| Auditoría | — | — | tres eventos con empresa, tenant, línea, producto y cantidad | T-F auditoría | ✔ |
| Paridad ORM = Alembic = PostgreSQL | — | — | seis `CHECK` en ambos | T-A restricciones · T-M catálogo | ✔ |
| OpenAPI | — | — | 8 operaciones nuevas | fixture regenerado | ✔ |
| Frontend | — | — | FE con ruta y menú | `tsc`, ESLint, build, 285/285 | ✔ |

## Los IMP del encargo

| Rango | Garantía | Dónde |
|---|---|---|
| 001-006 | empresa, contexto, cuerpo, recepción y línea padres | `_owned_incident`, `registrar_incidencia` |
| 007-008 | tres etapas cubiertas; sin incidencia de camino feliz | ciclo · T-F camino feliz |
| 009-010 | tipos del catálogo, sin inventar | enumerado + `CHECK` |
| 011 | evidencia P23 referenciada, no reescrita | sin columnas duplicadas |
| 012-015 | precisión, base consistente, sin recálculo, tope | `Numeric`, snapshot, `_tope_de_cantidad` |
| 016-020 | tratamientos por estado, terminal única, idempotencia, motivo y actor | `INCIDENT_TRANSITIONS`, bloqueo |
| 021-024 | 045 y 046 sin motores paralelos | integración + registro cerrado |
| 025-030 | resultado para 021; sin confirmación, sin estados, sin put-away, sin ubicación, sin picking | `resultado_de_incidencias` · guardias |
| 031-034 | cross-company, cross-tenant, AB, permiso ≠ empresa | T-F multiempresa |
| 035-037 | auditoría completa | `_audit` en los tres eventos |
| 038-039 | ciclo explícito, terminales inmutables | `INCIDENT_TRANSITIONS` |
| 040-044 | OpenAPI, contexto, doble envío, formulario sucio, sin 500 | API + FE + contratos de error |
| 045-048 | paridad, cero fallos inesperados, trazabilidad, sin deuda P0 | convergencia |

**Cobertura: 100 %. Huérfanos: 0.**

## Adenda tras la corrida de extremo a extremo

Dos elementos se añadieron después de la primera regresión, porque la prueba contra el producto real
encontró lo que las suites aisladas no podían ver.

| Elemento | Qué cubre | Código | Prueba | Status |
|---|---|---|---|---|
| Insertabilidad de la tabla migrada | `created_at`/`updated_at` nacen con `server_default`, como en el resto del repositorio | M | T-M insert del ORM contra la tabla de Alembic | ✔ |
| Nombre accesible de los selectores | El nombre que anuncia el lector de pantalla es la etiqueta visible (WCAG 2.5.3) | FE y otras cuatro páginas del bloque | E2E incidencias · axe | ✔ |

**Cobertura: 100 %. Huérfanos: 0.**
