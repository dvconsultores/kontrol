# Selectores de terceros · inventario de consumidores

Inventario hecho sobre el árbol local `814afc1`, sin incluir pruebas. Búsquedas: `maestros/terceros`, `Party`, `PagedResult<Party>`,
`customer_id`, `supplier_id` y `party_id`. No hay hook ni helper intermedio: cada pantalla hace su propio `apiFetch`.

## Contrato de partida

- `GET /maestros/terceros`: acepta `q` (busca en `name`, `tax_id` y `code`), `status`, `page` (1) y `page_size` (20, máximo 100). Filtra por
  la empresa del `CompanyContext`, ordena por `created_at` y devuelve `items`, `total`, `page` y `page_size`. **No filtra por rol.**
- `GET /maestros/terceros/{party_id}`: valida la empresa y devuelve `id`, `code`, `name`, `tax_id`, `roles`, `status` y otros campos.
- `Party.roles` es un JSON con valores como `CLIENTE`, `PROVEEDOR`, `TRANSPORTISTA` o `CONDUCTOR`. `POST .../roles/{role}` los guarda en
  mayúsculas; `POST /maestros/terceros` los guarda tal como llegan. `Party.status` puede ser `ACTIVE` o `INACTIVE` (`.../deactivate`).

## Consumidores

| FILE | FIELD | PROCESS | ENDPOINT/QUERY | FILTRO HOY | TRUNCADO | CLASIFICACIÓN |
|---|---|---|---|---|---|---|
| `ventas/cotizaciones/CotizacionesPage.tsx` | Cliente (`newCustomer`) | `POST /sales/quotes` | `/maestros/terceros` (20) | ninguno | Sí | REAL_DEFECT |
| `ventas/ordenes/OrdenesVentasPage.tsx` | Cliente (`newCustomer`) | `POST /sales/orders` | `/maestros/terceros` (20) | `roles.includes("CLIENTE")` **sobre los 20** | Sí, y peor | REAL_DEFECT |
| `ventas/facturas/FacturasVentasPage.tsx` | Cliente (`newCustomer`) | `POST /sales/invoices` | `/maestros/terceros` (20) | `roles.includes("CLIENTE")` sobre los 20 | Sí | REAL_DEFECT |
| `ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | Cliente ×2 (`newParty` en cobro, `advParty` en anticipo) | `POST /sales/collections`, `POST /sales/customer-advances` | `/maestros/terceros` (20) | ninguno | Sí | REAL_DEFECT |
| `compras/cotizaciones/CotizacionesComprasPage.tsx` | Proveedor (`newSupplier`) | `POST /purchasing/quotes` | `/maestros/terceros` (20) | ninguno | Sí | REAL_DEFECT |
| `compras/ordenes/OrdenesComprasPage.tsx` | Proveedor (`newSupplier`) | `POST /purchasing/orders` | `/maestros/terceros` (20) | `roles.includes("PROVEEDOR")` sobre los 20 | Sí | REAL_DEFECT |
| `compras/facturas/FacturasProveedorPage.tsx` | Proveedor (`newSupplier`) | `POST /purchasing/invoices` | `/maestros/terceros` (20) | `roles.includes("PROVEEDOR")` sobre los 20 | Sí | REAL_DEFECT |
| `compras/notas/NotasComprasPage.tsx` | Proveedor (`newSupplier`) | `POST /purchasing/credit-notes` | `/maestros/terceros` (20) | ninguno | Sí | REAL_DEFECT |
| `compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | Proveedor ×3 (`newParty` en pago, `advParty` en anticipo, `schedParty` en programación) | `POST /purchasing/payments`, `/advances`, `/payment-schedules` | `/maestros/terceros` (20) | ninguno | Sí | REAL_DEFECT |
| `fiscal/retenciones/RetencionesPage.tsx` | Tercero (`partyId`) | `POST /fiscal/withholdings/calculate`, que crea una retención de 004 (CxP) | `/maestros/terceros` (20) | ninguno; muestra solo `name` | Sí | REAL_DEFECT |
| `regulatorio/vehiculos/VehiculosPage.tsx` | Conductor (`partyId`) | `POST /regulatory/drivers` | `/maestros/terceros` (20) | ninguno; muestra solo `name` | Sí | REAL_DEFECT |
| `ventas/estado-de-cuenta/EstadoDeCuentaPage.tsx` | Cliente | consulta | bucle `page_size=100` hasta `total` | — | No | LOAD_ALL_VALID (deuda de escala) |
| `tesoreria/reembolsos/ReembolsosPage.tsx` | Cliente | consulta o devolución | bucle `page_size=100` hasta `total` | — | No | LOAD_ALL_VALID (deuda de escala) |
| `maestros/terceros/TercerosPage.tsx` | — | listado con `q` | — | — | — | OUT_OF_SCOPE (listado, no selector) |

En total hay **11 pantallas y 14 selectores**. En ninguna se usa la consulta de terceros para otra cosa que las opciones del selector.

## Backend: frontera de dominio actual

`sales._require_party` y `purchasing._require_party` solo comprueban que el tercero existe y es de la empresa. No miran ni el rol ni el estado.

| Función | Módulo | Dirección o semántica |
|---|---|---|
| `create_quote`, `create_order`, `create_invoice`, `create_credit_note`, `create_debit_note` | sales | cliente |
| `create_quote`, `create_order`, `create_invoice`, `create_credit_note`, `create_schedule` | purchasing | proveedor |
| `register_payment(direction)`, `register_advance(direction)` | purchasing, **compartidas** | `OUT` es proveedor (CxP) e `IN` es cliente (CxC, desde `sales/api.py`) |
| `create_withholding` | purchasing, **compartida** | `sales/api.py /withholdings-suffered` es cliente; `purchasing/api.py` y `fiscal.calculate_withholding` son proveedor |
| `customer_balance`, `customer_statement`, `customer_credits` | sales/api, lectura | historia: no se toca |
| `regulatory.create_driver` | regulatory | **no valida el tercero en absoluto**: acepta un `party_id` de otra empresa |
| `regulatory.create_vehicle(owner_party_id)` | regulatory | **no valida** `owner_party_id` |
