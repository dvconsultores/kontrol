# GOV-DOC-02 · inventario de suites exigidas

Creado con el plan (2026-11-01); el resultado se rellena al certificar.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin == `f462cc3` | PASS · solo `develop` (1 rama remota); HEAD == origin/develop al empezar y antes del commit |
| 2 | Humo UAT autenticado (entorno de la dueña) | `e2e/uat-humo-gobierno.spec.ts` (HUMO-UAT-01), proyecto `humo-uat` | PASS · usuario sintético de consulta abre por el menú Configuración del ente, Estructura organizativa, Cargos y competencias y Actos administrativos; rol retirado al terminar; no toca el MFA de `admin` (`UAT_SMOKE.md`) |
| 3 | Requisitos de Gobierno | GOV-DOC-003 → spec §1–§10 | PASS (spec); OD-DOC02-01..04 de la dueña |
| 4 | Modelo de proceso, autoridad y eficacia | spec §3–§5; LOPA arts. 9, 18, 72–76, 82–84 | PASS (diseño) |
| 5 | BD dirigida | migración 0066 upgrade → downgrade → upgrade | PASS · PostgreSQL 8 → 10 → 8 → 10 tablas `gov_`; cabeza única `0066_gov_doc02_actos` |
| 6 | API dirigida | `tests/test_gov_doc02_actos.py` | PASS · 36/36 (GA-01..GA-36) en PostgreSQL; GA-32..36 añadidas para matar mutantes supervivientes |
| 7 | Permisos, autoridad y alcance | ídem (consulta, registrador sin `issue`, emisor sin `annul`, otra empresa, otro tenant) | PASS · GA-25, GA-26, GA-32, GA-35; DOC2-E2E-03/04/05 |
| 8 | Concurrencia | `If-Match` y bloqueo de fila | PASS · GA-31 (409 STALE, una sola emisión), ACP-10 |
| 9 | Fechas y eficacia | vectores (≤ hoy, ≥ fecha del acto, prensa + 15 días, eficacia ≥ base, interno) | PASS · GA-15..19, GA-33, GA-34; EMI/EFI; `sumarDiasDeNegocio` en el módulo central (ADR-020) |
| 10 | Frontend: menú, pantallas, formularios | vitest | PASS · GSB-08/09, GAL-01..14, ACP-01..15, FRM-01..14, EMI-01..08, EFI-01..07, COR-01..07, REF-01..06 |
| 11 | Documentos | PDF firmado y soporte (046) con analizador real | PASS · GA-13/14/16/18; DOC2-E2E-01 con ClamAV real (`--con-analizador`); vínculos congelados al emitir y al registrar eficacia |
| 12 | Reportes | CSV (backend + UI + E2E) | PASS · GA-24, GA-36 (filtro por año), GAL-14, DOC2-E2E-01 (descarga `actos-AAAA.csv`) |
| 13 | Auditoría | 9 acciones; guarda del catálogo | PASS · GA-30; catálogo 253 → 262 (CATB-03); C27 de la base tras la E2E |
| 14 | Negativas y hostiles | ídem | PASS · número duplicado, autoridad o competencia ajenas, emitir incompleto, documento inválido, referencias inválidas, otra empresa, restricciones de BD (GA-28, 12 casos con su CHECK nombrado) |
| 15 | Mutaciones de negocio | `mutar07b` | PASS · 43 mutantes: 42 KILLED, 1 EQUIVALENT justificado, 0 supervivientes (`MUTATIONS.md`) |
| 16 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261101t162238p2765638n9afed8`: 4175 passed / 0 failed / 18 skipped · 3574 s monotónicos · salto de reloj del anfitrión (indicador no bloqueante). Con GA-01..31; GA-32..36 (solo pruebas) se añadieron después y pasan 36/36 en su fichero |
| 17 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261101t180626p3462202n7e5cdc`: 2786 passed / 0 failed / 1412 skipped · 1126 s · NORMAL (las pruebas multiempresa de DOC-02 corren solo en PostgreSQL, P21) |
| 18 | vitest completo · tsc · eslint · build | `node …` | PASS · vitest 899/899 (83 ficheros; HEAD 814/76 medido con un worktree: **+85** casos, +7 ficheros) · tsc 0 · eslint 0 · build correcto; fixtures regenerados con la herramienta |
| 19 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base, 0 en el ámbito tocado |
| 20 | Alembic | `alembic heads` | PASS · `0066_gov_doc02_actos` (única) |
| 21 | OpenAPI | `openapi_diff` contra HEAD | PASS · 10 rutas nuevas (13 operaciones bajo `/gobierno/actos`), 18 esquemas nuevos, 0 cambiados, 0 retirados, 0 operaciones existentes alteradas |
| 22 | E2E de DOC-02 + regresión ORG-01/02/03 ×3 navegadores | `qa/e2e-run.py --con-analizador --puerto-* 18000/15173/18010 --orden e2e_y_base_doc02.sh` | PASS · `r20261101t200031p3859189nebaa2e`: 82/82 (27 casos × 3 navegadores + HUMO-UAT-01), 0 reintentos, limpieza LIMPIA; antes `r20261101t184748p3646437n3b50f1` 84/84 |
| 23 | E2E canónica | `qa/e2e-run.py --con-analizador` (puertos 18000/15173/18010) | PASS · `r20261101t195031p3825915n61343d`: 415/415 (408 de la línea base + 7 de DOC-02), limpieza LIMPIA. HUMO-UAT-01 sale de la canónica a su proyecto `humo-uat` (ver nota) |
| 24 | Base tras la E2E | `scope_scan` + `integridad_doc02` (C1..C35) sobre la base de la corrida (`--orden`) | PASS · 446 aristas, 0 violaciones; integridad C1..C35 = 0 (24 actos: 15 BORRADOR, 6 EFICAZ, 3 REVOCADO) |
| 25 | Accesibilidad y responsive | axe 1280/768/320 en la E2E | PASS · DOC2-E2E-07: lista, acto y formulario sin violaciones serias y sin desbordamiento a 320 px |
| 26 | Ficha de pantallas y formularios | `SCREEN_FORM_COMPLETENESS.md` | PASS · 7 pantallas/paneles, 0 faltantes |
| 27 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 10 pasos, negativas a–d, autoridad, documentos, reportes, auditoría, historia |
| 28 | Convergencia | `/speckit-converge` | ver el informe de cierre |
| 29 | Secretos | escaneo del diff confirmado | ver el informe de cierre |
| 30 | Residuos | bases efímeras, ficheros temporales, puertos | ver el informe de cierre |

**Nota sobre la canónica (QA-LIC-GOB-01, deuda nueva, fuera de DOC-02).** `qa/licencia_firmada.py` firma licencias sintéticas sin
`entitlements` y `e2e/licencia-periodo.spec.ts` importa una: desde ese momento la instalación de la corrida queda sin el módulo
«gobierno». Corregir la herramienta (probado) destapa 7 specs no gubernamentales (documentos, empresas, N6, crawler) que solo pasaban
con Gobierno apagado (por ejemplo, esperan «Cambiar de empresa» y con Gobierno el botón dice «Cambiar de ente»). Arreglarlas es un
cambio transversal fuera de este ciclo; la herramienta queda como estaba y el humo UAT, que necesita Gobierno, corre en su proyecto.
