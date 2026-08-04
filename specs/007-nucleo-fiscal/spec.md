# SPEC — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Código | 007-nucleo-fiscal |
| Nombre | Núcleo fiscal: reglas, numeración, números de control, emisión, impresión, notas, retenciones, libros, períodos y homologación |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** + **002-maestros** + **004-compras-cuentas-por-pagar** (facturas proveedor, retenciones) + **005-ventas-cuentas-por-cobrar** (factura venta) + **006-tesoreria** (eventos IGTF). La implementación requiere 001 certificada, 002/004/005/006 implementados, y autorización expresa |
| Fuente | DOC-01 §1, §5, §7, §9; DOC-02 §11, §12; DOC-03 §7, §10, §12, §13 |
| Ruta | `specs/007-nucleo-fiscal/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **007-nucleo-fiscal**.

---

## 1. Problema

Los módulos administrativos (004/005/006) emiten documentos y calculan impuestos sin un **núcleo fiscal** que garantice: reglas versionadas (IVA, retención IVA, ISLR, IGTF), numeración/correlativos con asignación atómica, **números de control** (papel/imprenta), emisión fiscal inalterable con `hash`, impresión/reimpresión auditada, notas con límites al saldo ajustable, retenciones con su ciclo completo, libros reconstruibles desde eventos y períodos fiscales con cierre/reapertura aprobados.

DOC-01 §1 exige que el **núcleo fiscal se separe** de los módulos administrativos: documentos fiscales, numeraciones, números de control, tasas y eventos fiscales se versionan y quedan inalterables; una actualización administrativa no puede alterar documentos históricos ni una versión fiscal homologada.

## 2. Objetivos

1. **Reglas fiscales versionadas** (DOC-01 §9, DOC-03 §10): IVA (clasificación y alícuotas), retención IVA, ISLR e IGTF con `LegalSource` + `TaxRuleVersion` + `TaxProfile` + `TaxCalculation`; sin solape de versiones activas (DOC-03 §12).
2. **Numeración y números de control** (DOC-03 §7): `FiscalNumberSeries` (correlativos con `lock_version`), `ControlNumberBatch` (imprenta/rangos), `ControlNumber` (estados AVAILABLE/RESERVED/USED/VOID/LOST/DAMAGED); asignación **atómica** (DOC-02 §11).
3. **Emisión fiscal**: consumir correlativo y número de control dentro de **transacción atómica**; `FiscalDocument` con `hash` e inalterabilidad (DOC-02 §11, DOC-01 §5).
4. **Impresión/reimpresión auditada**: `PrintEvent` con motivo, usuario, copia y hora (DOC-02 §11).
5. **Notas fiscales**: referencia obligatoria a factura, causales, límites de cantidades/montos al **saldo ajustable** y efectos separados (DOC-02 §11, DOC-03 §7).
6. **Retenciones** con ciclo completo: calculada → aprobada → practicada → comprobante → declarada → pagada → conciliada; reversada (DOC-02 §11, DOC-03 §13).
7. **Libros fiscales reconstruibles** desde documentos y eventos (no tablas editables), equivalentes en bolívares, tasas y períodos (DOC-01 §9, DOC-02 §11).
8. **Períodos fiscales** y declaraciones: `FiscalPeriod` (open/closed/reopened con aprobaciones) y `TaxReturnBatch`.
9. **Homologación**: versión fiscal identificada, registro de eventos, integridad, conservación y proceso formal; **no declarar homologado sin acto formal** (DOC-01 §5, §9).
10. **Integración**: envolver los documentos de 004/005 (facturas/notas), retenciones de 004/005 y eventos IGTF de 006 con el núcleo fiscal.

## 3. Fuera de alcance

- **Regulación y traslados** (SICA, SIGESAI, SACS) — **Spec 008** (la guía fiscal no sustituye SICA/SIGESAI/SACS, DOC-01 §5).
- **Reportes** — Spec 009.
- El **acto formal de homologación** (SENIAT) es externo; 007 prepara la versión fiscal identificada y la trazabilidad.
- Los documentos de compra/venta (004/005) no se reimplementan: 007 los envuelve con el `FiscalDocument`.

## 4. Actores

| Actor | Uso |
|---|---|
| Configurador fiscal | Crea reglas, perfiles, series, imprentas y lotes de control (DOC-02 §12) |
| Revisor fiscal | Revisa reglas y configuraciones (DOC-02 §12) |
| Aprobador autorizado | Aprueba reglas, versiones y cierres de período (DOC-02 §12) |
| Contador / fiscal | Emisión, notas, retenciones, libros, períodos y declaraciones |
| Auditor | Trazabilidad de emisión, impresión y eventos fiscales |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-007-001 | Como configurador fiscal, quiero crear reglas IVA/retención/ISLR/IGTF versionadas con fuente legal y vigencia. |
| US-007-002 | Como configurador fiscal, quiero asignar perfiles fiscales por empresa, tercero y rubro. |
| US-007-003 | Como configurador fiscal, quiero configurar series/correlativos y lotes de números de control de imprenta. |
| US-007-004 | Como contador, quiero que la emisión fiscal consuma correlativo y número de control de forma atómica e inalterable. |
| US-007-005 | Como contador, quiero imprimir y reimprimir documentos fiscales con registro de motivo y usuario. |
| US-007-006 | Como contador, quiero emitir notas de crédito/débito con límites al saldo ajustable de la factura. |
| US-007-007 | Como contador, quiero calcular y gestionar retenciones con su ciclo completo y comprobante. |
| US-007-008 | Como contador, quiero generar libros fiscales reconstruibles desde documentos y eventos. |
| US-007-009 | Como contador, quiero gestionar períodos fiscales con cierre y reapertura aprobados. |
| US-007-010 | Como auditor, quiero la trazabilidad completa de la versión fiscal, emisión, impresión y eventos. |

## 6. Requisitos funcionales

Convención: `FR-007-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Reglas y perfiles fiscales

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-001 | `TaxRuleVersion`: reglas IVA/retención/ISLR/IGTF versionadas con vigencia y fuente legal; sin solape de versiones activas. | DOC-03 §10/§12 | P0 | Configurador |
| FR-007-002 | `LegalSource`: fuente legal (autoridad, tipo, número, gaceta, publicación, vigencias, archivo, hash). | DOC-03 §10 | P0 | Configurador |
| FR-007-003 | `TaxProfile`: perfil fiscal por empresa/tercero/rubro con clasificaciones y vigencia. | DOC-03 §10 | P0 | Configurador |
| FR-007-004 | `TaxCalculation`: cálculo por documento/línea con snapshot de base, tasa, monto, redondeo. | DOC-03 §10 | P0 | Sistema |

