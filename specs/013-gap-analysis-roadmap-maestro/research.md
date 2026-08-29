# INVESTIGACIÓN — 013

## Método

Auditoría **no destructiva** ejecutada sobre `develop @ def2b52`:

| Técnica | Ejecutada | Resultado |
|---|---|---|
| `pytest tests/ -q` | Sí | 223 passed, 0 failed |
| `vitest run` | Sí | 210 passed, 7 archivos |
| Conteo de decoradores `@router.*` | Sí | 275 endpoints |
| Extracción de `path:` del router | Sí | 78 rutas |
| Extracción de `__tablename__` | Sí | 144 tablas |
| Lectura de `down_revision` en Alembic | Sí | cadena lineal 0001→0014, head único |
| Extracción de texto de PDF (`pdftotext -layout`) | Sí | Volúmenes 0, 1, 2 |
| Extracción de texto de DOCX (`zipfile` + regex) | Sí | 2 procesos operativos |
| Inspección de modelos por dominio | Sí | ver hallazgos |
| Búsqueda dirigida de entidades esperadas | Sí | ver §Entidades ausentes |
| `alembic upgrade` sobre PostgreSQL real | **No** | Sin instancia disponible — bloqueo registrado |
| Navegadores reales / dispositivos | **No** | Fuera de sandbox |

## Fuentes documentales localizadas

15 PDF en `requerimientos/` (Volúmenes 0-6, licenciamiento, estándar frontend,
providencias SENIAT, expediente SICA/SIGESAI/1808, guías, leyes, manual Saint)
+ 2 DOCX de proceso operativo (2026-08-25, sin track) + 1 diagrama PNG.

Detalle en `docs/roadmap/source-inventory.md`.

## Entidades esperadas por la documentación y AUSENTES en el modelo

Verificado por búsqueda directa sobre `resources/backend/app/modules/*/models.py`:

| Concepto exigido | Fuente | Presencia en el modelo |
|---|---|---|
| INCOTERM, proforma, packing list, embarque, expediente de importación | DOCX Importación §1 | **0 coincidencias** |
| Incidencia de recepción (faltante/sobrante/daño/referencia) | DOCX Importación §2 | **0 coincidencias** (solo `quantity_rejected` + `quality`) |
| Put-away / asignación de ubicación en recepción | DOCX Importación §4 | `GoodsReceiptLine` **sin** `location_id` |
| Nivel y posición de ubicación | DOCX Importación §4 | `Location` tiene `zone/aisle/rack`; **sin** `level`/`position` |
| Secuencia / ruta de picking por ubicación | DOCX Pedido §3 | `PickListLine` **sin** `location_id` ni `sequence` |
| Confirmación independiente de pedido | DOCX Pedido §6 | **0 coincidencias**; `ORDER_TRANSITIONS` no tiene estado `CONFIRMED` |
| Liberación para facturación | DOCX Pedido §7 | **0 coincidencias** |
| Asociación factura↔pedido | DOCX Pedido §8 | `SalesInvoice` **sin** `order_id` |
| Listas y reglas de precios, comisiones, zonas, rutas | Vol. 1 §7 · Vol. 2 §1 | `price_list`/`zone` son `String(120)` libres |
| Centro de costo, unidad de negocio | Vol. 2 §3 | `cost_center_id` es `String(36)` sin tabla ni FK |
| Adjuntos vinculados a documento | Vol. 1 §4 | `file_metadata` sin `entity_type`/`entity_id` y **sin endpoint de subida** |
| Notificaciones, mis tareas, alertas | Vol. 2 §1 | **0 coincidencias** |

## Asimetría estructural detectada

La cadena de **compras** está correctamente trazada:
`SupplierInvoiceLine.order_line_id` + `.receipt_line_id` + `TripleMatch`.

La cadena de **ventas** no lo está: `SalesInvoice` no referencia orden, picking ni despacho.
Es el mismo equipo, el mismo patrón y dos resultados distintos — lo que sugiere omisión,
no decisión de diseño.
