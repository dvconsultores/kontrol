# E2E global ×1 tras la corrección

`resources/backend/.venv/bin/python qa/e2e-run.py` (base PostgreSQL efímera nueva, migrada, sembrada, backend + Vite,
Playwright, limpieza): corrida `r20261013t203941…`, **280 passed · 4 skipped** (los 4 de `ENTORNO-SIN-CLAMSCAN`), 4,0 min,
limpieza LIMPIA, salida 0; huella de red igual al inicio y al final, sin desvío de reloj, túnel VPN presente (como en las
globales anteriores). Bases de corrida después: 0. Puertos 8000/8010/5173 libres. Igual a la línea base 280/0/4.
Este ciclo no toca frontend ni E2E; la global se corre porque el encargo la exige como gate de cierre.
