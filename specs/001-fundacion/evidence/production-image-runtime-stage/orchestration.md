# Orquestación — PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE

Regla permanente 1:
- **Claude:** hizo la reproducción estructural y el inventario de consumidores, eligió el diseño (C: `runtime` como
  última etapa más `target: runtime` en la publicación) y escribió los briefs con anclas literales verificadas y el
  egress comprobado antes de cada llamada. Después auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió todos los cambios.
- Producto y requirements sin cambio.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1 `Dockerfile.backend` (etapa final `runtime`) | deepseek-v4-flash | 1172/591 | $0,000312 | AUDIT_PASS |
| 2 | T3 workflows (`target: runtime`) | deepseek-v4-flash | 1029/459 | $0,000255 | AUDIT_PASS |
| 3 | T2 prueba, intento | deepseek-v4-pro | 2310/1958 | $0,002598 | AUDIT_REJECT: ruta `resources/Dockerfile.backend` (7/8 con `FileNotFoundError`), `_efectiva` sin inicializar y sin docstring de módulo |
| 4 | T2 corrección 1 | deepseek-v4-pro | 4775/2243 | $0,003918 | AUDIT_REJECT: 8/8 y ruff limpio, pero sin el docstring de módulo (H3) |
| 5 | T2 corrección 2 (último reintento) | deepseek-v4-pro | 3198/2425 | $0,003390 | AUDIT_PASS: solo añade el docstring, verificado por diferencia |

**Total:** 5 llamadas, 12484/7676 tokens, **$0,010473**. Reintentos: 2 en T2 (el máximo). Rechazos: 2.

**Egress:** EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0 en cada llamada. Las
referencias `${{ secrets.… }}` de los workflows son plantillas de GitHub, no secretos.
