# SPEC 054 · Delta dirigida — E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO

**Fecha** 2026-10-13 · **Dueña** SPEC054 (`e2e/helpers/empresa.ts`, `e2e/empresa-helper.spec.ts`,
`src/tests/e2e-harness-contract.test.ts`) · **Apoyo** SPEC001 (`EmpresasPage`, `LoadingState`, `EstadoDeEmpresa`: solo para
entenderlos; no cambian), SPEC045 (`approvals.spec.ts` tiene una copia local del algoritmo) · **Antecedente**
`spec054-company-helper-delta.md` (E2E-HELPER-EMPRESA-AMBIGUO: los localizadores exactos y la postcondición, que no se
tocan) y `spec054-e2e-pantalla-sin-pintar-delta.md` (la familia general, que sigue OPEN) · **Base** `0f4a5c3` · **Rama**
`develop` · **Evidencia** `evidence/e2e-helper-empresa-carrera-de-pintado/`

Ciclo de arnés E2E: traza primero, reproducción determinista, producto 0; sin `waitForTimeout`, sin reintentos, sin
subir tiempos, sin relajar aserciones.

## 1. Checkpoint
`0f4a5c3` = HEAD = origin/develop · `develop` · limpio · 0 bases · 0 schemas · 0 dirs temporales · puertos libres · MASTER57 /
SPEC057 / NEXT MASTER SPEC sin tocar (`checkpoint.md`).

## 2. Solicitud
El ayudante decidía el estado de empresa con `count()` instantáneos tras `networkidle`, que no garantiza que React haya
pintado la tabla. Cambio: esperar, con la auto-repetición de Playwright, a que la pantalla muestre uno y solo uno de sus
estados válidos, y decidir con esa misma lectura. Producto 0 · tiempos sin cambio · reintentos 0 · esperas fijas 0.

## 3. Descubrimiento (`/speckit.clarify` · research)

| Registro | Valor | Evidencia |
|---|---|---|
| Llamadas al ayudante | canónico (7 llamadas en 5 suites) + copia local en `approvals.spec.ts` (3) + 2 copias reducidas en documentos (pulsan «Activar» si lo ven; no deciden por estado) · `UNKNOWN_CALLERS 0` | `caller-inventory.md` |
| Línea de tiempo de las 3 trazas | `networkidle` resuelto (2626 ms) **antes** de que la página emitiera la petición de la tabla (≈ 2830 ms, ≈ 360 ms tras la ruta, bajo carga); `desactivar.count()` 0 a 2895 → 1 a 3034; `RACE_TIMELINE = PROVEN` | `trace-timeline.md` |
| Estados de render del producto | LOADING (`role=status`), ERROR (`role=alert`), EMPTY, ROWS (`role=region` «Resultados: N»), ACTIVE_ROW («Activa» + «Desactivar»), INACTIVE_ROW («Activar»), GATE («Seleccione una empresa» + `elegir-empresa-*`), NO_COMPANIES · `UNKNOWN 0` · sin test-id nuevo | `render-state-model.md` |
| Firmas de estado | ACTIVA = `desactivar 1 ∧ activa 1 ∧ compuerta 0` (una sola semántica) · INACTIVA · COMPUERTA · NO_LISTA (todo 0, transitorio) · AMBIGUO (resto) | `state-signatures.md` |
| Frecuencia histórica | 3 pruebas en 1 corrida de 105; misma firma; sin mezcla con `ERR_NETWORK_CHANGED`/página en blanco | `historical-frequency.md` |
| Reproducción controlada | `page.route` retrasando la RESPUESTA no reproduce (experimentos B/C: el ayudante espera); diferir la EMISIÓN del `fetch` del listado en la página (`emitirLaTablaTarde`, `addInitScript`) sí: HE-02 falla **determinísticamente** contra el ayudante actual con `activar=0 compuerta=0 activa=0 desactivar=0` (`r20261013t183318…`) · `CURRENT_HELPER_RACE_REPRODUCED = YES` | `controlled-reproduction.md` |
| Causa raíz | **`HELPER_INSTANT_COUNT_BEFORE_RENDER`** (con `networkidle` como señal equivocada); descartados `PRODUCT_NEVER_PAINTS`, `NETWORK_MODULE_ABORT`, `AMBIGUOUS_LOCATOR_CONTRACT` · `PRODUCT_CHANGE 0` | `root-cause.md` |
| Diseño de la espera | `expect.poll` sobre `leerEstadoDeEmpresa` hasta `ACTIVA|INACTIVA|COMPUERTA`, devuelve la lectura que satisfizo la espera (sin TOCTOU); valor recibido = diagnóstico; `ESPERA_DEL_AYUDANTE_MS = 15000` (el de siempre); `networkidle` retirado; expect timeout 5 000 ms (defecto, sin cambio) | `wait-design.md` |
| Approvals | `LOCAL_SHARED_PRIMITIVE`: conserva su compuerta por código y comparte `esperarEstadoDeEmpresa` | `approvals-strategy.md` |

