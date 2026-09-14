# CONTRATOS DE API — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 (contratos v1) |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/contracts/api-contracts.md` |

> Autenticación/contexto: `X-Company-Id`, `Authorization: Bearer`. Respuesta estándar: `{data, meta}` o `{error: {code, message, details}}`. Idempotencia: `Idempotency-Key` en POST críticos. Los montos se expresan con decimal exacto.

## 1. Maestros financieros (prerequisito)

### Bancos
- `GET/POST /treasury/banks` · `GET/PUT /treasury/banks/{id}` — `financial_banks`.
- Body POST: `{code, name, swift?, country?, policies?}`.

### Cuentas bancarias
- `GET/POST /treasury/accounts` · `GET/PUT /treasury/accounts/{id}` — `financial_accounts`.
- Body: `{bank_id, code, name, currency, iban?, reference?, status}`.

### Cajas
- `GET/POST /treasury/cashboxes` · `GET/PUT /treasury/cashboxes/{id}` — `cashboxes`.
- Body: `{code, name, currency, warehouse_id?, policies?}`.

### Métodos e instrumentos
- `GET/POST /treasury/payment-methods` · `GET/POST /treasury/payment-instruments`.
- Body method: `{code, name, kind: CASH|BANK|OTHER, status}`.
- Body instrument: `{method_id, code, name, cashbox_id?, account_id?}`.

### Monedas y tasas
- `GET/POST /treasury/currencies` · `GET/POST /treasury/exchange-rates`.
- Body rate: `{currency_id, rate_date, rate, source?}`.

## 2. Cajas — sesiones y movimientos

- `POST /treasury/cash-sessions` — apertura: `{cashbox_id, opened_amount}` → `CashSession` OPEN.
- `POST /treasury/cash-sessions/{id}/movements` — `{movement_type: IN|OUT|ADJUST, payment_id?, amount, instrument_id?, reference?}`.
- `POST /treasury/cash-sessions/{id}/arqueo` — `{counted_amount, notes?}` → diferencia = conteo − esperado.
- `POST /treasury/cash-sessions/{id}/pre-close` — cierra movimientos; requiere arqueo.
- `POST /treasury/cash-sessions/{id}/close` — `{difference_approved: bool, approval_note?}`; **rechaza si diferencia ≠ 0 sin aprobación** (FR-006-003).
- `GET /treasury/cash-sessions/{id}` — detalle con movimientos y saldo.

## 3. Bancos — transacciones e ingresos/egresos

- `GET/POST /treasury/bank-transactions` — body: `{account_id, txn_date, value_date, direction: IN|OUT, amount, currency, reference, source, commission?}`. Importes como **texto decimal** (§3.1).

### 3.1 Contrato monetario del movimiento bancario — delta FLOAT-038-A (Spec 038 · 2026-09-14)

> **Cambio incompatible, autorizado por el owner** (`OQ-FLOAT-038-A-01`, `-02`).
> Antes, `amount` y `commission` eran números JSON al entrar y al salir. Ahora son
> texto decimal en ambos sentidos. El frontend del repositorio se adaptó en el
> mismo cambio; fuera del repositorio no hay inventario de consumidores.

| Campo | Petición | Respuesta |
|---|---|---|
| `amount` | `string`, `^[0-9]+(\.[0-9]{1,2})?$`, mayor que cero, hasta 16 dígitos enteros | `string` con dos decimales |
| `commission` | `string \| null`, `^-?[0-9]+(\.[0-9]{1,2})?$`, hasta 16 dígitos enteros | `string \| null` con dos decimales |

La escala y la precisión son las de la columna `bank_transactions.amount`,
`numeric(18,2)`. Nada se redondea.

Petición válida:

```json
{ "account_id": "…", "direction": "IN", "amount": "1234567890123456.78", "commission": "12.35" }
```

Respuesta (`POST` y cada elemento de `GET … items`):

```json
{ "amount": "1234567890123456.78", "commission": "12.35" }
```

Rechazadas con `422 VALIDATION_ERROR`, sin crear nada:

| Cuerpo | Motivo |
|---|---|
| `{"amount": 1234567890123456.78}` | número JSON |
| `{"amount": "0.001"}` · `{"amount": "0.005"}` | más de dos decimales |
| `{"amount": "0.00"}` · `{"amount": "-1.00"}` | no es mayor que cero |
| `{"amount": "1e3"}` · `"NaN"` · `"Infinity"` · `"-Infinity"` · `" 10"` · `"10."` | no es texto decimal |
| `{"amount": "12345678901234567.00"}` | más dígitos enteros que la columna |
- `POST /treasury/transfers` — `{from_cashbox_id?/from_account_id?, to_cashbox_id?/to_account_id?, amount, currency, value_date, reference?}` (FR-006-023).
- Ejecución de ingresos/egresos (consume 004/005):
  - `POST /treasury/executions/egresos` — ejecuta un pago OUT de 004 contra caja/banco (idempotente).
  - `POST /treasury/executions/ingresos` — ejecuta un cobro IN de 005 contra caja/banco (idempotente).

## 4. Conciliación

- `GET/POST /treasury/reconciliations` — body: `{account_id, statement_date, statement_ref, opening_balance, closing_balance}`.
- `POST /treasury/reconciliations/{id}/match` — propuesta de emparejamiento por reglas (match score).
- `POST /treasury/reconciliations/{id}/lines/{line_id}/resolve` — `{resolution: MATCHED|DIFFERENCE|COMMISSION|FX, notes?}` → auditoría (FR-006-030).
- `POST /treasury/reconciliations/{id}/approve` / `reject` — cierre/reapertura con aprobación.

## 5. IGTF por regla y evento

- `GET/POST /treasury/fiscal-rules` — body: `{rule_code, name, rule_type: IGTF|WITHHOLDING, version, effective_from, effective_to?, params, status}` (reglas versionadas).
- `GET /treasury/igft-events` — eventos evaluados: `{event_type, source_document, amount, currency, rate_snapshot, igft_amount, rule_id, evaluated_at}`.
- Nota: el motor fiscal completo es de 007; 006 expone la evaluación por regla/evento.

## 6. Contratos de integración (consumidos de 004/005 — v1)

| Contrato | Origen | Uso |
|---|---|---|
| Pago OUT (egreso) | 004 `ap_payments` (direction OUT) | Ejecutar contra caja/banco |
| Cobro IN (ingreso) | 005 cobros (direction IN) | Ejecutar y conciliar |
| OpenItem | 004/005 `ap_open_items` | Aplicar anticipos/pagos (FR-006-051) |
| Instrumentos | 004 `ap_payment_instruments` | Medios por transacción |
| Anticipo | 004/005 | Sin aplicación inicial e imputación posterior |

## 7. Endpoints (resumen estimado)

~24 rutas bajo `/treasury` (+ maestros financieros). Se verificarán tras implementación con `app.openapi()['paths']`.
