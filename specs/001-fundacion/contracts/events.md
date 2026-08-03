# Eventos de Dominio — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fuente | DOC-03 (§15) |
| Ruta | `specs/001-fundacion/contracts/events.md` |

## Envelope de evento (outbox)

```json
{
  "id": "uuid",
  "aggregate_type": "user",
  "aggregate_id": "uuid",
  "event_type": "UserCreated",
  "occurred_at": "2026-08-03T10:00:00-04:00",
  "payload": {},
  "request_id": "req_...",
  "tenant_id": "uuid",
  "company_id": "uuid|null"
}
```

## Eventos fundacionales

| Evento | Descripción |
|---|---|
| `InstallationIdentified` | Se generó/recuperó la identidad de instalación |
| `InstallationActivationRequested` | Se generó solicitud de activación |
| `LicenseImported` | Licencia importada/activada |
| `LicenseModeChanged` | Cambio de modo (FULL_ACCESS/READ_ONLY/etc.) |
| `LicenseRenewalRequested` | Comprobante cargado |
| `CompanyActivated` | Empresa inicial creada/activada |
| `UserCreated` | Usuario creado |
| `UserPasswordChanged` | Contraseña cambiada (obligatoria o voluntaria) |
| `UserLocked` | Cuenta bloqueada por intentos |
| `SessionStarted` | Inicio de sesión exitoso |
| `SessionFailed` | Inicio fallido |
| `SessionRevoked` | Sesión revocada |
| `RoleChanged` | Cambio de rol/permiso/alcance |
| `AuditExportRequested` | Exportación de auditoría |

## Reglas

- Los eventos se publican vía `OutboxEvent` (transaccional con la operación).
- Consumidores típicos: auditoría, notificaciones, reportes, integración.
- El estado de publicación se controla con `published_at`, `attempts`, `error`.
