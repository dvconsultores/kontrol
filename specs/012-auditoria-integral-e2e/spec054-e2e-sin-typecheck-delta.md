# SPEC 054 · Delta dirigida — E2E-SIN-TYPECHECK

**Fecha** 2026-10-12 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) · **Apoyo** SPEC001 (arnés
frontend; contrato del listado de empresas), SPEC047 (la suite con el único defecto de tipos) ·
**Antecedente** `spec054-typecheck-gate-delta.md` (BUILD-TSC-TESORERIA) y `spec054-reservation-identity-delta.md`
§19 (donde nació la deuda) · **Base** `eccaddd` · **Rama** `develop` · **Evidencia** `evidence/e2e-sin-typecheck/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `eccaddd` / `eccaddd` / `eccaddd` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_ECCADDD` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Descubrimiento: el grafo TypeScript, leído

| Registro | Valor |
|---|---|
| `ROOT_TSCONFIG` | `tsconfig.json`: solución (`files: []`), `references` → `tsconfig.app.json`, `tsconfig.node.json` |
| `APP_TSCONFIG` | `include: ["src"]`; ES2022 + DOM + DOM.Iterable; `moduleResolution bundler`; `jsx react-jsx`; `noEmit`; `strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noUncheckedSideEffectImports`; `paths @/*` |
| `NODE_TSCONFIG` | `include: ["vite.config.ts"]`; ES2023; `types: ["node"]`; misma severidad; `noEmit` |
| `CURRENT_INCLUDE` / `CURRENT_EXCLUDE` | `src` + `vite.config.ts` / ninguno. **`e2e/` y `playwright.config.ts` fuera de todo proyecto** |
| `TYPECHECK_SCRIPT` · `BUILD_SCRIPT` | `tsc -b --noEmit` · `tsc -b && vite build` |
| `LINT_SCRIPT` · `TEST_SCRIPT` · `E2E_SCRIPT` | `eslint . --max-warnings 0` (sí recorre `e2e/*.ts`) · `vitest run` (`src/**`) · `playwright test` |
| `TYPECHECK_IN_CI` | **no directo**: `.github/workflows/build-*.yml` solo construyen imágenes; `Dockerfile.frontend` ejecuta `npm run build` → `tsc -b` |
| `TYPECHECK_IN_E2E_RUNNER` · `TYPECHECK_IN_BUILD` | no · sí (`tsc -b`) |
| `E2E tree` | `TS_FILES 52` (46 suites + `global-setup.ts` + 6 ayudantes, sin `.tsx`) · `JS 0` · `MJS 2` (`audit-route-crawler.mjs`, `audit-responsive-crawler.mjs`: herramientas manuales de la auditoría 012, `node e2e/*.mjs`, fuera de Playwright) · `TOTAL 54` · `playwright.config.ts` fuera de `e2e/` |
| Entorno real | 48 de 52 ficheros usan `process`, `Buffer` o `node:*`; `page.evaluate` usa `document` (DOM); tipos de Playwright por `import` de `@playwright/test` |
| Supresores preexistentes en `e2e/` | `@ts-ignore` 0 · `@ts-expect-error` 0 · `as any` 0 · `: any` 0 · `as unknown as` 0 |
| `e2e/` importa de `src/` | **0** ficheros: no necesita `paths @/*` ni JSX |

## 3. Experimento de línea base (sin tocar el repositorio)

**ETS-01, reproducción:** un error sintético (`const deberiaSerNumero: number = "mal"`) añadido a
`e2e/smoke.spec.ts` → `tsc -b --noEmit` termina en **0**. El gate canónico no mira `e2e/`. Restaurado.

**Medición:** `tsconfig` temporal en el scratchpad (extiende `tsconfig.app.json`, `types: ["node"]`,
`typeRoots` del proyecto, `include` `e2e/**/*.ts` + `playwright.config.ts`):
`tsc --noEmit -p …` → **exit 2 · 4 errores · 2,79 s** (`linea-base.txt`).

