# ATTEMPT_LOG — P3-ENTERPRISE-REBASELINE-AND-COMPLETION-MATRIX

Fecha: 2026-11-20. Ejecutor: Claude (arquitecto local y auditor). `PRODUCT_CODE_CHANGES_ALLOWED=NO`.

## Entrada

| Campo | Valor |
|---|---|
| ENTRY_HEAD | `b3b53046`: commit local de herramientas (MCP 2.4.0), sin publicar porque este shell no tiene credenciales de GitHub |
| ORIGIN_DEVELOP | `b726c1da` (`git fetch origin`; no había avanzado) |
| WORKTREE_CLEAN | YES |
| ALEMBIC_HEAD | `0128_gov_tre04_pago` (136 revisiones, análisis estático de `down_revision`) |
| ALEMBIC_HEAD_COUNT | 1 |

## Entorno: ENVIRONMENT_FAILURE (no afecta al producto)

- No hay PostgreSQL, `psql` ni Docker.
- No hay `resources/backend/.venv`, y al `python3` del sistema le falta `argon2`: la aplicación no arranca.
- No hay `node_modules` en el frontend: vitest no arranca.
- **Consecuencia:** ninguna prueba se volvió a ejecutar en este ciclo. La matriz se basa en lectura del código del HEAD (M) más evidencia registrada en el repositorio (R, con ruta y fecha).
- No se concede ningún `OWNER_UAT_READY` nuevo: solo se mantiene donde la evidencia registrada cumple todas las condiciones.

## DeepSeek

`DEEPSEEK_CALLS=0` · `DEEPSEEK_RETRIES=0` · `DEEPSEEK_HARD_CAP=10` · `OWNER_EXCEPTION_USED=0`.

Motivo:
1. El encargo pide usar DeepSeek para análisis mecánico. En este repositorio, el ejecutor `deepseek-executor` está definido como *patch-only*: devuelve bloques SEARCH/REPLACE.
2. `.claude/CLAUDE.md` (precedencia 4) solo permite delegar implementación acotada, tras el gate. Las instrucciones de la tarea tienen precedencia 5.
3. Este ciclo no tiene implementación (`PRODUCT_CODE_CHANGES=0`).
4. El análisis mecánico se hizo con scripts deterministas, sin egreso de código a un proveedor externo:
   - cruce del fixture OpenAPI con las llamadas `apiFetch` del frontend;
   - cálculo de las cabezas de Alembic;
   - consolidación de los CSV.

Es más reproducible que una llamada a un modelo. No es una excepción a la regla: es la regla de mayor precedencia.

## Análisis mecánico (scripts de Claude)

| # | Objetivo | Entrada | Resultado | Aceptado |
|---|---|---|---|---|
| M1 | Cabezas de Alembic | `resources/backend/alembic/versions/*.py` | 136 revisiones, 1 cabeza | Sí |
| M2 | Rutas del frontend Enterprise sin backend | `openapi-routes.json` (1 154 ops) + `apiFetch` en `src/**` | 0 en Enterprise; 3 artefactos de análisis en Gobierno | Sí; confirmado por la auditoría G (las entradas «missing» eran plantillas dinámicas) |
| M3 | Rutas del backend Enterprise sin llamada desde el frontend | Ídem | 88 candidatas (`orphans.txt`) | Como candidatas. Las auditorías las clasificaron en 35 llamadas por otra vía, 30 legítimas sin pantalla y 22 capacidades de negocio sin pantalla |
| M4 | Consolidación y métricas | catálogo (236) + auditorías A..G (277) | Matriz, métricas, revalidación de las 92 filas | Sí |

## Auditorías delegadas (subagentes de Claude, solo lectura, sin egreso externo)

Cada auditoría recibió el mismo brief:
- estados y definiciones del encargo §7–§9;
- la regla de verificación M/R;
- la prohibición de editar el repositorio.

