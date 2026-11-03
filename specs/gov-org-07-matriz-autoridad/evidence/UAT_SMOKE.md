# Humo autenticado del entorno de prueba de la dueña (2026-11-03)

| Campo | Valor |
|---|---|
| Pila | persistente, commit `396710b` (ORG-01, ORG-02, ORG-03, ORG-07, DOC-02 y DOC-04), corrida `r20261103t210328p49911nc44a49`, base efímera de QA migrada a `0068_gov_org07_autoridad`; puertos 18100/15273/18110 |
| Relanzamiento | la pila anterior (`ab24924`) ya no existía tras el reinicio del equipo (0 conexiones); worktree nuevo en `396710b` |
| Prueba | HUMO-UAT-01 (`resources/frontend/e2e/uat-humo-gobierno.spec.ts`, proyecto `humo-uat`, OD-QA-UAT-01) |
| Recorrido | login real por la interfaz → empresa D1 → menú Gobierno → «Configuración del ente» → «Estructura organizativa» → «Cargos y competencias» → «Actos administrativos» → «Notificaciones administrativas» → «Matriz de autoridad», cada una con su encabezado y sin «Sin acceso» ni «módulo no habilitado» |
| Resultado | 1 passed (4,2 s) |
| Limpieza | rol retirado al usuario sintético `gov…` (0 roles al terminar) |
| MFA de la dueña | `admin` y `admintenant` con `mfa_enabled = false` (estado de primer acceso preservado; no se tocó) |
| Credenciales | UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE; nada impreso |

ORG07_OWNER_UAT_ACCESSIBLE = **YES** (y ORG-01, ORG-02, ORG-03, DOC-02 y DOC-04 siguen ACCESSIBLE en esta pila).
