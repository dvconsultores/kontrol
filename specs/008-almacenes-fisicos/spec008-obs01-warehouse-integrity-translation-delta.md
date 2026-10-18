# SPEC 008 · Delta dirigida — OBS-01 · WAREHOUSE-INTEGRITY-TRADUCE-TODO

Dueña: Spec 008 (almacenes físicos). Apoyo: Spec 001 (`app/core/integrity.py`, helper común). Fecha 2026-10-18, rama
`develop`, HEAD de partida `76b7b00`. Evidencia: `evidence/obs01-warehouse-integrity-translation/`.

## 1. Specify
Un `IntegrityError` en las altas de la estructura física se contesta siempre como «ya existe» (409 `*_CODE_DUPLICATE`),
también cuando la causa es una clave foránea rota u otra restricción.

## 2. Clarify · decisión de la dueña (2026-10-18, vinculante)
- Solo la violación única **reconocida** de la restricción del código se traduce al 409 de dominio, en cualquier motor,
  SQLite incluido.
- Cualquier otro `IntegrityError` se relanza al manejador genérico: 500 `INTERNAL_ERROR` saneado.
- Sin migraciones, sin esquema, sin cambio de concurrencia ni del contrato público del duplicado.
CLARIFY: el «código único de almacén» de la decisión abarca las cinco altas del mismo fichero, cada una con su restricción
de código. Es el alcance que registra OBS-01, con el mismo defecto y la misma corrección.

## 3. Plan
- **`app/core/integrity.py` (apoyo 001).** Se añaden dos funciones y `es_violacion_unica` queda intacta, así que sus siete
  llamantes no cambian.
  - `restriccion_unica(tabla, nombre)` resuelve la `UniqueConstraint` declarada. Falla al importar si el nombre no existe.
  - `es_violacion_unica_de(error, restriccion)` reconoce PostgreSQL por `pgcode 23505` más el nombre de la restricción.
    Reconoce SQLite por `sqlite3.IntegrityError` con `sqlite_errorcode == 2067 (SQLITE_CONSTRAINT_UNIQUE)` y el mensaje
    **exactamente igual** a `UNIQUE constraint failed: <tabla>.<c1>, <tabla>.<c2>`, derivado de las columnas declaradas.
    No compara subcadenas ni listas de mensajes. Es la única señal que SQLite ofrece, porque no da nombre de restricción.
- **`warehouse_api.py`.** Se retira `_integrity`. Cada uno de los cinco sitios hace `rollback`, relanza con `raise` si no es
  la violación de su restricción, y si lo es lanza el `ConflictError` de siempre. Es el patrón hermano de
  `treasury/rates.py` e `inventory/service.py`.
- **Pruebas.** Se crea `tests/test_warehouse_integrity.py`, con HTTP real en los dos motores y errores reales del driver.

## 4. Constitution gate
P21 (PostgreSQL autoridad, SQLite sin degradar) ✔ · P6 (aislamiento antes que dominio) ✔ · sin esquema ni migración ✔ ·
sin fail-open (lo desconocido se relanza) ✔ · sin fuga de detalle (manejador genérico vigente) ✔ · OBS-09 sin solape ✔.

## 5. Checklist · 6. Tasks
| Tarea | EXECUTOR | MODEL | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| T01 diseño, brief, egress | CLAUDE | n-a | delta, evidencia | — | brief auditado |
| T02 helper + 5 sitios + pruebas | DEEPSEEK | deepseek-v4-pro | `app/core/integrity.py`, `app/modules/organization/warehouse_api.py`, `tests/test_warehouse_integrity.py` | O01-01…14 | AUDIT_PASS, ruff, mypy, dirigidas en los dos motores |
| T03 mutaciones, certificación, converge | CLAUDE | n-a | evidencia | campaña + suites | gate de cierre |
SECURITY_SENSITIVE no (contrato de error, sin auth) · EGRESS_SAFE sí · RETRY_MAX 2.

## 7. Analyze · trazabilidad
Decisión 1→O01-01…05 · 2/3→O01-06…08 · 4 (sin fuga)→O01-01, 06 · 5 (SQLite)→O01-10 y la prueba de carrera · 7→O01-01…05 ·
D5→O01-12/13 · contrato estructural→O01-14. BLOCKER 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 %.

## 8. Diagnóstico y gate material — `diagnosis.md`, `root-cause.md`
ROOT_CAUSE_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 · DUPLICATE_CONTRACT_CONFIRMED 1 · NON_UNIQUE_CONTRACT_CONFIRMED 1 ·
CONSTRAINT_IDENTIFIED 1 · ERROR_CODE_IDENTIFIED 1 · SESSION_STRATEGY_CONFIRMED 1 (`rollback` antes de traducir o relanzar,
igual que hoy) · POSTGRES/SQLITE_BEHAVIOR_MEASURED 1/1 · decisiones de arquitectura, seguridad o dueña 0 · OBS09_OVERLAP 0 ·
MATERIAL_OQ 0 · UNKNOWN 0 → **implementación autorizada**.

## 9. Implementación (DeepSeek escribe, Claude audita) — `orchestration.md`
`app/core/integrity.py` añade `restriccion_unica` y `es_violacion_unica_de`. `es_violacion_unica` queda intacta. En
`warehouse_api.py` desaparece `_integrity`; las restricciones se resuelven al importar; los cinco sitios hacen
`rollback → if not es_violacion_unica_de: raise → raise ConflictError` con los mismos códigos y mensajes. La prueba nueva es
`tests/test_warehouse_integrity.py` (O01-01…14). Hubo 4 llamadas ($0,023), 2 rechazos auditados y la reclasificación T02b.
## 10. Pruebas, mutaciones y certificación — `directed-tests.md`, `mutation-campaign.md`, `certification.md`, `openapi.md`
14/14 en los dos motores, solas y en orden inverso · mutaciones 15 KILLED + 1 EQUIVALENT justificada · SQLite 1814/0/1046 ×2 ·
PostgreSQL 2834/0/26 · E2E 284/0/0 · OpenAPI 544/533/11.
## 11. Convergencia — `convergence.md`: **CLOSED / CONVERGED 2026-10-18**.
Observación no absorbida: `POST /organization/warehouses` acepta un `branch_id` del cuerpo sin validar. Con un identificador
inexistente ahora responde 500, que es lo que la dueña decidió. No se midió si una sucursal de **otra** empresa del tenant se
acepta: queda como candidata para un ciclo propio, sin causa demostrada.
