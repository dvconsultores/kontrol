# GOV-CTL-10 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `c2f4102`, puertos 18100 / 15273 / 18110; corrida `r20261107t001104p9800nc1021d`.
- **Relevo:** la pila anterior (`b20e7b7`) cayó con el reinicio de la estación del 2026-11-07; no había conexiones vivas que respetar.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las quince pantallas de Gobierno, entre ellas Controles de cierre.
- **Comprobaciones sin login:** `/login` → 200; `GET /api/v1/gobierno/cierres/politicas` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git, y se borra al detener la pila.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
