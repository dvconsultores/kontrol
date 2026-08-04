# CLARIFICACIONES — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/007-nucleo-fiscal/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-007-01 | Documentos fiscales | ¿007 reimplementa facturas/notas? | **No.** 007 **envuelve** los documentos de 004/005 con `FiscalDocument` (serie, número, control, moneda fiscal, tasa, hash). No duplica la lógica | Arquitecto | Resuelto |
| CL-007-02 | Reglas | ¿Se hardcodean tasas? | **No.** Reglas versionadas (`LegalSource` + `TaxRuleVersion` + `TaxProfile`) sin solape de vigentes (P8, DOC-03 §12) | Fiscal | Resuelto |
| CL-007-03 | Numeración | ¿Cómo se asigna el correlativo? | Asignación **atómica bajo lock/transacción**; `Unique(company, establishment, document_type, fiscal_number)` (DOC-03 §12) | Arquitecto | Resuelto |
| CL-007-04 | Libros | ¿Tablas editables? | **No.** Libros **reconstruibles** desde documentos y eventos; equivalentes en bolívares, tasas y períodos (DOC-02 §11) | Contador | Resuelto |
| CL-007-05 | Homologación | ¿007 homologa? | No: la homologación es un **acto formal externo**. 007 prepara versión fiscal identificada + trazabilidad + integridad; no declara homologado sin acto (DOC-01 §5) | Producto | Resuelto |
| CL-007-06 | Dependencias | ¿Se implementa sin 004/005/006? | Requiere **001 certificada** y **002/004/005/006 implementados**. Fase documental sin requisitos | Producto | Resuelto |
| CL-007-07 | Impresión | ¿Cómo se audita la reimpresión? | `PrintEvent` con motivo, usuario, copia y hora; la emisión original también | Auditoría | Resuelto |
| CL-007-08 | Períodos | ¿Cierre/reapertura? | `FiscalPeriod` open/closed/reopened con aprobaciones y plazos; reapertura auditada | Contador | Resuelto |
| CL-007-09 | IGTF | ¿007 recalcula el IGTF de 006? | 007 consume los **eventos IGTF de 006** (por regla y evento) para libros/declaraciones; no recalcula por separado | Fiscal | Resuelto |
| CL-007-10 | Retenciones | ¿Estado "enterada"? | DOC-02 §11 usa enterada/conciliada; DOC-03 §13 define CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED. Se unifican: CALCULATED→APPROVED→PRACTICED→CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED; REVERSED | Fiscal | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-007-01 | La emisión fiscal es sobre documentos ya aprobados de 004/005 (no revalida inventario ni crédito) | Doble control | Contract v1 con 004/005 |
| SU-007-02 | El `hash` del FiscalDocument usa SHA-256 sobre contenido canónico | Colisión/integridad | Versionar esquema del hash |
| SU-007-03 | Los números de control aplican a empresas con autorización de imprenta (papel) y modalidad digital | Sin control asignable | `ControlNumberBatch` opcional; contingencia FR-007-023 |
| SU-007-04 | La reapertura de período fiscal requiere aprobación y queda auditada | Aperturas no controladas | `FiscalPeriod` con aprobaciones (FR-007-051) |
| SU-007-05 | Los libros se sirven bajo demanda (vista), no se materializan en tablas | Rendimiento | Índices por período/empresa/documento |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-007-11 | Formatos concretos de libros/impresión (plantillas PDF) | Impresión/exportación | No la fase documental |
| CL-007-12 | Reglas exactas de IVA/ISLR/IGTF por ejercicio fiscal venezolano (alícuotas, montos) | Parámetros por defecto | No la fase documental (se cargan como datos, no código) |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
