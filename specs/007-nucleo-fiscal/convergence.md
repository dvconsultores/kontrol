# CONVERGENCIA — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Ruta | `specs/007-nucleo-fiscal/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-007-01 | Formatos concretos de libros/impresión (plantillas PDF) | Decisión (CL-007-11) | Contador | Pendiente |
| CVG-007-02 | Alícuotas/montos exactos IVA/ISLR/IGTF del ejercicio fiscal venezolano | Carga de datos como reglas (CL-007-12) | Fiscal | Pendiente |
| CVG-007-03 | Emisión electrónica/facturación a la SENIAT (intercambio oficial) | Esfuerzo externo | Producto | Pendiente |
| CVG-007-04 | Acto formal de homologación de la versión fiscal | Proceso formal externo (FR-007-060) | Producto | Pendiente |
| CVG-007-05 | Retenciones de 007 reutilizan 004 `ap_withholdings` (estado enterada/conciliada unificados) | Trabajo de integración | Fiscal | Pendiente |
| CVG-007-06 | Contingencia de facturación en UI | Frontend contingencia | Contador | Pendiente |

## 3. Implementado (007)

| Elemento | Estado |
|---|---|
| Reglas fiscales versionadas (`LegalSource`, `TaxRuleVersion`, `TaxProfile`, `TaxCalculation`) sin solape de vigentes | ✔ |
| Numeración y números de control (`FiscalNumberSeries`, `ControlNumberBatch`, `ControlNumber`) con asignación atómica | ✔ |
| Emisión `FiscalDocument` (correlativo + control atómicos, hash SHA-256) idempotente | ✔ |
| Impresión/reimpresión auditada (`PrintEvent` con motivo/usuario/copia) | ✔ |
| Notas fiscales con límites al saldo ajustable (`CreditDebitNote`) | ✔ |
| Retenciones: reglas (`WithholdingRule`) + ciclo completo vía 004 (`ap_withholdings`) + comprobante | ✔ |
| Períodos fiscales (`FiscalPeriod` OPEN→CLOSED→REOPENED) y declaraciones (`TaxReturnBatch`) | ✔ |
| Libros reconstruibles desde documentos/eventos (ventas, compras, retenciones, IGTF) | ✔ |
| Migración Alembic `0007_nucleo_fiscal` (head) | ✔ |
| API `/fiscal/*` (24 endpoints) | ✔ |
| Frontend: configuración, numeración, emisión, notas, retenciones, libros y períodos | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 130/130 (109 previos + 21 de fiscal) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 76 archivos, 0 issues |
| Alembic | ✔ head `0007_nucleo_fiscal` (0001→0007; ALTER de 0004 requiere PostgreSQL, igual que CI) |
| OpenAPI | ✔ 24 endpoints `/fiscal/*` (173 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Notas de arquitectura

- 007 **extiende** el módulo `fiscal` preparado en 001 (LegalSource, TaxRuleVersion, FiscalNumberSeries, ControlNumberBatch ya migradas en `0001`); añade las tablas nuevas en `0007`.
- Las retenciones instancia reutilizan `ap_withholdings` de 004 (no se redefine); el ciclo unificado es CALCULADA→PRACTICADA→EMITIDA(comprobante)→DECLARADA→PAGADA→CONCILIADA; REVERSADA (CL-007-10).
- Los libros son vistas reconstruibles, nunca tablas editables (FR-007-050).

## 6. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/004/005/006 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 008/009/010) | Pendiente — depende de 001 certificada y de Specs 008/009/010 |
