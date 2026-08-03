# WF-08 — Reporte

Patrón de reporte (DOC-08 §6). La generación definitiva es en backend con ReportLab (ADR-007).

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Reporte                        [Exportar]       │
├──────────────────────────────────────────────────────────────┤
│ Parámetros (filtros, moneda, tasa, período)                  │
├──────────────────────────────────────────────────────────────┤
│ Vista previa / Estado de generación                          │
├──────────────────────────────────────────────────────────────┤
│ Descarga + Auditoría (quién, cuándo, request ID)             │
└──────────────────────────────────────────────────────────────┘
```

Reglas: PDF/Excel/CSV desde backend; datos snapshot; hash y auditoría; sin recrear cálculos fiscales en el navegador; reimpresión auditada.
