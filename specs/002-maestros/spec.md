# SPEC — 002-MAESTROS (BORRADOR DE PROPUESTA)

| Campo | Valor |
|---|---|
| Código | 002-maestros |
| Nombre | Maestros: terceros, productos, servicios, rubros, unidades y perfiles |
| Versión | 0.1 (DRAFT — propuesta para `/speckit.specify`) |
| Estado | DRAFT — no aprobada; NO implementar sin flujo completo y autorización expresa |
| Fecha | 2026-08-04 |
| Dependencia | **001-fundacion** (debe estar certificada: CI verde, Docker validado, revisión legal T-048) |
| Fuente | DOC-06 §3; DOC-02 §3-5; DOC-03 §3-4; DOC-01 §7-8 |
| Ruta | `specs/002-maestros/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa solo se implementa tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **002-maestros**.

## 1. Problema

La fundación deja la estructura de organización y seguridad. Para operar el negocio se requieren los **datos maestros** que alimentan los módulos operativos (compras, ventas, inventario, tesorería, fiscal): terceros, productos, servicios, taxonomía configurable (sectores/rubros/categorías), unidades y perfiles (fiscal, inventario, regulatorio).

## 2. Objetivos

- Entidad común **Tercero** con extensiones por rol (cliente, proveedor, vendedor, transportista, conductor, beneficiario) sin duplicidad de RIF/direcciones/contactos/cuentas.
- Catálogo **multirrubro** configurable: sector, rubro, categoría, familia, línea, tipo, plantillas y atributos **gobernados** (sin EAV libre para datos críticos).
- **Producto y servicio** comparten entidad comercial base, con comportamientos separados (inventario/fiscal/regulatorio versionados).
- Unidades de medida y conversiones; presentaciones y códigos de barras.
- Perfiles: inventario, trazabilidad, fiscal y regulatorio **versionados** y reutilizables.

## 3. Fuera de alcance

- Procesos transaccionales (compras, ventas, inventario, tesorería, fiscal) — Specs posteriores.
- Emisión fiscal real.
- Migración de datos de INNOVA.

## 4. Actores

- Administrador de empresa, Compras, Ventas, Contador/fiscal, Almacén, Logística, Auditor.

## 5. Historias de usuario (borrador)

| ID | Historia |
|---|---|
| US-002-001 | Como administrador, quiero registrar un tercero con rol de cliente y proveedor para reutilizar datos sin duplicar el RIF. |
| US-002-002 | Como usuario de catálogo, quiero crear rubros y atributos configurables para adaptarme a mi sector sin código. |
| US-002-003 | Como comprador, quiero registrar un proveedor con perfil fiscal y retenciones para pagarle correctamente. |
| US-002-004 | Como usuario de catálogo, quiero registrar un producto por lotes/vencimiento para controlar inventario. |
| US-002-005 | Como usuario de catálogo, quiero registrar un servicio con unidad de facturación sin afectar inventario. |
| US-002-006 | Como contador, quiero asignar perfiles fiscales versionados a terceros y productos. |

## 6. Requisitos funcionales (borrador)

| ID | Requisito | Fuente |
|---|---|---|
| FR-002-001 | Entidad `Party` común + extensiones por rol; validación y control de duplicidad de RIF por empresa. | DOC-03 §3 |
| FR-002-002 | Taxonomía jerárquica configurable (sector/rubro/categoría/familia/línea/tipo) con estado. | DOC-03 §4 |
| FR-002-003 | Atributos configurables con tipo, unidad, obligatoriedad, opciones, validación, búsqueda y permisos. | DOC-02 §5 |
| FR-002-004 | Producto y servicio con entidad base común y especialización funcional. | DOC-02 §5 |
| FR-002-005 | Perfiles versionados (inventario, trazabilidad, fiscal, regulatorio) reutilizables. | DOC-03 §4 |
| FR-002-006 | Unidades de medida, conversiones, presentaciones y códigos de barras. | DOC-03 §4 |
| FR-002-007 | Pantalla completa para asistentes de producto/servicio (WF-02/WF-06); sin modales (ADR-015). | DOC-04 |

## 7. Próximos pasos del flujo

1. `/speckit.specify` → completar historias, requisitos, casos límite y criterios.
2. `/speckit.clarify` → resolver EAV gobernado vs. plantillas, perfil de servicio, catálogos globales.
3. `/speckit.plan` + `data-model.md` → entidades de DOC-03 §3-4.
4. `/speckit.analyze` y autorización expresa **002-maestros** antes de implementar.

## 8. Estado

| Elemento | Estado |
|---|---|
| Propuesta creada | ✔ (borrador) |
| Flujo Spec Kit de 002 | Pendiente — requiere 001 certificada |
| Aprobación | ✖ No autorizada |
