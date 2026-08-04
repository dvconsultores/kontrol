# CRITERIOS DE ACEPTACIÓN — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/acceptance-criteria.md` |

> Cada AC-006-XXX se enlaza a su FR en `traceability-matrix.md`. "Verde" = criterio demostrable con prueba automatizada o evidencia.

| ID | FR | Criterio de aceptación | Verde |
|---|---|---|---|
| AC-006-001 | FR-006-001 | Se crea una `CashSession` con caja, usuario, apertura, movimientos, conteo, diferencia y estado. | ⬜ |
| AC-006-002 | FR-006-002 | Una caja recorre apertura → movimientos → arqueo → pre-cierre → cierre en ese orden; se rechaza un avance inválido. | ⬜ |
| AC-006-003 | FR-006-003 | Una caja con diferencia ≠ 0 **no se cierra** sin aprobación/justificación registrada. | ⬜ |
| AC-006-004 | FR-006-004 | El arqueo reporta conteo por método/instrumento y diferencia explícita. | ⬜ |
| AC-006-010 | FR-006-010 | `BankTransaction` registra cuenta, fecha, fecha valor, monto, referencia, fuente y estado. | ⬜ |
| AC-006-011 | FR-006-011 | Las cuentas bancarias soportan moneda, comisiones y conciliación. | ⬜ |
| AC-006-012 | FR-006-012 | Los maestros financieros (bancos, cuentas, cajas, métodos e instrumentos, monedas y tasas) están disponibles y versionados. | ⬜ |
| AC-006-020 | FR-006-020 | Un cobro de 005 (ingreso) y un pago de 004 (egreso) se ejecutan contra caja/banco, separados de la factura y de la obligación. | ⬜ |
| AC-006-021 | FR-006-021 | Una transacción admite varios medios; un documento admite varias transacciones. | ⬜ |
| AC-006-022 | FR-006-022 | Reintentar la ejecución de un pago/cobro con la misma clave es idempotente (no duplica). | ⬜ |
| AC-006-023 | FR-006-023 | Transferencias entre cajas/cuentas y depósitos se registran sin alterar saldos intermedios. | ⬜ |
| AC-006-030 | FR-006-030 | La conciliación asiste con reglas (match score) y admite resolución manual auditada. | ⬜ |
| AC-006-031 | FR-006-031 | `Reconciliation` registra estado de cuenta, transacción, movimiento del sistema, puntuación, estado y resolución. | ⬜ |
| AC-006-032 | FR-006-032 | Comisiones y diferencias cambiarias se registran sin alterar el IVA original. | ⬜ |
| AC-006-033 | FR-006-033 | El cierre de período es con aprobación y la reapertura queda auditada. | ⬜ |
| AC-006-040 | FR-006-040 | El IGTF se evalúa por regla y evento; no se confunde con IVA adicional (montos separados). | ⬜ |
| AC-006-041 | FR-006-041 | El IGTF referencia reglas versionadas (no hardcode); al cambiar la regla vigente cambia el cálculo futuro, no el histórico. | ⬜ |
| AC-006-050 | FR-006-050 | 006 consume los pagos de 004 y cobros de 005 vía contrato v1 sin duplicar lógica. | ⬜ |
| AC-006-051 | FR-006-051 | Un anticipo se registra sin aplicación inicial y luego se imputa a la obligación. | ⬜ |
| AC-006-052 | FR-006-052 | Cada transacción conserva snapshot de moneda y tasa histórica. | ⬜ |
| AC-006-100 | FR-006-100 | Aislamiento multiempresa; idempotencia; decimal exacto. | ⬜ |
| AC-006-101 | FR-006-101 | Pantallas funcionales sin scroll horizontal; arqueo WF-05, conciliación WF-05, ingreso/egreso WF-02. | ⬜ |
