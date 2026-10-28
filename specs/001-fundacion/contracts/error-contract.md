# Contrato de Errores — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fuente | DOC-03 (§14), DOC-08 (§11.1) |
| Ruta | `specs/001-fundacion/contracts/error-contract.md` |

## Formato

```json
{
  "code": "FUNCTIONAL_ERROR_CODE",
  "message": "Mensaje amigable para el usuario.",
  "field_errors": {
    "field": ["Detalle de validación"]
  },
  "request_id": "uuid",
  "details": null
}
```

## Reglas

- No retornar excepciones SQL, stack traces, rutas internas, secretos, variables, datos de otros clientes/empresas.
- El frontend normaliza 400/401/403/404/409/422/423/429/5xx.
- 422 se mapea a campos; 409 = conflicto/concurrencia; 423 = modo solo consulta o bloqueo funcional.
- 401 intenta refresh una sola vez; si falla, cierre de sesión seguro.
- Nunca mostrar `details` técnico directamente al usuario.
- Un parámetro de consulta que la operación no declara responde 422 `UNKNOWN_QUERY_PARAMETER` en cualquier método
  (FR-001-268): `field_errors` con una clave `query.<nombre>` por nombre desconocido, y `details.unknown_query_parameters`
  con los nombres únicos en orden lexicográfico. La comparación es exacta y distingue mayúsculas; un valor vacío
  también cuenta; nunca se devuelve el valor. Lo comprueba un mecanismo central después de la autenticación, los
  permisos y el contexto de empresa, y antes de validar valores. No hay excepciones en `/api/v1/**`.
- Un instante (INSTANT, ADR-020) sin zona o una fecha suelta en un campo de instante responde 422 `NAIVE_DATETIME`
  cuando todos los errores de la petición son de zona; si hay otros, `VALIDATION_ERROR`. En los dos casos el campo
  lleva «Indique la zona horaria (Z o ±HH:MM).». Las fechas de negocio (AAAA-MM-DD) y los períodos (AAAA-MM) no
  cambian.

## Códigos fundacionales propuestos

| Código | Significado |
|---|---|
| `LICENSE_READ_ONLY` | Instalación en modo solo consulta (HTTP 423) |
| `LICENSE_SECURITY_SUSPENSION` | Firma inválida o manipulación (HTTP 423) |
| `LICENSE_EXPIRED` | Licencia vencida sin renovación (HTTP 423) |
| `AUTH_INVALID_CREDENTIALS` | Credenciales inválidas (HTTP 401) |
| `AUTH_ACCOUNT_LOCKED` | Cuenta bloqueada por intentos (HTTP 423) |
| `AUTH_PASSWORD_CHANGE_REQUIRED` | Debe cambiar contraseña (HTTP 403) |
| `SESSION_REVOKED` | Sesión revocada (HTTP 401) |
| `PERMISSION_DENIED` | Sin permiso (HTTP 403) |
| `SCOPE_DENIED` | Fuera de alcance organizacional (HTTP 403) |
| `VALIDATION_ERROR` | Errores de campo (HTTP 422) |
| `UNKNOWN_QUERY_PARAMETER` | Parámetro de consulta no declarado por la operación (HTTP 422) |
| `NAIVE_DATETIME` | Instante sin zona horaria explícita (HTTP 422) |
| `CONFLICT_VERSION` | Versión obsoleta / concurrencia (HTTP 409) |
| `DUPLICATE_ENTITY` | Entidad duplicada (HTTP 409) |
| `NOT_FOUND` | Recurso no encontrado (HTTP 404) |
| `RATE_LIMITED` | Límite de peticiones excedido (HTTP 429) |
| `INTERNAL_ERROR` | Error interno (HTTP 500) |
