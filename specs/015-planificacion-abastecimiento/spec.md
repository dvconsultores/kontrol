# Spec 015 · Planificación de abastecimiento y requisiciones

**Estado:** creada el 2026-11-10. **Fuente:** backlog B-031 («punto de reorden, rotación y proyección visibles al crear requisición»), DF-16 y el mapa de procesos «Detectar necesidad · revisar rotación/demanda» (`docs/roadmap/processes-to-specs-map.md`). **Autorización de implement:** encargo de la dueña del 2026-11-10, `SPEC015_ROTACION_PROYECCION_REORDER`.

`MATERIAL_DECISION_REQUIRED = 0`: los documentos no fijan ventana, horizonte, plazo, stock de seguridad ni clasificación. Todo eso es **política configurable y versionada por empresa**. No hay una fórmula KONTROL ni valores por defecto silenciosos: sin política, el resultado es `PLAN_NOT_CONFIGURED`.

## Resultado para la dueña

- **Maestros → Planificación de abastecimiento:** configura políticas (fuente de demanda, histórico, horizonte, plazo, stock de seguridad, métrica de rotación, alcance y vigencia) y bandas de rotación.
- **Compras → Planificación:** consulta, por producto y almacén, la demanda, la rotación, la proyección, el punto de reorden, el stock, la cobertura y la cantidad sugerida.
- **Compras → Requisiciones → Nueva:**
  - al elegir almacén y producto ve el panel de planificación y puede usar la cantidad sugerida o escribir otra;
  - al guardar queda una instantánea inmutable;
  - al reabrir la requisición la ve tal como se calculó.
- **Almacenamiento (Spec 018):** las reglas de almacenamiento pueden usar la banda de rotación que calcula esta Spec.

## Arqueología (autoridades reales)

| Hecho | Fuente | Consecuencia |
|---|---|---|
| La venta no crea movimientos OUT. El despacho confirmado reclasifica `PREPARADO → DESPACHADO`, con `document_ref = SHIPMENT:{id}`, solo con envío `READY` validado y factura emitida | `sales/service.py:confirm_shipment` | Fuente **`DISPATCHED_SALES`**: movimientos `RECLASIFICACION` con `target_state = DESPACHADO` |
| La devolución de venta reclasifica `DESPACHADO → DEVUELTO` (`SALES_RETURN:{id}`) | `sales/service.py:receive_return` | Neteo: se restan los movimientos `RECLASIFICACION` con `source_state = DESPACHADO` y `target_state = DEVUELTO` |
| `SALIDA_DESPACHO` (OUT) existe y se registra por `POST /inventory/operations/ship` | `inventory/api.py` | Fuente **`INVENTORY_ISSUES`**: movimientos de ese tipo, en magnitud |
| El reverso crea un movimiento `REVERSO` y enlaza los dos con `reversed_by_id` | `inventory/service.py:reverse_movement` | Se excluye todo movimiento con `reversed_by_id` y todo `REVERSO` |
| Las transferencias son `TRANSFERENCIA_SALIDA/ENTRADA`; también existen `AJUSTE_*`, `CONTEO`, `UBICACION`, `REUBICACION`, `ENTRADA_RECEPCION` y las demás reclasificaciones | `inventory/service.py` | **No son demanda** en ninguna fuente |
| La zona de negocio es fija (`America/Caracas`) y existen `inicio_del_dia_de_negocio` y `hoy_de_negocio` | `shared/clock.py` | La ventana se mide en días de negocio y no en el día del servidor |
| El saldo vendible es la suma de `qty_on_hand` en estado `DISPONIBLE`; el reservado vive en el ancla | `warehouse_sellable_on_hand`, `lock_balance` | Posición: existencia, reservado y disponible por separado |
| La orden de compra no tiene almacén; `quantity_ordered` está en la unidad tecleada y `quantity_received` en la base | `purchasing/models.py`, `service.py` | **`OPEN_SUPPLY_NOT_AVAILABLE = 1`**: no se puede calcular de forma fiable por almacén |
| No hay último costo, costo estándar ni lista de precios de compra | grep | Costo estimado de la línea **fuera de esta entrega**, declarado |
| La requisición no tiene almacén, ni detalle, ni edición, ni pantalla de alta | `purchasing/*`, `RequisicionesPage.tsx` | Esta Spec añade el almacén a la requisición, el detalle y la pantalla de alta, y la línea con instantánea |
| No hay índice por fecha en `inventory_movements` | migraciones | Índice `(company_id, warehouse_id, product_id, occurred_at)` |

## Decisiones

