# TRE-03 · Cierre (2026-11-18)

- **Entrada:** `9a18d5a` (GOV-SOD-COVERAGE-01 de P2), cabeza `0123_gov_bud09_causado`.
- **Salida:** cabeza `0125_gov_tre03_orden_pago` (una sola), sobre `0124_gov_commission_policy` de P2.
- **Paralelo (P2):** `origin/develop` = `9a18d5a` al entrar. En el `git fetch` final, P2 había publicado GOV-PROC-COMMISSION-POLICY (`dd1021c` + `a51816b`), con la migración `0124_gov_commission_policy`.
  - Se integró con una fusión ordinaria (`f0e2b0b`) sobre el commit de TRE-03 (`3d09a6f`).
  - Hubo 6 conflictos, todos de fijaciones. Claude tomó con git el lado propio y movió la migración con `git mv`, sin escribir contenido.
  - DeepSeek reencadenó la migración como `0125` y sumó las fijaciones (C5-7, autorizada por la dueña).
  - No hubo otros ficheros en común con efecto funcional, y OpenAPI quedó igual que antes de la fusión.
- **Ciclos:** COMPLETION-02 a COMPLETION-05 (ver `ATTEMPT_LOG.md`).

## Qué se entregó

- **Menú:** Gobierno · Tesorería › **Órdenes de pago** y **Políticas de órdenes de pago**.
  - Pantallas: lista con filtros y CSV, nueva/editar, detalle con controles, emitir y anular; lista y ficha de políticas; numeración.
- **API:** 12 rutas TRE-03 (17 operaciones) bajo `/gobierno/tesoreria` y 8 esquemas nuevos. BUD-09 queda intacto en OpenAPI tras renombrar 4 esquemas repetidos (C5-6).
- **Migración:** `0125_gov_tre03_orden_pago`, 8 tablas.
- **Permisos:** TRE-03 añade 5 (177 → 182; con P2, 183). Emitir, anular y activar o cerrar una política piden MFA.
- **Política de orden de pago configurable:** documentos exigidos, vigencia, fundamento. No hay ninguna precargada. El acto administrativo es opcional.
- **Reglas:**
  - solo sobre causados BUD-09 formalizados;
  - Σ ordenado ≤ causado, por causado, con órdenes parciales y varias órdenes; protegido contra concurrencia;
  - el borrador no consume; la emisión consume; la anulación restaura;
  - multicausado: varias obligaciones del mismo beneficiario y moneda en una sola orden;
  - autoridad = cargo ORG-03 con la competencia ORDENAR_PAGO × TESORERIA vigente. Nunca un nombre de cargo.
- **SoD:** el proceso TRE-03 entra en el catálogo de CTL-01 (`ProcesoSod += "TRE-03"`) y reutiliza su evaluador; sin eventos SoD duplicados.
- **Numeración:** configurable por el ente; patrón por defecto `{ANIO}-{NUMERO:5}`.
- **Frontera TRE-04:** la orden emitida muestra «Siguiente paso: Pago (TRE-04)». Ni paga ni contabiliza.
- **Auditoría (CTL-02):** TRE-03 añade 9 eventos (593 → 602; con P2, 608).
- **Aislamiento:** otra empresa recibe 404, también al escribir (`test_t03_11b`).
- **Cero hardcode institucional:** autoridad por competencia; políticas y numeración son datos del ente.

## Evidencia

