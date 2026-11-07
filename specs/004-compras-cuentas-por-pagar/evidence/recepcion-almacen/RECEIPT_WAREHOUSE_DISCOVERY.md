# Recepción: quién elige el almacén

Medido el 2026-11-07 sobre `c325c21`. Spec dueña: 004, capacidad 019. FR-004-030, US-004-005, actor Almacén; dependencia 008 «almacén de la empresa».

| # | Pregunta | Respuesta | Evidencia |
|---|---|---|---|
| 1 | ¿Se selecciona hoy? | No: texto libre con «Identificador del almacén» | `RecepcionesPage.tsx` |
| 2 | ¿La orden fija el almacén? | No: `PURCHASE_ORDER_FIXES_WAREHOUSE = 0` | `purchase_orders` no tiene columna de almacén; solo `goods_receipts` |
| 3 | ¿Hay almacén por defecto? | No | `create_receipt` lo exige |
| 4 | ¿Se puede cambiar? | Lo decide quien crea la recepción | `ReceiptCreate.warehouse_id` obligatorio |
| 5 | ¿Cuáles son elegibles? | Los de la empresa | `warehouse_belongs_to` |
| 6 | ¿Inactivos? | El backend no comprueba el estado | `create_receipt`; `RECEIPT_ACTIVE_WAREHOUSE_POLICY = ANY_COMPANY_WAREHOUSE` |
| 7 | ¿El backend protege empresa? | Sí | `warehouse_belongs_to`; verificación de servicio en verde |
| 8 | ¿Debe conocerse el identificador? | Sí, antes del arreglo | Un código da `WAREHOUSE_NOT_FOUND`: `db.get` busca por clave primaria |
| 9 | ¿Hay patrón hermano? | Sí | `useAlmacenesDeEmpresa`, 10 pantallas |
| 10 | ¿Ubicación o almacén? | Solo almacén en la creación | `ReceiptCreate` |

`WAREHOUSE_SELECTION_AUTHORITY = RECEIPT_OPERATOR`.

## Reproducción
`REPRO_BEFORE`: 14 de 14 pruebas en rojo contra la pantalla real. `USER_ACTION_REQUIRED`: escribir un identificador. `INTERNAL_IDENTIFIER_REQUIRED = 1`. `VISIBLE_ALTERNATIVE_EXISTS = 0`: la tabla de Almacenes muestra código y nombre, no el identificador; solo aparece en la URL del detalle. `OPERATION_BLOCKED_WITHOUT_INTERNAL_ID = 1`.

`PRODUCT_REQUIREMENT_VIOLATED = 1`: FR-004-030 y US-004-005 exigen que Almacén reciba contra orden, y la norma de completitud exige que el proceso se opere por interfaz. `ROOT_CAUSE_PROVEN = 1`.

## Resultado
`BACKEND_CHANGE_REQUIRED = 0`. Selector con la autoridad compartida. Una selección fuera de la lista no se envía. Vitest 14 de 14, mutaciones 12 de 12.

`CROSS_COMPANY_WAREHOUSE_BACKEND_PROTECTION = PASS` a nivel de servicio (`test_recepcion_almacen_empresa.py`). Las pruebas HTTP existentes (`test_spec019_receipt.py`, `test_mc_purchasing_ap_ab.py`) se omiten en SQLite: siguen pendientes de PostgreSQL.

Estado de la deuda: `TECHNICAL_FIX_COMPLETE_LOCAL / FULL_RUNTIME_E2E_PENDING`.

**La recepción por interfaz sigue bloqueada en el paso siguiente:** ver RECEPCION-LINEA-ORDEN-TEXTO-LIBRE.
