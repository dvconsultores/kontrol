# GOV-CTL-01 · humo UAT en la pila relanzada

- **Pila de prueba de la dueña:** relevada a `707b338` (worktree del scratchpad, `qa/e2e-run.py --con-analizador --orden uat_hold_707b338.sh`), puertos 18100 / 15273 / 18110; corrida `r20261104t232721p609180n17317c`.
- **Relevo:** la pila anterior (fb57ee5) había caído con el reinicio de la estación; no había conexiones vivas que respetar.
- **Humo autenticado HUMO-UAT-01** (proyecto `humo-uat`, fuera de la canónica): **1/1**. Un usuario sintético de consulta abre por el menú las **diez** pantallas de Gobierno, incluida «Segregación de funciones», sin «Sin acceso» ni «módulo no habilitado», y se le retira el rol al terminar. No toca el MFA de `admin` ni de `admintenant`.
- **Comprobaciones sin login:** `/login` → 200; `GET /api/v1/gobierno/sod/reglas` sin sesión → 401.
- **Acceso de la dueña:** fichero local con permisos 600 en el scratchpad (no se imprime ni entra en Git); se borra al detener la pila.

OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES · OWNER_ACCEPTED = pendiente (solo la dueña).
