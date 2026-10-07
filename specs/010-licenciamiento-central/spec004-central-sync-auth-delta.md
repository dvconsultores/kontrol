# SPEC 004 · DELTA DIRIGIDO — SINCRONIZACIÓN AUTENTICADA CLIENTE ↔ AUTORIDAD CENTRAL

> Iniciado el 2026-10-07. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Apoyos: SPEC002 (sesión y permiso local del llamador), SPEC004 ·
> Autoridad Central (`central-authority/`), SPEC054 (QA). Deuda: `CENTRAL-SYNC-AUTHORITY-UNDEFINED`
> (decisión de la dueña ya tomada; aquí se implementa).
>
> **Mecanismo ratificado, no se reabre:** identidad Ed25519 de la instalación + desafío-respuesta +
> nonce aleatorio de un solo uso + caducidad corta del servidor + firma de un sobre canónico ligado a
> `protocol_version`, `installation_id`, `challenge_id`, `nonce`, método, destino canónico y SHA-256 de
> los bytes exactos del cuerpo; verificación contra la clave pública **previamente vinculada** por el
> vendor. Sin secretos compartidos, sin autorregistro, sin confianza aportada por el llamador, sin mTLS
> como contrato de producto, sin mezclar la clave del propietario con la identidad de la instalación.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `ac27f59` / **`ac27f59`** / `ac27f59` / `develop` / limpio · `COMMITS_AFTER_AC27F59 = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` / `DEEPSEEK_TOOL` / `MODEL_ROUTING` / `RETRY_MAX` | `VERIFIED_END_TO_END` / `mcp__deepseek__deepseek_chat` / `deepseek-v4-flash` (mecánico) · `deepseek-v4-pro` (no usado) / 2 |
| `PRIMARY_OWNER` / `SECURITY_SUPPORT` / `CENTRAL_COMPONENT` / `QA_OWNER` | SPEC004 (`010-licenciamiento-central`) / SPEC002 (solo `require_permission`, sin cambio) / SPEC004 · Autoridad Central / SPEC054 |
| `OWNER_IDENTITY_CONFLICT` | **0** |

Tres autoridades, independientes: la clave privada de la **instalación** prueba «viene de X»; la clave
privada del **propietario** firma licencias; el certificado **TLS** protege el canal. Prohibido: enviar
cualquiera de las dos privadas; registrar una clave pública recibida en un sync; confiar en una clave que
traiga la petición; firmar licencias con la clave de la instalación; autenticar al cliente con la del
propietario.

## 2. Inventario (W01–W12)

| Qué | Dónde | Hallazgo |
|---|---|---|
| Flujo local de sync | `POST /api/v1/licensing/sync` → `licensing_service.sync_license(db, sync_client, actor)` | Ya exige sesión + `license:create`. Lleva además `require_write_allowed`: en `READ_ONLY` **bloqueaba la renovación** (contradice FR-SYNC-046) |
| Transporte remoto | `default_sync_client` (`urllib`, `POST /v1/license/sync`, cuerpo `{version, installation_id, license_jws, modules, requested_at}`) | **Anónimo**: solo `installation_id`; la respuesta (`status`, `entitlements`, `server_time`) se aplicaba al estado **sin firma** (`state.mode = server_status`) |
| Clave privada de la instalación | `installation_volume_path/installation_private_key.pem` (0600), `_private_key_path()`; Ed25519 PKCS8 PEM | Cargador canónico reutilizable; `INSTALACION-KEY-REFERENCE-120` no se toca |
| Clave pública de la instalación | `Installation.public_key` (PEM SPKI) y `installation_request_payload` | Ningún endpoint la expone; para el enrolamiento fuera de banda hace falta un ayudante local |
| Registro central | `cla_installations.public_key_pem` **NOT NULL**, vinculada en el alta por CLI (`register-installation --public-key-file`), idempotente, `INSTALLATION_CONFLICT` si cambian los datos | El enrolamiento controlado por el vendor **ya existe**; faltan la huella, la unicidad de clave entre instalaciones y el rechazo explícito de clave ya vinculada a otra |
| Sync central | `main.py`: solo health; `/v1/license/sync` → 404 (CLA-15) | Se expone solo con la prueba completa |
| Canonicalizador | `license_contract.canonical_bytes` (JSON con separadores por defecto) | Semántica distinta: el sobre define la suya (sin espacios), en módulo puro propio |
| Libro central | `cla_issuances` (período, `revision`, `payload`, `signature_hex`) | Selección del artefacto: período primero, `revision` después; se devuelve el artefacto exacto |
| Ordenación anti-retroceso en el cliente | `import_license` (período, `revision`, bloqueo) | Lo recibido por sync pasa por ella; la autenticación remota no la sustituye |
| Migraciones centrales | `0001_cla_fase1` (cabeza única) | Este ciclo añade `0002`; cliente: 0 |

