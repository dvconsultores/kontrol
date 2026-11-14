# AAL · Cierre del ciclo (P2, Gobierno)

- **Fecha:** 2026-11-14.
- **Entrada:** `f6fce8d`, igual a `origin/develop`. Alembic en `0110_gov_proc06_monto_oferta`.
- **Decisión de la dueña:** `OQ-OMA-01 = BLOCK_WITH_DECLARED_TOTAL_SAME_CURRENCY`. Sustituye a PDD-PROC08-13 («el límite no se valida»).
- **Migración:** ninguna. No hay tabla nueva ni segundo motor. El límite se lee de la competencia del cargo (ORG-03/04) en la fecha del acto.
- **Integración con P1:** durante el ciclo P1 publicó BUD-05 (`0111`) y BUD-06 (`0112`). Hubo dos fusiones ordinarias, `cd4850a` y `f6c3dbc`.
  - **Conflicto:** en las dos, solo el recuento del catálogo de auditoría: 535 y después **537**, que es 536 de P1 más `GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED`.
  - **Alembic:** una sola cabeza, `0112_gov_bud06_certificacion`.

## Regla aplicada

| Caso | Resultado |
|---|---|
| Resultado distinto de ADJUDICADA (DESIERTA, TERMINADA, NULIDAD) | No se compara nada |
| Competencia APROBAR × CONTRATACIONES con `SIN_LIMITE` | Pasa |
| `MONTO`, misma moneda, total con tributos ≤ límite | Pasa (`Decimal`, sin redondeo) |
| `MONTO`, misma moneda, total > límite | 409 `GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED` |
| `MONTO`, otra moneda | 409 `GOV_DECISION_AUTHORITY_CURRENCY_MISMATCH`, sin conversión |
| `MONTO` y una oferta antigua sin monto | 409 `GOV_DECISION_OFFER_AMOUNT_REQUIRED` |
| Override | No existe: no hay campo ni permiso |

## Puertas de producto

| Puerta | Estado | Evidencia |
|---|---|---|
| BACKEND | PASS | `service_decision_limite.py`, más la llamada en `registrar_decision` y la vista previa en `actos_elegibles[].control_monto`. 12/12 pruebas nuevas en PostgreSQL |
| DATABASE | PASS (sin cambios) | `MIGRATION_REQUIRED=0` |
| API | PASS | Mismo `POST` de la decisión: 409 con `details` y vista previa en el `GET` del expediente. La fixture OpenAPI no cambia de rutas |
| FRONTEND | PASS | `ControlLimiteAutoridad.tsx` en el formulario de decisión; Vitest 3/3 |
| MENU | PASS | Gobierno › Expedientes de contratación › expediente › Decisión |
| PROCESS | PASS | Elegir acto y «Adjudicada» → panel → confirmar → el backend recalcula con bloqueo → 409 o 201 |
| FIELDS | PASS | Monto, moneda, autoridad efectiva, límite y resultado (5 estados), sin UUID |
| ROLES | PASS | `gobierno_decision:decide`, el mismo de antes, con MFA |
| DOCUMENT | NOT_APPLICABLE | Usa el soporte del monto de PROC-06 |
| REPORTING | NOT_APPLICABLE | Sin reporte propio |
| AUDIT | PASS | `GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED` (SECURITY/REJECTION), con acto, oferta, causal y resultado, sin importes |
| SECURITY | PASS | El backend es la autoridad; el botón no decide |
| CONCURRENCY | PASS | Expediente y estructura con `FOR UPDATE`; T8, T9 y T10; la mutación M3 muere |
| SCREEN | PASS | `SCREEN_CONTRACT.md` |
| E2E | PASS | `gobierno-decision.spec.ts`: bloqueo, Cancelar, autoridad sin límite y adjudicación |
| RESPONSIVE | PASS | 1280, 390 y 320 sin desplazamiento horizontal |
| ACCESSIBILITY | PASS | Axe sobre el panel: `AXE_NEW_SERIOUS=0` |
| OWNER_UAT_READY | YES | `OWNER_UAT_CARD.md` y el humo autenticado en la UAT |

## QA final

