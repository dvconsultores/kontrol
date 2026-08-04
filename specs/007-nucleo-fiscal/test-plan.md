# PLAN DE PRUEBAS — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/test-plan.md` |

> Estrategia: pytest backend (sqlite in-memory, fixture `conftest.py`), Vitest frontend, build. Se añade `tests/test_fiscal.py`.

| ID | Tipo | Caso | Prerrequisito | Resultado esperado | Estado |
|---|---|---|---|---|---|
| TP-007-01 | Unit | Crear TaxRuleVersion con fuente legal | LegalSource | Regla versionada vigente; sin solape | ⬜ |
| TP-007-02 | Unit | LegalSource con gaceta/vigencias | — | Fuente con número, publicación y vigencia | ⬜ |
| TP-007-03 | Unit | TaxProfile por tercero | Party | Perfil asignado con clasificaciones | ⬜ |
| TP-007-04 | Unit | TaxCalculation con snapshot | Regla vigente | Base/tasa/monto/redondeo snapshot | ⬜ |
| TP-007-05 | Unit | Asignación atómica de correlativo | Serie | Números consecutivos sin huecos bajo concurrencia | ⬜ |
| TP-007-06 | Unit | Lote de control de imprenta | Imprenta | Rango recibido con estados y conteos | ⬜ |
| TP-007-07 | Negativo | Control duplicado | Lote | Rechaza `Unique(batch, value)` y compartición | ⬜ |
| TP-007-08 | Unit | Emisión consume correlativo + control atómicamente | Factura 005 aprobada | Número y control asignados en una transacción | ⬜ |
| TP-007-09 | Unit | FiscalDocument con hash inalterable | Emitido | Hash estable; numeración/control no editables | ⬜ |
| TP-007-10 | Unit | PrintEvent de impresión/reimpresión | Emitido | Registro con motivo, usuario, copia y hora | ⬜ |
| TP-007-11 | Unit | Contingencia de facturación | — | Modalidad y requisitos registrados | ⬜ |
| TP-007-12 | Unit | Nota referencia factura con límite | Factura emitida | Nota dentro del saldo ajustable | ⬜ |
| TP-007-13 | Negativo | Nota excede saldo ajustable | Factura | Rechazado | ⬜ |
| TP-007-14 | Unit | WithholdingRule IVA/ISLR | — | Concepto/código/base/tasa/mínimo/sustraendo | ⬜ |
| TP-007-15 | Unit | Ciclo de retención completo | Regla + evento | CALCULATED→…→RECONCILED; REVERSED | ⬜ |
| TP-007-16 | Unit | Libro reconstruible por período | Documentos/eventos | Libro con equivalentes en Bs/tasas | ⬜ |
| TP-007-17 | Unit | Período OPEN→CLOSED→REOPENED | Período | Transiciones con aprobación; reapertura auditada | ⬜ |
| TP-007-18 | Unit | TaxReturnBatch | Período cerrado | Archivos/totales/presentación/pago/conciliación | ⬜ |
| TP-007-19 | Unit | Versión fiscal + registro de eventos | Emisiones | Trazabilidad sin declarar homologación | ⬜ |
| TP-007-20 | Integración | Contract 004/005/006 | Facturas/retenciones/IGTF | 007 envuelve y consume sin duplicar | ⬜ |
| TP-007-21 | Unit | Aislamiento multiempresa | 2 empresas | Sin fuga de datos | ⬜ |
| TP-007-22 | UI | Pantallas fiscales | Frontend | Config/numeración/emisión/libros sin scroll horizontal | ⬜ |
