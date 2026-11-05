# GOV-TRE-01 · inventario de suites exigidas

Creado al certificar (2026-11-05). Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Preflight OBS-CERT-GOV-01 | runner versionado sobre base real de regresión | PASS · commit `2b1dc6f`: 58 controles, 0 violaciones |
| 2 | Rama única y reconciliación | ramas remotas; HEAD == origin | PASS · solo `develop` |
| 3 | Requisito de Gobierno | GOV-TRE-001 → spec §1–§10; prueba de bloqueo material | PASS · OD-TRE01-01..07 de la dueña; ORG-05 y ORG-06 no son necesarios; MATERIAL_BLOCKER = 0 |
| 4 | RED primero | suites `tests/test_gov_tre01_*.py` sobre un worktree de `2b1dc6f` | PASS (RED) · fallan al recolectar (`ImportError: GovernmentBankAccountHistory`) |
| 5 | BD dirigida | migración 0073 subir / bajar / subir en base efímera PostgreSQL | PASS · cabeza única; 7 disparadores, índice parcial, 3 permisos, proceso SoD ampliado |
| 6 | API y dominio dirigidos | 4 suites `test_gov_tre01_{cuentas,autorizados,estados,concurrencia}` | PASS · 48/48 en PostgreSQL |
| 7 | Hostiles | CB-05, CB-07, CB-09..12, CB-15, AC-02, AU-02..04 | PASS · otra empresa 404; banco, acto y cargo ajenos 422 con el mismo mensaje; `company_id` del cliente 422; número nunca en errores, auditoría ni historia |
| 8 | Concurrencia | CC-01..07 (CC-07 ×5) | PASS · dos activaciones, misma cuenta, mismo cargo, inactivar contra autorizar, dos ceses y código en carrera: nunca 500 ni doble efecto |
| 9 | Integraciones | IX-01..04 | PASS · proceso en CTL-04 y rastreo al objeto; 6 acciones SoD; guarda bloquea activar y autorizar |
| 10 | Mutaciones | `MUTATIONS.md` | PASS · 37 mutantes: 36 muertos, 1 equivalente demostrado, 0 supervivientes |
| 11 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261105t131149p506046n0bb36d`: 4393 passed / 0 failed / 18 skipped. Indicador de anomalía no bloqueante: 4244 s, compartió la máquina con la regresión y la canónica |
| 12 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261105t134956p766452nf28472`: 2791 / 0 / 1620 · NORMAL. Las pruebas multiempresa son solo de PostgreSQL (P21) |
| 13 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1180/1180 (115 ficheros; +59) · tsc 0 · eslint 0 · build correcto |
| 14 | ruff · mypy | `.venv/bin/ruff check .` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 15 | OpenAPI | contraste con `2b1dc6f` | PASS · 13 rutas nuevas, 0 retiradas. Cambio aditivo: el enum de proceso SoD gana `TRE-01` (2 operaciones y 4 esquemas) |
| 16 | E2E de TRE-01 ×3 + humo | `gobierno-tesoreria.spec.ts` en la regresión | PASS · dentro de #17, en chromium, firefox y webkit |
| 17 | Regresión de Gobierno ×3 + humo + base | `--orden qa/e2e-gobierno-regresion.sh` | PASS · `r20261105t131134p506047n118d47`: 168/168 + humo 1/1, 0 reintentos, limpieza LIMPIA |
| 18 | Base tras la E2E | `scope_scan` + `qa/gobierno_integridad.py` | PASS · sin violaciones de alcance; 75 controles, 0 violaciones (9 bancos, 9 cuentas, 6 autorizaciones) |
| 19 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261105t133417p605230n2f4095`: 444/444 (441 + 3), limpieza LIMPIA |
| 20 | Accesibilidad y responsive | axe a 1280, 768 y 320 en TRE-E2E-03 (S1–S4) | PASS · sin violaciones serias; sin desbordamiento a 320 px. La prueba destapó un desbordamiento real en Bancos por un `sr-only`, corregido |
| 21 | Ficha, campos y tarjeta | `TRE01_SCREEN_FORM_MATRIX.md`, `TRE01_FIELD_CONTRACT.md`, `OWNER_UAT_CARD.md` | PASS |
| 22 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | ver `UAT_SMOKE.md` |
| 23 | Convergencia | spec, plan y tasks contra el código | PASS · 0 hallazgos |
| 24 | Secretos | escaneo del diff | ver el commit: sin contraseñas, claves, tokens ni rutas de usuario; el SNAT protegido queda fuera |

**Limitación heredada:** los controles C21–C35 de DOC-02 y los de DOC-04 estaban en cadenas antiguas no recuperables y no se reconstruyeron; sus procesos los cubren sus suites y la regresión.

**Transitorio de WebKit del preflight:** los 5 fallos `AUTH_INVALID_TOKEN` no se repitieron en esta regresión. La causa sigue sin demostrar.

**Deudas abiertas no tocadas:** FIND-CTL04-02 (LOW), FIND-CTL04-03 (LOW), FIND-ORG07-02 (LOW). La cadena Alembic no corre en SQLite desde 0001 (preexistente): la migración se certifica en PostgreSQL.