### 6.2 Numeración y números de control

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-010 | `FiscalNumberSeries`: series/correlativos con prefijo, siguiente número y `lock_version`; asignación atómica `Unique(company, establishment, document_type, fiscal_number)`. | DOC-03 §7/§12 | P0 | Configurador |
| FR-007-011 | `ControlNumberBatch`: lotes de control por imprenta, rango, recibido, estado y conteos. | DOC-03 §7 | P0 | Configurador |
| FR-007-012 | `ControlNumber`: estados AVAILABLE/RESERVED/USED/VOID/LOST/DAMAGED; `Unique(batch, value)`; un documento fiscal activo no comparte control. | DOC-03 §7/§12 | P0 | Sistema |

### 6.3 Emisión, impresión y contingencia

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-020 | La emisión fiscal consume correlativo y número de control dentro de **transacción atómica**. | DOC-02 §11 | P0 | Sistema |
| FR-007-021 | `FiscalDocument` con `hash` e inalterabilidad; numeración y control no se editan desde pantallas ordinarias. | DOC-01 §5 | P0 | Sistema |
| FR-007-022 | `PrintEvent`: impresión/reimpresión registrada con motivo, usuario, copia y hora. | DOC-02 §11 | P0 | Sistema |
| FR-007-023 | Contingencia de facturación: modalidad autorizada, formato, requisitos, copias e impresión. | DOC-01 §9 | P1 | Contador |

