# GOV-DOC-04 · inventario de suites exigidas

Creado al certificar (2026-11-02). Ejecución: Claude; código y pruebas: DeepSeek (auditados por Claude).

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin == `932f7d2` | PASS · solo `develop` (1 rama remota); HEAD == origin/develop al empezar y antes del commit |
| 2 | Humo UAT autenticado (entorno de la dueña) | `e2e/uat-humo-gobierno.spec.ts` (HUMO-UAT-01), proyecto `humo-uat` (OD-QA-UAT-01) | PASS en la corrida de Gobierno; ahora abre también «Notificaciones administrativas» (T009f/T009g). En la pila UAT relanzada: ver `UAT_SMOKE.md` |
| 3 | Requisitos de Gobierno | GOV-DOC-005 → spec §1–§10 | PASS (spec); OD-DOC04-01..04 de la dueña; MATERIAL_BLOCKER = 0 |
| 4 | Normativa | LOPA arts. 72–77 (texto íntegro y recursos, domicilio y recibo, prensa + 15 días); Ley N29 arts. 1–17 (para el canal electrónico, fuera de alcance) | PASS (diseño) |
| 5 | BD dirigida | migración 0067 upgrade → downgrade → upgrade | PASS · PostgreSQL 10 → 13 → 10 → 13 tablas `gov_`; cabeza única `0067_gov_doc04_notificaciones` |
| 6 | API dirigida | `tests/test_gov_doc04_notificaciones.py` | PASS · 22/22 (GN-01..21 + GN-05b) en PostgreSQL; GN-05b corregida para matar BN-09 (T001c); GN-21 por la convergencia (T012) |
| 7 | DOC-02 adaptado (OD-DOC04-03) | `tests/test_gov_doc02_actos.py` | PASS · 36/36; GA-16 por DOC-04, GA-17 prensa → 422 GOV_ACT_NOTIFICATION_REQUIRED, GA-09 con `notificaciones` |
| 8 | Permisos, alcance y MFA | GN-14, GN-15, GN-16; `test_mfa_policy`, `test_delegation_ceiling` | PASS · `DOC04_MFA_MATRIX.md`; 47 sensibles / 39 estándar; techo 103; otra empresa → 404 |
| 9 | Concurrencia | `If-Match`; acto bloqueado antes que la notificación (AD-DOC04-03) | PASS · GN-04 (428, 409 STALE), GN-18 (dos entregas simultáneas → una), NTP-08 |
| 10 | Fechas y eficacia | vectores: ≥ fecha del acto, ≤ hoy, prensa + 15 días, eficacia con la fecha más tardía, anuladas excluidas | PASS · GN-05b, GN-06, GN-07, GN-09; INT-05, INT-07; DOC4-E2E-01 («Eficaz a partir de hoy + 15») |
| 11 | Frontend: menú, pantallas, formularios | vitest | PASS · GSB-10/11, NTL-01..08c, NTP-01..13, DST-01..08, INT-01..10, ANU-01..04, NDA-01..09c, ACP-40..42, EFI-01..08 |
| 12 | Documentos | oficio y constancias (046) con analizador real | PASS · GN-05, GN-06 (vínculos congelados), GN-17 (constancia repetida); DOC4-E2E-01 con ClamAV real (`--con-analizador`) |
| 13 | Reportes | CSV (backend + UI + E2E) y contadores del acto | PASS · GN-13, NTL-07, DOC4-E2E-01 (`notificaciones-AAAA.csv`); GN-02/07 (`notificaciones` del acto) |
| 14 | Auditoría | 7 acciones; guardas del catálogo; espejo | PASS · GN-20; catálogo 262 → 269 (CATB-03); espejo `specs/001-fundacion/evidence/audit-catalog/catalogo.md` v2026-11-02.1 con 269 filas; guardas 9/9; C48 de la base tras la E2E |
| 15 | Negativas y hostiles | ídem | PASS · acto no particular o no emitido, duplicado, cédula inválida, apoderado incompleto, oficio no vinculado, constancia = oficio, prensa sin fallido, acto revocado, notificada inmutable, otra empresa, restricciones de BD (GN-19) |
| 16 | Mutaciones de negocio | `mutar07b` | PASS · 41 mutantes: 37 KILLED (2 tras añadir o corregir su prueba; BN-18/BN-19 de la convergencia), 4 EQUIVALENT justificados, 0 supervivientes, 41/41 restaurados (`MUTATIONS.md`) |
| 17 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261102t011933p1445537n03b96c`: 4204 passed / 0 failed / 18 skipped · 2823 s · NORMAL (tras el último cambio de backend, T012/T014) |
| 18 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261102t011933p1445538nee362b`: 2786 passed / 0 failed / 1436 skipped · 961 s · NORMAL (las suites GN y GA corren solo en PostgreSQL, P21) |
| 19 | vitest completo · tsc · eslint · build | `node …` | PASS · vitest 969/969 (89 ficheros; HEAD 899/83 medido con un worktree: **+70** casos, +6 ficheros) · tsc 0 · eslint 0 · build correcto; fixtures regenerados con la herramienta |
| 20 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base, 0 en el ámbito tocado |
| 21 | Alembic | `alembic heads` | PASS · `0067_gov_doc04_notificaciones` (única) |
| 22 | OpenAPI | `openapi_diff` contra HEAD | PASS · 6 rutas nuevas (8 operaciones bajo `/gobierno/notificaciones`), 12 esquemas nuevos, 1 cambiado (`ActoOut.notificaciones`, intencionado), 0 retirados, 0 operaciones existentes alteradas. Una colisión de nombre con el `NotificacionOut` del módulo 047 se detectó aquí y se corrigió (T003h) |
| 23 | E2E de DOC-04 + DOC-02 + ORG-01/02/03 ×3 navegadores | `qa/e2e-run.py --con-analizador --puerto-* 18000/15173/18010 --orden e2e_y_base_doc04.sh` | PASS · `r20261102t020637p2013837ne15c8f` (tras la convergencia): 97/97 (32 casos × 3 navegadores + HUMO-UAT-01), 0 reintentos, limpieza LIMPIA |
| 24 | E2E canónica | `qa/e2e-run.py --con-analizador` (puertos 18000/15173/18010) | **414 PASS · 2 FAIL atribuidos a QA-LIC-GOB-01 · 4 no ejecutados** · `r20261102t005724p1343337n469969`, limpieza LIMPIA. Fallan DOC4-E2E-01 y DOC4-E2E-03 (chromium) con `403 MODULE_NOT_ENTITLED`: en el log, `licencia-periodo.spec.ts` (E2E-ROLLA-01..08, mismo proyecto chromium, `fullyParallel`) importa una licencia posterior sin el módulo «gobierno» mientras esas dos pruebas largas siguen en curso; DOC4-E2E-02/04/05 terminaron antes y pasaron. Los 4 «no ejecutados» son los proyectos dependientes `licencia-revision/sync/rotacion/tasa`, que Playwright salta cuando chromium tiene fallos. Sin el cambio de licencia (corrida de Gobierno, #23) DOC-04 pasa 15/15 ×3. No se relanzó la canónica para buscar un verde por orden de ejecución |
| 25 | Base tras la E2E | `scope_scan` + `integridad_doc04` (C1..C48) sobre la base de la corrida (`--orden`) | PASS · `r20261102t020637p2013837ne15c8f`: alcance sin violaciones; integridad C1..C48 = 0 (en la corrida previa: 21 notificaciones: 6 NOTIFICADA, 15 PENDIENTE; 9 intentos; actos 15 BORRADOR, 15 EMITIDO, 6 EFICAZ, 3 REVOCADO) |
| 26 | Accesibilidad y responsive | axe 1280/768/320 en la E2E | PASS · DOC4-E2E-05: lista, notificación y sección del acto sin violaciones serias y sin desbordamiento a 320 px |
| 27 | Ficha de pantallas y formularios | `SCREEN_FORM_COMPLETENESS.md` | PASS · 6 pantallas/paneles, 0 faltantes |
| 28 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 8 pasos, negativas a–e, documentos, reportes, auditoría, historia |
| 29 | Convergencia | `/speckit-converge` | PASS · 1.ª pasada: F1 HIGH (recursos sin validar), F2 LOW («Registrado el»), F3 LOW (rama muerta) → T012–T014 aplicados y reprobados; 2.ª pasada: convergida, 0 hallazgos |
| 30 | Secretos | escaneo del diff confirmado | PASS · sin claves, tokens, contraseñas, URLs con credenciales ni PII real; el `.docx` protegido no entra |
| 31 | Residuos | bases efímeras, ficheros temporales, puertos | PASS · todas las corridas E2E con limpieza LIMPIA; 18000/15173/18010 libres; solo la pila UAT en 18100/15273/18110 |

**Inestabilidad observada (no regresión).** En una corrida intermedia de Gobierno (`r20261101t233717p666331nce7510`), DOC2-E2E-01 y
GOV-E2E-01 agotaron 60 s esperando el `POST …/vinculos` de una carga de PDF desde la interfaz en firefox, con el analizador real y la
suite de SQLite corriendo a la vez. El paso no lo toca DOC-04; la corrida certificadora, sin carga concurrente, dio 97/97.
**QA-LIC-GOB-01** sigue OPEN_MEDIUM_RELEASE_BLOCKER (no se trata en este ciclo; política de la dueña).
