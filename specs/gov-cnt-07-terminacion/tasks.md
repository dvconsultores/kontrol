# Tareas · CNT-07

## Constitution Gate (2026-11-16)

```text
BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0
MATERIAL_OQ=0 (OD-CNT07-01..04 resueltas por la dueña; OQ-CNT07-01 es una deuda posterior, no bloquea)
UNKNOWN=0  TRACEABILITY=C07-01..28 → T002..T007 (100 %)
LEGAL_SOURCE_GATE=PASS (N11, N12 y N25 leídas sobre el texto exacto; FUENTES.md)
SUPPORTED_LEGAL_FIGURES=RESCISION_NO_IMPUTABLE, RESOLUCION_MUTUO_ACUERDO, RESCISION_IMPUTABLE (+CUMPLIMIENTO proyectado)
P1_FUNCTIONAL_OVERLAP=0
DEEPSEEK: deepseek-v4-pro, objetivo 3–5 llamadas, tope 8, OWNER_EXCEPTION_INHERITED=0
GATE=PASS
```

Autorización de `implement`: el encargo de la dueña «P2 · CNT-07 · GOV-CNT-008» (Constitución P2).

## Tareas

Todas las tareas tienen RETRY_MAX = 2.

### T001 · Fuentes, spec, plan, contrato de datos y gate

| Campo | Valor |
|---|---|
| EXECUTOR | CLAUDE |
| MODEL | n-a |
| SECURITY_SENSITIVE | 0 |
| EGRESS_SAFE | n-a |
| FILES | `FUENTES.md`, `spec.md`, `plan.md`, `contracts/terminacion.md` y `tasks.md` |
| TEST | — |
| DONE_WHEN | Gate en PASS |

### T002 · Migración, modelo, permiso, catálogos de auditoría y SoD

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 1. Claude fija el diseño completo: nombre, clase SENSITIVE y concesión según el patrón de 0119 |
| EGRESS_SAFE | 1 |
| FILES | `alembic/versions/0122_gov_cnt07_terminacion.py`, `models.py`, `setup/api.py`, `mfa_policy.py`, `audit_catalog_entries.py`, `service_sod.py`, `tests/test_audit_catalog_backup.py` y las cabeceras de prueba de la cabeza |
| TEST | `alembic upgrade`, `downgrade` y `upgrade`; MFA-G00; CATB-03 (584) |
| DONE_WHEN | Las pruebas de catálogo pasan |

### T003 · Servicio `service_contratos_terminacion.py`

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 1 (autoridad y aislamiento). Claude fija cada regla, el orden y los códigos (spec y contrato de datos) |
| EGRESS_SAFE | 1 |
| FILES | El servicio nuevo |
| TEST | T005 |
| DONE_WHEN | mypy y ruff limpios; T005 en verde |

### T004 · API y guardas

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 1 (frontera de permisos). Claude fija rutas y dependencias |
| EGRESS_SAFE | 1 |
| FILES | `api_contratos_terminacion.py`, `main.py`, guardas en CNT-02/03/04 (§Guardas), `condiciones` de CNT-09, `ficha` de CNT-01 e integración en CNT-08 (`service_expediente_contractual.py`) |
| TEST | T005; regresión de CNT-01/02/03/04/08/09 |
| DONE_WHEN | Regresión dirigida en verde |

### T005 · Pruebas PG

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 0 |
| EGRESS_SAFE | 1 |
| FILES | `tests/test_gov_cnt07_terminacion.py` |
| TEST | PG |
| DONE_WHEN | Casos de §46 en verde; M1–M8 muertas |

### T006 · Frontend

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 0 |
| EGRESS_SAFE | 1 |
| FILES | `TerminacionContratoPage.tsx` y su test, `api.ts` de contratos, `router.tsx`, `pantallas.ts`, `ContratoPage.tsx`, sección de CNT-08 y su test |
| TEST | Vitest, tsc, eslint y build |
| DONE_WHEN | Todo en verde |

### T007 · E2E del sponsor y negativos

| Campo | Valor |
|---|---|
| EXECUTOR | DEEPSEEK |
| MODEL | deepseek-v4-pro |
| SECURITY_SENSITIVE | 0 |
| EGRESS_SAFE | 1 |
| FILES | `e2e/gobierno-contratos-terminacion.spec.ts` (y un helper, si hace falta) |
| TEST | `qa/e2e-run.py` |
| DONE_WHEN | 1280, 390 y 320 px; Axe |

### T008 · Fixtures, evidencia, matrices, PG completa, UAT y cierre

| Campo | Valor |
|---|---|
| EXECUTOR | CLAUDE |
| MODEL | n-a |
| SECURITY_SENSITIVE | 0 |
| EGRESS_SAFE | n-a |
| FILES | Fixtures, `evidence/`, matrices y memoria |
| TEST | PG completa, Vitest completo, E2E y humo de la UAT |
| DONE_WHEN | Push con `HEAD == origin/develop` |
