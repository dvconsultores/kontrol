# Convergencia

**OBS-08 — CLOSED / CONVERGED** (2026-10-14): las siete carreras con mecanismo dependiente de PostgreSQL llevan el marcador
canónico con autoridad (FR-046-115, conc-046, P21); contrato estático; en SQLite se omiten con razón; cobertura no
concurrente intacta; 10/10 mutaciones; SQLite 1637/33/1049 ×2; PostgreSQL 2653/37/29; OpenAPI y E2E sin cambio; producto 0.

**ENTORNO-SIN-CLAMSCAN — BLOCKED BY OWNER DECISION**: sin analizador no se certifican 26+2 pruebas de backend (en los dos
motores: 35 nodos en PostgreSQL contando las carreras) y 4 E2E; inventario corregido (los 7 de `legacy_import` son OBS-10,
no del analizador). Opciones y recomendación (A) en `option-matrix.md` / `recommendation.md`.

Observaciones nuevas, no absorbidas: OBS-09 (imagen de producción sin analizador), OBS-10 (`legacy_import` sobre la conexión
compartida + petición HTTP con la sesión abierta). Cierre por delta: tareas 9 · CLAUDE_ONLY 9 · DeepSeek 0 · regresiones 0.
