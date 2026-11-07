# Spec 019 · delta RECEPCION-LINEA-ORDEN-INTEGRIDAD

Delta dirigido dentro de la Spec 004, capacidad 019. Autorizado por la dueña en el encargo RECEPCION-LINEA-ORDEN-INTEGRIDAD-01 (2026-11-07). Evidencia: `evidence/recepcion-linea-integridad/`.

## Problema

Dos causas demostradas por separado:

- **RC-UI, `INTERNAL_ORDER_LINE_ID_AS_USER_INPUT`:** recibir exigía escribir un identificador que ninguna pantalla muestra.
- **RC-INTEGRITY, `ORDER_LINE_PRODUCT_INVARIANT_MISSING`:** `order_line_id` y `product_id` eran dos fuentes independientes. Una línea con producto A y `product_id` B entraba al inventario como B, al costo de A, y acumulaba recibido en A.

## Requisitos

| ID | Requisito |
|---|---|
| FR-019-015 | El producto de una línea de recepción es el de su línea de orden. Una contradicción se rechaza con 422 `RECEIPT_LINE_PRODUCT_MISMATCH`, sin efectos |
| FR-019-016 | La línea se elige de las líneas de la orden de la recepción, con etiqueta humana. El producto se deriva y no se elige |
| FR-019-017 | Una línea recibida del todo sigue siendo elegible: el sobrante se registra, no se impide (FR-019-012) |
| FR-019-018 | Cambiar de línea vacía la presentación. Cambiar de recepción vacía lo capturado para la línea |

## Diseño

- API sin cambios. `product_id` se conserva por compatibilidad y el backend exige que coincida.
- Comprobación en `add_receipt_line`, después de `_require_product`: un producto de otra empresa sigue respondiendo que no existe. Va antes de calcular unidad, crear la línea o auditar.
- Las líneas salen de `GET /purchasing/orders/{id}`, no del listado paginado. Los nombres salen de `GET /maestros/catalogos/items/{id}`: un producto inactivo o fuera de la primera página también se resuelve.
- El producto se muestra en un campo de solo lectura.

## Constitution gate

Sin migración, sin esquema, sin dependencia, sin cambio de API. Multiempresa: se conservan las protecciones existentes y hay pruebas. Dinero: no se toca fórmula alguna; el invariante impide que un costo caiga en otro producto. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · MATERIAL OQ 0.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| RLI-A | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `RecepcionesLinea.test.tsx` | Vitest | 18 en rojo por el contrato |
| RLI-B | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `test_recepcion_linea_integridad.py` | pytest | Rojo solo donde falta el rechazo |
| RLI-C | CLAUDE | n-a | No | n-a | n-a | Este delta | — | Diseño congelado |
| RLI-D | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `service.py`, `test_spec019_receipt.py` | pytest | BT en verde |
| RLI-E | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `RecepcionesPage.tsx` | Vitest | FT en verde |
| RLI-F | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `RecepcionesLinea.test.tsx` | Vitest | Mutantes reales muertos |
| RLI-G | CLAUDE | n-a | No | n-a | n-a | Arnés temporal | Mutaciones | 0 supervivientes requeridos |
| RLI-H | DEEPSEEK | deepseek-v4-flash | No | Sí | 2 | `e2e/receipts.spec.ts` | TSC, ESLint | Preparada |

El invariante vive en un flujo de compras, sin tocar autenticación, permisos ni aislamiento. Claude fijó el diseño y el texto exacto de la comprobación antes de delegarla.

## Trazabilidad

| Requisito | Prueba |
|---|---|
| FR-019-015 | BT-01 a BT-12, `test_no_se_recibe_otro_producto_contra_la_linea_de_orden` |
| FR-019-016 | FT-01 a FT-09, FT-12 a FT-15 |
| FR-019-017 | FT-16, `un sobrante no deja pendiente negativo` |
| FR-019-018 | FT-10, FT-11, `volver a una línea no recupera la presentación anterior` |
