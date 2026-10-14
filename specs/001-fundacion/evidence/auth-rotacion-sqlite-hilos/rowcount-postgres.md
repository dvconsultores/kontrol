# rowcount en PostgreSQL (`cas-poc.py`, `cas-poc-output.txt`; schema temporal propio, liberado al terminar)

| | rowcount | `revoked_at` después |
|---|---|---|
| primera ejecución | **1** | puesto |
| segunda ejecución | **0** | sin cambio |

`POSTGRES_ROWCOUNT_1 = 1` · `POSTGRES_ROWCOUNT_2 = 0` · fiable (psycopg2 informa filas afectadas). 0 schemas residuales
tras la POC (una corrida previa abortada por un error del guion dejó 1, purgado con `qa/pg-test-residuos.py --purgar`).
