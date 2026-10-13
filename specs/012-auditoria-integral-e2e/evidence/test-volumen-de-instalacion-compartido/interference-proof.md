# Prueba de interferencia · gate material

| Criterio | Evidencia | Resultado |
|---|---|---|
| Visibilidad entre sesiones | `consecutive-sessions.md`: B arranca viendo la clave de A (`b48f3a0d791af572`) | **PROBADO** |
| Sobrescritura de clave | `consecutive-sessions.md` y `parallel-processes.md` 03a/03b: cada inicialización reescribe el mismo fichero | **PROBADO** |
| Lectura cruzada | 03a/03b: A firma con la clave que escribió B | **PROBADO** |
| Un proceso afecta a otro | 03a (10/13 fallos en A mientras B pasa) y 03b (determinista: 502 `CENTRAL_SYNC_REJECTED` / `SYNC_AUTH_INVALID`) | **PROBADO** |
| Imposibilidad determinista de dos sesiones aisladas concurrentes | 03b: basta que cualquier proceso inicialice una instalación entre el montaje y la firma | **PROBADO** |

`INTERFERENCE_PROVEN = YES`. Causa raíz: la ruta del volumen es una constante por máquina
(`tests/conftest.py:26`) y el producto escribe la clave siempre con el mismo nombre dentro de ese volumen
(contrato A3, correcto). Falta aislamiento en el arnés, no en el producto.
