# Spec 015 · Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | DONE_WHEN |
|---|---|---|---|---|---|---|---|
| T015-A | Módulo `planning`: modelos, migración (políticas, bandas, instantáneas de línea, `warehouse_id` de la requisición, `rotation_band_id` de la regla de almacenamiento, índice por fecha), API de configuración, auditoría y pruebas | DEEPSEEK | deepseek-v4-pro | SÍ (contrato fijado en spec.md) | SÍ | 2 | CRUD versionado, aislado y auditado en PostgreSQL y SQLite |
| T015-B | Motor: selección y neteo de la demanda, ventana, media, proyección, stock de seguridad, punto de reorden, posición, rotación (velocidad y turnover), banda, recomendación, historia insuficiente o parcial, demanda cero; API de consulta y pruebas | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Vectores exactos en `Decimal` |
| T015-C | Requisición: almacén, detalle, línea con conversión a base, instantánea, aceptación o cambio de la sugerencia, política vencida; pruebas | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Instantánea reproducible |
| T015-D | Spec 018: criterio de banda de rotación en reglas y motor de almacenamiento, sin recalcular; pruebas | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Una regla con banda determina la zona |
| T015-E | Frontend: Maestros → Planificación, Compras → Planificación, Nueva requisición y detalle con panel, banda en las reglas de almacenamiento; Vitest | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Flujos usables |
| T015-F | E2E de usuario: política, requisición con sugerencia, instantánea tras cambiar la política, banda en almacenamiento | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Chrome sobre PostgreSQL a 3 anchos |
| T015-G | Certificación, documentos y publicación | CLAUDE | n-a | NO | SÍ | 0 | `HEAD == origin/develop` |

## Estado al cierre (2026-11-10)

| ID | Estado | Llamadas | Evidencia |
|---|---|---|---|
| T015-A | COMPLETE | 1, 2, 4, 5 (y 3, que la ignoró) | `test_planning_config.py`; migración `0094_supply_planning` up/down/up en PostgreSQL |
| T015-B | COMPLETE | 3, 6, 7, 8 | `test_planning_engine.py` (vectores exactos en `Decimal`) |
| T015-C | COMPLETE | 9, 10, 11 | `test_planning_requisition.py` |
| T015-D | COMPLETE | 12, 13, 14 | `test_storage_rotation_band.py` |
| T015-E | COMPLETE | 15 a 20 (E1 Maestros → Planificación, E2 requisición nueva y detalle, E3 banda en reglas) | Vitest 1892/1892 |
| T015-F | COMPLETE | 21, 22, 23 | `e2e/planificacion.spec.ts` en Chrome sobre PostgreSQL a 1280, 390 y 320 |
| T015-G | COMPLETE | Claude | `evidence/EVIDENCE.md`, `evidence/ATTEMPT_LOG.md` |
