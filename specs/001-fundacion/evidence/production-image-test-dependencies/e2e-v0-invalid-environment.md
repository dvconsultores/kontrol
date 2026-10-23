# E2E V0 `r20261023t223550` — INVALID_ENVIRONMENT (OD-IMG-06), no cuenta como certificación

- **Antes:** la condición de salud se cumplió (load1 0,28; 5,9 GB disponibles; pswpin 0/min durante 3 min). Swap 2 MB.
- **Durante** (~200 s; suite de 174 s): el anfitrión **escribió 1 119 904 páginas en swap** (≈ 4,3 GB) y acabó con swap 3,46 GB y load1 12,97. Las corridas válidas de los ciclos anteriores rondan +0,2–0,4 M páginas. Sin salto de reloj ni cambio de red. Procesos de usuario ajenos en el equipo: Opera, VS Code.
- **Fallo:** `route-crawl.spec.ts:28`, «debería haber rutas de menú para recorrer», con 4 rutas cuando se esperaban más de 20, en 1,0 s. Por la dependencia de proyectos, 4 pruebas no se ejecutaron.
- **Historial:** `route-crawl.spec.ts:28` ha fallado 6 veces en 109 corridas, todas en ventanas de carga, entre ellas `r20261019t023304`, anterior a este ciclo, y las del 1 de octubre. Es la clase E2E-FLAKY-BAJO-CARGA (no se absorbe).
- **Causalidad del ciclo = 0:** en V0 el producto corre con el mismo intérprete que antes; el único cambio del arnés es una sonda previa al backend. La misma prueba pasó en la E2E V6 con este mismo código.
- **Decisión:** la E2E V0 se repite **una vez**, con la condición de salud y una comprobación de validez posterior (menos de 300 000 páginas escritas a swap durante la corrida y swap final por debajo de 2 GB).