| Comprobación | Resultado |
|---|---|
| `ENTRY_PG_FAILURES` | 4: n10, naive_datetime y spec019_receipt ×2 |
| PostgreSQL completo (base `ktest`, de 12:04 a 14:13, antes de fusionar) | 5533 pruebas: 5511 pasan, 18 se saltan y fallan 4, los de la base. No quedan esquemas `t_*` |
| `NEW_BACKEND_FAILURES` | 0 |
| Dirigidas tras la fusión con BUD-05 | 91/91: BUD-05, PROC-08 (límite, decisión y recomendación), PROC-10, REP-03 y catálogo |
| Dirigidas tras la fusión con BUD-06 | 187/187: catálogo, BUD-06, límite, decisión, MFA y techo de delegación |
| Ruff | Limpio |
| mypy | 157 errores, igual que la base |
| Vitest (Node v22.23.4) | 2030/2030 sobre el árbol final |
| Typecheck, lint y build | Limpios y OK sobre el árbol final |
| OpenAPI | Las fixtures regeneradas no cambian (`OPENAPI_DIFF=0`) |
| Alembic | 1 cabeza (`0112`). El ciclo no añade revisión |
| E2E dirigida | Decisión, garantías, monto y REP-03: 4/4, 0 reintentos |
| Regresión E2E de Gobierno (1 worker, tras la fusión con BUD-05) | ofertas, evaluación, decisión, garantías, reporte, monto, alertas, expedientes, comisiones, actos y presupuesto aprobado: **19/19**, 0 reintentos, limpieza LIMPIA. `NEW_E2E_FAILURES=0` |
| Mutaciones | 4 de 4 mueren (ver `ATTEMPT_LOG.md`). Restauradas con la misma huella |

**Corrida descartada.** Una corrida de todo `gobierno-*` con 6 workers no vale como evidencia: 85 de 88 fallaron en la preparación, con timeout de 15 s al subir documentos al analizador real. Es saturación del anfitrión, no un fallo de producto, y se repitió con 1 worker. Queda anotada como `GOV-E2E-PARALLEL-ANALYZER-TIMEOUT`: observación de entorno, no deuda del ciclo.

## Métricas

`OWNER_UAT_READY` de Gobierno: 33 → 35 de 122. Los 2 de diferencia son BUD-05 y BUD-06 de P1; este ciclo no suma filas. Puertas en PASS: 339 → 359 de 1271, también por P1.

AAL cierra una brecha funcional dentro de PROC-08, que ya era `OWNER_UAT_READY`: `FUNCTIONAL_GAP_CLOSED=1`, `PROCESS_ROW_COUNT_CHANGE=0`. `GATE_UNIVERSE_STATUS=PENDING_OWNER_RATIFICATION`.

## Deudas declaradas (no absorbidas)

- **OBS-PROC08-PARCIAL-01:** adjudicación parcial (OPEN).
- **OQ-OMA-02** (jurídica): base del porcentaje de las garantías (OPEN).
- **PROC-09:** sigue BLOCKED.
- **Conversión de moneda:** necesita TRE-09, la procedencia de las tasas.
- **GOV-AUDIT-PROCESS-LABELS** y **GATE-UNIVERSE-BUD02-REPORTS**, sin cambios.

## DeepSeek

- **Uso:** 5 llamadas a `deepseek-v4-pro`, con 2 reintentos y sin excepciones de la dueña.
- **Coste:** $0,022290.
- **Detalle:** en `ATTEMPT_LOG.md`.

`CLAUDE_SEMANTIC_CODE_WRITTEN=0 CLAUDE_SEMANTIC_TESTS_WRITTEN=0 CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0 CLAUDE_SEMANTIC_QA_WRITTEN=0`

`OWNER_ACCEPTED`: NO.

## UAT de P2 (pila propia; la de P1 no se tocó)

- **Commit publicado:** `f6c3dbc`, igual a `origin/develop`.
- **Base de datos:** `kuat` se migró de `0110` a `0112_gov_bud06_certificacion`, que es la cabeza. Es la base de UAT de P2, con datos sintéticos.
- **Servicios:**
  - backend en `127.0.0.1:8000`, `/docs` responde 200;
  - web en `127.0.0.1:5173`, responde 200.
- **Humo autenticado** de 15:29 a 15:31 (Caracas): `gobierno-decision.spec.ts` contra la UAT, con usuario real, MFA y la base `kuat`. **1 prueba pasada en 2,2 min.**
  - Autoridad insuficiente: Excede el límite → 409 → sin DEC-01.
  - Autoridad suficiente: Sin límite → DEC-01 Adjudicada.
- **Tarjeta de la dueña:** `OWNER_UAT_CARD.md`. `OWNER_UAT_ACCESSIBLE=YES`.
