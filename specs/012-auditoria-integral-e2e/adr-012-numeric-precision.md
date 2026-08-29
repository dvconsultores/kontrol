# ADR-016 · Precisión numérica: columnas de cantidad/medida (Float vs Numeric)

> **Renumerado en Gate G0 (2026-08-29).** Este documento se emitió como «ADR-012» tomando el número
> de la Spec que lo originó, lo que colisionaba con `specs/001-fundacion/adr/ADR-012.md` (Auditoría).
> Su identificador único en el registro maestro es **ADR-016**. La ruta del archivo se conserva para
> no romper enlaces existentes. Estado: **APPROVED**.
> Registro: `docs/governance/architecture-decision-register.md`.

> **T-202 (KAUD-011)** · Auditoría Integral E2E · 2026-08-12 · Rama `develop`
> Estado: **ACEPTADO** (decisión de alcance documentada).

## Contexto

La auditoría KAUD-011 detectó columnas numéricas modeladas como `Float` en el ORM.
En la **Ola 1** (T-201) se migraron a `Numeric(18,2)/(14,6)` todas las columnas de
**dinero** (18 columnas), quedando **36 columnas** de cantidad/medida/tasa como `Float`.
Este ADR documenta la decisión de política sobre esas 36 columnas restantes.

## Categorías y columnas

### A. Cantidad (existencia, movimientos, líneas de documento) — `Float` se CONSERVA
- `inventory`: `InventoryMovement.quantity`, `StockBalance.qty_on_hand|qty_reserved|qty_available`,
  `StockBalance.quantity`, `TransferLine.quantity_sent|quantity_received`, `InventoryCountLine.quantity`,
  `AdjustmentLine.quantity_in|quantity_remaining`.
- `purchasing`: `requisition/order/invoice/receipt` lines `quantity|quantity_ordered|quantity_received|quantity_accepted|quantity_rejected`.
- `sales`: líneas `quantity` (quotes/orders/invoices/NC/ND/pick-lists).

### B. Medida/física (factor, capacidad, contenido) — `Float` se CONSERVA
- `master_data.UnitConversion.factor`, `presentations.content`, `regulatory.Vehicle.capacity`, `regulatory.quantity`.

### C. Dinero (YA migrado a `Numeric` en T-201/migración `0014`)
- `ap_open_items.original/applied`, `ap_payments.applied`, `ap_advances.available`, `customers.credit_limit`,
  `withholding_rules.minimum/subtractor`, `bank_transactions.commission`, `cash_sessions.difference`,
  `sales/supplier_credit_notes.applied`, `sales_orders.margin`, `tax_calculations.rounding`,
  `triple_matches.variance_tax`, `*_lines.discount`.

## Decisión

1. **El dinero SIEMPRE será `Numeric`** — es obligación legal/fiscal (no se degrada).
2. **Las cantidades y medidas físicas permanecen como `Float`** por las siguientes razones:
   - Representan magnitudes **medidas/contadas** (unidades, kg, m³), no valores monetarios
     que requieran exactitud de centavo; el error de representación binaria es irrelevante
     a efectos de conteo físico.
   - Los servicios ya coercen con `float()` de forma consistente; migrar exigiría revisar
     la aritmética de 9 módulos sin beneficio funcional.
   - Las operaciones de inventario (saldo, kardex, valorización) tratan cantidades continuas
     (fracciones de unidad) donde `Float` es apropiado.
3. **Excepción a vigilar**: si en el futuro se necesitan **exactitud decimal de cantidades**
   (p. ej. liquidación fraccional con redondeo normativo), migrar selectivamente la columna
   afectada a `Numeric(18,6)` siguiendo el patrón de `0014_numeric_money_2` (con
   `postgresql_using='"{col}"::numeric'`).

## Consecuencias

- **Positivas**: sin migración riesgosa de 36 columnas; alineado con el modelo físico
  (cantidad ≠ dinero); 0 columnas de dinero en `Float` (verificación KAUD-011 cerrada).
- **Negativas/riesgo**: representación binaria en cantidades muy grandes o fraccionarias
  extremas; documentado para el equipo.
- **Validación**: `pytest 223` ✓ · `test_idempotency_concurrency.py` (movimientos sin
  duplicar saldo con `Float`) ✓ · migración `0014` offline PG ✓.

## Alternativas consideradas

| Alternativa | Veredicto |
|---|---|
| Migrar las 36 a `Numeric(18,6)` | Rechazada: alto esfuerzo, sin beneficio funcional para cantidades físicas |
| Usar `Decimal` en Python + `Float` en DB | Rechazada: inconsistencia ORM/DB sin valor |
| Dejar `Float` (decisión actual) | **Aceptada** con excepción documentada |

## Referencias

- `specs/012-auditoria-integral-e2e/orphan-endpoints-classification.md` (GAPs)
- `resources/backend/alembic/versions/0014_numeric_money_2.py` (patrón de migración)
- `qa/audits/KONTROL-AUDIT-20260812/findings.md` (KAUD-011)