## 4. `/speckit.specify`
FR-HE-001…028 del encargo, tal cual: sin fotografía instantánea; espera a un estado válido único; INACTIVO/ACTIVO/COMPUERTA
identificables por controles exactos; transición sin estado no es error hasta el tiempo; ambigüedad real sigue fallando;
diagnóstico preservado o mejorado; localizadores exactos; postcondición de una sola activa; idempotencia; sin
`waitForTimeout`/sleep/retry/timeout mayor/reload; `networkidle` no es autoridad; approvals con la misma semántica;
producto 0; contratos previos intactos; E2E-PANTALLA-SIN-PINTAR OPEN; 4 omisiones ClamAV; dos globales limpias;
MASTER57/057/puntero sin cambio.

## 5. `/speckit.clarify` — resueltas
(1) llamadas: §3 · (2) traza: §3 · (3) señal de pintado: los propios controles exactos (uno y solo uno de los estados) · (4)
frecuencia: 1/105 · (5) reproducción: emisión diferida · (6) espera: `expect.poll` + lectura única · (7) approvals: primitiva
compartida · (8) pruebas: HE-02/05/06/07/08/10 en `empresa-helper.spec.ts`, HE-11 en approvals, HE-12/13/14 estáticas en el
contrato del arnés, HE-03/04/09 = pruebas existentes (idempotente, contrario/compuerta, exact) · (9) mutaciones M-01…M-12 ·
(10) gates: typecheck (con e2e), lint, Vitest, build; backend 0 · (11) dos globales · (12) DeepSeek: 0 (todo es semántica de
estado y diseño de espera).

## 6. `/speckit.plan`
W01–W12 ✔ (checkpoint, artefactos, llamadas, traza, estados, firmas, frecuencia, diseño y ejecución de la reproducción,
causa raíz, diseño de espera, approvals) · W13–W19 pruebas, mutaciones, gates, globales, clasificación, analyze,
trazabilidad · W20 implementación (helper, approvals, pruebas HE, contrato estático) · W21 dirigida por el runner · W22
mutaciones · W23 gates · W24 dos globales · W25–W26 analyze y convergencia.

## 7. CONSTITUTION GATE
G01–G05 ✔ · G06 llamadas ✔ · G07 UNKNOWN 0 ✔ · G08 traza ✔ · G09–G10 estados ✔ · G11 firmas ✔ · G12–G13 reproducción
controlada y ayudante actual reproducido ✔ · G14 causa raíz ✔ · G15 producto 0 ✔ · G16 señal estable ✔ · G17 espera ✔ ·
G18–G20 sin `waitForTimeout`/reintentos/tiempo mayor ✔ · G21 exact ✔ · G22 postcondición ✔ · G23 approvals ✔ · G24–G25
pruebas y mutaciones ✔ · G26 deuda general separada ✔ · G27–G35 BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0
· ORPHAN 0/0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 % → **PASS**. Autorización expresa del encargo: cumplida.

## 8. `/speckit.tasks`

| ID | Requisitos | EXECUTOR | TARGET_FILES | Acción | DONE_WHEN |
|---|---|---|---|---|---|
| T01 | research | CLAUDE_ONLY | evidencia | inventario, traza, estados, firmas, frecuencia, causa raíz, diseño | §3 |
| T02 | FR-HE-001/006, reproducción | CLAUDE_ONLY | `e2e/helpers/empresa.ts` (`emitirLaTablaTarde`), `e2e/empresa-helper.spec.ts` (HE-02) | reproducción determinista | falla contra el ayudante actual (hecho), pasa tras el fix |
| T03 | FR-HE-001…018 | CLAUDE_ONLY | `e2e/helpers/empresa.ts` | `leerEstadoDeEmpresa`, `esperarEstadoDeEmpresa`, `diagnosticoDeEmpresa`, `activarEmpresa` decide con la lectura | HE verdes |
| T04 | FR-HE-019/020 | CLAUDE_ONLY | `e2e/approvals.spec.ts` | primitiva compartida + HE-11 | approvals verde |
| T05 | FR-HE-005…013 | CLAUDE_ONLY | `e2e/empresa-helper.spec.ts`, `src/tests/e2e-harness-contract.test.ts` | HE-05/06/07/08/10 + HE-12/13/14 estáticas | Vitest y runner verdes |
| T06 | FR-HE-021…028 | CLAUDE_ONLY | — | mutaciones, gates, dos globales, converge | §11–§12 |

