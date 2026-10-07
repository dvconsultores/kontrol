# Health y sync — contrato (Fase 1)

| Ruta | Respuesta | Nota |
|---|---|---|
| `GET /health/live` | `{"status": "ok", "service": "kontrol-central-authority"}` | sin versión, sin entorno |
| `GET /health/ready` | `{"status": "ok"\|"degraded", "service": …, "database": "ok"\|"unreachable"}` | solo conectividad |

**Sync (`POST /v1/license/sync`): NO EXPUESTO.** El cliente actual lo llama sin autenticación
ligada a la instalación. Bloqueo material separado: `CENTRAL-SYNC-AUTHORITY-UNDEFINED`. Cuando la
dueña decida el mecanismo (p. ej. firma de la petición con la clave privada de la instalación
registrada, verificada contra la clave pública del registro), el servidor responderá el contrato
v1 existente eligiendo el artefacto vigente por período y `revision`.
