# Entorno de prueba de la dueña · actualización a ORG-03 (2026-11-01)

| Campo | Valor |
|---|---|
| UAT_ENVIRONMENT_HEAD (al entrar) | `e993792` (ORG-01, ORG-02) |
| UAT_ENVIRONMENT_CURRENT_HEAD | `8ea3a92` (worktree desacoplado, sin cambios locales) |
| Propiedad comprobada | los tres puertos (18100, 15273, 18110) eran procesos de la pila del propio proyecto, lanzados desde su worktree |
| Uso en curso | 0 conexiones establecidas a 15273/18100 antes de detenerla (ninguna pestaña abierta) |
| Parada | por el fichero de parada del guion de espera: limpieza LIMPIA (base efímera anterior eliminada) |
| Base | efímera nueva en el PostgreSQL de QA, migrada hasta `0065_gov0_cargos` (65 migraciones), siembra sintética del arnés |
| Analizador documental | ClamAV de QA (`--con-analizador`), igual que la E2E canónica |
| Producción | no se tocó |

## Humo (sin alterar el estado de partida)

`admin` responde `MFA_ENROLLMENT_REQUIRED` en su primer acceso: es el estado previsto para que la dueña dé de alta su propio
autenticador. Un humo autenticado consumiría esa alta y la dejaría sin acceso, así que el humo se limitó a comprobaciones sin escritura:

| Comprobación | Resultado |
|---|---|
| `GET /login` (frontend 15273) | 200 |
| `POST /api/v1/auth/login` (`admin`) | `MFA_ENROLLMENT_REQUIRED` (correcto para el primer acceso) |
| Menú servido (`src/layout/Sidebar.tsx`): «Configuración del ente», «Estructura organizativa», «Cargos y competencias» | presentes, con destino `/gobierno/ente`, `/gobierno/estructura`, `/gobierno/cargos` |
| API sin sesión: `/gobierno/ente`, `/gobierno/estructuras`, `/gobierno/estructuras/2026/cargos` | 401 (montadas y protegidas) |
| OpenAPI servido | 22 rutas de Gobierno, 9 de cargos |

El recorrido autenticado login → menú → proceso de los tres procesos sobre este mismo commit lo certifican la E2E de Gobierno
(60/60 ×3 navegadores ×3 corridas) y la E2E canónica (408/408) del ciclo GOV-0-03, con el mismo arnés y la misma siembra.

ORG01_UAT_ACCESSIBLE = ORG02_UAT_ACCESSIBLE = ORG03_UAT_ACCESSIBLE = **YES** (con la salvedad anterior: la dueña es quien hace el
primer login real).
