# RESEARCH — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de datos / Arquitecto de software |
| Ruta | `specs/002-maestros/research.md` |

## 1. Decisiones investigadas

### 1.1 Atributos configurables: EAV libre vs. esquema gobernado

| Aspecto | Detalle |
|---|---|
| Problema | El catálogo debe ser multirrubro sin una tabla nueva por actividad, pero sin JSON/EAV libre para datos críticos |
| Opciones | (a) EAV libre; (b) JSON genérico; (c) **atributos gobernados** (`AttributeDefinition/Applicability/Value`) |
| Decisión | **(c) Atributos gobernados** con tipo, unidad, opciones, validación, buscable, permisos. JSON solo como snapshot. Inventario/impuestos/lotes/seriales/regulación nunca en EAV |
| Fuente | DOC-01 §8; DOC-03 §4; DOC-02 §5 |
| Estado | Decidido (CL-002-01) |

### 1.2 Modelo de terceros

| Aspecto | Detalle |
|---|---|
| Problema | Cliente/proveedor/vendedor/etc. comparten RIF, direcciones, contactos y cuentas |
| Opciones | (a) Tablas separadas por rol; (b) **`Party` común + extensiones por rol** |
| Decisión | **(b)** `Party` + `Customer/Supplier/Carrier/Driver` como extensiones; duplicidad de RIF controlada por empresa/rol |
| Fuente | DOC-03 §3; DOC-02 §4 |
| Estado | Decidido (CL-002-04) |

### 1.3 Taxonomía jerárquica

| Aspecto | Detalle |
|---|---|
| Problema | Sector → rubro → categoría → familia → línea → tipo configurable |
| Opciones | (a) Tabla de árbol genérica (`TaxonomyNode` con padre); (b) tablas fijas por nivel |
| Decisión | **(a) Tabla de árbol jerárquico** con `parent`, `applies_to`, ámbito empresa/global y estado; `clasificación` versionada |
| Fuente | DOC-03 §4 |
| Estado | Decidido (CL-002-03) |

### 1.4 Perfiles versionados

| Aspecto | Detalle |
|---|---|
| Problema | Perfiles de inventario/trazabilidad/fiscal/regulatorio reutilizables y con vigencia |
| Opciones | (a) Campos en el producto; (b) **tablas de perfil versionadas** referenciadas por el ítem |
| Decisión | **(b)** Perfiles versionados (inicio/fin, estado, aprobación) reutilizables por rubro/plantilla/producto |
| Fuente | DOC-02 §5; DOC-03 §4 |
| Estado | Decidido |

### 1.5 Búsqueda de catálogos grandes

| Aspecto | Detalle |
|---|---|
| Problema | Clientes/proveedores/productos pueden superar 10k registros |
| Opciones | (a) Descarga completa; (b) **búsqueda asíncrona backend** (debounce 300-500 ms, paginación, cancelación) |
| Decisión | **(b)** `AsyncCombobox` con búsqueda backend; índices por empresa/estado/código/nombre normalizado/barcode/atributos buscables |
| Fuente | DOC-08 §9.2, §17; DOC-05 §7 |
| Estado | Decidido |

### 1.6 Producto vs. servicio

| Aspecto | Detalle |
|---|---|
| Problema | Comportamientos distintos (inventario vs. facturación de servicio) |
| Opciones | (a) Una sola tabla con flags; (b) **`CatalogItem` base + `Product`/`Service` especializados** |
| Decisión | **(b)** Entidad base compartida y especialización separada; el servicio no usa lote/serial/almacén |
| Fuente | DOC-01 §8; DOC-03 §4 |
| Estado | Decidido (CL-002-05) |

## 2. Reutilización de la fundación

- Reutiliza de 001: multiempresa, RBAC + `allowed_actions`, auditoría, idempotencia, contrato de errores, sistema de diseño/componentes, patrones WF-01/02/03/06.
- No crea CRUD genérico que oculte reglas críticas (Constitución): los componentes compartidos solo se usan con semántica realmente común.

## 3. Estado de aprobación

| Elemento | Estado |
|---|---|
| Decisiones técnicas | ✔ |
| Reutilización de 001 | ✔ |
| Aprobación | Pendiente |
