# Estudio de frecuencia (acotado) · series crudas en `frequency-series.txt`

| Serie | Qué | Resultado | Firmas |
|---|---|---|---|
| A | prueba sola ×20, SQLite, sin sonda | **15/20 FAIL** (PASS: 2, 11, 13, 17, 20) | `[200, 200]` ×8 · `[200]` + `OperationalError: cannot commit transaction - SQL statements in progress` ×5 · `[401]` + `StaleDataError` ×1 · `[]` + `StaleDataError` ×1 |
| A' | prueba sola ×10, SQLite, con sonda de motor | **9/10 FAIL**; **1 conexión DBAPI** en 10/10 | `[200, 200]` ×5 · `OperationalError` ×3 · `StaleDataError` ×1 |
| B | módulo `test_auth_session_rotation.py` ×10, SQLite | **3/10 FAIL** (corridas 1, 3, 10), siempre la prueba objetivo; las otras 7 pruebas 70/70 | `[200, 200]` |
| C | prueba sola ×20, PostgreSQL | **20/20 PASS** | — |
| Exp. B | la prueba real con el fixture sobre `motor_para_hilos` (copia temporal, eliminada) ×20, SQLite | **20/20 PASS**; 2 conexiones DBAPI (sonda) | — (véase `controlled-interleaving.md`: pasa por sincronización, no por garantía) |

Lectura: en el árbol actual la prueba falla más veces de las que pasa en solitario (la fila del roadmap registraba «un hilo
sin respuesta» en 2026-09-30; hoy la firma dominante es que **ganan las dos**); PostgreSQL es estable. La frecuencia en
módulo es menor (3/10) porque las pruebas anteriores dejan el `TestClient` y el pool en otro estado de tiempos, no por
dependencia de orden (la prueba falla sola). `UNKNOWN_RESULT = 0`.
