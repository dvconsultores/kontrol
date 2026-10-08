# Paquete de licencia firmado — contrato (Fase 1)

Canonicalización: `json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")`. Firma:
Ed25519 sobre esos bytes, `signature_hex`. Verificación: sobre el dict recibido, sin reconstruirlo.

```json
{
  "issuer": "KONTROL Licensing Authority",
  "license_id": "LIC-3F9A2C7B1D0E",
  "installation_id": "KTL-XX-SINTETICA",
  "customer_id": "CUS-000000", "contract_id": "CON-000000", "company_tax_id": "J-00000000-0",
  "period_start": "2027-04-01T00:00:00-04:00", "period_end": "2028-03-31T23:59:59-04:00",
  "critical_warning_start": "2028-04-21T00:00:00-04:00", "read_only_start": "2028-05-01T00:00:00-04:00",
  "entitlements": {"companies": 3, "users": 25, "modules": ["ventas"]},
  "minimum_version": "1.0.0",
  "kid": "kontrol-lic-2026-01",
  "revision": 1
}
```

| Claim | Regla |
|---|---|
| `revision` | entero ≥ 1; **dentro** del material firmado; asignado solo por la autoridad; monótono por `installation_id` + período; reinicia en 1 por período; no es `kid`, ni fecha, ni orden de llegada. Ausente = paquete **legacy** (bytes históricos intactos; nunca `revision: null`) |
| `kid` | identificador de la clave de firma del propietario (DOC-07 §10.1: la pública se versiona mediante `kid`); dentro del material firmado; obligatorio (§10.2). La autoridad lo toma de su `kid` **activo** y firma con la privada de ese `kid`; el cliente elige la pública **exactamente** por él (desconocido o ausente → rechazo; `kid` A con firma de B → firma inválida). No ordena nada (FR-010-437..466) |
| período | DOC-07 §5.1: 1 abr 00:00:00 → 31 mar 23:59:59 (`-04:00`); aviso crítico 21 abr; solo lectura 1 may |
| derechos | libres entre reemisiones; no ordenan |

Validación en el parser compartido: `revision` presente debe ser `int` (no `bool`) ≥ 1; si no,
`LicenseContractError("revision inválida")`, que el cliente responde como 423
`LICENSE_INVALID_REVISION`.
