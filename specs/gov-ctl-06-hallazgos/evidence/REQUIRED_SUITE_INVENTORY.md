# GOV-CTL-06 · inventario de suites exigidas

Creado al certificar (2026-11-04). Ejecución: Claude; código y pruebas: DeepSeek (auditados por Claude).

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 0 | Preflight: certificación final de CTL-04 | `qa/suite_tiempos.py --motor postgres --con-analizador` sobre `8b7675d` | PASS · `r20261104t031121p1132460n2a89cc`: 4249 passed / 0 failed / 18 skipped · NORMAL → CTL04_FINAL_CERTIFICATION = PASS |
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop`; HEAD == origin/develop == `8b7675d` al empezar y antes del commit |
| 2 | Requisitos de Gobierno | GOV-CTL-008 → spec §1–§10; prueba de bloqueo material | PASS · OD-CTL06-01..04 de la dueña; ORG06_REQUIRED = 0; CTL02_REQUIRED = 0; MATERIAL_BLOCKER = 0 |
| 3 | Normativa | N18, N20, N22 (vía GOV-CTL-008) + IR §8 (estados del hallazgo) | PASS (diseño): ciclo OPEN → ACTION_PLAN → IN_REMEDIATION → EVIDENCE_SUBMITTED → VERIFIED/CLOSED |
| 4 | BD dirigida | migración 0070 subir / bajar / subir en base efímera | PASS · cabeza única `0070_gov_ctl06_hallazgos`; 6 tablas y 16 disparadores; base eliminada |
| 5 | API dirigida | 9 ficheros `tests/test_gov_ctl06_*.py` | PASS · 32/32 en PostgreSQL (GH6-01..32) |
| 6 | Responsable (OD-CTL06-01) | GH6-09, GH6-10, GH6-13 | PASS · solo cargos VIGENTES del ejercicio en curso y de la empresa; instantánea guardada |
| 7 | Maker-checker y MFA (OD-CTL06-02) | GH6-18, GH6-31, GH6-32; GH6-02 | PASS · ni quien presenta ni el autor de un avance pueden verificar; `:verify` SENSITIVE, `:view`/`:manage` STANDARD |
| 8 | Evidencia y cierre | GH6-16, GH6-17, GH6-19 | PASS · 100 % exige documento ACTIVE vinculado (Spec 046, analizador); `freeze_links` al cerrar |
| 9 | Concurrencia | GH6-08, GH6-26 | PASS · If-Match obligatorio (428); versión obsoleta 409 `GOV_FINDING_STALE`; sin actualizaciones perdidas |
| 10 | Inmutabilidad | GH6-21 (PostgreSQL) | PASS · recomendaciones, avances e historia rechazan UPDATE; hallazgos no admiten DELETE |
| 11 | Alcance y permisos | GH6-22, GH6-23 | PASS · otra empresa: 404; sin permiso: 403; view sin manage/verify: 403 en escrituras |
| 12 | Reportes | GH6-24, GH6-25; CTL6-E2E-02 | PASS · resumen operativo; CSV `plan-acciones-<fecha>.csv` auditado (`GOV_FINDINGS_EXPORTED`) |
| 13 | Auditoría | catálogo 272 → 282 (CATB-03); espejo `specs/001-fundacion/evidence/audit-catalog/catalogo.md` v2026-11-04.1; GH6-28 | PASS · 10 acciones `gov-ctl-06`; guardas del catálogo 36/36 |
| 14 | Integración con CTL-04 | GH6-29; GX-02 | PASS · proceso «CTL-06 · Hallazgos y acciones correctivas» en la población; rastreo `GovernmentFinding` |
| 15 | Mutaciones de negocio | `mutar_ctl04.py` sobre `mutantes.json` | PASS · 16 mutantes: 16 KILLED (3 tras añadir pruebas), 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 16 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261104t132441p2626888n9b6eb1`: 4283 passed / 0 failed / 18 skipped · NORMAL, sin salto de reloj (la corrida anterior `r20261104t120053…` dio 3 fallos N9 → T012a/T012b) |
| 17 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261104t132425p2626809n9b056d`: 2788 passed / 0 failed / 1513 skipped · NORMAL (la anterior `r20261104t125405…` dio 1 fallo N9 → T012a) |
| 18 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1066/1066 (101 ficheros; CTL-04: 1042: **+24**) · tsc 0 · eslint 0 · build correcto |
| 19 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 20 | OpenAPI | contraste con el backend de HEAD | PASS · 13 operaciones nuevas bajo `/gobierno/hallazgos`, 17 esquemas nuevos, 0 cambiados, 0 retirados |
| 21 | E2E de CTL-06 ×3 + humo | `qa/e2e-run.py --con-analizador -- e2e/gobierno-hallazgos*.spec.ts e2e/uat-humo-gobierno.spec.ts` (3 navegadores + humo-uat) | PASS · `r20261104t113805p1949898nc707a1`: 13/13 (CTL6-E2E-01..04 × chromium, firefox, webkit + HUMO-UAT-01 con 8 pantallas), limpieza LIMPIA |
| 22 | Regresión de Gobierno ×3 + humo + base | `--orden e2e_y_base_ctl06.sh` | PASS · `r20261104t114315p1959088n7ad9d5`: 141/141 (ORG-01/02/03/07, DOC-02/04, CTL-04, CTL-06) + humo 1/1 |
| 23 | Base tras la E2E | `scope_scan` + `integridad_ctl06` (C1..C20, M1..M8, H1..H13) | PASS · sin violaciones de alcance (476 aristas); integridad 0 (9 hallazgos, 3 cerrados) |
| 24 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261104t141731p3227728neb7e98`: 435/435 (431 de la línea base + 4 de CTL-06 en chromium), 0 reintentos, limpieza LIMPIA |
| 25 | Accesibilidad y responsive | axe a 1280/768/320 en CTL6-E2E-04 | PASS · sin violaciones serias; sin desbordamiento a 320 px |
| 26 | Ficha de pantallas | `CTL06_SCREEN_FORM_MATRIX.md` | PASS · 3 pantallas + componente de plan; 5 formularios de escritura; 0 faltantes |
| 27 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 10 pasos, negativas a–e |
| 28 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | ver `UAT_SMOKE.md` |
| 29 | Convergencia | spec, plan y tasks contra el código | PASS · 0 hallazgos; `tasks.md` sin fase de convergencia nueva |
| 30 | Secretos | escaneo del diff | PASS · el diff del ciclo no contiene contraseñas, claves, tokens, URLs con credenciales ni rutas de usuario; el SNAT protegido queda fuera del commit |
| 31 | Residuos | corridas, puertos, bases efímeras | PASS · puertos E2E 18000/15173/18010 libres; sin bases efímeras de corrida huérfanas (la única viva es la pila UAT previa, que se releva al cierre) |

**Hallazgos de QA del ciclo (corregidos dentro del ciclo):**
- Los defectos de prueba vinieron de tres fuentes:
  - el puente de DeepSeek, que condensa o retranscribe los encargos grandes;
  - dos errores de encargo de Claude: la expresión de la ruta de avances y el permiso verify del responsable en la E2E;
  - pruebas vacías detectadas por las mutaciones: HLP-06 y el maker-checker.
- Ninguno afectó al producto.

**Deudas abiertas no tocadas:**
- FIND-CTL04-02 (LOW, preexistente);
- FIND-CTL04-03 (LOW, observación);
- FIND-ORG07-02 (LOW).
