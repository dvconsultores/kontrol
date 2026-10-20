# Orquestación — normalización de pruebas para la paridad de despliegue

Regla permanente 1:
- **Claude:** reprodujo y midió, fijó el diseño (incluida la desviación justificada en OAS-14), escribió tres briefs
  con anclas SEARCH literales verificadas y comprobó el egress antes de cada llamada. Después auditó, aplicó tal cual y
  certificó.
- **DeepSeek:** escribió todos los cambios de prueba.
- Claude no escribió código de producto ni pruebas, y no hubo cambio de producto (OD-CERT-03).

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1 OAS-14 (`_matriz_runtime`) | deepseek-v4-pro | 1744/880 | $0,001414 | AUDIT_PASS |
| 2 | T2 ACS-08 (`_codigo_sin_docstring`) | deepseek-v4-flash | 1605/758 | $0,000419 | AUDIT_PASS |
| 3 | T3 U01-U04 (`_esperar_pool_en_reposo`) | deepseek-v4-pro | 2218/1443 | $0,002110 | AUDIT_PASS |

**Total:** 3 llamadas, 5567/3081 tokens, **$0,003943**. Reintentos 0, rechazos 0.

**Egress:** por llamada EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0, con 0
coincidencias de rutas, usuario, URL de QA o secretos en los tres briefs.
