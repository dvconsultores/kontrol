# FUNDACIÓN DE FRONTEND — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto frontend / UI/UX |
| Ruta | `specs/001-fundacion/frontend-foundation.md` |
| Fuente | DOC-08 (obligatorio) |

## 1. Stack

React 19 + TypeScript estricto + Vite (8.x propuesto) + Tailwind 4 + React Router + TanStack Query + React Hook Form + Zod + TanStack Table + Lucide + Vitest + RTL + Playwright + axe.

## 2. Sistema de diseño (antes de módulos)

- Tokens: color (brand, surface, background, border, text, muted, success, warning, danger, info, focus, disabled), tipografía Ubuntu (light/regular/medium/bold + escala), espaciado 4px (4..48), radios (small/medium/large), sombras, z-index, tamaños, breakpoints (mobile/tablet/laptop/desktop/wide).
- Iconografía: Lucide React única; acciones con tooltip y aria-label; sin emojis funcionales.
- Documentación de componentes (catálogo/Storybook).
- Sin estilos aislados por módulo sin ADR.

## 3. App Shell y navegación

- Sidebar colapsable (una rama expandida; opción activa visible).
- Topbar (empresa activa, sucursal/establecimiento, usuario, fecha confiable, licencia, salida).
- Breadcrumbs obligatorios en páginas de segundo nivel.
- Un H1 por ruta; URL propia para cada lista/alta/edición/detalle/proceso.
- Estado de lista conservado al regresar (búsqueda, página, orden, filtro).
- Rutas resuelven loading/ready/not-found/forbidden/error.
- Scroll al inicio y foco al H1 al navegar; guard de cambios sin guardar.

## 4. Patrones de pantalla

WF-01 Listado · WF-02 Formulario · WF-03 Detalle · WF-04 Documento · WF-05 Matriz · WF-06 Asistente · WF-07 Dashboard · WF-08 Reporte · WF-09 Solo consulta (ver `wireframes/`).

## 5. Política de modales (ADR-015)

- No modales para crear/editar, matrices, DataTables, configuraciones, documentos, permisos ni procesos complejos.
- Modales solo para confirmación breve (desactivar, eliminar, anular, reversar, descartar, alertas).
- Diálogos con portal, focus trap, Escape, restauración de foco, loader dentro de Confirmar.

## 6. Botones y acciones asíncronas

- Loader dentro del botón + texto de progreso; deshabilitado; prevención de doble envío; idempotencia.
- Éxito/error persistentes (sin auto-dismiss en operaciones importantes).
- Notificaciones con título, descripción, icono, cerrar, `aria-live`; sin duplicados; sin stack traces/SQL.

## 7. Formularios

- Label visible; requerido con indicador; error con borde rojo, texto, `aria-invalid`, `aria-describedby`; foco al primer error; resumen accesible.
- Inputs numéricos vacíos (no cero); decimales para dinero; IDs como texto.
- Catálogos grandes con búsqueda asíncrona (debounce 300-500ms, backend, paginación, cancelación).
- Monedas: etiquetas neutrales, indicador dinámico; sin hardcodear Bs/VES/USD.
- Fechas: zona horaria controlada; servidor como autoridad.

## 8. DataTables

- Sin scroll horizontal; prioridad de columnas; detalle expandible; tarjetas en móvil.
- Búsqueda general; filtro Todos/Activos/Inactivos; paginación >10; acciones a la derecha icon-only; loading/empty/error.

## 9. Estados y errores

- Loading (skeleton), Empty, NoResults, Error recuperable, Forbidden, NotFound, Offline/API unavailable, ReadOnly.
- Manejo de 400/401/403/404/409/422/423/429/5xx; 401 refresh único; 409 conflicto; 423 licencia.

## 10. Estado y caché

- TanStack Query con keys por dominio/empresa; invalidación selectiva; sin optimistic update en emisión/pagos/movimientos/licencia.
- Context global solo para auth, empresa activa, licencia, tema, notificaciones.
- LocalStorage solo para preferencias no sensibles; nunca tokens.

## 11. Seguridad, permisos y licencia

- `allowed_actions` del backend; rutas validan permiso antes de cargar datos.
- Contexto de licencia (FULL_ACCESS/RENEWAL_NOTICE/CRITICAL_RENEWAL_NOTICE/READ_ONLY); banner y bloqueo con enlace a Mi licencia.

## 12. Componentes obligatorios (DOC-08 §20)

Layout: AppShell, Sidebar, Topbar, PageLayout, PageHeader, PageContent, Breadcrumbs, PageActions.
Feedback: PersistentNotification, InlineAlert, ErrorSummary, LoadingButton, ProgressIndicator.
Estados: RouteLoader, EmptyState, NoResultsState, ErrorState, ForbiddenState, NotFoundState.
Formularios: FormField, TextField, NumberField, MoneyField, PercentageField, DateField, AsyncCombobox, FileUploader.
Tablas: DataTable, TableToolbar, GeneralSearch, StatusFilter, Pagination, RowActions, MobileCards.
Acciones: ActivateAction, DeactivateAction, DeleteAction, ConfirmDialog, UnsavedChangesGuard.
Seguridad: PermissionGate, LicenseGate, AllowedActions, SensitiveField.
Documentos: DocumentHeader, LineItemsEditor, TotalsPanel, AuditTimeline, AttachmentsPanel.
Reportes: ReportParameters, ReportStatus, ReportDownload, ExportAction.
Utilidades: Tooltip, Popover, Drawer, Badge, StatusBadge, Skeleton.

Cada componente: API documentada, variantes limitadas, estados, pruebas de teclado/accesibilidad, sin reglas de negocio de módulo.

## 13. Estado

| Elemento | Estado |
|---|---|
| Fundación de frontend | ✔ (especificado) |
| Aprobación | Pendiente |
