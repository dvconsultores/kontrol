# SPEC018_REUBICACION_ERROR_Y_VALIDACION_FISICA · registro de intentos

Llamadas secuenciales a `deepseek-v4-pro` con `stream=true`. Presupuesto del encargo: 5 llamadas, objetivo 3. La dueña autorizó después 2 llamadas extra: **7 en total**. Todo el código, las pruebas y la migración los propuso DeepSeek. Claude diseñó, auditó, aplicó y certificó. Las correcciones de medición se hicieron solo en copias temporales fuera del repositorio.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | T-RL-A backend completo | 14275/19012 | $0,022750 | AUDIT_REJECT. Un SEARCH no coincidía (la línea de import real lleva `costs,`). `KontrolError` sin `message`. `serial_id == None` hacía que nunca se marcara SUPERSEDED y que `stale` saliera siempre verdadero. 15 errores de mypy y 7 de ruff. Pruebas con `cab.post` sobre un dict. **Error del contrato de Claude:** las claves `before` de la reubicación no estaban en el catálogo |
| 2 | T-RL-A reintento 1 | 12508/8192 | $0,012568 | Producto casi resuelto. La respuesta se cortó por longitud (`max_tokens` no se pasó: **error de proceso de Claude**). El fichero de pruebas no se aplicó |
| 3 | T-RL-A reintento 2 (último) | 10125/8933 | $0,012176 | Producto AUDIT_PASS: ruff limpio y mypy 154. Las pruebas siguieron rotas (`Party` mal importado, `cab.post`, falta `company_id`). Reintentos agotados |
| 4 | T-RL-B frontend | 9039/7196 | $0,010082 | Componente AUDIT_PASS: TSC y ESLint limpios. Vitest 4 de 8 por defectos de prueba (mock del GET, etiqueta «Motivo *», texto repetido) |
| 5 | T-RL-T pruebas backend + Vitest (extra 1, decisión de la dueña) | 9635/8353 | $0,011458 | Backend AUDIT_PASS: 18 de 18, las mismas 108 aserciones. El bloque de Vitest se rechazó por un SEARCH duplicado y no se aplicó |
| 6 | T-RL-C E2E + reintento de Vitest (dos tareas, desviación autorizada) | 3524/2881 | $0,004039 | Vitest 31 de 31. La E2E no compilaba (`historial` redeclarado) y tenía 6 aserciones defectuosas, además de una aserción existente del paso 6 que se volvió ambigua al integrar la sección |
| 7 | T-RL-C reintento 1 (extra 2) | 1105/742 | $0,001126 | AUDIT_PASS. E2E PASS a 1280, 390 y 320 px |

**Total:** 7 llamadas, $0,074199. Rechazos: 1 completo (la llamada 1) y 4 parciales (2, 3, 4 y 5). Implementado por Claude: ninguna línea de producto, de pruebas ni de migración. La tarea T-RL-D (certificación, documentos y publicación) es de Claude por clasificación.
