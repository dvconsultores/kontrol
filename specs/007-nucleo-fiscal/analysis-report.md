# INFORME DE ANÁLISIS — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Analista funcional senior |
| Ruta | `specs/007-nucleo-fiscal/analysis-report.md` |

## 1. Resumen

Se completa la fase documental de `007-nucleo-fiscal`: el núcleo fiscal **separado** de los módulos administrativos (DOC-01 §1) con reglas versionadas (IVA, retención IVA, ISLR, IGTF), numeración y números de control con asignación atómica, emisión fiscal inalterable (`FiscalDocument` + `hash`), impresión auditada (`PrintEvent`), notas fiscales con límites al saldo ajustable, retenciones con ciclo completo, libros reconstruibles, períodos fiscales y declaraciones. La integración clave: 007 **envuelve** los documentos de 004/005 y **consume** retenciones e IGTF de 006 (no duplica lógica).

## 2. Cobertura de la especificación

| Artefacto | Archivo | Estado |
|---|---|---|
| Especificación | `spec.md` | ✔ |
| Clarificaciones | `clarifications.md` | ✔ |
| Plan | `plan.md` | ✔ |
| Modelo de datos | `data-model.md` | ✔ |
| Checklist | `checklist.md` | ✔ |
| Tareas | `tasks.md` | ✔ |
| Criterios de aceptación | `acceptance-criteria.md` | ✔ |
| Investigación | `research.md` | ✔ |
| Riesgos | `risk-register.md` | ✔ |
| Trazabilidad | `traceability-matrix.md` | ✔ |
| Plan de pruebas | `test-plan.md` | ✔ |
| Contratos de API | `contracts/api-contracts.md` | ✔ |
| Wireframes | `wireframes/README.md` | ✔ |

## 3. Análisis técnico

- **Backend**: módulo `app/modules/fiscal/` con las entidades de DOC-03 §7/§10 (`FiscalDocument`, `FiscalNumberSeries`, `ControlNumberBatch`, `ControlNumber`, `CreditDebitNote`, `PrintEvent`, `LegalSource`, `TaxRuleVersion`, `TaxProfile`, `TaxCalculation`, `WithholdingRule`, `Withholding`, `TaxReturnBatch`, `FiscalPeriod`). Migración Alembic `0007_nucleo_fiscal`.
- **Atomicidad**: asignación de correlativo y número de control bajo `lock_version`/transacción (DOC-03 §12).
- **Inalterabilidad**: `FiscalDocument` con `hash`; numeración/control no editables (P5, DOC-01 §5).
- **Libros**: vista reconstruible desde documentos/eventos, no tablas editables (FR-007-050).
- **Homologación**: 007 prepara versión fiscal identificada + trazabilidad; **no declara** homologación sin acto formal (CL-007-05).
- **Integración**: contract v1 con 004/005 (documentos, retenciones) y 006 (eventos IGTF).
- **Frontend**: páginas bajo `src/modules/fiscal/` siguiendo el patrón de 003/004/005/006.

## 4. Riesgos principales (resumen)

- RSK-007-01 (hardcodear tasas) y RSK-007-02 (huecos de numeración) son los de mayor puntuación; ambos tienen mitigación por requisito/regla (FR-007-001/010/020) y reglas versionadas.

## 5. Conclusión

**No se identifican bloqueos** para iniciar la implementación de `007-nucleo-fiscal` una vez obtenida la autorización expresa. El alcance está delimitado, las dependencias (001/002/004/005/006) están implementadas y los riesgos tienen mitigación.

## 6. Estado

- [x] Fase documental completada.
- [ ] Commit de la fase documental (`spec(007): ...`).
- [ ] **DETENCIÓN: solicitar autorización expresa que mencione 007-nucleo-fiscal antes de implementar.**

> Regla P1/P2 (Constitución): la implementación **no** puede iniciar con una autorización genérica; requiere mención expresa de **007-nucleo-fiscal**.
