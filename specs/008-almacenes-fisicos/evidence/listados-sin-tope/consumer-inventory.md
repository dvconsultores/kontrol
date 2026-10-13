# Inventario de consumidores (Discovery 05) · HEAD 6202994

## `GET /organization/warehouses`

| CONSUMER | EXPECTED_SHAPE | PASSES_LIMIT | PASSES_OFFSET | ASSUMES_ALL_ROWS | USES_TOTAL | MUST_CHANGE | RISK |
|---|---|---|---|---|---|---|---|
| `AlmacenesPage.tsx:50` (listado, `Paged<Warehouse>`) · `UbicacionesPage.tsx:39` · `OrdenesVentasPage.tsx:121` · `AjustesPage` · `MovimientosPage` · `ConteosPage` · `SerialesPage` · `ReservasPage` · `TransferenciasPage` (9 pantallas, `?company_id=`) | sobre `{items, total}` | no (defecto 50) | no | no (usan la primera página) | Almacenes sí | **no** (el defecto 50 no cambia) | ninguno |
| `PreparacionPage.tsx:70-83` | sobre, recorre páginas hasta `total` | **sí, `tanda = 200`** | sí | sí (por páginas) | sí | **sí**: 200 > 100 → 422; pasar a 100 | medio |
| `PutAwayPage.tsx:51` | sobre | **sí, `limit=500`** | no | sí (selector) | no | **sí**: 500 → 422; recorrer páginas (FR-001-188) | medio |
| E2E `putaway.spec.ts:87`, `picking.spec.ts:83` (`?limit=500`, buscan «otro almacén existente») | sobre | sí, 500 | no | no (uno distinto basta) | no | **sí**: 100 | bajo |
| E2E `sales-orders.spec.ts:54`, `receipts.spec.ts:46`, `inventory-confirmation.spec.ts:47`, `warehouse-structure.spec.ts:269` (sin `limit`) | sobre | no | no | no | parcial | no | ninguno |
| E2E/QA que hacen `POST` (`helpers/ventas.ts:125`, `billing`, `dispatch`, `order-confirmation`, `warehouse-a11y`, `functional-e2e-*`) | — | — | — | — | — | no | ninguno |
| `qa/functional-e2e-{local,inprocess}.py` (`?company_id=`) | sobre | no | no | no | no | no | ninguno |
| `qa/repro-almacenes-listado.py:57-58` (`limit=200`, `limit=500`) | sobre | sí | sí | — | — | **sí**: 100 (guion de medición manual) | bajo |
| backend `tests/test_warehouse_list_cost.py` (`limit=200` ×6, `limit=500` ×2; mundo de 40 + 6 almacenes) | sobre | sí | sí | sí (todo cabe) | sí | **sí**: 100 (todo sigue cabiendo; las aserciones no cambian) | bajo |
| backend `tests/test_warehouse_structure.py` (sin `limit`) | sobre | no | no | no | sí | no | ninguno |

## `GET /sales/pick-lists`

| CONSUMER | EXPECTED_SHAPE | PASSES_PAGE | ASSUMES_ALL_ROWS | USES_TOTAL | MUST_CHANGE | RISK |
|---|---|---|---|---|---|---|
| `PreparacionPage.tsx:136` (`?order_id=`, busca el plan vivo del pedido) | `{items}` | no | no (un pedido tiene ≤ 1 plan vivo; página por defecto 20 ≫) | no | no | ninguno |
| E2E `picking.spec.ts:222`, `order-confirmation.spec.ts:274` (`?order_id=`) | `{items}` | no | no | no | no | ninguno |
| E2E `putaway.spec.ts:413` (`/sales/pick-lists` **sin filtro**, filtra por `warehouse_id` en el cliente: necesita TODAS las de la empresa) | `{items}` | no | **sí** | no | **sí**: recorrer páginas con `page_size=100` hasta `total` (LT-21) | medio |
| QA, API client, backend tests con GET | — | — | — | — | no existen | — |

`CONSUMERS_UNKNOWN = 0` · `CONSUMERS_INVENTORIED = YES`. Cambios de consumidor: 2 pantallas, 3 suites E2E (+ helper), 1 guion
QA, 1 suite backend (valores de `limit` en pruebas). Ningún consumidor espera un array plano (`EXPECTS_RAW_ARRAY 0`).
