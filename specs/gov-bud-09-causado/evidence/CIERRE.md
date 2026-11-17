# BUD-09 · Cierre (2026-11-17)

- **Entrada:** `ffcea9f`, cabeza `0122_gov_cnt07_terminacion`.
- **Salida:** cabeza `0123_gov_bud09_causado` (una sola).
- **Paralelo (P2):** GOV-PARAMETERIZATION-AUDIT-01 (`eff5ba4`, solo documentación) se integró con una fusión ordinaria en `bcb519d`, sin conflictos.
  - BUD-08, CNT-03 y CTL-01, de los que depende BUD-09, figuran con `CURRENT_PRODUCT_DEFECT=NO`.
  - `P2_AUDIT_INTEGRATED=YES`, `P2_FINDINGS_AFFECTING_BUD09=NONE`: lo que señala P2 es una refactorización futura, no un defecto actual.

## Qué se entregó

- **Menú:** Gobierno · Presupuesto › **Causados** y **Políticas de causado**. Las pantallas son la lista con filtros y CSV, nuevo/editar, el detalle con formalizar y anular, y la lista y la ficha de políticas.
- **API:** 17 rutas bajo `/gobierno/presupuesto`:
  - configuración y numeración;
  - políticas: crear, editar, activar, cerrar;
  - causados: lista, opciones, CSV, crear, editar, detalle, controles, formalizar, anular.
- **Migración:** `0123_gov_bud09_causado`, con 8 tablas y sus triggers de inmutabilidad. Las 8 son configuración, políticas, documentos de la política, historia de la política, causados, líneas, evidencias e historia del causado.
- **Permisos:** `gobierno_presupuesto:cause_policy` y `gobierno_presupuesto:cause`. Formalizar, anular y activar una política piden MFA (`SENSITIVE`). El catálogo pasa de 175 a 177 permisos.
- **CAUSING_POLICY configurable por tipo de gasto:**
  - el disparador (solo documentos, valuación aprobada, recepción del contrato…);
  - los documentos exigidos por etapa;
  - si se exige la recepción;
  - su vigencia.
  - No hay ninguna precargada. Activarla exige fundamento y MFA; el acto administrativo es opcional (OD-BUD09-02).
- **Reglas:**
  - **R1:** solo sobre un compromiso BUD-08 vigente.
  - **R2:** Σ causado ≤ comprometido, por línea. Admite causados parciales y múltiples, con `FOR UPDATE` sobre las líneas del compromiso e `If-Match` (versión).
  - **R3:** la evidencia no puede ser posterior a la fecha efectiva.
  - **R4:** la fecha efectiva es distinta de `registered_at`.
  - **R5:** la autoridad es un cargo ORG-03 con la competencia CAUSAR × PRESUPUESTO vigente, más la guarda ORG-06. Nunca un nombre de cargo.
  - **R6:** el causado formalizado es inmutable, por trigger. Se anula con un motivo de al menos 10 caracteres, lo que restituye el pendiente; no se borra.
- **SoD:** el proceso BUD-09 entra en el catálogo de CTL-01 (`BUD09_COMPROMETER` → `BUD09_CAUSAR`), solo en modo BLOCK (OD-BUD09-01). El modo WARN queda como deuda SOD-WARN-MODE-01.
- **Numeración:** configurable por el ente; el patrón por defecto es `{ANIO}-{NUMERO:5}` y se valida antes de guardar.
- **Evidencia:** tipada, con huella sha256. Los controles se ven antes de formalizar.
- **Frontera TRE-03:** el causado expone `monto_ordenado` y `pendiente_de_ordenar`. Ni ordena ni paga.
- **Contabilidad:** `ACCOUNTING_ENTRY=OUT_OF_SCOPE`; el asiento es ACC-02 y depende de N36, pendiente.
- **Guarda de BUD-08:** un compromiso con causados vigentes no se puede anular.
- **Auditoría (CTL-02):** 9 eventos `GOV_BUDGET_CAUSE*` y `GOV_BUDGET_CAUSING_POLICY*`. El catálogo pasa de 584 a 593.
- **Aislamiento:** otra empresa recibe 404.
- **Cero hardcode institucional:** la autoridad sale de la competencia, y las políticas y la numeración son datos del ente.

## Evidencia

