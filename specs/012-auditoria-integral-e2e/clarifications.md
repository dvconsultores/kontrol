# Spec 012 — Aclaraciones (clarifications.md)

| # | Pregunta / supuesto | Decisión |
|---|---|---|
| CL-01 | ¿Corregir hallazgos en esta pasada? | **No.** Solo auditoría + artefactos. Implementación requiere autorización expresa. |
| CL-02 | ¿Usar producción para pruebas? | **No.** Análisis estático + reproducciones locales con BD en memoria. |
| CL-03 | ¿Navegadores reales? | No disponibles en este entorno → resultados `SIMULATED_ENGINE_VALIDATION`; NO se afirma validación real. |
| CL-04 | `DATETIME` sin timezone (334) | **Falso positivo del dialecto SQLite** (colapsa timezone=True). Pendiente verificación en PostgreSQL. |
| CL-05 | Endpoints "huérfanos" (117) | Requieren clasificación `DOCUMENTED_FUTURE_SCOPE` vs brecha; no todos son defectos (health/docs/licencia). |
| CL-06 | Alcance fiscal | No se validó cálculo contra normativa (IVA/ISLR/IGTF/retenciones); pendiente con equipo fiscal. |
