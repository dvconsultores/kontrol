# Spec 018 · decisiones pendientes (filas que quedan)

Encargo del 2026-11-11. HEAD `3cf7ed0`; cabeza Alembic `0102_gov_ctl09_actas`. La matriz está en 38 de 42 COMPLETE.

> Actualización del 2026-11-12: los estados §3 quedaron construidos como condición del proceso (`../spec018-process-condition-delta.md`). La matriz está en 40 de 42 COMPLETE, con la zona temporal y las zonas A–E como filas que quedan.
>
> Actualización del 2026-11-12 (cierre): la zona temporal quedó construida (`../spec018-temporary-zone-delta.md`). La matriz está en 41 de 42 COMPLETE, y solo quedan las zonas A–E, pendientes del sponsor.

**Fuentes leídas:**
- el DOCX de importación, entero: §2 («Colocar la mercancía temporalmente en zona de recepción o validación»), §3 («Diferenciar inventario: recibido; disponible; pendiente de validación; bloqueado por incidencia»), §4 y «Zonas preliminares que conviene validar para HJ»;
- las Specs 019, 020 y 021 (`spec021-implementation-cycle.md`, que da la etapa 9 por cubierta con el «resultado mixto por línea»);
- `inventory/states.py` (aristas `INCIDENT_OPEN` y `INCIDENT_CLOSE`, dueña la 020, sin uso);
- el putaway (`inventory.service.putaway`);
- la atribución del expediente (`imports/service.py`);
- los modelos de zonas y ubicaciones (`organization/models.py`).

## B. Trazabilidad hasta la ubicación final

```text
PUTAWAY_TRACEABILITY_CURRENT_CHAIN=import_file.order_id → goods_receipts.order_id (estructurado) → receipt_confirmations.movement_id (estructurado) → putaway: SOLO texto (inventory_movements.document_ref == receipt.code, imports/service.py:1347)
PUTAWAY_TRACEABILITY_MISSING_LINK=movimiento de putaway → recepción y línea de origen
STRUCTURED_LINK_REQUIRED=1
MIGRATION_REQUIRED=1 (una tabla de vínculos, dueña Recepciones, como receipt_confirmations)
```

- **Arquitectura (Claude):**
  - Recepciones registra el vínculo `(receipt_id, receipt_line_id, movement_id, base_quantity)` cuando la mercancía de una recepción se ubica con un endpoint de Recepciones que llama a `inventory.service.putaway`, el motor único.
  - Inventario no aprende nada de compras.
  - El expediente cuenta lo ubicado por ese vínculo y no por texto.
- **Decisiones abiertas (dueña):**
  - El stock sin ubicar es fungible, así que un putaway desde Inventario → Ubicación no puede saber de qué recepción viene sin que alguien lo indique.
  - Lo ya ubicado y ligado hoy por texto quedaría «pendiente de ubicar» sin una reconstrucción, que es un backfill de datos.
- `MATERIAL_DECISION_REQUIRED_PUTAWAY = 1` (alcance de la atribución y del histórico).

## A. Estados §3

- **Qué dice el documento:** el DOCX dice «Diferenciar **inventario**», en sentido literal.
- **Qué decidió la 020:** que la incidencia no toque el inventario. La 021 dio la etapa 9 por cubierta con DISPONIBLE, RECHAZADO y CUARENTENA.
- **Qué falta hoy:** nada. Construido el 2026-11-12 como condición del proceso (`../spec018-process-condition-delta.md`, evidencia en `process-condition/`): se deriva de la recepción, su confirmación y sus incidencias vivas, y se ve en Recepciones y en el expediente. Una incidencia abierta impide confirmar (`INCIDENTS_UNRESOLVED`) y ahora además se muestra como «Bloqueado por incidencia».
- **Opción A:** condición del proceso, visible en la recepción y en el expediente, sin tocar el stock. **Elegida y construida.**
- **Opción B:** estado físico de inventario (RECIBIDO → BLOQUEADO al abrir una incidencia y vuelta al cerrarla). Revierte la decisión de la 020. Descartada.
- **Opción C:** no construir más. Descartada.
- `MATERIAL_DECISION_REQUIRED_STATES = 0 (resuelta: opción A, construida)`.

## C. Zona temporal

