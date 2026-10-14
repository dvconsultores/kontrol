# I1 controlada en SQLite tras la corrección (SA-01) · `directed-series-after.txt`

`motor_para_hilos` (una conexión por hilo, mismo fichero), barreras antes del `SELECT sessions` y antes del primer
`UPDATE sessions` en cada petición: las dos leen la sesión sin revocar y las dos llegan a la escritura condicional.
Resultado **10/10**: estados `[200, 401]`, perdedor `SESSION_REVOKED`, ganador con access token y cookie nueva distinta,
las dos leyeron y las dos escribieron (`len(leyeron) == 2 == len(escribieron)`), sesión original revocada, vivas
= antes + 1 (exactamente un reemplazo), 0 excepciones de hilo, sin `database is locked`. Natural (prueba objetivo sola)
**20/20**; módulo ×10 **10/10** (8 pruebas cada uno). Antes de la corrección: 15/20 fallos sola y 5/5 `[200, 200]` con I1.
