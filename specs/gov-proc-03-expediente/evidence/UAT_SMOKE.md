# GOV-PROC-03 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `815282a`, puertos 18100 / 15273 / 18110; corrida `r20261108t233104p1422388nae7260`.
- **Relevo:** la pila anterior (`5371502`) no tenía conexiones vivas; se detuvo por su fichero de parada.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**, con Expedientes y su permiso añadidos **solo en el árbol desechable de la pila** (OBS-HUMO-EXP-01: el fichero del repositorio no los incluye todavía).
- **Comprobaciones sin login:** `/login` y `/gobierno/contrataciones/expedientes` → 200; `GET /api/v1/gobierno/contrataciones/expedientes` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git.

OWNER_UAT_ACCESSIBLE = YES · OWNER_UAT_READY = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