## 3. `/speckit.specify` — FR-010-367..436 (= FR-SYNC-001..070 del encargo)

| FR-010 | Requisito |
|---|---|
| 367–373 | Autenticación con la identidad Ed25519 de la instalación; clave pública vinculada por el vendor; la aportada por el llamador no crea confianza; sin autorregistro; sin vínculo = no enrolada; sin sustitución silenciosa; sin rotación |
| 374–378 | Endpoint de desafío mínimo; nonce criptográfico; caducidad corta del servidor; un solo uso; estado en PostgreSQL central |
| 379–385 | El sobre liga versión, identidad, desafío, nonce, método, destino canónico y SHA-256 de los bytes exactos del cuerpo |
| 386–387 | El servidor recalcula el hash de los bytes recibidos y verifica con la clave del registro |
| 388–392 | Firma inválida, desafío caducado o consumido se rechazan; reutilización impedida atómicamente; dos simultáneas → a lo sumo un éxito |
| 393–399 | Desafío de A no autentica a B; firma de A no autoriza una petición para B; alterar cuerpo, método, destino o versión invalida; versión desconocida se rechaza |
| 400–404 | Un desafío nuevo por intento; sin retroceso a sync anónimo; firma con la clave canónica; la privada no sale; la autoridad nunca la recibe |
| 405–407 | Solo la licencia de la instalación autenticada; lecturas cruzadas rechazadas; artefacto exacto |
| 408–412 | El cliente sigue verificando firma del propietario, identidad y anti-retroceso; sesión + `license:create`; renovación en `READ_ONLY` posible |
| 413–415 | HTTPS en producción; HTTP explícito solo en local/dev/qa; mTLS no requerido |
| 416–419 | Clave del propietario separada de la de identidad; `kid` igual; rotaciones fuera de alcance |
| 420–423 | Cliente: 0 migraciones; central: puede añadir vínculo y desafíos; estado del desafío sobrevive a varios procesos; replay probado en PostgreSQL |
| 424–426 | Canonicalización documentada en `contracts/`; determinista; cuerpo serializado una vez, hasheado, firmado y enviado tal cual |
| 427–429 | Los fallos no exponen registro ni licencia; el desafío no expone metadatos; registros sin claves ni credenciales |
| 430–434 | Emisor, anti-retroceso, `/license/status`, diagnóstico y health sin cambios |
| 435–436 | MASTER56 = 56; NEXT SPEC = 029 |

## 4. `/speckit.clarify` — resueltas, `MATERIAL OQ = 0`

