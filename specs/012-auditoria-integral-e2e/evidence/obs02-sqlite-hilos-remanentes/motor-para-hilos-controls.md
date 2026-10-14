# Control con `motor_para_hilos` (UoM)

| Prueba | `CONNECTION_A != CONNECTION_B` | `SAME_DATASTORE` | Resultado |
|---|---|---|---|
| POC (b): fichero temporal, pool por defecto | sí (2 ids DBAPI en `checkout`) | sí (mismo fichero; el perdedor ve la versión del ganador) | 35/35 sin excepción; I1 5/5 `[200, 409]` |
| O2-02 (`tests/test_uom_concurrencia_hilos.py`, fixture `motor_para_hilos("uom-concurrencia")`) | sí (`len(conexiones) == 2` medido en el gancho durante la carrera) | sí | `[200, 409]`, `PRESENTATION_VERSION_OVERLAP`, una abierta / dos en total, 0 excepciones; en PostgreSQL igual (serie en `directed-series-after.txt`) |
| Prueba objetivo con el fixture sobre `motor_para_hilos("uom-conversion")` | sí | sí | véase `directed-series-after.txt` |

Efecto colateral medido al cambiar el módulo entero de motor: `test_el_historico_no_cambia_al_cambiar_el_factor` pasó a
fallar con `database is locked` (F6) porque mantenía una sesión con escrituras sin confirmar mientras llamaba a la API.
Es un defecto de ciclo de vida de esa prueba (dependía de la conexión compartida), corregido en una línea: la empresa se
resuelve por la API antes de abrir la sesión de escritura; el barrido del módulo no encontró otro caso igual
(`implementation-decision.md`).
