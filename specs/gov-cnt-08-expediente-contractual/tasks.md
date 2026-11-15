# Tareas · CNT-08

## CONSTITUTION GATE (antes del código)

```text
GOV_CNT_009_CLEAR=1
CONTRACT_ROOT_CLEAR=1            (C08-01; CNT-01 FORMALIZADO; D08-01)
PROCUREMENT_SOURCE_CLEAR=1       (PROC-03/06/08 por los FK del contrato)
BUDGET_SOURCE_CLEAR=1            (BUD-06 por las asignaciones de CNT-01/02 y procurement_file_id; BUD-08 por procurement_file_id)
CNT01_SOURCE_CLEAR=1             (service_contratos.ficha)
CNT02_SOURCE_CLEAR=1             (service_contratos_modificaciones.historia)
CNT04_SOURCE_CLEAR=1             (service_contratos_supervision.supervision/supervisor_en)
CNT03_CONSUMER_CONTRACT_CLEAR=1  (FUENTES_FUTURAS; SOURCE_PROCESS_NOT_AVAILABLE hasta que P1 publique)
DOCUMENT_SOURCE_CLEAR=1          (documents.service + storage.exists/verify; folios PROC-03)
AUDIT_SOURCE_CLEAR=1             (AuditEvent + service_auditoria._resumenes; /gobierno/auditoria?evento=)
DOSSIER_IS_PROJECTION=1
EXPORT_STRATEGY_CLEAR=1          (D08-02)
DOC08_REUSE_CLEAR=1              (_evaluar, _json_bytes, _sha256, _copiar_subida, _entradas_seguras, _huella_de_entrada, storage)
SNAPSHOT_CONSISTENCY_CLEAR=1     (R7 REPEATABLE READ)
INTEGRITY_RULE_CLEAR=1           (R3)
CONTROL_FISCAL_ACCESS_CLEAR=1    (C08-14, D08-07)
P1_P2_OVERLAP=0
MATERIAL_DECISION_REQUIRED=0
BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0 UNKNOWN=0 TRACEABILITY=22/22
CONSTITUTION_GATE=PASS
```

## Tareas

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Arqueología, fuentes, spec, plan, contrato de datos y gate | CLAUDE | n-a | NO | SÍ | 2 | `specs/gov-cnt-08-expediente-contractual/*` | — | Gate en PASS |
| T002 | Migración 0119, modelos y guardas, catálogo de auditoría (+4) y cabeceras de prueba | DEEPSEEK | deepseek-v4-pro | SÍ (diseño fijado por Claude) | SÍ | 2 | `0119_gov_cnt08_expediente.py`, `models.py`, `audit_catalog_entries.py`, `test_audit_catalog_backup.py`, 3 pruebas de cabecera | Alembic up/down/up; catálogo; n10 | Cabeza única 0119 |
| T003 | Servicio de proyección (R1–R5) | DEEPSEEK | deepseek-v4-pro | SÍ (aislamiento fijado) | SÍ | 2 | `service_expediente_contractual.py` | T005 | ruff, mypy y T005 |
| T004 | Paquete (R6–R8), esquemas, API y `main` | DEEPSEEK | deepseek-v4-pro | SÍ | SÍ | 2 | `service_expediente_paquetes.py`, `api_expediente_contractual.py` (reutiliza `PaqueteIn`), `main.py` | T005 | ruff, mypy y T005 |
| T005 | Pruebas PG (C08-01..21) | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `tests/test_gov_cnt08_expediente_contractual.py` | Ella misma | En verde y con mutaciones muertas |
| T006 | Frontend con dos pantallas, API, rutas, menú y enlace, más Vitest | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `modules/gobierno/expedientes-contractuales/*`, `router.tsx`, `pantallas.ts`, `Sidebar.tsx`, `ContratoPage.tsx` | Vitest, tsc y eslint | En verde |
| T007 | E2E del sponsor (§52), responsive y Axe | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `e2e/gobierno-expediente-contractual.spec.ts` | E2E | 1/1 |
| T008 | Fixtures OpenAPI, evidencia, matrices, convergencia, UAT y publicación | CLAUDE | n-a | NO | SÍ | — | fixtures, `evidence/*`, matrices | Suite final | Informe |

`DEEPSEEK_TARGET=3..5`, `CAP=8` y `OWNER_EXCEPTION_INHERITED=0`.

T002 y T004 van juntas en una llamada, porque el paquete necesita el modelo. Orden de llamadas: T003, T002+T004, T005, T006 y T007, cinco en total; quedan 3 de reserva para reintentos.
