# Spec 004 · delta: comparar ofertas, adjudicar el proveedor y emitir la orden (IMP-05)

Encargo `SPEC018_REVALIDACION_Y_CONTINUACION`, del 2026-11-11. Spec dueña: 004, cotizaciones y órdenes de compra. Origen: la fila IMP-05 de `specs/018-importaciones/IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.md`, revalidada como PARTIAL. Evidencia: `evidence/quote-award/`.

## Requisito

DOCX de importación §1.6: «Seleccionar y confirmar proveedor». Se ejecuta entre la aprobación de la solicitud (§1.5) y la emisión de la orden (§1.8).

**Medido el 2026-11-11.** En Compras → Cotizaciones solo se pueden crear cotizaciones y añadirles líneas. Faltan tres cosas:
- comparar las ofertas de un mismo producto;
- registrar la adjudicación a un proveedor;
- emitir la orden desde la cotización elegida.

Hoy la orden se escribe a mano y su proveedor no queda ligado a ninguna oferta.

## Decisiones (fijadas por Claude; sin decisión material abierta)

- **QA-01. Quién elige.** El sistema compara y el usuario adjudica, con un motivo obligatorio. No hay «mejor oferta» automática ni ranking entre monedas. La tabla se ordena por moneda, luego por precio unitario ascendente, luego por plazo de entrega y por último por código. Solo es una presentación.
- **QA-02. Montos.** Importe de la línea = cantidad × precio unitario, cuantizado a 0,01 con ROUND_HALF_EVEN. Es la misma base que el contexto de aprobación de la orden (`_order_context`). El campo `discount` no tiene un significado monetario fijado en compras (ningún total lo usa), así que se muestra tal cual y no entra en ningún cálculo.
- **QA-03. Estados.** El precedente es la Spec 029 de Ventas (ACCEPTED → CONVERTED).
  - ACTIVE → AWARDED: se adjudica.
  - AWARDED → CONVERTED: se emite la orden.

  La vigencia no se guarda: se calcula, con `validity_until` nulo como «sin vencimiento» y la fecha de negocio `hoy_de_negocio()`.
- **QA-04. Adjudicar.** Se exige todo esto:
  - la cotización está ACTIVE;
  - no ha vencido;
  - tiene al menos una línea;
  - el proveedor sigue activo como PROVEEDOR («confirmar proveedor»);
  - hay un motivo.

  Se guardan `awarded_at`, `awarded_by` y `award_reason`. Permiso: `compras:approve`, el mismo que decide sobre la orden.
- **QA-05. Emitir la orden.** Desde una cotización AWARDED se crea la orden en DRAFT con el proveedor, la moneda y las condiciones de la cotización, y una línea por cada línea de la cotización (cantidad, precio, descuento y referencia fiscal). La orden guarda `quote_id`.
  - La conversión es idempotente: si la cotización ya generó su orden, devuelve la que existe.
  - Hay un índice único parcial sobre `purchase_orders.quote_id` para la concurrencia.
  - La orden sigue su flujo normal: enviar → aprobación por niveles (IMP-04) → aprobar. Permiso: `compras:create`.
- **QA-06. Auditoría.** Dos eventos nuevos en el catálogo:
  - `PURCHASE_QUOTE_AWARDED`, con `status`, `supplier_id` y `reason`;
  - `PURCHASE_QUOTE_CONVERTED`, con `order_id` y `status`.
- **QA-07. Aislamiento.** Todo filtra por la empresa del contexto, y una cotización de otra empresa da 404.

## Alcance

- **Backend:** el modelo, la migración `0099_quote_award` y el servicio con `compare_quotes`, `award_quote` y `order_from_quote`.
- **API:**
  - `GET /purchasing/quotes/comparison?product_id=`;
  - `POST /purchasing/quotes/{id}/award`;
  - `POST /purchasing/quotes/{id}/order`;
  - `GET /purchasing/quotes`, que ahora devuelve también el nombre del proveedor, la adjudicación y la orden.

  Todo son adiciones compatibles.
- **Frontend:** Compras → Cotizaciones, con:
  - la sección «Comparar ofertas»;
  - las acciones «Adjudicar» y «Emitir orden»;
  - el proveedor por su nombre y los estados en español.
- **E2E:** de la comparación a la orden aprobada.

**Fuera de alcance:**
- relacionar la cotización con la requisición;
- negociar dentro de la plataforma;
- las etiquetas de la pantalla de Órdenes (deuda ORDENES-UI-ETIQUETAS).

## Estado

CONVERGED el 2026-11-11. Implementado por DeepSeek y auditado por Claude (3 llamadas y 3 reintentos, $0,047). Backend PASS en SQLite y PostgreSQL. E2E PASS en Chrome a 1280, 390 y 320. Axe sin faltas graves. Evidencia en `evidence/quote-award/`.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T004-QA-A Backend, migración y pruebas | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/{models,service,api}.py`, `alembic/versions/0099_quote_award.py`, catálogo de auditoría, guardias de cabeza, `tests/test_purchasing_quote_award.py` | pytest en SQLite y PostgreSQL | QA-01 a QA-07 en PASS |
| T004-QA-B Pantalla y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `CotizacionesComprasPage.tsx`, tipos, `e2e/cotizaciones-adjudicacion.spec.ts` | E2E en Chrome sobre PostgreSQL | PASS a 1280, 390 y 320 |
| T004-QA-C Revalidación, delta, evidencia, matriz y tarjeta | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada |
