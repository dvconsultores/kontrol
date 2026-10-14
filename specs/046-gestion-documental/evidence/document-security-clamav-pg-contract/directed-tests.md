# Pruebas dirigidas · DOCENV-01…20 (`directed-series-after.txt`)

| Id | Qué | Resultado |
|---|---|---|
| DOCENV-01 | analizador ausente falla cerrado (422 `SCAN_FAILED`) | observado en 35 pruebas (inventario); contrato intacto |
| DOCENV-02/03/04 | PDF limpio `CLEAN`, EICAR `INFECTED`, error del proceso `SCAN_FAILED` con analizador real | **N/A: bloqueado** (sin analizador; decisión de la dueña) |
| DOCENV-05 | las carreras corren solo en el motor autorizado | SQLite: 9 nodos omitidos con razón; PostgreSQL: se ejecutan (y fallan por el analizador, no por la carrera) |
| DOCENV-06…11 | 409 del perdedor, misma clave, tenant, una V2, tres a la vez, séptima | **N/A: bloqueado** en esta máquina (422 antes de la carrera); su contrato queda declarado PostgreSQL-only |
| DOCENV-12 | SQLite no ejecuta SQL de PostgreSQL | contrato estático + omisión verificada |
| DOCENV-13 | cobertura no concurrente en SQLite | ≥ 25 pruebas sin marcador; ninguna se pierde |
| DOCENV-14 | sin bypass del analizador | contrato estático |
| DOCENV-15 | ningún `SCAN_FAILED` aceptado como éxito | contrato estático |
| DOCENV-16 | OpenAPI 544/533/11 | sin cambio (producto 0) |
| DOCENV-17 | UoM/almacenes/auth/ACS | PASS en los dos motores |
| DOCENV-18 | omisiones E2E solo según disponibilidad real del analizador | sin cambio: 4 (runner) |
| DOCENV-19 · DOCENV-20 | producción intacta · migración/esquema 0 | sí · sí |
