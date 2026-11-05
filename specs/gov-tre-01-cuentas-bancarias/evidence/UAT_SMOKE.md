# GOV-TRE-01 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `f8b7468`, puertos 18100 / 15273 / 18110; corrida `r20261105t142342p1232323nf36da5`.
- **Relevo:** la pila anterior (`707b338`) había caído con el reinicio de la estación; no había conexiones vivas que respetar.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las **doce** pantallas de Gobierno, incluidas «Cuentas bancarias» y «Bancos», sin «Sin acceso» ni «módulo no habilitado», y se le retira el rol al terminar. No toca el MFA de `admin` ni de `admintenant`.
- **Comprobaciones sin login:** `/login` → 200; `GET /api/v1/gobierno/tesoreria/cuentas` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600; no se imprime ni entra en Git, y se borra al detener la pila.

OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
