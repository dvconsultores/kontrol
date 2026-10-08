# SPEC 054 · DELTA DIRIGIDO — EL KEEP-ALIVE DE 5 SEGUNDOS DEL SERVIDOR HTTP

> Iniciado el 2026-10-08. Dueño: **Spec 054 — QA integral** (`012-auditoria-integral-e2e`), donde la
> deuda nació y donde vive su evidencia; apoyo **052** (imagen y arranque del backend: `Dockerfile.backend`,
> `Dockerfile.central`) y **001** (el health, que no cambia). Deuda: `BACKEND-KEEPALIVE-5S`. MASTER57,
> 057, D0-07, 039–043 y 056 no se tocan. No se reabre nada cerrado.
>
> **Objetivo:** localizar físicamente el mecanismo de «5 segundos», probar su propósito y sus
> consumidores, y eliminarlo, sustituirlo o formalizarlo solo según la evidencia; sin cambiar sesión,
> licencia, sync, límite de tasa, health ni el frontend si no son parte del problema.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `37084cf` / **`37084cf`** / `37084cf` / `develop` / limpio · `COMMITS_AFTER_37084CF = 0` · `RUN_DATABASES = 0` · puertos 8000/8010/5173 libres |
| Entorno | el PostgreSQL de QA no estaba levantado tras un reinicio (`/tmp/kontrol-pgdata-045` ausente): `bash qa/pg-provision.sh start` + `ktest` recreada; reloj del equipo coherente con el último commit |
| Dueñas | 054 primaria (origen y evidencia de la deuda, runner E2E); 052 apoyo (arranque en imagen); 001 solo porque el health se preserva · `OWNER_IDENTITY_CONFLICT = 0` |
| Punteros | `NEXT TECHNICAL CYCLE = BACKEND-KEEPALIVE-5S` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Descubrimiento (W03–W13) — búsqueda física, sin suposiciones

Búsqueda obligatoria ejecutada sobre `resources/frontend/src`, `resources/backend/app`,
`central_authority`, `resources/nginx`, `compose*.yaml`, `Dockerfile*`, `qa/`, `scripts/` y `docs/`
(`5000`, `5_000`, `seconds=5`, `sleep(5`, `setInterval`, `setTimeout`, `refetchInterval`,
`pollingInterval`, `heartbeat`, `keepalive`, `keep-alive`, `navigator.onLine`, `visibilitychange`,
`/health/live`, `/health/ready`, `timeout-keep-alive`, `keepalive_timeout`, `uvicorn`).

| Hallazgo | Qué es | ¿Es la deuda? |
|---|---|---|
| `Dockerfile.backend` CMD (producción y `dev`), `Dockerfile.central` CMD, `qa/e2e_corrida.py` (backend y autoridad de la corrida), `README.md` (orden de desarrollo) | arrancan `uvicorn` **sin `--timeout-keep-alive`**; uvicorn 0.32.1 tiene `timeout_keep_alive = 5` por defecto (medido en el intérprete) | **SÍ** |
| Agente HTTP global de Node v24 | `keepAlive = true`, `timeout = 5000` ms (medido): el cliente conserva una conexión ociosa **los mismos 5 s** que el servidor; Playwright (`APIRequestContext`) y el proxy de desarrollo de Vite lo usan | el otro extremo de la carrera |
| `resources/nginx/nginx.conf` | `proxy_http_version 1.1` **sin** `upstream`/`keepalive` ni `Connection ""`: nginx cierra la conexión con el backend tras cada petición; `proxy_read_timeout 60s` | no reutiliza: la producción detrás de nginx no la sufre hoy; un `upstream keepalive` futuro (60 s por defecto) sí |
| `NotificationBell.tsx` `refetchInterval: INTERVALO_SONDEO_MS` | sondeo de contadores de notificaciones, **60 s**, Spec 047, `enabled` solo con empresa activa | no: no es de 5 s ni es keep-alive; se registra y no se toca |
| `DashboardPage.tsx` `useQuery(["health"] → /health/ready)` | una lectura al montar (sin `refetchInterval`, `retry: false`); Spec 049 | no: no es periódica |
| frontend | **ningún** `setInterval`, ningún otro `refetchInterval`, ningún `heartbeat`/`keepalive`/`navigator.onLine`/`visibilitychange` | no existe un latido |
| backend / central | ningún `sleep(5`, `seconds=5`, `heartbeat`, `keepalive` de aplicación | no existe un temporizador |
| `evidence/e2e-flaky/keepalive.txt` (2026-10-01) | reproducción original: con uvicorn por defecto, 12/40 `ECONNRESET` a 4990–4999 ms de ocio y 40/40 caducadas a 5000–5019 ms; con `--timeout-keep-alive 60`, 0/160 | la deuda, ya medida al nacer |

