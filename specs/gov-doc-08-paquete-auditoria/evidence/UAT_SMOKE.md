# Humo autenticado del entorno de prueba de la dueña (2026-11-04)

| Campo | Valor |
|---|---|
| Pila | Persistente. Commit `fb57ee5` (ORG-01, ORG-02, ORG-03, ORG-07, DOC-02, DOC-04, CTL-04, CTL-06 y DOC-08). Corrida `r20261104t173037p125340n19e15e`. Base efímera de QA migrada a `0071_gov_doc08_paquetes`. Puertos 18100/15273/18110 |
| Relanzamiento | La pila anterior (`5845961`) se detuvo con su fichero de parada tras comprobar 0 conexiones establecidas (limpieza LIMPIA). Worktree nuevo en `fb57ee5` |
| Prueba | HUMO-UAT-01 (`resources/frontend/e2e/uat-humo-gobierno.spec.ts`, proyecto `humo-uat`, OD-QA-UAT-01) |
| Recorrido | Login real por la interfaz → empresa D1 → menú Gobierno → «Configuración del ente» → «Estructura organizativa» → «Cargos y competencias» → «Actos administrativos» → «Notificaciones administrativas» → «Matriz de autoridad» → «Auditoría institucional» → «Hallazgos y acciones correctivas» → «Paquetes de auditoría». En las 9 pantallas aparece su encabezado y ninguna muestra «Sin acceso» ni «módulo no habilitado» |
| Resultado | 1 passed (4,4 s) |
| Accesibilidad sin sesión | `http://localhost:15273/gobierno/paquetes` responde 200; la API `/api/v1/gobierno/paquetes` sin sesión responde 401 |
| Limpieza | Rol retirado al usuario sintético `gov…` (0 roles al terminar) |
| MFA de la dueña | `admin` y `admintenant` con `mfa_enabled = false`: estado de primer acceso preservado, no se tocó |
| Credenciales | UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE (permisos 600); nada impreso |

DOC08_OWNER_UAT_ACCESSIBLE = **YES**. ORG-01, ORG-02, ORG-03, ORG-07, DOC-02, DOC-04, CTL-04 y CTL-06 siguen ACCESSIBLE en esta pila.
