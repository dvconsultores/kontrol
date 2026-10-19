# Causa raíz — PROVEN
**ROOT_CAUSE_CLASS = `EVENT_LOOP_BLOCKED_BY_SYNC_DB_IN_ASYNC_MIDDLEWARE`.** Combina las hipótesis D, F e I de la matriz.
`LicenseMiddleware.dispatch` es `async`, pero espera de forma síncrona una conexión del pool en el hilo del bucle de eventos.
Si el pool está lleno, el bucle queda bloqueado, y con él el cierre de las sesiones que devolverían conexiones: es un
bloqueo mutuo que solo rompe `pool_timeout` a los 30 s. Ese middleware termina en 500 y todas las peticiones en curso se
congelan 30 s.

**Disparador.** El pool está saturado, con 15 conexiones prestadas, justo cuando llega una escritura no exenta. En la E2E, la
saturación la producen peticiones largas que retienen su conexión: cargas documentales durante clamscan y un equipo lento
por paginación.

**Criterios:**
1. **Predice.** Ocurre solo con el pool lleno y una escritura. C1 y C2 lo confirman.
2. **Se reproduce** de forma controlada (X3), con el equipo en calma.
3. **Retirar la condición lo elimina:** con 14 retenedoras, con una lectura, o descargando la llamada en X4.
4. **Explica los 4 fallos de la E2E roja.** Son 4 `TimeoutError` en `_get_mode` → `current_mode` →
   `_instalacion_canonica`, y las 7 pantallas de módulos ajenos se congelaron justo 30 s, que es la espera de la UI.
5. **No contradice el 284/0/0 posterior.** El disparador exige coincidencia, no basta con la presión de memoria.

**Hipótesis descartadas:**
| Id | Hipótesis | Veredicto | Motivo |
|---|---|---|---|
| A | paginación o retraso del planificador como causa | **descartada como causa**, factor que agrava | X3 se reproduce sin paginación; la paginación solo alarga las retenciones |
| B | conexiones no devueltas | **descartada** | checkout = checkin, 0 prestadas al final |
| C | transacción demasiado larga | **factor**, no causa | la petición retiene su conexión toda su vida (X1b); sin el bloqueo del bucle, el pool encola bien (X2) |
| D | sesión del middleware duplicada | **parte de la causa** | conexión propia, secuencial, pero tomada en el bucle |
| E | adquisición anidada | **descartada** | máximo 1 conexión simultánea por petición |
| F | el middleware de licencia adquiere conexiones extra | **parte de la causa** | una por escritura, síncrona en el bucle |
| G | el analizador produce solo demora | **confirmada como factor de saturación** | retiene la conexión durante clamscan; por sí solo no agota nada (X2) |
| H | la concurrencia E2E supera el diseño | **factor** | más de 15 peticiones en curso es posible con 40 hilos; el pool lo tolera si el bucle está libre |
| I | defecto del ciclo de vida o cierre | **parte de la causa** | el cierre de `get_db` necesita el bucle libre |
| J | pool demasiado pequeño | **descartada como causa** | con k = 20 no falla; agrandar el pool solo desplazaría el umbral |
| K | artefacto del arnés | **descartada** | la sonda usa la app y la configuración de producción |
HOST_PAGING_CAUSAL 0 · HOST_PAGING_CORRELATED 1 (agrava) · UNKNOWN 0.
