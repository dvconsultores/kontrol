# GOV-ORG-07 · inventario de suites exigidas

Creado al certificar (2026-11-02/03). Ejecución: Claude; código y pruebas: DeepSeek (auditados por Claude).

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop` (1 rama remota); HEAD == origin/develop == `b34f01a` al empezar y antes del commit |
| 2 | Requisitos de Gobierno | GOV-ORG-010 (+ GOV-ORG-003, IR §5, §9) → spec §1–§10 | PASS · OD-ORG07-01..04 de la dueña; MATERIAL_BLOCKER = 0; ORG-06 / ORG-04 no requeridos |
| 3 | Normativa | N03, N18, N20, N23 (vía GOV-ORG-010) | PASS (diseño): autoridad institucional por cargo; la ejecución de límites es de BUD/TRE y la SoD de CTL-01 |
| 4 | BD dirigida | migración 0068 (solo permiso) | PASS · cabeza única `0068_gov_org07_autoridad`; guardas de cabeza, MFA y techo de delegación (149 pasan); sin tablas |
| 5 | API dirigida | `tests/test_gov_org07_autoridad.py` | PASS · 21/21 (GM-01..21) en PostgreSQL |
| 6 | Regla de corte a la fecha | GM-04..07, GM-19, GM-21 | PASS · ventana actual, versión en vigor, respaldo retroactivo, fin de vigencia, ejercicio cerrado, sin caché |
| 7 | Filtros, orden y paginación | GM-09..12, GM-20, GM-21 | PASS · subunidades, texto por campo, filtros ajenos 422 (también sin cargos), orden del catálogo |
| 8 | Permisos, alcance y MFA | GM-01, GM-16..18 | PASS · `gobierno_autoridad:view` STANDARD (47 sensibles / 40 estándar); techo 104; sin el permiso 403; otra empresa sin acceso; FUNCIONAL_COMPLETO lo tiene |
| 9 | Concurrencia | lectura derivada | NOT_APPLICABLE en escritura; lectura coherente tras un cambio de ORG-03 sin caché (GM-19) |
| 10 | Frontend: menú, pantalla, detalle | vitest | PASS · MTZ-01..19, CDM-01..04, GSB-12/13, CSEL-01/02 |
| 11 | Reportes | CSV filtrado y auditado | PASS · GM-14, MTZ-10, ORG7-E2E-01 (descarga real `autoridad-<ej>-<fecha>.csv`) |
| 12 | Auditoría | `GOV_AUTHORITY_MATRIX_EXPORTED`; catálogo; espejo | PASS · catálogo 269 → 270 (CATB-03); espejo `specs/001-fundacion/evidence/audit-catalog/catalogo.md` v2026-11-02.2 (270 filas); guardas del catálogo verdes |
| 13 | Negativas y hostiles | GM-08, -09, -13, -15, -16, -17, -20 | PASS · fecha fuera del ejercicio, filtro ajeno, cargo BORRADOR / de otra estructura / de otra empresa, escrituras 405, sin permiso, otro tenant |
| 14 | Mutaciones de negocio | `mutar07b` | PASS · 42 mutantes: 39 KILLED (6 tras añadir pruebas), 3 EQUIVALENT justificados, 0 supervivientes, 42/42 restaurados (`MUTATIONS.md`) |
| 15 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261102t142832p213326nb87402`: 4225 passed / 0 failed / 18 skipped · 2950 s · NORMAL |
| 16 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261102t142832p213327n14bfa4`: 2786 passed / 0 failed / 1457 skipped · 1105 s · NORMAL (la suite GM es solo PostgreSQL, P21) |
| 17 | vitest · tsc · eslint · build | `node …` | PASS · vitest 998/998 (92 ficheros; DOC-04 969/89: **+29** casos, +3 ficheros) · tsc 0 · eslint 0 · build correcto; fixtures regenerados con `qa/fixtures_de_frontend.py` |
| 18 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio (incluido `qa/licencia_firmada.py`); mypy 154 = línea base |
| 19 | OpenAPI | `openapi_diff` contra HEAD | PASS · 5 rutas nuevas (GET), 13 esquemas `Matriz*` nuevos, 0 cambiados, 0 retirados, 0 operaciones existentes alteradas |
| 20 | E2E de ORG-07 ×3 navegadores | `qa/e2e-run.py --con-analizador … -- e2e/gobierno-autoridad.spec.ts` (3 proyectos) | PASS · `r20261102t142852p214783nfaafbc`: 15/15 (ORG7-E2E-01..05 × chromium, firefox, webkit), limpieza LIMPIA |
| 21 | E2E de Gobierno ×3 + humo + base | `--orden e2e_y_base_org07.sh` | `r20261102t141405…`: 105 PASS / 6 FAIL (ORG7-E2E-04/05 ×3 → T009c y T007c, corregidos y verificados en #20); `r20261102t215921p980783n3aed5b` (árbol final): 107 PASS / 4 FAIL, todos webkit en `gobierno-estructura` (ORG-02, no tocado) con `AUTH_INVALID_TOKEN` a mitad de una corrida de 15 min coincidente con la suspensión/reinicio del equipo; atribución: la misma spec en webkit `r20261103t205927p42316n451a34` 14/14. Humo HUMO-UAT-01 (6 pantallas) 1/1 en ambas |
| 22 | Base tras la E2E | `scope_scan` + `integridad_org07` (C1..C20) | PASS · sin violaciones de alcance; integridad 0 (99 cargos, 3 exportaciones de la matriz auditadas) |
| 23 | E2E canónica | `qa/e2e-run.py --con-analizador` (chromium + cadena de licencias) | PASS · `r20261102t155344p928645n9d088e`: **425/425**, 0 reintentos, limpieza LIMPIA (antes, en DOC-04: 414 PASS / 2 FAIL / 4 no ejecutados por QA-LIC-GOB-01) |
| 24 | QA-LIC-GOB-01 (delta acotado) | QA-A `qa/licencia_firmada.py`; QA-B `playwright.config.ts`; QA-C `n6-a11y-responsive`, `route-crawl`, `CompanySelector.test.tsx` | **CLOSED** · QA-A: la licencia sintética conserva `entitlements.modules` de la siembra (Gobierno) y solo `--modulos ""` lo quita a propósito; QA-B: `licencia-import` y `licencia-periodo` en el proyecto `licencia-estado`, después de chromium y antes de la cadena revision→tasa (un primer intento que dependía de los 3 navegadores arrastraba firefox/webkit a la canónica: 1243 pruebas; corregido); QA-C: contexto ente/empresa leído del módulo en `n6-a11y-responsive`, 404 de ente/estructura sin configurar admitido en el crawler solo bajo `/gobierno/`, y CSEL-01/02 prueban los dos contextos. De las «7 specs» de DOC-02, con QA-A+QA-B solo 2 fallaban en la canónica (chromium) |
| 25 | Accesibilidad y responsive | axe 1280/768/320 en ORG7-E2E-05 | PASS tras T007c (regiones desplazables enfocables); sin desbordamiento a 320 px |
| 26 | Ficha de pantallas | `ORG07_SCREEN_FORM_MATRIX.md` | PASS · 1 pantalla + 1 panel; formularios de escritura N/A; 0 faltantes |
| 27 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 8 pasos, negativas a–d, filtros, exportación, historia |
| 28 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | PASS · `r20261103t210328p49911nc44a49` en `396710b`: 1/1, seis pantallas por el menú (`UAT_SMOKE.md`) |
| 29 | Convergencia | revisión de spec/plan/tasks contra el código | PASS · 0 hallazgos abiertos; hallazgos ya resueltos en el ciclo: validación de filtros sin cargos (T004b), plural, accesibilidad de la tabla, contrato de consulta (QC-02) |
| 30 | Secretos | escaneo del diff | PASS · sin claves, tokens, contraseñas ni URLs con credenciales; el `.docx` protegido no entra; los encargos con una línea de QA sensible se enmascararon antes de salir |
| 31 | Residuos | corridas, puertos, bases efímeras | PASS · todas las corridas con limpieza LIMPIA; 18000/15173/18010 libres |

**Hallazgos informativos (no bloquean ORG-07):**
- FIND-ORG07-01 (LOW): DOC-02 valida la competencia de un acto con las competencias actuales del cargo, no con las de la fecha del acto.
- FIND-ORG07-02 (LOW, cobertura): con firefox/webkit forzados dentro de la canónica (intento descartado de QA-B), 24 pruebas no gubernamentales (`n6-*`, `empresas-*`, `tipos-movimiento`, `route-crawl`, `password-reset`) fallan en esos navegadores. La canónica es solo chromium por definición; queda como deuda de cobertura multinavegador, fuera de este ciclo.
