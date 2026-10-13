# Certificación paralela (W26) · los mismos dos procesos de la medición 03a, con el arnés aislado

Sin `xdist`. Dos `pytest` independientes lanzados a la vez, subconjuntos disjuntos, SQLite:

- A: `pytest tests/test_license_sync_client.py` (firma el sobre del desafío con la clave de su volumen)
- B: `pytest tests/test_license_trust_anchor.py tests/test_license_period_rollback.py` (dos mundos que inicializan instalación)

```
--- A ---
.............                                                            [100%]
A rc=0
--- B ---
..................................                                       [100%]
B rc=0
raíces residuales: 0
```

Antes (medición 03a, misma pareja): A fallaba 10/13 con `SYNC_AUTH_INVALID`. Ahora: A 13/13 y B 34/34, volúmenes
distintos (TV-04 lo comprueba por sondas con huellas), ninguna clave pisada, y las dos raíces eliminadas al terminar.
