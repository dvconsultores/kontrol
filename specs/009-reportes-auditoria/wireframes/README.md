# WIREFRAMES — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/wireframes/README.md` |

> Aplicación de las guías DOC-08. Grids sin scroll horizontal (FR-009-101).

## 1. Dashboard (Inicio)

- Tarjetas de indicadores por módulo: ventas (total/base/impuestos), compras, tesorería (caja/banco), fiscal (emisiones) y regulatorio (despachos bloqueados).
- Vencimientos: CxC/CxC, períodos fiscales, permisos.
- Alertas y tareas pendientes.

## 2. Centro de reportes

- Pestañas por categoría: Ejecutivos · Operativos · Financieros · Fiscales · Regulatorios.
- Filtros comunes: período, moneda, estado, categoría.
- Tabla de resultados + botones **Exportar CSV / PDF** (genera `report_exports`).
- Reportes fiscales enlazan a los libros de 007.

## 3. Exportaciones auditadas

- Histórico: `report_key | formato | exportado por | fecha | filtros`.

## 4. Trabajos asíncronos

- Lista de jobs con estado (PENDING/RUNNING/DONE/FAILED) y error.

## 5. Auditoría (timeline)

- Línea de tiempo de eventos `AuditEvent`: cambios, impresiones, exportaciones, accesos, incidentes; filtros por entidad/acción/usuario/fecha.

## 6. Navegación

- Sidebar (lucide-react): `Inicio` (dashboard) y `Reportes` → Centro de reportes · Exportaciones · Trabajos · Auditoría.
- Rutas: `/`, `/reportes/centro`, `/reportes/exportaciones`, `/reportes/trabajos`, `/reportes/auditoria`.
