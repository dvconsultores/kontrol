# CHECKPOINT DE LA CADENA OPERATIVA — 019 → 020 → 021 → 022 → 031 → 032

| Campo | Valor |
|---|---|
| Fecha | 2026-09-03 |
| Base medida | `9af45bb` (`SPEC 030 — COMPLETE / CONVERGED`) |
| Alcance | Documental y de gobierno. **Cambios de código productivo: 0** |
| Veredicto | `OPERATIONAL CHAIN — DEPENDENCY MAP CONVERGED / NEXT SPEC SELECTED` |

---

## Baseline remedida

| Métrica | Valor |
|---|---:|
| PostgreSQL | 18.6 |
| Modelos · tablas | 177 · 177 |
| Migraciones (cabeza `0043_spec030_reservation`) | 43 |
| Claves foráneas | 373 |
| Rutas · operaciones | 318 · 437 |
| Operaciones con contrato de empresa | 375 |

Ningún estado de este documento procede de un informe anterior. Los informes son entrada; el
repositorio es la evidencia.

---

## `/speckit.specify` — alcance del checkpoint

**Requisitos.** FR-OP-001..020 según el encargo. Se trazan uno a uno en
`operational-chain-traceability.md`.

**Incluido.** Estado real de 019, 020, 021, 022, 031 y 032; capacidades que cada una consume y de
quién; capacidades que los proveedores (008, 010, 011, 023, 024, 029, 030, 045, 046) entregan hoy;
punto en que la mercancía se vuelve vendible; semántica de la ubicación nula; comportamiento del
movimiento de recepción; propiedad de la captura de lote, serial y vencimiento; camino feliz y
camino con incidencia; grafo de capacidades; reconciliación de bloqueos; ruta crítica; ranking de
preparación; selección de una Spec.

**Excluido.** Implementar cualquiera de las seis. Corregir el movimiento de recepción. Corregir el
guardia dependiente del idioma del preflight. Crear una Spec nueva. Cambiar la numeración maestra.
Redefinir lo que hace la reserva (D0-03 está cerrada).

---

## `/speckit.clarify` — 30 preguntas, cada una con evidencia

