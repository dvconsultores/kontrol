# SPEC 054 · Delta dirigida — E2E-PANTALLA-SIN-PINTAR

**Fecha** 2026-10-12/13 · **Dueña** SPEC054 (QA / E2E; `specs/012-auditoria-integral-e2e`) · **Apoyo** SPEC001
(arranque del frontend), SPEC005 (navegación), SPEC052 (runner y entorno de QA) · **Base** `aed0d95` ·
**Rama** `develop` · **Evidencia** `evidence/e2e-pantalla-sin-pintar/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `aed0d95` / `aed0d95` / `aed0d95` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_AED0D95` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| Entorno al empezar (solo banderas) | 12 CPU · 15 GB (≈6 GB libres) · carga 0,9 · **VPN presente: sí** (dos interfaces de túnel) · reloj de pared y monotónico anotados por `entorno.sh` |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Descubrimiento (`grafo-de-arranque.txt`)

**Playwright canónico (sin cambio):** `TIMEOUT` 30 s (defecto) · `EXPECT_TIMEOUT` 5 s (defecto) ·
`ACTION_TIMEOUT`/`NAVIGATION_TIMEOUT` sin fijar · `RETRIES` 0 fuera de CI · `WORKERS` por defecto (12 CPU →
6) · `TRACE` `on-first-retry` (con `retries` 0 **nunca** captura el primer fallo) · `SCREENSHOT`/`VIDEO` off ·
`WEB_SERVER` ninguno · `BASE_URL` `http://localhost:5173` · `fullyParallel`.

**Runner (`qa/e2e_corrida.py`):** backend `uvicorn 127.0.0.1:8000` (keep-alive 75), Central 8010, Vite
`vite.js --host localhost --port 5173 --strictPort`; «frontend listo» = `GET /` responde (60 s, monotónico);
sin `workers` fijados; manifiesto con `inicio`/`fin` en reloj de pared y `segundos` de la suite en
monotónico; señales → limpieza; `KONTROL_E2E_*` exportadas. No captura `requestfailed`/`pageerror` ni estado
de red.

**Arranque del frontend:** `index.html` → `<script type=module src=/src/main.tsx>` → providers
(`QueryClient`, `Notification`, `Auth`, `License`, `Company`) → `RouterProvider` → `/login` es `lazy()` y
**está fuera de `RouteGuard`** → `LoginPage` pinta el formulario **incondicionalmente** (`Navigate` solo si
ya hay sesión). `AuthProvider` lanza `POST /auth/refresh` y `LicenseProvider` `GET /license/status`, y
`LoginPage` `GET /setup/status`, pero **ninguna condiciona el render del formulario** (los providers
renderizan `children` siempre; `isReady` solo lo espera `RouteGuard`, que no cubre `/login`).

| Petición antes del formulario | Bloquea el render | Si falla |
|---|---|---|
| `POST /auth/refresh` | no | anónimo, `isReady` true |
| `GET /license/status` | no | `status null` |
| `GET /setup/status` | no | catch silencioso |
| **módulos de Vite** (`/src/main.tsx`, `index.css`, `/@vite/client`, `.vite/deps/*`, chunk lazy de `LoginPage`) | **sí** | abortados → `#root` vacío o router sin componente, **sin reintento** |

Conclusión: `BLOCKING_PRELOGIN_REQUEST` queda descartada por construcción. Lo único que deja «Empresa
(código)» sin pintar es que un módulo de Vite no llegue: `NETWORK_CHANGE_IN_FLIGHT`, `MODULE_FETCH_ABORTED`
o `VITE_UNRESPONSIVE_UNDER_LOAD`. Inicios de sesión por interfaz: 36 ficheros, 39 sitios (`page.goto("/login")`
+ tres `fill` + clic): mucha carga de arranque repetida, pero no es la pregunta de este ciclo.

## 3. Evidencia histórica (`evidencia-historica.txt`)