| Puerta | Resultado |
|---|---|
| PG dirigida BUD-09 | 25/25, incluidos la carrera en PG y la inmutabilidad por trigger |
| SQLite | Las 25 pruebas de BUD-09 se saltan por diseño: el aislamiento multiempresa se verifica sobre PostgreSQL (P21). Las guardas de catálogo y estructura, 15/15 |
| Mutaciones | 7/7 muertas: M1a/M1b sobrecausado, M2/M2b evidencia y recepción, M3 autoridad, M4 tenant, M5 concurrencia. Cada mutante se restauró y se comparó byte a byte |
| Vitest de causados | 26/26 (carga, vacío, error, lista, crear, validación, falta de evidencia, saldo disponible, formalización, 403, 409, 422, responsive) |
| Vitest completo | 2349/2349 |
| tsc, eslint, build | OK |
| ruff | OK |
| mypy | 157, la línea base; un error menos que al empezar |
| Alembic (ida, vuelta e ida en PG) | OK; una cabeza (`0123`); 8 triggers |
| OpenAPI | Fixtures regenerados con `qa/fixtures_de_frontend.py`: +237 líneas, 0 borradas. `test_frontend_fixtures` y `test_openapi_security`, 48/48 |
| E2E `gobierno-presupuesto-causado` | 1/1: login, menú, lista, crear, compromiso, evidencia, formalizar, detalle, historia, sobrecausado negativo; 1280/390/320; `AXE_NEW_SERIOUS=0`, `AXE_NEW_CRITICAL=0`; sin desbordamiento |
| Humo UAT (HUMO-UAT-01) | 1/1 (catorce pantallas, causados y políticas incluidas) |
| PG completa, primera corrida (`r20261117t053228…`, antes de C16) | 5735 pruebas: 5707 pasan, 18 se saltan, 10 fallan. **5 NEW_FAILURE de BUD-09**: 7 modelos sin `__scope__` (3 guardas de estructura), el recuento de permisos (175 → 177) y el catálogo SoD sin BUD-09. Se corrigieron en C16. **5 BASELINE_FAILURE**, que fallan igual sobre `git archive HEAD` sin BUD-09: `test_imb_07_pip_check_limpio` (el entorno de pruebas no tiene pip; es del entorno), `n10` por `import_*.created_by`, `naive_datetime` (`aperturas:abierta_en`) y `spec019` ×2 |
| Tras C16 (PG dirigida) | Guardas de estructura, delegación, CTL-01, BUD-08 y BUD-09: 91/92. El fallo restante es `n10` de la línea base |
| **PG completa sobre el árbol final** (`r20261117t095706…`, tras C16) | 5735 pruebas: **5712 pasan**, 18 se saltan, 5 fallan, las cinco BASELINE_FAILURE ya citadas (`pip check` del entorno, `n10` `import_*`, `naive_datetime`, `spec019` ×2). **NEW_BACKEND_FAILURES=0**, FLAKY=0. 7037,6 s monotónicos, sin salto de reloj, anomalía NORMAL |

## Deudas y observaciones

- **SOD-WARN-MODE-01:** el modo de aviso (WARN) de CTL-01 no existe; BUD-09 usa solo BLOCK (OD-BUD09-01).
- **OBS-LICUX-ANON-403-01:** pendiente de P1 licencias; fuera de BUD-09.
- **ACCOUNTING_MAPPING_N36=PENDING:** el asiento contable del causado (ACC-02) espera a N36 (clase C).
- **Línea base heredada**, sin cambios en este ciclo: `n10` (`import_*.created_by`), `naive_datetime` (PROC-07 aperturas) y `spec019` ×2. Además, `pip check` es del entorno de pruebas.

## DAG

- `DIRECTLY_UNLOCKED`: **TRE-03**, Orden de pago desde obligación causada (P0), que dependía solo de BUD-09. Pasa a BUILDABLE_NOW.
- **REP-02:** su dependencia de BUD-09 queda satisfecha, pero sigue esperando el registro de avance físico.
- `TRANSITIVELY_UNLOCKED`: la cadena se abre a través de TRE-03. Lo que sigue esperando, con lo que le falta:
  - TRE-04 y REP-05: TRE-03.
  - BUD-12 y TRE-10: TRE-04.
  - TRE-08: TRE-03 y TRE-04.
  - CNT-05: TRE-03 y TRE-04.
  - ACC-02: ACC-01.
  - ACC-05: ACC-02 y TRE-04.
  - BUD-13: BUD-10.
  - REP-01: BUD-10 y TRE-04.
  - PROC-12: PROC-01, PROC-04, REQ-01, TRE-03 y TRE-04.
- **Ruta crítica:** BUD-09 → **TRE-03** → TRE-04.

## Métricas

- `OWNER_UAT_READY`: 44 → **45** de 122 (36,89 %).
- Puertas de la matriz: 452 → **463** de 1268.
- `OWNER_ACCEPTED=NO`: solo lo concede la dueña.
