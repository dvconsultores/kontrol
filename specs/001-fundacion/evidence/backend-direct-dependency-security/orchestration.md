# Orquestación — BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES

Reglas permanentes 1 y SECURITY_DECISIONS_CLAUDE_ONLY = 1.

- **Claude:**
  - refrescó los avisos (pip-audit con PyPI y OSV, OSV, GHSA, changelogs y avisos de OpenSSL), los deduplicó, inventarió
    el uso real y decidió la aplicabilidad con sondas conductuales;
  - eligió versiones y pisos, y construyó y auditó V4-CANDIDATE en el scratchpad;
  - escribió el registro de seguridad (`cve-review.md`) y el enlace cruzado, que son decisiones de seguridad documentadas;
  - regeneró el lock con el comando canónico (procedimiento, sin edición manual);
  - escribió los briefs con el egress comprobado antes de cada llamada, y auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió los pines y todas las pruebas.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| — | T1b `requirements.lock` (comando canónico) | — (procedimiento) | — | $0 | idéntico al candidato e idempotente; solo cambian `pyjwt` y `cryptography` |
| 1 | T1 pines `PyJWT==2.15.0` y `cryptography==50.0.2` | deepseek-v4-flash | 1201/355 | $0,000250 | AUDIT_PASS |
| 2 | T2 SDV-01..07 y pisos de `SUELOS_CVE` | deepseek-v4-pro | 5491/4236 | $0,005963 | `SUELOS_CVE`: AUDIT_PASS · SDV: AUDIT_REJECT, ver nota 1 |
| 3 | T2 corrección 1 | deepseek-v4-pro | 9249/3969 | $0,007366 | AUDIT_PASS: 36/36 en V0 y V4, ruff limpio y formateado, rojo correcto |

**Nota 1, motivos del rechazo de la llamada 2:**
- H1: SDV-05 no recibía el fixture (`AttributeError` en 8/8).
- H2: rama muerta con `callable`.
- H3: fixture sin anotación.
- H4: `next()` sin valor por defecto y aserciones vacías en `_tabla`; B905.
- H5: F401 `Path`. El brief lo pedía por error de Claude, corregido en la corrección.
- H6: sin `ruff format`.

**Total:** 3 llamadas, 15941/8560 tokens, **$0,013579**. Reintentos: 1 (T2). Rechazos: 1.

**Egress:** EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0 en cada llamada. Las
pruebas usan solo secretos sintéticos o la clave del entorno de pruebas.

**Nota de V4:** con PyJWT 2.15.0, la prueba emite `InsecureKeyLengthWarning` al **crear** el token HS512 que debe ser
rechazado. Viene de la prueba, no del producto: el flujo HS256 del producto con una clave de 32 caracteres no emite
avisos con `-W error`.
