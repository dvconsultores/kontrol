# EVIDENCIA DE COMPORTAMIENTO — 23/23

Sobre PostgreSQL 18.6, con el fixture multiempresa de N5: T1 con las empresas
A y B, T2 con C, y usuarios `ua`, `ub`, `uab`, `uc`.

## 1. Qué se prueba por cada tipo

| Comprobación | Cómo |
|---|---|
| La entidad existe de verdad | Se siembra por el modelo y se cuenta en su tabla |
| Se vincula en su empresa | `POST /documentos/{id}/vinculos` → 200 |
| No se vincula un recurso de otra empresa | → 404 |
| Y el vínculo cruzado no queda escrito | `document_links` sin la fila |
| No se vincula un recurso de otro tenant | → 404 |

## 2. Resultado

| # | Tipo | Entidad real | Alcance propio | Entre empresas | Entre tenants | Veredicto |
|---:|---|---|---|---|---|---|
| 1 | `ApprovalRequest` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 2 | `PurchaseRequisition` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 3 | `PurchaseOrder` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 4 | `GoodsReceipt` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 5 | `SupplierInvoice` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 6 | `Payment` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 7 | `SalesOrder` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 8 | `SalesInvoice` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 9 | `Shipment` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 10 | `SalesReturn` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 11 | `InventoryAdjustment` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 12 | `StockCount` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 13 | `Warehouse` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 14 | `Party` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 15 | `CatalogItem` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 16 | `PermitInstance` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 17 | `OfficialDocument` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 18 | `TransportVehicle` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 19 | `TransportDriver` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 20 | `BankTransaction` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 21 | `CashSession` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 22 | `Reconciliation` | ✅ | PASS | BLOCKED | BLOCKED | **PASS** |
| 23 | `HomologationRecord` | ✅ | PASS | `N/A — de instalación` | `N/A` | **PASS** |

**48 pruebas.** Ninguna saltada.

## 3. El registro sigue cerrado

Se intentaron cuatro nombres inventados y los cuatro se rechazaron con
`RESOURCE_TYPE_UNKNOWN`:

- `AnyModel` — un modelo cualquiera
- `parties` — un nombre de tabla
- `app.modules.master_data.models.Party` — una ruta de importación
- `Party; DROP TABLE documents` — una inyección

No hay reflexión ni resolución dinámica: el registro es un diccionario y lo que
no está, no existe.

## 4. Lo que estas pruebas sustituyen

Antes de N9, la única vinculación ejercitada era la de `ApprovalRequest`. El
propio `REM-046-001` lo escribió sin adornos: *«registré dieciséis tipos y probé
uno»*.

Marcar los otros como funcionales por estar en una lista es exactamente el error
que 046 vino a evitar en el legado documental —confundir una referencia con una
evidencia— y que se repitió en su propia matriz de consumidores.

## 5. Sobre la parametrización

Está permitida y aquí se usa, pero con condiciones: cada tipo tiene su fixture
real, su resolución real y un fallo que **nombra el tipo**. Una parametrización
que no distinguiera cuál falló valdría lo mismo que la prueba genérica que
sustituye.

Y si un tipo no puede sembrarse, su caso **falla**. Saltarlo lo escondería entre
los que sí funcionan, que es como se llegó hasta aquí.
