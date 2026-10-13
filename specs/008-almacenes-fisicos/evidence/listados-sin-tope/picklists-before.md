# `GET /sales/pick-lists` ANTES (Discovery 04)

Véase `warehouses-before.md` (reproducción conjunta, mismo guion). Resumen: la ruta devolvía la colección entera de la
empresa (1 100 filas, 203 550 bytes, ≈ 25 ms en proceso) con un sobre `{items, total: len(items), page: 1, page_size:
len(items) or 1}` que solo parecía paginado; `page` y `page_size` se ignoraban (`page=0`, `page=abc` → 200 con todo); el
alcance de empresa era correcto (las 50 de C2 no aparecían); orden `created_at desc` sin desempate; consumidores:
`PreparacionPage` (`?order_id=`), 3 suites E2E (una necesita todas las de la empresa), 0 QA, 0 pruebas backend con GET.
`PICKLIST_UNPAGINATED = PROVEN`.