Todos: `SECURITY_SENSITIVE no` · `EGRESS_SAFE n/a` (DeepSeek 0) · `RETRY_MAX 2`.

## 9. `/speckit.analyze` previo y trazabilidad
Búsqueda: `activarEmpresa`/`controlesDeEmpresa` (helper, approvals, 5 suites) · `estado de empresa no determinable` (helper,
approvals, trazas) · `count()`/`networkidle` (decisión instantánea → se retira de la decisión) · `waitForTimeout`/`setTimeout`/
`sleep`/`retry` (0 en la decisión; `setTimeout` solo en la sonda de arnés) · `toHaveCount`/`expect.poll` (postcondición /
espera nueva) · `exact:` (3) · `LoadingState` (`role=status`, solo diagnóstico) · `organization/companies` (la petición que se
emite tarde) · `page.route` (no reproduce; documentado) · `UNKNOWN` 0. `CURRENT_HELPER_RACE_REPRODUCED YES` · `TRACE_TIMELINE
PROVEN` · `ROOT_CAUSE PROVEN` · `STABLE_STATE_SIGNAL PROVEN` · `STATE_SIGNATURES PROVEN` · `PRODUCT_CHANGE 0` · `WAITFOR_TIMEOUT 0`
· `MANUAL_RETRY 0` · `TIMEOUT_INFLATION 0` · `RELOAD_WORKAROUND 0` · `ASSERTION_WEAKENING 0` · BLOCKER 0 · CRITICAL 0 ·
CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN 0/0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 %.

## 10. `/speckit.implement` — por tarea (todas CLAUDE_ONLY; DeepSeek 0: semántica de estado y diseño de espera)

```
T02 [EXECUTE] Claude · emitirLaTablaTarde (addInitScript: difiere la EMISIÓN del fetch del listado) + HE-02
    [TEST]    contra el ayudante actual: HE-02 FALLA con la firma exacta (r20261013t183318…) → CURRENT_HELPER_RACE_REPRODUCED = YES
T03 [EXECUTE] Claude · e2e/helpers/empresa.ts: EstadoDeEmpresa, LecturaDeEmpresa, ESPERA_DEL_AYUDANTE_MS = 15000,
              leerEstadoDeEmpresa (lectura clasificada), diagnosticoDeEmpresa, esperarEstadoDeEmpresa (expect.poll hasta
              ACTIVA|INACTIVA|COMPUERTA; devuelve esa lectura), activarEmpresa decide con la lectura; networkidle retirado;
              exact, compuerta por código, cambio de empresa, diagnóstico y postcondición intactos
    [AUDIT]   PASS: sin waitForTimeout/sleep/retry/reload; timeout 15000 (el de siempre); producto 0
T04 [EXECUTE] Claude · e2e/approvals.spec.ts: la función local decide con esperarEstadoDeEmpresa (LOCAL_SHARED_PRIMITIVE),
              conserva su compuerta por código, su exact y su postcondición; HE-11 nueva
T05 [EXECUTE] Claude · empresa-helper.spec.ts: HE-05/06/07/08/10 (DOM impostor solo en la prueba; emisión diferida; nunca
              emitida); src/tests/e2e-harness-contract.test.ts: invariantes estáticos (HE-12/13/14, exact, postcondición,
              sin relectura TOCTOU)
    [TEST]    runner dirigido r20261013t183855…: 13/13 · Vitest contrato 5/5 · tsc -b --noEmit OK · eslint OK
[STATUS]  T02–T05 COMPLETE · T06 en §11–§12
```

## 11. Resultados

| Certificación | Resultado | Evidencia |
|---|---|---|
| HE-01 (ayudante antiguo, emisión diferida) | falla determinista con la firma exacta (`r20261013t183318…`) | `controlled-reproduction.md` |
| HE-02…11 (runner canónico, base nueva) | **13/13** (`r20261013t183855…`; RESTORED `r20261013t184637…`) | `harness-tests.md` |
| HE-12/13/14 (contrato estático, Vitest) | 5/5 | `harness-tests.md` |
| Mutaciones | **12/12 muertas** (7 por el runner, 5 por Vitest); ninguna equivalente | `mutation-campaign.md` |
| Gates | typecheck (con e2e) ✔ · lint ✔ · Vitest **482/482** (481 + 1) · build ✔ · producto 0 | `frontend-static-gates.md` |
| Backend | 0 cambios (suites completas no requeridas: solo cambia arnés E2E) | — |
| E2E global 1 | `r20261013t184825…` **280 / 0 / 4** (273 + 7 nuevas), 4.3 min, backend 0 errores, red estable, sin salto de reloj | `global-e2e-1.md` |
| E2E global 2 | `r20261013t191155…` **280 / 0 / 4**, 4.7 min, ídem | `global-e2e-2.md` |
| Residuales | bases 0 · schemas 0 · dirs temporales 0 · puertos libres | — |
| HE-15 / HE-16 | producto 0 · E2E-PANTALLA-SIN-PINTAR sigue OPEN | roadmap |