| Fecha | Prueba | Traza | Estado de página | Lo que se sabe |
|---|---|---|---|---|
| 2026-10-01 | `empresas-busqueda.spec.ts:58` | no | desconocido | sin captura (retries 0) |
| 2026-10-06 | `sales-orders.spec.ts:167` (`r20261006t045634…`) | **sí** (`trace.zip`) | **I: módulos abortados** | la red `1-trace.network` registra **6 peticiones con `net::ERR_NETWORK_CHANGED`**: `/src/index.css`, `/src/components/NotificationViewport.tsx`, `/node_modules/vite/dist/client/env.mjs` y tres `.vite/deps/chunk-*.js`; React nunca montó. Reloj +5 h 08 min en la misma corrida; tokens caducados en `returns.spec.ts` |
| 2026-10-06 | `smoke.spec.ts:7` (`r20261006t115327…`) | no | desconocido | encabezado no visible en los 5 s de esa prueba; hermana en verde |
| 2026-10-12 | `pick-execution:297`, `picking:192` / `dispatch:342`, `documents-a11y:64` | no | **desconocido** (`error-context.md` sin instantánea) | backend 0 errores; Vite solo el banner; reloj estable; VPN presente; las 4 suites 27/27 dirigidas |

`NETWORK_CHANGE_IN_FLIGHT` está **PROVEN** para el 2026-10-06. Para el 2026-10-12 la causa primaria no
puede afirmarse sin captura: la configuración canónica no deja traza ni instantánea del primer fallo. De
ahí las dos mediciones (§4).

## 4. Mediciones (sin tocar el repositorio)

Configuración de medición **fuera del árbol** (`scratchpad/playwright.medicion.config.ts`): extiende la
canónica intacta y solo añade `trace: retain-on-failure` y `screenshot: only-on-failure`; `timeout`,
`retries`, `workers` y aserciones iguales. Instantánea de entorno antes y después de cada corrida
(`entorno.sh`: reloj de pared, monotónico, carga, lista de interfaces por nombre y estado, bandera VPN y
huella SHA-256 truncada de las direcciones; **sin** direcciones ni extremos).

- **Medición A**: global canónica + traza/captura al fallar.
- **Medición B**: la misma con `--workers=1`, solo para comparar la frecuencia con y sin concurrencia.

## 5. Resultado de las mediciones (`medicion-A.txt`, `medicion-B.txt`, `reproduccion-acotada.txt`)

| Corrida | Qué | passed | failed | skipped | Suite | Huella de red antes/después | Reloj pared/monotónico |
|---|---|---|---|---|---|---|---|
| A `r20261012t231055…` | global canónica + traza/captura | **273** | **0** | 4 | 3,9 min | `bac7befbbed5` = `bac7befbbed5` | 245 s / 244 s |
| B `r20261012t231459…` | ídem con `--workers=1` | **273** | **0** | 4 | 8,3 min | iguales | 511 s / 511,5 s |
| Acotada 1–3 `r20261012t232413…`, `…232458…`, `…232543…` | 8 suites históricas (60 pruebas, 22 inicios por interfaz) ×3, workers canónicos | 60 / 60 / 60 | 0 / 0 / 0 | 1 | 45 s c/u | iguales | coherentes |

Entorno durante toda la medición: VPN presente (dos interfaces de túnel), huella de direcciones
inalterada, reloj coherente (desvío < 1 s), carga de 0,9 a 10,6 (la reproducción acotada se encadenó
sin pausa a propósito). **Unas 730 ejecuciones de prueba con traza retenida y 0 fallos.** Las 4 omitidas
son siempre las de `ENTORNO-SIN-CLAMSCAN`.

`CAUSE_PROVEN` para los fallos del 2026-10-12: **NO** — no hubo fallo que capturar. El síntoma depende
de algo que hoy no estaba ocurriendo; lo único que diferencia las dos globales afectadas de ayer de
las once limpias de hoy es lo que no se registró entonces: con `retries 0` y `trace on-first-retry`,
la configuración canónica no deja traza, captura ni instantánea del **primer** fallo.

**Clasificación de los fallos históricos:** 2026-10-06 `sales-orders` → `NETWORK_CHANGE_IN_FLIGHT`
(**PROVEN** por la traza: 6 módulos abortados con `ERR_NETWORK_CHANGED`, más salto de reloj) ·
2026-10-01, 2026-10-06 `smoke` y los cuatro del 2026-10-12 → `UNKNOWN` por falta de captura (no por
falta de investigación): el grafo descarta `BLOCKING_PRELOGIN_REQUEST` y `PRODUCT_BOOT_DEFECT` como
causa de «formulario sin pintar» (ninguna petición condiciona el formulario; los providers y `/login`
no esperan a nada), y backend, Vite (banner limpio, proceso vivo) y reloj estaban sanos.

