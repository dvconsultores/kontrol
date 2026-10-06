# API Contracts — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fuente | DOC-03 (§14), DOC-07 (§12), DOC-08 (§2.1) |
| Ruta | `specs/001-fundacion/contracts/api-contracts.md` |

## Convenciones

- REST/JSON versionada (`/api/v1`); IDs opacos; timestamps ISO 8601 con zona.
- Listados con `q`, `status`, `sort`, `page`, `page_size`.
- Respuestas de entidad incluyen `allowed_actions` calculadas en backend.
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
| POST | `/api/v1/license/activate` | Importar licencia inicial firmada |
| POST | `/api/v1/license/import` | Importar archivo firmado offline |
| GET | `/api/v1/license/installation-request` | Descargar solicitud de activación; sesión + `license:view` (FR-010-108) |
| POST | `/api/v1/license/renewal-request` | Registrar comprobante/solicitud |
| GET | `/api/v1/license/history` | Historial local; sesión + `license:view` (FR-010-108) |
| POST | `/api/v1/license/sync` | Sincronización manual autorizada |

### Autenticación

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/auth/login` | Iniciar sesión |
| POST | `/api/v1/auth/logout` | Cerrar sesión (revoca) |
| POST | `/api/v1/auth/refresh` | Renovar access token |
| POST | `/api/v1/auth/change-password` | Cambiar contraseña (incluye obligatorio) |
| POST | `/api/v1/auth/password-reset/request` | Solicitar recuperación |
| POST | `/api/v1/auth/password-reset/confirm` | Confirmar recuperación |
| GET | `/api/v1/auth/sessions` | Listar sesiones propias |
| DELETE | `/api/v1/auth/sessions/{id}` | Revocar sesión |

### Organización

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/api/v1/organization/companies` | Listar/crear empresa |
| GET/PATCH | `/api/v1/organization/companies/{id}` | Consultar/editar empresa |
| GET/POST | `/api/v1/organization/branches` | Sucursales |
| GET/POST | `/api/v1/organization/establishments` | Establecimientos |
| GET/POST | `/api/v1/organization/warehouses` | Almacenes |
| GET/POST | `/api/v1/organization/locations` | Ubicaciones |

### Seguridad

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/api/v1/security/users` | Usuarios |
| GET/PATCH | `/api/v1/security/users/{id}` | Usuario (rol, alcance) |
| GET/POST | `/api/v1/security/roles` | Roles |
| GET/POST | `/api/v1/security/permissions` | Permisos |
| GET/POST | `/api/v1/security/roles/{id}/permissions` | RolePermission |

### Auditoría

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/audit/events` | Timeline con filtros y paginación |
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
