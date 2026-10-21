# Orquestación — PRODUCTION-BASE-IMAGE-FLOATING-TAG + BASE-IMAGE-CA-STORE-DSA-6572

- **Claude:**
  - revalidó el OCI y verificó la cadena de confianza de trixie-security;
  - seleccionó y verificó `ca-certificates` y tomó las decisiones de seguridad y de arquitectura;
  - escribió la fuente versionada `certified-deployment-base.json`, un registro de hechos medidos y decisiones;
  - construyó y clasificó V5;
  - escribió los briefs con el egress comprobado antes de cada llamada; después auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió el cambio del Dockerfile y la prueba IBB.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | T1 Dockerfile (FROM fijado y pin de ca-certificates) | deepseek-v4-flash | 2381/711 | $0,000515 | AUDIT_PASS |
| 2 | T2 IBB-01..06 | deepseek-v4-pro | 5634/3772 | $0,005622 | AUDIT_REJECT, ver nota 1 |
| 3 | T2 corrección 1 | deepseek-v4-pro | 12783/3146 | $0,008187 | AUDIT_REJECT, ver nota 2 |
| 4 | T2 corrección 2 (último reintento) | deepseek-v4-pro | 4073/3412 | $0,004630 | AUDIT_PASS: 48/48 en V0 y V5, ruff limpio y formateado, rojo correcto, 22/22 mutaciones |

**Nota 1, rechazo de la llamada 2:**
- `_dpkg_cmp` partía mal epoch y revisión.
- `_verrevcmp` no era el algoritmo de dpkg y tenía una rama muerta.
- IBB-02..04 comprobaban la fuente en lugar del Dockerfile (tautológico).
- IBB-01 tenía una aserción redundante.
- Identificador no ASCII.
- F401.

**Nota 2, rechazo de la llamada 3:**
- IBB-03 comprobaba el prefijo incluyendo `python:`.
- Faltaba `ruff format`.
- Había un desempaquetado sin uso.

**Total:** 4 llamadas, 24871/11041 tokens, **$0,018954**. Reintentos: 2 (T2, el máximo). Rechazos: 2.

**Egress:** EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1 y SECRET_EXPOSURE = 0 en cada llamada.

**Nota de aplicación:** la versión rechazada de la corrección 1 llegó a aplicarse en el árbol de trabajo para
auditarla. Antes de aplicar la versión aprobada se borró ese fichero, que era nuevo y estaba sin versionar; el
aplicador no sobrescribe ficheros existentes.
