# SPEC 054 · Delta dirigida — E2E-CUARENTA-OMITIDAS

**Fecha** 2026-10-12 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) · **Apoyo** 046 (documentos),
008 (almacenes), 011 (unidades), 045 y las Specs funcionales de cada ruta de accesibilidad ·
**Base** `7575f03` · **Rama** `develop` · **Evidencia** `evidence/e2e-cuarenta-omitidas/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `7575f03` |
| `ACTUAL_HEAD` | `7575f03` — **coincide** |
| `REMOTE_HEAD` (`origin/develop`) | `7575f03` |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | limpio |
| `COMMITS_AFTER_7575F03` | **0** |
| `RUN_DATABASES` | **0** (`qa/e2e-bases.py listar`) |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Descubrimiento: dónde se omite y quién decide

**Mecanismos buscados** (`test.skip`, `test.fixme`, `describe.skip`, `skip(`, `fixme(`, `testIgnore`,
`grepInvert`, `.only`) en `resources/frontend/e2e`, `playwright.config.ts` y `qa/`. Hallazgos: **cinco**
`test.skip` condicionales, todos con la misma forma `test.skip(!USER || !PASSWORD, …)`:

| Fichero | Línea | Alcance | Motivo literal |
|---|---|---|---|
| `e2e/accessibility.spec.ts` | 32 | el `describe` «páginas autenticadas» (21 rutas) | `KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados` |
| `e2e/warehouse-a11y.spec.ts` | 19 | fichero (3) | ídem |
| `e2e/documents.spec.ts` | 26 | fichero (8) | ídem |
| `e2e/documents-a11y.spec.ts` | 18 | fichero (4) | ídem |
| `e2e/uom-a11y.spec.ts` | 17 | fichero (4) | `credenciales E2E no configuradas` |

Ni `fixme`, ni `.only`, ni `grepInvert`. El `testIgnore` de la configuración (`DEPENDIENTES`) solo
aparta las cuatro suites de licencia de los proyectos de navegador para que corran en sus proyectos
dependientes: no omite nada en el recuento.

**`playwright.config.ts`, leído:** `PROJECTS` = `chromium`, `firefox`, `webkit`, `licencia-revision`,
`licencia-sync`, `licencia-rotacion`, `licencia-tasa` · `BROWSERS` = Desktop Chrome / Firefox / Safari
(los cuatro dependientes, Desktop Chrome) · `TEST_IGNORE` = `/licencia-(revision|sync|rotacion|tasa)\.spec\.ts/`
en los tres de navegador · `DEPENDENCIES` = cadena `chromium → licencia-revision → licencia-sync →
licencia-rotacion → licencia-tasa` · `RETRIES` = `process.env.CI ? 2 : 0` (en el runner, 0) · `WORKERS` =
por defecto · `GLOBAL_SETUP` = `./e2e/global-setup.ts` · `WEB_SERVER` = ninguno (lo levanta el runner).
No se modificó.

**Runner canónico, leído** (`qa/e2e-run.py` → `qa/e2e_corrida.py`): `orden_de_la_suite` pasa
`--project=chromium --project=licencia-revision --project=licencia-sync --project=licencia-rotacion
--project=licencia-tasa` (verificado en `HEAD`, y por `test_e2ecorrida_14`). **Firefox y WebKit no
forman parte de la corrida canónica**: no están entre las 40 ni cuentan como omitidas (Playwright no
reporta los proyectos no seleccionados). `entorno_de_procesos` fija `KONTROL_E2E_PASSWORD` por defecto
(la de la siembra de QA, que vive en el propio runner) y **no fija `KONTROL_E2E_USER`**, aunque él mismo inicia sesión
como `admin` para comprobar que el backend escribe en la base de la corrida.

**Última corrida real** (`qa/e2e-runs/r20261012t045252p2319011n8f86b8/suite.log`, HEAD `7575f03`):
`236 passed / 0 failed / 40 skipped`, suite 185,2 s. La lista exacta de las 40 salió del reporter `list`
(filas `-`): `evidence/e2e-cuarenta-omitidas/lista-inicial-40.txt`, **40 filas**.

## 3. Las 40, identificadas

| Fichero | Omitidas | Qué cubren |
|---|---|---|
| `accessibility.spec.ts` | 21 | axe WCAG 2.2 AA sobre 21 rutas autenticadas, navegadas por menú (T-12 de la auditoría, + 3 rutas de 045) |
| `documents.spec.ts` | 8 | gestión documental real: carga/versión/descarga, MIME, tamaño, malicioso, IDOR, inmutabilidad, reintento, tipos |
| `documents-a11y.spec.ts` | 4 | WCAG, detalle, carga por teclado, responsive de 046 |
| `uom-a11y.spec.ts` | 4 | WCAG, teclado, responsive, zoom 150 % de 011 |
| `warehouse-a11y.spec.ts` | 3 | WCAG listados y detalle, teclado, responsive de 008 |

Todas `chromium`, todas `ENV_CONDITION`. Matriz completa (requisito, dueña, pantalla, fixture,
dependencia, último verde documentado, origen, reproducción, target y estado final por fila):
`evidence/e2e-cuarenta-omitidas/matriz-40.md`. `EXPLICIT_FIXME = PROJECT_NOT_SELECTED = TEST_IGNORE =
BROWSER_NOT_RUN = FIXTURE_CONDITION = MISSING_SEED = PLATFORM_CONDITION = OTHER = UNKNOWN = 0`.

## 4. Causa real, distinta del mecanismo

El mecanismo es `test.skip` condicional. La causa es que **la corrida canónica nunca exportó
`KONTROL_E2E_USER`**: la variable nació con T-12 (`3fbaf5e`, 2026-08-10) para correr la accesibilidad
«a mano» con credenciales, y las suites de 008, 011 y 046 (`6c04f7b`, `a7afd6b`, `51cbb5a`, 2026-08-30)
copiaron la misma guarda. Los otros veinte ficheros que inician sesión escriben
`process.env.KONTROL_E2E_USER ?? "admin"`. Cuando el runner con base propia llegó (`579affb`, 2026-08-30;
`e2e-run.py`, 2026-10-01) fijó la contraseña y dejó el usuario sin valor: desde entonces las 40 se omiten
en toda certificación. La hoja de ruta ya lo decía (`E2E-CUARENTA-OMITIDAS`, §34 del delta de
estabilidad), y añadía una segunda dependencia real: `clamscan`.

## 5. Reproducción, sin tocar el árbol

```
KONTROL_E2E_USER=admin resources/backend/.venv/bin/python qa/e2e-run.py -- --project=chromium \
  e2e/accessibility.spec.ts e2e/uom-a11y.spec.ts e2e/warehouse-a11y.spec.ts e2e/documents.spec.ts e2e/documents-a11y.spec.ts
→ r20261012t052128p2361605n2dc91d · 37 passed / 4 failed (48,2 s) · limpieza LIMPIA
```

(41 pruebas: las 40 más «login: sin violaciones serias», que ya corría.) **36 de las 40 pasan** con la
sola variable. Las **4 que fallan** son exactamente las que necesitan que una carga termine en versión:

- `documents.spec.ts` · carga, versión y descarga por la interfaz real
- `documents.spec.ts` · una versión histórica no se reinterpreta al cargar otra
- `documents.spec.ts` · un reintento tras el fallo no deja el formulario sin salida
- `documents-a11y.spec.ts` · la carga de archivo es operable solo con teclado

Las cuatro esperan «Versión cargada» y la página muestra **«No se pudo verificar la seguridad del
archivo. Inténtelo de nuevo más tarde.»** (ocho capturas en `test-results/*/error-context.md`). Es el
falso seguro de `ClamAVScanner`: sin binario, `scan()` devuelve `SCAN_FAILED` (`scanner_unavailable`) y
`upload_version` rechaza con 422 todo tipo con `scan_required` (`scanning.py:73-80`,
`service.py:201-213`). `which clamscan` en esta máquina: nada. Es la deuda `ENTORNO-SIN-CLAMSCAN`,
abierta y **no absorbida** aquí. La prueba «un archivo malicioso se rechaza y no queda disponible» pasa
sin `clamscan`: su contrato acepta «malicioso» o «no se pudo verificar» y exige que **no quede archivo**
(invariante 10 de 046); certifica el falso seguro, y la detección del EICAR solo donde haya analizador.

Evidencia: `reproduccion-individual.txt` (sin secretos: 0 contraseñas, 0 tokens).

## 6. `/speckit.specify`

FR-E2E40-001 causa registrada y demostrada por omitida · 002 ninguna omisión sin motivo literal, dueña y
requisito · 003 las certificadas corren en la corrida canónica · 004 sin esperas, reintentos ni aserciones
debilitadas · 005 reescrituras conservan la intención (no hubo) · 006 eliminaciones con prueba de retiro o
sustituta (no hubo) · 007 lo no certificable se declara deuda con dueña y bloqueo · 008 la suite no gana
inestabilidad · 009 dos corridas globales limpias consecutivas · 010 base PostgreSQL nueva por corrida ·
011 bases residuales 0 · 012 producto sin cambio salvo defecto demostrado · 013 un defecto se arregla en su
Spec, no tapándolo en la prueba · 014 sin omisiones nuevas para converger · 015 OpenAPI/autenticación ·
016 roles · 017 licencia, sync, tasa, reverificación, versión, keep-alive 75 · 018 MASTER57 = 57 ·
019 SPEC057 PLANNED / NOT STARTED · 020 NEXT MASTER SPEC NOT YET PRIORITIZED.

Ajuste tras el descubrimiento: la corrida canónica debe **declarar** si el backend tiene analizador
(FR-E2E40-007 aplicado a `ENTORNO-SIN-CLAMSCAN`), para que las cuatro pruebas dependientes se omitan con
nombre, causa y dueña donde no lo hay, y corran y certifiquen donde sí.

## 7. `/speckit.clarify` — 27 puntos, 40/40

1–5 prueba, fichero, nombre, proyecto (`chromium`), navegador (Desktop Chrome): matriz. 6 mecanismo:
`test.skip` condicional. 7 motivo literal: §2. 8 causa: §4. 9–10 requisito y dueña: matriz (Constitución y
T-12 · NFR-011-04/05 · NFR-008-04/05 · NFR-046-04/05 · FR-046-002/005/006/011/012/040/043/044/045/070/072).
11–12 fixture y siembra: sesión UI `admin`/DEMO de la siembra canónica; empresa activa; tipos, documentos y
un almacén creados por API dentro de la prueba. 13 dependencia de entorno: `KONTROL_E2E_USER`. 14 externa:
`clamscan` en 4. 15 solas: 36 pasan, 4 fallan por el analizador. 16 integradas: §13–§14. 17 último verde:
matriz. 18–19 duplicadas: **ninguna** (ninguna otra prueba canónica ejecuta axe sobre esas rutas ni la
carga documental). 20 target: 36 CERTIFY, 4 DECLARE_DEBT. 21 cambio de producto: **no**. 22 cambio del
runner: **sí**, dos variables y una anotación. 23 política de navegadores: no requerida (§12). 24 deuda
final: `ENTORNO-SIN-CLAMSCAN` (ya existente). 25 impacto en tiempo: §14. 26 mutaciones: 17 (§13).
27 DeepSeek: 0 (clasificación, decisión y 31 líneas de cambio; nada mecánico que separe).
`MATERIAL OQ = 0`. `UNKNOWN = 0`.

## 8. Compuerta constitucional

G01–G04 HEAD/rama/MASTER57/SPEC057 ✔ · G05 runner mapeado ✔ · G06 proyectos mapeados ✔ · G07 omitidas
iniciales = 40 ✔ · G08–G12 40/40 identificadas, mecanismo, causa, requisito y dueña ✔ · G13 40/40
reproducidas ✔ · G14 40/40 con target ✔ · G15 sin requisito borrado ✔ · G16 sin aserción debilitada ✔ ·
G17 sin reintentos ✔ · G18 sin timeouts ampliados ✔ · G19 sin omisiones nuevas sin causa ✔ (las cuatro
condicionales llevan nombre, causa y dueña y responden a una dependencia externa demostrada) · G20 producto
0 ✔ · G21 política de navegadores: no afectada ✔ · G22 pruebas y mutaciones definidas ✔ · G23 dos
globales definidas ✔ · G24–G27 BLOCKER 0, MATERIAL OQ 0, UNKNOWN 0, trazabilidad 100 % ✔. **PASS.**
Autorización expresa: la del encargo (`E2E-CUARENTA-OMITIDAS`), condiciones cumplidas (40/40 en todo).

## 9. `/speckit.plan` · `/speckit.tasks`

W01–W08 reconciliación, orquestación, runner, proyectos, lista exacta, matriz, requisitos, origen (§1–§4);
W09–W12 reproducción (§5, una corrida con los cinco ficheros); W13–W15 clasificación, targets, decisiones
materiales (ninguna); W16 certificación; W17–W18 reescrituras/eliminaciones (0); W19 deuda declarada;
W20 fixtures (0); W21 runner (sí, justificado); W22 tiempo; W23 aserciones (0 cambios); W24 mutaciones;
W25 Claude/DeepSeek; W26 dirigida; W27–W28 globales; W29–W31 analyze, trazabilidad, converge.

| Tarea | Requisito | Dueña | EXECUTOR | MODEL | EGRESS_SAFE | Ficheros | Causa | Target | Acción | DONE_WHEN | Prueba | Mutación | RETRY_MAX |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-E2E40-001/002 | 054 | CLAUDE | n-a | n-a | evidencia | — | matriz | lista inicial, matriz 40/40, reproducción | 40 filas con causa, requisito, dueña, target | — | — | — |
| T02 | FR-E2E40-003/007/010 | 054 | CLAUDE | n-a | n-a | `qa/e2e_corrida.py` | runner sin `KONTROL_E2E_USER` | CERTIFY ×36 | exportar `KONTROL_E2E_USER` (por defecto `admin`, la misma identidad que la comprobación del backend) y `KONTROL_E2E_SCANNER_AVAILABLE` resuelto como lo resuelve el backend; anotar `analizador` en el manifiesto | dirigida de los cinco ficheros: 37 pasan, 4 omitidas con nombre | `tests/test_e2e_corrida.py` 14/14 | — | — |
| T03 | FR-E2E40-007 · FR-046-072 | 046 | CLAUDE | n-a | n-a | `e2e/documents.spec.ts`, `e2e/documents-a11y.spec.ts` | `clamscan` ausente | DECLARE_DEBT ×4 | guarda explícita `test.skip(!SCANNER, "ENTORNO-SIN-CLAMSCAN: …")` en las cuatro pruebas que exigen una versión cargada; fuera del runner no se omite | la omisión aparece con el nombre de la deuda; con analizador corren | dirigida | M-11 (vecina) | — |
| T04 | FR-E2E40-004 | 054 | CLAUDE | n-a | n-a | guion de mutaciones (scratchpad) | — | — | 17 mutantes en 3 lotes, uno por prueba (o ayudante con alcance declarado) | cada lote: fallan exactamente las esperadas; RESTORED limpio | — | 17 | — |
| T05 | FR-E2E40-008/009/011 | 054 | CLAUDE | n-a | n-a | — | — | — | dos corridas globales canónicas consecutivas | ambas limpias, 4 omitidas nombradas, bases 0 | `qa/e2e-run.py` ×2 | — | — |
| T06 | FR-E2E40-018/019/020 | 054 | CLAUDE | n-a | n-a | hoja de ruta, `next-spec-decision.md`, recuento MASTER57 | — | — | cerrar la deuda, anotar la dependencia en `ENTORNO-SIN-CLAMSCAN`, puntero | ficheros actualizados; 57 sin cambio | — | — | — |

`CLAUDE_ONLY = 6 · DEEPSEEK_ELIGIBLE = 0`. Razón: clasificación de causas, decisión por prueba, cambio del
runner y guardas ligadas a la clasificación son de Claude por el encargo; el cambio total son 31 líneas en
tres ficheros, sin matriz repetitiva que delegar. `DEEPSEEK CALLS = 0`; egress no aplicó.

## 10. `/speckit.analyze` previo

`INITIAL_SKIPPED = 40 · IDENTIFIED = 40 · CAUSE_PROVEN = 40 · REQUIREMENT_MAPPED = 40 · OWNER_ASSIGNED = 40 ·
TARGET_ASSIGNED = 40 · BLOCKER = 0 · CRITICAL = 0 · CONTRADICTIONS = 0 · OWNER CONFLICT = 0 · ORPHAN
REQUIREMENTS = 0 · ORPHAN TASKS = 0 · MATERIAL OQ = 0 · UNKNOWN = 0 · TRACEABILITY = 100 %`. Búsquedas:
`firefox`/`webkit` solo en la configuración (proyectos no canónicos); `waitForTimeout` preexistente en seis
puntos (cuatro en estas suites, §13); `retries` 0 en el runner; sin `.only`, sin `fixme`, sin `TODO` en los
cinco ficheros.

## 11. Implementación (Claude)

**`qa/e2e_corrida.py`** (+20/−2):
- `entorno_de_procesos` exporta `KONTROL_E2E_USER` (por defecto `admin`) junto a `KONTROL_E2E_PASSWORD`, y
  `KONTROL_E2E_SCANNER_AVAILABLE` = `"true"`/`"false"`.
- `analizador()` resuelve el binario **como lo resuelve el backend** (`KONTROL_CLAMSCAN_PATH`, luego
  `which clamscan` sobre el `PATH` de la corrida; `None` si `KONTROL_DOCUMENT_SCAN=off`, porque con el
  analizador apagado un tipo con `scan_required` también rechaza: `SKIPPED ≠ CLEAN`).
- `preparar` anota `manifiesto["analizador"] = {"clamscan": ruta | null}` y lo dice en la salida.
- La comprobación del backend inicia sesión con `KONTROL_E2E_USER` en vez del literal `admin`: una sola
  identidad para el runner y para las suites.

**`e2e/documents.spec.ts`** (+7) y **`e2e/documents-a11y.spec.ts`** (+4): constante `SCANNER =
process.env.KONTROL_E2E_SCANNER_AVAILABLE !== "false"` y, al principio de las cuatro pruebas que exigen
«Versión cargada», `test.skip(!SCANNER, "ENTORNO-SIN-CLAMSCAN: …, FR-046-072; dueña 046")`. Fuera del
runner la variable no existe y la prueba **corre** (y fallará, con razón, si no hay analizador): la
omisión solo la declara quien ha comprobado el entorno. No se tocan `scan_required`, aserciones,
timeouts ni selectores; las guardas `!USER || !PASSWORD` siguen donde estaban.

**Lo que no cambió:** producto (backend 0, frontend 0), `playwright.config.ts`, fixtures, siembra,
selectores, aserciones, timeouts, retries. Ninguna prueba reescrita ni eliminada.

## 12. Firefox / WebKit

Los proyectos existen en la configuración pero el gate canónico corre `chromium` y sus dependientes, por
decisión previa del runner (`test_e2ecorrida_14` la fija). Ninguna de las 40 provenía de un navegador no
ejecutado, así que ampliar la matriz no es necesario para esta deuda y **no se amplía**: sería una
decisión material de política de certificación (coste, estabilidad, duplicación) que no está en el
encargo. `BROWSER_MATRIX_EXPANSION_WITHOUT_POLICY = 0`.

## 13. Resultados dirigidos

**Dirigida de los cinco ficheros, runner parcheado, sin variables externas**
(`r20261012t052643p2369568n1cea7a`, `dirigido-tras-parche.txt`): **37 passed / 0 failed / 4 skipped** en
20,2 s; manifiesto `"analizador": {"clamscan": null}`; las cuatro omitidas aparecen con su nombre y las
36 restantes de las 40 pasan junto a la de login. Comparada con la reproducción del §5 (37/4 fallos), lo
único que cambió es que el fallo ciego por dependencia externa es ahora una omisión declarada.

**Mutaciones** (`mutaciones.txt`): 17 mutantes en 3 lotes; en cada lote cada mutante vive en una prueba
distinta (o en un ayudante cuyo alcance se declara), de modo que la atribución es exacta: el lote pasa
solo si fallan **exactamente** las pruebas esperadas y ninguna otra.

| Lote | Mutantes | Clases | Esperadas que fallan | Resultado |
|---|---|---|---|---|
| A | M-01 ruta analizada no comprobada (21) · M-02 foco no control · M-03 selector del almacén · M-04 formato admitido no exigido · M-05 WCAG invertida (biblioteca) | navegación, aserción, selector, estado de error, inversión | 25 | **25 fallan, 0 inesperados**, 4 omitidas |
| B | M-06 ayudante WCAG invertido (22) · M-07 scroll umbral imposible · M-08 responsive umbral imposible · M-09 error equivocado aceptado (tamaño) · M-10 WCAG invertida (detalle) | inversión, umbral, estado de error | 26 | **26 fallan, 0 inesperados**, 4 omitidas |
| C | M-11 queda archivo tras el malicioso · M-12 IDOR exige la fuga · M-13 código distinto en tipos · M-14 zoom umbral imposible · M-15 WCAG invertida (unidades) · M-16 ayudante WCAG invertido (2) · M-17 responsive documentos | requisito sorteado, inversión, selector, umbral | 8 | **8 fallan, 0 inesperados**, 4 omitidas |
| RESTORED | — | — | 0 | **37 passed / 0 failed / 4 skipped** |

`GOOD → PASS` (§13 dirigida) · `MUTATED → FAIL` 17/17 (muertos 17, equivalentes 0, supervivientes 0) ·
`RESTORED → PASS`. Las pruebas certificadas detectan lo que afirman: ruta equivocada, foco fuera de un
control, selector roto, mensaje sin el formato admitido, error equivocado, desbordamiento, archivo que
queda tras el rechazo, fuga de `storage_key`, código no creado, y violaciones serias de accesibilidad
(las inversiones fallan porque hoy hay **cero**).

**Frontend** (`frontend-gates.txt`): typecheck ✔ · lint `--max-warnings 0` ✔ (cubre `e2e/`) · Vitest
**467/467** ✔ · build ✔. Producto frontend: 0 cambios.

**Backend**: producto 0 cambios. El runner sí cambió, así que sus pruebas: `tests/test_e2e_corrida.py`
**14/14** sobre PostgreSQL (`KONTROL_TEST_DB_URL=…/ktest`); `ruff check qa/e2e_corrida.py` limpio antes y
después. Las suites completas no se exigen (sin cambio de producto, política del encargo).

**Observación honesta sobre esperas:** cuatro de las pruebas certificadas traen desde su origen un
`page.waitForTimeout(150|200)` tras `setViewportSize`/zoom (`uom-a11y:61,73`, `warehouse-a11y:93`,
`documents-a11y:146`). No se añadió ni amplió ninguna; se dejan como están y se anotan.

## 14. Dos corridas globales canónicas, consecutivas

`resources/backend/.venv/bin/python qa/e2e-run.py`, cada una con su base PostgreSQL nueva, migrada a
`0057_spec047_notifications`, sembrada, verificada y eliminada al terminar.

| Corrida | Id | passed | failed | skipped | Suite | Analizador | Limpieza |
|---|---|---|---|---|---|---|---|
| Línea base (antes del parche) | `r20261012t045252p2319011n8f86b8` | 236 | 0 | 40 | 185,2 s | — | LIMPIA |
| Global 1 | `r20261012t053308p2394299nfe8eb6` | **272** | **0** | **4** | 215,7 s (+16 %) | `null` | LIMPIA |
| Global 2 | `r20261012t053655p2420178n795912` | **272** | **0** | **4** | 201,6 s (+9 %) | `null` | LIMPIA |

236 + 36 = 272. Las 4 omitidas son, en ambas, las mismas cuatro con el nombre de la deuda
(`e2e-global-1.txt`, `e2e-global-2.txt`). Ninguna corrida adicional, ningún reintento (`retries` 0).
Bases de corrida residuales tras todo el ciclo: **0** (`qa/e2e-bases.py listar`). El tiempo crece por
36 pruebas que inician sesión por la interfaz y ejecutan axe; se documenta y no se optimiza omitiendo nada.

## 15. `/speckit.analyze` final

`UNKNOWN_SKIP_CAUSE 0 · SKIP_WITHOUT_OWNER 0 · SKIP_WITHOUT_REQUIREMENT 0 · NEW_UNEXPLAINED_SKIP 0 (las 4
condicionales nombran deuda, causa, requisito y dueña) · ASSERTION_WEAKENING 0 · EXPECT_TRUE_WORKAROUND 0 ·
SLEEP_WORKAROUND 0 (0 añadidos; 4 preexistentes anotados) · RETRY_INFLATION 0 · TIMEOUT_INFLATION 0 ·
TEST_REMOVED_WITHOUT_PROOF 0 · REQUIREMENT_REMOVED_WITHOUT_AUTHORITY 0 · PRODUCT_CHANGE_WITHOUT_PROVEN_DEFECT 0
(producto 0) · BROWSER_MATRIX_EXPANSION_WITHOUT_POLICY 0 · RESIDUAL_RUN_DATABASES 0 · SECRET_EXPOSURE 0
(evidencia escaneada: 0 contraseñas, tokens, claves o URL con credenciales) · ROLES_DELEGATION_POLICY_CHANGED 0 ·
OPENAPI_REGRESSION 0 · ROLES_CREATE_REGRESSION 0 (`roles-alta.spec.ts` pasa en ambas globales) ·
LICENSING_REGRESSION 0 (los cuatro proyectos de licencia pasan) · KEEPALIVE_75_REGRESSION 0 ·
VERSION_PANEL_REGRESSION 0 (`inicio-version.spec.ts` pasa) · PRODUCTION_502_SCOPE_EXPANSION 0 ·
SPEC057_STARTED 0 · NEXT_MASTER_SPEC_SELECTED 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 ·
ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.`

## 16. Trazabilidad y contabilidad de la reducción

`INITIAL_SKIPPED 40 → CERTIFIED 36 + REWRITTEN_AND_CERTIFIED 0 + REMOVED_WITH_PROOF 0 + DECLARED_DEBT 4 +
BLOCKED_DECISION 0 = 40`. `FINAL_SKIPPED = 4`, todas nombradas: E40-23 (`documents-a11y` · carga por
teclado), E40-26 (`documents` · carga, versión y descarga), E40-31 (`documents` · versión histórica),
E40-32 (`documents` · reintento) → `ENTORNO-SIN-CLAMSCAN`, dueña 046, bloqueo `clamscan` ausente,
siguiente acción: instalar el analizador en QA (fuera de este ciclo) y la corrida las ejecuta sin tocar nada.

Cadena por prueba (matriz, 40/40): omisión → causa (`KONTROL_E2E_USER` sin exportar; + `clamscan` en 4) →
requisito (Constitución/T-12, NFR-011-04/05, NFR-008-04/05, NFR-046-04/05, FR-046-002…072) → dueña
(054/011/008/046) → target (CERTIFY/DECLARE_DEBT) → T02/T03 → evidencia (`reproduccion-individual.txt`,
`dirigido-tras-parche.txt`, `mutaciones.txt`, `e2e-global-1.txt`, `e2e-global-2.txt`) → estado final.
Requisitos FR-E2E40-001…020 → tareas T01–T06 → evidencia: 100 %.

## 17. Convergencia

**`E2E-CUARENTA-OMITIDAS — CLOSED / CONVERGED`.** 40 identificadas, 40 con causa demostrada, 40 con
requisito, dueña y target; 36 certificadas en la corrida canónica en dos globales limpias consecutivas;
4 convertidas de omisión muda en deuda nombrada con dueña (`ENTORNO-SIN-CLAMSCAN`, que sigue abierta);
0 reescritas, 0 eliminadas, 0 bloqueadas; producto 0; 17/17 mutantes muertos; bases residuales 0.
Orquestación: 6 tareas, 6 `CLAUDE_ONLY`, 0 `DEEPSEEK_ELIGIBLE`, 0 llamadas, coste 0. Hoja de ruta,
`next-spec-decision.md` y recuento MASTER57 (57, sin cambio) actualizados. SPEC057 PLANNED / NOT STARTED;
NEXT MASTER SPEC NOT YET PRIORITIZED; producción fuera de ciclo.
