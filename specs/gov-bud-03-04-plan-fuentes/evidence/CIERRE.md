# CIERRE · BUD-03 + BUD-04 (2026-11-14)

```text
ENTRY=13fa797  CODE=4fb1b60  MERGE=ea8f397 (con origin/develop 5b7e1b9, P2 Spec 015, sin ficheros comunes)
ALEMBIC_HEAD=0108_gov_bud03_04_plan_fuentes (sobre 0107_gov_bud01_ejercicio)
BUD-03=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   BUD-04=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)
GOV-BUD-003/004/005=PASS   SECOND_PROGRAMMATIC_TREE=0   HARDCODED_OFFICIAL_CODES=0   BUD-05 NO INICIADO
GOV_GATES 309 -> 329 / 1273   OWNER_UAT_READY 29 -> 32 / 122 (catálogo)   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=10/11 (tope ampliado por la dueña)   USD 0,0858   CLAUDE_SEMANTIC_*_WRITTEN=0
SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0  EGRESS_CHECK_COMPLETE=1
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG enfocada BUD-03/04 + BUD-01 | 23/23 |
| PG completa con analizador (antes del merge) | 5420 passed / 36 failed / 18 skipped |
| PG tras el merge (BUD-03/04, Spec 015, catálogo, cabezas) | 31/31 |
| mypy | 157 = entrada |
| ruff (gobierno y pruebas tocadas) | limpio |
| Vitest con Node 22 | 1991/1991 (+6); tras el merge, módulos tocados 33/33 |
| tsc (también tras el merge), eslint, build | limpios |
| E2E gobierno-presupuesto-plan-fuentes (sin reintentos) | 1/1, y 4/4 con `--repeat-each=2 --workers=4` junto a BUD-01/02 |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en base nueva | upgrade, downgrade a 0107 y upgrade; una sola cabeza |

**Los 36 rojos de la PG completa** son los mismos de la entrada, NEW_BACKEND_FAILURES=0:

- 30 de pg_dump por entorno (QA_PGDUMP_ENV_DEBT).
- 6 ajenos: integridad_runner (control con violaciones −5), n10 (`import_*.created_by`), naive_datetime (contrataciones `abierta_en`), spec019 ×2 y pip check.

Los 6 se reprodujeron igual en un worktree de 13fa797.

## UAT

- Pila sin Docker desde el HEAD publicado ea8f397, frontend en el puerto 16073.
- Las pilas 15873 y 15973 siguen vivas.
- Credenciales: no se registran.

## Decisiones de diseño (Claude, no materiales)

PDD-B34-01..04 en el plan:

- responsable = unidad ORG-02;
- fuentes por ejercicio;
- partidas de EGRESO opcionales en la restricción;
- el plan no se exige para aprobar.

## Pendiente

- «Impedir créditos huérfanos» (GOV-BUD-004) queda como contrato para BUD-05.
- Siguiente ciclo propuesto: BUD-05, créditos por categoría, partida y fuente.
