# PLAN DE PRUEBAS — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | QA Lead |
| Ruta | `specs/001-fundacion/test-plan.md` |

## 1. Estrategia

Niveles: unitarias, componentes, contrato, integración, base de datos, E2E, infraestructura, accesibilidad, regresión visual. Herramientas: Pytest (backend), Vitest + React Testing Library (frontend), Playwright (E2E), axe-core (accesibilidad).

## 2. Pruebas unitarias (backend)

| Área | Cobertura |
|---|---|
| Contraseñas | Argon2id, política, cambio obligatorio |
| Autenticación | login, refresh, logout, revocación |
| Sesiones | rotación, expiración, cierre multi-pestaña |
| Roles/permisos | RBAC, alcance, allowed_actions |
| Licencia | firma, installation_id, modo, calendario, fecha confiable |
| Estados | máquinas de estado de entidades |
| Validadores | RIF, formatos, IDs como texto |
| Errores | contrato uniforme, códigos |
| Auditoría | eventos obligatorios, inmutabilidad |
| Idempotencia | Idempotency-Key, reintentos |

## 3. Pruebas de componentes (frontend)

Button, IconButton, AsyncButton, FormField, TextInput, NumberInput, MoneyInput, DateInput, AsyncSelect, Checkbox, Switch, DataTable, Pagination, SearchInput, StatusFilter, EmptyState, LoadingState, ErrorState, ForbiddenState, NotFoundState, ConflictState, PersistentNotification, ConfirmationDialog, UnsavedChangesGuard, LicenseBanner, PermissionGuard, RouteGuard, ErrorBoundary, AuditTimeline, FileUploader.

## 4. Pruebas de integración

- API/PostgreSQL.
- Autenticación + permisos.
- Multiempresa (aislamiento negativo).
- Auditoría.
- Licencia (modos y bloqueo).
- Migraciones (upgrade/downgrade).
- Seeds (idempotencia).
- OpenAPI/contratos.
- Errores y request ID.

## 5. Pruebas E2E (trayectoria fundacional)

| # | Escenario |
|---|---|
| 1 | Instalación inicial (compose up, health OK) |
| 2 | Activación de licencia |
| 3 | Creación segura del administrador |
| 4 | Cambio obligatorio de contraseña |
| 5 | Inicio de sesión |
| 6 | Navegación del App Shell |
| 7 | Acceso permitido |
| 8 | Acceso prohibido (403) |
| 9 | Licencia modo completo (FULL_ACCESS) |
| 10 | Licencia modo solo consulta (READ_ONLY) |
| 11 | Cierre de sesión |
| 12 | Recuperación de contraseña |
| 13 | Sesión revocada |
| 14 | Error 404 |
| 15 | Error de red |
| 16 | Responsive |
| 17 | Accesibilidad (axe) |
| 18 | Cambio de empresa/alcance |
| 19 | Intento de acceso cruzado (aislamiento) |
| 20 | Notificación persistente |

## 6. Pruebas de infraestructura

- Build limpio (frontend/backend).
- Docker Compose (config, health).
- Persistencia de identidad.
- Reinicio y recreación de contenedores.
- Backup y restore verificados.
- Migraciones y rollback.
- Variables ausentes → falla segura.
- Secretos inseguros → detección.
- Volumen ausente → diagnóstico.
- Logs JSON con request ID.

## 7. Pruebas de licencia (calendario) — casos obligatorios

Activación online/offline; installation_id incorrecto; reconstrucción de contenedores; entrada 1/4, 21/4, 1/5; bloqueo de cada endpoint de escritura; consulta/exportación permitidas; pago reportado sin confirmar; pago confirmado antes/después del 1/5; confirmación duplicada; firma inválida; cambio de reloj; restore de backup antiguo; migración de servidor; clonación; caída de autoridad; cliente offline; tarea programada intentando escribir; webhook intentando escribir; concurrencia al cambio de fecha; número no consumido al bloquearse; plan monoempresa; plan multiempresa en límite; revocación/sustitución; actualización Docker sin perder identidad.

## 8. Puertas de CI

TypeScript estricto sin errores; lint/formato; unit + contract; migraciones upgrade/downgrade; Playwright crítico; auditoría de dependencias/secretos; build Docker reproducible; regresión visual cuando cambie el design system.

## 9. Estado

| Elemento | Estado |
|---|---|
| Plan de pruebas | ✔ |
| Casos E2E | ✔ |
| Casos de licencia | ✔ |
| Ejecución | Pendiente (implementación) |