### Inventario del mecanismo

| Registro | Valor |
|---|---|
| `FILE` / `SYMBOL` | `Dockerfile.backend:CMD` (×2), `Dockerfile.central:CMD`, `qa/e2e_corrida.py:arrancar_backend`/`arrancar_autoridad`, `README.md` · símbolo: `uvicorn --timeout-keep-alive` ausente → `Config.timeout_keep_alive = 5` |
| `CALLER` / `CALLEE` | el servidor HTTP (h11 en uvicorn) cierra la conexión TCP ociosa; nadie «llama»: es un temporizador del protocolo, no de la aplicación |
| `INTERVAL` | 5 s de ocio **por conexión**, no periódico |
| `START_TRIGGER` / `STOP_TRIGGER` | se arma al terminar cada respuesta; se desarma con la siguiente petición o al cerrar |
| `REQUEST` / `RESPONSE` / `AUTH` | ninguna: no viaja nada; sin sesión, sin licencia, sin base de datos |
| `SIDE_EFFECT` | cierre del socket; el cliente que conserva la conexión el mismo tiempo pierde la carrera: `ECONNRESET`, `socket hang up` o petición sin respuesta hasta caducar |
| `FAILURE_BEHAVIOR` / `RETRY_BEHAVIOR` | el cliente de Node no reintenta una petición ya enviada por una conexión reutilizada (correcto: no es idempotente en general) |
| `UI_EFFECT` / `BACKEND_EFFECT` | ninguno en el producto (nginx no reutiliza); en E2E y desarrollo con Vite, fallos puntuales |
| `NETWORK_COST` / `DB_COST` | **0** peticiones, **0** consultas: no es tráfico |
| `PURPOSE_COMMENT` | ninguno: es el valor por defecto de uvicorn, nunca decidido |
| `TEST_COVERAGE` | ninguna hasta este ciclo |

### Compuertas materiales

| Compuerta | Veredicto |
|---|---|
| `KEEPALIVE_SOURCE` | **PROVEN**: `timeout_keep_alive` por defecto de uvicorn (5 s) en los cinco arranques del repositorio |
| `KEEPALIVE_OWNER` | **PROVEN**: 054 (origen, evidencia, runner) con 052 (imagen); no es 002 (sesión), 047 (notificaciones: 60 s), 049 (dashboard: una lectura), 001 (health intacto) |
| `KEEPALIVE_PURPOSE` | **PROVEN**: **CASO 6, keep-alive HTTP del servidor** — ni polling, ni latido de sesión, ni despertar de proveedor, ni indicador de conectividad; nada en el producto depende de ese valor |
| `KEEPALIVE_CONSUMERS` | cualquier cliente que reutilice conexiones: Playwright/Node (5 s), proxy de Vite (Node), y un proxy inverso con `keepalive` de upstream si se configurara (nginx: 60 s por defecto) |
| `KEEPALIVE_SIDE_EFFECTS` | `ECONNRESET`/cuelgue en la ventana de ~10 ms alrededor de los 5 s; 0 tráfico, 0 base, 0 sesión, 0 licencia |
| `KEEPALIVE_REQUIRED` | el **mecanismo** (cerrar conexiones ociosas) sí; el **valor** 5 s no: debe superar al de todo cliente o proxy que reutilice |
| `REPLACEMENT_OR_REMOVAL` | **PROVEN**: **ajustar el valor en el arranque** (`--timeout-keep-alive 75`): mayor que Node (5 s) y que el `keepalive_timeout` de upstream de nginx (60 s por defecto), y el valor por defecto que nginx usa con sus clientes (75 s). No se toca el frontend, ni sesión, ni licencia, ni health, ni nginx (que hoy no reutiliza) |
| Sesión / licencia / notificaciones / dashboard / despliegue | **sin impacto**: no viaja ninguna petición; el único cambio es cuánto vive un socket ocioso |

