# Convergencia · `OBS-02 — CLOSED / CONVERGED` (2026-10-14)

Todos los objetivos físicamente confirmados quedan resueltos o excluidos con evidencia: UoM (HARNESS_SHARED_CONNECTION +
vector incompleto) corregido en el arnés; `test_el_historico…` (HARNESS_STATE_LEAK) corregido en una línea; las seis
carreras de documentos no son objetivos de OBS-02 (su carrera se fuerza con primitivas de PostgreSQL y hoy están
bloqueadas por `clamscan`: ENVIRONMENT_BLOCKED, deuda `ENTORNO-SIN-CLAMSCAN` sin absorber; OBS-08 registrada); el resto
del inventario ya está aislado o es PostgreSQL-only. Producto 0, migración 0, esquema 0, `motor_para_hilos` sin cambio;
12/12 mutaciones; 55/55 corridas dirigidas; SQLite 1630/42/1040 ×2; PostgreSQL 2647/37/28; OpenAPI sin cambio; E2E
280/0/4; 0 bases, 0 schemas, 0 dirs; BLOCKER 0; MATERIAL OQ 0; UNKNOWN 0; trazabilidad 100 %.

Cierre por delta: tareas 9 · CLAUDE_ONLY 9 · DEEPSEEK 0 llamadas, $0 · implementadas por Claude: 2 ficheros de prueba
(1 modificado, 1 nuevo) · regresiones 0. Observaciones que siguen: OBS-01, OBS-03 (solo tocada localmente), OBS-04,
OBS-06, OBS-07 y la nueva **OBS-08** (`test_documents_security.py`: seis carreras forzadas con `pg_backend_pid` sin
`skipif(not PG)`; con `clamscan` presente y sin PostgreSQL fallarían por la función ausente, no por la carrera; dueñas 046/054).
