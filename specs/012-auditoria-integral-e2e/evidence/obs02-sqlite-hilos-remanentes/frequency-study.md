# Estudio de frecuencia (acotado) · `frequency-series-before.txt`

| Serie | Qué | Resultado | Lo que la serie **no** ve |
|---|---|---|---|
| A | UoM sola ×20, SQLite, sin sonda | **20/20 PASS** | en 4/20 (corridas 4, 12, 13, 14) pytest emite `PytestUnhandledThreadExceptionWarning`: un hilo murió con `InvalidRequestError: Could not refresh instance` y la prueba pasó igual (`len(abiertas) == 1` sigue siendo cierto porque **nadie** creó versión: la abierta es la original) |
| A' | UoM sola ×10 con sonda | 10/10 PASS; **1 conexión DBAPI en 10/10**; 1/10 con hilo muerto (corrida 8) | ídem |
| B | módulo `test_uom_conversion.py` ×10 | 10/10 PASS (16 pruebas) | — |
| C | UoM sola ×10 PostgreSQL | 10/10 PASS, sin avisos | — |
| Documents-security | — | no se corren series: `ENVIRONMENT_BLOCKED` (`documents-security-target.md`) | — |

Lectura: la prueba objetivo **no falla**, pero en ~17 % de las corridas (5/30) pasa con un hilo muerto y sin versión
creada: `REPRODUCED = YES` como **falso verde** (FR-O2-025: vector de resultados incompleto aceptado como PASS; FR-O2-024:
excepción de hilo invisible). `UNKNOWN_RESULT = 0`.
