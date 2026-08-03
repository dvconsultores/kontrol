# SPEC — 002-MAESTROS

| Campo | Valor |
|---|---|
| Código | 002-maestros |
| Nombre | Maestros: terceros, productos, servicios, rubros, unidades y perfiles |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** (org/seguridad/licencia/auditoría). La implementación de 002 requiere 001 certificada y autorización expresa |
| Fuente | DOC-01 §7-8; DOC-02 §4-5; DOC-03 §3-4; DOC-04 (pantallas 02-08); DOC-06 §3; DOC-08 |
| Ruta | `specs/002-maestros/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **002-maestros**.

---

## 1. Problema

La fundación deja la estructura de organización y seguridad. Para operar el negocio se requieren los **datos maestros** que alimentan los módulos operativos (compras, ventas, inventario, tesorería, fiscal): terceros, productos, servicios, taxonomía configurable (sectores/rubros/categorías), unidades y perfiles (fiscal, inventario, regulatorio).

El catálogo debe ser **multirrubro** (alimentos, medicamentos, celulares, textiles, etc.) sin desarrollar una tabla nueva por actividad; los comportamientos se implementan mediante **perfiles y extensiones estructuradas**, no con JSON/EAV libre para datos críticos.

## 2. Objetivos

1. Entidad común **Tercero (Party)** con extensiones por rol (cliente, proveedor, vendedor, transportista, conductor, beneficiario) sin duplicidad de RIF/direcciones/contactos/cuentas.
2. Taxonomía jerárquica configurable (sector → rubro → categoría → familia → línea → tipo) con estado y ámbito (empresa/global).
3. Atributos configurables **gobernados** (tipo, unidad, obligatoriedad, opciones, validación, búsqueda, permisos, orden).
4. **Producto y servicio** comparten entidad comercial base, con especialización funcional separada.
5. Unidades de medida, conversiones, presentaciones y códigos de barras.
6. Perfiles **versionados** (inventario, trazabilidad, fiscal, regulatorio) reutilizables.
7. Frontend con pantallas completas (asistente de producto, formularios de tercero) sin modales (ADR-015), DataTable sin scroll (FR-016) y catálogos grandes con búsqueda asíncrona.

## 3. Fuera de alcance

- Procesos transaccionales (compras, ventas, inventario, tesorería, fiscal, CxC/CxP) — Specs posteriores.
- Emisión fiscal real y cálculo de impuestos (solo perfiles/reglas de referencia).
- Migración de datos de INNOVA.
- Reportes de maestros (Spec 009).
- Regulación SICA/SIGESAI funcional (solo perfil regulatorio de referencia) — Spec 008.

## 4. Actores

| Actor | Uso |
|---|---|
| Administrador de empresa | Crea/configura maestros, taxonomía, plantillas y atributos |
| Compras | Registra proveedores y perfiles de compra |
| Ventas | Registra clientes y perfiles de venta/crédito |
| Contador / fiscal | Asigna perfiles fiscales y retenciones a terceros/productos |
| Almacén | Configura perfiles de inventario/trazabilidad |
| Logística | Configura perfil regulatorio de productos |
| Auditor | Consulta historial y auditoría de maestros |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-002-001 | Como administrador, quiero registrar un tercero con rol de cliente y proveedor para reutilizar datos sin duplicar el RIF. |
| US-002-002 | Como usuario de catálogo, quiero crear rubros y atributos configurables para adaptarme a mi sector sin código. |
| US-002-003 | Como comprador, quiero registrar un proveedor con perfil fiscal y retenciones para pagarle correctamente. |
| US-002-004 | Como usuario de catálogo, quiero registrar un producto con lote/vencimiento para controlar inventario. |
| US-002-005 | Como usuario de catálogo, quiero registrar un servicio con unidad de facturación sin afectar inventario. |
| US-002-006 | Como contador, quiero asignar perfiles fiscales versionados a terceros y productos. |
| US-002-007 | Como usuario de catálogo, quiero crear un producto mediante un asistente paso a paso para no omitir datos. |
| US-002-008 | Como usuario de catálogo, quiero ver el detalle completo de un producto (inventario, fiscal, regulatorio, historia). |
| US-002-009 | Como administrador, quiero desactivar un maestro conservando su historia para no romper documentos. |
| US-002-010 | Como usuario, quiero buscar un cliente/proveedor por RIF, nombre o código en un catálogo grande. |
| US-002-011 | Como comprador, quiero aprobar un proveedor (bancaria/fiscal) antes de poder pagarle. |
| US-002-012 | Como auditor, quiero consultar la auditoría de un maestro (quién, cuándo, cambios). |
| US-002-013 | Como administrador, quiero definir unidades de medida y conversiones para estandarizar el catálogo. |
| US-002-014 | Como usuario, quiero registrar presentaciones y códigos de barras de un producto. |
| US-002-015 | Como usuario de catálogo, quiero registrar un servicio profesional con concepto ISLR de referencia (no porcentaje fijo). |

## 6. Requisitos funcionales

Convención: `FR-002-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Terceros (Party)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-002-001 | Entidad `Party` común (identificación, tipo de persona, nacionalidad/residencia, razón social, RIF, actividad, estado) con extensiones por rol. | DOC-03 §3 | P0 | Administrador |
| FR-002-002 | Control de duplicidad de RIF por empresa/rol; validación de formato de RIF. | DOC-03 §12 | P0 | Sistema |
| FR-002-003 | Direcciones, contactos y cuentas bancarias asociadas con validez y tipo (fiscal/delivery). | DOC-03 §3 | P1 | Sistema |
| FR-002-004 | Extensión `Customer`: lista de precios, vendedor, zona, condición, días/límite de crédito, bloqueo, perfil fiscal, retenciones sufridas. | DOC-03 §3 | P1 | Ventas |
| FR-002-005 | Extensión `Supplier`: categoría, comprador, condición de pago, moneda, estado de aprobación (bancaria/fiscal) y perfil de retenciones. | DOC-03 §3 | P0 | Compras |
| FR-002-006 | Extensión `Carrier` y `Driver`: registro, seguros, permisos, licencia, vigencias y restricciones. | DOC-03 §3 | P2 | Logística |
| FR-002-007 | Los RIF, cédulas, teléfonos, cuentas y códigos se tratan como **texto** (ceros iniciales conservados). | DOC-08 FR-013 | P0 | Sistema |

