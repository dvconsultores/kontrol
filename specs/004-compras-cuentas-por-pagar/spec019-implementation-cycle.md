# SPEC 019 — RECEPCIÓN FÍSICA · CICLO SPECKIT PREVIO AL CÓDIGO

| Campo | Valor |
|---|---|
| Autorización | `SPEC 019 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-03) |
| Base | `01987ff` · `OPERATIONAL CHAIN — DEPENDENCY MAP CONVERGED` |
| Baseline remedida | PostgreSQL 18.6 (UTC) · 177 modelos · 177 tablas · 43 migraciones (cabeza `0043_spec030_reservation`) · 373 FK · 318 rutas · 437 operaciones · 375 con contrato de empresa |
| Fuente autoritativa del proceso | `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, §2 «Recepción de la importación» |

---

## Reconciliación documental previa: no son diez etapas, son doce

Los artefactos de hoja de ruta repiten «Recepción física (10 etapas), 3 cubiertas»
(`functional-debt-roadmap.md` DF-02, `requirements-to-specs-map.md`,
`KONTROL_GAP_ANALYSIS_ROADMAP_MAESTRO.md`, `master-56-specs-status.md`). La matriz de procesos
(`processes-to-specs-map.md` P-04) lista **nueve** filas.

Leído el DOCX que todos citan, §2 tiene **doce** etapas de primer nivel. La cifra 10 y la tabla de 9
son resúmenes que se copiaron entre documentos sin volver a la fuente. Este ciclo reconcilia la
cifra y la deja escrita: **12 etapas**, de las cuales 019 posee **8**.

| # | Etapa (DOCX §2, literal) | Owner | Estado hoy |
|---:|---|---|---|
| 1 | Confirmar arribo de la mercancía | **019** | ✖ ausente |
| 2 | Programar descarga y recepción | **019** | ✖ ausente |
| 3 | Recibir físicamente | **019** | ◐ hay recepción contable; sin bultos ni unidad real |
| 4 | Comparar físicamente lo recibido contra *packing list*, factura, orden de compra y documentación de recepción | **019** | ◐ solo contra la orden |
| 5 | Realizar inspección visual inicial | **019** | ◐ `quality_status` binario |
| 6 | Validar cantidad de bultos, estado físico, daños visibles, identificación y referencias | **019** | ✖ ausente |
| 7 | Determinar si la recepción es conforme | **019** | ◐ implícito en aceptar/rechazar |
| 8 | Si existen diferencias, registrar faltantes, sobrantes, daños, referencias incorrectas y diferencias documentales | 020 | ✖ |
| 9 | Generar evidencia de la incidencia | 020 · 046 | ✖ |
| 10 | Escalar la novedad a Compras | 020 · 047 | ✖ |
| 11 | Si la recepción es conforme, generar acta o registro de recepción | **019** | ◐ el registro existe; no hay acta emitida |
| 12 | Colocar la mercancía temporalmente en zona de recepción o validación | 022 | ✖ — cubierta conceptualmente por el invariante «almacén conocido, ubicación nula» del checkpoint operativo |

**Cobertura de 019: 3 parciales y 1 implícita de 8.** La cifra «3/10» del roadmap se corregirá a
«4 de 8 parciales, 12 etapas totales» en los artefactos de hoja de ruta.

---

## Los siete proveedores, enumerados desde el grafo

Tomados de `operational-chain-capability-matrix.md`, filas de 019. Ninguno se cita de memoria.

| # | Capacidad requerida | Proveedor | Estado | Evidencia | ¿Satisfecha? |
|---:|---|---|---|---|---|
| 1 | Orden de compra aprobada con líneas | 017 | PARTIAL | `purchase_orders`, `purchase_order_lines`, transiciones | **Sí** |
| 2 | Producto de catálogo | 010 | PARTIAL | `catalog_items` | **Sí** |
| 3 | Almacén de la empresa | 008 | COMPLETE | `warehouses` + `warehouse_locations` | **Sí** |
| 4 | Motor de entrada al ledger | 023 | PARTIAL | `record_movement`, `InventoryMovement`, `InventoryBalance` | **Sí** |
| 5 | Lote y serial materializables | 024 | PARTIAL | `inventory_lots`, `product_serials`, `create_lot`, `create_serial` | **Sí** |
| 6 | Conversión a unidad base | 011 | COMPLETE | `uom.to_base`, columnas en `goods_receipt_lines` | **Sí** como motor · **no consumida** |
| 7 | Evidencia documental | 046 | RECONVERGED | `documents`, `DocumentLink`, 23 tipos de recurso | **Sí** |

