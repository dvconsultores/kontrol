# SPEC 004 · DELTA DIRIGIDO — LÍMITE DE TASA DEL ENDPOINT DE DESAFÍO DE LA AUTORIDAD CENTRAL

> Iniciado el 2026-10-08. Dueño: **Spec 004 global — Licenciamiento** (`010-licenciamiento-central`);
> apoyo de endurecimiento 055 (sin directorio propio: vive en la hoja de ruta), 054 (QA) y 052 solo en
> la recomendación de pasarela. Deuda: `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`. MASTER57, 057, D0-07, 039–043
> y 056 no se tocan. No se reabre nada cerrado (sync autenticado, rotación, reverificación, orden).
>
> **Objetivo:** que el endpoint pre-autenticación que emite desafíos tenga una política explícita,
> configurable y proporcional de control de abuso, sin alterar el desafío-respuesta, la identidad
> Ed25519, el nonce de un solo uso, la emisión, la rotación, el anti-retroceso, el cliente ni la
> renovación en `READ_ONLY`. Defensa en profundidad: **no es autenticación**.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `e3e9617` / **`e3e9617`** / `e3e9617` / `develop` / limpio · `COMMITS_AFTER_E3E9617 = 0` · `RUN_DATABASES = 0` · puertos 8000/8010/5173 libres |
| `ORCHESTRATION_STATUS` | `READINESS = PASS (12/12)` · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| Dueñas | SPEC004 primaria; 055 apoyo (endurecimiento); 054 QA; 052 solo pasarela · `OWNER_IDENTITY_CONFLICT = 0` |
| Punteros | `NEXT TECHNICAL CYCLE = CENTRAL-SYNC-SIN-LIMITE-DE-TASA` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Compuerta de descubrimiento (W03–W08) — leído en el código y el despliegue

| Registro | Valor |
|---|---|
| `CHALLENGE_PATH` | `POST /v1/license/sync/challenge` (`sync_auth_contract.CHALLENGE_TARGET`; `central_authority/main.py::challenge`) |
| `CHALLENGE_INPUT` | cuerpo JSON `{"installation_id": "<texto ≤ 64>"}`; inválido → `400 SYNC_INSTALLATION_INVALID` |
| `CHALLENGE_OUTPUT` | `200 {"protocol_version": 1, "challenge_id", "nonce" (64 hex), "expires_at"}`; **idéntica** para identidad desconocida (fila sin instalación que nunca autentica: sin enumeración) |
| `CHALLENGE_TTL` | `KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS` = 120 (5–900) |
| `CHALLENGE_TABLE` | `cla_sync_challenges` (`id`, `installation_id` FK anulable, `nonce_sha256`, `protocol_version`, `created_at`, `expires_at`, `consumed_at`); índices `installation_id` y **`expires_at`** |
| `CHALLENGE_CLEANUP` | perezosa al emitir: `DELETE … WHERE expires_at < now - 1 h` (SYNC-19); sin planificador. Las filas consumidas/vencidas < 1 h se conservan (auditoría y forense del protocolo) |
| `EXISTING_RATE_LIMIT_INFRA` | **ninguna**: el cliente solo tiene bloqueo de login por intentos (`lockout_*`); `login_rate_limit_per_minute` existe en `Settings` del cliente pero no hay limitador reutilizable; `errors.py` mapea 429 → `RATE_LIMITED` solo en el cliente; sin Redis, sin middleware de throttling, sin métricas (la autoridad solo tiene `logging` + `log_json`) |
| `REVERSE_PROXY` | **ninguno en el repositorio para la autoridad**: `compose.central.yaml` levanta `central-db` + `central-api` (uvicorn, un proceso, `0.0.0.0:8010`) en la red `kontrol-central-net` **sin `ports:` publicados**; el README dice «póngalo detrás de la pasarela que corresponda». `resources/nginx/nginx.conf` es la pasarela del **cliente** (`proxy_pass backend:8000`, `X-Forwarded-For`), no de la autoridad |
| `TRUSTED_PROXY_POLICY` | **indefinida**: nadie declara qué proxy antecede a la autoridad ni qué cabeceras `Forwarded`/`X-Forwarded-For`/`X-Real-IP` son de confianza; uvicorn corre sin `--proxy-headers`/`--forwarded-allow-ips` |
| `CLIENT_IP_SOURCE` | `request.client.host` sería la IP del proxy (si lo hay) o la del contenedor vecino; **no identifica al origen** |
| Modelo de procesos | un `uvicorn` sin `--workers` en imagen y compose; nada impide réplicas o trabajadores: el estado del protocolo ya vive en PostgreSQL «para varios procesos y peticiones concurrentes» (modelo `SyncChallenge`) |
| Cliente | `UrllibSyncTransport._post`: cualquier 4xx → `CentralSyncRejected(code, status, message)` → `sync_license` registra `LicenseSyncRun FAILED`, evento `LICENSE_SYNC_REJECTED` con `central_code`, config `DISCONNECTED` y responde `502 CENTRAL_SYNC_REJECTED` al administrador; **sin reintentos** (ni en el servicio ni en un planificador: no hay sync automático), sin retroceso a sync anónimo; `/licensing/sync` exenta del bloqueo `READ_ONLY`; frontend: `useMutation` sin `retry` (0) y `debeReintentar` solo gobierna consultas |
| Auditoría | cada desafío emitido escribe `SYNC_CHALLENGE` (OK / UNKNOWN_INSTALLATION) en `cla_audit_events`; los rechazos del sync escriben `SYNC` |

