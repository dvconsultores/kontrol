# CIERRE · REP-03 Reporte de contrataciones (2026-11-13)

## Selección (encargo POST PROC-11)

- **Regla A (P0):** ningún P0 elegible.
  - N37 = BLOCKED_EXTERNAL_SOURCE: faltan los manuales locales y la ordenanza de presupuesto. La Gaceta 512 Ext. es de actividades económicas.
  - D-GOV-02 = OPEN: decisión material de la dueña; no se resuelve en silencio.
  - PROC-09 sigue BLOCKED (U.T. sin fuente; OQ-PROC09-01..04).
  - REQ-01, PROC-01 y CNT-01 dependen de presupuesto, U.T. o monto.
- **Regla B (mejor P1):** REP-03 (IR §12). Tiene datos reales en 6 de 7 dimensiones. El monto se declara NO_DISPONIBLE (OBS-PROC08-MONTO-01, OPEN).
  - No duplica la lista de PROC-03, ni REP-09 ni REP-10.
- **PAGADOR:** UNAVAILABLE_UNTIL_GOV_TRE_004 (FAKE_PAGADOR_CREATED=0).
- **OBS_PROC08_TZ_01:** CLOSED_TEST_INFRA; no se reprodujo ninguna regresión.

## Entrega

- **Backend:** servicio y API de solo lectura, en `/gobierno/contrataciones/reporte` (JSON y `.csv`), con la capacidad `gobierno_expedientes:view`.
  - Sin migración. La cabeza sigue siendo la de P2: `0105_receipt_temporary_zone`.
  - 0103 y 0104 intactas.
- **Catálogo de auditoría:** +1 `GOV_PROCUREMENT_REPORT_EXPORTED`. Tras el merge ordinario con Spec 018, que añadió otra entrada, el total es **495**.
  - El plan decía 487 → 488: era una cifra obsoleta. La real fue 493 → 494 y, tras el merge, 495.
- **Frontend:**
  - pantalla en Gobierno › Contrataciones › Reporte de contrataciones;
  - Vitest;
  - ruta, Sidebar y pantallas.ts;
  - humo UAT con REP-03 y la fila de PROC-11 que faltaba (`/gobierno/sod/funciones`).
- **E2E:** `e2e/gobierno-reporte-contrataciones.spec.ts`, con menú, CSV, negativa de período, aislamiento, 1280/390/320 px y Axe.

## Pruebas

| Prueba | Resultado |
|---|---|
| PG enfocada (REP-03 + catálogo, tras el merge) | 19/19 |
| PG completa | 5378 passed / 36 failed / 18 skipped |
| ruff | limpio |
| mypy | 157 errores = línea base de la entrada (0 nuevos) |
| Vitest con Node 22 (tras el merge) | 1968/1968 |
| tsc, eslint, build | limpios |
| E2E REP-03 | 1/1, y 2/2 con 4 workers; sin reintentos |

**Los 36 rojos de la PG completa:**

- El mismo conjunto falla en la entrada 279d6c8 (worktree de atribución): NEW_BACKEND_FAILURES=0.
- 30 son de copia y restauración: el `pg_dump` de pgserver no es compatible con el servidor PostgreSQL de QA actual (micromamba). Es causa de entorno.
- Los otros 6 (integridad, MIME, N10, datetime desnudo y Spec 019 recepción ×2) también fallan en la entrada, y no mencionan ficheros de REP-03.

## Orquestación

- **DeepSeek:** 8 llamadas (tope 8, sin autorizaciones extra), ≈0,042 USD. Detalle en ATTEMPT_LOG.md.
- **Código y pruebas escritos por Claude:** CLAUDE_SEMANTIC_CODE/TESTS/MIGRATION/QA_WRITTEN=0.

## UAT

- **Pila:** sin Docker, con el mecanismo del repositorio: `qa/e2e-run.py --orden` desde el HEAD publicado 8519e0b, frontend en el puerto 15873.
  - No se instaló infraestructura.
- **Humo:** `uat-humo-gobierno.spec.ts --project=humo-uat` cubre REP-03 y PROC-11.
- **Credenciales:** no se registran aquí ni en ningún informe.
- **OWNER_ACCEPTED:** NO, hasta la decisión explícita de la dueña.