| Fichero:línea | Código | Clasificación | Causa |
|---|---|---|---|
| `notifications.spec.ts:99` y `:118` | TS2339 `items` no existe en `T[] \| {items: T[]}` | **API_TYPE_DRIFT / REAL_TEST_TYPE_DEFECT** | unión «array o sobre» del listado de empresas, obsoleta desde `e813e6f` (2026-09-30): el sobre `{items}` es el contrato y «la tolerancia array o sobre se retira»; el código ya desreferencia `.items`, la rama array estaba muerta |
| `notifications.spec.ts:100` y `:118` | TS7006 parámetro `e` con `any` implícito | **IMPLICIT_ANY (derivado)** | el `find` pierde el tipo cuando `.items` no resuelve; mismo arreglo |

`BASELINE_ERROR_COUNT = 4 · ERROR_CLASSIFIED = 100 % · UNKNOWN = 0`. Ningún error de entorno (Node, DOM,
Playwright), ninguno en ayudantes, fixtures, `global-setup` ni `playwright.config.ts`. Dueñas del único
defecto: 047 (suite) y 001 (contrato de listados). Es un **defecto de tipo de la prueba**, no de producto:
el frontend y el backend ya hablan `{items}`; corregir el tipo no cambia ninguna aserción ni dato.

## 4. `/speckit.specify`

FR-E2ETS-001 todo `.ts` de la suite E2E cubierto por un gate explícito del repositorio · 002 el gate falla
ante un error de tipos en E2E · 003 la severidad de `src` no cambia · 004 el typecheck de E2E no añade
artefactos al build · 005/006 ningún supresor ni `any` nuevo · 007/008 correcciones sin cambiar semántica ni
aserciones · 009 tipos Node/DOM/Playwright explícitos según el runtime real · 010 `playwright.config.ts`,
`global-setup`, ayudantes y fixtures cubiertos · 011/012 el gate canónico lo invoca (un guion que nadie
ejecuta no vale) · 013 salida del build sin cambio · 014/015 E2E 272/0/4 con las cuatro omisiones de
`ENTORNO-SIN-CLAMSCAN` intactas · 016/017 typecheck no ejecuta E2E ni E2E sustituye al typecheck ·
018–021 auth/OpenAPI, roles, licencia, sync, tasa, reverificación, versión, keep-alive y esquema sin cambio ·
022–024 MASTER57, SPEC057, NEXT MASTER SPEC sin cambio.

## 5. `/speckit.clarify` — 30 puntos

1–3 grafo, typecheck y build: §2. 4–5 ficheros E2E y cobertura actual: 52 `.ts` + config, **0 %**.
6–8 Node (`process`, `Buffer`, `node:child_process`), DOM (`document` en `page.evaluate`), Playwright
(por `import`): los tres hacen falta. 9–11 `global-setup`, ayudantes y `playwright.config.ts`: TypeScript,
entran. 12 JS/MJS: los dos crawlers son herramientas manuales de auditoría, no corren en Playwright y no
son TypeScript; `checkJs` no se habilita sin evidencia; quedan fuera y se documenta. 13–14 línea base: 4
errores, clasificados. 15 **diseño: proyecto separado `tsconfig.e2e.json` referenciado desde la solución**
(opción B, que coincide con D: es exactamente el patrón ya ratificado para `tsconfig.node.json`, una
herramienta no productiva con su propio entorno; incluir `e2e/` en el proyecto `app` mezclaría runtimes —
Node + DOM sin JSX ni alias— y ampliaría el proyecto del producto). 16 gate canónico: `npm run typecheck`
(`tsc -b --noEmit`), que ya recorre las referencias; **sin guion nuevo**. 17 `package.json`: sin cambio.
18 CI/QA: el `tsc -b` del build (Docker) también lo recorre, como ya hacía con `vite.config.ts`; el runner
E2E no cambia. 19 build: `noEmit`, 0 artefactos (§8). 20 severidad: la misma que `src` (`strict`,
`noUnused*`, `noFallthrough`, `noUncheckedSideEffectImports`); sin `jsx`, sin `paths`, sin
`allowImportingTsExtensions` (nada lo usa). 21–22 supresores: 0 antes, 0 nuevos. 23 control negativo:
M-01. 24 directorio vacío: M-02/M-03 contra la prueba de contrato, que exige ≥ 40 ficheros y 0 fuera.
25 cobertura: la prueba resuelve los ficheros **como los resuelve `tsc`** (`parseJsonConfigFileContent`) y
los compara con el disco. 26 rendimiento: §8. 27 pruebas: ETS-01…25. 28 mutaciones: 11 (M-05 no
aplica: los tipos de Playwright llegan por `import`, no por `types`; «quitarlos» sería romper el paquete,
no la configuración). 29 E2E: una suite cambia (solo tipos) → dirigida + **dos** globales. 30 DeepSeek: 0
(el cambio son dos líneas de tipo, una configuración y una prueba de contrato cuyo diseño es la decisión).
`MATERIAL OQ = 0 · UNKNOWN = 0`. Ninguna condición de STOP: el modelo de proyecto se deriva del grafo
existente; ningún error exige semántica nueva; `src` no se toca; el build no emite E2E.

