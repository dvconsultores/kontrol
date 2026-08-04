# REGISTRO DE RIESGOS — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/risk-register.md` |

> Escala: P (probabilidad 1-5) × I (impacto 1-5) = R (riesgo). Umbral de acción R ≥ 8.

| ID | Riesgo | P | I | R | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RSK-008-01 | Despacho sale sin permisos (fuga) | 3 | 5 | 15 | Evaluación por línea + bloqueo por regla (FR-008-022) | Logística | Vigente |
| RSK-008-02 | Fabricar permisos externos | 2 | 5 | 10 | Solo registro/validación documental (CL-008-01) | Producto | Vigente |
| RSK-008-03 | Hardcodear aplicabilidad/reglas | 3 | 4 | 12 | Perfiles versionados (P8, FR-008-023) | Regulatorio | Vigente |
| RSK-008-04 | Contingencia mal usada | 3 | 4 | 12 | Solo con regla oficial versionada (FR-008-030) | Regulatorio | Vigente |
| RSK-008-05 | Duplicar el despacho de 005 | 2 | 4 | 8 | Consumir `Shipment` vía contrato v1 (CL-008-07) | Arquitecto | Vigente |
| RSK-008-06 | Documentos sin trazabilidad | 2 | 4 | 8 | Hash/verificación/auditoría por documento (FR-008-013) | Arquitecto | Vigente |
| RSK-008-07 | Vehículos/conductores duplicados | 2 | 3 | 6 | Registros oficiales con unicidad | Logística | Vigente |
| RSK-008-08 | Confundir guía fiscal con SICA/SIGESAI/SACS | 2 | 3 | 6 | Modelo de `official_documents` separado del fiscal | Fiscal | Vigente |
