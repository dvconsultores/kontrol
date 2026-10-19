# Pruebas dirigidas — `tests/test_license_middleware_event_loop.py` (17; SQLite y PostgreSQL; sin skip)
| Id | Qué prueba | Resultado |
|---|---|---|
| L01–L03 | FULL_ACCESS/READ_ONLY + lectura → 200 sin consultar el modo; FULL_ACCESS + escritura → 200 con exactamente 1 consulta | PASS ×2 |
| L04 (×4) | READ_ONLY + POST/PUT/PATCH/DELETE → 423 con el cuerpo exacto del contrato, y el endpoint no se ejecuta | PASS ×2 |
| L05 | SECURITY_SUSPENSION: lectura 200; escritura 423 con el cuerpo exacto, y el endpoint no se ejecuta | PASS ×2 |
| L06 | `LICENSE_EXEMPT_PREFIXES` y `WRITE_METHODS` literales; las exentas pasan sin consultar el modo; `/api/v1/zona/recurso` y `/api/v1/` → 423 | PASS ×2 |
| L07 | `_get_mode` corre en un hilo distinto del bucle | PASS ×2 |
| L08 | un `ContextVar` llega al hilo trabajador | PASS ×2 |
| L09 | el bucle sigue vivo mientras `_get_mode` espera (`Event` determinista) | PASS ×2 |
| L10 | AST: una única `await run_in_threadpool(self._get_mode)` dentro del `if` de escritura; ninguna llamada directa; termina en `return await call_next(request)` | PASS ×2 |
| U01 (X3) | uvicorn real + app real + pool 5 + 10: 15 retenedoras + escritura → 404, no 500; cada duración < `pool_timeout`; balance exacto | PASS ×2 |
| U02 (C1) | pool lleno + lectura → 200; balance | PASS ×2 |
| U03 (C2) | 14 retenedoras + escritura → 404 antes de soltar; balance | PASS ×2 |
| U04 (X2) | 20 retenedoras (15 con conexión) → 20 × 200; balance | PASS ×2 |

- **Totales.** DIRECTED_TOTAL 17 · PASS 17 · FAIL 0 · SKIP 0 en cada motor. Cada prueba pasa sola (17/17 ×2) y el módulo
  pasa en orden inverso (17/17 ×2). Sin `sleep`: la sincronización usa `Event` y `Semaphore` con esperas de seguridad, y
  uvicorn avisa de su arranque con `startup`.
- **Rojo contra el producto de `HEAD`.** Se restauró por copia y `cmp`. Fallan L07, L09, L10 y U01 en los dos motores (4/17),
  justo las del mecanismo; las de contrato pasan igual, porque la semántica no cambia.
- **Licencia existentes.** `test_license`, `test_process_flows`, `test_license_import_access` y
  `test_license_state_reverification` dan 55/55 en SQLite y en PostgreSQL. ruff y mypy están limpios.
