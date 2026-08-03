# WF-04 — Documento Transaccional

Patrón para documentos (orden/factura) — se prepara la estructura en 001 (no se emite fiscal).

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Título / Estado              [Acciones]         │
├──────────────────────────────────────────────────────────────┤
│ Cabecera (tercero, fechas, moneda, tasa)                     │
├──────────────────────────────────────────────────────────────┤
│ Líneas (producto/servicio, cantidad, precio, impuestos)      │
├──────────────────────────────────────────────────────────────┤
│ Totales por moneda · Impuestos · Pagos                       │
├──────────────────────────────────────────────────────────────┤
│ Timeline / Auditoría                                         │
└──────────────────────────────────────────────────────────────┘
```

Reglas: totales calculados en backend; snapshot por línea; sin recálculo fiscal en navegador.
