# Implementación (W25–W28)

| Tarea | Fichero(s) | Cambio | Ejecutor |
|---|---|---|---|
| T01 | `app/modules/organization/warehouse_api.py` | `from fastapi import … Query`; `limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)` solo en `search_warehouses` | DeepSeek (flash), AUDIT_PASS, aplicado verbatim |
| T02 | `app/modules/sales/api.py` | `list_pick_lists`: `page`/`page_size` canónicos, `total` por `count` en SQL dentro de empresa y filtro, orden `created_at desc, id`, `offset`/`limit` en SQL, sobre `{items,total,page,page_size}`; docstring | Claude |
| T03 | `tests/test_listados_sin_tope.py` | LT-01…16, 23, 24 + invariantes SQL/estático (1 100 listas, empates de instante, dos empresas, cabecera ajena) | Claude |
| T04 | `src/api/types.ts`, `src/api/organization.ts`, `src/api/organization.test.ts`, `PutAwayPage.tsx`, `PreparacionPage.tsx` | `WarehouseSummary`, `WarehousePage`, `listAllWarehouses` + 4 pruebas; las dos pantallas lo consumen | DeepSeek (flash), AUDIT_PASS, aplicado verbatim |
| T05 | `tests/test_warehouse_list_cost.py`, `qa/repro-almacenes-listado.py`, `e2e/putaway.spec.ts`, `e2e/picking.spec.ts` | `limit=200/500 → 100` (9 + 2 + 1 + 1 sitios); helper E2E `todasLasListasDePreparacion` que recorre páginas de 100 | DeepSeek (flash), AUDIT_PASS, aplicado verbatim |

Sin migración, sin cambio de esquema, sin tocar `RequestContext`, `X-Kontrol-Company`, permisos ni `POST /sales/pick-lists`.
