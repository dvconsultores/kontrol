# Cierre · CNT-03 Ejecución del contrato (GOV-CNT-003 + GOV-CNT-007)

**Estado:** OWNER_UAT_READY. La aceptación (OWNER_ACCEPTED) queda pendiente de la dueña.

## Base y reconciliación

- Entrada: 50fa364.
- Durante el ciclo se integró con un merge ordinario el CNT-02 de P2 (14f1341). Sin rebase ni force.
- Alembic: 0117 → 0118_gov_cnt02_modificaciones (P2) → 0119_gov_cnt03_ejecucion. Cabeza única: ALEMBIC_HEAD_COUNT=1.
- Ninguna migración publicada se modificó. La 0118 de CNT-03, que no estaba publicada, se renombró a 0119.

## Gate y alcance

- Gate de la Constitución: PASS (plan.md).
- Decisiones de la dueña:
  - OD-CNT03-01: dos flujos según el tipo (obras con aceptación provisional y garantía);
  - OD-CNT03-02: el cierre exige aprobación de la Comisión o la Unidad y la evaluación;
  - OD-CNT03-03: conforma el usuario vinculado al supervisor;
  - OD-CNT03-04: la factura tiene como tope lo valuado.
- Fuera de alcance, a propósito: CNT-05, CNT-06, CNT-07, CNT-08, BUD-09, TRE-04, contabilidad, pagos y almacén.

## Verificación sobre el árbol convergido final

| Comprobación | Resultado |
|---|---|
| PG dirigida (CNT-03, CNT-02, CNT-04, CNT-01 y fijaciones) | 214 pasan |
| PG completa, una sola vez (`qa/suite_tiempos.py --motor postgres --con-analizador`, run r20261115t212821p889371n8d8ac5) | 5624 pasan / 5 fallan / 18 omitidas |
| Fallos nuevos frente a la línea base | **0** |

Los 5 fallos ya estaban en la línea base y son ajenos al ciclo:
- imb_07 pip check;
- n10 ORM↔base;
- guard_d01;
- 2 de spec019 receipt.

Además dejaron de fallar 31 casos de entorno de la línea base: backup y restore con pg_dump, y el runner de integridad.

| Comprobación | Resultado |
|---|---|
| Vitest | 2089/2089 |
| tsc y eslint | 0 errores |
| build | OK |
| ruff | limpio |
| mypy | 157 errores, igual que la línea base |
| Alembic | up/down/up sobre una base nueva |
| E2E gobierno-contratos (16 pasos del sponsor, 1280/390/320, Axe) y gobierno-contratos-modificaciones | 2/2, 0 reintentos |

## Métricas

- Gates completos: 420 de 1268 aplicables (universo 1342, N_A 74). Antes del ciclo: 409.
- OWNER_UAT_READY: 41 de 122 (33,61 %). Antes del ciclo: 40.

## DeepSeek

- 17 llamadas con respuesta (deepseek-v4-pro), USD 0,1437. Ampliaciones autorizadas por la dueña: OWNER_EXCEPTION_USED=1.
- Detalle en ATTEMPT_LOG.md.
- CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## UAT

Pila UAT local levantada desde b98d4e6 en el worktree wt-b98d4e6:
- frontend 16773, backend 19600, autoridad central 19610;
- humo HUMO-UAT-01: 1/1 → OWNER_UAT_READY y ACCESSIBLE en esta estación.

La UAT remota para el sponsor sigue BLOCKED_BY_INFRASTRUCTURE (runbook docs/governance/uat-viva-sponsor-runbook.md).