## 3. `/speckit.specify` — FR-054-KA-001..030

Mapeo de los FR-KA sugeridos al hallazgo: 001–002 ningún tráfico periódico de 5 s existe y el
único mecanismo de 5 s queda con dueño (054/052), propósito (keep-alive HTTP) y valor decidido; 003,
005–007, 015–020 no aplican (no hay cliente que mantenga nada ni sondeo que parar; se **prueba** que no
existe ningún `setInterval`/`refetchInterval` salvo el de notificaciones a 60 s); 004 el temporizador
sigue acotado por conexión y se desarma solo; 008 health sin cambio; 009–014 sesión, licencia, sync,
límite de tasa, reverificación y rotación sin cambio; 016 el valor es explícito en cada arranque, uno
solo y por encima del proxy; 024 sin WebSocket/SSE/Redis; 025 la reducción medible es de **fallos** de
conexión, no de peticiones (no había tráfico): 20/20 cerradas a 5,3 s → 0/20; 026 contratos públicos
sin cambio; 027 esquema 0; 028–030 MASTER57, 057 y puntero sin cambio.

## 4. `/speckit.clarify` — 40 preguntas, `MATERIAL OQ = 0`

1–6 §2 (fuente, dueño, consumidor, función, armado y desarmado) · 7–8 sin petición, sin endpoint ·
9–18 sin base, auditoría, licencia, sesión, token, notificaciones, dashboard, health, conectividad ni
despertar · 19 **sí**: es exactamente el keep-alive del servidor · 20–28 frontend: sin dueño (no hay
sondeo; TanStack solo en la campana, 60 s, `enabled` con empresa) · 29 sin pruebas hasta hoy · 30
valor explícito 75 s en los cinco arranques · 31–33 frescura y cadencia no aplican · 34 esquema 0 · 35
despliegue: la imagen cambia su CMD; compose no cambia (lo hereda) · 36 nginx no reutiliza; se
documenta qué pasa si lo hace · 37 sin envoltorio móvil/escritorio · 38 E2E: el runner arranca igual
que producción; global ×2 · 39 mutaciones sobre los arranques y el valor · 40 DeepSeek: **0** (toda la
tarea es diagnóstico + una bandera; una lista de correcciones dictada no es delegación).

## 5. `/speckit.plan`, compuerta, checklist, tareas