Dueñas §1 · flujo local: `/licensing/sync` existente, se **quita** `require_write_allowed` (FR-046; la
sesión y `license:create` quedan) · transporte: objeto inyectable con `challenge()` y `sync()`;
por defecto `urllib` · clave privada: `_private_key_path()` + `load_private_key` del contrato puro ·
exportar la pública: ayudante local `scripts/clave_publica_instalacion.py` (deriva de la privada,
imprime PEM y huella, nunca la privada, nunca transmite) · registro: el alta por CLI **es** el
vínculo (`register-installation --public-key-file`); se añade `public_key_fingerprint` (SHA-256 del
DER SPKI) **único**: la misma clave para otra instalación → `INSTALLATION_KEY_ALREADY_BOUND`; otra
clave para la misma → `INSTALLATION_CONFLICT` (sin rotación) · filas sin clave: no existen (`NOT NULL`)
· desafío: `cla_sync_challenges` (`id` UUID opaco, FK **anulable** a la instalación —desconocida =
`NULL`, nunca autentica—, `nonce_sha256` (se guarda el **resumen**, no el nonce), `protocol_version`,
`created_at`, `expires_at`, `consumed_at`), índices por instalación y por caducidad · TTL:
`KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS`, por defecto **120 s** (5–900), configuración técnica
documentada · nonce: `secrets.token_hex(32)` = 256 bits · versión: entero `1`; otra → 400
`SYNC_PROTOCOL_UNSUPPORTED` · sobre: JSON UTF-8, claves ordenadas, `separators=(",", ":")`, siete
campos exactos; hash en hex minúsculo; método en mayúsculas; destino = ruta sin consulta (una consulta
→ `SYNC_TARGET_MISMATCH`) · transporte de la prueba: cabeceras `X-Kontrol-Installation`,
`X-Kontrol-Challenge`, `X-Kontrol-Nonce`, `X-Kontrol-Sync-Protocol`, `X-Kontrol-Signature`; el cuerpo
de negocio no cambia; una clave pública en la petición se **ignora** · orden en el servidor: versión →
cabeceras → destino → desafío (`FOR UPDATE`) + instalación + nonce + versión → consumido → caducado →
firma con la clave del registro (**una firma inválida no consume**) → consumo atómico (`UPDATE … WHERE
consumed_at IS NULL AND expires_at > now`, exactamente una fila) → identidad del cuerpo = identidad del
sobre → selección del artefacto · enumeración: el desafío responde igual a instalaciones desconocidas
(fila con FK `NULL`), y en el sync «instalación desconocida» y «firma inválida» comparten
`SYNC_AUTH_INVALID`; cuerpo/método/destino alterados también acaban en `SYNC_AUTH_INVALID` porque el
servidor los deriva de la petición real · sin licencia: `{"status": "NO_LICENSE"}`, el cliente anota y
no toca el estado · respuesta: `{"version": "1", "status": "LICENSE", "server_time", "license": {payload,
signature_hex}, "license_id", "revision"}`; el cliente la pasa por `import_license` (todas las
compuertas) · `server_time`: `last_reliable_date = max(actual, server_time)` (monótona) · matriz de
módulos: de `entitlements.modules` del paquete firmado (objeto módulo → bool); si no hay, vacía y
denegación por defecto · idempotencia diaria del cliente: se conserva (antes de contactar) · fallo tras
consumir: el cliente pide otro desafío en el siguiente intento explícito; sin reintentos ocultos ·
limpieza: perezosa y acotada al emitir desafíos (vencidos hace > 1 h); sin planificador ni Redis ·
límite de tasa: no hay mecanismo central reutilizable → deuda `CENTRAL-SYNC-SIN-LIMITE-DE-TASA` ·
HTTPS: en `prod` del cliente, `server_url` sin `https://` → 422 `CENTRAL_URL_INSECURE` (al configurar y
al sincronizar) · E2E: la corrida levanta la autoridad real (`uvicorn central_authority.main:app`,
puerto 8010, base SQLite efímera de la corrida, clave sintética) y el cliente sincroniza contra ella
por HTTP local; proyecto Playwright `licencia-sync` tras `licencia-revision` · DeepSeek: solo la matriz
pura del sobre.

## 5. `/speckit.plan` y compuerta

Contrato puro `app/core/sync_auth_contract.py` (compartido; la autoridad puede importarlo, CLA-14 lo
admite; `Dockerfile.central` lo copia) → modelo y migración central `0002_cla_sync_auth` (huella con
*backfill* desde el PEM guardado y unicidad; tabla de desafíos) → `central_authority/service.py`
(`register_installation` con huella y unicidad; `create_sync_challenge`; `authenticate_sync`;
`select_current_issuance`; `sync_response`) → `main.py` (`POST /v1/license/sync/challenge`, `POST
/v1/license/sync`) → cliente (`SyncTransport`, `UrllibSyncTransport`, `sync_license` autenticado e
importando por `import_license`; ruta sin `require_write_allowed`; HTTPS en prod) → ayudante de
exportación → pruebas → E2E → documentos.