| # | Pregunta | Respuesta medida |
|---|---|---|
| 1 | Estado real de 019 | `PARTIALLY_IMPLEMENTED`. Existe la recepción **contable** completa; falta la **física** |
| 2 | Estado real de 020 | `NOT_STARTED`. Cero tablas de incidencia. Solo `quantity_rejected` y `quality` en la línea |
| 3 | Estado real de 021 | `PARTIALLY_IMPLEMENTED` (esqueleto). Existe la compuerta `quality_status` en `accept_receipt`; no existe conciliación ni liberación formal |
| 4 | Estado real de 022 | `NOT_STARTED`. Cero proceso. La estructura física de 008 existe y la cadena de entrada no la usa |
| 5 | Estado real de 031 | `BLOCKED_BY_DEPENDENCY`. `pick_lists` y `pick_list_lines` existen; la línea **no tiene ubicación ni secuencia**; `create_picklist` recibe las líneas del llamante y no calcula ruta |
| 6 | Estado real de 032 | `BLOCKED_BY_DEPENDENCY`. Esqueleto en `sales`: `Shipment`/`ShipmentLine` y confirmación de despacho; sin almacenista, diferencia, daño ni consolidación |
| 7 | ¿020 necesita 019 completa o una capacidad concreta? | Una capacidad concreta: que exista una recepción identificable, con líneas, cantidades recibida/aceptada/rechazada y máquina de estados sobre la que colgar la incidencia |
| 8 | ¿Esa capacidad existe? | **Sí.** `GoodsReceipt` (empresa, orden, almacén, estado, calidad) y `GoodsReceiptLine` (línea de orden, producto, tres cantidades, lote, vencimiento, seriales, calidad) |
| 9 | ¿021 necesita 020 siempre o solo en el camino de excepción? | **Solo en el camino de excepción.** Una recepción sin discrepancia se confirma sin crear ninguna incidencia. La dependencia es de capacidad, no de registro obligatorio |
| 10 | ¿022 requiere 021 completa o una capacidad de confirmación? | Una capacidad: mercancía confirmada con empresa, almacén, producto, cantidad base y estado de origen inequívoco |
| 11 | ¿031 requiere 022 completa? | Requiere su **capacidad**: existencia ubicada y cantidad por ubicación. Hoy no existe ninguna de las dos |
| 12 | ¿032 requiere 031 completa? | Requiere cola y ruta: sin secuencia de recorrido no hay ejecución que seguir |
| 13 | ¿Qué necesita 032 de 024? | Lote, serial y vencimiento como dato consultable. `inventory_lots` (con `expiry_date` y estado) y `product_serials` existen. La **selección** FEFO/FIFO es alcance propio de 032 |
| 14 | ¿Existencia sin ubicación es legítima entre recepción y put-away? | **Sí, y es el estado real hoy.** `InventoryBalance.location_id` es anulable con clave foránea real y el motor lo trata como una dimensión más del saldo |
| 15 | ¿Cuándo se vuelve DISPONIBLE? | **Hoy: al aceptar la recepción.** `record_movement` escribe el saldo con `state="DISPONIBLE"` fijo. El contrato (`ADR-D0-010` R-D0-10-4) dice que debe exigir liberación formal en 021 |
| 16 | ¿Quién captura el lote? | 019 lo captura hoy: `GoodsReceiptLine.lot_number` y `accept_receipt` crea el `InventoryLot` |
| 17 | ¿Quién captura el serial? | 019: `GoodsReceiptLine.serials` (texto) y `accept_receipt` crea los `ProductSerial` |
| 18 | ¿Quién captura el vencimiento? | 019: `GoodsReceiptLine.expiry_date`, que viaja al lote |
| 19 | ¿Quién registra daño y cuarentena? | Hoy nadie con detalle: solo `quantity_rejected` y `quality` binario por línea. El tipo de daño, su evidencia y su tratamiento son de 020 (registro) y 021 (tratamiento) |
| 20 | ¿Qué movimiento escribe la recepción? | `ENTRADA_RECEPCION`, con almacén, sin ubicación, sin presentación, con `document_ref = RECEIPT:{id}` y saldo en `DISPONIBLE` |
| 21 | ¿Qué movimiento escribe la confirmación? | Ninguno: no existe el proceso |
| 22 | ¿Qué movimiento escribe el put-away? | Ninguno: no existe el proceso |
| 23 | ¿El put-away cambia `on_hand` o solo ubicación/custodia? | Debe ser un traslado interno entre dimensiones del saldo: cambia ubicación y estado de custodia, no la cantidad física de la empresa. El contrato lo fijará 022 |
| 24 | ¿031 consume reserva o saldo? | Ambas cosas y de distinta forma: la reserva le dice **qué y cuánto** (Spec 030, por línea, en base); el saldo por ubicación le diría **de dónde**. Lo segundo no existe |
| 25 | ¿031 necesita cantidad por ubicación? | Sí. Sin ella no hay «obtener ubicaciones de cada producto» ni recorrido |
| 26 | ¿La capacidad de recorrido de 008 basta? | Para **ordenar** sí: `WarehouseLocation.sequence` y `GET /organization/locations/ordered`. Para **saber qué hay en cada ubicación**, no: eso es saldo, no estructura |
| 27 | ¿`pick_list_lines` tiene los campos necesarios? | No. Tiene producto, lote, serial, cantidad y semántica de unidad. **No tiene `location_id` ni `sequence`** |
| 28 | ¿Bloqueo exacto de 031? | Existencia sin ubicación: `InventoryBalance.location_id` es siempre nulo por el camino de entrada. Owner: 022 |
| 29 | ¿Bloqueo exacto de 032? | El de 031, más su propia cola y ruta |
| 30 | ¿Cuál es la primera Spec verdaderamente implementable? | **019**: primera de la ruta crítica, cero bloqueos activos y funcionalmente incompleta |

---

## `/speckit.plan` — 18 olas

| Ola | Contenido | Resultado |
|---|---|---|
| 1 | Baseline del repositorio | tabla de arriba |
| 2-7 | Auditoría forense de 019, 020, 021, 022, 031, 032 | §«Cadena operativa» |
| 8 | Capacidad de 023 y 024 | §«Impacto de proveedores» |
| 9 | Análisis recepción → disponible | §«Punto de disponibilidad» |
| 10 | Análisis recepción → ubicación | §«Semántica de la ubicación» |
| 11 | Análisis P23 de datos de entrada | §«Datos de entrada y P23» |
| 12 | Grafo de capacidades | `operational-chain-capability-matrix.md` |
| 13 | Reconciliación de bloqueos | `active-blockers.md`, `resolved-blockers.md` |
| 14 | Ruta crítica | `critical-path-analysis.md` |
| 15 | Ranking de preparación | `readiness-ranking.md` |
| 16 | Decisión de la siguiente Spec | `next-spec-decision.md` |
| 17 | Actualización de Master 56 | `master-56-specs-status.md` |
| 18 | Convergencia | `operational-chain-convergence.md` |