## 6. Decisión: `NOT REPRODUCED`, con captura diagnóstica no material

Veredicto del ciclo: **`E2E-PANTALLA-SIN-PINTAR — NOT REPRODUCED`**. La deuda sigue **OPEN**. Producto:
**0** cambios (no hay defecto demostrado; `/license/status`, `/auth/refresh`, sesión y licencia intactos).
No se tocan tiempos, reintentos, trabajadores, esperas, recargas ni omisiones; no se toca la red ni el
reloj del equipo; no se reescriben los 39 inicios por interfaz.

Lo que sí se implementa, porque está **justificado por la propia medición** y es puramente diagnóstico
(no cambia qué pasa ni qué falla; solo qué queda cuando algo falla):

1. **`playwright.config.ts`:** `trace: "retain-on-failure"` y `screenshot: "only-on-failure"`. En verde se
   descarta todo (coste medido: 3,9 min frente a 3,7–3,8); al fallar queda la traza con la red, la consola
   y los errores de página, y la captura de pantalla con el estado real (vacío, cargando, formulario). Es
   lo que convirtió el 2026-10-06 en un caso explicado y lo que faltó el 2026-10-12.
2. **`qa/e2e_corrida.py`:** `resumir_red` (nombres y estado de interfaces, bandera de túnel y huella
   SHA-256 truncada de las direcciones: **nunca** direcciones ni extremos), `huella_de_red` (sobre `ip -br`;
   si no está, `disponible: false`), `desvio_de_reloj` (pared frente a monotónico; salto si > 5 s) y
   `anotar_entorno`: el manifiesto gana `entorno = {red_inicio, red_fin, red_cambio, reloj}` y la salida
   una línea «entorno: …» que **avisa y no aborta**. Si el arnés debe abortar o invalidar una corrida con
   red cambiada o reloj saltado es política del arnés: se presenta a la dueña (§10), no se decide aquí.
3. **Pruebas:** `test_e2ecorrida_15…18` (resumen sin direcciones, huella sensible al cambio y estable sin
   él, detector de salto con el caso real del 2026-10-06 y el ruido, y una corrida real que anota el
   entorno y lo dice) y `src/tests/e2e-harness-contract.test.ts` (tiempo/reintentos/trabajadores
   canónicos, traza y captura al fallar, inventario de omisiones y de esperas fijas de `e2e/` declarado).

## 7. `/speckit.specify` · `/speckit.clarify` · compuerta

FR-PSP-001 causa clasificada por fallo capturado (histórico: 1 PROVEN, 6 UNKNOWN por falta de captura;
en este ciclo: 0 fallos) · 002 el arnés captura lo suficiente para distinguir frontend/backend/entorno
(traza + captura + entorno en el manifiesto) · 003 condiciones de entorno en el manifiesto sin datos
sensibles · 004/005 red y reloj del equipo intactos · 006–010 sin tiempo, reintentos, esperas, recargas ni
omisiones nuevas (contrato vigilado) · 011/012 producto 0 · 013 detector determinista y probado · 014 el
manifiesto distingue fallo de producto de entorno inválido (`red_cambio`, `reloj.salto`) · 015–017 auth,
OpenAPI, roles, licencia, sync, tasa, reverificación, versión, 409 de picking, keep-alive y typecheck de
e2e sin cambio · 018–020 dos globales canónicas limpias, base nueva, residuales 0 · 021–023 MASTER57, 057,
puntero.

Clarify 1–29: historial (§3), configuración y runner (§2), arranque y peticiones (§2), `uiLogin` (36
ficheros), estado de página en los fallos (desconocido salvo 2026-10-06), módulos (abortados el
2026-10-06), backend/Vite/red/VPN/reloj/carga (§1, §5), medición A y B (§5), clasificación (§5),
producto/arnés/externo (externo probado el 2026-10-06; no reproducido hoy), política avisar/abortar
(pendiente de la dueña; aquí solo se avisa), pruebas (§6), mutaciones (§8), E2E (§9), DeepSeek 0.
`MATERIAL OQ = 0` para lo implementado (captura no material); la política de abortar queda fuera, nombrada.

