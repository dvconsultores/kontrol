# Licencia Firmada — Contrato (001-FUNDACION)

| Campo | Valor |
|---|---|
| Fuente | DOC-07 (§10) |
| Ruta | `specs/001-fundacion/contracts/license-contract.md` |

## Paquete mínimo firmado

```json
{
  "issuer": "KONTROL Licensing Authority",
  "license_id": "LIC-000142",
  "customer_id": "CUS-000087",
  "contract_id": "CON-000087",
  "installation_id": "KTL-VE-7D2A-8F91",
  "company_tax_id": "J-12345678-9",
  "period_start": "2026-04-01T00:00:00-04:00",
  "period_end": "2027-03-31T23:59:59-04:00",
  "critical_warning_start": "2027-04-21T00:00:00-04:00",
  "read_only_start": "2027-05-01T00:00:00-04:00",
  "entitlements": {
    "companies": 1,
    "users": 25,
    "modules": ["masters", "sales", "purchases"]
  },
  "minimum_version": "1.0.0",
  "kid": "kontrol-lic-2026-01"
}
```

## Reglas

- Firma asimétrica Ed25519 (ADR-005).
- Clave privada solo en la autoridad central.
- Verificación de firma, `audience`, `installation_id`, fechas, derechos y versión mínima en cada arranque y antes de aplicar licencia nueva.
- Una licencia alterada produce `SECURITY_SUSPENSION`, no READ_ONLY.
- Una licencia cuyo `installation_id` no coincida se rechaza.

## Datos que la instalación envía a la autoridad (permitidos)

- Identificador de licencia e instalación.
- Versión y estado técnico.
- Fecha del último heartbeat.
- Número de empresas/usuarios usados (conteos, no identidades).
- Razón social y RIF contratante.

## Datos prohibidos

- Facturas, productos, clientes, saldos.
- Contraseñas o secretos del cliente.
- Archivos de negocio.

## Período contractual

| Hito | Fecha (America/Caracas) |
|---|---|
| Inicio período anual | 1 de abril 00:00 |
| Fin período pagado | 31 de marzo 23:59 del año siguiente |
| Gracia ordinaria | 1 de abril 00:00 |
| Gracia crítica | 21 de abril 00:00 |
| Solo consulta | 1 de mayo 00:00 |
| Reactivación | momento de confirmación válida |
