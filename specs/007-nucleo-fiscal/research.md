# INVESTIGACIÓN — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/research.md` |

## 1. Referencias documentales

| Doc | Sección | Contenido usado | Estado |
|---|---|---|---|
| DOC-01 | §1 | El núcleo fiscal se separa de los módulos administrativos; documentos, numeraciones, números de control, tasas y eventos fiscales se versionan y quedan inalterables. | ✔ |
| DOC-01 | §5 | No eliminación física de facturas/notas/retenciones; corrección por documento de ajuste; numeración y control no editables desde pantallas; moneda de pago no modifica IVA; una factura = una obligación fiscal; no declarar homologado sin acto formal. | ✔ |
| DOC-01 | §7 | Maestros fiscales: IVA, retenciones, conceptos ISLR, IGTF, series, correlativos, lotes de control, imprentas y perfiles. | ✔ |
| DOC-01 | §9 | Requerimientos fiscales: IVA (gravado/exento/exonerado/no sujeto, alícuotas versionadas), retención IVA (75/100 u otra regla), ISLR (concepto/código/base/tarifa/mínimo/sustraendo), IGTF, facturación (medio autorizado, forma libre, contingencia), números de control, notas, libros reconstruibles, homologación. | ✔ |
| DOC-02 | §11 | Emisión consume correlativo y número de control en transacción atómica; impresión/reimpresión registrada con motivo y usuario; notas referencian factura y limitan al saldo ajustable; retenciones (calculada, practicada, emitida, declarada, enterada, conciliada, reversada); libros desde documentos y eventos. | ✔ |
| DOC-02 | §12 | Roles: Regla fiscal — Configurador crea, Revisor fiscal revisa, Aprobador autorizado aprueba. | ✔ |
| DOC-03 | §7 | Entidades: BusinessDocument, DocumentLine, FiscalDocument (business_document, fiscal_mode, series, invoice_number, control_number, fiscal_currency, exchange_rate_snapshot, emitted_at, hash, status), FiscalNumberSeries (company, establishment, document_type, prefix, next_number, lock_version, validity), ControlNumberBatch, ControlNumber (AVAILABLE/RESERVED/USED/VOID/LOST/DAMAGED), CreditDebitNote, PrintEvent (document, copy_type, printer, user, time, reason, hash). | ✔ |
| DOC-03 | §10 | Entidades: LegalSource, TaxRuleVersion, TaxProfile, TaxCalculation, WithholdingRule, Withholding, TaxReturnBatch, FiscalPeriod. | ✔ |
| DOC-03 | §12 | Integridad: Numeración Unique(company, establishment, document_type, fiscal_number) bajo lock; Control Unique(batch,value); Factura proveedor Unique(...); RIF; Vigencia sin solape; Multiempresa. | ✔ |
| DOC-03 | §13 | Retención CALCULATED→APPROVED→PRACTICED→CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED; REVERSED. | ✔ |
| DOC-08 | — | Wireframes: configuración fiscal, emisión, impresión y libros. | ✔ |

## 2. Estado de dependencias en el código

| Dependencia | Estado | Uso en 007 |
|---|---|---|
| 001-fundacion | Implementada (certificada) | `companies`, `users`, multiempresa |
| 002-maestros | Implementada | `parties` (perfiles por tercero), rubros |
| 004-compras | Implementada | `SupplierInvoice` (factura proveedor), `Withholding` (retenciones practicadas) |
| 005-ventas | Implementada | `SalesInvoice` (factura venta → emisión), notas |
| 006-tesoreria | Implementada | `IgftEvent` (eventos IGTF para libros/declaraciones) |
| 008-regulacion | NO (futuro) | Guía fiscal no sustituye SICA/SIGESAI/SACS |

## 3. Patrones reutilizables verificados

- Módulo backend plano `models.py`/`service.py`/`api.py` + registro en `init_models` y `app/main.py`.
- `lock_version`/transacción para asignación atómica (mismo patrón de `row_version`).
- Snapshot por línea/evento (igual que 004/005/006).
- Contrato de integración v1 (004/005/006) para envolver documentos y eventos.
- Máquinas de estado con transiciones explícitas (igual que 004/005/006).

## 4. Riesgos de investigación

| Riesgo | Detalle | Mitigación |
|---|---|---|
| Duplicar documentos de 004/005 | 007 podría reimplementar facturas | Envolver vía `FiscalDocument` (CL-007-01) |
| Hardcodear tasas/reglas | IVA/ISLR/IGTF cambian | Reglas versionadas con fuente legal (P8) |
| Declarar homologación | Sin acto formal | 007 prepara versión/trazabilidad; no declara (CL-007-05) |
| Huecos/duplicados de numeración | Concurrencia | Asignación atómica bajo lock (FR-007-010/020) |
