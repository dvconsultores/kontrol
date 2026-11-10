# PROC-08 · Evidencia de cierre (2026-11-10)

Producto publicado en `570a033` sobre `b40bbdc` (avance rápido; sin merge). Migración `0094_gov_proc08_decision`
sobre `0093_fusion_gov_storage` (fusión pública de PROC-07 y la clasificación de almacenamiento de P2). Cabeza única.

| Comprobación | Resultado |
|---|---|
| E2E `e2e/gobierno-decision.spec.ts` (Chromium, PostgreSQL efímero, Alembic, analizador real) | 1/1 PASS |
| E2E de regresión PROC-07 `e2e/gobierno-evaluacion.spec.ts` | 1/1 PASS |
| Backend PostgreSQL: PROC-08 (13), PROC-07, PROC-06, PROC-03, DOC-02, DOC-04, ORG-04, ORG-06 y guardas (catálogo, MFA, delegación, cabeza de Alembic, URL de migraciones, Spec 018) | 283/283 |
| Alembic en PostgreSQL nuevo: upgrade head, downgrade `0093_fusion_gov_storage`, upgrade head | PASS |
| Paridad modelos/migración (tablas de PROC-08) | 0 diferencias |
| tsc, ESLint, build | PASS |
| Vitest Gobierno | 76 ficheros, 634 pruebas PASS |
| Vitest completo | 1858 PASS; 10 rojas preexistentes en `b40bbdc` (importaciones 9, terceros 1), fuera de Gobierno |
| ruff | limpio |
| mypy `app` | 154 = línea base; 0 nuevos |
| OpenAPI frente a `b40bbdc` | solo añadidos: 4 rutas `/decision…`, 4 esquemas; 0 cambiados, 0 quitados |
| Fixtures de frontend (`qa/fixtures_de_frontend.py`) | regenerados: 4 rutas y 3 capacidades `gobierno_decision` |
| Catálogo de auditoría | 448 (444 públicas + 4) |

## Lo que recorre la E2E en el navegador

Menú → expediente con evaluación concluida → «Recomendación y decisión»:
1. Estado (evaluación concluida, «Preparar recomendación») y ofertas evaluadas O-01 y O-02.
2. Recomendación: motivación, exámenes, opciones 1 y 2, todos los firmantes, contador de quórum; confirmación en línea; 201.
3. Solo lectura tras emitir («Emitida: no se puede editar.»); la sustitución exige abrirla y motivarla.
4. Descarga del informe PDF.
5. Decisión: acto DOC-02 emitido y particular, «Adjudicada», oferta única admitida O-01, motivación; confirmación; 201.
6. DEC-01 «Adjudicada», enlace al acto; notificaciones por oferente «Sin notificación» → «Pendiente» tras registrar DOC-04.
7. Historial con REC-01 y DEC-01; nota de CNT-01.
8. Axe sin violaciones en 4 puntos; 390 y 320 px sin desborde.

Resultados alternativos (desierta, terminación, nulidad, segunda opción tras información falsa, violación legal sin
opción siguiente, rechazo) y negativas materiales: verificados en PostgreSQL (`test_gov_proc08_*`).

## Gaps declarados

- OBS-PROC08-PARCIAL-01: la adjudicación parcial exige un pliego que la declare (PROC-04 bloqueado).
- OBS-PROC08-MONTO-01: la oferta no registra monto; no se validan límites monetarios de autoridad.
- OBS-VITEST-P2-01: 10 pruebas Vitest rojas ya en `b40bbdc` (importaciones, terceros), ajenas a PROC-08.

## UAT

Pila de la dueña relevada a `570a033` (`wt-570a033`): HUMO-UAT-01 PASS; `/login` 200; rutas `/decision` sin sesión 401.
