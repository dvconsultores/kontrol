# Suministro abierto por almacén: evidencia

- **Delta:** `../../spec015-open-supply-by-warehouse-delta.md`.
- **Cadena y decisión de la dueña:** `OPEN_SUPPLY_TRACEABILITY_CURRENT.md`.
- **Intentos:** `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: `purchase_order_lines.destination_warehouse_id` (migración `0106`) y una sola autoridad, `purchasing/open_supply.py` |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: la planificación descuenta lo pedido y no recibido por almacén. Se ve en la necesidad, la requisición, las órdenes y las recepciones |
| OWNER_READINESS_STATUS | Pasos 134 a 143 de la tarjeta. La UAT local (`kuat`) está en `0106`, con el backend y el frontend arriba. Humo autenticado: `suministro-abierto.spec.ts` contra la UAT, 1/1. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | Autoridad única en `open_supply.py`: `cantidad_abierta` para una línea y `suministro_abierto` para un lote, con una sola consulta agregada sin N+1. Lo consume el mismo motor (`compute_plan`); no hay un segundo planificador. Compras añade `fijar_destino_de_linea` (bloqueo de fila y auditoría) y el bloqueo 409 `RECEIPT_LINE_OTHER_WAREHOUSE` |
| DATABASE_COMPLETE | `0106_open_supply_by_warehouse`: una columna nullable con su FK y el índice (destino, producto), más 4 columnas nullable en `replenishment_needs`. Sin backfill: lo histórico queda NO_ATTRIBUTION. Ida, vuelta e ida en PostgreSQL. `n10` sin diferencias nuevas |
| API_COMPLETE | `POST /purchasing/orders/{id}/lines/{line_id}/destination` (`compras:create`). `destination_warehouse_id` es opcional al crear una línea. El detalle de la orden añade `destination_warehouse`, `open_quantity` y `can_set_destination`. La necesidad añade `open_supply` y `projected_available` (en la causa y en la situación actual). El plan rellena `open_supply`. Sin rutas eliminadas |
| FRONTEND / SCREEN_COMPLETE | Órdenes: almacén destino obligatorio al agregar una línea; un panel «Líneas de la orden» con el pendiente para la planificación y el destino; fijar el destino. Necesidad: «Suministro abierto» y «Disponible proyectado». Requisición: el valor del suministro abierto. Recepciones: el destino en la etiqueta de la línea. Sin UUID |
| MENU_COMPLETE | Compras → Órdenes, Compras → Necesidades de reposición y Compras → Recepciones (menús existentes) |
| PROCESS_COMPLETE | Necesidad → requisición → cotización → orden con destino → aprobación → la necesidad se resuelve sin duplicarse → recepción parcial → el pendiente baja → cierre → el pendiente queda en 0 y la necesidad reaparece si sigue faltando |
| FIELDS_COMPLETE | Almacén destino por línea, pendiente, suministro abierto y disponible proyectado |
| ROLES_COMPLETE | Ver: `compras:view`. Fijar el destino: `compras:create`; con solo `compras:view`, 403 |
| AUDIT_COMPLETE | `PURCHASE_ORDER_LINE_DESTINATION_SET`, con el destino anterior y el nuevo (id y código). Repetir el mismo destino no audita. Los cálculos no se auditan. Catálogo: 496 |
| SECURITY / ISOLATION_COMPLETE | La empresa sale del contexto. Las órdenes de otra empresa no suman, aunque apunten a un almacén propio (T8). Un almacén ajeno da 404 y una orden ajena, 404 |
| CONCURRENCY_COMPLETE | Lectura con una consulta agregada, sin bloqueos nuevos. El episodio ACTIVE único de la necesidad se mantiene. Fijar el destino bloquea la fila de la orden |
| INVENTORY_SEMANTICS | `OPEN_SUPPLY_CHANGES_STOCK=0`, `CREATES_INVENTORY_MOVEMENT=0`, `CREATES_RECEIPT=0`, `CHANGES_COST=0` (T5) |
| E2E_COMPLETE | `e2e/suministro-abierto.spec.ts`, 12 pasos sobre PostgreSQL efímero con ClamAV: necesidad → requisición → orden → destino → aprobación → resolución sin duplicado → recepción en otro almacén bloqueada → parcial (pendiente 7) → cierre (0) → necesidad nueva |
| RESPONSIVE_COMPLETE | 1280, 390 y 320, sin desplazamiento horizontal |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0, 2.1 y 2.2, niveles A y AA) en el detalle de la necesidad y en el panel de líneas, a las tres anchuras: `AXE_NEW_SERIOUS=0` |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec015_open_supply.py`, de T1 a T9 (parcial 100→60→30→0, estados, varios almacenes, planificación sin duplicado, sin efecto en inventario, recepción bloqueada, API y auditoría, aislamiento, detalle de la necesidad) | 9/9 en PostgreSQL |
| Mutaciones: contar órdenes en DRAFT o SUBMITTED; no filtrar por almacén destino; quitar el bloqueo de recepción | Las 3 mueren y los originales se restauraron byte a byte |
| Pruebas existentes afectadas (planificación, compras, arquitectura 019 y 021, `n10`, catálogo y cabezas) | 139 PASS; solo la línea base de `n10` |
| Vitest · typecheck · lint · build | 1972/1972 · limpio · limpio · correcto |
| E2E `suministro-abierto` + `reposicion` | 2/2 a 1280, 390 y 320 |
| Regresión E2E de compras e inventario (13 specs) | 51/51 a 1280 |
| ruff · mypy | limpio · 157, igual que HEAD (sin errores nuevos) |
| OpenAPI | +1 ruta. Fixtures regeneradas |
| Suite completa de backend en PostgreSQL (una vez, con ClamAV) | 5426 PASS, 18 SKIP, 5 FAIL, en 1 h 56 min. Los 5 fallos son la línea base exacta: `gobierno_integridad_runner`, `n10` (solo las 6 diferencias de `import_*.created_by`), `naive_datetime` y `spec019_receipt` ×2. `NEW_BACKEND_FAILURES=0` |
| GOV-TEST-UTC-DATE | La suite corrió de 11:45 a 13:41 (Caracas), fuera de la franja de 20:00 a 24:00 en la que fallaba. Gobierno: 0 fallos. No hay herramienta para mover el reloj (faketime, freezegun), así que la corrección de P1 **no se pudo medir dentro de la franja**: `GOV_TEST_UTC_DATE=NOT_REMEASURED_IN_WINDOW` |

## Deudas (no absorbidas)

- ~~**RECEIVED-UNCONFIRMED-PROJECTION.**~~ Pagada el 2026-11-13 en `../received-unconfirmed/` (`spec015-received-unconfirmed-projection-delta.md`).
- **QUOTE-REQUISITION-LINK.** No hacía falta, porque la dueña eligió el destino en la línea: `OPEN_SUPPLY_REQUIRES_QUOTE_REQUISITION_LINK=0`.
- **ORDENES-UI-ETIQUETAS.** La tabla de órdenes sigue mostrando el id del proveedor. Es previo a este ciclo y no se absorbe; el panel nuevo no muestra UUID.
