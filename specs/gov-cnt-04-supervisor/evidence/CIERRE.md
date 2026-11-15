# CIERRE · CNT-04 Supervisor / responsable del contrato (GOV-CNT-004) · 2026-11-15

## PRODUCT COMPLETENESS GATE

- WHERE_IS_IT_IN_MENU: Gobierno · Contratos › Contratos y órdenes › (contrato formalizado) › sección «Supervisor / responsable del contrato».
- WHAT_CAN_USER_DO:
  - designar al supervisor de un contrato formalizado: funcionario con ocupación vigente y acto de designación eficaz emitido por un cargo con Aprobar × Contrataciones;
  - sustituirlo con un acto nuevo, una fecha efectiva y un motivo (la sustitución puede quedar programada);
  - consultar el vigente, el programado y el historial;
  - consultar quién era supervisor en una fecha.
- OWNER_UAT_READY: YES · OWNER_ACCEPTED: NO (solo la concede la dueña).
- PRODUCT_STATUS: OWNER_UAT_READY (10/10 compuertas).
- MISSING_GATES: ninguna.

## Resultado

| Comprobación | Resultado |
|---|---|
| PG dirigidas (CNT-04 12 + CNT-01 13) | 25/25 |
| PG completa (una vez, árbol final convergido, run r20261115t141525p1435180n459fd5) | 5559 en verde, 36 en rojo, 18 omitidas; los 36 rojos son idénticos a la línea base → NEW_BACKEND_FAILURES=0 |
| Vitest | 2071/2071 |
| tsc, eslint, build | OK |
| E2E gobierno-contratos (CNT-01 + CNT-04, 1280/390/320, Axe) | 1/1, 0 reintentos |
| mypy | 157 (línea base) |
| ruff | limpio |
| Alembic | up/down/up; cabeza 0117_gov_cnt04_supervisor (1 cabeza) |

## Métricas

- 399/1269 compuertas aplicables en PASS (antes 389).
- 39/122 requisitos OWNER_UAT_READY (antes 38).
- N_A 73; universo 1342.

## Efectos sobre otros requisitos

- ORG-05: CONTRACT_RESOURCE_NOW_EXISTS=1. Sigue BLOCKED y no se declara READY.
- CNT-03: tiene contrato de consumo (`supervisor_en`, `supervisor_vigente`, GET `/supervision/en`). CNT03_IMPLEMENTED=0.

## Abierto

- **OQ-CNT04-01:** varios supervisores a la vez (por ejemplo, por frente de obra). La fuente no lo exige; por ahora rige OD-CNT04-01, un solo supervisor vigente.
- **Revocación sin sucesor:** no se implementa, porque las fuentes no la regulan.

## DeepSeek

10 llamadas a deepseek-v4-pro (la 9.ª y la 10.ª las autorizó la dueña). Detalle en ATTEMPT_LOG.md.

## UAT

- Pila nueva desde el SHA publicado 5828ec2 (worktree wt-5828ec2): frontend http://localhost:16673/, backend 19500, central 19510.
- Humo HUMO-UAT-01: 1/1. OWNER_UAT_ACCESSIBLE=YES.
- Credenciales: fuera de Git, en un fichero local con permisos 600. No se registran aquí.
- La dueña acepta (OWNER_ACCEPTED): NO, pendiente.
