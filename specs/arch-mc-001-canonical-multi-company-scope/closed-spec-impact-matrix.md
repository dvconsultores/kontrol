# IMPACTO SOBRE LAS SPECS CERRADAS — ARCH-MC-001

| Spec | Estado | Impacto | Justificación |
|---|---|---|---|
| **008 · Almacenes físicos** | `COMPLETE_100` | **`NO_CHANGE`** | Usa FK real a `companies` en sus 8 tablas. Probado: filtrar por A y por B devuelve 1 y 1. Es la **referencia positiva** |
| **045 · Aprobaciones** | `COMPLETE_100` | **`REGRESSION_REQUIRED`** | Su modelo usa empresa real y no se toca. `approval_events` deriva de `approval_requests`: se declara, no se migra. Regresión para confirmar |
| **011 · Unidades** | `COMPLETE_100` | **`CONTRACT_ADAPTATION`** | La semántica de conversión **no se altera**. Pendiente `OQ-MC-01`: si `units_of_measure` es del tenant o de la empresa |
| **046 · Documental** | `COMPLETE_100` **en revisión** | **`RECONCERGENCE_REQUIRED`** | Su registro cerrado está roto para 16 de 19 tipos. Tras normalizar: `scope_kind` explícito, 4 entradas nuevas, 19/19 probados, `REM-046-001` cerrado y convergencia |
| **002 · Seguridad y sesiones** | Parcial | **`CONTRACT_ADAPTATION`** | Aporta `CompanyContext`. **No** debe reintroducir la carrera de `/auth/refresh` cerrada en `REM-AUTH-ROUTE-CRAWL-001` |
| **003 · Usuarios y permisos** | Parcial | **`CONTRACT_ADAPTATION`** | `UserScope` y `user_roles` pasan a ser autoridad de acceso. Se adaptan, no se sustituyen |
| **004 · Licenciamiento** | Parcial | **`CONTRACT_ADAPTATION`** | El backend impone el límite de empresas. No se inventan planes |
| **007 · Organización** | Parcial | **`MIGRATION_ONLY`** | `companies` y `branches` ya son correctas |

## Lo que no se reabre

Ninguna Spec cerrada se reabre **funcionalmente**. 008 y 045 no cambian de
comportamiento. 046 no toca almacenamiento, análisis de malware, versionado ni
modelo documental: solo su registro de recursos, que es donde está el defecto.

## Revalidación exigida tras implementar

| Spec | Qué se vuelve a ejecutar |
|---|---|
| 008 | Suite completa + E2E de estructura |
| 011 | Suite de conversión y congelado |
| 045 | Motor completo + integración 045→046 |
| 046 | Suite completa con **ClamAV real**: EICAR, falso seguro, almacenamiento, versionado, 19 tipos |
| Global | Backend, frontend, OpenAPI, Playwright en tres navegadores, recorrido de rutas |

Requiere reaprovisionar **PostgreSQL 18.6** y **ClamAV**, hoy ausentes del
entorno efímero.
