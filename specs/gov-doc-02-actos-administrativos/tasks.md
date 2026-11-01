# Tareas · GOV-DOC-02 Actos administrativos

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`.
`EGRESS_SAFE`: sí (datos sintéticos; sin contraseñas ni rutas del equipo en los encargos).

## Phase 0: Entorno de prueba de la dueña

- [x] T000 HUMO-UAT-01: humo autenticado con usuario sintético de consulta sobre la pila persistente (`e2e/uat-humo-gobierno.spec.ts`) · DEEPSEEK · flash · 0 reintentos · `evidence/UAT_SMOKE.md`

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov_doc02_actos.py` (GA-01..): registro, campos, autoridad y competencia, número duplicado, faltantes, emitir con documento y congelado, eficacia por carácter y medio (vectores de fechas, prensa + 15 días), corrección, revocación y nulidad por referencia, borrado de borrador, historial, `If-Match`, CSV, autoridades, auditoría, permisos, MFA, módulo, aislamiento · DEEPSEEK · pro · SECURITY_SENSITIVE sí · DONE_WHEN falla en rojo sin el código · HECHO: GA-01..GA-36 36/36 en PostgreSQL (GA-32..36 añadidas por mutantes supervivientes)
- [x] T002 Modelos y migración 0066 · DEEPSEEK · pro · TEST cabeza única y ciclo de migración en PG · HECHO: 0066, ciclo upgrade/downgrade/upgrade en PG
- [x] T003a Esquemas `schemas_actos.py` · DEEPSEEK · pro · HECHO
- [x] T003b Servicio: listar, crear, obtener, modificar, eliminar, autoridades, exportar, versiones · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO
- [x] T003c Servicio: emitir, eficacia, corregir, revocar, anular · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO
- [x] T004 API `api_actos.py` y registros (router, permisos, `ResourceKind`, 9 acciones de auditoría + espejo, MFA) · DEEPSEEK · HECHO: 13 operaciones; catálogo 262
- [x] T005 Guardas y contratos (cabeza 0066, catálogo, N9 + semilla, MFA, techo de delegación, permisos de instalación) + fixtures del frontend (herramienta) · DEEPSEEK + herramienta · HECHO: guardas en verde; fixtures regenerados
- [x] T006a Frontend: contrato (`api.ts`), rutas, `pantallas.ts`, menú · DEEPSEEK · HECHO
- [x] T006b Pantalla del registro del año · DEEPSEEK · HECHO
- [x] T006c Formulario del acto · DEEPSEEK · HECHO
- [x] T006d Pantalla del acto · DEEPSEEK · HECHO
- [x] T006e Diálogos: emitir, eficacia, corregir, revocar/anular · DEEPSEEK · HECHO (+ T006e1f: suma de días en el módulo central de fechas, ADR-020)
- [x] T007 Pruebas de frontend (vitest) · DEEPSEEK · HECHO: vitest 899/899 (+82 casos de DOC-02)
- [x] T008 E2E `e2e/gobierno-actos.spec.ts` (login → menú → proceso completo; consulta; registrador sin `issue`; otro ente; validaciones; axe 1280/768/320) + regresión ORG-01/02/03 · DEEPSEEK · HECHO: DOC2-E2E-01..07 ×3 navegadores + HUMO-UAT-01 (82/82) y canónica 415/415 (T008a..g)
- [x] T009 Mutaciones de negocio (herramienta de Claude) · CLAUDE · n-a · HECHO: 43 mutantes, 42 KILLED, 1 EQUIVALENT, 0 SURVIVED (`evidence/MUTATIONS.md`)
- [x] T010 Certificación (suites completas, E2E ×3 y canónica, base tras la E2E, OpenAPI, residuos, ficha, tarjeta UAT, métricas, humo UAT final) · CLAUDE · n-a · HECHO: PG 4175/0/18, SQLite 2786/0/1412, E2E Gobierno 82/82 y canónica 415/415, base tras la E2E 0, OpenAPI sin cambios ajenos, residuos 0, ficha, tarjeta, métricas (`evidence/REQUIRED_SUITE_INVENTORY.md`)
