# SPEC 031 · CONVERGENCIA

`SPEC 031 — COMPLETE / CONVERGED`

> 2026-09-05, sobre `5bb2f8f`. Ciclo de implementación completo tras `D0-15`.

## Puerta

| Criterio | Resultado |
|---|---|
| Cola con orden autoritativo | `released_at ASC, id ASC`, calculado en backend |
| Prioridades `FUTURE` activadas | **0** |
| División entre ubicaciones | soportada |
| Planificación parcial | solo en `DRAFT`, con remanente publicado |
| Confirmación con remanente | **imposible** (`PICKING_PLAN_INCOMPLETE`) |
| Plan incompleto consumible por la 032 | **no** |
| Ciclo de vida | cinco estados con `CHECK` en la base |
| Reserva comercial liberada por la 031 | **no** |
| `qty_on_hand` / `qty_reserved` alterados al planificar | **0 / 0** |
| `InventoryMovement` creados al planificar | **0** |
| Algoritmo de ruta nuevo | **0** — se consume `physical_order_query` |
| FIFO / FEFO / prioridad de lote inventados | **0** |
| Permisos nuevos inventados | **0** — `ventas:view` y `ventas:create` |
| Especificaciones paralelas creadas | **0** |
| Backend | 1071 pruebas · **1063 pasan · 8 saltos · 0 fallos** |
| Saltos esperados / reales | **8 / 8** |
| Frontend | **291 / 291** · `tsc` limpio · `eslint` limpio · `ruff` limpio |
| E2E de la Spec 031 | **24 / 24** (8 casos × Chromium, Firefox, WebKit) |
| E2E de la cadena operativa | **84 / 84** (019, 020, 021, 022, 030, 031 × 3 navegadores) |
| Migración | `0049` ida y vuelta sobre base limpia |
| ORM ↔ base | sin deriva (`test_el_orm_y_la_base_no_difieren_en_nada`) |
| Trazabilidad | **100 %**, 48 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## Deltas dirigidos sobre Ventas / Spec 030

Los dos que `D0-15` había declarado. **No** se reabre la Spec 030 ni se declara
reconvergencia global: son dos aristas con su guardia actualizada y su razón
escrita.

| Delta | Cambio | Guardia |
|---|---|---|
| A | `create_picklist` deja de mover el pedido a `PREPARING` al crear el borrador | `test_crear_un_plan_no_mueve_el_pedido` |
| B | `ORDER_TRANSITIONS` gana `PREPARING → RELEASED` | `test_la_maquina_de_estados_es_la_de_d0_03`, actualizada con el motivo |

## Lo que se midió y no se supuso

Las dos afirmaciones centrales se comprobaron **mutando el código**: al ordenar
la cola por `submitted_at` y al devolver `create_picklist` a su comportamiento
anterior, las pruebas correspondientes fallan. Una prueba que no falla cuando el
defecto vuelve no prueba nada.

La concurrencia se ejerce sobre PostgreSQL real con dos transacciones en hilos
distintos peleando por la misma ubicación: de dos peticiones de 70 sobre una
existencia de 100, entra exactamente una.

## Lo que este ciclo encontró y no era suyo

| Hallazgo | Dueño | Acción |
|---|---|---|
| `pgserver` no trae `btree_gist` y sin él **toda** la suite falla en el fixture | QA | automatizado en `qa/pg-provision.sh` |
| La e2e de la Spec 019 leía `/inventory/balances` sin filtro y el listado pagina | 019 | acotada al producto |
| La e2e de la Spec 020 comparaba la primera página entera de saldos | 020 | ídem |
| `uom.py` declara para `sales_orders` cuatro estados de los que solo existe `CLOSED` | 011 | anotado, no corregido |
| `uom-a11y`, `documents`, `warehouse-a11y` y `approvals` fallan por datos que esta siembra no crea | QA | **verificado con los cambios apartados: fallan igual sin ellos** |

## Delta dirigido recibido — 2026-09-07 (desde el ciclo de la Spec 035)

El selector de almacén de `PreparacionPage` pedía
`/organization/warehouses?limit=500`. Cuando la base de e2e llegó a **564**
almacenes, la respuesta se cortó y los 64 últimos —incluido el que cada prueba
acababa de crear— dejaron de existir para el desplegable. Seis pruebas e2e de
esta Spec se pusieron en rojo, y no por lo que probaban.

El tope se sustituyó por tandas hasta agotar `total`. Subirlo a 2000 habría
movido el acantilado escribiendo un número que ya se sabe equivocado. Las seis
vuelven a pasar: 24/24 en los tres navegadores.

El patrón sigue abierto en otras ocho pantallas —siete se quedan en el límite
por defecto de 50— y eso es del módulo de organización, no de esta Spec.

## Estado resultante

| | |
|---|---|
| Spec 031 | **COMPLETE / CONVERGED** · con un delta dirigido recibido de la 035 (2026-09-07) |
| Spec 030 | `COMPLETE / CONVERGED` con dos deltas dirigidos convergidos |
| Spec 032 | **BLOCKED UNTIL SPEC031 CONVERGES** → desbloqueada por dependencia; su contrato de entrada está en `spec032-handoff-after-spec031.md`. **No implementada.** |
