# CADENA OPERATIVA — MATRIZ DE CAPACIDADES

> Criterio de inclusión: una fila por **capacidad concreta** que una Spec consume de otra. No se
> anota «depende de X»: se anota qué necesita exactamente, quién lo entrega y con qué evidencia.
> Medida el 2026-09-03 contra `9af45bb`.

## Consumidores de la cadena

| Consumidor | Capacidad | Proveedor | Estado del proveedor | ¿Satisfecha? | Bloqueo |
|---|---|---|---|---|---|
| 019 | Orden de compra aprobada con líneas | 017 | PARTIAL | **Sí** | — |
| 019 | Producto de catálogo | 010 | PARTIAL | **Sí** | — |
| 019 | Almacén de la empresa | 008 | COMPLETE | **Sí** | — |
| 019 | Motor de entrada al ledger | 023 | PARTIAL | **Sí** | — |
| 019 | Lote y serial materializables | 024 | PARTIAL | **Sí** | — |
| 019 | Conversión a unidad base | 011 | COMPLETE | **Sí** (motor) · **no consumida** | deuda propia de 019 |
| 019 | Evidencia documental | 046 | RECONVERGED | **Sí** | — |
| 019 | Aprobación de excepciones | 045 | COMPLETE | **Sí** | — |
| 020 | Recepción identificable con líneas y cantidades | **019** | PARTIAL | **Sí** | — |
| 020 | Máquina de estados sobre la que colgar la incidencia | 019 | PARTIAL | **Sí** | — |
| 020 | Producto, almacén, empresa | 010 · 008 · ARCH-MC | — | **Sí** | — |
| 020 | Evidencia adjunta de la incidencia | 046 | RECONVERGED | **Sí** | — |
| 020 | Escalamiento a Compras | 017 | PARTIAL | **Sí** | — |
| 020 | Aprobación de sobrante o ajuste | 045 | COMPLETE | **Sí** | — |
| 021 | Recepción cerrada | 019 | PARTIAL | **Sí** | — |
| 021 | Registro y resolución de excepciones | **020** | NOT_STARTED | **No** | 020 |
| 021 | Escribir saldo en estado no vendible | **023** | PARTIAL | **No** | el motor fija `DISPONIBLE` |
| 021 | Catálogo de estados de mercancía | ADR-D0-010 | vigente | **Sí** (declarado) · **no implementado** | 023 |
| 021 | Cantidad base de lo recibido | 011 vía 019 | COMPLETE | **No** | 019 no la captura |
| 022 | Estructura física de ubicaciones | **008** | COMPLETE | **Sí** | — |
| 022 | Ordenación determinista de ubicaciones | 008 (`sequence`, `/locations/ordered`) | COMPLETE | **Sí** | — |
| 022 | Dimensión de ubicación en saldo y movimiento | 023 | PARTIAL | **Sí** | — |
| 022 | Mercancía confirmada con estado de origen inequívoco | **021** | PARTIAL | **No** | 021 |
| 022 | Capacidad declarada de la ubicación | 008 (`capacity_units/weight/uom`) | COMPLETE | **Sí** | — |
| 031 | Pedido liberado a preparación | **030** | COMPLETE | **Sí** | — |
| 031 | Reservas activas por línea, en base | 030 | COMPLETE | **Sí** | — |
| 031 | Almacén del pedido | 030 · 008 | COMPLETE | **Sí** | — |
| 031 | Existencia ubicada y cantidad por ubicación | **022** | NOT_STARTED | **No** | 022 |
| 031 | Ordenación de recorrido | 008 | COMPLETE | **Sí** | — |
| 031 | Ubicación y secuencia en la línea de picking | propia (`pick_list_lines`) | — | **No** | alcance propio de 031 |
| 032 | Cola y ruta de picking | **031** | BLOCKED | **No** | 031 |
| 032 | Ubicación de origen de cada extracción | **022** | NOT_STARTED | **No** | 022 |
| 032 | Lote, serial y vencimiento consultables | 024 | PARTIAL | **Sí** | — |
| 032 | Reservas a consumir | 030 | COMPLETE | **Sí** | — |
| 032 | Salida física que consume la reserva | 030 · 035 | COMPLETE | **Sí** | — |
| 032 | Estados de custodia de la mercancía | 023 | PARTIAL | **No** | mismo hueco que 021 |

## Proveedores: qué entregan y qué no

| Proveedor | Entrega hoy | No entrega |
|---|---|---|
| **008** Almacenes físicos | zonas, pasillos, racks, niveles, ubicaciones con `sequence` y capacidad; API completa con `/locations/ordered`; propiedad por empresa | nada que la cadena necesite. **No vuelve a ser bloqueo de 022** |
| **010** Productos | catálogo y taxonomía | — |
| **011** Unidades y presentaciones | `to_base`, versiones con factor congelado, columnas de unidad en todas las líneas | nada; el hueco está en quien no la llama |
| **023** Inventario y Kardex | movimientos inmutables, saldos reconstruibles, dimensión de ubicación y de lote/serial admitidas, reservas | **escribir saldo en un estado distinto de `DISPONIBLE`** |
| **024** Lotes y seriales | `inventory_lots` con vencimiento y máquina de estados; `product_serials` con estado y almacén | selección FEFO/FIFO, que es de 032 |
| **029** Pedido comercial | pedido con origen comercial completo | — |
| **030** Crédito y reserva | pedido `RELEASED`, reservas `ACTIVE` por línea en base, consumo en despacho | — |
| **045** Aprobaciones | motor único con política, cuórum y segregación | — |
| **046** Documentos | 8 tablas, 23 tipos de recurso, antivirus real | almacenamiento S3 real (P1 externa) |

## Aristas del grafo, con su evidencia

| Arista | Tipo | Evidencia |
|---|---|---|
| 019 → 020 | capacidad satisfecha | `GoodsReceipt`/`GoodsReceiptLine` con cantidades y estados |
| 019 → 021 (camino feliz) | capacidad satisfecha | `accept_receipt` ya exige calidad aprobada |
| 020 → 021 (camino de excepción) | **capacidad ausente** | cero tablas de incidencia |
| 023 → 021 | **capacidad ausente** | `record_movement` fija `state="DISPONIBLE"` |
| 021 → 022 | **capacidad ausente** | no existe confirmación ni estado de origen |
| 008 → 022 | capacidad satisfecha | ubicaciones con `sequence` y capacidad |
| 022 → 031 | **capacidad ausente** | `InventoryBalance.location_id` nulo en todo lo recibido |
| 030 → 031 | capacidad satisfecha | `order_dict` expone reservas por `source_line_id` y `eligible_for_picking` |
| 031 → 032 | **capacidad ausente** | `create_picklist` no calcula cola ni ruta |
| 024 → 032 | capacidad satisfecha | lotes con vencimiento, seriales con estado |
| 030 → 032 | capacidad satisfecha | reservas y su consumo en la salida física |

Sin ciclos: el grafo es un orden parcial estricto.