Aprobaciones (045) aparece en el grafo como proveedor disponible, no como requisito de 019: ninguna
etapa del DOCX §2 asignada a 019 exige aprobación. El tratamiento de las diferencias —lo único que
podría exigirla— es de 020/021.

---

## `/speckit.specify`

**Solicitud.** Cerrar las etapas del DOCX §2 que pertenecen a 019, con énfasis en los datos que solo
se conocen mientras la mercancía está en el muelle, y eliminar el riesgo de que el asiento de
inventario registre la cantidad tecleada en lugar de la cantidad base.

**Fuera de alcance, con dueño.** Registro y resolución de incidencias (020). Confirmación y
conciliación de inventario, liberación formal y estados no vendibles del saldo (021 + capacidad de
023). Ubicación final y put-away (022). Cola, ruta, picking y consolidación (031/032). Importación
como expediente (018).

### Requisitos

Se reconcilian los FR-004-030..035 vigentes de la recepción y se añaden los propios de 019 como
**IMP-019-001..048** según la autorización, más los siguientes, que salen del DOCX y no del prompt:

| Id | Requisito | Etapa |
|---|---|---|
| FR-019-001 | La recepción registra el arribo confirmado: momento y quién lo confirma | 1 |
| FR-019-002 | La recepción registra la descarga programada | 2 |
| FR-019-003 | La línea de recepción captura unidad, presentación, factor congelado y cantidad base de las tres cantidades | 3 |
| FR-019-004 | La recepción registra las referencias contra las que se comparó y el resultado de cada comparación: *packing list*, factura del proveedor, orden de compra y documentación | 4 |
| FR-019-005 | La recepción registra la inspección visual: momento y quién la realiza | 5 |
| FR-019-006 | La recepción registra los bultos declarados y los contados | 6 |
| FR-019-007 | La línea registra la observación física: estado, cantidad dañada observada, descripción del daño, identificación correcta y referencia correcta | 6 |
| FR-019-008 | La recepción registra su conformidad y no la deduce | 7 |
| FR-019-009 | Una recepción conforme emite su acta con momento y responsable | 11 |
| FR-019-010 | El asiento de inventario usa la cantidad base, nunca la tecleada cuando difieren | 3 |
| FR-019-011 | La observación física sobrevive aunque después la Spec 020 procese la incidencia | 6, 8 |
| FR-019-012 | Un sobrante respecto a la orden se registra como hecho observado; su tratamiento es de 020 | 6, 8 |
| FR-019-013 | Aceptar dos veces no duplica movimiento ni cantidad recibida | — |
| FR-019-014 | Dos aceptaciones concurrentes sobre la misma línea de orden no pierden una acumulación | — |

---

