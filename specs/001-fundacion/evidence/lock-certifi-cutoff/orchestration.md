# Orquestación — LOCK-CERTIFI-PYSEC-2026-4320

- **Claude:**
  - revalidó el aviso y los artefactos;
  - midió la semántica de frontera de uv y eligió el corte mínimo;
  - inventarió la ventana e hizo las dos resoluciones y el diff;
  - auditó el lock;
  - regeneró el lock con el comando canónico (procedimiento, sin edición manual);
  - escribió el registro de seguridad (`cve-review`) y el brief con el egress comprobado antes de la llamada;
  - auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió el cambio de IDL-04 y la prueba SDV-08.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| — | T1 `requirements.lock` (comando canónico, corte nuevo) | procedimiento | — | $0 | idéntico al candidato, idempotente; solo cambia certifi |
| 1 | T2 IDL-04 (fracción de segundo) y SDV-08 (suelo de transitivas) | deepseek-v4-pro | 9440/1218 | $0,005056 | AUDIT_PASS a la primera: 43/43 en V0 y V5, ruff limpio y formateado, rojo correcto |

**Total:** 1 llamada, $0,005056. Reintentos: 0. Rechazos: 0.

**Egress:** EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0.