```text
TEMPORARY_ZONE_EXISTING_MODEL=zone_types (catálogo configurable por empresa: code, name), warehouse_zones, warehouse_locations, location_types(is_storable). Lo recibido queda hoy en RECIBIDO con ubicación nula
TEMPORARY_ZONE_CAN_REUSE_LOCATION_MODEL=1
TEMPORARY_ZONE_DEPENDS_ON_A_E=0 (la zona D, «pendiente de revisión», se parece, pero el DOCX la pide aparte y sin validar)
MATERIAL_DECISION_REQUIRED_TEMP_ZONE=1
```

Opciones:
- solo registrar en qué ubicación temporal quedó la recepción;
- colocar físicamente lo recibido en esa ubicación, para que el putaway salga de ella. Esto cambia el flujo de saldos de la 019, la 021 y la 022.

## D. Zonas A a E (SPONSOR_VALIDATION_REQUIRED)

```text
WHAT_DOCUMENT_SAYS=«Zonas preliminares que conviene validar para HJ»: A alta rotación; B rotación media; C baja rotación; D pendiente de revisión, diferencia o incidencia; E sobredimensionados, pesados o de manejo especial
WHAT_PRODUCT_ALREADY_HAS=tipos de zona configurables por empresa; clasificación de almacenamiento y rotación (Spec 015, bandas de rotación); asignación manual de ubicación sin recomendación (R-D0-14-10)
WHAT_IS_AMBIGUOUS=si son un catálogo fijo o la configuración de HJ; si la rotación debe asignar zona automáticamente; si D es la misma que la zona temporal
OPTION_A=configuración de HJ con tipos de zona existentes (sin código nuevo de producto)
OPTION_B=recomendación de zona según banda de rotación y atributos (nuevo motor de recomendación)
OPTION_C=catálogo fijo A–E en el producto
RECOMMENDED_OPTION=A (R-D0-12-6: el proceso de un cliente es configuración, no regla del producto)
WHY=el documento las llama «preliminares» y «que conviene validar»
PRODUCT_IMPACT=A: ninguno en código; B: un motor nuevo; C: contamina el modelo general
```

Esta fila sigue en SPONSOR_VALIDATION_REQUIRED hasta que valide el sponsor.

## Decisiones de la dueña (2026-11-11)

| Fila | Decisión | Efecto en este ciclo |
|---|---|---|
| B. Trazabilidad: alcance | «Recepción opcional en Inventario» | Construida. El expediente liga siempre la recepción. Inventario → Put-away ofrece «Recepción de origen» como dato opcional |
| B. Trazabilidad: histórico | «Reconstruir por coincidencia exacta» | Backfill en `0103`, solo con coincidencia exacta (regla en `../spec018-putaway-trace-delta.md`, PT-02) |
| A. Estados §3 | «Condición del proceso» (opción A) | Construida el 2026-11-12 (`../spec018-process-condition-delta.md`). La condición se ve en la recepción y en el expediente, sin tocar el stock; la decisión de la Spec 020 se mantiene |
| C. Zona temporal | «Registrar la ubicación temporal» (sin mover lo recibido) | Construida el 2026-11-12 (`0105`). No cambia el flujo de saldos de las Specs 019, 021 y 022 |
| D. Zonas A a E | Sin decisión del sponsor | Sigue en SPONSOR_VALIDATION_REQUIRED (opción A recomendada) |

```text
MATERIAL_DECISION_REQUIRED_PUTAWAY=0 (resuelta)
MATERIAL_DECISION_REQUIRED_STATES=0 (resuelta y construida: opción A)
MATERIAL_DECISION_REQUIRED_TEMP_ZONE=0 (resuelta: registrar; construida el 2026-11-12)
SPONSOR_VALIDATION_REQUIRED_ZONES_A_E=1
SELECTED_ROW=Condición del proceso de recepción (§3)
```

**Cambio de arquitectura durante la integración.** El diseño inicial puso las rutas en Compras. La guardia aprobada de la Spec 021 (`test_no_existe_endpoint_de_put_away_en_compras`) lo detectó, y las rutas se movieron a Inventario: `/inventory/putaway/recepciones` y `/inventory/putaway/desde-recepcion`. El vínculo y su servicio siguen siendo de Recepciones. La guardia no se tocó.
