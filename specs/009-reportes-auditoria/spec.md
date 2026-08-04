# SPEC — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Código | 009-reportes-auditoria |
| Nombre | Reportes y auditoría: dashboard, reportes ejecutivos/operativos/financieros/fiscales/regulatorios, exportación auditada y trazabilidad |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** (AuditEvent, multiempresa) + **003-inventario** + **004-compras** + **005-ventas** + **006-tesoreria** + **007-nucleo-fiscal** (libros) + **008-regulacion**. La implementación requiere 001 certificada, 003-008 implementados, y autorización expresa |
| Fuente | DOC-01 §1, §4, §5; DOC-02 §4; DOC-03 §11; DOC-08 |
| Ruta | `specs/009-reportes-auditoria/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **009-reportes-auditoria**.

---

## 1. Problema

Los módulos 003-008 operan, pero falta el **centro de información**: un dashboard (indicadores, alertas, vencimientos) y **reportes** ejecutivos, operativos, financieros, fiscales y regulatorios que se puedan **reconstruir desde eventos y documentos auditables** (DOC-01 §1) y **exportar de forma auditada** (DOC-01 §5). También falta consolidar la **auditoría** (timeline de cambios, impresiones, exportaciones, accesos e incidentes — DOC-01 §4).

DOC-01 §4 define Reportes como: Ejecutivos, operativos, fiscales, financieros, regulatorios y de auditoría; y Auditoría como: timeline, cambios, impresiones, exportaciones, accesos e incidentes. DOC-01 §5 exige **exportaciones auditadas**, minimización, permisos por campo y retención.

## 2. Objetivos

1. **Dashboard (Inicio)**: indicadores, tareas, alertas y vencimientos agregados (DOC-01 §4).
2. **Reportes ejecutivos**: KPIs de ventas, compras, tesorería, fiscal y regulatorio.
3. **Reportes operativos**: inventario, órdenes, despachos, cajas y movimientos.
4. **Reportes financieros**: CxC/CxP aging, tesorería y diferencias cambiarias.
5. **Reportes fiscales**: libros de 007 (ventas/compras/retenciones/IGTF).
6. **Reportes regulatorios**: matrices y permisos (008).
7. **Exportación auditada** (CSV/PDF) con registro de quién/cuándo/qué (P5, DOC-01 §5).
8. **Auditoría consolidada**: timeline de cambios, impresiones, exportaciones, accesos e incidentes (reutiliza `AuditEvent` de 001).
9. **Reconstrucción** de saldos, libros y estados desde eventos y documentos auditables (DOC-01 §1); nunca tablas editables.
10. **Privacidad**: minimización, permisos por campo y retención configurable.

## 3. Fuera de alcance

- Reimplementar los módulos 003-008: 009 **consume sus datos** en lectura.
- La **contabilidad formal** (mayor, partidas dobles, cierre contable completo) — no forma parte del roadmap actual.
- La **emisión de documentos oficiales** (007/008).

## 4. Actores

| Actor | Uso |
|---|---|
| Dirección | Dashboard y reportes ejecutivos |
| Operación | Reportes operativos (inventario, órdenes, despachos, cajas) |
| Finanzas | Reportes financieros (CxC/CxP, tesorería) |
| Contador / fiscal | Reportes fiscales (libros 007) y regulatorios |
| Auditor | Consulta integral, evidencias y exportaciones controladas (DOC-01 §4) |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-009-001 | Como dirección, quiero un dashboard con indicadores y vencimientos por módulo. |
| US-009-002 | Como dirección, quiero reportes ejecutivos con KPIs de ventas/compras/tesorería/fiscal. |
| US-009-003 | Como operación, quiero reportes operativos de inventario, órdenes, despachos y cajas. |
| US-009-004 | Como finanzas, quiero reportes financieros de CxC/CxP aging y tesorería. |
| US-009-005 | Como contador, quiero reportes fiscales reconstruibles (libros 007) y regulatorios. |
| US-009-006 | Como usuario, quiero exportar reportes de forma auditada (CSV/PDF). |
| US-009-007 | Como auditor, quiero la timeline de cambios, impresiones, exportaciones, accesos e incidentes. |

## 6. Requisitos funcionales

Convención: `FR-009-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Dashboard

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-009-001 | Dashboard con indicadores agregados (ventas, compras, tesorería, fiscal) y vencimientos. | DOC-01 §4 | P0 | Dirección |
| FR-009-002 | Alertas y tareas/vencimientos consolidados por módulo. | DOC-01 §4 | P1 | Dirección |

### 6.2 Reportes

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-009-010 | Reportes ejecutivos: KPIs por módulo (ventas, compras, tesorería, fiscal, regulatorio). | DOC-01 §4 | P0 | Dirección |
| FR-009-011 | Reportes operativos: inventario, órdenes, despachos, cajas y movimientos. | DOC-01 §4 | P0 | Operación |
| FR-009-012 | Reportes financieros: CxC/CxP aging, tesorería y diferencias cambiarias. | DOC-01 §4 | P0 | Finanzas |
| FR-009-013 | Reportes fiscales: libros de 007 (ventas/compras/retenciones/IGTF). | DOC-01 §4 | P0 | Contador |
| FR-009-014 | Reportes regulatorios: matrices y permisos (008). | DOC-01 §4 | P1 | Operación |
| FR-009-015 | Filtros por empresa, período, moneda, estado y categoría; reconstrucción desde eventos (DOC-01 §1). | DOC-01 §1 | P0 | Sistema |

### 6.3 Exportación y auditoría

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-009-020 | Exportación auditada (CSV/PDF) con registro de quién/cuándo/qué (P5). | DOC-01 §5 | P0 | Sistema |
| FR-009-021 | Permisos por campo y minimización; retención configurable (privacidad). | DOC-01 §5 | P0 | Sistema |
| FR-009-022 | Auditoría: timeline de cambios, impresiones, exportaciones, accesos e incidentes (reutiliza `AuditEvent` de 001). | DOC-01 §4 | P0 | Auditor |
| FR-009-023 | Trabajos asíncronos para reportes pesados con estado y error. | DOC-01 §4 | P1 | Sistema |

### 6.4 Transversales

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-009-100 | Aislamiento multiempresa; idempotencia; decimal exacto. | DOC-03 §12 | P0 | Sistema |
| FR-009-101 | Frontend: dashboard y centro de reportes sin scroll horizontal. | DOC-08 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §1/§5)

- Los saldos, libros y estados se **reconstruyen** desde eventos y documentos auditables; no desde tablas editables.
- Las **exportaciones son auditadas** (quién, cuándo, qué) — P5.
- Privacidad: minimización, permisos por campo y retención configurable.
- 009 consume datos de 003-008; no duplica su lógica.
- Multiempresa estricta; los reportes no cruzan empresas sin relación autorizada.

## 8. Criterios de éxito (resumen)

- Dashboard con indicadores y vencimientos por módulo.
- Reportes ejecutivos/operativos/financieros/fiscales/regulatorios con filtros.
- Exportación auditada (CSV/PDF) con registro de eventos.
- Auditoría consolidada (timeline de cambios, impresiones, exportaciones, accesos, incidentes).
- Reconstrucción desde eventos; sin tablas editables.
- Trabajos asíncronos para reportes pesados.
