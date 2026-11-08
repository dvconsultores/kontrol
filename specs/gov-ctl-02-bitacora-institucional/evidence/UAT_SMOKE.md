# GOV-CTL-02 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `0c0356b`, puertos 18100 / 15273 / 18110; corrida `r20261108t174815p617504nb291d5`.
- **Relevo:** la pila anterior (`e2e28b9`) no tenía conexiones vivas; se detuvo por su fichero de parada, con limpieza correcta.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las pantallas de Gobierno, Bitácora institucional incluida.
- **Comprobaciones sin login:** `/login` y `/gobierno/bitacora` → 200; `GET /api/v1/gobierno/bitacora` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