Claude auditó cada informe y verificó leyendo el código 22 defectos de muestra. Los 22 se confirmaron, en 4 casos con una parte PLAUSIBLE (tabla en `PRODUCT_DEFECTS.md`).

| Lote | Módulos | Filas | Resultado | Ajustes de Claude al consolidar |
|---|---|---|---|---|
| A | Inicio, Organización, Terceros, Productos | 43 | 4 COMPLETE, 27 PARTIAL, 8 DEFECT, 4 NOT_BUILT | Verificados PRD-15, PRD-11 y TER-02 |
| B | Comercial, Financiero, Fiscal maestro, Fiscal | 37 | 17 PARTIAL, 16 DEFECT, 4 NOT_BUILT | Verificados la escala de tasa, el correlativo sin bloqueo, el snapshot 1.0 y el IGTF 500 |
| C | Compras, CxP, Importaciones (42 filas de la Spec 018) | 66 | 41 COMPLETE, 15 PARTIAL, 9 DEFECT, 1 SPONSOR | Verificados IMP-28, IMP-21, CMP-14 y CXP-06. **OWNER_UAT_READY rebajado a NO** en CMP-09 y en las 39 COMPLETE de la Spec 018 por A11Y-IMPORT-SCROLL-REGIONS (falta grave de Axe a 390 y 320 en el expediente; evidencia en `specs/005-ventas-cuentas-por-cobrar/evidence/dispatch-cost-relief/EVIDENCE.md:103`). Se mantiene YES solo en CMP-06: Axe con 0 faltas graves a 1280, 390 y 320 (`specs/004-compras-cuentas-por-pagar/evidence/quote-award/EVIDENCE.md:36`) |
| D | Ventas, Pedido (DOCX), CxC | 35 | 19 PARTIAL, 14 DEFECT, 1 NOT_BUILT, 1 SPONSOR | Verificados la transición genérica, la cancelación de un pedido facturado y la nota DRAFT |
| E | Inventario, Tesorería | 27 | 2 COMPLETE, 12 PARTIAL, 11 DEFECT, 1 NOT_BUILT, 1 SPONSOR | Verificados el recálculo sin permiso, el ajuste sin `apply` y el costo perdido en la transferencia |
| F | Regulatorio, Regulación, Aprobaciones, Seguridad, Auditoría, Documentos, Configuración, Reportes | 53 | 5 COMPLETE, 36 PARTIAL, 7 DEFECT, 5 NOT_BUILT | Verificados el alcance vacío (diseño documentado, no defecto oculto), el pago sin maker-checker y la anulación regulatoria sin auditoría |
| G | Transversal, Activos fijos, hard-code, BD, OpenAPI | 16 | 6 PARTIAL, 5 DEFECT, 5 NOT_BUILT | Verificados la idempotencia por cabecera y el snapshot 1.0 |

`DEEPSEEK_CALLS=0`. Los subagentes son instancias de Claude: no cuentan contra el tope de DeepSeek.

## Clasificación de fallos (regla 0.3 del encargo)

- **PRODUCT_DEFECT:** 60 únicos (`ENTERPRISE_CURRENT_DEFECTS.md`).
- **TEST_DEFECT:** 2:
  - `test_spec033_confirmation.py:343-346`;
  - `tests/test_purchasing.py:265-273`.
- **BASELINE_DEBT:** 1 (SALES-CONFIRMATION-EXTRA-WITHOUT-PRODUCT-500).
- **ENVIRONMENT_FAILURE:** 1 (el puesto).
- **FIXTURE_DEFECT:** 0.

No se modificó código de producto.

## Salida

- `PRODUCT_CODE_CHANGES=0`.
- Ficheros del ciclo:
  - en `docs/roadmap/enterprise-application-completion/`: los cuatro documentos `ENTERPRISE_*`, más una línea de «sustituida» en `SPONSOR_APPLICATION_COVERAGE_MATRIX.md`;
  - en `specs/enterprise-rebaseline/evidence/`: los seis documentos de evidencia.