---

## CONSTITUTION GATE

| Validación | Resultado | Evidencia |
|---|---|---|
| Numeración maestra intacta | PASS | 56 filas, sin altas ni bajas |
| ARCH-MC-001 | PASS | toda capacidad auditada preserva `CompanyContext`; ninguna propuesta lo relaja |
| Spec 008 | PASS | se reconoce la estructura entregada; no se vuelve a bloquear 022 por «no hay ubicaciones» |
| Spec 011 | PASS | `to_base` sigue siendo la única autoridad de conversión |
| Spec 023 | PASS | un solo motor de inventario; el gap de estados se atribuye, no se duplica |
| Spec 029 · 030 | PASS | el handoff `RELEASED` + reservas por línea se preserva sin cambios |
| Spec 045 · 046 | PASS | aprobaciones y documentos se citan como proveedores existentes, no como bloqueos nuevos |
| Sin segundo motor de inventario | PASS | — |
| Sin segunda autoridad de almacén | PASS | — |
| Sin implementación de producto | PASS | `git diff` sobre `resources/` y `alembic/` = 0 |
| Sin dependencia inventada | PASS | cada arista del grafo cita código o requisito |
| Sin estado de proceso inventado | PASS | solo se nombran estados que existen en el catálogo o en `ADR-D0-010` |

**CONSTITUTION GATE: PASS**

---

## `/speckit.checklist`

Los 30 ítems del encargo quedan cubiertos: baseline remedida; las seis Specs auditadas; capacidad de
023 y 024 medida; movimiento de recepción analizado y clasificado; semántica de ubicación nula
resuelta; punto de disponibilidad identificado; transiciones de estado de mercancía identificadas;
propiedad de lote, serial y vencimiento identificada; caminos feliz y de excepción definidos;
contratos de entrada de confirmación, put-away, cola y ejecución definidos; handoff de 030
preservado; fronteras de empresa confirmadas; bloqueos históricos reconciliados; bloqueos ocultos
identificados; ruta crítica calculada; candidatas ordenadas; una Spec seleccionada; cambios de
código productivo = 0.

---

## `/speckit.tasks`

T-OP-001..038 según el encargo, todas ejecutadas y trazadas en
`operational-chain-traceability.md`. Sin tareas huérfanas.

---

## `/speckit.analyze`

| Detección buscada | Resultado |
|---|---|
| Spec sin estado | 0 |
| Estado sin evidencia | 0 |
| Dependencia sin capacidad | 0 |
| Capacidad sin proveedor | 0 |
| Bloqueo histórico ya resuelto | **2 encontrados y retirados** (ver §«Bloqueos reconciliados») |
| Bloqueo real omitido | **2 encontrados y añadidos** (estados de mercancía no escribibles; unidad no capturada en recepción) |
| 020 tratado como listo sin 019 suficiente | No: la capacidad que 020 consume se midió y existe |
| 021 bloqueada por 020 completa cuando solo necesita capacidad de excepción | **Corregido**: la dependencia pasa a ser de capacidad, con camino feliz sin incidencia |
| 022 bloqueada por falta de ubicaciones aunque 008 las entrega | **Corregido**: el bloqueo real es el estado de origen de la mercancía, no la estructura |
| 031 tratada como lista sin existencia ubicada | No: se mantiene bloqueada, con la capacidad exacta nombrada |
| 032 tratada como lista sin ruta/ubicación/lotes | No |
| Recepción obligada a hacer put-away | No: se declara legítimo terminar la recepción sin ubicación |
| Put-away obligado a hacer picking | No |
| Confirmación obligada a asignar ubicación | No |
| Dependencia circular | 0 |
| Dato P23 capturado demasiado tarde | **1 encontrado**: presentación y unidad de la línea de recepción |
| Estado disponible ambiguo | No: identificado, con owner y contrato citado |
| Código productivo cambiado por accidente | 0 |

| Métrica del checkpoint | Valor |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |

