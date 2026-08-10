# Spec 012 — Matriz de Completitud Funcional

Regla: COMPLETE = Requirement AND Route AND Page AND API AND Backend AND DB AND Permission AND Audit AND Tests AND E2E.
Si un elemento obligatorio falta → NO COMPLETE.

## Procesos críticos

| Dominio | Función | Req | Menú | Ruta | UI | API | DB | Permisos | E2E | Estado |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Org | Empresa: listar/activar | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** |
| Org | Sucursal: crear/consultar | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** (F-0 resuelto) |
| Org | Almacén: crear/consultar | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** |
| Org | **Establecimiento** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** (T-03) |
| Org | Ubicación | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** (T-04) |
| Seguridad | **Usuarios** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** (T-01) |
| Seguridad | **Roles/Permisos** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** (T-02) |
| Maestros | Terceros: listar/ver | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** |
| Maestros | Productos/Servicios/Catálogo | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** |
| Maestros | Perfiles fiscales | ✔ | ✖ | ✖ | ✖ | ✔ | ✔ | ✔ | ✖ | **PARTIAL** |
| Ventas | Cotización→Orden→Factura→CxC | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** (sin E2E integral) |
| Compras | Requisición→Orden→Recepción→Factura→CxP | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** |
| Inventario | Existencias/Kardex/Transferencias/Conteos/Ajustes | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** (movements API sin UI) |
| Tesorería | Cajas/IE/Transf/Conciliación/IGTF | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** |
| Fiscal | Configuración/Numeración/Emisión/Notas/Retenciones/Libros | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** (validación fiscal pendiente) |
| Regulatorio | Organismos/Vehículos/Permisos/Evaluación | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** |
| Reportes | Centro/Exportaciones/Auditoría | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** |
| Licencia | Estado/Config central/Sync/Renovación/Eventos | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **COMPLETE** |
| Homologación | Actos/Versiones/Timeline | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ⚠ | **PARTIAL** |

Leyenda: ✔ = verificado en esta pasada · ✖ = ausente · ⚠ = presente pero sin E2E/evidencia de proceso completo.

## Resultado agregado

- **COMPLETE**: 7 cadenas (Empresa, Sucursal, Almacén, Terceros, Maestros, Licencia).
- **PARTIAL / BROKEN**: el resto. Dos **BROKEN** (Usuarios, Roles) y dos **PARTIAL** estructurales (Establecimiento, Ubicación).
- Conclusión: **NO-GO** para certificación fiscal bajo la definición estricta del Spec (existen HIGH y procesos no 100%).
