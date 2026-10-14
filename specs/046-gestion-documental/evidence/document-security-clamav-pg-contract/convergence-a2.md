# Convergencia · `ENTORNO-SIN-CLAMSCAN — CLOSED / CONVERGED` (2026-10-14)
Todas las condiciones de la compuerta: decisión A/A2; ClamAV real 1.4.3 provisionado sin root en prefijo de usuario con
paquetes oficiales verificados; cierre de dependencias probado; firmas usables (main 63 · daily 28153 · bytecode 339);
CLEAN y EICAR reales en cada preflight; fallo cerrado probado; producto, `scanning.py` y producción intactos; siete carreras
PostgreSQL-only y ejecutadas con éxito; fallos del analizador 0 en SQLite y PostgreSQL; E2E sin omisiones del analizador ×2;
SQLite ×2 y PostgreSQL sin regresión (solo OBS-10 y el intermitente de reloj, clasificados); OpenAPI sin cambio; migración 0;
esquema 0; 14/14 mutaciones; 0 bases, 0 schemas, 0 dirs; BLOCKER 0; MATERIAL OQ 0; UNKNOWN 0; trazabilidad 100 %.
Observaciones que siguen, no absorbidas: OBS-01/03/04/06/07, OBS-09 (imagen de producción sin analizador), OBS-10
(`legacy_import` sobre la conexión compartida), **OBS-11** (`test_sync_success_records_run_snapshot_and_event` compara con
el instante de inicio del módulo y falla cuando la suite tarda minutos; 8/8 sola; dueñas 010/054).
Cierre por delta (las tres fases): tareas 9+9 · CLAUDE_ONLY · DeepSeek 0 · producto 0 · ficheros nuevos: `qa/clamav_qa.py`,
`tests/test_clamav_qa.py`; modificado: `qa/e2e_corrida.py` (`--con-analizador`).