Compuerta: G01–G13 ✔ · **G14 (un fallo capturado en este ciclo): NO** → no se implementa solución alguna
sobre el síntoma; solo captura diagnóstica, autorizada por la ruta NOT REPRODUCED del encargo · G15–G18 no
aplican a una solución (no la hay); para la captura: dueña 054/052, externo/arnés, política no requerida
(se avisa, no se aborta) · G19–G22 ✔ (0 tiempo, 0 reintentos, 0 esperas, 0 omisiones) · G23–G24 ✔ ·
G25–G28 ✔.

| Tarea | Requisito | Dueña | EXECUTOR | EGRESS | Ficheros | Acción | DONE_WHEN | Prueba | Mutación |
|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001/002 | 054 | CLAUDE | n-a | evidencia | mapa histórico, grafo, mediciones A/B, acotada ×3 | ficheros | — | — |
| T02 | FR-002/006/007 | 054 | CLAUDE | n-a | `playwright.config.ts` | traza y captura al fallar | contrato 4/4 | `e2e-harness-contract.test.ts` | M-06, M-08, M-09, M-10, M-11 |
| T03 | FR-003/004/005/013/014 | 052/054 | CLAUDE | n-a | `qa/e2e_corrida.py` | `resumir_red`, `huella_de_red`, `desvio_de_reloj`, `anotar_entorno` | runner 18/18 | `test_e2ecorrida_15…18` | M-01…M-05, M-07 |
| T04 | FR-018–023 | 054 | CLAUDE | n-a | hoja de ruta, puntero, recuento | deuda OPEN con lo medido; puntero; 57 | ficheros | — | — |

`CLAUDE_ONLY 4 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0`.

## 8. Pruebas y mutaciones (`runner-tests.txt`, `frontend-gates.txt`, `mutaciones.txt`)

| Gate | Resultado |
|---|---|
| `tests/test_e2e_corrida.py` (PostgreSQL) | **18/18** (14 previas + `15` resumen sin direcciones, `16` huella sensible y estable, `17` salto de reloj con el caso real y el ruido, `18` una corrida anota el entorno y lo dice) |
| `ruff` runner y pruebas | limpio |
| Frontend: typecheck (src + herramientas + e2e) · lint · Vitest · build | ✔ · ✔ · **477/477** (473 + 4 del contrato del arnés) · ✔; producto frontend 0 |

| Mutante | Gate que lo mata | Resultado |
|---|---|---|
| M-01 el runner deja de anotar el entorno | `test_e2ecorrida_18` | muere |
| M-02 huella de red constante | `16` | muere |
| M-03 la red «siempre cambió» | `18` | muere |
| M-04 el salto de reloj nunca se detecta | `17` | muere |
| M-05 salto de reloj falso (umbral 0) | `17`, `18` | muere |
| M-06 traza de vuelta a «primer reintento» | contrato del arnés | muere |
| M-07 el manifiesto guarda las direcciones | `15`, `18` | muere |
| M-08 se amplía el tiempo global | contrato | muere |
| M-09 reintentos fuera de CI | contrato | muere |
| M-10 una omisión nueva | contrato (inventario) | muere |
| M-11 `workers: 1` como «solución» | contrato | muere |

11 mutantes, **11 muertos**, 0 equivalentes. M-12 (comportamiento de licencia/auth) no aplica: no hay
cambio de producto.

## 9. Certificación E2E canónica (`e2e-global-1.txt`, `e2e-global-2.txt`)

| Corrida | Id | passed | failed | skipped | Suite | Manifiesto `entorno` | Limpieza |
|---|---|---|---|---|---|---|---|
| Global 1 | `r20261012t233603p3151593n13d9af` | **273** | **0** | **4** | 236,2 s | `red_cambio: false` · `reloj: {desvio_s: 0.0, salto: false}` · túnel presente · sin direcciones | LIMPIA |
| Global 2 | `r20261012t234010p3177890n3a84d9` | **273** | **0** | **4** | 237,8 s | ídem | LIMPIA |

