# GOV-CTL-10 · RED medido antes del producto

Medido con las suites `test_gov_ctl10_*` escritas y sin servicio, API ni guarda de CTL-10.

| Medida | Resultado |
|---|---|
| Fallidas | 74 |
| Error de recolección | 1 (`test_gov_ctl10_modelo.py`: el modelo aún no existía) |
| Pasadas sin producto | 2 |

Las dos que pasaron sin producto:

- `test_cc02_dos_cierres_mismo_programa_sin_pendientes`: cierra dos veces un programa sin política; describe el comportamiento previo de TRE-02, que CTL-10 debe conservar. Es una prueba de no regresión, no un RED.
- `test_sg04_uuid_inexistente`: esperaba 404 y lo obtuvo porque la ruta no existía. En RED no probaba nada; cobró sentido al existir la ruta, y lo sostiene el mutante S01.

`test_bl07` se añadió después, junto con el defecto que cubre (usuario como UUID y falta de `politica_id` en la lista de bloqueos). Falló por esos campos antes de aplicar M1.

El log completo queda fuera de Git, en la caché de QA del ciclo.