Que una Spec siga bloqueada no bloquea el checkpoint: los bloqueos están nombrados y respaldados.

---

## Cadena operativa, Spec por Spec

### SPEC 019 — RECEPCIÓN FÍSICA

| Campo | Medida |
|---|---|
| Estado | `PARTIALLY_IMPLEMENTED` |
| Modelo | `GoodsReceipt` (empresa, orden, almacén, estado, `quality_status`) · `GoodsReceiptLine` (línea de orden, producto, recibida/aceptada/rechazada, lote, vencimiento, seriales, calidad, columnas de unidad de Spec 011) |
| Máquina de estados | `DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED / PARTIALLY_ACCEPTED / REJECTED → CLOSED`; `CANCELLED` desde borrador |
| API | crear recepción, añadir línea, confirmar, calidad, aceptar, rechazar |
| Pruebas | `test_purchasing.py` (aceptación actualiza inventario vía 003; exige orden aprobada), `test_qa_fixes.py` (autosiembra del tipo de movimiento) |
| Capacidades entregadas | recepción identificable contra orden de compra · tres cantidades por línea · lote, vencimiento y seriales capturados y materializados en 024 · compuerta de calidad · movimiento de entrada con costo de la orden · alcance de empresa |
| Capacidades ausentes | confirmación de arribo y programación de descarga · bultos y pallets · comparación contra *packing list* (solo compara contra la orden) · acta de recepción · evidencia documental · **presentación y unidad de la línea** · detalle del daño |
| Dependencias | 017 órdenes de compra ✓ · 010 productos ✓ · 011 unidades ✓ · 008 almacenes ✓ · 023 motor de inventario ✓ · 045 aprobaciones ✓ · 046 documentos ✓ |
| Bloqueos activos | **ninguno** |
| Preparación | **lista para completarse**: es la primera de la ruta y no espera a nadie |

Cobertura de proceso documentada: 3 de 10 etapas.

### SPEC 020 — INCIDENCIAS DE RECEPCIÓN

| Campo | Medida |
|---|---|
| Estado | `NOT_STARTED` |
| Modelo | cero tablas de incidencia |
| Implementación existente | `GoodsReceiptLine.quantity_rejected` y `quality` (binario por línea); `GoodsReceipt.quality_status` |
| Capacidades requeridas | recepción sobre la que colgar la incidencia (019 ✓) · producto (010 ✓) · unidad y presentación (011 ✓ como motor) · almacén (008 ✓) · evidencia documental (046 ✓) · aprobación de excepciones (045 ✓) · empresa (ARCH-MC ✓) · escalamiento a compras (017 ✓) |
| Capacidades ausentes | entidad de incidencia con tipo, cantidad, evidencia, responsable y ciclo de resolución |
| Tipos documentados | faltante · sobrante · producto equivocado · daño · evidencia de la incidencia · escalamiento a Compras. **No se inventan otros** |
| Bloqueos activos | **ninguno** |
| Preparación | `READY_FOR_IMPLEMENTATION` |

### SPEC 021 — CONFIRMACIÓN Y CONCILIACIÓN DE INVENTARIO

| Campo | Medida |
|---|---|
| Estado | `PARTIALLY_IMPLEMENTED` (esqueleto) |
| Implementación existente | compuerta `quality_status` que `accept_receipt` exige aprobada antes de escribir en el ledger |
| Capacidades requeridas | recepción cerrada (019 ✓) · capacidad de incidencia para el camino de excepción (020 ✗) · autoridad de inventario con **estados de mercancía escribibles** (023 ✗) · conteo por SKU y conciliación contra orden y recepción física (✗) · liberación formal del lote (✗) |
| Dependencia de 020 | **de capacidad, no de registro**. El camino feliz no crea incidencia alguna |
| Dependencia del camino feliz | solo 019 |
| Bloqueos activos | **dos**: la capacidad de incidencia (020) y la imposibilidad de escribir saldo en un estado distinto de `DISPONIBLE` (023) |
| Preparación | bloqueada |

### SPEC 022 — PUT-AWAY Y UBICACIÓN