### Compuertas materiales

| Compuerta | Veredicto | Por qué |
|---|---|---|
| `CHALLENGE_ABUSE_MODEL` | **PROVEN** | un llamador no autenticado puede pedir desafíos sin cota: cada uno es una fila (`nonce` aleatorio, auditoría), presión de CPU/IO en PostgreSQL y crecimiento acotado solo por la limpieza perezosa (TTL + 1 h). El riesgo volumétrico de red queda fuera (FR-RATE-031) |
| `TRUSTED_SOURCE_POLICY` | **NOT_REQUIRED** | no hay contrato de proxy de confianza, así que la IP de origen **no es** una identidad fiable en la aplicación: no se usa. El límite por origen se **recomienda en la pasarela** (donde la IP real sí es conocida); la aplicación impone un mínimo que no depende de cabeceras del llamador (FR-RATE-011/012) |
| `RATE_LIMIT_AUTHORITY` | **PROVEN** | la dimensión **global** por autoridad es la única identidad fiable pre-autenticación; `installation_id` lo controla el llamador (no puede ser autoridad única, FR-RATE-010) y, además, una dimensión por `installation_id` sobre la FK (nulo para desconocidos) **distinguiría** conocidos de desconocidos (fuga, FR-RATE-009) o exigiría una columna nueva: no se añade |
| `FAILURE_POLICY` | **PROVEN** | el límite se decide dentro de la misma transacción de PostgreSQL que persiste el desafío, sobre las filas que ya existen: **no hay subsistema propio** que pueda fallar abierto o cerrado por separado; si la base no responde tampoco se emite (comportamiento existente). Sin decisión nueva |
| `MULTI_PROCESS_BEHAVIOR` | **PROVEN** | estado en PostgreSQL (compartido por trabajadores y réplicas) y candado consultivo transaccional `pg_advisory_xact_lock` alrededor de «contar + insertar»: límite **exacto** entre procesos; SQLite (local/QA) serializa las escrituras |
| Exposición directa | **no bloquea** | el compose no publica 8010 (privado a la red del propietario); si un operador lo publica, la aplicación ya impone el mínimo global: el diseño no depende de que la pasarela exista |
| Valores por defecto | **inferibles** | una sincronización legítima = un desafío; el sync es manual (sin automático), la renovación es anual; una flota de N instalaciones que sincronizara el mismo minuto necesita N. **120 desafíos por ventana de 60 s**: ráfaga completa, 2/s sostenido, 172 800/día —órdenes de magnitud sobre cualquier flota legítima— y acota la tabla a ≤ 120 filas por minuto (≤ 7 320 filas retenidas con TTL 120 s + 1 h). Configurable |

