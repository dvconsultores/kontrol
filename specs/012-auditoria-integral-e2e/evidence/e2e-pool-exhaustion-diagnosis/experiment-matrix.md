# Matriz de experimentos (sonda desechable; uvicorn real en un puerto libre; app real `create_app()`; PostgreSQL de QA con schema efímero; motor con los parámetros de producción; 2026-10-19 05:2x, equipo en calma: MemAvailable ≈ 6,7 GB)
| Id | Condición | Resultado medido | Lectura |
|---|---|---|---|
| X1 | 10 lecturas + 10 escrituras secuenciales | checkout 20 = checkin 20 · máximo prestado 1 · final 0 | sin fuga; 1 conexión por petición |
| X1b | petición autenticada que dura 1 s | prestadas durante el endpoint 1, al final del endpoint 1, tras la respuesta 0 | la conexión se retiene toda la petición |
| X2 | k = 1, 2, 5, 10, 15, 20 lecturas concurrentes que retienen 2 s | todas 200; máximo prestado = min(k, 15); k = 20: p50 2,06 s, máximo 4,02 s; balance exacto | el pool encola sin error con el bucle libre |
| **X3** | 15 retenedoras de 3 s + **1 escritura** | retenedoras: **30,28 s**; escritura: **500 en 30,05 s** (`QueuePool limit of size 5 overflow 10 reached … timeout 30.00`) | **reproduce la firma de la E2E** |
| C1 | 15 retenedoras + 1 lectura | retenedoras 3,05 s · lectura 200 en 2,99 s | la lectura no pasa por la consulta del middleware: sin bloqueo |
| C2 | 14 retenedoras + 1 escritura | retenedoras 3,05 s · escritura 404 en 0,01 s | con una conexión libre no hay bloqueo |
| **X4** | X3 con la llamada del middleware descargada al threadpool (`await run_in_threadpool(self._get_mode)`; solo en la sonda) | retenedoras **3,04 s** · escritura **404 en 2,99 s** | retirar la espera síncrona del bucle **elimina** el fallo |
Totales: 144 checkouts = 144 checkins; 0 conexiones prestadas al final; resultados crudos en `experiment-results.json`.
La sonda se eliminó del árbol tras ejecutarse (`TEMP_PROBES = 0`, `POOL_TELEMETRY_HOOKS = 0`).
