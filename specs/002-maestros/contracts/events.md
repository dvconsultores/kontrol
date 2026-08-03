# Eventos de Dominio — 002-MAESTROS

| Campo | Valor |
|---|---|
| Fuente | DOC-03 §15 |
| Ruta | `specs/002-maestros/contracts/events.md` |

## Eventos

| Evento | Descripción |
|---|---|
| `PartyCreated` | Tercero creado |
| `PartyUpdated` | Tercero actualizado |
| `PartyApproved` | Tercero aprobado (proveedor) |
| `PartyActivated` / `PartyDeactivated` | Activación / desactivación |
| `ProductCreated` | Producto creado |
| `ProductActivated` | Producto activado |
| `ServiceCreated` | Servicio creado |
| `TaxonomyNodeCreated` | Nodo de taxonomía creado |
| `AttributeDefinitionCreated` | Atributo definido |
| `ProfileVersionApproved` | Versión de perfil aprobada |
| `UnitConversionCreated` | Conversión creada |

## Reglas

- Envelope y outbox: heredados de `001-fundacion/contracts/events.md`.
- Consumidores típicos: auditoría, notificaciones, reportes, integración.
