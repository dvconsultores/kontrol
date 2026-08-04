# PLAN — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/007-nucleo-fiscal/plan.md` |

## 1. Resumen ejecutivo

Implementar el **núcleo fiscal** separado de los módulos administrativos: reglas fiscales versionadas (IVA, retención IVA, ISLR, IGTF), numeración/correlativos y números de control con asignación atómica, emisión fiscal inalterable (`FiscalDocument` + `hash`), impresión auditada (`PrintEvent`), notas fiscales con límites al saldo ajustable, retenciones con ciclo completo, libros reconstruibles, períodos fiscales y declaraciones. Backend `app/modules/fiscal/`, migración `0007_nucleo_fiscal`, tests, frontend `src/modules/fiscal/`.

## 2. Estrategia técnica

- **Backend** (`app/modules/fiscal/`): patrón `models.py` / `service.py` / `api.py` / `__init__.py`, registrado en `app/core/database.py` (init_models) y `app/main.py`. Prefijo `/fiscal`.
- **Migración**: Alembic `0007_nucleo_fiscal`. Actualizar head.
- **Reutilización**: 007 **envuelve** los documentos de 004/005 (`FiscalDocument` ligado a `SalesInvoice`/`SupplierInvoice`), las retenciones de 004/005 y los eventos IGTF de 006. No redefinir tablas existentes.
- **Núcleo**: reglas (`LegalSource`, `TaxRuleVersion`, `TaxProfile`, `TaxCalculation`), numeración (`FiscalNumberSeries`), control (`ControlNumberBatch`, `ControlNumber`), emisión (`FiscalDocument`, `CreditDebitNote`, `PrintEvent`), retenciones (`WithholdingRule`, `Withholding`), períodos/declaraciones (`FiscalPeriod`, `TaxReturnBatch`), libros (vista reconstruible).
- **Atomicidad**: asignación de correlativo y control con `lock_version`/transacción (DOC-03 §12).
- **Tests**: fixture `conftest.py` (sqlite in-memory). Cobertura de reglas, numeración, emisión atómica, hash, impresión, notas, retenciones, libros y períodos.
- **Frontend** (`src/modules/fiscal/`): configuración fiscal, numeración/control, emisión, impresión, retenciones y libros con patrón `DataTable` + `AsyncButton`.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Reglas fiscales: `LegalSource`, `TaxRuleVersion`, `TaxProfile`, `TaxCalculation` | Modelos + API | pytest/ruff/mypy |
| F2 | Numeración y control: `FiscalNumberSeries`, `ControlNumberBatch`, `ControlNumber` (asignación atómica) | Modelos + servicio + API | pytest |
| F3 | Emisión e impresión: `FiscalDocument` (+hash), `PrintEvent`, contingencia | Modelos + servicio + API | pytest |
| F4 | Notas fiscales: `CreditDebitNote` con límites al saldo ajustable | Modelos + servicio + API | pytest |
| F5 | Retenciones: `WithholdingRule`, `Withholding` (ciclo completo) | Modelos + servicio + API | pytest |
| F6 | Períodos y declaraciones: `FiscalPeriod`, `TaxReturnBatch`; libros reconstruibles | Modelos + servicio + API | pytest |
| F7 | Migración `0007_nucleo_fiscal` + integración 004/005/006 | Migración + contract tests | alembic upgrade head |
| F8 | Frontend fiscal (config, numeración, emisión, impresión, retenciones, libros) | Páginas + tipos | tsc/eslint/vitest/build |
| F9 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

No hay datos legacy; migración estructural `0007_nucleo_fiscal`. Las tablas de 004/005/006 no se alteran (solo se leen/consumen vía contrato).

## 5. Coordinación y riesgos clave

- Acoplamiento con 004/005/006: consumir vía contrato v1 (CL-007-01/09/SU-007-01).
- No hardcodear tasas ni reglas: versionadas con fuente legal (CL-007-02).
- Homologación no formal: 007 prepara versión/trazabilidad, no declara homologado (CL-007-05).
- Asignación atómica de correlativo/control: `lock_version` + transacción (FR-007-010/020).
