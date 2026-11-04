# GOV-CTL-01 · inventario de suites exigidas

Creado al certificar (2026-11-04/05). Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop`; HEAD == origin/develop == `9dd2fe6` al empezar |
| 2 | Requisito de Gobierno | GOV-CTL-001 → spec §1–§10; prueba de bloqueo material | PASS · OD-CTL01-01..04 de la dueña; ORG-06, CTL-02 y DOC-01 no son necesarios; MATERIAL_BLOCKER = 0 |
| 3 | Normativa | N20, N23 (vía GOV-CTL-001) | PASS (diseño). Ninguna fija pares concretos; las reglas las declara Control Interno |
| 4 | RED primero | las 4 suites `tests/test_gov_ctl01_*.py` sobre un worktree de `9dd2fe6` | PASS (RED) · fallan al recolectar (`ImportError: GovernmentSoDRuleHistory`) |
| 5 | BD dirigida | migración 0072 subir / bajar / subir en base efímera | PASS · cabeza única `0072_gov_ctl01_sod`; 2 tablas, 5 disparadores (reglas no borrables, historia inmutable), 3 permisos concedidos a FUNCIONAL_COMPLETO |
| 6 | API y guarda dirigidas | `tests/test_gov_ctl01_{reglas,guarda_ctl06,guarda_doc02,concurrencia}.py` | PASS · 22/22 en PostgreSQL (CR-01..11, SG-01..07, SD-01..02, SC-01..02) |
| 7 | Guarda preventiva | SG-01, SD-01 | PASS · el mismo usuario y el mismo objeto quedan bloqueados ANTES de mutar (409 GOV_SOD_CONFLICT); el objeto no cambia (versión y contenido); otro usuario lo hace |
| 8 | Alcance de la regla | SG-02..SG-06, SD-02 | PASS · bidireccional; borrador, futura y cerrada no bloquean; otra empresa no aplica; otro objeto no aplica |
| 9 | Precedencia del dominio | SG-07 | PASS · el maker-checker de CTL-06 responde GOV_FINDING_SELF_VERIFICATION y no se registra conflicto SoD |
| 10 | Concurrencia | SC-01 ×5 repeticiones, SC-02 | PASS · dos acciones incompatibles a la vez: exactamente un 201 y un 409 (STALE o SOD); nunca ambas mutaciones. Bloqueo de fila del objeto + If-Match |
| 11 | Reglas | CR-03..CR-08, CR-11 | PASS · validaciones, If-Match (428/409), activar con MFA, duplicada 409, cierre con motivo, historia inmutable en PostgreSQL |
| 12 | Permisos, alcance y MFA | CR-02, CR-09, CR-10 | PASS · view/manage STANDARD, activate SENSITIVE; sin permiso 403; otra empresa 404 |
| 13 | Auditoría | catálogo 286 → 291 (CATB-03); espejo `catalogo.md` v2026-11-04.3 | PASS · 5 acciones `gov-ctl-01`; el bloqueo es REJECTION con `record_audit_after_rollback` |
| 14 | Integración con CTL-04 | GX-02; `_objeto_desde_evento` | PASS · proceso «CTL-01 · Segregación de funciones» en la población; rastreo de `GovernmentSoDRule` → `/gobierno/sod/{id}` |
| 15 | Mutaciones de negocio | `mutar_ctl04.py` | PASS · 19 mutantes: 19 KILLED, 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 16 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261104t214504p9236n690c3e`: 4342 passed / 0 failed / 18 skipped. Aviso no bloqueante: salto de reloj del anfitrión (suspensión); la duración monotónica es válida |
| 17 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261104t190426p434700n838fa1`: 2790 passed / 0 failed / 1570 skipped · NORMAL. Las pruebas de CTL-01 y DA-08 son del mundo multiempresa, solo PostgreSQL (P21) |
| 18 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1121/1121 (110 ficheros; DOC-08: 1097 → **+24**) · tsc 0 · eslint 0 (`--max-warnings 0`) · build correcto |
| 19 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check .` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 20 | OpenAPI | contraste con `9dd2fe6` | PASS · 8 operaciones nuevas (6 rutas), 13 esquemas nuevos, 0 cambiados, 0 retirados: los contratos de DOC-02 y CTL-06 no cambian |
| 21 | Guarda de puertas de UI | `src/tests/gate-coverage.test.ts` | PASS · los ficheros con POST llevan `useAutoridad` |
| 22 | E2E de CTL-01 ×3 + humo | `qa/e2e-run.py --con-analizador -- e2e/gobierno-sod.spec.ts e2e/uat-humo-gobierno.spec.ts --project=chromium --project=firefox --project=webkit --project=humo-uat` | PASS · `r20261104t185300p298375n9aa800`: 10/10 (SOD-E2E-01..03 × 3 navegadores + HUMO-UAT-01 con 10 pantallas); limpieza LIMPIA |
| 23 | Regresión de Gobierno ×3 + humo + base | `--orden e2e_y_base_ctl01.sh` | 158/159 en `r20261104t214450p9237n9e6982`. El fallo (CTL4-E2E-06, axe `target-size` a 1280 px en chromium) era una regresión real de CTL-01, corregida en T013b. Repetición de `gobierno-auditoria.spec.ts` ×3: `r20261104t224613p189760n87fe3b` 18/18 |
| 24 | Base tras la E2E | `scope_scan` + `integridad_ctl01` (H1–H10, S1–S9) | PASS · sin violaciones de alcance; integridad 0 (9 reglas, 6 vigentes, 6 conflictos, 12 hallazgos). **Limitación:** tras el reinicio de la estación se perdieron `integridad_ctl04.py` e `integridad_doc08.py` (scratchpad); sus controles heredados de ORG/CTL-04/DOC-08 no se volvieron a ejecutar en este ciclo |
| 25 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261104t224951p251493n0fbfe6`: 441/441 (438 de la línea base + 3 de CTL-01 en chromium); 0 reintentos; limpieza LIMPIA |
| 26 | Accesibilidad y responsive | axe a 1280, 768 y 320 en SOD-E2E-03 (S1–S4) | PASS · sin violaciones serias; sin desbordamiento a 320 px |
| 27 | Ficha de pantallas | `CTL01_SCREEN_FORM_MATRIX.md` | PASS · 4 pantallas + alerta; 3 formularios de escritura; 0 faltantes |
| 28 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 7 pasos y negativas a–f |
| 29 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | ver `UAT_SMOKE.md` |
| 30 | Convergencia | spec, plan y tasks contra el código | PASS · 0 hallazgos. El bloqueo de fila del §4.2 lo toman los cargadores de DOC-02 y CTL-06 (`SELECT … FOR UPDATE`) antes de llamar a la guarda (AD-CTL01-03) |
| 31 | Secretos | escaneo del diff | ver el commit: sin contraseñas, claves, tokens ni rutas de usuario; el SNAT protegido queda fuera |

**Regresiones de procesos anteriores destapadas por CTL-01, corregidas dentro del ciclo:**
- DA-08 (DOC-08): aislamiento de la instantánea de licencia (T013-r).
- CTL4-E2E-06 (CTL-04): ancho de los filtros con la etiqueta de auditoría más larga (T013b).

**Deudas abiertas no tocadas:** FIND-CTL04-02 (LOW, preexistente), FIND-CTL04-03 (LOW, observación) y FIND-ORG07-02 (LOW).
