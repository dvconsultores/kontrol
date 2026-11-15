# CIERRE · CNT-01 contrato u orden derivada de la adjudicación (2026-11-15)

```text
ENTRY=efcf4b2  CODE=681479f  MERGE=ae46fee (P1 publicó BUD-08: 6da5b20, 91e0fce)
ALEMBIC: 0112 -> 0113_gov_bud08_compromiso (P1) -> 0114_gov_cnt01_contratos   ALEMBIC_HEAD_COUNT=1
  (la migración de CNT-01 nació como 0113 y se reencadenó como 0114 en el merge, sin cambiar su contenido)
CNT-01=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   GOV-CNT-001 PASS
CANONICAL_GATE_UNIVERSE=1342   N/A 73   APLICABLES 1269   GATES_REMOVED=0
GOV_GATES_PASSED 369 (tras BUD-08) -> 379   OWNER_UAT_READY 36 -> 37 de 122   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=9 (tope 8; la 9.ª la autorizó la dueña, solo este ciclo)   RETRIES=6   USD 0,092031
BUDGET_FINANCIAL_EFFECT=0  AUTOMATIC_CURRENCY_CONVERSION=0  CNT02..08_IMPLEMENTED=0
CLAUDE_SEMANTIC_*_WRITTEN=0   SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG `test_gov_cnt01_contratos` (vectores A–I, inmutabilidad en base, permisos, MFA y CTL-01) | 13/13, 121 aserciones |
| Mutaciones M1–M5 sobre `service_contratos.py` | 5/5 muertas; huella restaurada |
| PG dirigida antes del merge (PROC-06/08/10, BUD-06, AAL, recuentos y cabezas) | 254 passed |
| PG completa antes del merge, con analizador | solo los 4 rojos de la línea base (n10 `import_*`, naive_datetime, spec019 ×2); 0 esquemas `t_*` huérfanos |
| PG afectada tras el merge (CNT-01, BUD-08, BUD-06, AAL, recuentos, cabezas, n10) | 202 passed; 1 rojo de la línea base (n10, solo `import_*`) |
| PG completa tras el merge, con analizador | 5556 passed / 4 failed / 18 skipped. Los 4 rojos son los de la línea base (n10 solo `import_*.created_by`, naive_datetime en `evaluacion/aperturas`, spec019 ×2); NEW_BACKEND_FAILURES=0; esquemas 388/388 soltados, 0 huérfanos |
| ruff | limpio |
| mypy (`app`) | 157, igual que a la entrada |
| Vitest con Node 22 | 2050/2050 tras el merge. `AsyncButton` falló una vez bajo carga; aislado pasó 3/3 y la suite siguiente, 2044/2044 |
| tsc, eslint, build | limpios |
| E2E `gobierno-contratos` (sin reintentos) | 1/1: recorrido, negativas, Axe y 1280/390/320 |
| Regresión E2E de Gobierno (19 specs, 1 worker) | 38/39. El rojo era PROC-08, que buscaba el párrafo retirado por CNT-01; se corrigió en la llamada 9 → decisión y contratos 2/2 |
| E2E del árbol fusionado (contratos, decisión, compromiso BUD-08 y certificación BUD-06) | 4/4, limpieza LIMPIA |
| Alembic | upgrade, downgrade y upgrade en base nueva; tras el merge, cadena 0112 → 0113 → 0114 en PG y en la UAT; una sola cabeza |

## UAT

- Pila de P2: backend en 8000 y web en 5173, base `kuat` migrada de 0112 a 0114. HTTP 200 en `/docs` y en la web.
- Humo `gobierno-contratos.spec.ts` contra la UAT: 1/1 en 3,4 min. OWNER_UAT_ACCESSIBLE=YES.
- Credenciales: no se registran.
- Tarjeta: `OWNER_UAT_CARD.md` (14 pasos).

## Observaciones abiertas

- **OBS-CNT01-BUD08-01** (decisión de la dueña). BUD-08 llegó durante el ciclo: los compromisos consumen CDP, con situación DISPONIBLE, PARCIALMENTE_CONSUMIDA o AGOTADA. CNT-01 sigue calculando el saldo libre como el monto de la CDP menos las asignaciones de otros contratos, sin restar lo consumido por compromisos. No se cambió, porque la frontera fijada era `CNT01_REQUIRES_BUD08=0`. Para el ciclo de integración CNT-01 ↔ BUD-08 hay que decidir:
  - si la cobertura del contrato usa el remanente de BUD-08;
  - si el compromiso debe nacer del contrato formalizado.
- OQ-CNT01-01 (disponibilidad parcial y contratos plurianuales).
- OQ-CNT01-02 (VES/VED).
- OBS-CNT01-SOD-01, OBS-CNT01-PROC08-01 y OBS-CNT01-PLAZO-01: ver `spec.md`.

## Siguiente

CNT-04 (supervisor o administrador del contrato) o CNT-02 (adendas), sobre el contrato FORMALIZADO. Antes, o junto con ellos, conviene decidir OBS-CNT01-BUD08-01.
