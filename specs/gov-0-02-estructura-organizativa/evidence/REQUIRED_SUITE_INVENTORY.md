# GOV-0-02 · inventario de suites exigidas

Creado antes de la implementación semántica (2026-10-30); el resultado se rellena al certificar.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Reconciliación del repositorio | `git fetch`; HEAD == origin == `41a3e78`; árbol | PASS (solo el `.docx` protegido sin seguimiento) |
| 2 | Regresión de ORG-01 | `tests/test_gov0_ente.py` + `e2e/gobierno-ente.spec.ts` ×3 navegadores | PASS · backend 18/18; E2E GOV-E2E-01..05 ×3 navegadores en las 3 corridas (36/36 con ORG-02) y en la canónica |
| 3 | GOV0-UI-01 | vitest de la compuerta + E2E en `/gobierno/*` | PASS · GUI-01..03 (vitest) + GOV2-E2E-06 ×3 navegadores; mutante GF10 KILLED |
| 4 | Requisitos de Gobierno | GOV-ORG-002/008 → spec §2–§11 | PASS (spec) |
| 5 | Revisión normativa | N02, N03, N04, N21, N24 (A); ejercicio 1 ene–31 dic por OD-ORG02-01 | PASS (sin cita de artículo: no verificado textualmente; corrección del 2026-11-01) |
| 6 | Modelo de proceso / ejercicio / jerarquía | spec §3–§5 | PASS (diseño) |
| 7 | BD dirigida | migración 0064 upgrade → downgrade → upgrade; restricciones | PASS · PostgreSQL: upgrade → downgrade `0063_gov0_entes` → upgrade (5 → 2 → 5 tablas `gov_`) sobre una base propia, borrada después; cabeza única `0064_gov0_estructuras`. SQLite no se migra con Alembic (la suite crea el esquema desde los modelos) |
| 8 | API dirigida | `tests/test_gov0_estructura.py` | PASS · 32/32 (GS-01..29; GS-28/29 añadidas por la convergencia) en PostgreSQL; primero en rojo antes del servicio |
| 9 | Permisos y alcance | ídem (consulta, otro ente, otro tenant, UUID directo) | PASS · GS-14, GS-23, GS-24, GS-27 y barridos `test_iso_barridos.py` (IDS/LISTAS) sin hallazgos |
| 10 | Concurrencia | ídem (`If-Match`, estructura bloqueada) | PASS · GS-10 (`If-Match` de unidad: 428 sin él, 409 con versión vieja), GS-13 y GS-21 (versión de la estructura al publicar y cerrar) |
| 11 | Frontend: menú, pantallas, formularios | vitest | PASS · GEJ-01..06, GES-01..10, GUF-01..05, GDU-01/02, GSB-04/05, NOT-01..03 |
| 12 | Documentos | ídem + E2E (acto con analizador real) | PASS · GS-04, GS-13, GS-15, GS-27 + GOV2-E2E-01 con ClamAV real (`--con-analizador`) |
| 13 | Reportes | CSV (backend + UI + E2E) | PASS · GS-20 (CSV), botón «Exportar CSV» en GES, GOV2-E2E-01 (descarga `estructura-AAAA.csv`) |
| 14 | Auditoría | 8 acciones; guarda del catálogo | PASS · 39 comprobaciones de acciones `GOV_STRUCTURE_*`/`GOV_UNIT_*` en `test_gov0_estructura.py`; catálogo 236 → 244 (CATB-03); C9 de la base tras la E2E |
| 15 | Negativas y hostiles | ídem | PASS · GS-07/08/16/17/18/21/23/24/27 (ciclos, código, campos bloqueados, otro ente, otro tenant, UUID directo) |
| 16 | Mutaciones de negocio | `mutar07b` | PASS · 38 mutantes: 36 KILLED, 2 EQUIVALENT justificados, 0 supervivientes (`MUTATIONS.md`) |
| 17 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261031t221301p53287nfa83cf`: 4107 passed / 0 failed / 18 skipped · 2886 s · anomalía NORMAL |
| 18 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261031t230126p506521n25350b`: 2781 passed / 0 failed / 1344 skipped · 932 s · anomalía NORMAL |
| 19 | vitest completo · tsc · eslint · build | `node …` | PASS · vitest 763/763 (71 ficheros) · tsc 0 · eslint 0 avisos · build correcto; fixtures (`qa/fixtures_de_frontend.py`) sin cambios |
| 20 | ruff · mypy sin errores nuevos (línea base 154 en 18 ficheros ajenos) | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 errores en 18 ficheros = línea base, 0 en `app/modules/government` |
| 21 | Alembic: cabeza única 0064 | guardas MIG/KR | PASS · `alembic heads` = `0064_gov0_estructuras` (única); guardas MIG/KR en verde en la suite |
| 22 | OpenAPI | `openapi_diff` contra HEAD | PASS · 9 rutas nuevas, 10 esquemas nuevos, 0 cambiados, 0 eliminados (todas de `/gobierno/estructuras`) |
| 23 | E2E de ORG-02 ×3 navegadores | `qa/e2e-run.py --con-analizador -- e2e/gobierno-estructura.spec.ts --project=firefox --project=webkit` | PASS · `e2e/gobierno-estructura.spec.ts` + `e2e/gobierno-ente.spec.ts` ×3 navegadores ×3 corridas: 36/36 cada una, 0 reintentos, limpieza LIMPIA (`r20261031t220508…`, `r20261031t220731…`, `r20261031t220959…`) |
| 24 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261031t231658p639771n00f2cf`: 400/400, limpieza LIMPIA |
| 25 | Base tras la E2E | consulta de integridad sobre una corrida conservada (`--orden`) | PASS · `r20261031t232615p672653ncb8109` (ORG-02 + ORG-01 ×3 navegadores, 36/36) y sobre su base: `scope_scan` 429 aristas, 0 violaciones, 0 roles de instalación personalizados; integridad de ORG-02 C1..C10 = 0 (24 estructuras, 45 unidades, 54 versiones, 177 eventos `GOV_*`) |
| 26 | Accesibilidad y responsive | axe 1280/768/320 en la E2E | PASS · GOV2-E2E-07: axe sin violaciones serias a 1280/768/320 y sin desbordamiento a 320 px |
| 27 | Ficha de pantallas y formularios | `SCREEN_FORM_COMPLETENESS.md` | PASS · `SCREEN_FORM_COMPLETENESS.md`: 6 pantallas, 0 faltantes |
| 28 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · `OWNER_UAT_CARD.md` (10 pasos, negativas, documentos, reportes, auditoría) |
| 29 | Secretos | escaneo del diff confirmado | PASS · escaneo del diff: 0 secretos, 0 claves, 0 URLs con credenciales, 0 PII |
| 30 | Residuos | bases efímeras, ficheros temporales, puertos | PASS · CLEAN: 0 bases de corrida ajenas, 0 ficheros temporales en el árbol, puertos de E2E libres. Única base viva y puertos 18100/15273/18110: el entorno de prueba de la dueña, levantado a propósito |

Errata registrada el 2026-11-01: el mensaje del commit `e993792` dice «vitest +43»; el delta medido es **+36** (727 en `HEAD~1`, medido con un worktree, → 763). La historia publicada no se reescribe; esta nota es la corrección.
