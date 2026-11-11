# IMP-05 · adjudicación de cotizaciones: registro de intentos

Todo con `deepseek-v4-pro` y `stream=true`. **Presupuesto:** objetivo 2 llamadas, máximo 4, y 2 reintentos por subproblema. **Usados:** 3 llamadas (backend, frontend y la corrección de una causa nueva) y 3 reintentos (2 del backend y 1 del frontend), en 6 envíos.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | Backend: modelo, migración 0099, servicio, API, catálogo, guardias y pruebas | 9145/9092 | $0,011888 | Parcial. Pasaron la auditoría y se aplicaron el modelo, el import de Party, `order_dict`/`quote_dict`, la API, el catálogo, la cuenta 464, las guardias y la migración. Se rechazaron: `db.refresh(populate_existing=)` (no es válido), código muerto, un bloque que no cambiaba nada, un `_es_violacion_unica` propio sin manejar la carrera, y las pruebas |
| 1·R1 | Correcciones X1 a X5 | 11090/5538 | $0,009642 | Pasaron y se aplicaron los imports, `compare_quotes`, `award_quote` y `order_from_quote` (con `begin_nested` + `es_violacion_unica`). Se rechazaron: los helpers con dos funciones muertas, `date` sin importar, y pruebas que comparaban `float` con `__import__` |
| 1·R2 | Y1 a Y3 | 4276/3698 | $0,005077 | AUDIT_PASS. Pruebas: 36 PASS en SQLite y 73 PASS en PostgreSQL. Queda un orden de imports que corrigió `ruff --fix` (mecánico) |
| 2 | Pantalla de Cotizaciones y E2E | 6948/5859 | $0,008120 | Aplicado y medido. Fallaba typecheck (dos `onClick` que no devolvían una promesa y un `Page` sin uso) y la E2E se apartaba de la convención (imports, y un `?q=` que la API no tiene) |
| 2·R1 | Z1 a Z4 | 1582/563 | $0,001178 | AUDIT_PASS. typecheck y lint limpios. E2E PASS a 1280, 390 y 320 |
| 3 | NEW_ROOT_CAUSE medida en Vitest: el selector genérico `/^Producto/` de `catalogoSelectores.test.tsx` encontraba dos comboboxes en Cotizaciones (3 fallos). Se renombra la etiqueta a «Artículo a comparar» y se cierran los 3 errores de tipo de mypy del delta | 792/559 | $0,000831 | AUDIT_PASS. Vitest 1911/1911; E2E PASS a 1280, 390 y 320; mypy sin errores nuevos en el delta |

**Total:** 6 envíos, $0,046736.

**Implementado por Claude:** ninguna línea de producto, de prueba ni de migración. Hizo dos correcciones mecánicas: el orden de imports con `ruff --fix` y las fixtures de rutas regeneradas con `qa/fixtures_de_frontend.py`.

**Incidencia de proceso:** en la reanudación, el aplicador de parches del scratchpad (`/tmp`) se había perdido. Se recreó en `~/.local/share/kontrol-p2-herramientas/sondas/`, igual que antes.

**Otra incidencia de proceso:** en los envíos 1·R1, 1·R2, 2 y 2·R1, el puente avisó de que copió el brief a mano y no pudo garantizar que fuera byte a byte.