## `/speckit.clarify` — 36 respuestas con evidencia

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Cuáles son las etapas documentadas? | Doce, listadas arriba desde el DOCX §2 |
| 2 | ¿Cuáles están implementadas? | Parcialmente 3, 4, 5 y 11; el resto de 019 ausente |
| 3 | ¿Cuáles faltan? | 1, 2, 6 completas; 3, 4, 5, 11 a completar |
| 4 | ¿Todas las faltantes son de 019? | Sí: 8, 9 y 10 son de 020 y la 12 de 022 |
| 5 | Modelo `GoodsReceipt` | empresa, orden, almacén, `code`, `status`, `quality_status` |
| 6 | Modelo `GoodsReceiptLine` | recepción, línea de orden, producto, tres cantidades, lote, `lot_number`, vencimiento, seriales (texto), `quality`, y las columnas de unidad de Spec 011 **sin escribir** |
| 7 | Estados de la recepción | `DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED / PARTIALLY_ACCEPTED / REJECTED → CLOSED`; `CANCELLED` desde borrador |
| 8 | ¿Qué significa aceptar? | Exige `quality_status = APPROVED`; crea lote y seriales; registra `ENTRADA_RECEPCION`; acumula recibido en la línea de orden; sincroniza el estado de la orden |
| 9 | ¿Qué documentos origen admite? | Solo orden de compra: `GoodsReceipt.order_id` es obligatorio |
| 10 | ¿La orden es obligatoria? | Sí, hoy y en este ciclo. Recepción sin orden no está documentada |
| 11 | ¿La recepción de importación es de 019 o de 018? | El expediente de importación es de 018 (`NOT_STARTED`). La recepción física de esa mercancía es de 019 y no requiere 018 |
| 12 | ¿Cómo se identifica la línea fuente? | `GoodsReceiptLine.order_line_id`, clave foránea real |
| 13 | ¿Pedido contra recibido? | `accept_receipt` acumula en `order_line.quantity_received`; no compara contra lo pedido |
| 14 | ¿Tolerancia de sobrante o faltante? | **No hay ninguna documentada.** El DOCX manda *registrar* faltantes y sobrantes, no impedirlos |
| 15 | ¿Quién decide un sobrante? | 020 (registro y escalamiento) y 021 (tratamiento). 019 solo lo observa y lo marca |
| 16 | ¿Qué campos de unidad existen? | `uom_id`, `uom_source` |
| 17 | ¿Y de presentación? | `presentation_id` |
| 18 | ¿Y de factor? | `conversion_factor_snapshot` |
| 19 | ¿Y de cantidad base? | `base_quantity_received`, `base_quantity_accepted`, `base_quantity_rejected` |
| 20 | ¿Qué código no las escribe? | `add_receipt_line` no las asigna y `ReceiptLineCreate` no las admite. Las creó la migración `0021` y la `0022` rellenó lo histórico |
| 21 | ¿Qué debe cambiar en `record_movement`? | Nada en el motor: ya admite `presentation_id`. Lo que cambia es que `accept_receipt` debe pasarla |
| 22 | ¿Qué exige el contrato sobre bultos? | «Validar: cantidad de bultos» (etapa 6). Declarados y contados |
| 23 | ¿Qué información física de daño es de 019? | «estado físico; daños visibles; identificación; referencias» (etapa 6): la observación |
| 24 | ¿Qué parte del daño es de 020? | Clasificar la incidencia, adjuntar su evidencia, escalarla y resolverla (etapas 8, 9, 10) |
| 25 | ¿Quién captura el lote? | 019, y ya lo hace |
| 26 | ¿Y el serial? | 019, y ya lo hace |
| 27 | ¿Y el vencimiento? | 019, y ya lo hace |
| 28 | ¿Qué documentos exige la recepción? | Los de comparación (etapa 4) como referencia, y el acta (etapa 11). Los adjuntos van por 046, que ya declara `GoodsReceipt` como recurso enlazable |
| 29 | ¿La base admite ubicación nula? | Sí: `InventoryBalance.location_id` y `InventoryMovement.location_id` son anulables con clave foránea real |
| 30 | ¿Qué estado de inventario se escribe hoy? | `DISPONIBLE`, fijo en el motor |
| 31 | ¿Qué comportamiento se conserva hasta 021? | Ese mismo. 019 no crea un motor de estados paralelo |
| 32 | ¿Qué pruebas demuestran la aceptación? | `test_purchasing.py::test_receipt_accept_updates_inventory_via_003`, `test_receipt_requires_approved_order`, `test_qa_fixes.py::test_receipt_accept_autoseeds_movement_type_and_updates_stock` |
| 33 | ¿Qué rutas existen? | listar, crear, añadir línea, confirmar, calidad, aceptar |
| 34 | ¿Qué frontend existe? | `RecepcionesPage`: una tabla de cinco columnas y tres botones. **No permite capturar líneas** |
| 35 | ¿Qué permisos? | `compras:create` para crear y añadir líneas; `compras:quality` para calidad y aceptar |
| 36 | ¿Qué contrato de idempotencia y concurrencia hay? | Ninguno propio: la máquina de estados impide la doble aceptación, pero la acumulación en la línea de orden es lectura-modificación-escritura sin bloqueo |

**Ninguna decisión material nueva.** Las tres candidatas están cerradas por contrato: ubicar es de
022, el momento de la disponibilidad es de 021 más capacidad de 023, y el flujo de incidencias es de
020.

---

## `/speckit.plan` — olas