| Campo | Medida |
|---|---|
| Estado | `NOT_STARTED` |
| Implementación existente | ninguna. Ningún proceso escribe `location_id` en saldos ni movimientos desde la cadena de entrada |
| Capacidad de 008 | **entregada y suficiente**: zonas, pasillos, racks, niveles y ubicaciones con `sequence` y capacidad declarada; API completa incluido `GET /organization/locations/ordered` |
| Capacidad de 023 | `InventoryMovement.location_id` e `InventoryBalance.location_id` existen con clave foránea real y el motor los admite como dimensión del saldo |
| Capacidad requerida de 021 | mercancía confirmada con empresa, almacén, producto, cantidad base, lote/serial y **estado de origen inequívoco** del que el put-away la saca |
| Bloqueos activos | **uno**: el estado de origen. Hoy la mercancía aceptada ya está `DISPONIBLE` y sin ubicación, de modo que el put-away no tendría de dónde sacarla ni a qué estado llevarla |
| Preparación | bloqueada por 021, no por 008 |

### SPEC 031 — COLA Y RUTA DE PICKING

| Campo | Medida |
|---|---|
| Estado | `BLOCKED_BY_DEPENDENCY` |
| Handoff de 030 | **satisfecho**: pedido en `RELEASED`, reservas `ACTIVE` por `source_line_id`, almacén del pedido, cantidad base y presentación por línea, aislamiento de empresa |
| Capacidad de reserva | satisfecha (Spec 030) |
| Dependencia de ubicación | **insatisfecha**: `InventoryBalance.location_id` es nulo en todo lo que entra por recepción, así que no existe «cantidad por ubicación» |
| Requisitos de ruta | ordenación disponible en 008 (`sequence`, `/locations/ordered`); falta la existencia ubicada que ordenar |
| Modelo propio | `pick_lists` ✓; `pick_list_lines` **sin `location_id` ni `sequence`**; `create_picklist` recibe las líneas del llamante y no calcula cola, prioridad ni recorrido |
| Bloqueos activos | **uno**: existencia ubicada (owner 022) |
| Preparación | bloqueada |

### SPEC 032 — PICKING Y CONSOLIDACIÓN

| Campo | Medida |
|---|---|
| Estado | `BLOCKED_BY_DEPENDENCY` |
| Implementación existente | esqueleto en `sales`: `Shipment`, `ShipmentLine`, validación y confirmación de despacho (que ya consume la reserva como `FULFILLED`) |
| Dependencia de 031 | cola y ruta: sin secuencia no hay ejecución que seguir |
| Dependencia de 022 | ubicación de origen de cada extracción |
| Dependencia de 024 | **satisfecha como dato**: `inventory_lots` con `expiry_date` y máquina de estados, `product_serials` con estado y almacén. La selección FEFO/FIFO es alcance propio de 032 |
| Dependencia de 030 | **satisfecha**: reservas por línea, con consumo en la salida física ya implementado |
| Bloqueos activos | **dos**: 031 y 022 |
| Preparación | bloqueada |

---

## Punto de disponibilidad

| Etapa | Qué ocurre hoy |
|---|---|
| Recepción física | `create_receipt` → `add_receipt_line` → `confirm_receipt`; no toca inventario |
| Incidencia | no existe |
| Confirmación | `set_receipt_quality` marca `quality_status`; `accept_receipt` exige que esté `APPROVED` |
| Aceptación | `accept_receipt` crea lote y seriales y llama a `record_movement`, que escribe el saldo **en `DISPONIBLE`** |
| Put-away | no existe |

**La mercancía se vuelve vendible al aceptar la recepción.** Opción A del encargo.

El contrato dice otra cosa: `ADR-D0-010` R-D0-10-4 — «El paso a `DISPONIBLE` desde la cadena de
recepción exige **liberación formal** (Spec 021). No es automático».

**No es una contradicción abierta**: el propio ADR-D0-010 lo previó y le puso dueño y fecha — «El
cambio de comportamiento (recepción ya no salta a `DISPONIBLE`) llega con la Spec 021, no con esta
decisión». Es un hueco conocido, atribuido y programado. Por eso el checkpoint cierra con
`CONTRADICTIONS = 0` y con un bloqueo nombrado en 021.

Consecuencia para D0-03, que no se toca: la Spec 030 reserva sobre saldo `DISPONIBLE`, y hoy eso
significa «todo lo aceptado en recepción». Cuando 021 introduzca la liberación formal, el conjunto
reservable se estrechará sin que la regla de reserva cambie una coma.

---

## Semántica de la ubicación

