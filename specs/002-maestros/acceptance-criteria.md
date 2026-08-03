# CRITERIOS DE ACEPTACIÓN — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Ruta | `specs/002-maestros/acceptance-criteria.md` |

## Criterios globales

| ID | Criterio | Verificación |
|---|---|---|
| AC-002-001 | Un tercero tiene múltiples roles sin duplicar RIF/direcciones/contactos | Test Party + E2E |
| AC-002-002 | El catálogo se adapta a un sector nuevo sin migración | Test de taxonomía/atributos |
| AC-002-003 | Producto y servicio con comportamientos separados; el servicio no toca inventario | Test de especialización + E2E |
| AC-002-004 | Perfiles versionados y reutilizables | Test de versiones |
| AC-002-005 | Listados cumplen el estándar frontend (sin scroll horizontal, búsqueda asíncrona, paginación >10, `allowed_actions`) | E2E + axe |
| AC-002-006 | Desactivar conserva historia; eliminar solo sin relaciones | Test de acciones |
| AC-002-007 | Aislamiento multiempresa probado con pruebas negativas | Pytest negativo |
| AC-002-008 | Cada requisito tiene identificador, fuente, dueño, criterio y prueba | Trazabilidad |
| AC-002-009 | No se hardcodean rubros, monedas ni reglas fiscales | Revisión de código |

## Criterios por historia (US)

| Historia | Criterio |
|---|---|
| US-002-001 | Se crea un tercero con rol cliente+proveedor; el RIF se reutiliza, no se duplica |
| US-002-002 | Se crea un rubro y sus atributos; el producto lo usa sin migración |
| US-002-003 | El proveedor tiene perfil fiscal y retenciones; no se paga sin aprobación |
| US-002-004 | El producto con lote/vencimiento registra su perfil de inventario |
| US-002-005 | El servicio se registra sin lote/serial/almacén y con unidad de facturación |
| US-002-006 | El perfil fiscal se versiona y se reutiliza en terceros/productos |
| US-002-007 | El asistente de producto valida por paso y permite guardar borrador |
| US-002-008 | El detalle de producto muestra inventario, fiscal, regulatorio e historial |
| US-002-009 | Desactivar conserva historia; eliminar solo sin relaciones |
| US-002-010 | La búsqueda por RIF/nombre/código responde desde backend |
| US-002-011 | El proveedor no aprobado no puede pagarse |
| US-002-012 | La auditoría del maestro muestra quién, cuándo y qué cambió |
| US-002-013 | Se definen unidades y conversiones válidas |
| US-002-014 | Se registran presentaciones y códigos de barras únicos |
| US-002-015 | El servicio refiere un concepto ISLR, no un porcentaje fijo |

## Criterios de la fase documental

| ID | Criterio | Estado |
|---|---|---|
| AC-002-DOC-001 | Spec 002 completa | ✔ |
| AC-002-DOC-002 | Ambigüedades resueltas o bloqueadas | ✔ (pendientes registrados) |
| AC-002-DOC-003 | Plan pasa la Constitución | ✔ |
| AC-002-DOC-004 | Modelo de datos documentado | ✔ |
| AC-002-DOC-005 | Tareas atómicas y trazadas | ✔ |
| AC-002-DOC-006 | `/speckit.analyze` sin contradicciones bloqueantes | Pendiente — se ejecuta en `analysis-report.md` |
| AC-002-DOC-007 | Autorización solicitada antes de implementar | ✔ (punto de detención) |
