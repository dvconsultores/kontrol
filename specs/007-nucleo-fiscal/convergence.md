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

## Delta dirigido recibido — 2026-09-11 (desde el ciclo de la Spec 036)

### El defecto

`US-007-006` dice, desde la especificación: «Como contador, quiero **emitir notas
de crédito/débito** con límites al saldo ajustable de la factura». Y
`FiscalDocument.document_type` declaraba en su propio comentario los tres tipos:
`INVOICE / CREDIT_NOTE / DEBIT_NOTE`.

La implementación de `emit_document` cubría **uno**:

```python
if not business_document.startswith("INVOICE:"):
    raise KontrolError(code="INVALID_BUSINESS_DOCUMENT", ...)
...
doc = FiscalDocument(..., document_type="INVOICE", ...)
```

El tipo estaba **escrito a mano** y el resto se rechazaba. No era una decisión:
era un requisito implementado a medias, y no se notó porque hasta la Spec 036
nadie había emitido una nota.

### Por qué es de esta Spec y no de la 036

Porque la numeración es suya. La norma exige a la nota de crédito «**consecutivo
propio**» y «**número de control**», que es exactamente lo que este núcleo
existe para asignar de forma atómica (`FR-007-020`). Si la 036 lo hubiera
resuelto por su cuenta habría creado un segundo numerador, que es lo que
`FR-007-021` prohíbe: «la numeración y el control no se editan desde pantallas
ordinarias».

### El arreglo

`EMITTABLE_DOCUMENT_TYPES = {INVOICE, CREDIT_NOTE, DEBIT_NOTE}` —los mismos tres
que el modelo declaraba—, el tipo se deriva del documento de negocio y **la serie
se comprueba contra él**: emitir una nota con la serie de facturas gastaría el
correlativo equivocado y rompería los dos libros. `SERIES_DOCUMENT_TYPE_MISMATCH`.

Nada más cambia: la reserva del correlativo, la asignación del número de control,
la atomicidad, el `hash` y la idempotencia por documento de negocio son los
mismos.

### Evidencia

| | |
|---|---|
| Prueba estructural | `test_spec036_architecture.py::test_el_motor_fiscal_sabe_de_los_tres_documentos` |
| Prueba funcional | `test_spec036_returns.py::test_la_nota_lleva_consecutivo_y_control_propios` |
| Serie equivocada | `test_spec036_returns.py::test_la_nota_no_se_emite_con_la_serie_de_las_facturas` |
| Idempotencia | `test_spec036_returns.py::test_emitir_dos_veces_no_gasta_dos_numeros` |
| E2E | `returns.spec.ts`, tres navegadores |
| Regresión | 1279 · 1271 pasan · 8 saltos · 0 fallos |

Una prueba del repositorio creaba la serie como `"FACTURA"` y emitía un
`INVOICE:`; la comprobación nueva la destapó. `"FACTURA"` aparecía en **un solo
sitio** y todo lo demás usa `"INVOICE"`: era una prueba desalineada, no un
vocabulario en pugna.

### Deuda que este delta deja anotada

`FiscalNumberSeries.document_type` es `String(32)` **sin restricción ni catálogo
canónico**. La comprobación nueva compara dos cadenas libres. Declarar el
vocabulario es de esta Spec y **no se hace aquí**: sería una decisión de modelo
fiscal que merece su propio ciclo.

### Alcance

Delta dirigido. La Spec 007/042 **no se reabre**: sigue
`BLOCKED_BY_LEGAL_VALIDATION` por `D0-07`, y este delta **no** cambia eso. Lo que
cierra es la parte de `US-007-006` que estaba implementada a medias.