## 6. Compuerta constitucional

G01–G04 ✔ · G05 grafo probado ✔ · G06 guiones ✔ · G07 inventario ✔ · G08 línea base medida (4) ✔ ·
G09 100 % clasificados ✔ · G10 entorno Node/DOM/Playwright probado ✔ · G11 diseño probado por el patrón
de `tsconfig.node.json` ✔ · G12 integración en el gate canónico (`tsc -b` recorre referencias; probado por
la prueba de contrato y por M-08) ✔ · G13 aislamiento del build (`noEmit`, `dist` idéntico) ✔ ·
G14 severidad preservada ✔ · G15 supresores 0/0 ✔ · G16 JS/MJS fuera con razón ✔ · G17 control negativo ✔ ·
G18 cobertura de ficheros ✔ · G19 comparación de `dist` ✔ · G20–G22 pruebas, mutaciones, política E2E ✔ ·
G23 tareas clasificadas ✔ · G24–G27 BLOCKER 0, MATERIAL OQ 0, UNKNOWN 0, trazabilidad 100 % ✔. **PASS.**
Autorización expresa: la del encargo, con `TSCONFIG_GRAPH`, `BASELINE_ERROR_COUNT`, `ERROR_CLASSIFICATION`,
`E2E_PROJECT_DESIGN`, `CANONICAL_GATE_INTEGRATION` y `PRODUCT_BUILD_ISOLATION` = PROVEN.

## 7. `/speckit.plan` · `/speckit.tasks`

W01–W19 (§1–§6) · W20–W22 implementación (§8) · W23–W28 gates y `dist` (§9) · W29–W30 E2E (§10) ·
W31–W33 analyze, trazabilidad, converge (§11–§13).

