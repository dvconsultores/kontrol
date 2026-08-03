# WF-02 — Formulario de Alta/Edición

Patrón de formulario en pantalla completa (DOC-08 §6.2, FR-002/FR-009/FR-024).

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs                                                    │
│ Título / Estado                         [Volver] [Guardar]     │
├──────────────────────────────────────────────────────────────┤
│ Sección 1 — Identificación                                   │
│ [Campo] [Campo] [Campo]                                      │
│ Sección 2 — Datos fiscales                                   │
│ [Campo] [Búsqueda asíncrona]                                 │
│ Sección 3 — Adjuntos / Auditoría                             │
├──────────────────────────────────────────────────────────────┤
│ Barra sticky: cambios pendientes        [Cancelar] [Guardar]  │
└──────────────────────────────────────────────────────────────┘
```

Reglas: URL propia; H1; validación inline con foco al primer error; mensaje "Campo obligatorio"; inputs numéricos vacíos (no cero); IDs como texto; guard de cambios sin guardar; botón con loader y texto "Guardando…".