## 12. `/speckit.analyze` final, trazabilidad y veredicto

Búsqueda sobre el árbol final: `instant count` / `count() before render` → la decisión usa la lectura de `esperarEstadoDeEmpresa`
(M-02 muerto) · `networkidle only` → retirado de las dos funciones (M-12 muerto) · `waitForTimeout` / `sleep` / `retry` /
`timeout increase` / `reload` → 0 (M-07, M-08 muertos; inventario sin cambio) · `fuzzy locator` / `Activar substring` → exact ×3
(M-05 muerto) · `postcondition removed` → presente (M-06 muerto) · `fresh unsafe reread` / `TOCTOU` → la espera devuelve su
lectura (M-10 muerto) · `product diff` → 0 · `approvals divergent logic` → primitiva compartida (M-09 muerto) · `new skip` /
`assertion weakening` → 0 · `E2E-PANTALLA closed globally` → no · auth/OpenAPI/licensing/sync/picklist/listados/typecheck/
captura/keep-alive/version → sin tocar · SPEC057 / NEXT MASTER → sin cambio · UNKNOWN 0.

`HELPER_INSTANT_DECISION_RACE 0` · `NOT_READY_TREATED_AS_FAILURE 0` · `STATE_SIGNATURE_AMBIGUITY 0` ·
`ACTIVE_STATE_FALSE_AMBIGUITY 0` · `FUZZY_ACTIVAR_MATCH 0` · `POSTCONDITION_WEAKENED 0` · `TOCTOU_REREAD 0` · `WAITFOR_TIMEOUT 0`
· `SLEEP_WORKAROUND 0` · `RETRY_WORKAROUND 0` · `TIMEOUT_INFLATION 0` · `RELOAD_WORKAROUND 0` · `ASSERTION_WEAKENING 0` · `NEW_SKIP
0` · `PRODUCT_CHANGE 0` · `APPROVALS_DIVERGENT_RACE 0` · `AUTH_REGRESSION 0` · `OPENAPI_REGRESSION 0` · `LICENSING_REGRESSION 0` ·
`CENTRAL_SYNC_REGRESSION 0` · `PICKLIST_409_REGRESSION 0` · `LISTADOS_REGRESSION 0` · `BACKEND_HARNESS_REGRESSION 0` ·
`INSTALLATION_VOLUME_REGRESSION 0` · `PG_SCHEMA_OPTIMIZATION_REGRESSION 0` · `E2E_TYPECHECK_REGRESSION 0` ·
`E2E_CAPTURE_REGRESSION 0` · `CLAMSCAN_SKIP_REGRESSION 0` · `KEEPALIVE_75_REGRESSION 0` · `VERSION_PANEL_REGRESSION 0` ·
`E2E_PANTALLA_FALSELY_CLOSED 0` · `PRODUCTION_502_SCOPE_EXPANSION 0` · `SPEC057_STARTED 0` · `NEXT_MASTER_SPEC_SELECTED 0` ·
`SECRET_EXPOSURE 0` · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 ·
MATERIAL OQ 0 · UNKNOWN 0 · **TRAZABILIDAD 100 %** (`traceability-matrix.md`).

Observaciones anotadas, no absorbidas: `documents.spec.ts` y `documents-a11y.spec.ts` activan la empresa con una copia
reducida («si veo Activar, pulso») que no decide por estado; no comparten la primitiva (candidata para la dueña 054).

Orquestación: tareas 6 · `CLAUDE_ONLY` 6 · `DEEPSEEK_ELIGIBLE` 0 (semántica de estado y diseño de espera: todo es juicio) ·
DeepSeek 0 llamadas · implementadas por Claude 6 · pruebas nuevas 7 Playwright + 1 Vitest · mutaciones 12/12 · regresiones 0.

**Veredicto: `E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO — CLOSED / CONVERGED`.** Commit y push a `origin/develop` al cierre.