**Compuerta: PASS.** HEAD y rama verificados; orquestación operativa; dueñas resueltas; contrato físico
del sync localizado; clave de la instalación y registro central inspeccionados; tres autoridades
separadas; protocolo, sobre, orden de verificación y consumo atómico definidos; esquema cliente 0;
migración central definida con conservación de filas; compuertas locales, ancla, identidad,
anti-retroceso, estado público, diagnóstico y health preservados; rotaciones, mTLS y reverificación
excluidas; fiscal fuera; pruebas y mutaciones definidas; `.pyc` purgado; `MATERIAL OQ = 0`; `UNKNOWN =
0`; trazabilidad 100 %.

## 6. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | FR-010 | EXECUTOR · MODEL | SEC | EGRESS |
|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, Spec Kit | — | CLAUDE | YES | n-a |
| T02 | Contrato puro del sobre | 379–387, 424–426 | CLAUDE | **YES** | n-a |
| T03 | Central: modelo, migración `0002`, huella y unicidad, desafíos, autenticación, selección, rutas, TTL | 367–399, 405–407, 420–423, 427–429 | CLAUDE | **YES** | n-a |
| T04 | Cliente: transporte, `sync_license` autenticado, importación, HTTPS, ruta sin bloqueo de escritura | 400–415 | CLAUDE | **YES** | n-a |
| T05 | Pruebas puras del sobre (vectores de Claude) | 379–385, 424–426 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES |
| T06 | Pruebas de la autoridad (SQLite+PG), carrera de consumo (PG), migración con filas previas (PG) | 367–399, 405–407, 420–423 | CLAUDE | **YES** | n-a |
| T07 | Pruebas del cliente con la autoridad real en proceso (TestClient) y adaptación de `test_licensing_central.py` | 400–415 | CLAUDE | **YES** | n-a |
| T08 | Ayudante de exportación de la clave pública; `Dockerfile.central`; CLA-14/15; contratos y README | 367, 424 | CLAUDE | YES | n-a |
| T09 | E2E: autoridad real en la corrida, proyecto `licencia-sync`; mutaciones; suites; docs; Git | 413, 423 | CLAUDE | NO | n-a |

`analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; huérfanos 0;
`MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %. **Autorización de `implement`:** la del encargo.

## 7. Implementación (T02–T04, T08)

- **Contrato puro compartido** `app/core/sync_auth_contract.py`: `PROTOCOL_VERSION = 1`, destinos y
  cabeceras del protocolo, `new_nonce` (256 bits), `nonce_digest`, `body_sha256`, `canonical_body`,
  `build_envelope` (método en mayúsculas; destino sin consulta ni fragmento; hash hex minúsculo; campos
  sin espacios), `envelope_bytes` (siete campos exactos, JSON ordenado y sin espacios),
  `sign_envelope`/`verify_envelope`, `public_key_fingerprint` (SHA-256 del DER SPKI) y
  `public_key_pem_from_private`. La autoridad puede importarlo (CLA-14 lo admite junto a
  `license_contract`) y `Dockerfile.central` lo copia.
