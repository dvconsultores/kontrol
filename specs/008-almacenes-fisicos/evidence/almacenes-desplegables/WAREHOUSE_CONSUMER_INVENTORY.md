# Inventario de consumidores de almacenes

Medido el 2026-11-07 sobre `5335eb0`. Todas las pantallas requieren empresa activa y ninguna filtra por estado: `ACTIVE_POLICY_BEFORE = ACTIVE_POLICY_AFTER = SIN_FILTRO_DE_ESTADO`.

| FILE | COMPONENT | USE_CASE | CURRENT_CALL | LIMIT | OFFSET | USES_LIST_ALL | NEEDS_COMPLETE_SET | COMPANY_SCOPED | ACTIVE_FILTER | FIX_REQUIRED | WHY |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inventario/ajustes/AjustesPage.tsx` | AjustesPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/transferencias/TransferenciasPage.tsx` | TransferenciasPage | Dos selectores | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/conteos/ConteosPage.tsx` | ConteosPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/reservas/ReservasPage.tsx` | ReservasPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/seriales/SerialesPage.tsx` | SerialesPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/movimientos/MovimientosPage.tsx` | MovimientosPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `ventas/ordenes/OrdenesVentasPage.tsx` | OrdenesVentasPage | Selector | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `organizacion/ubicaciones/UbicacionesPage.tsx` | UbicacionesPage | Filtro | `apiFetch` directo | 50 | 0 | No | Sí | Sí | Ninguno | Sí | Primera página |
| `inventario/putaway/PutAwayPage.tsx` | PutAwayPage | Selector | `listAllWarehouses` | 100 | Recorre | Sí | Sí | Por cabecera; clave sin empresa | Ninguno | Endurecido | Sin aviso de error ni clave por empresa |
| `ventas/preparacion/PreparacionPage.tsx` | PreparacionPage | Filtro | `listAllWarehouses` | 100 | Recorre | Sí | Sí | Por cabecera; clave sin empresa | Ninguno | Endurecido | Igual |
| `organizacion/almacenes/AlmacenesPage.tsx` | AlmacenesPage | Tabla con búsqueda | `apiFetch` directo | 50 | 0 | No | No | Sí | Ninguno | No | PRODUCT_PAGINATED_LIST: deuda aparte |
| `organizacion/almacenes/AlmacenDetallePage.tsx` | AlmacenDetallePage | Un registro | `apiFetch` | — | — | No | No | Sí | — | No | PRODUCT_SINGLE_RECORD |
| `compras/recepciones/RecepcionesPage.tsx` | RecepcionesPage | Texto libre | Ninguna | — | — | No | — | — | — | No | FALSE_POSITIVE de truncado; ver RECEPCION-ALMACEN-TEXTO-LIBRE |
| `inventario/existencias`, `valorizacion`, `ventas/despacho`, `devoluciones` | Varias | Solo columna o id | Ninguna | — | — | No | No | — | — | No | FALSE_POSITIVE |

Pantallas de Government: ningún consumidor. `GOVERNMENT_ANALOGOUS_DEFECT_FOUND = 0`.
