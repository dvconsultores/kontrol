# INVESTIGACIÓN — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/research.md` |

## 1. Referencias documentales

| Doc | Sección | Contenido usado | Estado |
|---|---|---|---|
| DOC-01 | §1 | Reconstruir saldos, libros y estados desde eventos y documentos auditables. | ✔ |
| DOC-01 | §4 | Inicio: Dashboard, tareas, alertas, vencimientos e indicadores; Auditoría: timeline, cambios, impresiones, exportaciones, accesos, incidentes; Reportes: ejecutivos, operativos, fiscales, financieros, regulatorios; trabajos asíncronos para reportes y documentos. | ✔ |
| DOC-01 | §5 | Privacidad: minimización, permisos por campo, exportaciones auditadas y retención. | ✔ |
| DOC-02 | §4 | Reportes: ejecutivos, operativos, financieros, fiscales, regulatorios, auditoría; Auditoría: timeline, datos, accesos, impresiones, exportaciones, incidentes. | ✔ |
| DOC-03 | §11 | Entidades: AuditEvent (tenant, company, user, action, entity, before/after, request_id, session, source, reason, evidence, timestamp), OutboxEvent. | ✔ |
| DOC-08 | — | Wireframes: dashboard y centro de reportes. | ✔ |

## 2. Estado de dependencias en el código

| Dependencia | Estado | Uso en 009 |
|---|---|---|
| 001-fundacion | Implementada (certificada) | `AuditEvent` (timeline), multiempresa |
| 003-inventario | Implementada | balances/movimientos (operativos) |
| 004-compras | Implementada | CxP aging, pagos |
| 005-ventas | Implementada | ventas, órdenes, despachos |
| 006-tesoreria | Implementada | transacciones bancarias, cajas |
| 007-fiscal | Implementada | libros reconstruibles |
| 008-regulacion | Implementada | evaluaciones, permisos |
| 010+ | NO (futuro) | licenciamiento central |

## 3. Patrones reutilizables verificados

- Módulo backend plano `models.py`/`service.py`/`api.py` + registro en `init_models` y `app/main.py`.
- `AuditEvent` de 001 para trazabilidad (reutilizar).
- Libros de 007 como vista reconstruible (mismo patrón para reportes).
- Contrato de integración v1 (003-008) para consumir datos en lectura.

## 4. Riesgos de investigación

| Riesgo | Detalle | Mitigación |
|---|---|---|
| Reportes lentos en datos grandes | Agregaciones pesadas | Paginación + jobs asíncronos (FR-009-023) |
| Exportaciones sin auditar | Contrario a P5 | `report_exports` obligatorio (FR-009-020) |
| Duplicar lógica de módulos | 009 podría reimplementar | Solo lectura vía contratos (CL-009-01) |
| Fuga de datos entre empresas | Reportes multiempresa | Aislamiento estricto (FR-009-100) |
