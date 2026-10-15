# Vida de la referencia de módulo
`VARIABLE` `SERVER_TIME` · `DEFINED_AT` `tests/test_licensing_central.py:106` · `IMPORT_TIME`: recolección de pytest (minutos u
horas antes de la prueba en una suite completa) · `USED_BY_TESTS`: respuesta y desafío de `_TransporteFalso` (todas las
pruebas que sincronizan) y la aserción del objetivo (1 prueba) · `AGE_WHEN_FULL_SUITE_FAILS`: > 5 min (firma: actual
15:45:41 = activación; esperado 15:38:04 = importación + 5 min → el módulo tenía ≈ 12,6 min al ejecutar la prueba) ·
`AGE_WHEN_ISOLATED_PASSES`: segundos · `MODULE_IMPORT_TIME_USED_AS_OPERATION_BOUNDARY` = **YES**.
Dirección del fallo: `last_reliable_date` (activación, posterior) > `SERVER_TIME` → el producto, correctamente monótono,
conserva la activación y la igualdad falla. `SQLITE_FAILURE_DELTA` ≈ +7,6 min; `POSTGRES_FAILURE_DELTA`: misma firma (la
suite PostgreSQL tarda más de 5 min hasta este módulo); `BOUNDARY_EXCEEDED_BY` = edad del módulo − 5 min.
