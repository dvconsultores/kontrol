# SPEC 008 · Delta dirigida — WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY

Dueña: Spec 008. Contrato: ADR-D0-014 (catálogos `Scope.COMPANY`). Precedente: `_exige_sucursal_propia`
(WAREHOUSE-BRANCH-CROSS-COMPANY) y `create_establishment`. Fecha 2026-10-19, `develop`, HEAD de partida `870c40b`.
Evidencia: `evidence/warehouse-catalog-type-cross-company/`.

## 1. Specify
Las ubicaciones y las zonas de la empresa A aceptan y persisten tipos de catálogo de otra empresa o de otro tenant, en el
alta, en el alta masiva y en la edición. La lectura posterior expone el código del tipo ajeno.

## 2. Clarify
- **Contrato de error**, con la convención `MOVEMENT_TYPE_NOT_FOUND`, `PERMIT_TYPE_NOT_FOUND` y
  `DOCUMENT_TYPE_NOT_FOUND`:
  - 404 `LOCATION_TYPE_NOT_FOUND`, «Tipo de ubicación no encontrado».
  - 404 `ZONE_TYPE_NOT_FOUND`, «Tipo de zona no encontrado».
- Un tipo ajeno, de otro tenant o inexistente da la misma respuesta.
- `null` y omitir el campo mantienen la semántica vigente.
- Los tipos inactivos de la propia empresa son otra semántica y quedan fuera.
- La alta masiva valida también en vista previa: una vista previa con un tipo ajeno no es una operación legítima.
- MATERIAL_OQ 0.

## 3. Plan
Un ayudante `_exige_tipo_propio(db, ctx, modelo, tipo_id, code, message)`, junto a `_exige_sucursal_propia`. Puntos de
llamada:
- `create_location_full`, tras resolver el código (precede `LOCATION_CODE_REQUIRED` y `LOCATION_CODE_EXHAUSTED`).
- `bulk_locations`, tras validar el patrón y antes de la vista previa (precede `LOCATION_PATTERN_INVALID`).
- `patch_location`, tras `_get_location`, `_check_version` y `_get_warehouse`, solo si el cuerpo trae el campo y antes de
  reubicar o mutar.
- `_create` de nodo, solo en zonas, tras `STRUCTURE_LEVEL_DISABLED` y la validación del padre.
- `_patch` de nodo, solo en zonas y solo si el cuerpo trae el campo, tras `_get_node`, `_check_version` y `_get_warehouse`,
  antes de mutar.

**OBS-01.** O01-07, O01-08 y O01-09 neutralizan la validación previa con `monkeypatch`, solo dentro de la prueba, para seguir
alcanzando la clave foránea real. Así conservan sus aserciones del 500 intacto y no se pierde cobertura.

Sin migración, sin esquema y sin cambio de OpenAPI.

## 4. Constitution gate
P6 ✔ · ADR-D0-014 ✔ · P21 ✔ · sin esquema ni migración ✔ · sin fail-open ✔ · sin oráculo ✔ · OBS-09 sin solape ✔ ·
OBS-01 y WAREHOUSE-BRANCH preservadas ✔.

## 5. Checklist · tareas
| Tarea | EXECUTOR | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| K01 diagnóstico, diseño, brief | CLAUDE | n-a | delta, evidencia | gate material |
| K02 producto + pruebas | DEEPSEEK | deepseek-v4-pro | `warehouse_api.py`, `tests/test_warehouse_catalog_scope.py`, `tests/test_warehouse_integrity.py` (O01-07/08/09 + import) | AUDIT_PASS, ruff, mypy, dos motores, rojo en HEAD |
| K03 mutaciones, certificación | CLAUDE | n-a | evidencia | gate de cierre |
SECURITY_SENSITIVE sí (aislamiento): diseño y auditoría de Claude, escritura de DeepSeek. RETRY_MAX 2.

## 6. Analyze · trazabilidad
- R1, alta de ubicación: C01–C04.
- R2, alta masiva: C05, C06, C06b.
- R3, PATCH de ubicación: C07, C08.
- R4, alta de zona: C09–C12.
- R5, PATCH de zona: C13, C14.
- R6 y R7, misma respuesta sin oráculo: C04, C12, C27.
- R8, sin escritura: C02, C06, C08, C14.
- R9, `null`: C15. R10, campo omitido: C16.
- R11, orden: C17–C23.
- Contexto de empresa: C24, C25.
- Estructura: C28, C29.
- OBS-01: O01-07, O01-08, O01-09.

BLOCKER 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 %.

## 7. Gate material
ROOT_CAUSE_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 · CONTRACT_CONFIRMED 1 · PRE_FIX_DEFECT_REPRODUCED 1 ·
LOCATION_TYPE/ZONE_TYPE_CONTRACT_CONFIRMED 1/1 · ERROR_CODES_CONFIRMED 1 · CREATE/PATCH/BULK_PATHS_IDENTIFIED 1/1/1 ·
ORDERING_CONFIRMED 1 · OBS01_IMPACT_UNDERSTOOD 1 · SCOPE_BOUNDED 1 · OWNER_DECISION_REQUIRED 0 · MIGRATION_REQUIRED 0 ·
BACKFILL_REQUIRED 0 · OBS09_OVERLAP 0 · WAREHOUSE_BRANCH_OVERLAP 0 (mismo fichero, otra función) · MATERIAL_OQ 0 ·
UNKNOWN 0 → **implementación autorizada**.

## 8. Implementación (DeepSeek escribe, Claude audita) — `orchestration.md`
- `_exige_tipo_propio` consulta la empresa del tipo con una sola sentencia. Un tipo inexistente devuelve `None` y da el
  mismo 404 que uno ajeno.
- Las cinco llamadas están en el orden fijado.
- O01-07, O01-08 y O01-09 neutralizan la validación previa con `monkeypatch`, sin cambiar aserciones.
- Hubo 4 llamadas ($0,036), 2 rechazos (mypy por un defecto del diseño de Claude, y una respuesta truncada) y la
  reclasificación en K02a y K02b.
## 9. Pruebas, mutaciones, certificación — `directed-tests.md`, `mutation-campaign.md`, `certification.md`
- **Dirigidas:** 28/28 en los dos motores, solas y en orden inverso. Contra HEAD fallan 13, justo las de la fuga.
- **Mutaciones:** 17/17 muertas, y OBS-01 revalidada.
- **Suites:** SQLite 1859/0/1046 ×2 y PostgreSQL 2879/0/26. OpenAPI queda en 544/533/11.
- **E2E:** 273/7 por una firma ambiental nueva, el pool agotado bajo paginación del equipo, no atribuible al cambio.
## 10. Estado — `convergence.md`: **IMPLEMENTED — E2E CERTIFICATION BLOCKED BY ENVIRONMENT** (2026-10-19)
Observación nueva, no absorbida: `E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING`. El middleware de licencia agota el pool de 5+10
cuando el equipo pagina. No está demostrada como defecto de producto.
