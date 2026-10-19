# Mutaciones (GOOD→PASS · MUTATED→FAIL · RESTORED→PASS; juego: catálogos + integridad + sucursales + estructura; SQLite **y** PostgreSQL)
| Id | Mutación | Resultado |
|---|---|---|
| M01 | alta de ubicación sin validación | KILLED (C02/03/04/25/28/29) |
| M02 | alta masiva sin validación | KILLED (C06/06b/28/29) |
| M03 | PATCH de ubicación sin validación | KILLED (C08/28) |
| M04 | alta de zona sin validación | KILLED (C10/11/12/28/29) |
| M05 | PATCH de zona sin validación | KILLED (C14/28) |
| M06 | solo comprueba existencia | KILLED |
| M07 | compara el tenant en vez de la empresa | KILLED |
| M08 | comparación invertida | KILLED |
| M09 | código distinto | KILLED |
| M10 | mensaje distinto | KILLED (C10) |
| M11 | ajeno distinguible de inexistente | KILLED |
| M12 | `null` rechazado | KILLED |
| M13 | PATCH de ubicación valida siempre | KILLED (C28/29) |
| M14 | PATCH de zona valida tras mutar | KILLED (C29) |
| M15 | alta masiva valida tras la vista previa | KILLED (C06b/29) |
| M16 | alta de ubicación valida antes de LOCATION_CODE_REQUIRED | KILLED (C22) |
| M17 | alta de zona valida antes de STRUCTURE_LEVEL_DISABLED | KILLED (C23/28/29) |
MEANINGFUL 17 · KILLED 17 · SURVIVED 0 · EQUIVALENT 0 · RESTORED 100 % (idéntico a GOOD; 92 passed / 1 skipped y 93 passed).
