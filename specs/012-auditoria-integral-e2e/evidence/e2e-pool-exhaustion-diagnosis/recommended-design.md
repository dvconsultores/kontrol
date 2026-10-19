# Diseño recomendado para el siguiente ciclo (NO implementado aquí)

**Corrección mínima.** En `LicenseMiddleware.dispatch`, cambiar `mode = self._get_mode()` por
`mode = await run_in_threadpool(self._get_mode)`. `run_in_threadpool` es `starlette.concurrency.run_in_threadpool`, que ya
es dependencia del proyecto. La consulta del modo se espera en el threadpool y nunca en el bucle.

**Qué no cambia:**
- el pool, sus tamaños y sus esperas;
- las sesiones y su ciclo de vida;
- el analizador;
- la semántica de licencia: mismo orden, mismas exenciones, mismos 423;
- OpenAPI.

**Evidencia previa.** El contrafactual X4 bajó la latencia de 30,28 s a 3,04 s y cambió el resultado de un 500 a la
respuesta normal.

**Pruebas del ciclo de corrección (las escribe DeepSeek):**
- una regresión con uvicorn real que reproduzca X3 y exija que las retenedoras terminen sin congelarse y que la escritura
  no dé 500 por el pool;
- los controles C1, C2 y X2;
- un contrato AST: `dispatch` no llama a `_get_mode` fuera de `run_in_threadpool`;
- las pruebas de licencia en READ_ONLY y SECURITY_SUSPENSION intactas;
- las mutaciones: volver a la llamada síncrona, saltar la comprobación y cambiar las exenciones.

**Material gate.** El cambio altera el modelo de ejecución del middleware de licencia (seguridad, Spec 001), sin cambiar su
semántica. Hay que confirmar en el clarify del ciclo que ninguna prueba ni consumidor depende de que el middleware corra en el
bucle. No se conoce ninguno.

**Fuera de alcance:**
- liberar la conexión de la carga antes de clamscan, que cambia la transacción documental (Spec 046);
- cualquier cambio de tamaño del pool.
