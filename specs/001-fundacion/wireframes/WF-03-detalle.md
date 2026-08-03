# WF-03 — Detalle de Entidad

Patrón de detalle (DOC-08 §6).

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Título                     [Acciones permitidas] │
│ Resumen + Estado + Identidad                                 │
├──────────────────────────────────────────────────────────────┤
│ Pestañas/Secciones: Datos · Configuración · Alcance · Auditoría│
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Timeline de auditoría (Request ID, usuario, fecha)        │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

Reglas: `allowed_actions` del backend; sin modales de edición; auditoría accesible sin exponer datos fuera de alcance.
