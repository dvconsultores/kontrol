# Convención del tope de `limit` · aplicación a `GET /organization/warehouses`

El listado de almacenes no usa el estilo canónico `page/page_size`: responde `{total, limit, offset, items}` con `limit`
por defecto 50 y `offset` 0, contrato ratificado por la delta WHL (`tests/test_warehouse_list_cost.py`,
FR-054-E2EFLK-002..005: «el listado dice lo mismo que el detalle y no cuesta más por fila») y consumido por 12 pantallas,
10 suites E2E y 3 guiones de QA. Cambiar los nombres de los parámetros o el sobre sería un cambio de contrato con
consumidores incompatibles y reabriría una delta cerrada: **fuera de este ciclo** (observación `ALMACENES-PAGINACION-
LIMIT-OFFSET`, para la dueña 008).

Lo que sí está ratificado a nivel de plataforma y se aplica tal cual al tamaño de página del listado, se llame `limit` o
`page_size`:

| Registro | Valor | Fuente |
|---|---|---|
| Máximo de filas por respuesta | **100** | `MAX_PAGE_SIZE = 100` (Spec 001, canon transcrito) |
| Mínimo | **1** (`ge=1`) | canon (`page_size` 1..100) |
| Por encima del máximo / por debajo del mínimo / no numérico | **422** `VALIDATION_ERROR` | canon (AC-047) |
| `offset` | **≥ 0** (`ge=0`); negativo → 422 | misma validación; hoy un `offset` negativo es un **500** en PostgreSQL |
| Valor por defecto de `limit` | **50**, sin cambio | contrato WHL vigente (`test_whl_07`: «por defecto 50»); cambiarlo sería un cambio silencioso para 12 pantallas (FR-LT-014) |
| Sobre | `{total, limit, offset, items}`, sin cambio | contrato WHL vigente |

Decisión material pendiente: **ninguna** — el tope (100) y el comportamiento por encima (422) tienen fuente ratificada;
el estilo de nombres queda anotado, no decidido aquí.
