# Spec 012 — Plan de Auditoría

## Fases ejecutadas (pasada 1)
- FASE 0 · Git/ambiente: rama `develop`, limpia; spec `012` creada.
- FASE 1 · Lectura de Specs y contexto: uso de memoria de repo (010, 011, auditoría 001-011) + router/sidebar reales.
- FASE 2-6 · `/speckit.specify` → spec.md; inventarios (menú, router, páginas, API) generados por scripts.
- FASE 7-9 · plan.md, checklist.md, tasks.md.
- FASE 10-12 · Auditoría automática: menú↔ruta↔página↔API (135 llamadas), BD estática (144 tablas), marcadores.
- FASE 28-30 · Consolidación → findings.md, functional-completeness-matrix.md, remediation-plan.md, reporte ejecutivo.
- FASE 31-32 · **NO-GO** (definición estricta) → DETENER y solicitar autorización.

## Fases NO ejecutadas (requieren ambiente/recursos autorizados)
- Navegadores reales (Safari/Opera/Samsung), dispositivos → `SIMULATED_ENGINE_VALIDATION` solamente.
- Seguridad destructiva (OWASP, tenant isolation, IDOR) contra ambiente controlado.
- Backup→restore real; rendimiento con dataset grande; accesibilidad (axe).
- Auditoría fiscal normativa completa y validación de inmutabilidad de documentos.
- E2E de procesos completos (Playwright) y puertas permanentes (T-08..T-11).