| Tarea | Requisito | Dueña | EXECUTOR | MODEL | EGRESS | Ficheros | Acción | DONE_WHEN | Prueba | Mutación | RETRY |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-E2ETS-001/009/010 | 054 | CLAUDE | n-a | n-a | `tsconfig.e2e.json` (nuevo) | proyecto E2E: ES2022 + DOM, `types node`, misma severidad, `noEmit`, `include e2e + playwright.config.ts` | `tsc -b tsconfig.e2e.json --noEmit` limpio; 53 ficheros recorridos | ETS-02/03/09–13 | M-04, M-06, M-07, M-09, M-10 | — |
| T02 | FR-E2ETS-011/012 | 054 | CLAUDE | n-a | n-a | `tsconfig.json` | tercera referencia | `npm run typecheck` recorre e2e (ETS-01 invertido) | ETS-04 | M-01, M-08 | — |
| T03 | FR-E2ETS-007/008 · FR-001 (listados) | 047/001 | CLAUDE | n-a | n-a | `e2e/notifications.spec.ts` | el genérico pasa a `{ items: … }` en dos llamadas | 0 errores; mismas aserciones | ETS-18 dirigida | — | — |
| T04 | FR-E2ETS-002/004/005/006 | 054 | CLAUDE | n-a | n-a | `src/tests/typecheck-gate.test.ts` | seis pruebas de contrato: referencia, cobertura real (resolución de `tsc` vs disco, ≥ 40), `noEmit` y `src` intacto, Node + DOM, severidad igual al producto, 0 supresores | 12/12 | ETS-02/05/07/08 | M-02, M-03, M-08–M-12 | — |
| T05 | FR-E2ETS-011 | 054 | CLAUDE | n-a | n-a | `.claude/CLAUDE.md` (comandos) | `npm run typecheck` «recorre src, herramientas y e2e» | documentado | — | — | — |
| T06 | FR-E2ETS-014/015 | 054 | CLAUDE | n-a | n-a | — | dirigida `notifications` + dos globales | 272/0/4 ×2, bases 0 | ETS-19/20 | — | — |
| T07 | FR-E2ETS-022–024 | 054 | CLAUDE | n-a | n-a | hoja de ruta, `next-spec-decision.md`, recuento MASTER57 | cerrar la deuda; puntero; 57 sin cambio | ficheros actualizados | — | — | — |

`CLAUDE_ONLY 7 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0`: arquitectura del grafo, política del compilador,
clasificación y diseño del control son de Claude por el encargo; lo mecánico (dos líneas de tipo) no
justifica una delegación.

## 8. Implementación (Claude)

- **`tsconfig.e2e.json`** (nuevo): copia la severidad de `tsconfig.app.json` (`strict`, `noUnusedLocals`,
  `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noUncheckedSideEffectImports`), `lib` ES2022 + DOM +
  DOM.Iterable (los callbacks de `page.evaluate` corren en el navegador), `types: ["node"]` (`process`,
  `Buffer`, `node:child_process`), `module ESNext` / `moduleResolution bundler` / `isolatedModules` /
  `moduleDetection force` como los otros dos, `noEmit`, `tsBuildInfoFile` en `node_modules/.tmp` como los
  otros dos. Sin `jsx`, sin `paths`, sin `allowImportingTsExtensions`: nada en `e2e/` los usa (0 importaciones
  de `src/`). `include: ["e2e", "playwright.config.ts"]`; sin `exclude`. Los dos `.mjs` quedan fuera por no
  ser TypeScript (sin `allowJs`/`checkJs`).
- **`tsconfig.json`**: tercera referencia `./tsconfig.e2e.json`. Con ello `npm run typecheck` (`tsc -b
  --noEmit`) y el `tsc -b` del build recorren `e2e/`, exactamente como ya recorrían `vite.config.ts`.
- **`e2e/notifications.spec.ts`**: en las dos llamadas a `pedir` sobre `/organization/companies` el genérico
  pasa de `T[] | { items: T[] }` a `{ items: T[] }`. Ninguna aserción, dato ni flujo cambia: el código ya
  leía `.items`.
- **`src/tests/typecheck-gate.test.ts`**: cabecera actualizada (ya no dice que `e2e/` queda fuera) y un
  segundo `describe` con seis pruebas de contrato (T04). La cobertura se calcula con la API de TypeScript
  (`readConfigFile` + `parseJsonConfigFileContent`) y se compara con un recorrido real del disco: un
  `include` vacío, equivocado o parcial falla aunque `tsc` termine en 0.
- **`.claude/CLAUDE.md`**: la línea de comandos canónicos dice qué recorre `npm run typecheck`.

**Sin cambio:** `package.json` (ningún guion nuevo: el canónico ya basta), `tsconfig.app.json`,
`tsconfig.node.json`, `vite.config.ts`, `playwright.config.ts`, producto (backend 0, frontend 0), runner E2E,
CI. `NEW_TS_IGNORE 0 · NEW_TS_EXPECT_ERROR 0 · NEW_ANY 0`.

## 9. Resultados estáticos (`frontend-gates.txt`, `mutaciones.txt`, `ficheros-recorridos.txt`)

