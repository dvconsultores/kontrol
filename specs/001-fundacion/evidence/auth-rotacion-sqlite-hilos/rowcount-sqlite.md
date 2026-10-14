# rowcount en SQLite (`cas-poc.py`, `cas-poc-output.txt`)

Misma fila sintética; el UPDATE condicional exacto dos veces, en transacciones distintas:

| | rowcount | `revoked_at` después |
|---|---|---|
| primera ejecución (fichero temporal, pool por defecto) | **1** | puesto |
| segunda ejecución | **0** | sin cambio |
| primera / segunda sobre `:memory:` + `StaticPool` | **1 / 0** | — |

`SQLITE_ROWCOUNT_1 = 1` · `SQLITE_ROWCOUNT_2 = 0` · fiable (`sqlite3_changes` por sentencia).
