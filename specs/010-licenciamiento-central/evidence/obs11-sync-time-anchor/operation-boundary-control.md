# Control de frontera de operación
Mismo guion: antes de invocar la prueba objetivo, la referencia se vuelve a capturar **en la operación**
(`SERVER_TIME = ahora + 5 min` justo antes de la llamada) para cada una de las ocho edades. Resultado: **8/8 PASS en
SQLite y 8/8 PASS en PostgreSQL**, incluidas las edades que fallan con la referencia de importación.
`OPERATION_BOUNDARY_CONTROL = PASS`: la edad del módulo deja de importar cuando la referencia nace en la operación.