| Pregunta | Respuesta |
|---|---|
| ¿Se conoce la ubicación al recibir? | No. `accept_receipt` llama a `record_movement` sin `location_id` |
| ¿Es legítimo el saldo con almacén conocido y ubicación nula? | **Sí.** `InventoryBalance.location_id` es anulable con clave foránea real y el motor lo trata como dimensión: `location_id IS NULL` es una fila de saldo válida y distinta |
| Autoridad | Spec 023 define la dimensión; Spec 008 define la estructura; **Spec 022 será quien la escriba** |

Invariante que este checkpoint deja documentado: entre la recepción y el put-away, la existencia
vive con **almacén conocido y ubicación nula**. No es un defecto de 019: recibir no es ubicar.

---

## Movimiento de recepción

| Aspecto | Valor actual |
|---|---|
| Llamada | `inv_service.record_movement(...)` desde `accept_receipt` |
| Tipo | `ENTRADA_RECEPCION` |
| Almacén | el de la recepción |
| Ubicación | **nula** |
| Estado del saldo | `DISPONIBLE` (fijo en el motor) |
| Cantidad | `line.quantity_accepted` |
| Presentación | **no se pasa** |
| Cantidad base | se calcula con presentación nula, es decir factor 1 |
| Documento origen | `RECEIPT:{id}` |

**Clasificación por dimensión, porque no todo el hueco tiene el mismo dueño:**

| Dimensión | Clase | Dueño |
|---|---|---|
| Ubicación nula | **A — correcto porque recibir es previo al put-away** | 022 la escribirá |
| Estado `DISPONIBLE` inmediato | **C — incompleto** | 021 |
| Presentación no pasada y cantidad base igual a la tecleada | **B — incompleto** | 019 |

La tercera fila merece detalle. `GoodsReceiptLine` tiene desde la Spec 011 las columnas `uom_id`,
`presentation_id`, `conversion_factor_snapshot`, `base_quantity_received/accepted/rejected` y
`uom_source`. La migración `0021` las creó y la `0022` rellenó lo histórico. **Ningún código las
escribe hoy**: ni el servicio ni el esquema de la API las contemplan. Es el mismo patrón que la
Spec 029 cerró para el precio y la Spec 030 para la reserva —la columna existe y nadie la llena—,
todavía abierto en la recepción.

Hoy el efecto está enmascarado porque la API no admite presentación: toda recepción se teclea en
unidad base y la igualdad se cumple por accidente. En cuanto se reciba «3 pallets de 10 cajas de
12», el ledger anotará 3.

---

## Estados de mercancía

`ADR-D0-010` declara quince estados. Se midió cuáles escribe el código:

| Estado | ¿Lo escribe alguien? |
|---|---|
| `DISPONIBLE` | Sí, y es el **único**: las cinco llamadas a `_get_balance` del motor lo fijan |
| `RECIBIDO`, `PENDIENTE_CONFIRMACION`, `BLOQUEADO`, `PICKING`, `PREPARADO`, `DESPACHADO`, `DEVUELTO` | **No** |
| `RESERVADO`, `CUARENTENA`, `TRANSITO`, `RECHAZADO`, `DESECHO`, `VENDIDO`, `ESPERADO` | No como estado de saldo. `CUARENTENA`, `TRANSITO`, `RECHAZADO`, `DESECHO`, `VENDIDO` y `RESERVADO` sí existen en la máquina de **lotes y seriales** |

De ahí sale el bloqueo nuevo: **021 no puede confirmar mercancía a un estado no vendible porque el
motor de saldos solo sabe escribir `DISPONIBLE`.** Es capacidad de 023 y la consume 021.

Nota: las cuatro apariciones de `PICKING` en el código son estados de **transferencia**, no de
mercancía. No cuentan.

---

## Datos de entrada y P23

| Dato | ¿Se captura hoy? | Dónde | Dueño |
|---|---|---|---|
| Lote | **Sí** | `GoodsReceiptLine.lot_number` → `InventoryLot` | 019 |
| Vencimiento | **Sí** | `GoodsReceiptLine.expiry_date` → lote | 019 |
| Serial | **Sí** | `GoodsReceiptLine.serials` (texto separado por comas) → `ProductSerial` | 019 |
| Presentación y unidad | **No** | columnas presentes, nadie las escribe | **019** |
| Bultos y pallets | **No** | no existe el concepto | 019 |
| Evidencia del daño | **No** | solo `quantity_rejected` y `quality` binario | 020 (con 046) |
| Tipo de discrepancia | **No** | — | 020 |