## 3. `/speckit.specify` — FR-010-538..576 (= FR-RATE-001..039)

El endpoint de desafío tiene límite explícito, configurable y por defecto activo; es defensa en
profundidad, no autenticación; ráfaga = capacidad, sostenido = capacidad/ventana; se decide **antes**
de persistir la fila; un rechazo no consume ni altera desafíos emitidos ni estado de licencia ni
registro; nonce, caducidad, un solo uso, propiedad, firma, método, destino y hash del cuerpo no cambian;
conocidos y desconocidos reciben el **mismo** 429; `installation_id` no es autoridad única; la IP solo
desde un contrato de confianza (no lo hay → pasarela); cabeceras `Forwarded` no deciden; correcto con
varios trabajadores/réplicas; `429 {"code": "SYNC_RATE_LIMITED", "message": genérico}` + `Retry-After`
determinista; el cliente no retrocede ni reintenta en bucle; renovación en `READ_ONLY` posible;
`license:create`, verificación del desafío, rotación y reverificación intactas; sin material en
registros; registro acotado (un aviso por ventana, sin `installation_id`), sin inundar la auditoría de
negocio; tabla acotada por el límite + limpieza existente; la limpieza nunca borra un desafío vivo;
agnóstico de proveedor; sin WAF/KMS obligatorios; sin Redis; no es protección volumétrica (documentar
pasarela); health mínimo; esquema cliente 0; esquema central 0 (sin tabla ni índice nuevos); MASTER57,
057 y puntero sin cambio.

## 4. `/speckit.clarify` — 48 preguntas, `MATERIAL OQ = 0`

1–8 §2 · 9–11 un proceso por imagen; réplicas posibles; estado en PostgreSQL · 12 sin `ports:` (privado);
la app impone el mínimo igualmente · 13–16 sin proxy ni contrato de confianza → IP no se usa en la app ·
17–18 ninguna infraestructura reutilizable · 19 `Settings` pydantic `KONTROL_CENTRAL_*` con validador de
`prod` · 20–21 sin reintentos automáticos (servicio, planificador, frontend) · 22 `/licensing/sync`
exenta de `READ_ONLY` · 23–24 crecimiento acotado por TTL + 1 h; retención de consumidos intacta ·
25–27 solo `logging`; rechazos → aviso acotado, no auditoría de negocio · 28 sin subsistema propio (§2)
· 29 **ventana deslizante exacta** sobre `created_at` (correcta, simple, sin estado nuevo, reinicio
indiferente, multiproceso por PostgreSQL, ráfaga = capacidad); se descartan token/leaky bucket (estado
mutable nuevo) y ventana fija (doble ráfaga en el borde) · 30–33 global sí; origen → pasarela;
`installation_id` no (fuga por FK nula + control del llamador) · 34–35 NAT/IPv6: no aplican en la app
(sin IP); se documentan para la pasarela · 36 `Retry-After` = segundos hasta que el más antiguo salga de
la ventana, [1, ventana] · 37 120/60 s (§2) · 38–39 QA/pruebas: capacidad alta por defecto; las pruebas
construyen `Settings` propios (capacidad pequeña); `enabled=false` solo fuera de `prod` · 40 candado
consultivo PG · 41–43 esquema 0; migración 0; frontend 0 · 44–47 pruebas RL (hostiles, PG concurrente,
mutaciones, E2E dirigido con la autoridad real + global) · 48 DeepSeek: matriz pura de `decide` y
validación de `Settings`.

## 5. `/speckit.plan`, compuerta, checklist, tareas

