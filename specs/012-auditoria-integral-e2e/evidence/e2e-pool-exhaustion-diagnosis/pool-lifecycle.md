# Ciclo de vida de la conexión por petición (medido en la sonda, X1/X1b)
1. **Petición de escritura no exenta.** El `LicenseMiddleware`, que es `async`, llama a `_get_mode()` de forma síncrona.
   Eso hace un checkout, consulta la instalación y la licencia, y hace un checkin, todo en el hilo del bucle de eventos.
2. **`call_next` lleva la petición al endpoint síncrono, en el threadpool.** `get_db` abre la sesión. La autenticación
   (`get_current_user`) hace la primera consulta, y con ella el checkout que se mantiene.
3. **El endpoint trabaja con la conexión retenida.** Así ocurre en una carga documental durante clamscan. X1b midió 1
   conexión prestada durante el endpoint y al final de él.
4. **Se serializa la respuesta y se cierra la pila de salida** desde el bucle: `db.close()` hace el checkin. Tras la
   respuesta quedaban 0 conexiones prestadas.

**Datos medidos:**
- MAX_CONNECTIONS_PER_REQUEST = 1, porque la conexión del middleware es secuencial y no anidada.
- La demanda concurrente máxima es la de las peticiones en curso, con un tope de 40 hilos frente a 15 conexiones.
- El pool encola el exceso sin error mientras el bucle esté libre (X2 con k = 20: 20/20 OK, máximo 4,02 s).

**Si el pool está lleno y llega una escritura:**
- El paso 1 bloquea el bucle hasta 30 s, que es lo que dura `pool_timeout`.
- Ninguna petición en curso puede llegar al paso 4 ni devolver su conexión.
- A los 30 s el middleware lanza `TimeoutError`, que se convierte en un 500, y el bucle se libera.
