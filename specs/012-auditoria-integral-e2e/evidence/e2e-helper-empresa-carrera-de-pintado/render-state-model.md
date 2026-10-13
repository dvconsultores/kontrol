# Estados de render de la pantalla de empresas (producto, sin cambios)

Fuentes: `src/pages/EmpresasPage.tsx` (DataTable con `loading={query.isLoading}`, `error`, filas con controles por fila),
`src/components/DataTable.tsx`, `src/components/LoadingState.tsx`, `src/components/company/EstadoDeEmpresa.tsx` (compuerta),
`src/app/contexts/CompanyContext.tsx` (estados `AUTH_LOADING`, `COMPANY_LOADING`, `ERROR`, `NO_COMPANIES`,
`COMPANY_SELECTION_REQUIRED`, listo).

| Estado | Señal estable en el DOM (sin test-id nuevo) | Controles de decisión |
|---|---|---|
| LOADING (tabla) | `LoadingState`: `role="status"` + `aria-live="polite"` («Cargando…») | ninguno |
| LOADING (contexto) | `LoadingState` «Cargando empresas…» (`role="status"`) | ninguno |
| ERROR | `role="alert"` («No fue posible cargar las empresas.» / «No se pudieron cargar las empresas») | ninguno |
| EMPTY | `EmptyState` «No hay registros» | ninguno |
| ROWS_RENDERED | `role="region"` con `aria-label="Resultados: N registros"` y `<table>` | por fila |
| ACTIVE_ROW | botón «Activa» (`disabled`, `title="Empresa activa"`) + botón «Desactivar» en la fila de la empresa activa | `Activa` + `Desactivar` |
| INACTIVE_ROW | botón «Activar» en cada fila no activa | `Activar` |
| GATE (`COMPANY_SELECTION_REQUIRED`) | `<h1>` «Seleccione una empresa» + botones `data-testid="elegir-empresa-<código>"` (sustituye a la tabla) | `elegir-empresa-*` |
| NO_COMPANIES | «No tiene empresas asignadas» | ninguno |
| UNKNOWN | — | **0** |

`DATA_RENDER_COMPLETE` para el ayudante = **aparece exactamente un control de decisión** (o la pareja `Activa`+`Desactivar`):
son los controles exactos que el producto ya pinta; no hace falta leer `role="status"` para decidir (se incluye solo en el
diagnóstico). `UNKNOWN = 0`. Ningún cambio de producto requerido.
