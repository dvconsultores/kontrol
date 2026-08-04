# REGISTRO DE RIESGOS — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/risk-register.md` |

> Escala: P (probabilidad 1-5) × I (impacto 1-5) = R (riesgo). Umbral de acción R ≥ 8.

| ID | Riesgo | P | I | R | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RSK-009-01 | Exportaciones sin auditoría | 2 | 5 | 10 | `report_exports` obligatorio (FR-009-020) | Auditoría | Vigente |
| RSK-009-02 | Reportes lentos en datos grandes | 3 | 4 | 12 | Paginación + jobs asíncronos (FR-009-023) | Arquitecto | Vigente |
| RSK-009-03 | Fuga de datos entre empresas | 2 | 5 | 10 | Aislamiento multiempresa (FR-009-100) | Arquitecto | Vigente |
| RSK-009-04 | Duplicar lógica de 003-008 | 2 | 4 | 8 | Solo lectura vía contratos (CL-009-01) | Arquitecto | Vigente |
| RSK-009-05 | Tablas editables para saldos/libros | 2 | 4 | 8 | Reconstrucción desde eventos (CL-009-08) | Contador | Vigente |
| RSK-009-06 | Permisos por campo insuficientes | 2 | 3 | 6 | Minimización + retención (FR-009-021) | Producto | Vigente |
| RSK-009-07 | Jobs sin supervisión | 2 | 3 | 6 | Estado/error y reintento manual | Arquitecto | Vigente |