Núcleo puro `central_authority/rate_limit.py` (`RateLimitPolicy`, `RateLimitDecision`, `window_start`,
`decide`); `Settings.sync_challenge_rate_limit_{enabled,capacity,window_seconds}` (prod no se apaga);
`service.create_sync_challenge`: candado consultivo → limpieza → **`_comprobar_tasa_de_desafios`**
(cuenta `created_at >= inicio` acotada por el índice `expires_at > inicio`; llena → `rollback` +
`SyncRateLimited(429)` con `Retry-After`; aviso acotado por ventana) → insertar; `main._error` añade la
cabecera. Cliente: **sin cambio** (el 429 ya es un rechazo acotado, sin reintentos). Pasarela: README +
contrato con la recomendación de límite por origen y la advertencia sobre cabeceras reenviadas. E2E:
proyecto `licencia-tasa` (tras `licencia-rotacion`) contra la autoridad real de la corrida con capacidad
reducida por el runner. **Compuerta G01–G41: PASS.** Tareas: T01 inventario/Spec Kit · T02 núcleo puro ·
T03 config + servicio + API · T04 **DeepSeek** matriz pura + validación de config · T05 pruebas hostiles
(RL-01..) y PG concurrente · T06 E2E · T07 mutaciones, suites, docs, Git. `analyze` previo:
`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0, `MATERIAL OQ = 0`, `UNKNOWN = 0`,
trazabilidad 100 %. **Autorización de `implement`:** la del encargo (todas las compuertas PROVEN /
NOT_REQUIRED).

## 6. Implementación (T02, T03)

- **Núcleo puro** · `central_authority/rate_limit.py`: `RateLimitPolicy(enabled, capacity, window_seconds)`
  (inmutable; valores < 1 → `ValueError`), `RateLimitDecision(allowed, reason, retry_after_seconds)`,
  `window_start`, `decide(policy, now, issued_in_window, oldest_in_window)`: apagada → admite
  (`disabled`); `issued < capacity` → `ok`; si no, rechazo `capacity_exceeded` con `Retry-After` =
  segundos hasta que el más antiguo salga de la ventana, acotado a [1, ventana]; sin instante del más
  antiguo → ventana entera (cerrado ante error). Sin azar, sin `sleep`, sin reloj propio.
- **Configuración** · `Settings.sync_challenge_rate_limit_enabled` (`true`), `…_capacity` (120; 1–100000),
  `…_window_seconds` (60; 1–3600); el validador de `prod` rechaza `enabled=false` (misma convención que la
  clave de firma obligatoria). `compose.central.yaml` expone las dos variables numéricas con sus valores
  por defecto; README central documenta las tres.
- **Servicio** · `create_sync_challenge`: validar identidad → **candado consultivo transaccional**
  (`pg_advisory_xact_lock`, solo PostgreSQL; sección crítica de milisegundos que hace el límite exacto
  entre trabajadores) → limpieza perezosa existente → **`_comprobar_tasa_de_desafios`**: cuenta y mínimo
  de `created_at` de las filas con `created_at >= inicio`, acotadas por el índice existente
  (`expires_at > inicio`, superconjunto de la ventana); ventana llena → `db.rollback()` (no queda fila, no
  se toca nada), aviso de registro **acotado** (uno por ventana y proceso, con el recuento de rechazos
  acumulados; sin `installation_id`, que es del llamador) y `SyncRateLimited` (429, mensaje genérico,
  `retry_after_seconds`) → si hay hueco, insertar y auditar como siempre. `main._error` añade
  `Retry-After` solo a ese error. `POST /v1/license/sync` no se limita por esta política (consume
  desafíos ya emitidos). Sin métricas nuevas: la autoridad no tiene pila de observabilidad; el recuento
  por proceso va en el aviso.
- **Cliente** · **sin cambio**: `UrllibSyncTransport` ya convierte cualquier 4xx en `CentralSyncRejected`
  y `sync_license` lo registra como `LicenseSyncRun FAILED` + evento `LICENSE_SYNC_REJECTED`
  (`central_code: SYNC_RATE_LIMITED`) y responde `502 CENTRAL_SYNC_REJECTED`; no hay reintentos (ni
  servicio, ni planificador, ni `useMutation`), no hay retroceso, `/licensing/sync` sigue exenta de
  `READ_ONLY`, `license:create` intacto. Probado con la autoridad real en proceso (RLC-01..03).
- **QA** · `qa/e2e_corrida.py` levanta la autoridad de la corrida con capacidad 40 / 60 s
  (`KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_*`) y pasa `KONTROL_E2E_CENTRAL_RATE_CAPACITY` a la suite;
  proyecto Playwright `licencia-tasa` (tras `licencia-rotacion`, el último: inunda la ventana) con
  `e2e/licencia-tasa.spec.ts`; `test_e2ecorrida_14` cuenta cinco proyectos.
- **Lo que no cambia** · esquema central **0** (sin tabla, columna ni índice: RL-13 lo fija), cliente **0**,
  frontend de producto **0**; desafío-respuesta, nonce, caducidad, un solo uso, consumo atómico,
  firma del sobre, emisión, `revision`, rotación por `kid`, reverificación del vigente, health. Sin
  Redis, sin WAF obligatorio, sin planificador, sin CAPTCHA, sin `sleep`.

## 7. Pruebas y mutaciones (T04, T05, T06)

| Suite | Casos | Motor |
|---|---|---|
| `tests/central/test_rate_limit_rules.py` (T04; **escrita por Claude** tras agotar los dos reintentos de DeepSeek, ver §9) | RLR-01..12 (44 recogidas): apagada admite; `window_start`; por debajo de la capacidad; en la capacidad y por encima; `Retry-After` exacto por antigüedad (0 → ventana, 50 s → 10, 59.2/59.9/60/70 s → 1); sin instante → ventana entera; recuento negativo; política inválida; `Settings` por defecto (True, 120, 60); límites de pydantic inválidos y extremos válidos; `prod` no se apaga y `qa` sí; determinismo e inmutabilidad | puro |
| `tests/central/test_central_challenge_rate_limit.py` | RL-01..13: bajo el límite; **429 genérico sin fila ni auditoría**; `Retry-After` determinista desde el más antiguo (≈10 s tras envejecerlo 50 s); lo emitido no se toca; **un desafío anterior autentica y devuelve la licencia con la emisión limitada** (y sigue siendo de un solo uso); conocida y desconocida reciben el mismo 429; rotar identidades inventadas no esquiva el límite y la tabla queda acotada; configurable, `prod` no se apaga, rangos, defecto activo; ventana deslizante (hueco exacto para uno; ráfaga = capacidad al vaciarse); health no limitado ni revelador; registro acotado (un aviso por ventana, sin identidad del llamador); limpieza perezosa igual; **esquema central 0** (columnas, índices y tablas exactos) | SQLite y PostgreSQL |
| `tests/central/test_central_challenge_rate_limit_pg.py` | RLPG-01: 24 peticiones simultáneas por hilos (sesiones distintas) con capacidad 10 → exactamente 10 × 200 y 14 × 429; 10 filas | PostgreSQL |
| `tests/test_license_sync_rate_limit_client.py` | RLC-01..03 con la autoridad real en proceso (capacidad 1): el primer sync entra; con la autoridad limitando, el cliente responde `502 CENTRAL_SYNC_REJECTED` / `central_code SYNC_RATE_LIMITED`, **una sola petición de desafío y ninguna de sync**, `LicenseSyncRun FAILED`, evento `LICENSE_SYNC_REJECTED`, estado de licencia intacto, sin material; un intento explícito posterior con la ventana movida sincroniza | SQLite |
| Adaptadas | `test_e2ecorrida_14` (quinto proyecto `licencia-tasa`) | — |
| E2E | `e2e/licencia-tasa.spec.ts` (E2E-RATE-01..04) en el proyecto `licencia-tasa`, el último, contra la autoridad real de la corrida con capacidad 40 | PostgreSQL + autoridad real |

**Mutaciones** (`evidence/central-sync-rate-limit/mutaciones-backend.txt`, purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`; GOOD → PASS 60/60 y 1/1 PG antes de mutar): M-01 el límite no se comprueba ·
M-02 «≤» en vez de «<» (admite capacidad + 1) · M-03 `Retry-After` siempre la ventana · M-04 `Retry-After`
puede ser 0 o negativo · M-05 `enabled` ignorado · M-06 la comprobación llega después de crear la fila ·
M-06b la comprobación no se invoca · M-07 el rechazo no deshace la transacción · M-08 dimensión por
`installation_id` (solo desconocidas) · M-09 la ventana no desliza · M-10 429 sin `Retry-After` · M-11 aviso
de registro en cada rechazo · M-12 `prod` puede apagar el límite · M-13 sin candado consultivo
(**PostgreSQL**, carrera) · M-14 el 429 lleva el identificador pedido. Primera pasada: **14/15 muertas**;
M-07 sobrevivió porque desde la API la sesión se cierra al salir y el `rollback` implícito lo tapa. Se
añadió **RL-14** (invariante del servicio: tras el 429 no queda transacción en vuelo, la sesión sigue
usable y no hay fila) y M-07 muere: **15/15**.