Los tres primeros están bien resueltos y son justo los que P23 más protege. Los cuatro siguientes
son datos que **solo se conocen mientras el camión está en el muelle**: cuando se descubran aguas
abajo, ya no habrá cómo reconstruirlos.

---

## Camino feliz

```
Orden de compra APPROVED
  → create_receipt (DRAFT)
  → add_receipt_line ×N        [lote, vencimiento, seriales]
  → confirm_receipt (CONFIRMED)
  → set_receipt_quality APPROVED
  → accept_receipt (ACCEPTED)  → InventoryLot + ProductSerial
                               → record_movement ENTRADA_RECEPCION
                               → saldo DISPONIBLE, ubicación NULL
```

Ninguna incidencia se crea, y así debe seguir siendo: exigir un registro de excepción a una
recepción sin excepciones sería inventar trabajo.

## Camino con incidencia (objetivo, aún no implementado)

```
create_receipt → add_receipt_line (recibido 100)
  → discrepancia detectada
  → Incidencia [tipo, cantidad, evidencia (046), responsable]   ← Spec 020
  → escalamiento a Compras si procede                            ← Spec 020 + 017
  → resolución [aceptar / reclamar / devolver / cuarentena]      ← Spec 020 → 021
  → Confirmación: aceptado 90, rechazado 10                      ← Spec 021
  → liberación formal de los 90 a DISPONIBLE                     ← Spec 021 (exige 023)
  → put-away de los 90 a su ubicación                            ← Spec 022
```

Hoy, de este camino solo existe el número: `quantity_rejected = 10`. Sin tipo, sin evidencia, sin
responsable y sin tratamiento.

---

## Bloqueos reconciliados

### Retirados (eran ciertos y ya no lo son)

| Bloqueo histórico | Por qué se retira |
|---|---|
| «022 bloqueada porque no hay ubicaciones» | Falso desde la Spec 008: hay zonas, pasillos, racks, niveles y ubicaciones con `sequence` y capacidad, con API completa. Lo que falta no es la estructura, es el **estado de origen** de la mercancía |
| «031 y 032 bloqueadas por 030» | Resuelto: la Spec 030 cerró y entrega pedido `RELEASED` con reservas por línea. El bloqueo que queda es **022**, no 030 |

### Reformulados (el bloqueo era real pero estaba mal nombrado)

| Antes | Ahora |
|---|---|
| «021 bloqueada por 020» | 021 necesita de 020 **la capacidad de registrar y resolver excepciones**, no una incidencia por recepción. El camino feliz no pasa por 020 |
| «031 bloqueada por 022» | 031 necesita de 022 **existencia ubicada y cantidad por ubicación**. Sin nombrar la capacidad, el bloqueo no se puede cerrar ni comprobar |

### Nuevos (descubiertos en este checkpoint)

| Bloqueo | Tipo | Dueño | Specs afectadas | Resolución requerida |
|---|---|---|---|---|
| El motor de saldos solo sabe escribir `DISPONIBLE` | Capacidad | **023** | 021, 022, 032 | Admitir el estado como parámetro del movimiento y del saldo, con el catálogo de `ADR-D0-010` |
| La línea de recepción no captura presentación ni unidad | Dato (P23) | **019** | 019, 021, 022 | Capturarla al recibir y pasarla a `record_movement` |

---

## Ruta crítica

```
ENTRADA
  019 Recepción física  ✅ sin bloqueos, incompleta   ← PRIMERA CAPACIDAD FALTANTE
    → 020 Incidencias    ✅ sin bloqueos, no empezada
      → 021 Confirmación ⛔ 020 + estados de mercancía (023)
        → 022 Put-away   ⛔ 021

SALIDA
  029 ✅ → 030 ✅ → 031 ⛔ existencia ubicada (022) → 032 ⛔ 031 + 022

UNIÓN
  022 → 031: la cadena de salida no avanza hasta que la de entrada ubique la mercancía
```

La ruta crítica del producto entero pasa hoy por la cadena de entrada. Todo lo comercial está
cerrado (012, 029, 030) y espera a que el almacén sepa dónde está lo que vende.

---

## Ranking de preparación