| ID | Decisión | Tipo |
|---|---|---|
| PL-01 | Módulo `app/modules/planning/` (modelos, motor y API), registrado en `main.py` y en `init_models` | DTD |
| PL-02 | Fuentes de demanda cerradas en código, cada una con su autoridad real: `DISPATCHED_SALES` (neto de devoluciones) e `INVENTORY_ISSUES`. Una fuente nueva exige su autoridad | SBR |
| PL-03 | `planning_policies` por empresa, con almacén opcional; la de almacén gana a la de empresa. Campos: código, nombre, `demand_source`, `lookback_days` (> 0), `horizon_days` (> 0), `lead_time_days` (≥ 0), `safety_mode` (`NONE` / `FIXED_QTY` / `DAYS`), `safety_value` (≥ 0), `rotation_metric` (`DEMAND_VELOCITY` / `TURNOVER`), estado, vigencia y versión. Una sola política ACTIVA por alcance (409) | DTD |
| PL-04 | `rotation_bands` por empresa: código, nombre, métrica, `lower_bound` (incluido), `upper_bound` (excluido, opcional), orden, estado y versión. No se admiten solapes dentro de una misma métrica (409). No hay bandas fijas en el producto | DTD |
| PL-05 | **Ventana.** Los últimos `lookback_days` días de negocio completos hasta hoy incluido: `[inicio_del_dia(hoy − lookback + 1), inicio_del_dia(hoy + 1))` sobre `occurred_at` | DTD |
| PL-06 | **Métodos, versionados como `AVG_CALENDAR_WINDOW_V1`:** `demanda_media_diaria = demanda_neta / lookback_days` (días calendario de la ventana); `proyección = media × horizon_days`; `stock_seguridad = 0 / valor / media × días`; `punto_de_reorden = media × lead_time_days + stock_seguridad`; `cobertura = disponible / media` (nula si la media es 0); `recomendación = max(0, proyección + stock_seguridad − disponible)` | SBR (§12–§25) |
| PL-07 | **Rotación.** `demand_velocity = media diaria`. `turnover = demanda_neta / existencia_media`, donde la existencia media es la media de los cierres diarios del estado `DISPONIBLE` en el almacén, reconstruidos desde el ledger (saldo inicial previo a la ventana más los deltas diarios). Si la existencia media es 0, el turnover es nulo y la banda no aplica. La métrica de la banda la elige la política | SBR (§16–§17) |
| PL-08 | **Historia.** Si no hay ningún movimiento del producto en el almacén antes del fin de la ventana: `INSUFFICIENT_HISTORY`, sin recomendación. Si el primer movimiento cae dentro de la ventana: `history_partial` con los días observados. Demanda 0 con historia es un resultado válido (media 0, proyección 0), no «sin datos» | SBR (§30–§32) |
| PL-09 | Todo en `Decimal` y en cantidad base; se cuantiza a 6 decimales en la frontera | SBR |
| PL-10 | La requisición gana `warehouse_id` (nulo para las antiguas). Endpoints nuevos: detalle con líneas y planificación; alta de línea con la cantidad tecleada, la presentación (conversión a base con el motor de la Spec 011), `use_recommendation` y `expected_policy_version`. Si la política cambió desde que se vio el panel: 409 `PLANNING_POLICY_STALE` | DTD |
| PL-11 | `requisition_line_plans`, una por línea e inmutable: política y versión, fuente, ventana, horizonte, plazo, stock de seguridad, demanda, media, métrica y banda de rotación, existencia, reservado, disponible, suministro (no disponible), punto de reorden, proyección, recomendación, cantidad pedida, diferencia, si se aceptó la sugerencia, actor y `calculated_at`. Un cambio de política no la toca | SBR (§28–§29) |
| PL-12 | **Spec 018.** `storage_rules.rotation_band_id` es un criterio más. El motor de almacenamiento pide la banda a `planning.service` y no recalcula nada. La clasificación guarda `input_rotation_band` | SBR (§19) |
| PL-13 | **Permisos.** Políticas y bandas: `maestros:view/create/edit`. Consulta de planificación: `compras:view`. Línea de requisición: `compras:create`, el permiso de hoy | SBR |
| PL-14 | **Auditoría**, con `record_audit` y acciones literales: `PLANNING_POLICY_CREATED/UPDATED`, `ROTATION_BAND_CREATED/UPDATED` y `REQUISITION_LINE_PLANNED`, que incluye `accepted` y `difference` | DTD |
| PL-15 | **Sin caché.** El cálculo se hace a petición con el índice por fecha y la UI vuelve a pedirlo. No se modifican las aprobaciones de la Spec 045: el contexto sigue siendo el mismo | DTD |

## Criterios de aceptación

1. Sin política: `PLAN_NOT_CONFIGURED` y la requisición manual sigue disponible.
2. Con política: la demanda solo cuenta los movimientos de la fuente, menos devoluciones y reversos. Las transferencias, los ajustes y los movimientos internos no cuentan.
3. La media, la proyección, el stock de seguridad, el punto de reorden y la recomendación siguen exactamente PL-06, con `Decimal`.
4. La rotación expone `demand_velocity` y el turnover cuando se puede calcular, y la banda configurada.
5. Producto sin historia: `INSUFFICIENT_HISTORY`. Demanda cero: 0 sin error. Historia parcial: se indica.
6. La línea de requisición guarda su instantánea; cambiar la política no la modifica, y la diferencia frente a la sugerencia queda registrada.
7. Una regla de almacenamiento con banda de rotación determina la zona usando la banda de esta Spec.
8. Aislamiento por empresa, permisos y auditoría.

## Fuera de alcance

- Suministro abierto por almacén (`OPEN_SUPPLY_NOT_AVAILABLE`).
- Costo estimado de la línea.
- Plazo por producto o proveedor.
- Métodos estadísticos, estacionalidad o IA.
- Aprobación por monto.
- Zonas A a E.
