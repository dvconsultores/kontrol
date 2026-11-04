# Tareas · GOV-CTL-04 Consulta y muestreo read-only del auditor (+ FIND-ORG07-01)

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`.
`EGRESS_SAFE`: sí (datos sintéticos; sin contraseñas ni rutas del equipo en los encargos).

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov_ctl04_auditoria.py` (GX-…): alcance de Gobierno (privados, otra empresa, otro tenant), filtros y fechas, detalle y evidencia segura, rastreo, tres medios de muestreo, reproducibilidad, inmutabilidad, CSV auditado, permisos · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T002 Modelos + migración `0069_gov_ctl04_auditoria` (2 tablas, disparadores, permisos) + registros (setup, MFA, guardas) · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003 Esquemas y servicio `schemas_auditoria.py` / `service_auditoria.py` · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T004 API `api_auditoria.py`, registro, 2 acciones de auditoría + espejo del catálogo · DEEPSEEK · flash
- [x] T005 [FIND-ORG07-01] `competencias_en_vigor` + DOC-02 `_validar_autoridad` y `autoridades`; pruebas A–F · DEEPSEEK · pro
- [x] T006 Frontend: contrato `api.ts`, rutas, `pantallas.ts`, menú, fixtures · DEEPSEEK · flash
- [x] T007 `AuditoriaInstitucionalPage` + `MuestraPage` · DEEPSEEK · pro
- [x] T008 Pruebas de frontend (vitest) · DEEPSEEK · pro
- [x] T009 E2E `e2e/gobierno-auditoria.spec.ts` + humo UAT con 7 pantallas · DEEPSEEK · pro
- [x] T010 Mutaciones de negocio · CLAUDE · n-a
- [x] T011 Certificación (suites, E2E ×3 y canónica, base tras la E2E, OpenAPI, residuos, ficha, tarjeta UAT, métricas, relevo UAT + humo-uat) · CLAUDE · n-a

## Phase 2: Convergence

- [x] T012 Enlazar cada documento citado del panel de evidencia a `/documentos/{id}`, visible solo con `documentos:view` (sin la capacidad, el id como texto), con sus pruebas vitest per spec §4.3 (partial) · DEEPSEEK · flash
- [x] T013 [FIND-CTL04-01, QA, autorizado por la dueña] `e2e/auditoria-sobre.spec.ts`: eventos controlados por el paso de contraseña del login (`MFA_CHALLENGE_ISSUED` o `LOGIN_SUCCESS`), sin consumir pasos TOTP; después, canónica nueva del árbol completo · DEEPSEEK · flash
