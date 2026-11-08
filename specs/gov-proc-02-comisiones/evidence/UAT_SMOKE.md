# GOV-PROC-02 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `5371502`, puertos 18100 / 15273 / 18110; corrida `r20261108t200011p993942n804a24`.
- **Relevo:** la pila anterior (`0c0356b`) no tenía conexiones vivas; se detuvo por su fichero de parada.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las pantallas de Gobierno, Comisiones incluida.
- **Comprobaciones sin login:** `/login` y `/gobierno/contrataciones/comisiones` → 200; `GET /api/v1/gobierno/contrataciones/comisiones` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