- **Autoridad**: `Installation.public_key_fingerprint` único; `SyncChallenge` (`cla_sync_challenges`, FK
  anulable, resumen del nonce, índices por instalación y caducidad); migración `0002_cla_sync_auth`
  con *backfill* de la huella desde el PEM guardado (sin generar claves, sin enrolar nada) y detención si
  dos filas previas compartieran clave; `register_installation` rechaza `INSTALLATION_KEY_ALREADY_BOUND`;
  `create_sync_challenge` (respuesta igual para desconocidas; limpieza perezosa de lo vencido hace > 1 h);
  `authenticate_sync` (orden de §4; firma inválida no consume; consumo atómico con `UPDATE … WHERE
  consumed_at IS NULL AND expires_at > now`, `rowcount == 1`, **confirmado antes de seguir**: un desafío
  consumido no resucita aunque falle lo que viene después); `select_current_issuance` (período, luego
  `revision`); `sync_response` (identidad del cuerpo = sobre; artefacto exacto o `NO_LICENSE`);
  auditoría `SYNC_CHALLENGE`/`SYNC`. `main.py` expone `POST /v1/license/sync/challenge` y `POST
  /v1/license/sync` sobre los bytes crudos. TTL `KONTROL_CENTRAL_SYNC_CHALLENGE_TTL_SECONDS` (120 s).
  Los verbos SQL se importan con alias privado para que el libro siga sin operación pública de edición
  (CLA-08).
- **Cliente**: `SyncTransport` (protocolo `challenge`/`sync`), `UrllibSyncTransport` (4xx →
  `CentralSyncRejected`), `_installation_private_key` (cargador canónico), `_exigir_https_en_produccion`
  (al configurar y al sincronizar). `sync_license(db, *, transport, actor)`: idempotencia diaria antes de
  contactar; cuerpo serializado una vez, hasheado, sobre firmado, mismos bytes enviados; sin retroceso;
  lo recibido pasa por `import_license` (`source="CENTRAL"`); `server_time` → `last_reliable_date`
  monótono; matriz de módulos desde `entitlements.modules` del paquete firmado (objeto o lista); corridas
  `FAILED` con el código del fallo y eventos `LICENSE_SYNC_FAILED`/`LICENSE_SYNC_REJECTED`/`LICENSE_SYNCED`.
  Ruta `POST /licensing/sync` sin `require_write_allowed` y exenta en `LicenseMiddleware`: la renovación
  en `READ_ONLY` ya no queda bloqueada (hallazgo: el bloqueo estaba en dos sitios).
- **Ayudante local** `scripts/clave_publica_instalacion.py` (PEM público y huella; nunca la privada).
- **Emisor de licencias**: sin cambios en la asignación de `revision`. **Esquema del cliente: 0.**
  **Frontend de producto: 0.**

## 8. QA y pruebas (T05–T07, T09)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_sync_auth_contract.py` (DeepSeek T05, `AUDIT_PASS` a la primera) | SAC-01..14: normalización, rechazos del sobre, bytes canónicos exactos, firma/verificación, alteración de cada campo, versión, nonce, hash, cuerpo canónico, huella, constantes | puro |
| `tests/central/test_central_sync_auth.py` | SYNC-01..20: desafío mínimo y resumen del nonce; artefacto exacto verificado por el cliente; repetición → `USED`; caducado no resucita; nonce/desafío incorrectos; desafío de A no vale para B; cuerpo alterado o reserializado no vale y no consume; firma de otra clave o rota no consume; método/destino firmados; cinco versiones desconocidas; desconocida sin enumeración; clave aportada ignorada; identidad del cuerpo; `NO_LICENSE`; selección por período y revisión (no por fecha); sin cabeceras / cuerpo ilegible tras consumir; unicidad de clave y sin sustitución; sin fugas; limpieza perezosa; registros limpios | SQLite y PostgreSQL |
| `tests/central/test_central_sync_auth_pg.py` | SYNCPG-01: cuatro peticiones idénticas concurrentes × 4 rondas → exactamente una autentica; SYNCPG-02: migración `0002` sobre filas previas (huella calculada, unicidad en base, índices, bajada) | PostgreSQL |
| `tests/test_license_sync_client.py` | CSYNC-01..13 con la autoridad real en proceso: `NO_LICENSE`; licencia autenticada e importada; bytes exactos y sin clave privada; idempotencia sin contactar; fallo sin retroceso y desafío nuevo por intento; rechazo central anotado; artefacto ajeno o manipulado no entra aunque llegue autenticado; respuesta fuera de contrato; sesión + `license:create`; renovación en `READ_ONLY`; HTTPS en prod; sin clave privada falla cerrado antes de contactar; ayudante de exportación | SQLite y PostgreSQL |
| Adaptadas | `test_licensing_central.py` (transporte autenticado, `NO_LICENSE`, módulos desde el paquete firmado, `server_time` futuro), CLA-08 (alias privados), CLA-14 (segundo contrato puro), CLA-15 (sync existe y exige prueba), CLAPG-03 (cabeza `0002`), `test_e2ecorrida_14` (tercer proyecto) | — |
| E2E | `qa/e2e_corrida.py` migra y levanta la autoridad real (`uvicorn central_authority.main:app`, 8010, base SQLite efímera, clave sintética); proyecto `licencia-sync` tras `licencia-revision`; `e2e/licencia-sync.spec.ts` (E2E-SYNC-01..08) | PostgreSQL (cliente) + SQLite (autoridad) |

