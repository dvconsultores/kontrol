# SPEC018_REPORTE_FORMAL_DIFERENCIAS · registro de intentos

Llamadas secuenciales a `deepseek-v4-pro` con `stream=true`. Presupuesto del encargo: 5 llamadas (objetivo 3). La dueña autorizó 3 extra y después 1 más: **9 llamadas en total**. Todo el código lo propuso DeepSeek; Claude auditó, aplicó y probó.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | T-DR-A completa | 14163/24619 | $0,027579 | AUDIT_REJECT: campo inexistente `ApprovalRequest.entity_id`, código muerto, 19 errores de mypy, PDF incompleto, `storage_key` expuesto, pruebas con campos inventados y falsos verdes |
| — | Reintento de 176 KB y luego de 74 KB | — | — | No llegó a DeepSeek: el subagente no puede retranscribir briefs de ese tamaño. Se partió en A1 (servicio) y A2 (pruebas) |
| 2 | T-DR-A1 servicio y API | 14355/12907 | $0,017363 | AUDIT_REJECT: `ZoneInfo.localize`, reutilización de `stmt` (17 errores de mypy), hash nulo sin reporte, doble escapado, fechas en UTC |
| 3 | T-DR-A1, reintento por EDIT | 5563/4231 | $0,006101 | AUDIT_PASS. mypy 154, ruff limpio |
| 4 | T-DR-A2 pruebas | 10238/7171 | $0,010692 | Aplicada parcialmente. Destapó un defecto de servicio (fechas ISO en columnas `DateTime`, SQLite) y corrigió consultas y aserciones |
| 5 | T-DR-A2, reintento | 13884/8341 | $0,013186 | Quedan dos pruebas y ruff. **Error del brief de Claude:** prohibió la cabecera `# ruff: noqa`, que es el precedente medido en las pruebas de importaciones |
| 6 | T-DR-A2, extra 1 | 3415/3693 | $0,004698 | AUDIT_PASS: 13 de 13 en PostgreSQL |
| 7 | T-DR-B frontend, extra 2 | 7914/7615 | $0,010068 | Vitest 99 de 100: referencia duplicada en el historial y un falso verde |
| 8 | T-DR-B corrección y T-DR-C E2E, extra 3 | 3502/1960 | $0,003229 | Vitest, TSC y ESLint en verde. **Desviación:** dos tareas en una llamada. La E2E falló por un selector que dictó Claude en el brief y destapó la caché vieja |
| 9 | T-DR-FIX, extra 4 | 2058/1559 | $0,002252 | AUDIT_PASS: `created_by` no anulable, `refetchOnMount: "always"`, nombre accesible y selectores por rol. E2E PASS a 1280, 390 y 320 px |

**Total:** 9 llamadas, $0,095168. Rechazos: 2 completos (1 y 2) y 3 parciales (4, 5 y 7). AUDIT_PASS: 3, 6, 8 y 9. Implementadas por Claude: ninguna; T-DR-D (certificación, documentos y publicación) es de Claude por clasificación.
