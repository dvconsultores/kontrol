# Carrera controlada en PostgreSQL tras la corrección (SA-02) · `directed-series-after.txt`

Barrera antes del `SELECT … FOR UPDATE` en las dos peticiones (no se fuerza una escritura simultánea: el bloqueo de fila
la hace imposible). Resultado **5/5**: `[200, 401]`, perdedor `SESSION_REVOKED`, un solo reemplazo, original revocada,
0 excepciones. Natural ×20 **20/20**. `with_for_update()` conservado (SA-16); la escritura condicional queda como segunda
guarda: el segundo `SELECT FOR UPDATE` relee la fila ya revocada y ni siquiera llega al UPDATE (POC `cas-poc-output.txt`).
Módulo auth + SA + ACS + almacenes + OpenAPI en PostgreSQL: 99 passed.
