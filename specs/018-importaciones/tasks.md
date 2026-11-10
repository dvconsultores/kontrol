# Spec 018 · tareas

| Tarea | Alcance | EXECUTOR | ESTADO |
|---|---|---|---|
| T018-01 | Backend: expediente, negociación, orden, documentos, estados, auditoría | DEEPSEEK | Hecha |
| T018-02 | Frontend: listado, alta, expediente, menú y permisos | DEEPSEEK | Hecha |
| T018-03 | E2E real en navegador | DEEPSEEK, ejecutada por Claude | Hecha: Chrome sobre SQLite |
| T018-04 | Ciclo 2: backend de seguimiento, agente, despacho, pago y correcciones | DEEPSEEK | Hecha |
| T018-04b | Ciclo 2: secciones del expediente y selector de órdenes sin truncar | DEEPSEEK | Hecha |
| T018-04c | Ciclo 2: E2E en Chrome | DEEPSEEK, ejecutada por Claude | Hecha: Chrome sobre SQLite |
| T018-04d | Regresión de reglas del ciclo 2: corrección a ORDERED, DISPATCHED no cancela, permisos, órdenes sin truncar | DEEPSEEK | Hecha |
| T018-05 | Ciclo 3: arribo, recepción, diferencias, confirmación y ubicación integrados con 019 a 022 | DEEPSEEK | Hecha: E2E en Chrome sobre SQLite |
| T018-06 | Ciclo 4: gastos de importación con Spec 026 | DEEPSEEK | Hecha: gastos. Chrome sobre PostgreSQL migrado |
| T018-06b | Ciclo 4B: preview, distribución y aplicación de landed cost | DEEPSEEK; auditoría de Claude | Hecha: `spec018-landed-cost-delta.md`, evidencia en `evidence/landed-cost/` |
| T018-07 | Reporte formal de diferencias: instantánea, PDF, revisiones y acceso desde Recepciones | DEEPSEEK; auditoría de Claude | Hecha: `spec018-difference-report-delta.md`, evidencia en `evidence/difference-report/` |
| T018-08 | Validación física de ubicación y reubicación por error | DEEPSEEK; auditoría de Claude | Hecha: `spec018-relocation-delta.md`, evidencia en `evidence/relocation/` |
| T018-PG | IMP-PG-INTEGRITY-01: Importaciones sobre PostgreSQL migrado. Los ciclos 1 a 3 pasan de `BROWSER_VERIFIED_SQLITE_ONLY` a `POSTGRESQL_BROWSER_VERIFIED` | DEEPSEEK; auditoría y evidencia de Claude | Hecha: `spec018-pg-integrity-delta.md` |