### 6.2 Taxonomía y atributos configurables

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-002-010 | Árbol jerárquico configurable (sector/rubro/categoría/familia/línea/tipo) con ámbito empresa/global, código, nombre, estado y `applies_to`. | DOC-03 §4 | P0 | Administrador |
| FR-002-011 | `AttributeDefinition`: código, tipo de dato, unidad, obligatoriedad, múltiple, opciones, validación, buscable, permisos. | DOC-03 §4 | P0 | Administrador |
| FR-002-012 | `AttributeApplicability` por rubro/categoría/plantilla: condición, orden y sección. | DOC-03 §4 | P1 | Administrador |
| FR-002-013 | `AttributeValue` tipado con validez; índices para atributos buscables. | DOC-03 §4 | P1 | Sistema |
| FR-002-014 | Un rubro ordinario se crea **sin migración de base de datos**; agregar comportamiento funcional nuevo requiere Spec. | DOC-01 §8 | P0 | Sistema |
| FR-002-015 | **Prohibido** EAV/JSON libre para datos críticos (inventario, impuestos, lotes, seriales, regulación). | DOC-01 §8 | P0 | Sistema |

### 6.3 Productos y servicios

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-002-020 | `CatalogItem` base (tipo PRODUCT/SERVICE, código, nombre, descripción, categoría, unidad base, perfil fiscal, estado). | DOC-03 §4 | P0 | Sistema |
| FR-002-021 | `Product`: plantilla, perfiles (inventario/trazabilidad/regulatorio), fabricante, país de origen. | DOC-03 §4 | P0 | Almacén |
| FR-002-022 | `Service`: plantilla, unidad de facturación, duración, recurrencia, modalidad, contrato, evidencia. No muestra lote/serial/almacén. | DOC-03 §4, DOC-04 | P0 | Usuario |
| FR-002-023 | Producto y servicio comparten entidad base pero con comportamientos separados; la línea de factura puede incluir ambos (sin afectar inventario del servicio). | DOC-01 §8 | P0 | Sistema |
| FR-002-024 | Plantillas de producto/servicio versionadas (inventario, lote, serial, vencimiento, variantes, garantía, decimales). | DOC-03 §4 | P1 | Administrador |
| FR-002-025 | Presentaciones (unidad, contenido, códigos de barras) y variantes de producto. | DOC-03 §4 | P1 | Usuario |

### 6.4 Unidades y perfiles

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-002-030 | `UnitOfMeasure` (dimensión, código, símbolo, decimales, estado) y `UnitConversion` (factor, redondeo, vigencia). | DOC-03 §4 | P1 | Administrador |
| FR-002-031 | Perfiles **versionados** y reutilizables: inventario, trazabilidad, fiscal y regulatorio. | DOC-02 §5, DOC-03 §4 | P0 | Sistema |
| FR-002-032 | El concepto ISLR en servicios es **referencia a regla**, no porcentaje fijo hardcodeado. | DOC-04 | P0 | Contador |
| FR-002-033 | No hardcodear rubros, categorías, monedas ni reglas de negocio (Constitución P8). | DOC-01 | P0 | Sistema |

