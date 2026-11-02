# Tareas · GOV-DOC-04 Notificaciones administrativas

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`.
`EGRESS_SAFE`: sí (datos sintéticos; sin contraseñas ni rutas del equipo en los encargos).

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov_doc04_notificaciones.py` (GN-…): alta de destinatario, duplicado, acto no particular o no emitido, oficio exigido, entrega con recibo, intento fallido, prensa solo tras fallo (+15 días), eficacia del acto cuando todos están notificados (fecha más tardía), anulación, inmutabilidad, `If-Match`, historial, CSV, permisos, MFA, aislamiento, auditoría · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO: GN-01..20 + GN-05b, 21/21 PostgreSQL (subtareas T001b, T001c)
- [x] T002 Modelos y migración 0067 · DEEPSEEK · pro · TEST cabeza única y ciclo en PG · HECHO: 3 modelos, 0067 ciclo 10 → 13 → 10 → 13 en PG, cabeza única
- [x] T003a Esquemas `schemas_notificaciones.py` · DEEPSEEK · pro · HECHO
- [x] T003b Servicio: listar, crear, obtener, modificar, anular, versiones, exportar · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO (T003d bloqueo acto → notificación; T003e salida plana; T003f fechas serializadas; T003h nombre de esquema sin colisión con 047)
- [x] T003c Servicio: registrar intento y eficacia del acto (AD-DOC04-02) · DEEPSEEK · pro · SECURITY_SENSITIVE sí · HECHO
- [x] T004 API y registros (router, permisos, `ResourceKind`, 7 acciones de auditoría + espejo, MFA) · DEEPSEEK · HECHO: router, permisos, ResourceKind, 7 acciones (catálogo 269, espejo v2026-11-02.1), MFA 47/39
- [x] T005 DOC-02 adaptado (PDD-DOC04-06): `/eficacia` PARTICULAR → 422; contadores en `ActoOut`; pruebas GA ajustadas · DEEPSEEK · HECHO: /eficacia PARTICULAR → 422; `notificaciones` en ActoOut; GA 36/36
- [x] T006 Guardas y contratos (cabeza 0067, catálogo, N9 + semilla, MFA, techo de delegación) + fixtures del frontend · DEEPSEEK + herramienta · HECHO: cabeza 0067, catálogo, N9 29 + semilla, MFA, techo 103; fixtures regenerados
- [x] T007a Frontend: contrato (`api.ts`), rutas, `pantallas.ts`, menú · DEEPSEEK · HECHO
- [x] T007b Lista de notificaciones · DEEPSEEK · HECHO
- [x] T007c Página de la notificación + paneles (destinatario, intento, anular) · DEEPSEEK · HECHO (T007c1 paneles, T007c2 página)
- [x] T007d Sección «Notificaciones» en `ActoPage`; `RegistrarEficacia` solo GENERAL · DEEPSEEK · HECHO
- [x] T008 Pruebas de frontend (vitest) · DEEPSEEK · HECHO: vitest 968/968 (+69; T008a..T008d, T008c3..c5)
- [x] T009 E2E `e2e/gobierno-notificaciones.spec.ts` (login → menú → acto → destinatarios → entrega y prensa → acto eficaz; consulta; otro ente; validaciones; axe) + regresión DOC-02/ORG-01..03 · DEEPSEEK · HECHO: DOC4-E2E-01..05 ×3 (T009b..g); DOC2-E2E-01 ajustado; humo UAT con 5 pantallas
- [x] T010 Mutaciones de negocio (herramienta de Claude) · CLAUDE · n-a · HECHO: 39 mutantes, 35 KILLED, 4 EQUIVALENT, 0 supervivientes (`evidence/MUTATIONS.md`)
- [x] T011 Certificación (suites, E2E ×3 y canónica, base tras la E2E, OpenAPI, residuos, ficha, tarjeta UAT, métricas, relevo UAT + humo-uat) · CLAUDE · n-a · HECHO: PG 4203/0/18, SQLite 2786/0/1435, E2E Gobierno 97/97, canónica 414 PASS + 2 FAIL atribuidos a QA-LIC-GOB-01, base tras la E2E 0, OpenAPI sin cambios ajenos (`evidence/REQUIRED_SUITE_INVENTORY.md`); relevo UAT tras el commit (`evidence/UAT_SMOKE.md`)

## Phase 2: Convergence

- [x] T012 Validar «Recursos que proceden» (5–2000, recortado, obligatorio) también al crear (`NotificacionIn`) y cubrirlo con una prueba GN per spec §4.3 / §5 N08 (partial) · DEEPSEEK · flash · SECURITY_SENSITIVE no · HECHO: `NotificacionIn._valida_recursos` 5–2000; GN-21; mutante BN-18 KILLED
- [x] T013 Mostrar en la tabla «Intentos» quién registró cada intento y cuándo per spec §4.4 (partial) · DEEPSEEK · flash · HECHO: columna «Registrado el»; NTP-14
- [x] T014 Simplificar `_fecha_determinante` a la fecha de notificación (rama inalcanzable) per plan AD-DOC04-02 (unrequested) · DEEPSEEK · flash · HECHO: `_fecha_determinante` = fecha de notificación; mutante BN-19 KILLED (GN-07)
