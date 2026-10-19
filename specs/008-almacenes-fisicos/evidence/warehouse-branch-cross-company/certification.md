# Certificación (2026-10-18/19; `qa/suite_tiempos.py --con-analizador`, `qa/e2e-run.py --con-analizador`)
| Suite | Resultado | Duración | Anomalía | Delta frente a la entrada |
|---|---|---|---|---|
| SQLite #1 | **1831 / 0 / 1046** | 708,7 s | NORMAL (1,11×) | +17 = B-01…17 (O01-06 adaptada, sin cambio de recuento) |
| SQLite #2 | **1831 / 0 / 1046** | 720,4 s | NORMAL (1,13×) | +17 |
| PostgreSQL | **2851 / 0 / 26** | 2043,4 s | NORMAL (1,43×; el equipo paginó: swap 10,5→14,2 GB) | +17 |
| E2E #1 | **275 / 5 / 0 + 4 sin ejecutar** | 4,5 min | — | −9 frente a 284; limpieza LIMPIA |
| E2E #2 | **275 / 5 / 0 + 4 sin ejecutar** | 4,5 min | — | mismas 5 |
| OpenAPI | **544 / 533 / 11** | — | — | sin cambio |

## E2E: fallo atribuido al entorno (medido)
- Las 5 que fallan son de carga documental con el analizador real: `documents.spec.ts` 118/203/246/286 y
  `documents-a11y.spec.ts` 98. Las 4 sin ejecutar son las que dependen de ellas en serie.
- En todas, la pantalla se queda en «Verificando el archivo…» hasta que vence la espera de 30 o 60 s.
- **Control con el producto de `HEAD`.** Se retiró solo `warehouse_api.py` con `git stash`, se ejecutó el subconjunto de
  documentos y se restauró, comprobado con `cmp`. El resultado fue 3 fallidas de 12, frente a 2 de 12 con el cambio. Es el
  mismo producto que dio 284/0/0 a las 18:12, así que este ciclo no causa la falla.
- **Medición.** Se muestreó cada segundo durante el subconjunto. Hubo 8 clamscan, que vivieron 5, 6, 7, 22, 27, 28, 29 y
  33 s, frente a 6,4 s en reposo medidos justo antes. El RSS máximo fue de 966 MB y la memoria disponible mínima de 311 MB.
- **Equipo.** Por la tarde la swap estaba entre 4,1 y 4,3 GB, y la memoria disponible entre 2,4 y 5,3 GB. Esta noche la swap
  subió hasta 14,2 GB y la memoria disponible bajó hasta 0,5 GB. Lo ocupan las aplicaciones del escritorio (navegador
  ~2 GB, editor). No quedaba ningún proceso de los ciclos (ni clamd ni uvicorn ni vite).
- **Clasificación:** `EXTERNAL_ENVIRONMENT · HOST_MEMORY_PRESSURE`. No se tocó ninguna espera, timeout ni prueba. La
  corrida no se repitió para que «pasara»: la segunda corrida y el control son evidencia.
Residuos: bases de corrida 0 · esquemas `t_` 0 · raíces efímeras 0 · puertos 8000/8010/5173 libres.

## Cierre E2E conjunto (2026-10-19 05:01)
| Campo | Valor |
|---|---|
| Precheck | MemAvailable 6 640 MB · swap 4 631 MB · carga 1,08 · clamscan previos 0 → apto |
| E2E (`r20261019t030105p679326nda98b2`) | **284 / 0 / 0** · 4,6 min · limpieza LIMPIA · salida 0 |
| Durante la corrida | MemAvailable mínima 886 MB · swap pico 6 827 MB · carga máxima 15,65 · clamscan simultáneos pico 5 · vida máxima 20 s |
| Backend | 0 `QueuePool` · 0 errores no controlados · 0 respuestas `*_TYPE_NOT_FOUND` / `BRANCH_NOT_FOUND` |
| Código | sin cambio desde `f93232b` (`CODE_UNCHANGED = 1`); certificación backend reutilizada |