## 9. Mutaciones (`evidence/central-sync-auth/mutaciones-backend.txt`; purga de `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`)

M-01 una firma inválida consume el desafío · M-02 el nonce no se comprueba · M-03 la caducidad no se
comprueba · M-04 el consumo deja de ser atómico (PostgreSQL) · M-05 el hash del cuerpo no liga los bytes
recibidos · M-06 el destino no se comprueba · M-07 cualquier versión se acepta · M-08 el desafío de otra
instalación vale · M-09 la instalación del cuerpo no se compara · M-10 la misma clave puede vincularse a
otra instalación · M-11 el artefacto se elige por fecha de emisión · M-12 el cliente aplica lo recibido sin
pasar por la importación · M-13 el cliente hashea una serialización distinta de la que envía · M-14 HTTPS
deja de exigirse en prod · M-15 el sobre deja de ser determinista. **Primera pasada 14/15: M-04 sobrevivió** porque solo quitaba la condición del `UPDATE` y la comprobación previa bajo `FOR UPDATE` seguía rechazando la segunda petición (dos guardas independientes: mutante equivalente). Se rediseñó para quitar las dos y murió (`mutaciones-backend-m04-repeticion.txt`): **15/15 muertas**.

## 10. Resultados

| Gate | Resultado |
|---|---|
| Nuevas suites SQLite / PostgreSQL | SAC 14 + SYNC 20 + CSYNC 13 = **47** (SQLite) · + SYNCPG 2 = **49** (PostgreSQL); CLA, CLAPG, REVC, RACE y RROV en verde |
| Backend completo SQLite / PostgreSQL | **44 failed / 1295 passed / 1019 skipped** (42 de documentos sin `clamscan` + `test_dos_renovaciones_simultaneas…` y `test_concurrencia_de_codigo_resuelta_por_constraint`, intermitentes SQLite ya registrados; +49 nuevas) / **38 failed / 2293 passed / 27 skipped** (37 de documentos + `test_e2ecorrida_01`, que fija la lista de fases del lanzador y se adaptó a la fase «autoridad central»; después `tests/test_e2e_corrida.py` 14 passed; 0 regresiones) |
| `ruff check` · `mypy` | limpio · limpio |
| Frontend `typecheck` · `lint` · `vitest` · `build` | OK · OK · **459/459** · build OK (`frontend-gates.txt`) (cambio de producto 0) |
| E2E dirigido (`licencia-sync` sola, `--no-deps`, autoridad real en la corrida) | **1 passed** (E2E-SYNC-01..08, base `r20261007t211836…`, limpieza LIMPIA). Tres corridas previas enseñaron defectos de la propia suite y del lanzador, no del protocolo: año contractual sobre `period_end`, patrón de fuga que incluía el cuerpo v1, expectativa de idempotencia tras cambiar la licencia, y una autoridad huérfana en 8010 porque la limpieza no la detenía (ahora comprueba el puerto y la detiene) |
| E2E global (`chromium` → `licencia-revision` → `licencia-sync`) | **230 passed, 0 failed, 40 skipped** (228 + linaje + sync; base `r20261007t213539…`, limpieza LIMPIA, puerto 8010 libre al cierre) |
| Bases de corrida al cierre | 0 |