| Puerta | Resultado |
|---|---|
| E2E principal + multicausado (`r20261118t024450`, árbol final) | 2/2, limpieza LIMPIA. Cubre política, numeración, borrador sin consumo, documentos, emisión, historia, frontera TRE-04, anulación con restauración, lista y CSV, multicausado, dos órdenes sobre un causado, sobreorden (409 `GOV_PAYMENT_ORDER_OVER_ORDER`), SoD real (409 `GOV_SOD_CONFLICT`) |
| Axe 1280/390/320 | 0 serios, 0 críticos (tras C5-5: regiones desplazables enfocables) |
| Responsive 390/320 | PASS; el diálogo de anulación cabe en 320 |
| Vitest completo | 2420/2420 (217 ficheros) |
| tsc, eslint, build | 0 / 0 / OK (build con Node 22 directo; `npm run build` falla por el enlace aplanado de `node_modules/.bin`, entorno) |
| ruff | OK |
| mypy | 157, la línea base; ninguno en ficheros tocados |
| PG dirigida amplia | 681/681 |
| Trío BUD-08 + BUD-09 + TRE-03 + guardas OpenAPI (tras el renombrado) | 115/115 |
| Mutaciones | 9/9 muertas (M4 con `test_t03_11b`) |
| OpenAPI | 12 rutas TRE-03, 0 inesperadas; solo cambian los esquemas SoD por el proceso nuevo |
| **Tras la fusión con P2 (`f0e2b0b`)** | |
| Alembic | Una cabeza (`0125`). La cadena 0123 → 0124 (P2) → 0125 sube, baja y vuelve a subir en una base PG propia, ya borrada |
| PG dirigida | 518/518: guardas, OpenAPI, CTL-01, BUD-08, BUD-09, TRE-03, comisiones de P2, PROC-02/07/08, N7, N9 y alcance. Los 2 rojos de `test_n9_integrity` en la corrida sin analizador pasan 3/3 con él (ENVIRONMENT) |
| E2E (`r20261118t135544`) | 3/3: TRE-03 principal, TRE-03 multicausado y la política de comisiones de P2. Limpieza LIMPIA |
| Vitest, tsc, eslint, build, ruff, mypy, `git diff --check` | 2446/2446 (220 ficheros) · 0 · 0 · OK · OK · 157 (línea base) · 0 |
| OpenAPI frente a `origin/develop` | 12 rutas y 8 esquemas nuevos de TRE-03; solo cambian los 4 esquemas SoD y las 2 operaciones SoD que los usan; 0 inesperados |
| **PG completa sobre el árbol final** (`qa/suite_tiempos.py --motor postgres --con-analizador`, `r20261118t135908…`, árbol `f0e2b0b`) | 5808 pruebas: **5788 pasan**, 18 se saltan, 5 fallan. Las cinco son BASELINE_FAILURE ya conocidas, ajenas a TRE-03: `pip check` (entorno), `n10` (`import_*.created_by`), `naive_datetime` (`aperturas:abierta_en`, PROC-07) y `spec019` ×2. **NEW_FAILURES=0**. 7431,8 s monotónicos, sin salto de reloj, anomalía NORMAL |

## Deudas y observaciones

- **HUMO-UAT de TRE-03:** `uat-humo-gobierno.spec.ts` (`PANTALLAS`) no incluye las 2 pantallas de TRE-03. Es un gate de ACCESSIBLE (OD-QA-UAT-01), no de READY. **Cerrado en TRE-03-ACCESSIBLE-01 (2026-11-18, `a9bae79`)**: el humo abre las 2 pantallas y la pila de la dueña corre ese commit. TRE-03 queda **OWNER_UAT_READY + ACCESSIBLE** (ver `UAT_SMOKE.md`).
- **SOD-WARN-MODE-01:** heredada; solo BLOCK.
- **Pago, retenciones y contabilidad:** TRE-04, TRE-05, ACC-*.

## DAG

- `DIRECTLY_UNLOCKED`: **TRE-04** (Pago) y **REP-05**, que pasan a BUILDABLE_NOW. TRE-04 conserva LEGAL_VALIDATION_REQUIRED N37 (clase C).
- `TRANSITIVELY_UNLOCKED`: ninguno. TRE-05, TRE-08, CNT-05 y PROC-12 siguen esperando a TRE-04.
- **Ruta crítica:** BUD-09 → TRE-03 → **TRE-04**.

## Métricas

- `OWNER_UAT_READY`: 45 → **46** de 122 (37,70 %).
- Puertas de la matriz: 463 → **474** de 1268.
- `OWNER_ACCEPTED=NO`: solo lo concede la dueña.
