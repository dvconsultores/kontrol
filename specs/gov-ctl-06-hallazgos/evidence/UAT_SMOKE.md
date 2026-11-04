# Humo autenticado del entorno de prueba de la dueña (2026-11-04)

| Campo | Valor |
|---|---|
| Pila | persistente, commit `5845961` (ORG-01, ORG-02, ORG-03, ORG-07, DOC-02, DOC-04, CTL-04 y CTL-06), corrida `r20261104t143110p3271302nfae4b0`, base efímera de QA migrada a `0070_gov_ctl06_hallazgos`; puertos 18100/15273/18110 |
| Relanzamiento | la pila anterior (`0984ede`) se detuvo con su fichero de parada tras comprobar 0 conexiones establecidas (limpieza LIMPIA); worktree nuevo en `5845961` |
| Prueba | HUMO-UAT-01 (`resources/frontend/e2e/uat-humo-gobierno.spec.ts`, proyecto `humo-uat`, OD-QA-UAT-01) |
| Recorrido | login real por la interfaz → empresa D1 → menú Gobierno → «Configuración del ente» → «Estructura organizativa» → «Cargos y competencias» → «Actos administrativos» → «Notificaciones administrativas» → «Matriz de autoridad» → «Auditoría institucional» → «Hallazgos y acciones correctivas», cada una con su encabezado y sin «Sin acceso» ni «módulo no habilitado» (8 pantallas) |
| Resultado | 1 passed (3,8 s) |
| Accesibilidad sin sesión | `http://localhost:15273/` y `/gobierno/hallazgos` responden 200; la API `/api/v1/gobierno/hallazgos` sin sesión responde 401 |
| Limpieza | rol retirado al usuario sintético `gov…` (0 roles al terminar) |
| MFA de la dueña | `admin` y `admintenant` con `mfa_enabled = false` (estado de primer acceso preservado; no se tocó) |
| Credenciales | UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE (permisos 600); nada impreso |

CTL06_OWNER_UAT_ACCESSIBLE = **YES** (y ORG-01, ORG-02, ORG-03, ORG-07, DOC-02, DOC-04 y CTL-04 siguen ACCESSIBLE en esta pila).