## 11. Deudas y veredicto

| Deuda | Estado |
|---|---|
| `CENTRAL-SYNC-AUTHORITY-UNDEFINED` | **CLOSED / CONVERGED** (2026-10-07) |
| `CENTRAL-SYNC-SIN-LIMITE-DE-TASA` | **NUEVA — OPEN** (endurecimiento operativo del endpoint de desafío; el diseño no se debilitó para evitarla) |
| `LICENCIA-SIN-ROTACION-DE-CLAVE`, `LICENCIA-ESTADO-SIN-REVERIFICAR`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `INSTALACION-KEY-REFERENCE-120` y el resto del encargo | OPEN, sin cambio |
| D0-06 | CLOSED / IMPLEMENTED (sin cambio); ADR-D0-006 anota el sync implementado |
| Fiscal / homologación (D0-07, SPEC039–043, SPEC056) | no se toca |

`MASTER56`: 56 filas, sin cambio. `NEXT SPEC = 029`, no iniciada. Orquestación: 9 tareas, `CLAUDE_ONLY`
8, `DEEPSEEK_ELIGIBLE` 1 (T05: 1 llamada `deepseek-v4-flash`, 2274/3247 tokens, $0.00121, `AUDIT_PASS`,
0 reintentos, 0 rechazos; egress: solo el contrato puro y una suite hermana; claves sintéticas generadas en
la prueba). Esquema del cliente 0; migración central `0002` (una cabeza); emisor sin cambios en la
asignación de `revision`.

## 12. `analyze` final y trazabilidad

`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; huérfanos 0; `MATERIAL OQ = 0`; `UNKNOWN = 0`;
trazabilidad 100 %:

| FR-010 | Código | Prueba | Mutación |
|---|---|---|---|
| 367–373 | `register_installation` (huella, unicidad, conflicto), CLI; sin ruta de autorregistro | SYNC-11, 12, 17; SYNCPG-02; CSYNC-13 | M-10 |
| 374–378 | `create_sync_challenge`, `SyncChallenge`, TTL | SYNC-01, 04, 19; SYNCPG-01 | M-03 |
| 379–387 | `sync_auth_contract` (sobre, bytes, firma); `authenticate_sync` recomputa el hash con los bytes recibidos y usa la clave del registro | SAC-01..14; SYNC-02, 07, 08, 09, 12 | M-05, M-07, M-15 |
| 388–392 | `authenticate_sync` (orden), consumo atómico confirmado | SYNC-03, 04, 07, 08, 16; SYNCPG-01 | M-01, M-02, M-04 |
| 393–399 | desafío por instalación; identidad del cuerpo; versión; método/destino | SYNC-06, 09, 10, 13; SAC-07 | M-06, M-08, M-09 |
| 400–404 | `sync_license`: desafío nuevo, sin retroceso, clave canónica, la privada no viaja | CSYNC-03, 05, 06, 12 | M-13 |
| 405–407 | `select_current_issuance`, `sync_response` | SYNC-02, 13, 14, 15 | M-09, M-11 |
| 408–412 | `import_license` tras el sync; ruta sin bloqueo de escritura; exención en el middleware | CSYNC-02, 07, 08, 09, 10 | M-12 |
| 413–415 | `_exigir_https_en_produccion` | CSYNC-11 | M-14 |
| 416–419 | sin cambio en `kid`/claves | CLA-05..07, REVC | — |
| 420–423 | `0002_cla_sync_auth`; estado en la base; carrera PG | SYNCPG-01, 02; CLAPG-03 | M-04 |
| 424–426 | `contracts/health-and-sync.md`; `canonical_body` una vez | SAC-04, 12; CSYNC-03 | M-13, M-15 |
| 427–429 | respuestas `{code, message}`; desafío mínimo; registros | SYNC-01, 11, 18, 20 | — |
| 430–434 | sin cambio en emisor, anti-retroceso, status, diagnóstico, health | CLA, REVC, CSYNC-08; E2E-SYNC 8 | — |
| 435–436 | hoja de ruta | §11 | — |
