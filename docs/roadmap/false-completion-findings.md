# TOP 10 — FUNCIONALIDADES QUE PARECEN TERMINADAS Y NO LO ESTÁN

> Patrón raíz: **el patrón Sucursales** — una etapa que el sistema asume existente pero que
> nunca fue construida. Aquí se aplica el mismo diagnóstico a todo KONTROL.
> Ninguno de estos hallazgos produce error visible ni test rojo. Esa es exactamente su peligrosidad.

---

## FC-01 · La factura de venta no sabe a qué pedido pertenece — BLOCKER

**Aparenta:** el ciclo de venta está completo y probado (E2E 20/20 incluye "Factura de venta EMITTED + CxC").

**Realidad:** `SalesInvoice` (`sales/models.py:123`) no tiene `order_id`, ni `shipment_id`, ni `picklist_id`.
Sus campos son `company_id`, `customer_id`, `invoice_number`, importes y estado. Nada más.

**Consecuencias comprobables:**
- No se puede responder "¿qué pedido facturó esta factura?" desde la base de datos.
- Nada impide facturar dos veces el mismo pedido.
- Nada impide facturar un pedido nunca preparado ni despachado.
- La regla documentada «Asocia la factura al pedido» (DOCX Pedido §8) no tiene soporte.

**Asimetría reveladora:** la cadena de compras **sí** está trazada —
`SupplierInvoiceLine.order_line_id` + `.receipt_line_id` + tabla `triple_matches`.
Mismo equipo, mismo patrón, resultado opuesto: es omisión, no decisión de diseño.

---

## FC-02 · El picking existe como documento, no como proceso — CRITICAL

**Aparenta:** hay `PickList`, `PickListLine`, pantalla `/ventas/despacho`, y el E2E dice "Despacho PK/DESP PASS".

**Realidad:** `PickListLine` (`sales/models.py:88`) tiene `product_id`, `lot_id`, `serial_id`, `quantity`.
**No tiene `location_id`. No tiene `sequence`.**

El documento de proceso define la ruta de picking por ubicación física como *la característica
distintiva de la operación*: «Los productos no se buscan de forma aleatoria… Pedido → Zona → Pasillo
→ Rack → Ubicación → Producto → Siguiente ubicación». Eso no existe: no hay cola, ni prioridad,
ni recorrido, ni almacenista asignado.

Lo que hay es una lista de productos a tomar. Un almacenista real no podría usarla.

---

## FC-03 · La confirmación de pedido no existe en ningún sitio — CRITICAL

**Aparenta:** el flujo va de preparación a despacho sin errores.

**Realidad:** `ORDER_TRANSITIONS` (`sales/service.py:57`) es
`DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED → PREPARING → SHIPPED → CLOSED`.
**No hay estado `CONFIRMED`.** Búsqueda de `confirmation`/`confirmacion` en modelos: 0 coincidencias.

El documento dedica una sección entera (Proceso 6) a esta etapa y la justifica como
**separación funcional**: «Almacén prepara. Confirmación verifica. Facturación factura sobre un
pedido previamente confirmado.» Es un control de segregación de funciones, no un paso administrativo.
Su ausencia es también una brecha de control interno, no solo de funcionalidad.

---

## FC-04 · La recepción aumenta stock pero nunca ubica la mercancía — CRITICAL

**Aparenta:** «Recepción RC-QA-0001 (confirm+quality+accept) PASS» y «Inventario MONITOR=10 PASS».

**Realidad:** `accept_receipt` (`purchasing/service.py:346`) llama a `record_movement(...)`
**sin `location_id`**. `GoodsReceiptLine` no tiene columna de ubicación.

La mercancía entra al almacén como una cifra flotante sin posición física. Todo el bloque 4 del
proceso documentado —zona, pasillo, rack, nivel, posición, etiquetado, traslado, confirmación
física, validación de coincidencia— no tiene soporte. `InventoryMovement.location_id` existe y es
nullable; en la práctica siempre queda nulo.

---

## FC-05 · La recepción salta la cuarentena y la liberación — CRITICAL

**Aparenta:** hay control de calidad (`quality_status`) y estados de inventario ricos
(`DISPONIBLE / RESERVADO / TRANSITO / CUARENTENA / RECHAZADO / DESECHO`).

**Realidad:** el motor de estados existe (`inventory/service.py:102`), pero el flujo de recepción
**no lo usa**: `accept_receipt` escribe directamente en `DISPONIBLE`.

No existen los estados documentados «recibido», «pendiente de validación» ni «bloqueado por
incidencia». No hay conteo independiente, ni conciliación contra packing list, ni liberación formal
del lote. El documento lo enuncia como control crítico: «Liberación formal del inventario antes de
permitir su despacho».

---

## FC-06 · KAUD-001 figura RESUELTO y cubre 7 de 9 módulos — HIGH

**Aparenta:** el reporte ejecutivo de la auditoría 012 declara el único CRITICAL como resuelto,
con E2E 20/20 de respaldo.

