# CIERRE · CNT-01 contrato u orden derivada de la adjudicación (2026-11-15)

```text
ENTRY=efcf4b2  CODE=681479f  MERGE_1=ae46fee (P1 BUD-08: 6da5b20, 91e0fce)  FIX=downgrade (llamada 10)  MERGE_2 (P1 TRE-09: 05d3ea7, 945bec7)
ALEMBIC: 0112 -> 0113_gov_bud08_compromiso (P1) -> 0114_gov_tre09_tasas (P1) -> 0115_gov_cnt01_contratos   ALEMBIC_HEAD_COUNT=1
  (la migración de CNT-01 nació como 0113 y se reencadenó dos veces, sin cambiar su contenido; solo el downgrade de permisos se corrigió en la llamada 10)
CNT-01=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   GOV-CNT-001 PASS
CANONICAL_GATE_UNIVERSE=1342   N/A 73   APLICABLES 1269   GATES_REMOVED=0
GOV_GATES_PASSED 379 (tras BUD-08 y TRE-09) -> 389   OWNER_UAT_READY 37 -> 38 de 122   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=10 (tope 8; la 9.ª y la 10.ª, autorizadas por la dueña)   RETRIES=6   USD 0,092703
BUDGET_FINANCIAL_EFFECT=0  AUTOMATIC_CURRENCY_CONVERSION=0  CNT02..08_IMPLEMENTED=0
CLAUDE_SEMANTIC_*_WRITTEN=0   SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG `test_gov_cnt01_contratos` (vectores A–I, inmutabilidad en base, permisos, MFA y CTL-01) | 13/13, 121 aserciones |
| Mutaciones M1–M5 sobre `service_contratos.py` | 5/5 muertas; huella restaurada |
| PG dirigida antes de los merges (PROC-06/08/10, BUD-06, AAL, recuentos y cabezas) | 254 passed |
| PG completa antes de los merges, con analizador | solo los 4 rojos de la línea base; 0 esquemas `t_*` huérfanos |
| PG completa tras el merge con BUD-08, con analizador | 5556 passed / 4 failed / 18 skipped. Los 4 rojos son los de la línea base (n10 solo `import_*.created_by`, naive_datetime en `evaluacion/aperturas`, spec019 ×2); NEW_BACKEND_FAILURES=0; esquemas 388/388 soltados |
| PG afectada tras el merge con TRE-09 (CNT-01, TRE-09, BUD-08, BUD-06, PROC-08, recuentos 548/172/75/80, cabezas, n9 y fixtures) | 306/306 |
| Alembic tras la llamada 10 (base nueva, rol extra con los 3 permisos) | up → down (asignaciones y permisos a 0) → up; una sola cabeza, 0115 |
| ruff | limpio |
| mypy (`app`) | 157, igual que a la entrada |
| Vitest con Node 22 | 2061/2061 tras el merge con TRE-09. `AsyncButton` (fichero sin cambios desde 788eb48) falla de forma intermitente bajo carga; pasa al repetirlo |
| tsc, eslint, build | limpios |
| E2E `gobierno-contratos` (sin reintentos) | 1/1: recorrido, negativas, Axe y 1280/390/320 |
| Regresión E2E de Gobierno (19 specs, 1 worker) | 38/39. El rojo era PROC-08, que buscaba el párrafo retirado por CNT-01; se corrigió en la llamada 9 → decisión y contratos 2/2 |
| E2E tras el merge con BUD-08 (contratos, decisión, compromiso y certificación) | 4/4, limpieza LIMPIA |
| E2E tras el merge con TRE-09 (contratos, decisión, compromiso, certificación y tasas oficiales) | 5/5, limpieza LIMPIA |

## UAT

- Pila de P2: backend en 8000 y web en 5173.
- La base `kuat` no pudo bajar de la 0114 local a la 0113, porque los eventos CONTRATO del humo violan el CHECK antiguo. Los downgrades hermanos (0088, 0092, 0094 y 0096) tampoco purgan eventos. Se reconstruyó con `rehacer_pg.sh` (esquema solo con Alembic y datos sintéticos) en la cabeza 0115.
- `kuat` en 0115_gov_cnt01_contratos, con ALEMBIC_RC=0 y SEED_RC=0. Licencia VALID. HTTP 200 en `/docs` y en la web.
- Humo `gobierno-contratos.spec.ts` contra la UAT: 1/1 en 3,4 min (desde 644650a). OWNER_UAT_ACCESSIBLE=YES.
- Credenciales: no se registran.
- Tarjeta: `OWNER_UAT_CARD.md` (14 pasos).

## Observaciones abiertas

- **OBS-CNT01-BUD08-01** (decisión de la dueña). Los compromisos de BUD-08 consumen la CDP, pero el saldo libre de CNT-01 no resta ese consumo. Hay que decidir si la cobertura usa el remanente y si el compromiso nace del contrato.
- **OBS-CNT01-TRE09-01** (decisión de la dueña). TRE-09 normaliza VED → VES, y las CDP nuevas salen en VES. CNT-01 compara las monedas literalmente. Hay que decidir si adopta `canonical_currency` para las CDP antiguas en VED. La conversión por tasa sigue prohibida en CNT-01.
- OQ-CNT01-01 (cobertura parcial y plurianual), y OQ-CNT01-02, que TRE-09 resuelve en parte.
- OBS-CNT01-SOD-01, OBS-CNT01-PROC08-01 y OBS-CNT01-PLAZO-01: ver `spec.md`.

## Siguiente

CNT-04 (supervisor o administrador del contrato) o CNT-02 (adendas), sobre el contrato FORMALIZADO. Conviene decidir antes OBS-CNT01-BUD08-01 y OBS-CNT01-TRE09-01.