`Dockerfile.backend` (CMD de producción y de `dev`), `Dockerfile.central` (CMD), `qa/e2e_corrida.py`
(`KEEP_ALIVE_SEGUNDOS = 75` en el backend y la autoridad de la corrida), `README.md` (orden de desarrollo):
**`--timeout-keep-alive 75`**. Sonda `qa/keepalive_sonda.py` (mide la supervivencia de una conexión
ociosa) y prueba `tests/test_backend_keepalive.py` que arranca uvicorn **con la orden exacta de las
imágenes** (leída del fichero): KA-01 reproduce el defecto, KA-02 lo cierra, KA-03 un solo valor por
encima del proxy en todos los arranques, KA-04 no existe ningún sondeo de 5 s, KA-05 health y nginx sin
cambio. nginx, frontend, sesión, licencia, central (salvo su CMD), esquema: **0**. **Compuerta
G01–G33: PASS.** Tareas: T01 descubrimiento/Spec Kit · T02 sonda + prueba (reproducción antes de tocar)
· T03 banderas · T04 mutaciones, medición, suites, E2E ×2, docs, Git. `analyze` previo:
`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0, `MATERIAL OQ = 0`, `UNKNOWN = 0`,
trazabilidad 100 %. **Autorización de `implement`:** la del encargo («tune HTTP keep-alive only if this
is the actual proven debt»: lo es).

## 6. Implementación (T02, T03)

- **Reproducción antes de tocar** · `qa/keepalive_sonda.py`: abre N conexiones HTTP/1.1, pide una vez
  por cada una, espera `ocio` segundos y vuelve a pedir **por la misma conexión**; cuenta cuántas sigue
  atendiendo el servidor y con qué error se cierran las demás. `tests/test_backend_keepalive.py::KA-01`
  arranca uvicorn con la orden de `Dockerfile.backend` **sin** la bandera (el estado de `37084cf`) y
  mide: 12/12 cerradas a los 5,3 s (`RemoteDisconnected`). Determinista: la carrera de ~10 ms de la
  evidencia original es la de un cliente que conserva la conexión *exactamente* lo mismo; con un ocio
  mayor que el valor del servidor la pérdida es total y repetible.
- **Cambio** · `--timeout-keep-alive 75` en los **cinco** arranques: `Dockerfile.backend` (CMD de
  producción y CMD de `dev` con `--reload`), `Dockerfile.central` (CMD), `qa/e2e_corrida.py`
  (`KEEP_ALIVE_SEGUNDOS = 75`, usado por el backend y la autoridad de la corrida: la corrida arranca
  como producción) y la orden de desarrollo del `README.md`. Por qué 75 y no 60 (el valor de la
  reproducción original): el servidor debe conservar la conexión **más** que cualquier cliente o proxy
  que la reutilice; Node, 5 s; el `keepalive_timeout` de upstream de nginx, 60 s por defecto — igualarlo
  reproduciría la misma carrera un piso más arriba el día que se active `upstream keepalive`; 75 s es,
  además, el valor con el que nginx conserva las de sus propios clientes. `compose.yaml` hereda el CMD
  de la imagen; `compose.central.yaml`, ídem.
- **Lo que no cambia, y por qué** · `resources/nginx/nginx.conf`: no reutiliza conexiones con el
  backend (sin `upstream`/`keepalive`/`Connection ""`), así que la producción detrás de nginx no sufría
  el fallo y no se le añade un `keepalive` de upstream que nadie ha pedido (M-10 lo vigila como cambio
  no decidido). Frontend **0** (no hay sondeo que parar: KA-04 lo fija), sesión y tokens **0**, licencia,
  sync, límite de tasa, reverificación y rotación **0**, `/health/live` y `/health/ready` **0** (KA-05),
  esquema cliente y central **0**, sin WebSocket/SSE/Redis. **DeepSeek: 0 llamadas** — la tarea entera
  es diagnóstico más una bandera repetida cinco veces; dictar esa lista no es delegar.

## 7. Pruebas y mutaciones (T02, T04)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_backend_keepalive.py` | KA-01 reproducción (orden de la imagen sin bandera → 12/12 cerradas a 5,3 s, `RemoteDisconnected`); KA-02 **orden exacta** de `Dockerfile.backend` y de `Dockerfile.central`, leída del fichero → 12/12 reutilizadas, 0 errores, y el valor > 60; KA-03 los cuatro CMD y el runner fijan **un solo** valor por encima del proxy; KA-04 el repositorio no tiene ningún sondeo de 5 s (único `refetchInterval`: notificaciones, 60 s); KA-05 `/health/live` y nginx sin cambio | uvicorn real en puerto libre, SQLite efímero |
| Regresión | `tests/test_e2e_corrida.py` (14, PostgreSQL) y las suites completas | — |
| E2E | global ×2 (el runner arranca backend y autoridad con la bandera) | PostgreSQL + autoridad real |

