# Sondas del ciclo de vida en PostgreSQL

Módulos de prueba deliberadamente pequeños —y alguno deliberadamente roto— que
`tests/test_pg_harness_lifecycle.py` ejecuta en un proceso aparte para comprobar qué deja
el arnés en la base cuando una prueba pasa, falla, deja una conexión abierta o crea
recursos fuera de toda fixture.

No se llaman `test_*.py` a propósito: `pytest tests` no los recoge. Solo corren cuando se
les nombra por su ruta.

Las sondas `sonda_sesion_*.py` (TEST-PG-UN-SCHEMA-POR-PRUEBA) ejercitan `sesion_de_prueba`: la
sesión con la base limpia por prueba que, en PostgreSQL, trabaja sobre un único schema por
módulo. `tests/test_pg_sesion_aislada.py` las lanza en procesos aparte y lee lo que cuentan
por JSON (`KONTROL_SONDA_INFORME`).
