# API Contracts — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fuente | DOC-03 (§14), DOC-07 (§12), DOC-08 (§2.1) |
| Ruta | `specs/001-fundacion/contracts/api-contracts.md` |

## Convenciones

- REST/JSON versionada (`/api/v1`); IDs opacos; timestamps ISO 8601 con zona.
- Listados con `q`, `status`, `sort`, `page`, `page_size`.
- Respuestas de entidad incluyen `allowed_actions` calculadas en backend.
- Autoridad por empresa (ADR-017): las rutas de empresa que declaran un permiso y los catálogos de todo el tenant en todas las empresas exigen la capacidad en la empresa de la petición, con el alcance de `user_scopes` (sin filas, todo el tenant); las lecturas de empresa sin permiso declarado siguen gobernadas por el acceso (ARCH-MC-001). Precedencia: tenant ajeno o empresa inaccesible/inexistente → 404 `COMPANY_NOT_FOUND`; sin la capacidad en ninguna empresa → 403 `PERMISSION_DENIED`; con ella pero no en la empresa de la petición → 403 `COMPANY_SCOPE_FORBIDDEN`, sin efecto y auditado como `COMPANY_SCOPE_DENIED`; después, las reglas de dominio; nunca un 500, y `X-Kontrol-Company` elige la empresa, no la autoriza.
- Autoridad en la interfaz (ADR-018): la UI no tiene modelo de permisos propio; decide menú, rutas y acciones con tres proyecciones de solo lectura del backend (`/auth/operations`, `/authority/company` y `tenant_permissions` de `/auth/me`). Es orientación de uso: el backend autoriza cada petición.
- POST críticos aceptan `Idempotency-Key`.
- PATCH usa `version`/ETag.
- Transiciones usan endpoints explícitos: `/submit`, `/approve`, `/cancel`, `/revoke`.

## Endpoints fundacionales (alto nivel)

### Instalación y licencia local

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/health/live` | Liveness: `{status, service}`, público, sin versión (FR-010-116) |
| GET | `/api/v1/health/ready` | Readiness |
| GET | `/api/v1/license/status` | Estado público mínimo, sin sesión: `{mode, license_url}` (FR-010-102) |
| GET | `/api/v1/license/detail` | Estado completo —identidad, modo, fechas, derechos—; sesión + `license:view` (FR-010-107) |
| POST | `/api/v1/license/activate` | Importar licencia inicial firmada; sesión + `license:create` (FR-010-125..127) |
| POST | `/api/v1/license/import` | Importar archivo firmado offline; sesión + `license:create` (FR-010-125..127) |
| GET | `/api/v1/license/installation-request` | Descargar solicitud de activación; sesión + `license:view` (FR-010-108) |
| POST | `/api/v1/license/renewal-request` | Registrar comprobante/solicitud |
| GET | `/api/v1/license/history` | Historial local; sesión + `license:view` (FR-010-108) |
| POST | `/api/v1/license/sync` | Sincronización manual autorizada |

### Autenticación

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/auth/login` | Iniciar sesión: `AUTHENTICATED`, o `MFA_REQUIRED`/`MFA_ENROLLMENT_REQUIRED` con `challenge_token` (Spec 002) |
| POST | `/api/v1/auth/logout` | Cerrar sesión (revoca) |
| POST | `/api/v1/auth/refresh` | Renovar access token |
| POST | `/api/v1/auth/change-password` | Cambiar contraseña (incluye obligatorio) |
| GET | `/api/v1/auth/me` | Usuario actual con `permissions` (lo que usa `require_permission`) y `tenant_permissions` (capacidades que valen en todas las empresas del tenant; vacío si no hay empresas) (ADR-018) |
| GET | `/api/v1/auth/operations` | Catálogo de operaciones de la API `{operations: [{method, path, capabilities, scope}]}`, `scope` ∈ COMPANY / TENANT / GLOBAL; igual para todo usuario, sin datos de usuario (ADR-018) |
| POST | `/api/v1/auth/mfa/verify` | Completar el login con TOTP o código de recuperación (`challenge_token`); público |
| POST | `/api/v1/auth/mfa/enrollment` | Iniciar el alta del factor: forzada (con `challenge_token`, pública) o voluntaria/reemplazo (con sesión) |
| POST | `/api/v1/auth/mfa/enrollment/confirm` | Confirmar el alta con el primer código; devuelve los 10 códigos de recuperación |
| GET | `/api/v1/auth/mfa` | Estado del segundo factor del usuario (exigido, clase de política, activo, códigos restantes) |
| POST | `/api/v1/auth/mfa/recovery-codes` | Generar códigos de recuperación nuevos (invalida los anteriores; exige reautenticación) |
| DELETE | `/api/v1/auth/mfa` | Quitar el factor propio (solo usuarios STANDARD; exige reautenticación) |
| POST | `/api/v1/auth/reauth` | Reautenticación (contraseña + código) válida 5 min para operaciones críticas |
| POST | `/api/v1/auth/password-reset/request` | Solicitar recuperación: responde siempre 202 `{ok: true}`; no revela si la cuenta existe ni devuelve código (sin canal fuera de banda no se emite; público) |
| POST | `/api/v1/auth/password-reset/confirm` | Fijar la contraseña con el código que entrega el soporte (`password_breakglass`): 200, o 400 `RESET_TOKEN_INVALID` / `RESET_TOKEN_EXPIRED` / `RESET_TOKEN_USED`, 422 `PASSWORD_POLICY`; revoca todas las sesiones y no toca el MFA (público) |
| GET | `/api/v1/auth/sessions` | Listar sesiones propias |
| DELETE | `/api/v1/auth/sessions/{id}` | Revocar sesión |

