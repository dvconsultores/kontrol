# CTL-07 · Cierre del ciclo (P2, Gobierno)

- **Fecha:** 2026-11-14.
- **Entrada:** `9566303`, igual a `origin/develop` y al merge-base.
- **Alembic:** de `0108_gov_bud03_04_plan_fuentes` a `0109_gov_ctl07_alertas`, con una sola cabeza.
- **P1 (BUD-05):** no publicó nada durante el ciclo. Tras el `git fetch`, `origin/develop` sigue en `9566303`, así que no hubo fusión ni hubo que reencadenar la migración.

## Puertas de producto

| Puerta | Estado | Evidencia |
|---|---|---|
| BACKEND | PASS | `service_alertas.py`, `api_alertas.py` y `schemas_alertas.py`. 12/12 pruebas dirigidas en PostgreSQL |
| DATABASE | PASS | Tabla `gov_atypical_alert_reviews` con UNIQUE(company_id, clave), CHECK y disparadores de inmutabilidad. En una base nueva, Alembic hace upgrade, downgrade y upgrade sin errores. La paridad n10 no tiene diferencias nuevas |
| API | PASS | `GET /gobierno/control/alertas` y `POST /gobierno/control/alertas/revisiones`. Fixture OpenAPI regenerada solo con adiciones |
| FRONTEND | PASS | `AlertasAtipicasPage.tsx`; Vitest 8/8 |
| MENU | PASS | Gobierno › Alertas de operaciones atípicas |
| PROCESS | PASS | Detectar → revisar → seguir como hallazgo (CTL-06) |
| FIELDS | PASS | Resultado, observación de 10 caracteres o más, filtros por tipo y estado |
| ROLES | PASS | Permisos `gobierno_alertas:view` (STANDARD) y `review` (SENSITIVE, con MFA), concedidos a FUNCIONAL_COMPLETO. Un usuario no puede revisar una alerta de la que es sujeto |
| DOCUMENT | NOT_APPLICABLE | La revisión no genera documento: el requisito pide una señal y una revisión, no un acto |
| REPORTING | PASS | Tabla «Tipos de alerta» con el total y las pendientes de cada tipo, más los filtros |
| AUDIT | PASS | Evento `GOV_ATYPICAL_ALERT_REVIEWED` en el catálogo (524 entradas) |
| SECURITY | PASS | 422/404/409 sin escritura; documentos enmascarados; sin UUID en los sujetos; prueba de permisos |
| ISOLATION | PASS | `test_aislamiento_entre_empresas`. La mutación que quita el filtro de empresa muere |
| CONCURRENCY | PASS | `test_carrera_de_revisiones`: exactamente una 201 y el resto 409 |
| SCREEN | PASS | `SCREEN_CONTRACT.md` |
| E2E | PASS | `gobierno-alertas.spec.ts`, con el conflicto real de PROC-11. Regresión E2E de Gobierno: 9/9 |
| RESPONSIVE | PASS | 1280, 390 y 320 sin desplazamiento horizontal |
| ACCESSIBILITY | PASS | Axe en los 3 anchos: `AXE_NEW_SERIOUS=0` |
| OWNER_UAT_READY | YES | `OWNER_UAT_CARD.md` |

## QA final

| Comprobación | Resultado |
|---|---|
| PostgreSQL completo, línea base (export de `9566303`, base `ktestbase`) | Corrió entre las 23:36 y las 01:56, en la franja de 20:00 a 24:00 de GOV-TEST-UTC-DATE: 52 fallos, de los cuales 48 son de Gobierno por «La vigencia no puede empezar antes de hoy». Los 48 se repitieron fuera de la franja y pasaron todos: 46 en la repetición aislada; las 2 de doc02 fallaron ahí por depender del orden y pasaron con su módulo completo (36/36) |
| `ENTRY_PG_FAILURES` (fuera de la franja) | **4**: n10, naive_datetime y spec019_receipt ×2 |
| PostgreSQL completo, final (árbol del ciclo, base `ktest`, de 00:15 a 02:34, fuera de la franja) | 5508 pruebas: 5485 pasan, 5 fallan y 18 se saltan. Los 5 son los 4 de la base más `test_mfa_g00b_recuentos` |
| Corrección del fallo nuevo | `test_mfa_g00b_recuentos` contaba 69 y 75 permisos. Lo corrigió DeepSeek en la llamada Y (OWNER_EXCEPTION). `test_mfa_policy.py` pasa 95/95 |
| `FINAL_PG_FAILURES` | **4**, los mismos de la base. `NEW_BACKEND_FAILURES=0` |
| Ruff | Limpio |
| mypy | 157 errores, igual que la línea base |
| Vitest (Node v22.23.4) | 2008/2008 |
| Typecheck, lint y build | Limpios y OK |
| E2E | `gobierno-alertas` PASS y regresión de Gobierno 9/9: `NEW_E2E_FAILURES=0` |
| Mutaciones | 2 de 2 mueren: sin autorrevisión y sin filtro de empresa |

`GOV_TEST_UTC_DATE`: se reprodujo en la línea base dentro de la franja. Es externa a CTL-07 y no es una puerta de este ciclo.

## Deudas declaradas (no absorbidas)

- **GOV-AUDIT-PROCESS-LABELS.** La bitácora muestra el código «gov-ctl-07» en lugar del nombre del proceso, igual que en BUD-01..04.
- **GATE-UNIVERSE-BUD02-REPORTS.** El universo bajó de 1275 a 1273 en `f100c34` (P1), porque REPORTS pasó de FAIL a N/A en BUD-02 y BUD-04. Lo decide la dueña.
- **Fraccionamiento y override frecuente:** no disponibles (OBS-PROC08-MONTO-01, N38 y la ausencia de excepciones a la SoD).

## DeepSeek

10 llamadas a `deepseek-v4-pro`: las 8 del tope y 2 OWNER_EXCEPTION. 4 reintentos. Coste total: $0,053141. El detalle está en `ATTEMPT_LOG.md`.

`CLAUDE_SEMANTIC_CODE_WRITTEN=0 CLAUDE_SEMANTIC_TESTS_WRITTEN=0 CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0 CLAUDE_SEMANTIC_QA_WRITTEN=0`

`OWNER_ACCEPTED`: NO.
