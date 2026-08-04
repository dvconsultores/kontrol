# PLAN DE PRUEBAS — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/test-plan.md` |

> Estrategia: pytest backend (sqlite in-memory, fixture `conftest.py`), Vitest frontend, build. Se añade `tests/test_treasury.py`.

| ID | Tipo | Caso | Prerrequisito | Resultado esperado | Estado |
|---|---|---|---|---|---|
| TP-006-01 | Unit | Crear CashSession | Caja + usuario | Sesión OPEN con apertura registrada | ⬜ |
| TP-006-02 | Unit | Ciclo completo de caja | Sesión abierta | Apertura→movimientos→arqueo→pre-cierre→cierre OK | ⬜ |
| TP-006-03 | Negativo | Cierre con diferencia sin aprobación | Sesión con diferencia | Rechazado; requiere aprobación/justificación | ⬜ |
| TP-006-04 | Unit | Arqueo por método/instrumento | Sesión abierta | Conteo y diferencia explícita | ⬜ |
| TP-006-05 | Unit | Crear BankTransaction | Cuenta bancaria | Transacción con fecha valor y referencia | ⬜ |
| TP-006-06 | Unit | Cuenta con comisión | Cuenta | Comisión registrada al conciliar | ⬜ |
| TP-006-07 | Unit | Maestros financieros | — | Bancos/cuentas/cajas/monedas/tasas CRUD | ⬜ |
| TP-006-08 | Integración | Egreso de 004 ejecutado contra banco | Pago 004 aprobado | Se ejecuta; aparece en caja/banco; idempotente | ⬜ |
| TP-006-09 | Unit | Varios medios por transacción | Pago | Múltiples instrumentos por transacción | ⬜ |
| TP-006-10 | Negativo | Reintento con misma idempotency_key | POST ejecutado | No duplica | ⬜ |
| TP-006-11 | Unit | Transferencia entre cajas/cuentas | 2 cajas | Saldos consistentes | ⬜ |
| TP-006-12 | Unit | Conciliación asistida por regla | Estado de cuenta + movimientos | Match con puntuación; propuesta | ⬜ |
| TP-006-13 | Unit | Resolución manual auditada | Línea sin match | Resolución registrada con usuario/fecha | ⬜ |
| TP-006-14 | Unit | Diferencia cambiaria | Pago en otra moneda | Se registra sin alterar IVA original | ⬜ |
| TP-006-15 | Unit | Cierre de período con aprobación | Período | Cierre OK; reapertura auditada | ⬜ |
| TP-006-16 | Unit | IGTF por regla y evento | Regla vigente | Monto IGTF calculado por evento | ⬜ |
| TP-006-17 | Negativo | IGTF no confundido con IVA | Factura con IVA | IGTF e IVA separados | ⬜ |
| TP-006-18 | Integración | Contrato 004/005 v1 | Pagos/cobros | 006 consume sin duplicar | ⬜ |
| TP-006-19 | Unit | Anticipo sin aplicación e imputación | Anticipo | Aplicable posterior | ⬜ |
| TP-006-20 | Unit | Snapshot de tasa histórica | Tasa posterior distinta | La transacción conserva su snapshot | ⬜ |
| TP-006-21 | Unit | Aislamiento multiempresa | 2 empresas | Sin fuga de datos | ⬜ |
| TP-006-22 | UI | Pantallas tesorería | Frontend | Arqueo/conciliación/ingreso-egreso sin scroll horizontal | ⬜ |
