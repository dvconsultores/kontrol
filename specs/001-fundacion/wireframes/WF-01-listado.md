# WF-01 — Listado

Patrón base de listado (DOC-08 §6.1). Aplica a: empresas, sucursales, establecimientos, almacenes, usuarios, roles, auditoría.

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs                                                    │
│ Título                                      [Acción primaria]  │
│ Descripción breve                                              │
├──────────────────────────────────────────────────────────────┤
│ [Buscar en esta pantalla................] [Estado ▼]          │
├──────────────────────────────────────────────────────────────┤
│ Tabla sin scroll horizontal                     N registros   │
│ ┌────────────────────────────────────────────┬──────────────┐ │
│ │ Columnas prioritarias (ID, nombre, estado) │ Acciones (→) │ │
│ └────────────────────────────────────────────┴──────────────┘ │
├──────────────────────────────────────────────────────────────┤
│ Paginación solo si total > 10                                  │
└──────────────────────────────────────────────────────────────┘
```

Reglas: sin scroll horizontal; búsqueda general; filtro Todos/Activos/Inactivos; paginación >10; acciones a la derecha icon-only con tooltip y aria-label; estados loading/empty/error/forbidden/not-found; mobile → tarjetas.