Cualquier operación crítica puede responder 403 `REAUTH_REQUIRED`; el cliente pide la reautenticación y repite la petición una vez (Spec 002, ADR-004).

Toda sesión lleva el sello de credencial del usuario: cambia con cada cambio o recuperación de contraseña, y una sesión con otro sello responde 401 `SESSION_REVOKED`, también al renovar (Spec 002, ADR-004).

### Organización

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/api/v1/organization/companies` | Listar/crear empresa |
| GET/PATCH | `/api/v1/organization/companies/{id}` | Consultar/editar empresa |
| GET/POST | `/api/v1/organization/branches` | Sucursales |
| GET/POST | `/api/v1/organization/establishments` | Establecimientos |
| GET/POST | `/api/v1/organization/warehouses` | Almacenes |
| GET/POST | `/api/v1/organization/locations` | Ubicaciones |
| GET | `/api/v1/authority/company` | Capacidades efectivas del usuario en la empresa de `X-Kontrol-Company`: `{company_id, permissions}`; empresa inaccesible, de otro tenant o inexistente → 404 `COMPANY_NOT_FOUND` (ADR-018) |

### Seguridad

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/api/v1/security/users` | Usuarios |
| GET/PATCH | `/api/v1/security/users/{id}` | Usuario (rol, alcance) |
| POST | `/api/v1/users/{id}/mfa/reset` | Restablecer el MFA de otro usuario (`users:mfa_reset`, nunca uno mismo, techo de privilegios, cierra sus sesiones; exige reautenticación) |
| GET | `/api/v1/roles` | Roles visibles para el tenant del actor (los de empresa de otro tenant no se listan); cada uno con `delegable` y `motivo` (`AUTHORITY_CEILING_EXCEEDED`) calculados para quien pregunta (`roles:view`) |
| POST | `/api/v1/roles` | Alta de un rol personalizado (`roles:create`, reautenticación). Techo: los permisos ⊆ los del actor y el alcance de empresa dentro del suyo; si no, 403 `AUTHORITY_CEILING_EXCEEDED` / `CROSS_SCOPE_DELEGATION_FORBIDDEN` (auditado como `AUTHORITY_DELEGATION_DENIED`) |
| POST | `/api/v1/users/{id}/roles` | Asignar `{role_id, company_id?}` (`roles:edit`, reautenticación; campos no declarados → 422). Techo: capacidades del rol ⊆ las del actor (403 `AUTHORITY_CEILING_EXCEEDED`, o `SELF_ESCALATION_FORBIDDEN` a uno mismo); rol protegido (ADMIN, FUNCIONAL_COMPLETO) solo si el actor lo tiene con ese alcance; alcance concedido ⊆ el del actor (403 `CROSS_SCOPE_DELEGATION_FORBIDDEN`); rol de otro tenant 404 `ROLE_NOT_FOUND`; inactivo 409 `ROLE_INACTIVE` |
| DELETE | `/api/v1/users/{id}/roles/{role_id}` | Quitar (`roles:edit`, reautenticación), también renunciar a un rol propio. Solo roles dentro del techo del actor (403 `AUTHORITY_CEILING_EXCEEDED` / `TARGET_OUT_OF_SCOPE`); nunca deja al tenant sin administrador de seguridad (`users:create` + `roles:edit` + `users:mfa_reset`): 409 `LAST_SECURITY_ADMIN_REQUIRED` (auditado como `LAST_ADMIN_OPERATION_DENIED`) |
| GET/POST | `/api/v1/security/roles` | Roles |
| GET/POST | `/api/v1/security/permissions` | Permisos |
| GET/POST | `/api/v1/security/roles/{id}/permissions` | RolePermission |

### Auditoría

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/audit/events` | Timeline con filtros y paginación; solo eventos de empresas donde el actor tiene `audit:view` (los sin empresa, solo con `audit:view` en todo el tenant) (ADR-017) |
| GET | `/api/v1/audit/events/{id}` | Detalle de evento |

### Diagnóstico

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/system/diagnostics` | Estado de servicios, versión, identidad, licencia (sanitizado) |

## Ejemplo de respuesta con allowed_actions

```json
{
  "allowed_actions": {
    "view": true,
    "edit": true,
    "activate": false,
    "deactivate": true,
    "delete": false,
    "audit": true
  }
}
```

## Respuesta de bloqueo por licencia (HTTP 423)

```json
{
  "code": "LICENSE_READ_ONLY",
  "message": "La licencia anual de KONTROL no ha sido renovada. La instalación se encuentra en modo solo consulta.",
  "read_only_since": "2027-05-01T00:00:00-04:00",
  "license_url": "/mi-licencia",
  "request_id": "..."
}
```