| Ola | Contenido |
|---|---|
| 1 | Baseline y auditoría forense (hecha) |
| 2 | Reconciliación de las doce etapas (hecha) |
| 3 | Modelo: cabecera de arribo, comparación, inspección, bultos, conformidad y acta; línea con observación física |
| 4 | Contrato de captura P23 |
| 5-6 | Integración con Spec 011: unidad, presentación, factor congelado y cantidad base |
| 7 | Bultos y observaciones físicas |
| 8 | Lote, serial y vencimiento: ya son de 019; se preservan |
| 9 | Migración `0044` |
| 10 | Paridad ORM = Alembic = PostgreSQL |
| 11 | Servicios de recepción |
| 12 | Aceptación con cantidad base |
| 13 | Idempotencia y concurrencia de la aceptación |
| 14 | Documentos (046) donde el contrato lo exige |
| 15 | Permisos y auditoría |
| 16 | API y OpenAPI |
| 17 | Frontend con captura real |
| 18 | Seguridad multiempresa |
| 19 | Pruebas hostiles en PostgreSQL |
| 20 | Invariancia histórica |
| 21 | Fronteras con 020, 021 y 022 |
| 22 | Instalación limpia |
| 23 | Regresión completa |
| 24 | Convergencia |

---

## CONSTITUTION GATE

| Validación | Resultado |
|---|---|
| Constitución (P5 histórico, P8 sin política codificada, P21 PostgreSQL, P23 captura temprana) | PASS |
| ARCH-MC-001 | PASS: contexto autoridad, cadena padre bajo empresa, cuerpo sin `company_id` |
| Checkpoint de la cadena operativa | PASS: no se absorben 020, 021, 022, 031 ni 032 |
| Spec 008 | PASS: no se asigna ubicación |
| Spec 010 | PASS |
| Spec 011 | PASS: `to_base` es la única autoridad; el factor se congela |
| Spec 017 | PASS: la orden es el documento origen |
| Spec 023 | PASS: se consume el motor; no se crea otro ni se toca el estado del saldo |
| Spec 024 | PASS: se reutilizan lote y serial |
| Spec 045 | PASS: ninguna etapa de 019 exige aprobación; no se crea motor local |
| Spec 046 | PASS: los adjuntos van por documentos, sin almacenamiento paralelo |
| Estándar de frontend | PASS |
| Sin segundo motor de inventario, unidad, presentación ni aprobaciones | PASS |
| Invariante de ubicación nula preservado | PASS |

**CONSTITUTION GATE: PASS**

---

## `/speckit.checklist`

Los 40 ítems de la autorización quedan cubiertos por las olas 1-21 y se marcan con evidencia en
`checklist.md` §SPEC 019 al cerrar.

## `/speckit.tasks`

T-019-I-001..060 según la autorización, ajustadas a los requisitos reales: la 021 (backfill) se
resuelve midiendo primero, y la 030 (aprobaciones) queda **no aplicable** porque ninguna etapa de
019 la exige.

## `/speckit.analyze`

| Detección | Resultado |
|---|---|
| Requisito sin tarea · tarea sin requisito | 0 · 0 |
| Etapa sin dueño | 0: las doce tienen dueño |
| Etapa de 020, 021 o 022 absorbida | 0 |
| Cantidad tecleada sin unidad | **existe hoy** → olas 5-6 |
| Presentación no persistida | **existe hoy** → olas 5-6 |
| Factor no congelado | **existe hoy** → ola 6 |
| Cantidad base ausente | **existe hoy** → ola 6 |
| `record_movement` con cantidad tecleada | **existe hoy** → ola 12 |
| Histórico que consulta el factor actual | no |
| Observación de daño perdida | **existe hoy** → ola 7 |
| Bultos no capturados | **existe hoy** → ola 7 |
| Lote, serial o vencimiento diferidos | no: los captura 019 |
| Empresa, padre o almacén cruzados | no |
| Ubicación final asignada | no |
| Flujo de incidencias creado | no |
| Confirmación de inventario creada | no |
| Segundo motor de inventario o de aprobaciones | no |
| Aceptación o movimiento duplicados | **riesgo hoy** → ola 13 |
| Desajuste ORM contra migración | no |
| Frontend sin unidad ni presentación | **existe hoy** → ola 17 |
| Pruebas verdes por causa equivocada | revisión caso a caso |

BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0.

**Autorización expresa satisfecha: se procede a `/speckit.implement`.**
