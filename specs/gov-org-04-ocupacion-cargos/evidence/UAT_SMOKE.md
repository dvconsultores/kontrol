# GOV-ORG-04 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `d1656a7`, puertos 18100 / 15273 / 18110; corrida `r20261107t190705p3241803naf17ba`.
- **Relevo:** la pila anterior (`6fa6d4f`) no tenía conexiones vivas; se detuvo por su fichero de parada, sin bases huérfanas.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las pantallas de Gobierno, Ocupación de cargos incluida.
- **Comprobaciones sin login:** `/login` → 200; `/gobierno/ocupacion` → 200; `GET /api/v1/gobierno/ocupacion/catalogo` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
