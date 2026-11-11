# IMP-05 · Comparar ofertas, adjudicar el proveedor y emitir la orden: evidencia

Delta: `../../spec004-quote-award-delta.md`. Registro de intentos: `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE. Backend, migración `0099_quote_award`, API, catálogo de auditoría y pruebas |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE. Compras → Cotizaciones: comparar, adjudicar y emitir la orden, en Chrome sobre PostgreSQL |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 90 a 95 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `compare_quotes`, `award_quote` y `order_from_quote` en `purchasing/service.py` |
| DATABASE_COMPLETE | 0099: `supplier_quotes.awarded_at`, `awarded_by` y `award_reason`; `purchase_orders.quote_id` con su FK y el índice único `uq_purchase_orders_quote_id`. En PostgreSQL nuevo: sube a la cabeza → baja → vuelve a subir, con una sola cabeza |
| API_COMPLETE | `GET /purchasing/quotes/comparison`, `POST /purchasing/quotes/{id}/award` y `POST /purchasing/quotes/{id}/order`. La lista de cotizaciones y `order_dict` ganan claves nuevas (adiciones compatibles) |
| FRONTEND / SCREEN / MENU_COMPLETE | Compras → Cotizaciones (menú ya existente): la sección «Comparar ofertas» (selector «Artículo a comparar»), las acciones «Adjudicar» y «Emitir orden», el proveedor por nombre y los estados en español (Vigente, Vencida, Adjudicada, Orden emitida) |
| PROCESS_COMPLETE | Comparar → adjudicar con motivo → emitir la orden en DRAFT ligada a la cotización → flujo normal de la orden (enviar → aprobación por niveles → aprobar), probado en el backend |
| FIELDS_COMPLETE | Cantidad, precio unitario, descuento (mostrado tal cual), importe, plazo de entrega, vigencia, estado y motivo |
| ROLES_COMPLETE | `compras:view` compara; `compras:approve` adjudica; `compras:create` emite. La pantalla muestra cada acción solo con su permiso (`puede`) |
| AUDIT_COMPLETE | `PURCHASE_QUOTE_AWARDED` y `PURCHASE_QUOTE_CONVERTED` en el catálogo (464 entradas) |
| SECURITY_COMPLETE | Todo filtrado por la empresa del contexto: una cotización de otra empresa da 404 (probado) |
| DOCUMENT / REPORTING | NOT_APPLICABLE. La orden de compra es el documento resultante, y su emisión ya existía |
| E2E_COMPLETE | `e2e/cotizaciones-adjudicacion.spec.ts` |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_purchasing_quote_award.py` (comparación ordenada y aislada; adjudicación correcta; cinco negativas; orden copiada; idempotencia; flujo normal; condiciones; `quote_dict`) | PASS en SQLite y PostgreSQL |
| `tests/test_purchasing.py`, catálogo de auditoría, guardias de cabeza | PASS en PostgreSQL (73) |
| E2E `cotizaciones-adjudicacion.spec.ts`, Chrome sobre PostgreSQL efímero migrado, analizador real | PASS a 1280, 390 y 320 |
| Axe (WCAG 2.0/2.1 A y AA) en Cotizaciones, después de emitir la orden | 0 graves o críticas a 1280, 390 y 320. Sin desbordamiento horizontal a 390 ni a 320 |
| Vitest de contrato y autoridad (gate-coverage, authority-surfaces, audit-completeness, query-contract), con las fixtures regeneradas | 383 PASS |
| Vitest completo | 1911/1911. Hubo un fallo intermedio: la etiqueta «Producto a comparar» rompía el selector genérico `/^Producto/` de `catalogoSelectores.test.tsx`; la llamada 3 la renombró a «Artículo a comparar» |
| build de producción | correcto |
| typecheck · lint · ruff | limpio · limpio · limpio |
| mypy | Sin errores nuevos en las funciones del delta: la llamada 3 cerró los tres de tipo (UUID frente a `str`, `Decimal` frente a `float`). El fichero conserva los errores que ya tenía en HEAD |

## Fuera de alcance (deudas)

- **QUOTE-REQUISITION-LINK:** la cotización no queda ligada a la requisición que la originó.
- **ORDENES-UI-ETIQUETAS:** la tabla de Órdenes muestra el UUID del proveedor y las acciones con su código interno.
