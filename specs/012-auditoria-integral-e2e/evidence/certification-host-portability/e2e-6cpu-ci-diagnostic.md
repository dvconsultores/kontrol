# E2E de diagnóstico: `CI=true` y 6 CPU lógicas (2026-10-25, MEASURED; no certifica)

Orden: `CI=true taskset -c 0-5 <venv del arnés>/bin/python qa/e2e-run.py --con-analizador -- --workers=6 --retries=0`
(los mismos argumentos que añade ahora `orden_de_e2e`). Corrida `r20261025t033310p762449n8b1989`. PostgreSQL de QA sobre
los binarios fijados.

| Medida | Valor |
|---|---|
| Workers informados | «Running 284 tests using 6 workers» (sin el perfil fijo, con 6 CPU, Playwright habría usado 3) |
| Reintentos con `CI=true` | 0: ninguna línea «retry» y ningún fallo repetido (sin el `--retries=0`, la configuración habría dado 2) |
| Resultado | 277 passed · 3 failed · 4 did not run · limpieza LIMPIA |
| Fallos | `documents-a11y.spec.ts:98` (31,8 s), `documents.spec.ts:118` (36,8 s), `documents.spec.ts:286` (39,1 s): cargas que esperan el análisis ClamAV; los 4 sin ejecutar son la cadena de licencias, que depende de ellos |
| Huella de KONTROL | pico 8020 MB Pss+SwapPss (47 procesos); MemAvailable mínimo del anfitrión 1189 MB |
| Duración | 316 s |

Conclusión:
- G1 y G2 quedan probados en la práctica: el perfil no depende de las CPU ni de `CI`.
- Con 6 CPU, la concurrencia de 6 workers y los análisis simultáneos vencen las esperas del analizador; con 12 CPU, la misma carga dio 284 passed (diagnóstico `r20261024t185614p424055n541fd2`). Por eso, `CERTIFICATION_HOST_CPU_MIN = 12` lógicas (medido, ya no «exactas»).
- La presión de memoria de la estación multiproyecto también contribuye. La diferencia entre las dos corridas es solo el número de CPU, pero no se aísla del todo.
