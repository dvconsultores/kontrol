# Spec 018 · delta: trazabilidad de la importación hasta la ubicación final

- **Encargo:** `SPEC018_DECISIONES_PENDIENTES_Y_SIGUIENTE_FILA`, del 2026-11-11.
- **Spec dueña:** 018, dueña del proceso.
- **Autoridades del dato:**
  - el vínculo es de la Spec 019 (Recepciones);
  - el motor de put-away y sus rutas son de la Spec 022 (Inventario).
- **Decisiones:** `evidence/SPEC018_REMAINING_DECISIONS.md`.
- **Evidencia:** `evidence/putaway-trace/`.

## Decisiones de la dueña (2026-11-11)

- **Alcance de la atribución: «Recepción opcional en Inventario».**
  - El put-away del expediente liga siempre su movimiento a la recepción.
  - Desde Inventario → Put-away, el operario puede indicar la recepción de origen.
  - Si no la indica, el movimiento no se atribuye a ninguna recepción, porque el stock sin ubicar es fungible.
- **Histórico: «Reconstruir por coincidencia exacta».** Se autoriza un backfill en la migración `0103`, limitado a la coincidencia exacta que define PT-02.

## Contrato

- **PT-01. Vínculo estructurado.**
  - Tabla `receipt_putaways`, con `company_id`, `receipt_id`, `movement_id`, `product_id`, `warehouse_id`, `base_quantity` y `created_by`.
  - `movement_id` es único. El modelo es `ReceiptPutaway`, con alcance de empresa, y lo posee Recepciones.
  - No duplica el ledger: referencia el movimiento.
- **PT-02. Migración `0103_receipt_putaway_link`**, sobre `0102_gov_ctl09_actas`. Además de crear la tabla, hace el backfill autorizado. Liga solo los movimientos que cumplen todo esto:
  - son de tipo UBICACION, están POSTED y no están revertidos;
  - son una primera colocación (`source_location_id IS NULL`);
  - su `document_ref` es igual al código de una recepción de la misma empresa y del mismo almacén;
  - ese código es único en la empresa.

  Los códigos ambiguos, otro almacén, los revertidos, las reubicaciones y el texto libre no se ligan.
- **PT-03. Servicio (Recepciones, `purchasing.service`).**
  - `vincular_putaway` crea el vínculo.
  - `pendiente_de_ubicar` calcula, por producto, lo confirmado DISPONIBLE menos lo ligado, contando solo los vínculos cuyo movimiento terminó en DISPONIBLE.
  - `recepciones_con_pendiente` lista las recepciones con pendiente de un producto en un almacén.
  - `ubicar_desde_recepcion`:
    - bloquea la fila de la recepción;
    - da 404 `RECEIPT_NOT_FOUND` si la recepción es de otra empresa;
    - da 409 `PUTAWAY_EXCEEDS_RECEIPT_PENDING` si la cantidad supera lo pendiente;
    - usa el motor único `inventory.service.putaway`, crea el vínculo y audita `RECEIPT_PUTAWAY_ATTRIBUTED`.
- **PT-04. Rutas (Inventario, `inventory/api.py`).**
  - `GET /inventory/putaway/recepciones?warehouse_id=&product_id=`, con `inventario:view`.
  - `POST /inventory/putaway/desde-recepcion`, con `{receipt_id, product_id, target_location_id, quantity}` e `inventario:create`.
  - Viven en Inventario por la guardia aprobada de la Spec 021, que prohíbe rutas de put-away en Compras (`test_no_existe_endpoint_de_put_away_en_compras`). La guardia no se tocó.
- **PT-05. Put-away del expediente.** `imports/storage_flow.putaway_for_file` conserva todas sus comprobaciones y liga su movimiento con `vincular_putaway`.
- **PT-06. Cantidades del expediente.** «Ubicado» suma los vínculos de la recepción y el producto cuyo movimiento está POSTED, sin revertir y en DISPONIBLE. Ya no se cuenta por texto.
- **PT-07. Ubicación física del expediente.** `attributed_rows` atribuye por el vínculo del put-away y por el de la validación de la reubicación (`InventoryLocationValidation.receipt_id`), con la clave de la recepción en lugar del texto.
- **PT-08. Trazabilidad en pantalla.**
  - `logistics.putaway_trace` trae una fila por colocación y por reubicación, con recepción, producto, almacén, desde, hacia, cantidad, fecha y usuario.
  - El expediente la muestra en «Trazabilidad hasta la ubicación final».
- **PT-09. Auditoría.** Se añade al catálogo `RECEIPT_PUTAWAY_ATTRIBUTED` (de 486 a 487 entradas).
- **PT-10. Inventario → Put-away.** Si la mercancía elegida está DISPONIBLE, sin lote ni serial, aparece el selector opcional «Recepción de origen» (`<código> · pendiente <n>`):
  - con recepción, el put-away usa `desde-recepcion`;
  - sin ella, usa `/inventory/putaway` como hasta ahora.

## Estado

CONVERGED el 2026-11-11. Lo implementó DeepSeek y lo auditó Claude. El detalle de llamadas, reintentos y coste está en `evidence/putaway-trace/ATTEMPT_LOG.md`.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T018-PT-0 Arquitectura, decisiones y migración (diseño) | CLAUDE | n-a | SÍ (datos históricos) | n-a | n-a | autoridad y delta | — | decisiones de la dueña registradas |
| T018-PT-A Backend: vínculo, servicio, expediente, catálogo, guardias | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/{models,service}.py`, `imports/{service,storage_flow,physical_locations}.py`, catálogo, guardias | pytest PostgreSQL | PT-01 y PT-03 a PT-09 |
| T018-PT-A2 Modelo y migración 0103 (reclasificada tras agotar A) | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/models.py`, `alembic/versions/0103_receipt_putaway_link.py` | ida, vuelta e ida en PostgreSQL | PT-01 y PT-02 |
| T018-PT-A3 Pruebas del vínculo | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `tests/test_receipt_putaway_link.py` | pytest PostgreSQL | T1 a T6 |
| T018-PT-B Preparación de la prueba de reubicación, mypy y prueba del backfill | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `tests/test_importaciones_relocation.py`, `tests/test_receipt_putaway_backfill.py`, tipos | pytest PostgreSQL | sin regresión, backfill probado |
| T018-PT-C Pantallas y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `ImportacionUbicacion.tsx`, `tipos.ts`, `PutAwayPage.tsx`, `e2e/importaciones.spec.ts`, `e2e/putaway.spec.ts` | E2E Chrome PostgreSQL | 1280, 390 y 320 |
| T018-PT-D Rutas de Compras a Inventario (frontera de la Spec 021) | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/api.py`, `inventory/api.py`, pruebas, `PutAwayPage.tsx`, E2E | guardias 021 y 022 | sin ruta de put-away en Compras |
| T018-PT-E Evidencia, matriz y tarjeta de UAT | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada |
