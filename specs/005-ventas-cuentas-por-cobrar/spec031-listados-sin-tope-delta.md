# SPEC 031 · Delta dirigida — LISTADOS-SIN-TOPE (enlace cruzado)

La deuda `LISTADOS-SIN-TOPE` tiene dos dueñas: SPEC008 (`GET /organization/warehouses`) y SPEC031 (`GET /sales/pick-lists`).
La delta completa, con discovery, convención, reproducción, decisión de contrato, implementación, mutaciones, suites y
convergencia, vive en **`specs/008-almacenes-fisicos/spec008-listados-sin-tope-delta.md`** y su evidencia en
`specs/008-almacenes-fisicos/evidence/listados-sin-tope/`. Aquí solo se deja constancia de lo que cambia en el dominio de picking:

| | |
|---|---|
| Contrato nuevo de `GET /sales/pick-lists` | `order_id?`, `page` ≥ 1 (1), `page_size` 1..100 (20); sobre `{items, total, page, page_size}`; `total` dentro de la empresa y del filtro, antes de cortar; orden `created_at desc, id`; 422 fuera de rango; página vacía más allá del final |
| Lo que no cambia | `POST /sales/pick-lists` y el 409 `PICKLIST_DUPLICATE` (`spec031-picklist-duplicada-delta.md`), el alcance de empresa, los permisos, el resto de rutas de picking |
| Consumidores adaptados | `putaway.spec.ts` recorre páginas (`todasLasListasDePreparacion`); `PreparacionPage` y las demás suites filtran por `order_id` y no cambian |
| Pruebas | `tests/test_listados_sin_tope.py` (LT-04…16, 23, 24, SQL) |
