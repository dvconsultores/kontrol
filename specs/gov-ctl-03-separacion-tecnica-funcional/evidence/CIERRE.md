# CIERRE · CTL-03 (GOV-CTL-004) · 2026-11-11

- **Producto:** `011cf82` (feat) y `7db2ecc` (humo UAT) en `develop`, sobre `f69bd69` (origin integrado; Alembic `0097_fusion_gov_replenishment`, sin migración).
- **Menú:** Gobierno › Separación técnica y funcional. **API:** `GET /gobierno/control/separacion` (`gobierno_auditoria:view`).
- **Arqueología:** escenario A (`AUTHORITY_FABRICATION_SURFACE_MATRIX.md`); sin motor nuevo ni `if ADMIN deny`.

## Evidencia
| Puerta | Resultado |
|---|---|
| E2E Chromium `gobierno-separacion.spec.ts` (P1..P7, Axe WCAG 2.2 AA, 1280/390/320) | 1/1 PASS |
| Backend CTL-03 en PostgreSQL (AP-01..06, SP-01..08) | 14/14 |
| Regresión dirigida en PostgreSQL (Spec 003, ORG-03/04/06/07, CTL-01/02, DOC-02; 29 ficheros) | 328/328 |
| Mutaciones (techo, guarda, listado) | 3/3 muertas |
| mypy | 154 = línea base |
| ruff | limpio |
| tsc, ESLint, build | PASS |
| Vitest de Gobierno | 640/640 |
| Vitest consumidores de fixtures | 393/393 |
| OpenAPI frente a origin | +1 ruta, +11 esquemas; 0 retirados, 0 cambiados, 0 operaciones cambiadas |
| Fixtures (`qa/fixtures_de_frontend.py`) | solo altas (+1 ruta, +1 operación) |
| UAT `wt-7db2ecc` (15473/18300), humo HUMO-UAT-01 con la pantalla nueva | PASS |

## Hallazgos del ciclo
- **P5:** el defecto estaba en el selector de la E2E. El nombre accesible de la tabla lo lleva su `div role="region"`.
  SP-08 demuestra por HTTP la cadena completa: evento → proyección → aislamiento.
- **OpenAPI:** colisión de nombre con `CompetenciaOut` de `schemas_cargos`, corregida con `CompetenciaSeparacionOut`.
- **Rechazado:** quitar `db.rollback()` de `authority._denegar`. Era especulativo y SP-08 pasa sin ese cambio.
- **Declarados:**
  - OD-ORG06-09 está inactiva por defecto y la pantalla lo muestra;
  - las denegaciones propias de ORG-04 y ORG-06 no generan evento de techo.

## DeepSeek
- **Llamadas:** C1..C14, todas `deepseek-v4-pro`. Todo el código y todas las pruebas los escribió DeepSeek.
- **Claude:** solo aplicación mecánica. Dos excepciones de formato, ambas declaradas:
  - conversión de bloques markdown en C4;
  - `ruff --fix` de imports en SP-08.

OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES · OWNER_ACCEPTED = NO
