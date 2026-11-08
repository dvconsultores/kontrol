# GOV-0-06 · humo UAT en la pila levantada

- **Pila de prueba de la dueña:** levantada en `e2e28b9`, puertos 18100 / 15273 / 18110; corrida `r20261108t161658p302936nb72cd2`.
- **Relevo:** tras el reinicio del equipo no había pila anterior ni conexiones vivas.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las pantallas de Gobierno, Identidad institucional incluida.
- **Comprobaciones sin login:** `/login`, `/gobierno/identidad` y `/gobierno/identidad/mi-contexto` → 200; `GET /api/v1/gobierno/identidad/catalogo` y `/mi-contexto` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
