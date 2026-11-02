# Humo autenticado del entorno de prueba de la dueña (2026-11-02)

| Campo | Valor |
|---|---|
| Pila | persistente, commit `ab24924` (ORG-01, ORG-02, ORG-03, DOC-02 y DOC-04), corrida `r20261102t022108p2043439n18854c`, base efímera de QA migrada a `0067_gov_doc04_notificaciones`; puertos 18100/15273/18110 |
| Relanzamiento | pila anterior (`932f7d2`) detenida por su fichero de parada con 0 conexiones establecidas; worktree nuevo en `ab24924` |
| Prueba | HUMO-UAT-01 (`resources/frontend/e2e/uat-humo-gobierno.spec.ts`, proyecto `humo-uat`, OD-QA-UAT-01) |
| Recorrido | login real por la interfaz → empresa D1 → menú Gobierno → «Configuración del ente» → «Estructura organizativa» → «Cargos y competencias» → «Actos administrativos» → «Notificaciones administrativas», cada una con su encabezado y sin «Sin acceso» ni «módulo no habilitado» |
| Resultado | 1 passed (4,2 s) |
| Limpieza | rol retirado al usuario sintético `gov…` (0 roles al terminar) |
| MFA de la dueña | `admin` y `admintenant` con `mfa_enabled = false` (estado de primer acceso preservado; no se tocó) |
| Credenciales | UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE; nada impreso |

DOC04_OWNER_UAT_ACCESSIBLE = **YES** (y ORG-01, ORG-02, ORG-03, DOC-02 siguen ACCESSIBLE en esta pila).
