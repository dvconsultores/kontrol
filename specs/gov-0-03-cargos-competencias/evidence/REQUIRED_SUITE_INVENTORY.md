# GOV-0-03 · inventario de suites exigidas

Creado antes de la implementación semántica (2026-11-01); el resultado se rellena al certificar.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; rama por defecto; HEAD == origin == `e993792` | PASS · `feature/001-fundacion`: ancestro de `develop` (AHEAD 249, BEHIND 0, base `8c82289`), 0 commits propios, eliminada; rama por defecto `develop`; REMOTE_BRANCH_COUNT = 1; `git-governance.md` §0 |
| 2 | Deudas documentales | LOAFSP; errata vitest | PASS · N03 y OD-ORG02-01 sin cita de artículo no verificado; errata del commit `e993792` (+43 → +36) anotada en la evidencia de ORG-02 sin reescribir historia |
| 3 | Regresión de ORG-01 y ORG-02 | `tests/test_gov0_ente.py`, `tests/test_gov0_estructura.py` + `e2e/gobierno-ente.spec.ts`, `e2e/gobierno-estructura.spec.ts` ×3 navegadores | PASS · backend en las suites completas; GS-25 ajustada para excluir `/cargos`; E2E de ORG-01/02 ×3 navegadores en las 3 corridas (60/60 con ORG-03) y en la canónica |
| 4 | Requisitos de Gobierno | GOV-ORG-003 (+ vocabulario de GOV-ORG-010) → spec §2–§11 | PASS (spec); ORG-04 (delegación) fuera de alcance |
| 5 | Modelo de proceso / cargo / competencia / límite | spec §3–§5 | PASS (diseño; OD-ORG03-01..04 de la dueña) |
| 6 | BD dirigida | migración 0065 upgrade → downgrade → upgrade | PASS · PostgreSQL: 8 → 5 → 8 tablas `gov_` sobre una base propia (`gov3mig`), borrada después; cabeza única `0065_gov0_cargos`. SQLite crea el esquema desde los modelos |
| 7 | API dirigida | `tests/test_gov0_cargos.py` | PASS · 31/31 (GC-01..27, con parametrizados) en PostgreSQL; primero en rojo antes del servicio |
| 8 | Permisos, autoridad y alcance | ídem (consulta, preparador sin `publish`, otro ente, otro tenant, UUID directo) | PASS · GC-13, GC-22, GC-23, GC-24 y barridos `test_iso_barridos.py` sin hallazgos |
| 9 | Concurrencia | ídem (`If-Match` del cargo; estructura bloqueada `FOR UPDATE`) | PASS · GC-07 (428 sin `If-Match`, 409 STALE con versión vieja); toda escritura pasa por `_estructura(..., bloquear=True)` |
| 10 | Dinero | vectores del límite (texto decimal, > 0, ≤ 2 decimales, ≤ 16 enteros, número JSON rechazado, coherencia) | PASS · GC-06 (vectores), GKF-03/05 (cliente); `Numeric(18,2)`, sin `float` |
| 11 | Frontend: menú, pantallas, formularios | vitest | PASS · GCE-01..04, GCL-01..10, GCP-01..13, GCF-01..05, GKF-01..07, GDC-01, GRC-01/02, GSB-06/07 (cargos 45/45) |
| 12 | Documentos | acto del cargo (046) con analizador real | PASS · GC-08, GC-10, GC-17 + GOV3-E2E-01 con ClamAV real (`--con-analizador`) |
| 13 | Reportes | CSV (backend + UI + E2E) | PASS · GC-19 (CSV, una fila por competencia), «Exportar CSV» en GCL, GOV3-E2E-01 (descarga `cargos-AAAA.csv`) |
| 14 | Auditoría | 9 acciones; guarda del catálogo | PASS · comprobaciones `GOV_POSITION_*`/`GOV_COMPETENCY_*` en `test_gov0_cargos.py`; catálogo 244 → 253 (CATB-03); `cargos_copiados` en GOV_STRUCTURE_CREATED; C22 de la base tras la E2E |
| 15 | Interacción con ORG-02 | copia de cargos; unidad con cargos | PASS · GC-18, GC-20, GC-21, GC-25, GC-27 |
| 16 | Negativas y hostiles | ídem | PASS · duplicados, campos bloqueados, última competencia, unidad inactiva, ejercicio cerrado, otro ente, otro tenant, UUID directo |
| 17 | Mutaciones de negocio | `mutar07b` | PASS · 40 mutantes: 39 KILLED, 1 EQUIVALENT justificado, 0 supervivientes (`MUTATIONS.md`) |
| 18 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261101t044000p1738968nd30cb5`: 4142 passed / 0 failed / 18 skipped · 3012 s · anomalía NORMAL (ORG-02: 4107; +35 = 31 de `test_gov0_cargos.py` y 4 de guardas). Con `KONTROL_PG_BIN_DIR` (sin él, 30 pruebas de copia de seguridad fallan por falta de `pg_dump` en el PATH: entorno, no producto) |
| 19 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261101t044000p1738970n59581d`: 2786 passed / 0 failed / 1374 skipped · 1110 s · anomalía NORMAL (ORG-02: 2781/0/1344; de `test_gov0_cargos.py` corren 5 y 26 se omiten por P21: el aislamiento multiempresa se verifica sobre PostgreSQL) |
| 20 | vitest completo · tsc · eslint · build | `node …` | PASS · vitest 814/814 (76 ficheros; HEAD 763/71 medido con un worktree: **+51** casos, +5 ficheros) · tsc 0 · eslint 0 avisos · build correcto; fixtures regeneradas con la herramienta |
| 21 | ruff · mypy sin errores nuevos (línea base 154 en 18 ficheros ajenos) | `.venv/bin/ruff check` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 errores en 18 ficheros = línea base, 0 en `app/modules/government` |
| 22 | Alembic: cabeza única 0065 | guardas MIG/KR | PASS · `alembic heads` = `0065_gov0_cargos` (única) |
| 23 | OpenAPI | `openapi_diff` contra HEAD | PASS · 9 rutas nuevas (12 operaciones, todas bajo `/gobierno/estructuras/{ejercicio}/cargos`), 12 esquemas nuevos, 0 cambiados, 0 retirados, 0 operaciones existentes alteradas |
| 24 | E2E de ORG-03 ×3 navegadores | `qa/e2e-run.py --con-analizador --puerto-* 18000/15173/18010 --orden …` | PASS · `gobierno-cargos` + `gobierno-estructura` + `gobierno-ente` ×3 navegadores ×3 corridas: 60/60 cada una, 0 reintentos, limpieza LIMPIA (`r20261101t040951…`, `r20261101t041457…`, `r20261101t042023…`) |
| 25 | E2E canónica | `qa/e2e-run.py --con-analizador` (puertos 18000/15173/18010) | PASS · `r20261101t042810p1690420n42879e`: 408/408, limpieza LIMPIA |
| 26 | Base tras la E2E | `scope_scan` + `integridad_org03` (C1..C23) sobre la base de cada corrida (`--orden`) | PASS · en las 3 corridas: `scope_scan` 438 aristas, 0 violaciones; integridad C1..C23 = 0 (54 estructuras, 27 cargos, 30 competencias, 81 versiones de cargo, 450 eventos `GOV_*`) |
| 27 | Accesibilidad y responsive | axe 1280/768/320 en la E2E | PASS · GOV3-E2E-08: axe sin violaciones serias a 1280/768/320 y sin desbordamiento a 320 px (tras T006h) |
| 28 | Ficha de pantallas y formularios | `SCREEN_FORM_COMPLETENESS.md` | PASS · 6 pantallas/formularios, 0 faltantes |
| 29 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 11 pasos, negativas a–d, documentos, reportes, auditoría, historia |
| 30 | Convergencia | `/speckit-converge` | PASS · convergido: 0 hallazgos; `tasks.md` sin fase de convergencia |
| 31 | Secretos | escaneo del diff confirmado | PASS · escaneo del diff (incluidos los ficheros nuevos): 0 claves privadas, 0 tokens, 0 URLs con credenciales, 0 contraseñas literales, 0 ficheros `.env`/`.pem`/`.key`; datos sintéticos |
| 32 | Residuos | bases efímeras, ficheros temporales, puertos | PASS · CLEAN: 0 bases de corrida del ciclo (las 6 corridas E2E limpiaron: LIMPIA), base `gov3mig` borrada, worktree temporal de medición retirado, 0 ficheros temporales en el árbol, puertos 18000/15173/18010 libres. Única base viva y puertos 18100/15273/18110: el entorno de prueba de la dueña congelado en `e993792`, levantado a propósito |
