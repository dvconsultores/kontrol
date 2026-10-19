# Certificación (2026-10-19)
| Suite | Resultado | Duración | Anomalía | Delta frente a la entrada |
|---|---|---|---|---|
| SQLite #1 | **1859 / 0 / 1046** | 676,8 s | NORMAL (1,06×) | +28 = C01…C29 |
| SQLite #2 | **1859 / 0 / 1046** | 654,3 s | NORMAL (1,02×) | +28 |
| PostgreSQL | **2879 / 0 / 26** | 1468,4 s | NORMAL (1,02×) | +28 |
| OpenAPI | **544 / 533 / 11** | — | — | sin cambio |
| OBS-01 revalidada | 15 KILLED + 1 EQUIVALENT (M11, ya justificada), restauración idéntica | — | — | sin cambio |
| E2E (una corrida, `r20261019t023304p631158n81064f`) | **273 / 7 / 0 + 4 sin ejecutar** | 6,5 min | — | limpieza LIMPIA |

## E2E: no verde; firma nueva no atribuible al cambio
- **Gate de entorno antes de la corrida:** apto. Había 5 308 MB disponibles y 3 829 MB de swap; Opera había bajado de
  13,9 GB a 3,5 GB. Se ejecutó UNA corrida, sin repetirla.
- **Durante la corrida:** a los 50-100 s el escritorio paginó, con la swap de 3,8 a 6,6 GB. La memoria disponible bajó
  hasta 1 011 MB. Hubo 9 clamscan, con una vida máxima de 17 s.
- **Fallos:** 7. Son `documents.spec.ts:164`, `returns.spec.ts:466`, `route-crawl.spec.ts:28`, `sales-orders.spec.ts:143`
  y `:167`, y `treasury.spec.ts:96` y `:118`. Todos son esperas vencidas (`waitForLoadState`, `locator.fill`,
  pantallas en «Cargando…») o un contexto de petición destruido.
- **Backend:** 4 `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached`, todos en el middleware de
  licencia (`_get_mode` → `current_mode` → `_instalacion_canonica`).
- **Atribución al cambio: 0.**
  - Ninguna traza pasa por `warehouse_api`.
  - Ninguna respuesta lleva `LOCATION_TYPE_NOT_FOUND` ni `ZONE_TYPE_NOT_FOUND`.
  - Los módulos que fallan no llaman a los cinco puntos cambiados.
  - Las 17 E2E de almacenes, ubicaciones, multiempresa y picking pasaron.
- **No se repitió el control sobre HEAD,** porque la firma no es atribuible al cambio.
- **Clasificación:** `EXTERNAL_ENVIRONMENT · HOST_PAGING_BURST`, con observación nueva no absorbida:
  `E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING`. El middleware de licencia abre una sesión por petición, y con el equipo lento el
  pool de 15 se agota. NOT_PROVEN como defecto de producto.

Residuos: bases de corrida 0 · `t_` 0 · efímeros 0 · puertos libres · clamscan 0 · sondas 0.

## Cierre E2E conjunto (2026-10-19 05:01)
| Campo | Valor |
|---|---|
| Precheck | MemAvailable 6 640 MB · swap 4 631 MB · carga 1,08 · clamscan previos 0 → apto |
| E2E (`r20261019t030105p679326nda98b2`) | **284 / 0 / 0** · 4,6 min · limpieza LIMPIA · salida 0 |
| Durante la corrida | MemAvailable mínima 886 MB · swap pico 6 827 MB · carga máxima 15,65 · clamscan simultáneos pico 5 · vida máxima 20 s |
| Backend | 0 `QueuePool` · 0 errores no controlados · 0 respuestas `*_TYPE_NOT_FOUND` / `BRANCH_NOT_FOUND` |
| Código | sin cambio desde `f93232b` (`CODE_UNCHANGED = 1`); certificación backend reutilizada |