## 8. Resultados

| Gate | Resultado |
|---|---|
| Nuevas suites SQLite / PostgreSQL | RLR 44 + RL 14 + RLC 3 = **61** (SQLite) · RLR 44 + RL 14 + RLPG 1 = **59** (PostgreSQL); regresión central (CLA, SYNC, SYNC-PG, REV), sync del cliente (CSYNC 13) y runner (14) en verde |
| Backend completo SQLite / PostgreSQL (`backend-sqlite-completo.txt`, `backend-postgres-completo.txt`) | **42 failed / 1430 passed / 1020 skipped** = línea base exacta de documentos sin `clamscan`; **0 regresiones** / **38 failed / 2427 passed / 27 skipped** = 35 documentos + 2 `n9_integrity` (línea base) + `test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event`, que compara `last_reliable_date` con un instante capturado al importar el módulo y falla si entre el import y la prueba pasan minutos (suite de 23 min bajo carga); pasa solo y en la corrida dirigida PostgreSQL (29/29) y no toca nada de este ciclo: intermitente de tiempo del arnés, anotado, no absorbido |
| `ruff check` · `mypy central_authority` | limpio · limpio (11 ficheros) |
| Frontend `typecheck` · `lint` · `vitest` · `build` (`frontend-gates.txt`) | OK · OK · **459/459** · OK (producto 0; solo `e2e/` y `playwright.config.ts`) |
| E2E global (`chromium` → `licencia-revision` → `licencia-sync` → `licencia-rotacion` → **`licencia-tasa`**; `e2e-global.txt`) | **232 passed, 0 failed, 40 skipped** (231 + E2E-RATE-01..04 contra la autoridad real con capacidad 40: inundación → 429 genérico con `Retry-After`, capacidad no superada, health intacto); base `r20261008t035509…`, limpieza LIMPIA, puertos libres al cierre |
| Bases de corrida al cierre | **0** |
| Esquema central / cliente / frontend de producto | **0 / 0 / 0** |

