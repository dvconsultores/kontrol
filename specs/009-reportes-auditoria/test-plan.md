# PLAN DE PRUEBAS — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/test-plan.md` |

> Estrategia: pytest backend (sqlite in-memory, fixture `conftest.py`), Vitest frontend, build. Se añade `tests/test_reporting.py`.

| ID | Tipo | Caso | Prerrequisito | Resultado esperado | Estado |
|---|---|---|---|---|---|
| TP-009-01 | Unit | Dashboard con indicadores y vencimientos | Datos 003-008 | Indicadores y vencimientos agregados | ⬜ |
| TP-009-02 | Unit | Alertas/vencimientos consolidados | Datos | Alertas por módulo | ⬜ |
| TP-009-03 | Unit | Reporte ejecutivo de ventas | Facturas 005 | KPIs (total, base, impuestos) | ⬜ |
| TP-009-04 | Unit | Reporte operativo de inventario | Movimientos 003 | Existencias y movimientos | ⬜ |
| TP-009-05 | Unit | Reporte financiero CxC/CxP aging | Open items 004/005 | Aging por bucket | ⬜ |
| TP-009-06 | Unit | Reporte fiscal reutiliza libros 007 | Emisiones 007 | Libro ventas/compras | ⬜ |
| TP-009-07 | Unit | Reporte regulatorio | Evaluaciones 008 | Matriz y permisos | ⬜ |
| TP-009-08 | Unit | Filtros por empresa/período/estado | Datos | Resultados filtrados | ⬜ |
| TP-009-09 | Unit | Exportación auditada (CSV/PDF) | Reporte | `report_exports` registrado (quién/cuándo/qué) | ⬜ |
| TP-009-10 | Unit | Permisos por campo y minimización | Perfil | Solo campos permitidos | ⬜ |
| TP-009-11 | Unit | Auditoría consolidada (AuditEvent) | Eventos | Timeline de cambios/exportaciones | ⬜ |
| TP-009-12 | Unit | Job asíncrono con estado/error | Reporte pesado | PENDING→RUNNING→DONE/FAILED | ⬜ |
| TP-009-13 | Unit | Aislamiento multiempresa | 2 empresas | Sin fuga de datos | ⬜ |
| TP-009-14 | UI | Dashboard y centro de reportes | Frontend | Sin scroll horizontal; exportación accesible | ⬜ |
