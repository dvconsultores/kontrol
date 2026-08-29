# MATRIZ DE PANTALLAS → SPECS

78 rutas · 77 páginas · 72 ítems de menú. **0 menús sin ruta · 0 rutas sin página** (puertas G1-G4 vigentes).
El patrón Sucursales original está cerrado a nivel de navegación; sobrevive a nivel de **proceso**.

| Pantalla | Ruta | Spec | Estado |
|---|---|---|---|
| Login / Reset / Setup / Cambiar contraseña | `/login`, `/reset-password`, `/setup`, `/cambiar-contrasena` | 002 | ✔ |
| Dashboard | `/` | 049 | ◐ sin rotación ni tendencias |
| Mi licencia | `/mi-licencia` | 004 | ✔ |
| Empresas · Sucursales · Establecimientos · Almacenes · Ubicaciones | `/organizacion/*` | 007, 008 | ◐ sin nivel/posición |
| — Centros de costo | — | 007 | ✖ **sin pantalla** |
| — Unidades de negocio | — | 007 | ✖ **sin pantalla** |
| Terceros · Productos · Servicios · Catálogo · Atributos · Perfiles fiscales | `/maestros/*` | 009, 010, 011, 014 | ✔ |
| — Listas de precios · Descuentos · Comisiones · Zonas · Rutas · Condiciones | — | 012 | ✖ **rama sin pantallas** |
| Existencias · Kardex · Movimientos · Tipos de movimiento · Transferencias · Conteos · Ajustes · Lotes · Seriales · Reservas · Valorización | `/inventario/*` | 021-026 | ✔ maestro / ◐ proceso |
| — Put-away / asignación de ubicación | — | 022 | ✖ **sin pantalla** |
| Requisiciones · Cotizaciones · Órdenes · Recepciones · Facturas · Devoluciones · Notas · CxP | `/compras/*` | 015-017,019,027,028,036 | ✔ |
| — Importaciones / expediente | — | 018 | ✖ **sin pantalla** |
| — Incidencias de recepción | — | 020 | ✖ **sin pantalla** |
| Cotizaciones · Órdenes · Picking y despacho · Facturas · Notas · Devoluciones · CxC | `/ventas/*` | 029-037 | ◐ |
| — Bandeja de crédito | — | 030 | ✖ **sin pantalla** |
| — Cola y ruta de picking | — | 031 | ✖ **sin pantalla** |
| — Confirmación de pedido | — | 033 | ✖ **sin pantalla** |
| Cajas y arqueo · Ingresos y egresos · Transferencias · Conciliación · IGTF · Maestros | `/tesoreria/*` | 013, 038, 041 | ✔ |
| Configuración · Numeración · Emisión · Notas · Retenciones · Libros · Lotes de declaración | `/fiscal/*` | 014, 039-043 | ◐ |
| — Contingencia de facturación | — | 042 | ✖ **sin pantalla** |
| Organismos · Vehículos · Permisos y guías · Evaluación · Aprobaciones | `/regulatorio/*` | 044, 045 | ✔ |
| — Bandeja transversal de aprobaciones · Delegaciones | — | 045 | ✖ **sin pantalla** |
| Centro de reportes · Exportaciones · Auditoría | `/reportes/*` | 049, 050, 051 | ✔ |
| Configuración central · Entitlements · Renovación · Eventos | `/licenciamiento/*` | 004 | ✔ |
| Actos · Versiones · Timeline | `/homologacion/*` | 056 | ✔ |
| Usuarios · Roles · Sesiones | `/seguridad/*` | 002, 003 | ◐ |
| — Alcances · MFA | — | 003, 002 | ✖ **sin pantalla** |
| Auditoría · Diagnóstico | `/auditoria`, `/diagnostico` | 051, 006 | ◐ |
| — Configuración del sistema (correo, impresión, integraciones, storage, notificaciones, monitoreo, respaldos) | — | 047, 048, 052, 053 | ✖ **rama sin pantallas** |
| — Mis tareas · Mis aprobaciones · Alertas | — | 047 | ✖ **sin pantallas** |

## Recuento

| | Cantidad |
|---|---:|
| Pantallas existentes y funcionales | 77 |
| Pantallas exigidas por el requerimiento y **ausentes** | **18** |
| Ramas de menú del Vol. 2 sin ninguna pantalla | **3** (Comercial, Aprobaciones, Configuración del sistema) |

## Cumplimiento del estándar de pantalla (Vol. 2 §2)

| Criterio | Estado | Evidencia |
|---|---|---|
| URL propia para listar/crear/editar/consultar | ✔ | 78 rutas, sin modales de creación (ADR-015) |
| Breadcrumb, título, descripción, contexto de empresa | ✔ | `PageHeader`, `Breadcrumbs` |
| Estados Loading/Ready/Empty/Forbidden/NotFound/Error | ✔ | Componentes de estado compartidos |
| Formulario complejo en pantalla completa | ✔ | P18 respetado |
| DataTable sin scroll horizontal | ✔ | responsive 198/198, 0 scroll horizontal |
| Accesibilidad WCAG 2.2 AA | ✔ | axe 19/19 |
| Permisos en ruta, API y dominio | ◐ | `PermissionGuard` activo; alcances sin UI |
| **Protección de cambios sin guardar** | ✖ | No implementado |
