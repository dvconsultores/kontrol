# Humo autenticado del entorno de prueba de la dueña (2026-11-01)

| Campo | Valor |
|---|---|
| Pila | persistente, commit `8ea3a92` (ORG-01, ORG-02, ORG-03), base efímera de QA migrada a `0065_gov0_cargos` |
| Prueba | HUMO-UAT-01 (`resources/frontend/e2e/uat-humo-gobierno.spec.ts`, escrita por DeepSeek flash, auditada por Claude) |
| Usuario | sintético `gov…` creado por la API del producto con un rol de solo consulta: `organization:view`, `gobierno_ente:view`, `gobierno_estructura:view`, `gobierno_cargos:view`, `documentos:view`; alcance: empresa D1 |
| Administración usada | la identidad sintética de QA `admintenant_w0` (clon de la siembra canónica `qa/mfa-e2e-identidades.py`), nunca `admin` ni `admintenant` |
| Recorrido | login real por la interfaz → sesión → empresa D1 → menú Gobierno → «Configuración del ente» → «Estructura organizativa» → «Cargos y competencias», cada una con su encabezado y sin «Sin acceso» ni «módulo no habilitado» |
| Resultado | 1 passed (chromium) |
| Limpieza | rol retirado al usuario sintético (0 roles al terminar); la API no permite borrar usuarios |
| MFA de la dueña | `admin` y `admintenant` con `mfa_enabled = false` antes y después (estado de primer acceso preservado) |
| Credenciales | UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE (fichero local legible solo por la usuaria); nada impreso |

ORG01_OWNER_UAT_ACCESSIBLE = ORG02_OWNER_UAT_ACCESSIBLE = ORG03_OWNER_UAT_ACCESSIBLE = **YES**.