| Rank | Spec | Dependencia | Arquitectura | Modelo | Contrato | Existente | Criticidad | Desbloqueo | Riesgo | Total |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **019 Recepción física** | 5 | 5 | 4 | 4 | 3 | 5 | 5 | **5** | **36/40** |
| 2 | 020 Incidencias | 5 | 5 | 3 | 4 | 0 | 4 | 4 | 4 | 29/40 |
| 3 | 021 Confirmación | 2 | 4 | 3 | 3 | 1 | 5 | 5 | 4 | 27/40 |
| 4 | 022 Put-away | 1 | 5 | 4 | 3 | 0 | 5 | 5 | 3 | 26/40 |
| 5 | 031 Cola y ruta | 1 | 4 | 2 | 3 | 1 | 4 | 3 | 2 | 20/40 |
| 6 | 032 Picking | 0 | 4 | 2 | 2 | 1 | 4 | 2 | 2 | 17/40 |

El número ayuda a ordenar; no decide. Lo que decide está abajo.

---

## Spec seleccionada

> **NEXT SPEC = 019 — RECEPCIÓN FÍSICA**
>
> **RUNNER-UP = 020 — INCIDENCIAS DE RECEPCIÓN** (referencia; no autorizada)

### Por qué 019

**Es la primera de la ruta crítica y no espera a nadie.** Sus siete proveedores están satisfechos:
órdenes de compra, productos, unidades, almacenes, motor de inventario, aprobaciones y documentos.
Bloqueos activos: cero.

**Está incompleta, y de forma medible.** Tres de las diez etapas documentadas del proceso de
recepción física. Falta confirmar el arribo, contar bultos y pallets, comparar contra el *packing
list*, levantar el acta y adjuntar evidencia.

**El dato que no captura es irrecuperable.** Presentación y unidad de lo recibido, número de bultos,
detalle del daño: se conocen mientras el camión está en el muelle y no después. Es P23 en su forma
más literal — «no se pierde el dato, es que nunca se captura» —, y es el mismo patrón que la Spec
029 cerró para el precio y la Spec 030 para la reserva. Las columnas de unidad llevan desde la
Spec 011 esperando en `GoodsReceiptLine` a que alguien las escriba.

**Tiene además un riesgo de corrección latente.** `accept_receipt` llama a `record_movement` sin
presentación, así que la cantidad base del asiento es la tecleada. Hoy no hace daño porque la API no
admite presentaciones; el día que se reciba en cajas, el ledger anotará cajas como si fueran
unidades. Cerrar 019 cierra ese hueco antes de que exista.

**Y elegirla evita trabajar alrededor de lo incompleto.** Construir 020 primero sería levantar el
registro de incidencias sobre una recepción que todavía no sabe describir lo que llegó: una
incidencia de «faltan dos cajas» se anotaría en unidades ambiguas.

### Por qué antes que 020

020 también tiene cero bloqueos y es la candidata natural por tamaño del hueco: no existe. Pero está
**aguas abajo**. Su calidad depende de la precisión de la recepción sobre la que cuelga, y la regla
del propio encargo es preferir la primera capacidad faltante cuyas dependencias estén satisfechas,
en lugar de saltar aguas abajo para rodear lo que falta arriba. Además, 019 puntúa más alto
exactamente donde importa: riesgo de dato irreversible.

### Qué desbloquea

Completar 019 no desbloquea Specs por sí solo —020 ya está desbloqueada—, pero **mejora la base de
las cuatro siguientes**: 020 registra incidencias sobre líneas que saben su presentación; 021
concilia contra cantidades base fiables; 022 ubica lo que 021 confirmó; 031 y 032 heredan la
precisión de todo lo anterior.

---

## Deuda externa y futura, clasificada

| Asunto | Dueño | ¿Bloquea esta cadena? |
|---|---|---|
| Guardia del preflight que compara el mensaje traducido de PostgreSQL (`does not exist`) | preflight multiempresa (N4/N8) | **No.** Severidad media: produce un diagnóstico falso cuando falta una base. Este checkpoint no basó ninguna decisión en texto localizado: se usaron catálogo, modelos y código |
| `sales_invoice_lines.unit_price` con menos precisión que la conservada por la Spec 029 | **034** | **No** |
| S3 sin servicio real (8 saltos) | infraestructura / 046 | **No.** Ninguna Spec de esta cadena lo necesita para sus criterios de aceptación |

---

## Cambios de código productivo

Backend 0 · Frontend 0 · Alembic 0.
