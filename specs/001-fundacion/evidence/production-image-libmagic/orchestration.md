# Orquestación — PRODUCTION-IMAGE-WITHOUT-LIBMAGIC

Regla permanente 1:
- **Claude:** reprodujo, determinó la base (Debian 13 trixie, por digest), el paquete real (`libmagic1t64` con
  `libmagic-mgc`) y la versión (`python-magic` 0.4.27). Fijó el diseño y escribió los briefs con anclas literales
  verificadas y el egress comprobado antes de cada llamada. Después auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió todos los cambios.
- Producto sin cambio.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1 `requirements.txt` | deepseek-v4-flash | 952/284 | $0,000195 | AUDIT_PASS |
| 2 | T2 `Dockerfile.backend` | deepseek-v4-flash | 1191/545 | $0,000302 | AUDIT_PASS |
| 3 | T3 prueba, intento | deepseek-v4-pro | 2147/2026 | $0,002586 | AUDIT_REJECT |
| 4 | T3 corrección 1 | deepseek-v4-pro | 4990/2245 | $0,004013 | AUDIT_REJECT |
| 5 | T3 corrección 2 (último reintento) | deepseek-v4-pro | 3435/2200 | $0,003298 | AUDIT_PASS |

**Total:** 5 llamadas, 12715/7300 tokens, **$0,010394**. Reintentos: 2 en T3 (el máximo). Rechazos: 2.

**Motivos de rechazo:**
- **Intento:** `nombre_anterior` usado antes de asignarse (F821 y `UnboundLocalError` en IMB-03), padre de etapa mal
  calculado, «_final» metido dentro del diccionario de etapas, continuaciones solo de FROM/RUN, y UP012.
- **Corrección 1:** resolvió todo salvo H4. Claude demostró que dejarlo daba un **falso PASS**: una línea de
  continuación de `ENV` que empieza por `RUN apt-get install … libmagic1t64` se tomaba por un RUN real.

**Egress:** por llamada EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0, con 0
coincidencias de rutas, usuario, URL de QA o secretos en todos los contenidos enviados.

**Herramienta de Claude:** en la primera pasada de mutaciones, el escenario de M09 se ejecutó en V1, donde
`detect_mime` falla antes en `import magic`. Era un error de elección de escenario; se repitió en V1' y quedó KILLED.
