# Tareas · BUD-02-CLASSIFIER-PARENT-LEVEL

**Autorización de implement:** el encargo «P2 — BUD-02 · Validación de jerarquía del clasificador presupuestario» (2026-11-20).
**Tope de DeepSeek:** 6 llamadas.

Todas las tareas comparten `RETRY_MAX: 2`. Cuando ejecuta DeepSeek, el modelo es `deepseek-v4-pro`; cuando ejecuta Claude, MODEL=n-a.

| Tarea | EXECUTOR | SEC_SENS | EGRESS_SAFE | FILES | TEST | DONE_WHEN | FR |
|---|---|---|---|---|---|---|---|
| T01 Regla única de jerarquía | CLAUDE (aislamiento por clasificador y empresa; se hizo con la prueba del defecto) | SÍ (alcance de empresa) | n-a | `service_presupuesto.py` | T02 | Defecto corregido | FR-CPL-01 a 07 |
| T02 PG del ciclo y mutaciones | CLAUDE (evidencia del defecto) | NO | n-a | `tests/test_gov_bud02_jerarquia.py` | sí misma | 9/9 y M1–M8 muertas | FR-CPL-01 a 07 |
| T03 E2E de alta y CSV | DEEPSEEK | NO | SÍ | `e2e/gobierno-presupuesto-jerarquia.spec.ts` | E2E real | 1/1 con Axe | FR-CPL-08 |
| T04 Regresión, hardcode, tarjeta, roadmap y cierre | CLAUDE | NO | n-a | `evidence/classifier-parent-level/*` y `docs/roadmap/*` | PG dirigida y completa | Sin fallos nuevos | todos |

| T05 Accesibilidad de la lista de errores del CSV | CLAUDE (defecto destapado por Axe; una línea) | NO | n-a | `ClasificadorEjercicio.tsx` | E2E con Axe | 0 violaciones serias | FR-CPL-08 |

**Trazabilidad:** 8 de 8 requisitos con tarea y prueba (100 %).
