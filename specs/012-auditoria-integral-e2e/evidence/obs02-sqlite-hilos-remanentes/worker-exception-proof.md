# Excepciones de hilo visibles · vector de resultados completo

| | Antes | Después |
|---|---|---|
| Hilo muerto en la prueba objetivo | invisible: `TestClient` relanza el 500 en el hilo, pytest solo emite `PytestUnhandledThreadExceptionWarning` y la prueba pasa (5/30 corridas) | `attempt` captura la excepción en `errores` y la prueba exige `errores == []` (mensaje con tipo y texto) |
| Vector incompleto (`results == [409]`) | aceptado: ninguna aserción sobre `results` | rechazado: `len(results) == 2 and set(results) <= {200, 409} and 200 in results` |
| Prueba de arnés | — | O2-11: un hilo que lanza `ValueError` aparece en la lista devuelta por `_en_hilos`; O2-02 exige `errores == []` durante la carrera forzada |
| Tras la corrección | — | 20/20 corridas del objetivo sin aviso de hilo muerto; 10/10 módulo; I1 ×10 SQLite y ×5 PostgreSQL con 0 excepciones (`directed-series-after.txt`) |

OBS-03 (comportamiento global de `TestClient`) no se cierra: solo se corrige localmente lo necesario para que la aserción
del objetivo sea veraz.