### 6.5 Operación y UX

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-002-040 | Asistente de producto en pantalla completa (pasos + validación + resumen); guardar borrador y reanudar. | DOC-04 pantalla 03 | P0 | Usuario |
| FR-002-041 | Detalle de producto con resumen de inventario, fiscal y regulatorio, historial y auditoría. | DOC-04 pantalla 04 | P0 | Usuario |
| FR-002-042 | Listados con búsqueda general (RIF/nombre/código), filtro de estado, paginación >10, sin scroll horizontal, acciones a la derecha. | DOC-08 | P0 | Sistema |
| FR-002-043 | Catálogos grandes con **búsqueda asíncrona** (debounce, backend, paginación, cancelación, estados). | DOC-08 §9.2 | P0 | Sistema |
| FR-002-044 | Desactivar/activar conserva historia; eliminar solo sin relaciones (`can_delete`). | DOC-08 §12 | P0 | Sistema |
| FR-002-045 | Auditoría accesible por entidad (timeline con Request ID). | DOC-01 | P0 | Auditor |

## 7. Requisitos no funcionales

- Hereda los NFR de `001-fundacion` (NFR-001-*): seguridad, rendimiento, accesibilidad WCAG 2.2 AA, responsive, observabilidad, multiempresa, auditoría.
- **Aislamiento multiempresa:** todos los maestros pertenecen a una empresa; pruebas de aislamiento negativo.
- **Rendimiento:** listados de catálogos grandes <2 s p95; búsquedas asíncronas sin bloquear escritura.
- **Concurrencia:** versión/ETag en edición de maestros; 409 sin sobrescritura silenciosa.
- **Decimal exacto** para cantidades/precios en presentaciones.
- **Snapshot:** el detalle y los documentos futuros conservan el snapshot del maestro aplicado.

## 8. Casos límite

| ID | Caso límite | Comportamiento esperado |
|---|---|---|
| EDGE-002-01 | RIF duplicado en el mismo rol | 409 `DUPLICATE_ENTITY` con mensaje claro |
| EDGE-002-02 | Tercero con rol activo en documentos | Bloqueo de desactivación/eliminación; estado conservado |
| EDGE-002-03 | Producto con lote pero sin vencimiento | Validación por perfil de inventario |
| EDGE-002-04 | Servicio con perfil de inventario | Rechazo: los servicios no usan lote/serial/almacén |
| EDGE-002-05 | Atributo requerido faltante | Foco al primer error + "Campo obligatorio" |
| EDGE-002-06 | Rubro en uso por productos | No eliminar; solo desactivar con confirmación |
| EDGE-002-07 | Conversión de unidades inválida (factor 0/negativo) | Rechazo por validación |
| EDGE-002-08 | Código de barras duplicado | Unique por empresa/plantilla |
| EDGE-002-09 | Edición concurrente de un maestro | 409 + versión/ETag |
| EDGE-002-10 | Catálogo grande (>10k) | Búsqueda backend paginada, sin descargar todo |
| EDGE-002-11 | Proveedor sin aprobación bancaria intentando pago | Bloqueado (estado de aprobación) |
| EDGE-002-12 | Cambio de perfil fiscal de un tercero con documentos | Versionado; no altera documentos históricos |
| EDGE-002-13 | Acceso a maestro de otra empresa | 403 / aislamiento negativo |

## 9. Criterios de aceptación

- Un tercero puede tener múltiples roles sin duplicar RIF/direcciones/contactos.
- El catálogo se adapta a un sector nuevo sin migración (rubros/atributos configurables).
- Productos y servicios se registran con comportamientos separados; el servicio no toca inventario.
- Los perfiles (fiscal/inventario/regulatorio) son versionados y reutilizables.
- Los listados cumplen el estándar frontend (sin scroll horizontal, búsqueda asíncrona, paginación >10, `allowed_actions`).
- Desactivar conserva historia; eliminar solo sin relaciones.
- Aislamiento multiempresa probado con pruebas negativas.
- Cada requisito tiene identificador, fuente, dueño, criterio y prueba (trazabilidad).
- No se hardcodean rubros, monedas ni reglas fiscales.

---

## 10. Documentos fuente

| Ref | Documento |
|---|---|
| DOC-01 | Documento Maestro de Requerimientos (§7-8) |
| DOC-02 | Arquitectura Funcional (§4-5) |
| DOC-03 | Modelo de Datos (§3-4, §12) |
| DOC-04 | Wireframes (pantallas 02-08) |
| DOC-06 | Spec Kit (estructura de iniciativas) |
| DOC-08 | Estándar Maestro de Frontend |

## 11. Estado

| Elemento | Estado |
|---|---|
| Identificación | ✔ |
| Historias y requisitos | ✔ |
| Casos límite y criterios | ✔ |
| Aprobación | Pendiente — requiere `/speckit.analyze` y autorización expresa **002-maestros** |
