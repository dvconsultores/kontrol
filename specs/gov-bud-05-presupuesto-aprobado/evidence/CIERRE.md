# CIERRE · BUD-05 presupuesto aprobado (2026-11-14)

```text
ENTRY=f100c34  CODE=a78f49b  MERGE=f1aef28 (con origin/develop f6fce8d: P2 CTL-07, PROC-06 OMA, Spec 021)
ALEMBIC: 0108 -> 0109_gov_ctl07_alertas (P2) -> 0110_gov_proc06_monto_oferta (P2) -> 0111_gov_bud05_aprobado   ALEMBIC_HEAD_COUNT=1
BUD-05=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE; alcance v1 de D-GOV-02 = A)   GOV-BUD-008 PASS · GOV-BUD-007 PARTIAL · GOV-BUD-006 LATER_PHASE
CANONICAL_GATE_UNIVERSE=1342 (antes y después)   N/A 69 -> 70 (REPORTS de BUD-05)   APLICABLES 1273 -> 1272   GATES_REMOVED=0
GOV_GATES_PASSED 329 -> 339 (BUD-05) -> 349 tras el merge (CTL-07 de P2)   OWNER_UAT_READY 32 -> 33 (BUD-05) -> 34 (CTL-07)   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=13 (tope 8; ampliaciones de la dueña a 10, 11, 12 y 13; una llamada sin respuesta por timeout)   USD 0,0757
CLAUDE_SEMANTIC_*_WRITTEN=0   SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG enfocada (BUD-05, BUD-01..04, catálogo, cabezas) | 80/80 antes del merge |
| PG completa con analizador, una vez (antes del merge) | 5439 passed / 36 failed / 18 skipped |
| PG tras el merge (presupuesto, P2, catálogo, cabezas, n10, integridad) | 255 passed / 2 failed: los de la línea base |
| mypy | 157, igual que a la entrada (antes y después del merge) |
| ruff | limpio |
| Vitest con Node 22 | 1999/1999 antes del merge (+8); 2021/2021 tras el merge |
| tsc, eslint, build | limpios |
| E2E gobierno-presupuesto-aprobado (sin reintentos) | 1/1 |
| E2E de las tres de presupuesto con `--repeat-each=2 --workers=4` | 6/6 |
| E2E tras el merge (presupuesto + E2E de P2) | 12/13. El fallo, importaciones.spec.ts (Enterprise), falla igual en un worktree de f6fce8d |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en base nueva | upgrade, downgrade a 0110 y upgrade; una sola cabeza |
| Fixtures OpenAPI | regenerados con `qa/fixtures_de_frontend.py`; contratos de frontend 452/452 |
| Humo UAT | 1/1 |

**Los 36 rojos de la PG completa** son los mismos de la entrada: 30 de pg_dump y 6 ajenos (integridad −5, n10 import_*, naive_datetime de contrataciones, spec019 ×2 y pip check). Ya estaban atribuidos en un worktree de la base. NEW_BACKEND_FAILURES=0.

## UAT

- Pila sin Docker desde el HEAD publicado f1aef28: frontend en el puerto 16173 (backend 19000, central 19010).
- Siguen vivas las pilas 15873, 15973 y 16073.
- Credenciales: no se registran.

## Decisiones

**De la dueña:**
- OD-BUD05-01 = A: aprobado completo (ingresos y créditos) con cuadre LOPPM 240.
- OD-BUD05-02: holgura del Tesoro declarada con certificación.

**De diseño, de Claude:** PDD-B05-01..07, en el plan.

## Pendiente

- Formulación (GOV-BUD-006, anteproyecto y proyecto): LATER_PHASE por D-GOV-02 A. Necesitará N08 y N37.
- Siguiente en la cadena de dependencias: BUD-06, disponibilidad y certificación (GOV-BUD-009/010).
