# GOV-TRE-01 · TRE01_PRIVATE_REUSE_MATRIX

El módulo privado de tesorería (Spec 006) es solo referencia. Nada de esto cuenta como producto de Gobierno.

| Elemento privado | Clasificación | Decisión |
|---|---|---|
| `financial_accounts` (cuenta privada) | FORBIDDEN | Las cuentas de Gobierno no se guardan aquí: sin acto, sin autorizados, sin historia, moneda con otro vocabulario |
| `financial_banks` (banco privado) | NOT_APPLICABLE | Sin código fijo ni validación del número (OD-TRE01-04) |
| `party_bank_accounts` | NOT_APPLICABLE | Cuenta de un tercero, no del ente |
| `currencies` (moneda por empresa) | NOT_APPLICABLE | Gobierno ya tiene su vocabulario (`MONEDAS_LIMITE`, ORG-03); un ente de QA no siembra `currencies` |
| Tasas, cajas, conciliación, transferencias | NOT_APPLICABLE | Fuera de alcance (TRE-02, TRE-07, TRE-09) |
| `account_type` «CORRIENTE» de `party_bank_accounts` | REUSE_PATTERN_ONLY | Coincide el literal; el vocabulario es decisión OD-TRE01-05 |
| Almacenamiento del número en claro | REUSE_PATTERN_ONLY | Se añade enmascarado y salida única auditada |
| `gov_acts`, `gov_positions`, `AuditEvent`, `record_audit`, MFA | REUSE_SHARED_PRIMITIVE | Primitivos de Gobierno y de plataforma |
| Patrón instantánea de cargo de CTL-06 | REUSE_PATTERN_ONLY | Autorizado con FK fuerte + instantánea |
| Patrón reglas no borrables + historia inmutable de CTL-01 | REUSE_PATTERN_ONLY | Disparadores en PostgreSQL |
