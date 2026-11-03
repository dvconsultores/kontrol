# Tareas · GOV-ORG-07 Matriz auditable de autoridad

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`.
`EGRESS_SAFE`: sí (datos sintéticos; sin contraseñas ni rutas del equipo en los encargos).

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov_org07_autoridad.py` (GM-…) · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO: rojo atribuible (404 de la ruta); subtareas T001d (unidad del ejercicio anterior), T001e (GM-13/15/19), T001f/T001g (mutantes supervivientes, GM-21); GM-01..21 21/21 en PostgreSQL
- [x] T002 Migración `0068_gov_org07_autoridad` y registros · DEEPSEEK · flash · HECHO: permiso + concesión a FUNCIONAL_COMPLETO; MFA 47/40; techo 104; cabeza 0068 en las guardas (149 pasan)
- [x] T003 Esquemas `schemas_autoridad.py` · DEEPSEEK · pro · HECHO: 13 esquemas `Matriz*` sin colisión en OpenAPI
- [x] T004 Servicio `service_autoridad.py` · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO: proyección única `_filas_filtradas` (reintentos 1–2: tipado, doble cálculo, texto por campo, unidad del detalle); T004b valida filtros también sin cargos (GM-20)
- [x] T005 API `api_autoridad.py`, registro y auditoría · DEEPSEEK · flash · HECHO: 5 rutas GET; `GOV_AUTHORITY_MATRIX_EXPORTED` (catálogo 270, espejo v2026-11-02.2)
- [x] T006 Frontend: contrato, ruta, `pantallas.ts`, menú · DEEPSEEK · flash · HECHO; T006b nombres literales de consulta (guardián QC-02)
- [x] T007 `MatrizAutoridadPage` + panel de detalle · DEEPSEEK · pro · HECHO (reintentos: tipos, paginación/detalle en la URL, búsqueda controlada, error de fecha en el campo); T007b plural «autorizaciones»; T007c regiones desplazables enfocables (axe a 768 px)
- [x] T008 Pruebas de frontend (vitest) · DEEPSEEK · pro · HECHO: MTZ-01..19 + CDM-01..04 + GSB-12/13 (T008b, T008c)
- [x] T009 E2E `e2e/gobierno-autoridad.spec.ts` + humo UAT con 6 pantallas · DEEPSEEK · pro · HECHO: ORG7-E2E-01..05 (T009b lógica, T009c código de 404 sin estructura)
- [x] T010 Mutaciones de negocio · CLAUDE · n-a · HECHO: 42 mutantes, 39 KILLED, 3 EQUIVALENT, 0 supervivientes (`evidence/MUTATIONS.md`)
- [x] T011 Delta QA-LIC-GOB-01 · DEEPSEEK · flash/pro · HECHO: QA-A T011a (entitlements de la siembra; `--modulos`), QA-B T011b (proyecto `licencia-estado` tras chromium), QA-C T011c (`n6-a11y-responsive`, `route-crawl`, CSEL-01/02); canónica 425/425 → QA_LIC_GOB_01 = CLOSED
- [x] T012 Certificación · CLAUDE · n-a · HECHO: PG 4225/0, SQLite 2786/0, vitest 998, ORG-07 E2E 15/15, canónica 425/425, base tras la E2E 0, OpenAPI sin cambios ajenos, métricas 64/1280 y 6/122 (`evidence/REQUIRED_SUITE_INVENTORY.md`); relevo UAT tras el commit (`evidence/UAT_SMOKE.md`)