| Gate | Resultado |
|---|---|
| `PRODUCT_TYPECHECK` + `E2E_TYPECHECK` (`tsc -b --noEmit`, el canónico) | **PASS** · 11,6 s (antes 9,7 s: +1,9 s) |
| `E2E_TYPECHECK` solo (`tsc -b tsconfig.e2e.json --noEmit`, sin caché) | PASS · 1,4 s |
| Ficheros recorridos por `tsconfig.e2e.json` (`--listFilesOnly`, sin `node_modules`) | **53** = 52 `.ts` de `e2e/` + `playwright.config.ts` → `E2E_TS_FILES_TYPECHECKED / TOTAL = 100 %` |
| ETS-01 (antes) | error sintético en `e2e/` → `tsc -b --noEmit` exit 0: **no se detectaba** |
| ETS-04 (después, M-01) | el mismo error → exit 2 `TS2322`; restaurado → 0 |
| `LINT` (`eslint . --max-warnings 0`) | PASS |
| `VITEST` | **473/473** (467 + 6 de contrato) |
| `BUILD` (`tsc -b && vite build`) | PASS |
| `dist/` antes/después | **idéntico**: mismo listado (133 ficheros) y mismos SHA-256; artefactos E2E en `dist`: 0 |

**Mutaciones** (GOOD → PASS, MUTATED → FAIL, RESTORED → PASS; caché `tsbuildinfo` borrada antes de cada
typecheck):

| Mutante | Gate que lo mata | Resultado |
|---|---|---|
| M-01 error de tipos sintético en una suite | typecheck canónico | muere (`TS2322`) |
| M-02 `include` sin `e2e/` | contrato (Vitest) | muere: «51 ficheros que el proyecto no recorre» |
| M-03 `include` a un directorio vacío | contrato | muere: configuración con errores (`No inputs were found`) |
| M-04 sin `types: ["node"]` | typecheck | muere (`TS2591 Cannot find name 'process'`) |
| M-05 quitar los tipos de Playwright | — | **no aplica**: llegan por `import` de `@playwright/test`, no por configuración; «quitarlos» sería desinstalar el paquete |
| M-06 el ayudante `activarEmpresa` cambia su contrato | typecheck | muere (`TS2345` en `empresa-helper.spec.ts`) |
| M-07 campo obligatorio nuevo en `MundoN6` | typecheck | **equivalente** (la fixture se construye con `as Partial<MundoN6>` y nadie lee el campo): declarado y sustituido |
| M-07b `nombre_a` deja de ser texto en la fixture | typecheck | muere (`TS2345` en `empresas-busqueda.spec.ts:50`) |
| M-08 la solución deja de referenciar `tsconfig.e2e.json` | contrato | muere |
| M-09 `noEmit: false` + `outDir: dist` | contrato | muere |
| M-10 `strict: false` en e2e | contrato | muere |
| M-11 `// @ts-ignore` en una suite | contrato | muere |
| M-12 `as any` en una suite | contrato | muere |

11 mutantes significativos, **11 muertos**, 1 equivalente declarado (M-07, sustituido), 1 no aplicable
(M-05, razón dada). Obligatorios del encargo (M-01, M-02/M-03, M-08, M-09, M-10, M-11): todos muertos.

## 10. E2E (`e2e-dirigida-notifications.txt`, `e2e-global-1.txt`, `e2e-global-2.txt`)

La única suite tocada (`notifications.spec.ts`, solo tipos) → dirigida `r20261012t133741p2486125n49e905`:
**7/7**, limpieza LIMPIA. Y como cambió una suite, dos globales canónicas consecutivas, cada una con su base
PostgreSQL nueva:

| Corrida | Id | passed | failed | skipped | Suite | Limpieza |
|---|---|---|---|---|---|---|
| Referencia (cierre de E2E-CUARENTA-OMITIDAS) | `r20261012t053655p2420178n795912` | 272 | 0 | 4 | 201,6 s | LIMPIA |
| Global 1 | `r20261012t133823p2488306n874333` | **272** | **0** | **4** | 230,0 s | LIMPIA |
| Global 2 | `r20261012t134227p2519190n8e265a` | **272** | **0** | **4** | 231,0 s | LIMPIA |

