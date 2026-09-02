# N10 — TRAZABILIDAD GLOBAL

| Fase | Objeto | Artefacto | Prueba | Cobertura |
|---|---|---|---|---|
| N0 | Decisiones y ADR | `spec.md`, `adr/` | `test_architecture_scope` | 100% |
| N1 | `CompanyContext` | `contracts/` | `test_mc_company_isolation` | 100% |
| N2 | Escritores y lectores | `canonical-scope-matrix.md` | `test_no_company_scope_writer_uses_tenant_id` | 100% |
| N3 | Esquema | `n3-schema-expand-report.md` | `test_n7_structure` | 100% |
| N4 | Migración de legado | `n4-*.md` | `test_mc_preflight` + fixture hostil | 100% |
| N5 | Dominios | `n5-*.md` | 8 suites A/B | 100% |
| N6 | Frontend | `n6-*.md` | 278 pruebas + E2E | 100% |
| N7 | Restricciones | `n7-*.md` | `test_n7_corruption`, `test_n7_structure` | 100% |
| N8 | Contrato y retirada | `n8-*.md` | `test_n8_contract` | 100% |
| N9 | Documentos y Spec 046 | `n9-*.md` | `test_n9_resourcekinds`, `test_n9_integrity` | 100% |
| N10 | Convergencia global | `n10-*.md` | `test_n10_convergence`, `test_n10_cross_company_writes`, `test_n10_cross_tenant` | 100% |

## Requisitos de N10 con su prueba

| Requisito | Prueba |
|---|---|
| FR-N10-011/012 · alcance clasificado, 0 indeterminados | `test_all_persistent_models_have_declared_scope` |
| FR-N10-014/015 · rutas de tenant válidas | `test_toda_tabla_de_tenant_dice_por_donde_llega_a_su_tenant` |
| FR-N10-016 · rutas derivadas no anulables | `test_derived_scopes_use_non_nullable_fk_path` |
| FR-N10-020 · paridad ORM/Alembic/PostgreSQL | `test_el_orm_y_la_base_no_difieren_en_nada` |
| FR-N10-021/023 · contrato de la API sin huecos | `test_ninguna_operacion_de_la_api_queda_sin_alcance` |
| FR-N10-024/027 · escrituras entre empresas | `test_n10_cross_company_writes` (11) |
| FR-N10-025 · cruces de tenant | `test_n10_cross_tenant` (4) |
| FR-N10-028 · lectores incorrectos | `test_los_establecimientos_de_otra_empresa_no_se_listan` |
| FR-N10-023 · rutas sin contexto | `test_ninguna_ruta_recibe_un_id_de_empresa_sin_ver_el_contexto` |
| FR-N10-032..038 · N4 y estrategias | `test_mc_preflight` |
| FR-N10-039..044 · registro documental | `test_n9_resourcekinds`, `test_n9_integrity` |

Requisitos sin tarea: 0 · Tareas sin requisito: 0 · Huérfanos: 0.