## 9. Deudas, veredicto y trazabilidad

| Deuda | Estado |
|---|---|
| `CENTRAL-SYNC-SIN-LIMITE-DE-TASA` | **CLOSED / CONVERGED** (2026-10-08) |
| Límites declarados | la aplicación no limita por origen (sin contrato de proxy de confianza: va en la pasarela, documentado); no es protección volumétrica; un proxy de confianza futuro sería una decisión nueva |
| `BACKEND-KEEPALIVE-5S`, `PANEL-VERSION-VACIA`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` y el resto del encargo | OPEN, sin cambio |
| Punteros | `NEXT TECHNICAL CYCLE` ejecutado · `NEXT MASTER SPEC = NOT YET PRIORITIZED` (sin cambio) |
| MASTER57 · SPEC057 · D0-07 · 039–043 · 056 | sin cambio |

Orquestación: 7 tareas, `CLAUDE_ONLY` 6, `DEEPSEEK_ELIGIBLE` 1 (T04). DeepSeek `deepseek-v4-flash`: 3
llamadas (intento + 2 reintientos; 2209/2005, 2005/2226 y 2384/2478 tokens; $0.000853 + $0.000904 +
$0.00101 = **$0.002767**), **3 parches rechazados, 0 aceptados**: (1) `pytest.skip` en una parametrización
cruzada, `import math` sin uso y una línea tautológica; (2) ruff B010 por dos `setattr` —instrucción
errónea de mi propio brief, que corregí en el tercero—; (3) `Settings(_env_file=None)` sin `environment`
ni `db_url`, dependiente del entorno del proceso (deriva de contrato). Reintentos agotados →
reclasificada: **la matriz la escribió Claude** (44 casos). Egress en las tres llamadas: solo la firma del
módulo puro, nombres de campos de `Settings` y claves sintéticas generadas en la prueba
(`ENV_FILES=0 REAL_PRIVATE_KEYS=0 REAL_PUBLIC_KEYS=0 REAL_LICENSES=0 REAL_SIGNATURES=0
REAL_INSTALLATION_IDS=0 REAL_IP_ADDRESSES=0 REAL_DB_URLS=0 TOKENS=0 PASSWORDS=0 REAL_PII=0`). `analyze`
final: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; huérfanos 0; `MATERIAL OQ = 0`;
`UNKNOWN = 0`; trazabilidad 100 %:

| FR (010-538..576 = RATE-001..039) | Dónde | Prueba |
|---|---|---|
| 001–004 límite explícito, defensa en profundidad, configurable, ráfaga + sostenido | `rate_limit.py`, `Settings`, `_comprobar_tasa_de_desafios` | RLR-01..05, 09–11; RL-01, 02, 08, 09; M-01, 02, 05, 12 |
| 005–008 antes de persistir; sin consumir ni mutar; sin tocar licencias; semántica del desafío intacta | orden en `create_sync_challenge`, `rollback` | RL-02, 04, 05, 14; SYNC-01..20 en verde; M-06, 06b, 07 |
| 009–010 sin fuga de registro; `installation_id` no es autoridad | dimensión global; 429 idéntico | RL-06, 07; M-08, 14 |
| 011–012 IP solo con contrato de confianza; cabeceras reenviadas no deciden | sin IP en la app; README/contrato | §2 (`TRUSTED_SOURCE_POLICY = NOT_REQUIRED`) |
| 013 multiproceso correcto | PostgreSQL + `pg_advisory_xact_lock` | RLPG-01; M-13 |
| 014–016 429 canónico, mensaje genérico, `Retry-After` determinista | `SyncRateLimited`, `main._error` | RL-02, 03, 06; RLR-05; E2E-RATE-03; M-03, 04, 10 |
| 017–020 cliente sin retroceso ni tormenta; `READ_ONLY` y `license:create` intactos | cliente sin cambio | RLC-01..03; CSYNC en verde |
| 021–023 verificación, rotación, reverificación intactas | sin cambio | SYNC, KEYROT, REVST en verde (suites completas) |
| 024–025 sin material; registro acotado; sin inundar auditoría | `_anotar_rechazo_de_tasa` | RL-02, 11; M-11 |
| 026–027 tabla acotada; la limpieza no borra lo vivo | límite + limpieza existente | RL-07, 12; SYNC-19 |
| 028–033 agnóstico, sin WAF/Redis, no volumétrico, docs de pasarela, health mínimo | README, contrato | RL-10; E2E-RATE-04; CLA-18 |
| 034–036 esquema cliente 0; central 0; sin tabla nueva | sin modelos ni migraciones | RL-13 |
| 037–039 MASTER57, 057, puntero | docs | §9 |

**Veredicto: CONVERGED.**
