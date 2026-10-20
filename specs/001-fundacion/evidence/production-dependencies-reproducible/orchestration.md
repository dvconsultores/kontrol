# Orquestación — REPRODUCIBLE DEPLOYMENT DEPENDENCIES

Regla permanente 1:
- **Claude:**
  - descubrió el lock histórico, construyó la tabla de autoridad de versiones y pasó las puertas de compatibilidad y de
    CVE;
  - hizo la prueba de determinismo y el humo de V3, y diseñó el contrato;
  - ejecutó la regeneración del lock como **procedimiento mecánico**: el comando canónico, sin edición manual
    (`requirements.lock` es salida de uv);
  - escribió los briefs con el egress comprobado antes de cada llamada; después auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió el cambio del Dockerfile y todas las pruebas.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| — | T1 `requirements.lock` (comando canónico de uv) | — (procedimiento) | — | $0 | regeneración idempotente y cuerpo igual al grafo de V3 |
| 1 | T2 `Dockerfile.backend` (instalar el lock con `--no-deps` y `pip check`) | deepseek-v4-flash | 2076/361 | $0,000374 | AUDIT_PASS |
| 2 | T3 `test_dependencias_lock.py` (IDL-01..07) e IMB-03 | deepseek-v4-pro | 8824/3703 | $0,006950 | IMB-03: AUDIT_PASS · IDL: AUDIT_REJECT, ver nota 1 |
| 3 | T3 corrección 1 | deepseek-v4-pro | 13025/3413 | $0,008525 | AUDIT_PASS: H1-H4 resueltos, 28/28 en V0 y V3, ruff limpio y formateado, rojo correcto |

**Nota 1, motivos del rechazo de la llamada 2:**
- H1 `_python_de_la_base` partía el nombre de etapa por «AS».
- H2 IDL-06 comprobaba la unión de cadenas en vez de cada una.
- H3 docstring inexacto y regex duplicada.
- H4 sin `ruff format`.

**Total:** 3 llamadas, 23925/7477 tokens, **$0,015849**. Reintentos: 1 (T3). Rechazos: 1.

**Egress:** EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0 en cada llamada.
`/tmp/requirements.*` es una ruta dentro del contenedor, no local.
