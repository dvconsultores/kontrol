# GOV-TRE-02 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `ed1bf87`, puertos 18100 / 15273 / 18110; corrida `r20261105t232055p122279nf470f3`.
- **Relevo:** la pila anterior (`f8b7468`) había caído con el reinicio de la estación; no había conexiones vivas que respetar.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las **catorce** pantallas de Gobierno, incluidas «Programación financiera» y «Rubros de caja», sin «Sin acceso» ni «módulo no habilitado», y se le retira el rol al terminar. No toca el MFA de `admin` ni de `admintenant`.
- **Comprobaciones sin login:** `/login` → 200; `GET /api/v1/gobierno/tesoreria/programas` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git, y se borra al detener la pila.
- **Incidencia:** un segundo lanzamiento mío salió con rc 70 por los puertos ocupados y truncó el log de la pila; no afectó a la pila, y el resultado del humo se leyó de su propio log.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES tras cerrar T038 · OWNER_ACCEPTED = pendiente (solo la dueña).

**Tras T038:** la pila sigue en `ed1bf87`. El código de producto no cambió después de ese commit: T038 solo toca una prueba E2E y la configuración de Playwright. El humo se repitió en la regresión final, 1/1, y la pila responde.