**Realidad, contando llamadas a `_audit(...)` por servicio:**

| Módulo | Llamadas |
|---|---:|
| purchasing / sales / treasury / fiscal / inventory / regulatory / reporting | 11 / 10 / 5 / 5 / 4 / 4 / 1 |
| **organization** | **0** |
| **master_data** | **0** |

El hallazgo original `KQA-102` enumeraba literalmente «empresa, sucursales, almacenes, clientes,
proveedores, productos». Esas seis entidades viven exactamente en los dos módulos que quedaron en cero.
Crear una empresa o un cliente hoy no deja rastro en `audit_events`.

---

## FC-07 · Existe tabla de archivos y ninguna forma de subir uno — HIGH

**Aparenta:** hay gestión documental (`file_metadata` con `sha256`, `storage_key`, `mime_type`, `size`).

**Realidad:** búsqueda de `UploadFile` en todo el backend: **0 coincidencias**. No hay endpoint de
subida ni de descarga de adjuntos. Además, `file_metadata` no tiene `entity_type` ni `entity_id`:
aunque hubiera subida, un archivo no podría vincularse a una factura, un permiso o una incidencia.

Toda la evidencia documental que los procesos exigen (packing list, fotos de daño, certificados,
soportes de importación) no tiene dónde vivir.

---

## FC-08 · Las ubicaciones son un maestro sin jerarquía ni consumidores — HIGH

**Aparenta:** existe `/organizacion/ubicaciones`, tabla `locations`, endpoints GET/POST.

**Realidad:** `Location` (`organization/models.py:94`) tiene `zone`, `aisle`, `rack`, `capacity`,
`restrictions`. **No tiene `level` (nivel) ni `position` (posición)**, que el proceso exige como los
dos últimos niveles de la dirección física. No hay entidad Zona con su clasificación A–E
(alta/media/baja rotación, incidencias, sobredimensionados). Y ningún proceso escribe en ella.

---

## FC-09 · Listas de precios, zonas y centros de costo son texto libre — HIGH

**Aparenta:** el cliente tiene lista de precios, zona, condición de pago y vendedor.

**Realidad:** `Customer.price_list`, `.zone`, `.payment_term`, `.salesperson` son `String(120)`
sin catálogo. `cost_center_id` es `String(36)` sin tabla ni FK. No hay motor de precios: el precio
se teclea por línea y el descuento es un monto manual.

Viola el Principio 8 de la Constitución (no hardcodear reglas de negocio; reglas críticas
versionadas y con fuente). Y como no hay Spec que lo cubra, es también requisito huérfano.

---

## FC-10 · Las líneas de documento no distinguen unidad ni presentación — HIGH

**Aparenta:** existen `units_of_measure`, `unit_conversions`, `presentations` y `barcodes`.

**Realidad:** ninguna línea de documento (`sales_*_lines`, `purchase_*_lines`, `goods_receipt_lines`,
`pick_list_lines`, `shipment_lines`, `transfer_lines`) tiene `uom_id` ni `presentation_id`.
Solo `quantity`.

La distinción exigida —SKU base ≠ unidad de inventario ≠ presentación comercial ≠ unidad de
despacho— existe en el maestro y desaparece en la transacción. Comprar en cajas y vender en
unidades no es representable hoy, y el proceso de recepción pide expresamente identificar
diferencias «por presentación» y «por unidad de medida».

---

## Patrón común

Ocho de los diez hallazgos comparten la misma forma: **el maestro existe, la transacción lo ignora.**
Ubicaciones, unidades, presentaciones, estados de inventario, centros de costo y archivos están
modelados pero ningún proceso los escribe. El sistema parece completo desde la pantalla de
configuración y se vacía en la operación.

---

## FC-11 · La prueba de aislamiento entre empresas de la Spec 045 no prueba nada — 2026-09-03

**Aparenta:** la bandeja de aprobaciones tiene cobertura de multiempresa. `approvals.spec.ts` pide
la bandeja con `company_id=empresa-inexistente` y comprueba que el total es cero.

**Realidad:** el endpoint no declara ese parámetro. FastAPI ignora los parámetros desconocidos, y la
empresa sale del contexto de la petición, que es lo que el contrato de alcance manda. La aserción
solo pasa cuando la bandeja está vacía por cualquier otra razón. Con datos dentro, falla; y falla
señalando un problema que no existe.

**Por qué encaja en esta lista:** no es una prueba que se rompió, es una prueba que nunca comprobó
lo que dice comprobar. Una verificación falsa de la frontera entre empresas es peor que su ausencia,
porque cierra la pregunta. La frontera real sí está sostenida —el contexto es la única autoridad—,
pero no por esta prueba.

**Encontrado desde:** la corrida de extremo a extremo de la Spec 020, contra PostgreSQL con datos.
**No corregido:** es prueba de la Spec 045. Corregirla desde la 020 habría sido salirse del alcance.
**Dueño:** Spec 045.
