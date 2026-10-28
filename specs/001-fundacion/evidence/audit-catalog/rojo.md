# Rojo atribuible (ciclo 04)

Cada prueba se aplicó ANTES que su corrección y se ejecutó sobre el producto anterior. Salidas literales (resumen de pytest/vitest):

## rojo_C04_T03.txt
```
FAILED tests/test_audit_record_contract.py::test_rec01_accion_no_catalogada_no_agrega_evento
FAILED tests/test_audit_record_contract.py::test_rec02_document_created_sin_company_id_exige_empresa
FAILED tests/test_audit_record_contract.py::test_rec03_evento_de_tenant_con_empresa_genera_scope_mismatch
FAILED tests/test_audit_record_contract.py::test_rec04_detalle_prohibido_o_no_permitido[kwargs0-AUDIT_DETAIL_FORBIDDEN]
FAILED tests/test_audit_record_contract.py::test_rec04_detalle_prohibido_o_no_permitido[kwargs1-AUDIT_DETAIL_FORBIDDEN]
FAILED tests/test_audit_record_contract.py::test_rec04_detalle_prohibido_o_no_permitido[kwargs2-AUDIT_DETAIL_KEY_NOT_ALLOWED]
FAILED tests/test_audit_record_contract.py::test_rec07_correlacion_por_contextvar
7 failed, 4 passed in 2.36s
```
## rojo_C04_T06_sqlite.txt
```
FAILED tests/test_audit_immutability.py::test_imm_02_delete_sql_rechazado - F...
FAILED tests/test_audit_immutability.py::test_imm_03_orm_rechazado - Failed: ...
FAILED tests/test_audit_immutability.py::test_imm_06_indice_existe - Assertio...
4 failed, 1 passed, 2 skipped in 1.29s
```
## rojo_C04_T06_pg.txt
```
FAILED tests/test_audit_immutability.py::test_imm_03_orm_rechazado - Failed: ...
FAILED tests/test_audit_immutability.py::test_imm_04_truncate_rechazado - Fai...
FAILED tests/test_audit_immutability.py::test_imm_06_indice_existe - Assertio...
5 failed, 1 passed, 1 deselected in 1.44s
```
## rojo_C04_T07.txt
```
25 failed in 10.28s
```
## C04-T04 (CTX, SQLite)
Con el catálogo activo y la emisión antigua: `AUDIT_ACTION_LEGACY: DOCUMENT_TYPE_CREATED/Document` (×3) y `AUDIT_COMPANY_REQUIRED: CREATE/unit_of_measure` → 6 failed; tras T04a/b, CTX-01/02/04/06 verdes (CTX-03/05 eran defectos de la prueba, corregidos en r2).
## C04-T08 (AF)
10 failed, 1 passed: `/audit/filters` 404, `KeyError: details`, filtros ignorados (fechas, empresa y usuario).
## C04-T11 (frontend)
3 failed | 11 passed: ISO crudo en Reportes › Auditoría y mensajes de SCAN_FAILED sin categoría → 14/14.
## R3 (control)
El filtro de lectura vigente ya cumplía OD-AUD-01: AF-05, AUD-TENANT-09 y AUDIT-E2E-02 pasan sobre el producto anterior (verde de control, sin defecto).
