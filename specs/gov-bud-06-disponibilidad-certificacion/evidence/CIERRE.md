# CIERRE · BUD-06 disponibilidad y certificación presupuestaria (2026-11-14)

```text
ENTRY=1c66b6c  CODE=86165ed (sin merge: origin/develop no avanzó)
ALEMBIC: 0111_gov_bud05_aprobado -> 0112_gov_bud06_certificacion   ALEMBIC_HEAD_COUNT=1
BUD-06=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   GOV-BUD-009 PASS · GOV-BUD-010 PASS
CANONICAL_GATE_UNIVERSE=1342 (antes y después)   N/A 70 -> 71 (REPORTS de BUD-06)   APLICABLES 1272 -> 1271   GATES_REMOVED=0
GOV_GATES_PASSED 349 -> 359   OWNER_UAT_READY 34 -> 35 de 122   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=9 (tope 8; 9.ª autorizada por la dueña, solo este ciclo)   45.065 in / 45.980 out · USD 0,0595
CLAUDE_SEMANTIC_*_WRITTEN=0   SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG test_gov_bud06 (vectores A–F, concurrencia, anulación, aislamiento, autoridad, documento, inmutabilidad, MFA, estado) | 10/10 |
| PG completa con analizador, una vez | 5486 passed / 36 failed / 18 skipped (entrada: 5476 / 36 / 18) |
| mypy | 157, igual que a la entrada |
| ruff (ficheros del ciclo) | limpio |
| Vitest con Node 22 | 2027/2027 (entrada 2021) |
| tsc, eslint, build | limpios |
| E2E gobierno-presupuesto-certificacion (sin reintentos) | 1/1 |
| E2E de presupuesto ×2 con 4 workers | 7/8. El fallo es plan-fuentes (409), que falla igual en la base 1c66b6c: OBS-BUD34-E2E-PARALELO |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en base nueva | upgrade, downgrade a 0111 y upgrade; una sola cabeza |
| Fixtures OpenAPI | regenerados con `qa/fixtures_de_frontend.py` |

**Los 36 rojos de la PG completa** coinciden uno a uno con la línea base reproducida en un worktree de 1c66b6c:
- 30 de pg_dump (backup create/restore);
- integridad_runner;
- imagen pip check;
- n10;
- naive_datetime;
- spec019 ×2.

NEW_BACKEND_FAILURES=0.

## UAT

- Pila sin Docker desde el HEAD publicado 86165ed: frontend en el puerto 16273 (backend 19100, central 19110). PILA UAT LISTA; HTTP 200.
- Humo UAT HUMO-UAT-01: 1/1. OWNER_UAT_ACCESSIBLE=YES.
- Siguen vivas las pilas 15873, 15973, 16073 y 16173.
- Credenciales: no se registran.

## Decisiones de diseño (Claude)

PDD-B06-01..07, en el plan:
- la disponibilidad se deriva siempre y no se guarda;
- bloqueo FOR UPDATE del ejercicio y del crédito;
- certificación inmutable en base, anulación por registro y no por UPDATE libre;
- PDF almacenado con sha256;
- firmante = cargo ORG-03 con FIRMAR×PRESUPUESTO más la guarda ORG-06;
- expediente = PROC-03 o referencia institucional.

## Pendiente

- OBS-BUD34-E2E-PARALELO: plan-fuentes con 409 bajo 4 workers. Es anterior a este ciclo.
- Siguiente en la cadena: BUD-08 (compromiso; BUD-07 es precompromiso o reserva y BUD-10 son las modificaciones), que consume las certificaciones VIGENTES.
