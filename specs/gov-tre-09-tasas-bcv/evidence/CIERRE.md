# CIERRE · TRE-09 provenance de tasas BCV (2026-11-15)

```text
ENTRY=91e0fce  CODE=<ver commit de publicación> (sin merge: origin/develop no avanzó)
ALEMBIC: 0113_gov_bud08_compromiso -> 0114_gov_tre09_tasas   ALEMBIC_HEAD_COUNT=1
TRE-09=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   GOV-TRE-011 PASS
CANONICAL_GATE_UNIVERSE=1342   N/A 72   APLICABLES 1270   GATES_REMOVED=0
GOV_GATES_PASSED 369 -> 379   OWNER_UAT_READY 36 -> 37 de 122   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=11 (tope 8; 9.ª-12.ª autorizadas por la dueña, usadas 11)   69.758 in / 84.172 out · USD 0,1031
OBS_BUD08_VES_VED=CLOSED  CANONICAL=VES  NEW_GOVERNMENT_VED_WRITES=0  MASS_UPDATE=0  ORG03_NEW_VED_LIMIT_ALLOWED=0
RATE_EFFECTIVE_DATE_SELECTION=APROBADA con max(fecha_efectiva) <= fecha de la operación
PROC08_INTEGRATION=DEFERRED  CNT01_INTEGRATION=DEFERRED  P1_TOUCH_CNT01=0  P1_P2_OVERLAP=0
BUD07/09/10/11/12_IMPLEMENTED=0  CLAUDE_SEMANTIC_*_WRITTEN=0  SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG test_gov_tre09: ciclo de vida, vectores A–J, maker-checker, evidencia, concurrencia real, aislamiento, permisos, inmutabilidad, auditoría, normalización BUD-01/ORG-03 | 12/12 |
| PG test_gov_tre09 + test_gov_bud08 | 25/25, dos corridas |
| PG dirigida (fijaciones, N9, BUD-01/06/08, test_iso_barridos) | 277/277 tras el ajuste esperado del vector G–I de BUD-08 |
| PG completa con analizador, una vez | 5525 passed / 36 failed / 18 skipped (entrada BUD-08: 5510 / 36 tras C9) |
| Fallos nuevos frente a la línea base | 0 (los 36 coinciden uno a uno) |
| mypy | 157, igual que a la entrada |
| ruff | limpio |
| Vitest con Node 22 | 2047/2047 (entrada 2036) |
| tsc, eslint, build | limpios |
| E2E gobierno-tasas-oficiales (sin reintentos) | 1/1 |
| Familia E2E de presupuesto + tasas | 6/6 |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en base nueva | upgrade, downgrade a 0113 y upgrade; una sola cabeza |

## Reglas verificadas

- Convención 1 MONEDA EXTRANJERA = X VES; Decimal, Numeric(28,12), sin float ni redondeo intermedio.
- BORRADOR → APROBADA → SUSTITUIDA / ANULADA; quien captura no aprueba (MAKER_CHECKER); aprobar exige evidencia documental con sha256.
- Corregir crea una versión nueva enlazada (sustituye_id) y no sobrescribe; una sola APROBADA por empresa, moneda y fecha (índice único parcial).
- `gobierno_tasas:approve` es SENSITIVE (MFA); view y manage son estándar.
- BUD-08: si la moneda de la operación difiere de la del límite, se usa la tasa aprobada vigente a la fecha. La comparación se hace en VES exactos y la instantánea queda en `snapshot.autoridad.conversion` (huella y PDF). Sin tasa: 422 GOV_OFFICIAL_RATE_REQUIRED (moneda de la operación, moneda del límite, fecha).
- Concurrencia: aprobar una corrección mientras se compromete re-evalúa la fila bloqueada FOR SHARE; si desaparece, se relee una vez.
- VED se normaliza a VES (factor 1, no es FX) al escribir en BUD-01, BUD-06 y BUD-08; ORG-03 sigue rechazando VED.

## UAT

Pendiente de registrar tras la publicación (ver la sección UAT añadida en el commit de documentación).

## Observaciones abiertas

- OBS-BUD08-VES-VED: **CERRADA** en este ciclo.
- Integración de tasas en PROC-08 y CNT-01: DIFERIDA (CNT-01 pertenece a P2).
- OBS-BUD34-E2E-PARALELO sigue abierta. Es anterior a este ciclo.

## Siguiente

La cadena BUD está bloqueada por fuentes: BUD-07 por N37, BUD-09 por N36 y BUD-10 por N09/N37. Ver el prompt del siguiente ciclo en el informe final.
