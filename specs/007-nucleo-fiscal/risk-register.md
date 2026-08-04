# REGISTRO DE RIESGOS — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/risk-register.md` |

> Escala: P (probabilidad 1-5) × I (impacto 1-5) = R (riesgo). Umbral de acción R ≥ 8.

| ID | Riesgo | P | I | R | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RSK-007-01 | Hardcodear tasas o reglas fiscales | 3 | 5 | 15 | Reglas versionadas con `LegalSource`/`TaxRuleVersion` (P8) | Fiscal | Vigente |
| RSK-007-02 | Huecos o duplicados de numeración/control | 3 | 5 | 15 | Asignación atómica bajo lock/transacción (FR-007-010/020) | Arquitecto | Vigente |
| RSK-007-03 | Alterar documentos históricos o versión fiscal | 2 | 5 | 10 | `FiscalDocument` con `hash` e inalterabilidad (P5) | Arquitecto | Vigente |
| RSK-007-04 | Declarar homologación sin acto formal | 2 | 5 | 10 | 007 prepara versión/trazabilidad; no declara (CL-007-05) | Producto | Vigente |
| RSK-007-05 | Duplicar documentos/retenciones de 004/005 | 2 | 4 | 8 | Envolver vía `FiscalDocument`/`Withholding` (CL-007-01) | Arquitecto | Vigente |
| RSK-007-06 | Notas que exceden el saldo ajustable | 3 | 3 | 9 | Límites por cantidades/base/IVA del original (FR-007-031) | Contador | Vigente |
| RSK-007-07 | Solape de versiones de reglas vigentes | 2 | 4 | 8 | `UQ` de vigencia y validación (DOC-03 §12) | Fiscal | Vigente |
| RSK-007-08 | Libros materializados/editables | 2 | 4 | 8 | Libros como vista reconstruible (FR-007-050) | Contador | Vigente |