Las 4 omitidas son, en ambas, las cuatro de `ENTORNO-SIN-CLAMSCAN`, con su nombre (ETS-20). Sin corridas
adicionales ni reintentos. Bases de corrida residuales: **0**.

## 11. `/speckit.analyze` final

`E2E_TYPESCRIPT_UNCHECKED 0 · E2E_GATE_NOT_INVOKED 0 (lo invoca npm run typecheck y el build) ·
E2E_TS_FILE_UNCOVERED 0 (53/53) · PRODUCT_STRICTNESS_RELAXED 0 · NEW_TS_IGNORE 0 · NEW_TS_EXPECT_ERROR 0 ·
NEW_ANY_BYPASS 0 · PRODUCT_DIST_E2E_ARTIFACT 0 · E2E_SEMANTIC_CHANGE_FOR_TYPECHECK 0 · ASSERTION_WEAKENING 0 ·
PLAYWRIGHT_CONFIG_UNCHECKED 0 · GLOBAL_SETUP_UNCHECKED 0 · E2E_HELPER_UNCHECKED 0 · E2E_FIXTURE_UNCHECKED 0 ·
CLAMSCAN_SKIP_REGRESSION 0 · OPENAPI_REGRESSION 0 · ROLE_CREATE_REGRESSION 0 (`roles-alta.spec.ts` pasa) ·
LICENSING_REGRESSION 0 (los cuatro proyectos de licencia pasan) · KEEPALIVE_75_REGRESSION 0 ·
VERSION_PANEL_REGRESSION 0 · CLIENT_SCHEMA_CHANGE 0 · CENTRAL_SCHEMA_CHANGE 0 ·
PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 · NEXT_MASTER_SPEC_SELECTED 0 · SECRET_EXPOSURE 0 ·
BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 ·
MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.` `checkJs`/`allowJs`: no habilitados; los dos `.mjs`
quedan fuera con razón (§5.12).

## 12. Trazabilidad

FR-E2ETS-001/009/010 → T01 → `tsconfig.e2e.json` → ETS-02/03/09–13 → M-04/M-06/M-07b/M-09/M-10 →
`frontend-gates.txt`, `ficheros-recorridos.txt`, `mutaciones.txt`. FR-002/011/012 → T02 → `tsconfig.json`
→ ETS-01/04 → M-01/M-08. FR-007/008 → T03 → `notifications.spec.ts` → ETS-18 (dirigida 7/7). FR-003/004/
005/006 → T04 → `typecheck-gate.test.ts` → ETS-05/07/08/15 → M-02/M-03/M-09–M-12. FR-011 → T05 → CLAUDE.md.
FR-013 → `dist` idéntico. FR-014/015 → T06 → dos globales. FR-016/017 → el gate es `tsc`, no Playwright.
FR-018–024 → analyze final. Cada error de línea base: error → clasificación → dueña (047/001) → T03 → 0
errores. Cobertura 100 %.

## 13. Convergencia

**`E2E-SIN-TYPECHECK — CLOSED / CONVERGED`.** `e2e/` y `playwright.config.ts` son el tercer proyecto de
la solución, con el mismo rigor que `src`, sin emitir, recorridos por el gate canónico y por el build;
cobertura 53/53 vigilada por una prueba que resuelve los ficheros como `tsc`; un defecto de tipos real
corregido sin tocar semántica; producto 0; `dist` idéntico; 11/11 mutantes muertos; Vitest 473/473; E2E
272/0/4 ×2; bases 0. Orquestación: 7 tareas, 7 `CLAUDE_ONLY`, 0 `DEEPSEEK_ELIGIBLE`, 0 llamadas, coste 0.
Hoja de ruta, `next-spec-decision.md` y recuento MASTER57 (57, sin cambio) actualizados; SPEC057 y NEXT
MASTER SPEC sin cambio; producción fuera de ciclo.
