# Delta PROC-08 · TRE-09 — límite de autoridad multimoneda en la adjudicación (2026-11-15)

Spec dueña: `specs/gov-proc-08-recomendacion-decision`. Este delta sustituye el bloqueo `MONEDA_DISTINTA` del delta AAL
(`proc08-authority-amount-limit-delta.md`) por la conversión con la tasa oficial aprobada de TRE-09. No crea fila de proceso
(`PROCESS_ROW_COUNT_CHANGE=0`) y cierra la integración `PROC08_CROSS_CURRENCY_INTEGRATION` que TRE-09 dejó DIFERIDA.

## Routing

Entrada 945bec7 = origin. CNT-01 no está publicado (sin migración, código ni fila READY; el catálogo lo da NOT_STARTED), así que
el encargo fija la RUTA B. `P1_TOUCH_CNT01=0`.

## Contrato (X08-01..12)

| Id | Regla |
|---|---|
| X08-01 | Monto = total con tributos de la versión vigente del monto declarado de la oferta (PROC-06). Límite = competencia APROBAR × CONTRATACIONES del cargo del acto (ORG-03). |
| X08-02 | Fecha de autoridad = `acto.fecha`, la misma que ya usa el delta AAL para la competencia en vigor. No se introduce otra fecha. |
| X08-03 | Monedas canónicas (`canonical_currency`: VED → VES, factor 1, no es FX). Si coinciden, la comparación es directa y no se consulta ninguna tasa. |
| X08-04 | Si difieren, se usa `service_tasas.verificar_limite`: tasa APROBADA con la mayor `fecha_efectiva` ≤ fecha de autoridad, por cada moneda distinta de VES. Se compara `total × tasa(op) ≤ límite × tasa(lím)` en VES con Decimal exacto, sin redondeo intermedio. |
| X08-05 | Sin una tasa necesaria: bloqueo 422 `GOV_OFFICIAL_RATE_REQUIRED` con moneda de la oferta, moneda del límite, fecha y monedas sin tasa. Sin respaldo, sin tasa privada y sin consulta externa. |
| X08-06 | Exceso tras la conversión: 409 `GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED` (mismo código del delta AAL), con la conversión en `details`. |
| X08-07 | La adjudicación guarda la conversión usada en `gov_procurement_decisions.conversion_autoridad`: monedas, fecha, por tasa su id, versión, valor, fuente BCV, referencia y sha256 de la evidencia, más los equivalentes en VES. Es inmutable: la guarda PG existente compara la fila completa. Si no hubo conversión, queda nula. |
| X08-08 | La vista previa (`control_monto` de cada acto elegible) muestra la tasa, la fecha, la fuente BCV, los equivalentes y el resultado. El estado nuevo `SIN_TASA` («Sin tasa oficial aprobada») sustituye a `MONEDA_DISTINTA`. El backend sigue siendo la autoridad. |
| X08-09 | Concurrencia: al adjudicar, las tasas se leen con FOR SHARE (`bloquear=True`). Una tasa sustituida o anulada en paralelo hace que la decisión use la versión vigente o se bloquee. El límite cambiado y la doble adjudicación siguen cubiertos por el delta AAL. |
| X08-10 | Auditoría: `GOV_PROCUREMENT_DECISION_ISSUED` añade `conversion` (monedas, fecha, ids y versiones de las tasas, sin importes). El bloqueo por tasa audita `GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED` con la causal `GOV_OFFICIAL_RATE_REQUIRED`. |
| X08-11 | Aislamiento: las tasas son de la empresa del contexto. No hay rutas nuevas; las rutas de decisión ya responden 404 entre empresas y siguen en el barrido ISO. |
| X08-12 | La ficha de cada decisión muestra la conversión histórica guardada; no se recalcula. E2E en 1280/390/320 con Axe. |

## Constitution Gate

BLOCKER=0 · CRITICAL=0 · CONTRADICTIONS=0 · OWNER_CONFLICT=0 · MATERIAL_OQ=0 · UNKNOWN=0. Las reglas monetarias (fórmula, escala, redondeo,
fecha y error) están fijadas por TRE-09 y por el encargo. La migración 0116 (reencadenada tras 0115_gov_cnt01_contratos de P2) solo añade una columna nula; no hay backfill.

## Plan y tareas

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| X001 | Reconciliación, routing, arqueología, delta y gate | CLAUDE | n-a | no | n-a | 0 | este fichero | — | gate PASS |
| X002 | C1: columna + 0115, evaluación multimoneda, instantánea, auditoría, salida de la decisión, fijaciones de cabeza | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models, 0115, service_decision_limite, service_decision_resolver, service_decision, tests de cabeza | alembic, ruff, mypy | verde |
| X003 | C2: pruebas PG multimoneda y ajuste de las 2 pruebas AAL de moneda distinta | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_proc08_multimoneda.py, tests/test_gov_proc08_limite_monto.py | pytest PG | verde |
| X004 | C3: panel de control con conversión y conversión en la ficha de la decisión + Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | ControlLimiteAutoridad(.test).tsx, ExpedienteDecision.tsx | tsc, eslint, vitest | verde |
| X005 | C4: E2E multimoneda dentro de gobierno-decision.spec.ts | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-decision.spec.ts | E2E | X08-12 |
| X006 | Suites una vez, publicación, UAT y cierre | CLAUDE | n-a | no | n-a | 0 | evidence | suites, humo | HEAD == origin |
