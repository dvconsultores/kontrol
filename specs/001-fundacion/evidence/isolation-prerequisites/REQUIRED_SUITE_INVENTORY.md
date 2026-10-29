# REQUIRED_SUITE_INVENTORY — ciclo 07 (reanudación)

> Inventario de suites exigidas (§68 del encargo de reanudación), fijado **antes** del cierre. La columna «Resultado» la rellena la
> evidencia del cierre (§9 del delta); una suite sin ejecutar deja el ciclo abierto (`UNRUN_REQUIRED_SUITES` debe ser 0).

| RS | Suite | Orden o artefacto | Qué demuestra |
|---|---|---|---|
| RS-01 | Reconciliación del repositorio | `git status`, `HEAD = origin/develop = 1cbb79f` | punto de partida |
| RS-02 | Procedencia del trabajo sin confirmar | `UNCOMMITTED_C07_RECONCILIATION_MATRIX.md` (medición línea a línea contra respuestas crudas) | 0 código semántico de Claude |
| RS-03 | Auditoría de decisiones de la dueña | traza: respuestas del diálogo 2026-10-29T03:02:42Z (OD-ISO-10/11) | `INVENTED_OWNER_DECISIONS = 0` |
| RS-04 | Requisitos de Gobierno | IR v1.0 releída; `GOVERNMENT_REQUIREMENTS_RECONCILIATION.md` | cobertura aplicable 100 % |
| RS-05 | Inventario de modelos | `SCOPE_MODEL_INVENTORY.md` (SALIDA) | 0 modelos sin clasificar |
| RS-06 | Inventario de rutas | `SCOPE_ROUTE_INVENTORY.md` (SALIDA, con cobertura hostil medida) | 0 rutas sin clasificar |
| RS-07 | Servicios | `SERVICE_SCOPE_INVENTORY.md` | ayudantes de carga con alcance |
| RS-08 | Almacén | `STORAGE_SCOPE_INVENTORY.md` | `STORAGE_CROSS_TENANT_ACCESS = BLOCKED` |
| RS-09 | Sondas de almacenes y sucursales | `scope_scan` sobre la base de la E2E; `test_warehouse_branch_scope.py`, `test_warehouse_catalog_scope.py` | filas cruzadas medidas, nuevas bloqueadas |
| RS-10 | Superficies de producto afectadas | `AFFECTED_PRODUCT_SURFACE_MATRIX.md` + `e2e/tipos-movimiento.spec.ts` | ficha de pantalla en PASS |
| RS-11 | Puertos del arnés (PDD-QA-PORTS-01) | `tests/test_e2e_corrida.py` (41, sin omitidas con el 8000 ajeno ocupado) | puertos por defecto intactos; configurados propagados; ocupante intacto |
| RS-12 | Rojo dirigido | T02a–d (53/25/21/3 rojas en `0dbe632`) | cada GAP tenía su prueba roja |
| RS-13 | Hostiles | `test_iso_*`, barridos IDS/LISTAS/CABECERA, `test_iso_tenant_rutas.py`, `test_n10_*`, `test_mc_*` | 0 fugas, 0 mutaciones no autorizadas |
| RS-14 | Negativas | rutas propias manipuladas (ISO-TEN-07), cuerpo con ids ajenos, `global_scope=true` | rechazo según contrato |
| RS-15 | PostgreSQL completa | `qa/suite_tiempos.py --motor postgres --con-analizador` con `KONTROL_PG_BIN_DIR` | regresión cero |
| RS-16 | SQLite completa | `qa/suite_tiempos.py --motor sqlite --con-analizador` | regresión cero |
| RS-17 | vitest completo | `node node_modules/vitest/vitest.mjs run` | frontend |
| RS-18 | tsc | `node node_modules/typescript/bin/tsc -b --noEmit` (incluye `e2e/`) | tipos |
| RS-19 | eslint | `node node_modules/eslint/bin/eslint.js . --max-warnings 0` | estilo |
| RS-20 | build | `node node_modules/vite/bin/vite.js build` | empaquetado |
| RS-21 | ruff | `.venv/bin/ruff check` (backend y `qa/e2e_corrida.py`) | estilo |
| RS-22 | mypy sin errores nuevos | `.venv/bin/mypy app` frente a `HEAD` (lista idéntica) | tipos |
| RS-23 | Alembic | cabeza única `0062`; upgrade y downgrade (T09) | migración |
| RS-24 | OpenAPI | `app.openapi()` frente a `HEAD` | deriva explicada = 0 |
| RS-25 | Guardas de arquitectura | `tests/test_iso_guardas.py`, `tests/test_architecture_scope.py`, `src/tests/alcance-frontend.test.ts` | modelos, rutas y frontend |
| RS-26 | ISOLATION-E2E ×3 | `qa/e2e-run.py --con-analizador --orden c07/e2e/post_e2e.sh` (Chromium, Firefox, WebKit) | aislamiento en el navegador |
| RS-27 | E2E canónica | `qa/e2e-run.py --con-analizador` (incluye `tipos-movimiento.spec.ts`) | producto existente sin regresión |
| RS-28 | Base tras la E2E | `post_e2e_inspect.py` (cabeza, triggers, catálogo, `scope_scan`) | `CROSS_SCOPE_ROWS_CREATED_BY_E2E = 0` |
| RS-29 | Copia y restauración | `qa/backup_restore_cert.py` | `BACKUP_RESTORE_CERT_STILL_PASS = 1` |
| RS-30 | Mutaciones | campaña 07 (rondas 1–4, `mutantes07*.json`) | `BEHAVIORALLY_SURVIVING_MUTANTS = 0` |
| RS-31 | Seguridad | barridos + matriz de errores + escáner + egress | `HOSTILE_LEAKS = 0` |
| RS-32 | Accesibilidad y responsive de la UI cambiada | E2E-TMOV-03 (axe de `main` a 1280 y 320 px) | sin violaciones |
| RS-33 | Ficha de pantalla | `AFFECTED_PRODUCT_SURFACE_MATRIX.md` | `AFFECTED_SCREEN_FORM_COMPLETENESS_GATE = PASS` |
| RS-34 | Métricas de completitud | `docs/roadmap/government-product-completeness/` (F05) | fundamentos 14/38; funcional y UAT sin cambio |
| RS-35 | Barrido de secretos | egress de cada encargo + barrido del diff antes del commit | 0 secretos |
| RS-36 | Residuos | `qa/pg-test-residuos.py`, `qa/e2e-bases.py listar`, `git status` | limpio |

`REQUIRED_SUITE_COUNT = 36`.
