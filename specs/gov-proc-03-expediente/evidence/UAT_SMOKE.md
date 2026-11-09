# GOV-PROC-03 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `3fd0f4e`, puertos 18100 / 15273 / 18110; corrida `r20261109t014710p1509752n48a5ac`.
- **Relevo:** la pila anterior no tenía conexiones vivas; se detuvo por su fichero de parada.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1, con el fichero publicado**, que ya cubre Expedientes.
- **Comprobaciones sin login:** `/login` y `/gobierno/contrataciones/expedientes` → 200; `GET /api/v1/gobierno/contrataciones/expedientes` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña). La pila **no contiene PROC-06**.
