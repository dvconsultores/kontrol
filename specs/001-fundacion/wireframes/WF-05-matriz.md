# WF-05 — Matriz

Patrón para matrices (roles/permisos, alcances). Nunca en modal (DOC-08 §7).

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Título                    [Acciones]            │
├──────────────────────────────────────────────────────────────┤
│ Contexto (empresa/sucursal) + grupos                        │
├──────────────────────────────────────────────────────────────┤
│ ┌──────────┬─────────┬─────────┬─────────┐                    │
│ │ Recurso  │ Ver     │ Crear   │ Editar  │ ...  (columnas)    │
│ ├──────────┼─────────┼─────────┼─────────┤                    │
│ │ Clientes │ [x]     │ [x]     │ [ ]     │                    │
│ └──────────┴─────────┴─────────┴─────────┘                    │
├──────────────────────────────────────────────────────────────┤
│ Barra sticky de acciones                                      │
└──────────────────────────────────────────────────────────────┘
```

Reglas: compacta, acciones sticky, sin scroll horizontal, matriz responsive por secciones en tablet/móvil.