### 6.4 Notas fiscales

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-030 | `CreditDebitNote`: referencia obligatoria a factura, causales, límites de cantidades/montos al saldo ajustable y efectos separados. | DOC-02 §11, DOC-03 §7 | P0 | Contador |
| FR-007-031 | Una nota no ajusta por encima de cantidades/base/IVA pendientes del original. | DOC-03 §12 | P0 | Sistema |

### 6.5 Retenciones

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-040 | `WithholdingRule` (IVA/ISLR): concepto/código, condiciones, base, tasa, mínimo y sustraendo. | DOC-03 §10 | P0 | Configurador |
| FR-007-041 | `Withholding`: estados CALCULATED→APPROVED→PRACTICED→CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED; REVERSED. | DOC-02 §11, DOC-03 §13 | P0 | Contador |

### 6.6 Libros, períodos y declaraciones

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-050 | Libros fiscales **reconstruibles** desde documentos y eventos; equivalentes en bolívares, tasas y períodos; no desde tablas editables. | DOC-01 §9, DOC-02 §11 | P0 | Contador |
| FR-007-051 | `FiscalPeriod`: open/closed/reopened con aprobaciones y plazos. | DOC-03 §10 | P0 | Contador |
| FR-007-052 | `TaxReturnBatch`: declaraciones con archivos, totales, presentación, pago y conciliación. | DOC-03 §10 | P1 | Contador |

### 6.7 Homologación e integración

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-007-060 | Versión fiscal identificada + registro de eventos + integridad + conservación; **no declarar homologado sin acto formal**. | DOC-01 §5/§9 | P0 | Sistema |
| FR-007-061 | 007 consume documentos fiscales de 004/005, retenciones de 004/005 y eventos IGTF de 006 (contratos v1); no duplica su lógica. | DOC-01 §1 | P0 | Sistema |
| FR-007-100 | Aislamiento multiempresa; idempotencia en POST críticos; decimal exacto; asignación bajo lock/transacción. | DOC-03 §12 | P0 | Sistema |
| FR-007-101 | Frontend: configuración fiscal, numeración/control, emisión, impresión, retenciones y libros. | DOC-08 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5 / DOC-02 §11)

- No existe eliminación física de facturas, notas, retenciones ni eventos fiscales; corrección por documento de ajuste relacionado (P5).
- La numeración fiscal y los números de control no se editan desde pantallas ordinarias.
- La moneda de pago no modifica por sí sola el IVA causado.
- Una factura tiene una sola obligación fiscal; el cobro puede usar varios medios y monedas.
- La emisión consume correlativo y número de control dentro de transacción atómica.
- La impresión y reimpresión quedan registradas con motivo y usuario (PrintEvent).
- Los libros se generan desde documentos y eventos, no desde tablas editables.
- Las reglas fiscales son versionadas con fuente legal; prohibido hardcodear (P8).
- No declarar que Kontrol está homologado sin acto formal y versión fiscal aprobada.
- La guía fiscal no sustituye SICA/SIGESAI/SACS (008).

## 8. Criterios de éxito (resumen)

- Reglas IVA/retención/ISLR/IGTF versionadas con fuente legal y sin solape de vigentes.
- Series/correlativos y números de control con asignación atómica e inalterable.
- La emisión consume correlativo + control en transacción atómica con `hash`.
- Impresión/reimpresión auditadas (PrintEvent).
- Notas con límites al saldo ajustable del original.
- Retenciones con ciclo completo y comprobante.
- Libros reconstruibles desde documentos y eventos en bolívares/tasas/períodos.
- Períodos fiscales con cierre/reapertura aprobados.
- Trazabilidad completa de la versión fiscal sin declarar homologación no formal.
