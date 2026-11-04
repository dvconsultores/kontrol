# GOV-CTL-04 · inventario de suites exigidas

Creado al certificar (2026-11-03/04). Ejecución: Claude; código y pruebas: DeepSeek (auditados por Claude).

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop`; HEAD == origin/develop == `4d4f76c` al empezar y antes del commit |
| 2 | Requisitos de Gobierno | GOV-CTL-005 (+ FIND-ORG07-01) → spec §1–§10 | PASS · OD-CTL04-01..04 de la dueña; MATERIAL_BLOCKER = 0; CTL-01, CTL-02 y motor SoD fuera de alcance |
| 3 | Normativa | N18, N22 (vía GOV-CTL-005) | PASS (diseño): consulta de solo lectura sobre la evidencia; muestreo explícito y reproducible como papel de trabajo |
| 4 | BD dirigida | migración 0069 subir / bajar / subir en base efímera | PASS · cabeza única `0069_gov_ctl04_auditoria`; 2 tablas y 6 disparadores (UPDATE, DELETE, TRUNCATE) tras la segunda subida; base eliminada |
| 5 | API dirigida | `tests/test_gov_ctl04_auditoria.py` | PASS · 17/17 (GX-01..17) en PostgreSQL |
| 6 | FIND-ORG07-01 | `tests/test_gov_doc02_autoridad_historica.py` | PASS · 7/7 (GH-01..07): DOC-02 valida cargo, competencia y autoridad a la fecha del acto con `competencias_en_vigor` (lógica histórica de ORG-07) |
| 7 | Regresión de Gobierno | todas las suites `test_gov_*` | PASS · 287/287 |
| 8 | Permisos, alcance y MFA | GX-14..16; guardas MFA y techo de delegación | PASS · `gobierno_auditoria:view` y `:sample` STANDARD, independientes de `audit:view` (OD-CTL04-03); FUNCIONAL_COMPLETO los tiene; otro ente: 404 |
| 9 | Inmutabilidad | GX-13; IMM-01..05 | PASS · muestra y partidas rechazan UPDATE/DELETE/TRUNCATE; PATCH/PUT/DELETE 405; IMM-04 corregido en T011a (ver nota) |
| 10 | Frontend: menú, pantallas, panel y formulario | vitest | PASS · 1040/1040 (ORG-07: 998: **+42** casos); AUD, EVI, REG, MUE, CDA y GSB-14/15 |
| 11 | Reportes | CSV de la muestra, auditado | PASS · GX-12, GX-17 (cabecera `# metodo` / `# semilla`), CTL4-E2E-05 |
| 12 | Auditoría | `GOV_AUDIT_SAMPLE_CREATED`, `GOV_AUDIT_SAMPLE_EXPORTED`; catálogo; espejo | PASS · catálogo 270 → 272 (CATB-03); espejo `specs/001-fundacion/evidence/audit-catalog/catalogo.md` v2026-11-03.1 (272 filas) |
| 13 | Negativas y hostiles | GX-06..08, -10, -11, -14..16 | PASS · eventos privados o ajenos 404, población vacía, demasiado grande, tamaño inválido, partidas fuera de la población, sin permiso, otro ente |
| 14 | Mutaciones de negocio | `mutar_ctl04` | PASS · 14 mutantes: 14 KILLED (M09 tras añadir GX-17), 0 equivalentes, 0 supervivientes, 14/14 restaurados (`MUTATIONS.md`) |
| 15 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | `r20261103t233255p274777n89ceea`: 4248 passed / **1 failed** / 18 skipped · 4136 s. El fallo, IMM-04, era una regresión real del ciclo (ver nota). Corregido en T011a; `tests/test_audit_immutability.py` 7/7 en PostgreSQL. **No se repitió la suite completa** |
| 16 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261104t004215p745558n3a7e58`: 2787 passed / 0 failed / 1480 skipped · 1223 s · NORMAL (las suites GX y GH son solo PostgreSQL, P21) |
| 17 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1040/1040 · tsc 0 · eslint 0 · build correcto; fixtures regenerados con `qa/fixtures_de_frontend.py` |
| 18 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 19 | OpenAPI | contraste con HEAD | PASS · 7 operaciones nuevas (6 GET y 1 POST bajo `/gobierno/auditoria`), 12 esquemas nuevos (`Auditoria*`, `MuestraIn`), 0 cambiados, 0 retirados, 0 operaciones existentes alteradas |
| 20 | E2E de Gobierno ×3 + humo + base | `--orden e2e_y_base_ctl04.sh` | PASS · `r20261103t231504p236057n838395`: 129/129 (incluye CTL4-E2E-01..06 × chromium, firefox y webkit); HUMO-UAT-01 (7 pantallas) 1/1. Tras T012: `r20261104t012410p901143nd12752` CTL4-E2E-01..06 ×3 = 18/18 |
| 21 | Base tras la E2E | `scope_scan` + `integridad_ctl04` (C1..C20 de ORG-07 y M1..M8 de muestras) | PASS · sin violaciones de alcance; integridad 0 |
| 22 | E2E canónica | `qa/e2e-run.py --con-analizador` (chromium + cadena de licencias) | **PASS** · certificación `r20261104t024205p1089934nd56c3d` (árbol final, con T012 y T013): **431/431** (425 de la línea base + 6 CTL4-E2E en chromium), 0 reintentos, limpieza LIMPIA. Antes, sin T013: `r20261104t012730p910400n3ca718` 414 PASS / 1 FAIL / 16 no ejecutadas (`auditoria-sobre` ENV-01/02, «no hay paso TOTP libre para admin_w3») y `r20261104t020229p955560n6db004` 414 / 1 / 16 (`mfa.spec` 05 bloqueo: tiempo agotado esperando el formulario de login). Atribución: HEAD `4d4f76c` en worktree, `r20261104t021348p990225nea0315` 425/425; las dos pruebas aisladas en el árbol del ciclo, `mfa.spec` ×5 70/70 y `auditoria-sobre` ×3 6/6; el mismo fallo TOTP ya ocurrió en `r20261028t171009p840212n1d80ae` (antes del ciclo); 0 errores 5xx. Por decisión de la dueña se corrigió el arnés (T013) antes de certificar; no hubo reintento hasta verde |
| 22b | Delta QA del arnés (T013, FIND-CTL04-01) | `e2e/auditoria-sobre.spec.ts` | PASS · los eventos controlados salen ahora del paso de contraseña del login (`MFA_CHALLENGE_ISSUED`, o `LOGIN_SUCCESS` si no hay segundo factor), con el `request_id` de `X-Request-ID`: no consumen pasos TOTP. Con un solo worker y cada prueba ×4: 8/8 (la condición que antes agotaba los pasos) |
| 23 | Accesibilidad y responsive | axe 1280/768/320 en CTL4-E2E-06 | PASS · regiones con nombre único; sin desbordamiento a 320 px |
| 24 | Ficha de pantallas | `CTL04_SCREEN_FORM_MATRIX.md` | PASS · 2 pantallas, 1 panel y 1 formulario de escritura (F1); 0 faltantes |
| 25 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 9 pasos, negativas a–e |
| 26 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | PASS · `r20261104t025631p1126940n521000` en `0984ede`: 1/1, siete pantallas por el menú (`UAT_SMOKE.md`) |
| 27 | Convergencia | spec, plan y tasks contra el código | PASS tras T012 · 1 hallazgo (`partial`, MEDIUM, spec §4.3: los documentos citados no enlazaban a `/documentos/{id}` con `documentos:view`), añadido como Phase 2 y resuelto en T012 (EVI-06/07; mutante CTL-M15 KILLED); 0 abiertos |
| 28 | Secretos | escaneo del diff | PASS · sin claves, tokens, contraseñas, URLs con credenciales ni rutas del equipo; el `.docx` protegido no entra; en T013 se omitió del encargo una línea de configuración local (falso positivo de egress) |
| 29 | Residuos | corridas, puertos, bases efímeras | PASS · todas las corridas con limpieza LIMPIA; base efímera de la migración eliminada; worktree de atribución retirado; 18000/15173/18010 libres; solo queda viva la base de la pila UAT |

**Nota sobre IMM-04 (regresión hallada por la suite completa):** la migración 0069 añade la clave foránea `gov_audit_sample_items.audit_event_id → audit_events.id`. Con ella, PostgreSQL rechaza un `TRUNCATE audit_events` sin CASCADE por la clave foránea, antes de llegar al disparador `trg_audit_events_no_truncate`. La tabla seguía protegida, pero IMM-04 esperaba el mensaje del disparador.
- La clave foránea se mantiene: una partida nunca apunta a un evento inexistente.
- IMM-04 exige ahora dos cosas. Sin CASCADE: el TRUNCATE falla y la fila sigue. Con CASCADE: falla con `AUDIT_EVENT_IMMUTABLE` y la fila sigue. Así demuestra que el disparador actúa aunque la clave foránea deje de detener el TRUNCATE.

**Hallazgos:**
- FIND-CTL04-01 (MEDIUM, arnés E2E): **CLOSED** con T013.
- FIND-CTL04-02 (LOW, arnés E2E, preexistente): `auditoria-paginacion` aislada falla (`total = 0` en su relleno), también en HEAD `4d4f76c`. Depende de la actividad que acumula la canónica. OPEN, fuera de alcance.
- FIND-CTL04-03 (LOW, observación): `mfa.spec` 05 bloqueo se colgó 30 s en 1 de 4 corridas canónicas del árbol del ciclo. No se reprodujo en 70 repeticiones ni en la certificación, y el ejecutor retira la traza (material MFA). Sin causa demostrada; OPEN.
- FIND-ORG07-01: **CLOSED** (MEDIUM, reclasificado por la dueña).
- FIND-ORG07-02: sigue **OPEN** (LOW, cobertura multinavegador de pruebas no gubernamentales).
