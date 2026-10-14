# Entrelazados controlados (instrumentación) · `poc-output.txt`, `same-datastore-poc-uom.py`

I1 (de la secuencia SQL real de `create_version`): las dos peticiones ejecutan `SELECT` de la versión abierta y se
retienen en una `Barrier(2, timeout=10)` justo antes de su primera escritura a `product_presentation_versions`
(`UPDATE valid_to` o `INSERT`); se sueltan a la vez.

| Topología | Modo | Rondas | Resultado | Versiones (abiertas/total) |
|---|---|---|---|---|
| (a) actual (`StaticPool` `:memory:`) | natural ×30 | 30 | 18× `[200, 200]` (serializadas, legítimo) · 7× `[200, 409]` · **4× `[409]` + hilo muerto (`InvalidRequestError`)** · 1× `[200]` + `DatabaseError` · 1× `[200]` + `cannot commit transaction` | falsos verdes: 1/1 (nadie creó versión) |
| (a) | I1 | 5 | 3× `[200, 409]` · **2× `[409]` + hilo muerto, 1/1** | — |
| (b) una conexión por hilo (= `motor_para_hilos`) | natural ×30 | 30 | 27× `[200, 409]` · 3× `[200, 200]` (serializadas, legítimo) · **0 excepciones** | 1/2 ó 1/3 |
| (b) | I1 | 5 | **5× `[200, 409]`**, 1/2, 0 excepciones, sin `database is locked` | 1/2 |

Conclusión: con la conexión compartida, el entrelazado real produce hilos muertos y falsos verdes (7/35); con conexiones
propias sobre el mismo datastore, 0/35 excepciones y el contrato exacto (`[200, 409]`, una versión nueva). La barrera no
forma parte de la corrección: vive solo en la POC y en O2-02 (prueba de arnés).