**Mutaciones** (`evidence/backend-keepalive/mutaciones.txt`, purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`, GOOD → PASS 6/6 antes de mutar; cada mutante arranca uvicorn de verdad con
la orden mutada): M-01 la imagen de producción sin bandera · M-02 la de desarrollo sin bandera · M-03 la
autoridad sin bandera · M-04 valor explícito 5 (la bandera está y no cambia nada) · M-05 valor 60 (igual
al proxy: la misma carrera un piso más arriba) · M-06 bandera mal escrita (uvicorn no arranca) · M-07 el
runner E2E arranca el backend sin la bandera · M-08 el runner fija otro valor que la imagen · M-09
producción y central divergen · M-10 nginx empieza a reutilizar conexiones sin decisión. Resultado:
**10/10 muertas**, RESTORED → PASS en las diez. Las del encargo que no aplican al mecanismo real —timer
sin limpiar, sondeo tras logout, tormenta de reintentos, pestaña oculta, multipestaña— no se fabrican:
no hay temporizador ni sondeo que mutar, y KA-04 fija que no lo hay.

## 8. Resultados

| Gate | Resultado |
|---|---|
| Reproducción determinista (KA-01 / KA-02) | sin bandera: **12/12** conexiones cerradas a los 5,3 s (`RemoteDisconnected`) · con la orden exacta de `Dockerfile.backend` y de `Dockerfile.central`: **12/12** reutilizadas, 0 errores |
| Medición controlada (`medicion-antes-despues.txt`, 20 conexiones por punto, ocios 1–74 s) | ANTES (por defecto): 20/20 vivas a 1 s y 4,9 s; **20/20 cerradas** a 5,0 · 5,3 · 10 · 30 · 60 · 74 s · DESPUÉS (75 s): **20/20 vivas** en los ocho puntos · registros del servidor: 1 línea cada uno (arranque), sin ruido. No había tráfico que reducir: `BEFORE_REQUESTS = AFTER_REQUESTS = 0` periódicas; la reducción medible es de **conexiones perdidas**: 20/20 → 0/20 por encima de 5 s |
| Mutaciones (`mutaciones.txt`) | **10/10 muertas**, RESTORED → PASS |
| Backend completo SQLite (`backend-sqlite-completo.txt`) | **43 failed / 1436 passed / 1020 skipped** = 42 documentales sin `clamscan` + `test_warehouse_structure::test_concurrencia…` (`ALMACENES-CARRERA-SQLITE-HILOS`, registrado; no se absorbe); +6 nuevas; **0 regresiones** |
| Backend completo PostgreSQL (`backend-postgres-completo.txt`, 21 min 43 s) | **39 failed / 2433 passed / 27 skipped** = 35 documentales + 2 `n9_integrity` (línea base 37) + `test_sync_success_records_run_snapshot_and_event` (intermitente de tiempo del arnés ya registrado: instante capturado al importar el módulo, suite larga) + `test_e2ecorrida_01` (vigila que la base protegida `ktest` no reciba escrituras durante una minicorrida, y la **propia suite completa** estaba escribiendo en `ktest`: `escrituras 2188122`; interacción de orden del arnés, ya vista en el ciclo de rotación). **Repetición dirigida PostgreSQL: 15/15** (`repeticion-dirigida-pg.txt`). Clasificación: C (intermitentes conocidos) ×2; **A (regresión del ciclo): 0**; **E (desconocido): 0**; ninguno absorbido, ningún código ni timeout tocado |
| `ruff check` (sonda, runner, prueba) | limpio |
| Frontend (`frontend-gates.txt`) | producto **0**; typecheck OK · lint OK · **459/459** · build OK |
| E2E global ×2 (`e2e-global-1.txt`, `e2e-global-2.txt`; backend y autoridad de la corrida con `--timeout-keep-alive 75`) | **232 passed / 0 failed / 40 skipped** y **232 / 0 / 40**; bases `r20261008t142441…` y `r20261008t142830…`, limpieza LIMPIA en ambas; `ECONNRESET`: **0** en las dos; puertos 8000/8010/5173 libres al cierre |
| Bases de corrida al cierre | **0** |
| Esquema cliente / central · frontend · sesión/auth · licencia · health · nginx | **0 / 0 · 0 · 0 · 0 · 0 · 0** (verificado en el diff: solo `Dockerfile.backend`, `Dockerfile.central`, `qa/e2e_corrida.py`, `README.md`, la sonda, la prueba, el delta, la evidencia y la hoja de ruta) |
| Docker | **no disponible** en esta máquina: no se afirma `docker build`; lo validado es la orden exacta del `CMD` ejecutada por uvicorn real, la sintaxis del `Dockerfile` y las pruebas |

**Los cinco arranques, verificados al cierre** (`grep -rn "uvicorn" --include=Dockerfile* --include=*.py --include=*.md`):
`STARTUP_PATH_1` `Dockerfile.backend` producción = **75** · `STARTUP_PATH_2` `Dockerfile.backend` `dev` (`--reload`) = **75** · `STARTUP_PATH_3` `Dockerfile.central` = **75** · `STARTUP_PATH_4` `qa/e2e_corrida.py` backend = **75** (`KEEP_ALIVE_SEGUNDOS`) · `STARTUP_PATH_5` `qa/e2e_corrida.py` autoridad = **75** (misma constante) · README (orden de desarrollo) = 75 · `CONSISTENT = YES`; `FIVE_SECOND_HTTP_KEEPALIVE_REMAINING = 0`.

## 9. `analyze` final, trazabilidad y veredicto

`UNJUSTIFIED_APPLICATION_5S_POLLING = 0` · `UNCONFIGURED_UVICORN_KEEPALIVE_PATH = 0` ·
`FIVE_SECOND_HTTP_KEEPALIVE_REMAINING = 0` · `FRONTEND_KEEPALIVE_CHANGE = 0` · `SESSION_CHANGE = 0` ·
`AUTH_CHANGE = 0` · `LICENSE_CHANGE = 0` · `HEALTH_CHANGE = 0` · `NGINX_CHANGE = 0` ·
`CLIENT_SCHEMA_CHANGE = 0` · `CENTRAL_SCHEMA_CHANGE = 0` · `FISCAL_SCOPE_EXPANSION = 0` ·
`SPEC057_STARTED = 0` · `NEXT_MASTER_SPEC_SELECTED = 0` · `RETRY_TO_GREEN = 0` (dos corridas E2E, una
cada una; la repetición dirigida de PostgreSQL es clasificación, no reintento a verde) ·
`RANDOM_SLEEP_WORKAROUND = 0` · `NEW_SKIP_WORKAROUND = 0` · `TIMEOUT_INFLATION_IN_TESTS = 0` ·
`SECRET_EXPOSURE = 0` · `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0` · huérfanos 0 ·
`MATERIAL OQ = 0` · `UNKNOWN = 0` · trazabilidad 100 %.

| Deuda | Estado |
|---|---|
| `BACKEND-KEEPALIVE-5S` | **CLOSED / CONVERGED** (2026-10-08) |
| `ALMACENES-CARRERA-SQLITE-HILOS`, intermitente de sync (tiempo del arnés), `test_e2ecorrida_01` dentro de la suite completa PostgreSQL | OPEN / intermitentes del arnés, no absorbidos |
| `PANEL-VERSION-VACIA` | **OPEN** — `NEXT TECHNICAL CYCLE` fijado por la dueña; **no iniciada** |
| Resto del encargo | OPEN, sin cambio |
| MASTER57 · SPEC057 · D0-07 · 039–043 · 056 · NEXT MASTER SPEC | sin cambio |

Orquestación: 4 tareas, `CLAUDE_ONLY` 4, `DEEPSEEK_ELIGIBLE` 0, **DeepSeek 0 llamadas**: todo el ciclo
(descubrimiento, sonda, prueba, bandera, mutaciones, medición, documentos, Git) lo hizo Claude.

| Cadena | Dónde |
|---|---|
| `BACKEND-KEEPALIVE-5S` → fuente física | `uvicorn.config.Config.timeout_keep_alive = 5` (medido) en los cinco arranques (§2) |
| → dueño / apoyo | 054 / 052 (§1) |
| → reproducción determinista | KA-01 (antes), KA-02 (después) |
| → valor | 75 s: > Node 5 s, > nginx upstream 60 s, = nginx cliente 75 s (§6) |
| → implementación | `Dockerfile.backend` ×2, `Dockerfile.central`, `qa/e2e_corrida.py` ×2, `README.md` |
| → medición | `medicion-antes-despues.txt` |
| → pruebas / mutaciones | `tests/test_backend_keepalive.py` KA-01..05 · M-01..10 |
| → PostgreSQL / E2E | suites completas + dirigida · E2E global ×2 |
| → documentación | este delta, `technical-debt-roadmap.md`, `next-spec-decision.md`, `master-56-specs-status.md`, README |
| → convergencia | **CONVERGED** |

**Veredicto: `BACKEND-KEEPALIVE-5S — CLOSED / CONVERGED`.**
