# Pruebas dirigidas (después del cambio)
| Prueba | SQLite | PostgreSQL |
|---|---|---|
| módulo CSYNC en su orden | 13/13 (8,3 s; `setup` de módulo 3,0 s + ~0,4 s por prueba) | 13/13 |
| cada prueba **sola** (01…13) | **13/13** (antes 3/13) | — (cubierto por la regresión en PG) |
| módulo en **orden inverso** (regresión aisl_02, con orden verificado por `-vv`) | PASS (antes 11 failed) | PASS |
| csync_02 sola (regresión aisl_01) | PASS | PASS |
| contrato estático (aisl_03) | PASS | PASS |
| total módulo + regresión | 16/16 (26 s) | 16/16 (43 s) |
Diff del módulo frente a `HEAD`: solo añadidos (fixture partido en `_aplicaciones` de módulo y `_mundo` de prueba, tres
ayudantes, diez primeras sentencias de precondición); **ninguna línea original eliminada ni aserción debilitada**. ruff limpio.
