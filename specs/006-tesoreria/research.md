# INVESTIGACIÓN — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/research.md` |

## 1. Referencias documentales

| Doc | Sección | Contenido usado | Estado |
|---|---|---|---|
| DOC-01 | §4 | Tesorería: caja, bancos, ingresos, egresos, conciliación, comisiones, diferencias cambiarias e IGTF. | ✔ |
| DOC-01 | §3 | Monedas y tasas; snapshot histórico. | ✔ |
| DOC-01 | §5 | Cobros/pagos separados de la obligación; IGTF no confundir con IVA adicional. | ✔ |
| DOC-02 | §3 | Maestros / Financiero: monedas, tasas, bancos, cuentas, cajas, métodos e instrumentos y conceptos. | ✔ |
| DOC-02 | §10 | Tesorería: cajas (apertura/movimientos/arqueo/pre-cierre/cierre/diferencias), bancos/cuentas (moneda, fecha valor, referencia, comisiones, conciliación), cobros/pagos separados de la obligación, varios medios por transacción y varias transacciones por documento, anticipos sin aplicación inicial y posterior imputación, IGTF por regla y evento, conciliación asistida con reglas y resolución manual auditada. | ✔ |
| DOC-02 | §12 | Roles: Pago (crea CxP, revisa Tesorería, aprueba Aprobador de pago); Proveedor y banco (crea Compras/maestros, revisa Tesorería, aprueba Aprobador de tercero). | ✔ |
| DOC-03 | §9 | Entidades: OpenItem, Payment (direction IN/OUT, idempotency_key), PaymentInstrument, Application, Advance, BankTransaction (account, date, value_date, amount, reference, source, status), Reconciliation (statement, transaction, system movement, match score, status, resolution), CashSession (cashbox, user, opening, movements, counted, difference, status). | ✔ |
| DOC-08 | — | Wireframes: arqueo WF-05, conciliación WF-05, ingreso/egreso WF-02. | ✔ |

## 2. Estado de dependencias en el código

| Dependencia | Estado | Uso en 006 |
|---|---|---|
| 001-fundacion | Implementada (certificada) | `companies`, `users`, `warehouses`/`locations` |
| 002-maestros | Implementada | `parties` (terceros); **maestros financieros NO existen** → prerequisito |
| 004-compras | Implementada | `ap_payments`/`ap_payment_instruments`/`ap_open_items` (egresos) |
| 005-ventas | Implementada | Pagos/cobros IN (ingresos) y `OpenItem` RECEIVABLE |
| 007-nucleo-fiscal | NO (futuro) | IGTF: 006 estructura por regla/evento; motor completo en 007 |

## 3. Patrones reutilizables verificados

- Módulo backend plano `models.py`/`service.py`/`api.py` + registro en `init_models` y `app/main.py`.
- Reutilización de almacenes en 003 vía `policies` JSON (mismo patrón para políticas de caja/conciliación).
- Idempotencia en POST (004/005) → replicar en ejecución de ingresos/egresos.
- Snapshot de moneda/tasa por transacción.
- Contrato de integración v1 (004/005) para consumir pagos/cobros.

## 4. Riesgos de investigación

| Riesgo | Detalle | Mitigación |
|---|---|---|
| Duplicación de lógica de pagos | 006 podría reimplementar Payment | Consumir 004/005 vía contrato (CL-006-01) |
| IGTF incompleto | Cálculo fiscal completo es de 007 | Reglas versionadas + eventos; sin reescritura |
| Maestros financieros faltantes | No estaban en 002 | Prerequisito de 006 (CL-006-05) |

## 5. Evidencia del delta FLOAT-038-A — el número JSON no es exacto (Spec 038 · 2026-09-14)

Medido contra PostgreSQL 16.2 antes de tocar código:

| Camino | Entrada | Resultado |
|---|---|---|
| número JSON → `json.loads` → `float` → `numeric(18,2)` | `1234567890123456.78` | **`1234567890123456.80`** |
| `Decimal` → `jsonable_encoder` → respuesta | `Decimal('1234567890123456.78')` | **`1234567890123456.8`** |
| texto → `Decimal` | `"1234567890123456.78"` | exacto |
| `float` con `gt=0` → `numeric(18,2)` | `0.001` | **`0.00`**: un movimiento bancario de cero |
| redondeo de PostgreSQL | `0.005` | `0.01` (mitad hacia arriba) |
| `_money` (cuantización `Decimal`) | `0.005` | `0.00` (mitad al par) |

Conclusiones:

- la pérdida ocurre **antes** de Pydantic y otra vez **después** del servicio: convertir a `Decimal` en medio no la repara;
- el mismo módulo redondeaba de dos formas distintas según el camino, así que rechazar el exceso de escala en la frontera es la única regla que no elige entre dos números;
- la columna ya es exacta: no hace falta migración.

## 6. Evidencia del delta FLOAT-038-B — arqueo y cierre (Spec 038 · 2026-09-15)

Leído en código y en PostgreSQL 16.2 antes de tocar nada:

| Punto | Estado |
|---|---|
| Resta del arqueo | ya exacta: `_money(counted_amount) - _money(expected)`, `Decimal` (errata §14 de `spec038-convergence.md`) |
| `cash_sessions.opened_amount`, `counted_amount`, `expected_amount`, `difference` | `numeric(18,2)` en PostgreSQL; `Mapped[float]` en el ORM |
| Entrada del conteo | `ArqueoBody.counted_amount: float = Field(ge=0)` |
| Cierre | `abs(session.difference or 0.0) > 1e-6` |
| Auditoría | `float(...)` en `CASH_SESSION_ARCHED` y `CASH_SESSION_CLOSED` |
| Respuesta | `Decimal` crudo en `session_dict` → número JSON; OpenAPI `{}` |
| Pantalla | `Number(countedAmount) \|\| 0`, `toFixed(2)` y comparación numérica de la diferencia |
| Consumidores de la auditoría | ninguno lee `after`; la API de auditoría no lo interpreta |

Sobre el épsilon: con importes de escala 2 ninguna diferencia no nula es menor que
`1e-6`, de modo que el épsilon no cambiaba resultados con dinero bien formado. Su
defecto es que admite un criterio de «suficientemente cerca de cero» que no tiene
autoridad, y que el `float` de la entrada sí podía llevar a la base un valor que
no era el contado. Por eso la prueba permanente fija la regla —un céntimo es
diferencia— y no el literal.