Configuración canónica (sin traza forzada, sin `workers`, sin reintentos); la salida dice
«entorno: túnel (VPN) presente» y nada más, porque nada más pasó. Las 4 omitidas son las de
`ENTORNO-SIN-CLAMSCAN`. Bases residuales: **0**. Corridas adicionales: ninguna. Coste de retener la traza
solo al fallar: 236–238 s frente a 226–231 s de ayer (+3 %), en verde no queda ningún fichero.

## 10. `/speckit.analyze` final, trazabilidad y lo que queda para la dueña

`FAILURE_CAUSE_UNKNOWN`: 0 en este ciclo (0 fallos); histórico: 6 sin captura, declarados como tales, 1
PROVEN · `TIMEOUT_INFLATION 0 · RETRY_INFLATION 0 · SLEEP_WORKAROUND 0 · RELOAD_WORKAROUND 0 ·
WORKERS_ONE_AS_SOLUTION 0 (solo medición) · NEW_SKIP 0 · HOST_NETWORK_MODIFIED 0 · HOST_CLOCK_MODIFIED 0 ·
RAW_NETWORK_DATA_EXPOSED 0 (manifiesto y evidencia escaneados; solo nombres de interfaz, banderas y
huellas) · PRODUCT_CHANGE_WITHOUT_PROOF 0 (producto 0) · MASS_E2E_LOGIN_REWRITE 0 · AUTH/LICENSE/OPENAPI/
ROLE_CREATE/PICKLIST_409/E2E_TYPECHECK/CLAMSCAN_SKIP/KEEPALIVE_75/VERSION_PANEL_REGRESSION 0 ·
CLIENT/CENTRAL_SCHEMA_CHANGE 0 · PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 ·
NEXT_MASTER_SPEC_SELECTED 0 · SECRET_EXPOSURE 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER
CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 (para lo implementado) · UNKNOWN 0 ·
TRACEABILITY 100 %.`

Trazabilidad: síntoma → fallos históricos (§3) → traza 2026-10-06 (`ERR_NETWORK_CHANGED` ×6) → grafo de
arranque (§2) → mediciones A, B y acotada ×3 (§5, 0 fallos) → causa: externa probada el 2026-10-06, no
reproducida hoy → dueña 054 (arnés) / 052 (runner) → FR-PSP-001…023 → T01–T04 → `playwright.config.ts`,
`qa/e2e_corrida.py`, pruebas → M-01…M-11 → globales ×2 → NOT REPRODUCED.

**Decisión pendiente de la dueña (política del arnés, no bloquea esta captura):** qué hacer cuando el
manifiesto registre `red_cambio: true` o `reloj.salto: true`:
- **A · avisar** (lo implementado): la corrida sigue, el fallo se clasifica a mano con la traza y el
  manifiesto. Pros: nada se oculta, ninguna corrida se pierde por un aviso. Contras: la clasificación sigue
  siendo manual.
- **B · abortar antes de la suite** si hay túnel o la huella cambió durante la preparación. Pros: no se
  gasta una corrida que no podrá certificar. Contras: con la VPN siempre presente en este equipo no habría
  corridas; la presencia de túnel no demostró ser causa (hoy ≈1 300 ejecuciones limpias con túnel).
- **C · invalidar la corrida** (código de salida propio, «entorno inválido») si la red cambió o el reloj
  saltó *durante* la suite, sin contar sus fallos como de producto. Pros: separa automáticamente lo que
  hoy se separa a mano; no castiga la mera presencia de la VPN. Contras: una corrida entera se repite por
  un cambio puntual. **Recomendación: C**, con la condición medida (cambio en vuelo), no con la presencia.

## 11. Veredicto

**`E2E-PANTALLA-SIN-PINTAR — NOT REPRODUCED`.** La deuda sigue OPEN. Sin causa nueva no hay solución, y
no se cambió nada «por si acaso»: producto 0, tiempos/reintentos/trabajadores/esperas/omisiones 0, red y
reloj del equipo intactos. Lo que entra es captura: la próxima vez que el formulario no se pinte quedará
la traza con la red y la consola, la captura con el estado real de la página y el manifiesto con si la
red cambió o el reloj saltó. Orquestación: 4 tareas `CLAUDE_ONLY`, 0 DeepSeek. Hoja de ruta (OPEN, con lo
medido), `next-spec-decision.md` y recuento MASTER57 (57) actualizados.
