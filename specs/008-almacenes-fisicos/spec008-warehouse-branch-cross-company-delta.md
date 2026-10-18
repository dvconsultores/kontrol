# SPEC 008 · Delta dirigida — WAREHOUSE-BRANCH-CROSS-COMPANY

Dueña: Spec 008 (almacenes físicos). Contrato: ADR-D0-014 / ARCH-MC-001 (alcance canónico de empresa). Fecha 2026-10-18,
`develop`, HEAD de partida `e8501f2`. Evidencia: `evidence/warehouse-branch-cross-company/`.

## 1. Specify
El alta y la edición de un almacén aceptan una sucursal de otra empresa del tenant, e incluso de otro tenant, y lo
persisten (medido: D1-D3).

## 2. Clarify
- El contrato ya está escrito. ADR-D0-014 dice que el contexto lo decide el servidor, y cada referencia de empresa es
  de la empresa activa.
- El precedente exacto es `create_establishment`: una sucursal ajena o inexistente da 404 `BRANCH_NOT_FOUND`, «Sucursal no
  encontrada».
- `branch_id` sigue siendo opcional. Omitirlo o enviar `null` sigue valiendo, también en `PATCH` para desligar.
- MATERIAL_OQ 0.

## 3. Plan
- Un ayudante del router, `_exige_sucursal_propia(db, ctx, branch_id)`. Si `branch_id` es `None` no hace nada; si la
  sucursal no existe o su `company_id` no es `ctx.company_id`, lanza `NotFoundError("BRANCH_NOT_FOUND")`.
- Se llama en `create_warehouse_full` antes de construir la fila, y en `patch_warehouse` tras `_check_version` y antes de
  mutar, solo si el cuerpo trae `branch_id`.
- Sin migración, sin esquema, sin cambio de OpenAPI. El 404 ya es un error documentado del router.
- Las filas cruzadas que ya existan no se reparan aquí: es un backfill, `CLAUDE_ONLY`, y no está autorizado.
- Prueba nueva: `tests/test_warehouse_branch_scope.py`, en los dos motores, con un mundo propio de dos empresas y dos tenants.
- Adaptación justificada de `test_o01_06`. Con la validación previa, una sucursal inexistente ya no llega a la base. La rama
  500 del sitio de almacén sigue fijada por O01-10, por O01-14 y por la mutación M02 de OBS-01. Los 500 por HTTP siguen
  probados en ubicación (07) y zona (08).

## 4. Constitution gate
P6 (aislamiento en el servidor) ✔ · ADR-D0-014 ✔ · P21 (PostgreSQL autoridad; SQLite sin degradar) ✔ · sin esquema ni
migración ✔ · sin fail-open ✔ · sin oráculo de enumeración (inexistente = ajena) ✔ · OBS-09 sin solape ✔ · OBS-01 preservada ✔.

## 5. Checklist · tareas
| Tarea | EXECUTOR | MODEL | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| B01 diagnóstico, diseño, brief | CLAUDE | n-a | delta, evidencia | sonda | gate material |
| B02 producto + pruebas | DEEPSEEK | deepseek-v4-pro | `warehouse_api.py`, `tests/test_warehouse_branch_scope.py`, `tests/test_warehouse_integrity.py` (solo O01-06) | B-01…15 + O01 | AUDIT_PASS, ruff, mypy, dos motores |
| B03 mutaciones, certificación, converge | CLAUDE | n-a | evidencia | campaña + suites | gate de cierre |
SECURITY_SENSITIVE **sí** (aislamiento de empresa y tenant): el diseño, el contrato y la auditoría son de Claude, y la
escritura de DeepSeek, por la regla permanente 1. EGRESS_SAFE sí. RETRY_MAX 2.

## 6. Analyze · trazabilidad
D1→B-02, B-12 · D2→B-03 · D3→B-07, B-08 · nominal→B-01, B-05, B-06, B-09, B-10, B-11 · sin oráculo→B-04 · precedencia→B-13,
B-14 · contrato estructural→B-15 · OBS-01→O01-06 adaptada, O01-01…14. BLOCKER 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 %.

## 7. Diagnóstico y gate material — `diagnosis.md`, `root-cause.md`
ROOT_CAUSE_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 · CONTRACT_CONFIRMED 1 · SCOPE_BOUNDED 1 · OBS09_OVERLAP 0 ·
ARCHITECTURE/SECURITY/OWNER_DECISION_REQUIRED 0/0/0 · MATERIAL_OQ 0 · UNKNOWN 0 → **implementación autorizada**.

## 8. Implementación (DeepSeek escribe, Claude audita) — `orchestration.md`
- Se añade `_exige_sucursal_propia`. Una sucursal ajena, de otro tenant o inexistente da el mismo 404 `BRANCH_NOT_FOUND`.
- Se llama en el alta, después de `COMPANY_NOT_FOUND` y de `WAREHOUSE_CODE_REQUIRED`.
- Se llama en el PATCH, después de `_check_version` y antes de mutar, solo si el cuerpo trae `branch_id`.
- O01-06 se adapta como estaba previsto.
- Hubo 4 llamadas ($0,014), 2 rechazos y la reclasificación B02b.
## 9. Pruebas, mutaciones, certificación — `directed-tests.md`, `mutation-campaign.md`, `certification.md`
- **Dirigidas:** 17/17 en los dos motores, solas y en orden inverso. Contra HEAD fallan justo las del defecto.
- **Mutaciones:** 12/12 muertas, y la campaña de OBS-01 revalidada.
- **Suites:** SQLite 1831/0/1046 ×2 y PostgreSQL 2851/0/26. OpenAPI queda en 544/533/11.
- **E2E:** dos corridas con 275 verdes y 5 fallidas de carga documental, atribuidas al entorno con control de HEAD y
  medición de clamscan.
## 10. Estado — `convergence.md`: **IMPLEMENTED — E2E CERTIFICATION BLOCKED BY ENVIRONMENT** (2026-10-19)
Observaciones nuevas, no absorbidas:
- **WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY**, medida: una ubicación o una zona de A aceptan el `location_type_id` o el
  `zone_type_id` de B (200).
- **Filas cruzadas ya existentes.** No se detectan ni se reparan, porque sería un backfill no autorizado. Hace falta una
  consulta de solo lectura por instalación, decidida por la dueña.
- **`CompanyContext.branch_ids`.** Es el límite de sucursales del usuario, y este cambio no lo aplica a la sucursal del
  almacén, igual que el precedente de establecimientos. No se midió si debe hacerlo.
- **Restricción en base.** Una FK compuesta `(company_id, branch_id)` exigiría migración, que no está autorizada.
