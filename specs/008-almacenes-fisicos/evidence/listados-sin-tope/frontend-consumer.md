# Frontend (Discovery 05 / W19 / W27)

| Pantalla | Antes | Después |
|---|---|---|
| `PreparacionPage` (cola de picking, selector de almacén) | recorría páginas con `tanda = 200` (> 100 → 422) | `listAllWarehouses()` (páginas de 100 hasta `total`) |
| `PutAwayPage` (selector de almacén) | `?limit=500` (truncaba en 500 y ahora sería 422) | `listAllWarehouses()` |
| `PreparacionPage` (`/sales/pick-lists?order_id=`) | lee `items` y busca el plan vivo | sin cambio: un pedido tiene ≤ 1 plan vivo; la página por defecto (20) sobra |
| 9 pantallas con `?company_id=` (defecto 50) | sobre `{items,total}` | sin cambio (el defecto no cambia) |

No hay pantalla que liste pick-lists en tabla: no hay paginador nuevo, ni UX nueva, ni modal. `WarehouseSummary` pasa a
`src/api/types.ts` (dos interfaces locales idénticas se retiran); `listAllWarehouses` y `WarehousePage` en
`src/api/organization.ts` junto a `listAllCompanies` (mismo patrón, mismo `TAMANO_MAXIMO_DE_PAGINA = 100`); cuatro
pruebas Vitest nuevas en `organization.test.ts` (230 → 3 llamadas con `limit=100&offset=0/100/200`; 2 → 1 llamada; 0 → `[]`;
nunca pide `limit` fuera de contrato). API client: manual (no generado); tipos actualizados en origen. Frontend Master
Standard intacto (páginas enrutadas, estados de carga/vacío/error, sin scroll horizontal nuevo).
