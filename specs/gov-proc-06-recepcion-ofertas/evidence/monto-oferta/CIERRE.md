# OMA · Cierre del ciclo (P2, Gobierno)

- **Fecha:** 2026-11-14.
- **Entrada:** `fbc8235`, igual a `origin/develop`.
- **Alembic:** de `0109_gov_ctl07_alertas` a `0110_gov_proc06_monto_oferta`, con una sola cabeza.
- **Ruta:** B, habilitada por `OQ-PROC09-01 = A`. BUD-05 no estaba publicado, así que la ruta A no aplicaba.
- **P1 (BUD-05):** no publicó nada durante el ciclo. Tras el `git fetch`, `origin/develop` sigue en `fbc8235`: no hubo fusión ni hubo que reencadenar la migración.

## Puertas de producto

| Puerta | Estado | Evidencia |
|---|---|---|
| BACKEND | PASS | `service_ofertas_montos.py` y los consumidores PROC-10, REP-03 y PROC-08. 13/13 pruebas dirigidas en PostgreSQL |
| DATABASE | PASS | Tabla `gov_procurement_offer_amounts`, de solo inserción, con disparadores de inmutabilidad, 2 UNIQUE y 7 CHECK. En una base nueva, Alembic hace upgrade, downgrade y upgrade sin errores. La paridad n10 no tiene diferencias nuevas |
| API | PASS | `POST /gobierno/expedientes/{id}/ofertas/{oferta_id}/montos`. El monto también se expone en la ficha de la oferta, en la decisión y en el reporte. Fixture OpenAPI regenerada solo con adiciones |
| FRONTEND | PASS | `OfertaMonto.tsx` en la ficha de la oferta, la columna en la decisión y la tabla por moneda en REP-03. Vitest dirigido en verde |
| MENU | PASS | Gobierno › Expedientes de contratación › Ofertas › Ver detalle › Monto declarado |
| PROCESS | PASS | Recibir → (abrir si está sellada) → declarar → corregir con motivo → concluir la evaluación (cierre) → consumidores |
| FIELDS | PASS | Moneda, monto sin IVA, tributos, total con tributos, soporte y motivo (corrección) |
| ROLES | PASS | `gobierno_ofertas:amount` (SENSITIVE, con MFA), concedido a FUNCIONAL_COMPLETO |
| DOCUMENT | PASS | Soporte obligatorio: documento de la oferta, con versión y huella, o el acta de apertura |
| REPORTING | PASS | REP-03 «Monto» por moneda, también en el CSV |
| AUDIT | PASS | `GOV_PROCUREMENT_OFFER_AMOUNT_DECLARED` y `..._CORRECTED` (catálogo de 526 entradas) y la cronología, ambas sin importes |
| SECURITY | PASS | Sellada → 409 hasta la apertura; 422 por moneda, soporte o importe inválido; 404 para otro ente |
| ISOLATION | PASS | Prueba de aislamiento entre empresas |
| CONCURRENCY | PASS | Carrera de declaraciones: exactamente una 201 y el resto 409 |
| SCREEN | PASS | `SCREEN_CONTRACT.md` |
| E2E | PASS | `gobierno-monto-oferta.spec.ts` y REP-03 |
| RESPONSIVE | PASS | 1280, 390 y 320 sin desplazamiento horizontal |
| ACCESSIBILITY | PASS | Axe en los 3 anchos: `AXE_NEW_SERIOUS=0` |
| OWNER_UAT_READY | YES | `OWNER_UAT_CARD.md` y el humo autenticado en la UAT (ver más abajo) |

## QA final

| Comprobación | Resultado |
|---|---|
| `ENTRY_PG_FAILURES` | **4**, tomados de la corrida final de CTL-07 (mismo código que `fbc8235`): n10, naive_datetime y spec019_receipt ×2 |
| PostgreSQL completo, final (base `ktest`, de 08:33 a 10:40 de Caracas, fuera de la franja de GOV-TEST-UTC-DATE) | 5521 pruebas: 5499 pasan, 4 fallan y 18 se saltan. Los 4 son los de la base. No quedan esquemas `t_*` huérfanos |
| `NEW_BACKEND_FAILURES` | 0 |
| Ruff | Limpio |
| mypy | 157 errores, igual que la línea base |
| Vitest (Node v22.23.4) | 2015/2015 |
| Typecheck, lint y build | Limpios y OK |
| E2E dirigida | Monto y REP-03: 2/2 sin reintentos |
| Regresión E2E de Gobierno | ofertas, evaluación, decisión, garantías, reporte, monto, alertas, expedientes, comisiones y actos: **18/18**, 0 reintentos, limpieza LIMPIA. `NEW_E2E_FAILURES=0` |
| Mutaciones | 3 de 3 mueren: sin el control del sello, documento sellado como soporte y límite de la evaluación. Se restauraron con la misma huella |

`GOV_TEST_UTC_DATE`: `NOT_MEASURED_THIS_CYCLE`. La suite corrió fuera de la franja y no es una puerta.

## Métricas

`COMPLETE_GATES_BEFORE=339`, `COMPLETE_GATES_AFTER=339`. Gobierno sigue en 33/122 en `OWNER_UAT_READY`.

El ciclo cierra una dependencia de dominio, la del monto, dentro de PROC-06. No cierra una fila nueva de la matriz: PROC-09 sigue BLOCKED (0/10) y PROC-08 y PROC-10 no cambian de estado. `GATE_UNIVERSE_STATUS=PENDING_OWNER_RATIFICATION`.

## Deudas declaradas (no absorbidas)

- **OQ-OMA-01** (dueña): la regla para comparar el monto con `limit_amount`. Hasta entonces, PROC-08 no valida límites.
- **OQ-OMA-02** (jurídica): si la base del porcentaje incluye los tributos. Hasta entonces, PROC-10 evalúa por bandas.
- **OQ-PROC09-02..04:** PROC-09 sigue bloqueado.
- **OBS-PROC08-PARCIAL-01:** la adjudicación parcial.
- **GOV-AUDIT-PROCESS-LABELS** y **GATE-UNIVERSE-BUD02-REPORTS**, sin cambios.

## DeepSeek

8 llamadas a `deepseek-v4-pro` (el tope), con 6 reintentos y sin excepciones de la dueña. Coste total: $0,079350. El detalle está en `ATTEMPT_LOG.md`.

`CLAUDE_SEMANTIC_CODE_WRITTEN=0 CLAUDE_SEMANTIC_TESTS_WRITTEN=0 CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0 CLAUDE_SEMANTIC_QA_WRITTEN=0`

`OWNER_ACCEPTED`: NO.

## UAT de P2 (pila propia; la de P1 no se tocó)

- **Commit publicado:** `a7740c6`, igual a `origin/develop`.
- **Base de datos:** la base UAT `kuat` se migró de `0109` a `0110_gov_proc06_monto_oferta`, que ya es la cabeza.
- **Servicios:** backend en `127.0.0.1:8000` (`/docs` responde 200) y web en `127.0.0.1:5173` (responde 200).
- **Humo autenticado** a las 11:01 de Caracas: `gobierno-monto-oferta.spec.ts` contra la UAT, con un usuario real, MFA y la base `kuat`, pasó (1 prueba en 1,6 min).
- **Tarjeta de la dueña:** `OWNER_UAT_CARD.md`. `OWNER_UAT_ACCESSIBLE=YES`.
