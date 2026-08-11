# INFORME EJECUTIVO — RUN `KONTROL-QA-20260810-234937`

## Resultado general
**FAIL** (NO CERTIFICABLE) — bloqueado por caída del backend.

## Indicadores
- Total pruebas: 4 directas + 5 viewports responsive + 1 navegador (login).
- PASS: 2 · FAIL: 4 · BLOCKED: 50+ · NOT_IMPLEMENTED: 0 · EXPECTED_VALIDATION: 0.

## Severidad
- BLOCKER: 1 (KQA-001 · API 502).
- CRITICAL: 0 · HIGH: 1 (KQA-002 · health checks devuelven SPA) · MEDIUM: 0 · LOW: 0.

## Procesos
- Completos: 0 · Incompletos: 0 · Rotos/Bloqueados: todos (login).

## Recomendación
- **Requiere corrección**: restaurar el backend (KQA-001) y corregir health check de nginx (KQA-002).
- **No apto para producción** en el estado observado (la instancia pública no permite operar).
- Re-ejecutar la prueba completa tras la remediación.
