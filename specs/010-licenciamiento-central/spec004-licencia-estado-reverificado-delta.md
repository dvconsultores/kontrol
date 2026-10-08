# SPEC 004 · DELTA DIRIGIDO — REVERIFICACIÓN DEL ESTADO DE LICENCIA PERSISTIDO

> Iniciado el 2026-10-07. Dueño: **Spec 004 global — Licenciamiento** (`010-licenciamiento-central` +
> `001-fundacion`); apoyos 001 (ciclo de vida de la aplicación), 002 (la sesión sigue accesible), 052/053
> (restauración = arranque posterior), 054 (QA). Deuda: `LICENCIA-ESTADO-SIN-REVERIFICAR`. MASTER57,
> 057, D0-07, 039–043 y 056 no se tocan.
>
> **Objetivo:** que el artefacto de licencia **vigente y persistido** se reverifique contra la política de
> confianza **actual** (conjunto `kid → clave`, firma del propietario, identidad de instalación,
> integridad del artefacto) al arrancar y antes de autorizar escrituras de negocio, sin reimportar, sin
> tocar período, `revision` ni historial, sin romper sesión ni recuperación, y con el estado operativo
> que ya define el contrato.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `4e1b115` / **`4e1b115`** / `4e1b115` / `develop` / limpio · `COMMITS_AFTER_4E1B115 = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END` · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| Dueñas | SPEC004 primaria; 001/002/052/053 solo donde su contrato ya interviene; 054 QA · `OWNER_IDENTITY_CONFLICT = 0` |
| Punteros | `NEXT TECHNICAL CYCLE = LICENCIA-ESTADO-SIN-REVERIFICAR` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Fuente contractual (W03) — DOC-07, leído íntegro

| Registro | DOC-07 |
|---|---|
| `DOC07_REVERIFY_REQUIREMENT` | §10.1 «La firma se verifica **en cada arranque** y antes de aplicar una licencia nueva»; §14.5 «En arranque: validar firma, instalación, fecha y derechos»; §4.2 «Verifica la licencia con la clave pública de KONTROL; calcula el modo actual con base en fechas contractuales y fecha confiable» |
| `DOC07_TRIGGER` | Arranque del proceso (§10.1, §14.5) y restauración (§16.2: «arrancar en modo mantenimiento → validar identidad, licencia y última fecha confiable → sincronizar o importar paquete actual → abrir operación según modo real»); §15.1 «Base restaurada con licencia antigua → reconciliar con volumen y autoridad; no retroceder período» |
| `DOC07_EXPECTED_FAILURE_BEHAVIOR` | §10.1 «Una licencia alterada produce **SECURITY_SUSPENSION**, no READ_ONLY»; §5.2 «REVOKED o firma inválida → SECURITY_SUSPENSION»; §15.1 «Firma inválida → SECURITY_SUSPENSION y alerta; no aplicar paquete · Installation ID diferente → rechazar licencia · Edición manual de tablas → la firma y el hash no coinciden; no conceder acceso» |
| `DOC07_RECOVERY_PATH` | §9.1/§9.2: en modos bloqueados siguen permitidos inicio de sesión, consulta, carga de comprobante y «endpoints expresamente permitidos de renovación y seguridad»; §16.2 paso 4 «sincronizar o importar paquete actual»; código: `MODE_TRANSITIONS` «READ_ONLY / SECURITY_SUSPENSION son terminales: solo se sale re-importando», rutas `/api/v1/license/*` y `/licensing/sync` exentas del bloqueo |

**Compuertas materiales:** `INVALID_CURRENT_POLICY = PROVEN` (SECURITY_SUSPENSION, modo existente que el
middleware ya bloquea y del que se sale reimportando) · `LICENSE_STATE_AUTHORITY = PROVEN` para lo
criptográfico: el **artefacto firmado** (`license_artifacts`: carga, firma, hash, `kid`) es la fuente;
`license_states` es derivado (§11.2: «licencia vigente, modo calculado, última verificación y fecha
confiable»; el código lo escribe desde la carga parseada y recalcula el modo en lectura) ·
`RECOVERY_PATH = PROVEN` (sesión, lectura, importación, sync) · `STARTUP_GATING_POINT = PROVEN`: el
`lifespan` de FastAPI corre antes de servir y, además, el middleware consulta `current_mode` en cada
escritura, con lo que ninguna petición puede adelantarse al resultado · `DOC07_REVERIFY_REQUIREMENT =
PROVEN`. **Límite declarado (no inventado):** DOC-07 no define reconstruir el estado derivado desde el
artefacto ni tratar una diferencia de **fechas/derechos** entre ambos como manipulación (los hitos se
recalculan en lectura y las suites simulan el paso del tiempo escribiendo esas fechas, por diseño). Por
eso `ARTIFACT_STATE_MISMATCH` se limita al **vínculo e integridad**: el estado señala una licencia sin
artefacto guardado, el artefacto no coincide con su propio hash, o su `license_id` no es el del estado.

## 3. Inventario (W04–W14)

| Registro | Hallazgo |
|---|---|
| `CURRENT_ARTIFACT_STORAGE` | `LicenseArtifact.payload` (JSON firmado tal cual) · `CURRENT_SIGNATURE_STORAGE` `signature_hex` · `payload_hash` · `CURRENT_KID_STORAGE` `kid` (y dentro de la carga firmada) · el vigente es la última fila aceptada de `state.license_id` (regla de la `revision`) |
| `CURRENT_STATE_STORAGE` / `CURRENT_DERIVED_FIELDS` | `LicenseState`: `license_id`, `mode` (caché), período e hitos (UTC), `entitlements`, `minimum_version`, `kid`, `verified_at`, `last_reliable_date` |
| Ciclo de vida | `create_app()` sin `lifespan`; `LicenseMiddleware(get_mode=current_mode)` en cada método de escritura salvo prefijos exentos (`/api/v1/license/`, `/licensing/sync`, setup, auth, health); `require_write_allowed` en rutas concretas; `current_mode` → `get_status` → `compute_mode(fechas, reloj, fecha confiable)` y persiste el modo si cambió |
| Sesión y recuperación | login exento; `import_license`/`sync_license` exentos y con `license:create`; `SECURITY_SUSPENSION` terminal hasta reimportar |
| Verificadores | `trust_anchor.load_trust_set` + `resolve_trusted_owner_key` (por `kid` firmado) · `verify_license_signature` · identidad = `installation_uuid` · `parse_license_payload` · `payload_hash` |
| Reloj | `_now()` UTC técnico; `compute_mode` con `_as_utc`; instantes del estado normalizados a UTC desde `ac27f59`; `America/Caracas` solo en los hitos firmados |
| Health | `/health/live` proceso vivo; `/health/ready` solo base. Sin evidencia para cambiarlos: se preservan |
| Diagnóstico | `license:view`; bloque `license` con `activated`, `mode`, `period_end`: admite una **clase** de verificación, sin material |
| Restauración | `scripts/restore.sh` externo → arranque posterior: la reverificación de arranque la cubre; no se duplica |
| Multiproceso | `uvicorn` puede correr varios trabajadores; la reverificación es pura, barata e idempotente por proceso; lo único persistido es el modo caché (igual que hoy) y un evento con deduplicación |

## 4. `/speckit.specify` — FR-010-488..537 (= FR-REVERIFY-001..050)

Arranque: determinar si hay artefacto vigente; sin él, `PENDING`/arranque inicial intacto; con él,
reverificar **antes** de autorizar escrituras normales, partiendo del artefacto firmado persistido:
`kid` firmado → clave exacta del conjunto **actual** (desconocido/retirado → falla; sin probar otras) →
firma del propietario → identidad de instalación → integridad del artefacto y vínculo con el estado.
Sin crear importación, sin tocar `revision`, período ni artefacto, sin refirmar; política de confianza
**actual**, no la del momento de importar (el retiro de una clave se observa al arrancar). Artefacto
inválido → no concede autoridad de escritura (`SECURITY_SUSPENSION`), pero sesión, lectura e
importación/sync con `license:create` siguen; válido pero vencido → `READ_ONLY` por fechas, nunca
«firma inválida»; `America/Caracas`, UTC y sin TZ del anfitrión; restauración + arranque = misma
reverificación; status público mínimo; diagnóstico protegido; health sin internos; sync, rotación,
anti-retroceso, renovación en `READ_ONLY` y setup sin cambio; esquema cliente 0; central 0; el artefacto
nunca se borra; fallo auditable sin material; determinista e idempotente; multiproceso sin estado
inconsistente; sin reverificación periódica. MASTER57, 057 y puntero sin cambio.

## 5. `/speckit.clarify` — 50 preguntas, `MATERIAL OQ = 0`

1 §2 · 2–6, 18–25 §3 · 7–8 sin hooks: se añade `lifespan` · 9 no hay «inicialización» del servicio: todo
es por petición · 10–12 middleware + `require_write_allowed` + `current_mode` · 13–15 `PENDING` sin
estado; `initialize` crea admin antes de licencia; login exento · 16–17 import/sync exentos con
`license:create` · 26–27 health: sin cambio · 28 status: solo `mode` y `license_url` · 29 diagnóstico:
clase de verificación · 30 actor del sistema: evento sin `user_id` (`source` «SYSTEM») · 31–32 restaurar
= arrancar · 33 varios trabajadores: por proceso, puro · 34–35 persistencia: solo el modo caché que ya
persiste `get_status` (mecanismo existente D) y un evento deduplicado; el artefacto no se toca · 36
política: §2 · 37 sin estado → `NO_CURRENT_LICENSE` → `PENDING` · 38 `MALFORMED_ARTIFACT` →
suspensión · 39 `KID_UNKNOWN`/`KID_MISSING` → suspensión · 40 `SIGNATURE_INVALID` → suspensión · 41
`INSTALLATION_MISMATCH` → suspensión · 42 `ARTIFACT_STATE_MISMATCH` (vínculo/integridad) → suspensión; las
fechas no (§2) · 43 válido + fechas vencidas → `READ_ONLY` · 44 carrera: `lifespan` antes de servir y
gate por petición sin caché (una firma Ed25519 por escritura: barata, pura, sin estado compartido); un
import/sync que acepta un artefacto nuevo lo convierte en el vigente y la siguiente petición ya lo
reverifica → recuperación inmediata · 45 esquema 0 · 46 central 0 · 47–49
pruebas con «reinicio» (app nueva), restauración (copia de filas a una base nueva) y recuperación con la
autoridad real en proceso; E2E global de regresión (el E2E no reinicia el backend) · 50 DeepSeek: matriz
pura del clasificador.

## 6. `/speckit.plan`, compuerta, checklist, tareas

Núcleo puro `app/core/license_reverification.py`: `evaluate_current_artifact(payload, signature_hex,
stored_hash, installation_uuid, state_license_id, trust_set) → (status, reason)`. Servicio
`licensing/reverification.py`: carga estado + artefacto vigente, conjunto actual, evalúa (sin caché: ver
§5 Q44), anota `LICENSE_STATE_REVERIFICATION_FAILED` una vez por fallo distinto.
Integración: `get_status`/`current_mode` aplican `SECURITY_SUSPENSION` si el vigente no verifica;
`lifespan` en `create_app` ejecuta la reverificación al arrancar (sin tumbar el proceso si la base no
responde: el gate por petición vuelve a intentarlo); diagnóstico expone la clase. **Compuerta G01–G40:
PASS.** Tareas: T01 inventario/Spec Kit · T02 núcleo puro · T03 servicio + integración + `lifespan` ·
T04 **DeepSeek** matriz pura · T05 pruebas hostiles (manipulación, otra instalación, `kid` retirado,
vínculo roto, sin licencia, vencida, restauración, reinicios repetidos, recuperación por import y por
sync con la autoridad real) · T06 mutaciones, suites, E2E global, docs, Git. `analyze` previo:
`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0, `MATERIAL OQ = 0`, `UNKNOWN = 0`,
trazabilidad 100 %. **Autorización de `implement`:** la del encargo.

## 7. Implementación (T02, T03)

- **Núcleo puro** · `app/core/license_reverification.py`: clases `NO_CURRENT_LICENSE`, `MALFORMED_ARTIFACT`,
  `KID_MISSING`, `KID_UNKNOWN`, `SIGNATURE_INVALID`, `INSTALLATION_MISMATCH`, `ARTIFACT_STATE_MISMATCH`,
  `TRUST_SET_INVALID`, `VALID`; `FAILURES` (todo lo que no es `VALID` ni `NO_CURRENT_LICENSE`);
  `Reverification(status, reason, license_id, kid)` inmutable; `evaluate_current_artifact(payload,
  signature_hex, stored_hash, installation_uuid, state_license_id, trust_set)` en este orden: artefacto
  legible → hash almacenado = recalculado → `license_id` del artefacto = del estado → `kid` firmado →
  clave **exacta** del conjunto actual (`resolve_trusted_owner_key`; nunca prueba otras) → firma del
  propietario → contrato (`parse_license_payload`) → identidad de la instalación. Sin SQLAlchemy, sin
  settings, sin red; la fuente es el artefacto, el estado solo aporta el vínculo (§2: fechas y derechos
  no se comparan).
- **Servicio** · `app/modules/licensing/reverification.py`: `artefacto_vigente` (último aceptado de la
  licencia que el estado señala, misma regla que la reemisión por `revision`); `reverificar_vigente(db,
  installation, state)` (sin estado → `NO_CURRENT_LICENSE`; sin artefacto → `ARTIFACT_STATE_MISMATCH`
  «artifact_missing»; conjunto de confianza actual desde `get_settings()`, `TrustAnchorError` →
  `TRUST_SET_INVALID`; evalúa; en fallo anota `LICENSE_STATE_REVERIFICATION_FAILED` con
  `{license_id, kid, status, reason}`, `user_id` nulo, `source` «SYSTEM», **deduplicado** si el último
  evento de ese tipo trae el mismo detalle; un `warning` en el log sin material); `reverificar_al_arrancar
  (session_factory)` una vez por proceso, sin tumbar el proceso si la base no responde (`ultimo_arranque`
  queda `None` y el gate por petición decide). Nada se escribe en el artefacto; no hay caché (§5 Q44).
- **Integración** · `licensing/service.py::get_status`: tras `compute_mode`, si la reverificación del
  vigente está en `FAILURES` el modo es `SECURITY_SUSPENSION` (se persiste por el mecanismo existente de
  caché del modo); `verification` sale en el estado interno → `/license/detail` (con sesión y
  `license:view`) y bloque `license.verification` del diagnóstico (`system/api.py`). `current_mode`
  (middleware) y `require_write_allowed` (rutas) leen `get_status`, así que **toda escritura de negocio
  pasa por la reverificación**; import, sync, auth, setup y health siguen exentos: son la recuperación.
  `app/main.py`: `create_app(lifespan=_lifespan)` ejecuta `reverificar_al_arrancar(get_session_factory())`
  antes de servir. `/license/status` sigue siendo `mode` + `license_url` (modelo `extra="forbid"`).
- **Pruebas adaptadas (no producto)** · doce mundos de prueba importaban una licencia con un ancla
  temporal y después la quitaban del entorno (`os.environ.pop`), dejando el conjunto de confianza
  vacío: eso es exactamente el hueco que se cierra (`TRUST_SET_INVALID` → suspensión), así que ahora
  conservan el ancla configurada (`audit_world`, `approvals_api`, `audit_integration`,
  `audit_tenant_isolation`, `homologation`, `idempotency_concurrency`, `license_import_access`,
  `licensing_central`, `password_reset`, `process_flows`, `qa_fixes`, `security_integration`,
  `services`); `test_license_period_rollback._simular_licencia_antigua` escribía un estado sin artefacto
  (vínculo roto): ahora inserta el artefacto firmado y coherente antes de envejecer el estado.
- **Lo que no cambia** · esquema del cliente **0** (sin columna `verification`), central **0**, frontend
  **0**, fechas de licencia, `America/Caracas`, criptografía, período/`revision`/anti-retroceso, sync
  autenticado, setup y login. Sin reverificación periódica, sin Redis, sin trabajadores.

## 8. Pruebas y mutaciones (T04, T05, T06)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_license_reverification_rules.py` (DeepSeek T04, `AUDIT_PASS` a la primera) | RVR-01..13: válido; artefacto ilegible (carga no mapa, firma nula); hash distinto y carga alterada tras firmar; `license_id` ≠ estado; `kid` ausente/no textual; `kid` desconocido; firma de **otra** clave de confianza (`kid` A, firma B → inválida); firmas inválidas; contrato roto (`period_start` ausente, `revision` 0); otra instalación; orden (integridad antes que `kid`, `kid` antes que identidad); conjuntos y autoridad; determinismo y no mutación | puro |
| `tests/test_license_state_reverification.py` | REVST-01..15: sin licencia → `PENDING`, setup y sesión siguen, diagnóstico `NO_CURRENT_LICENSE`; válida → arranque `VALID`, escritura 200, detalle; válida y vencida → `READ_ONLY`, 0 eventos; **firma manipulada en la base + reinicio** → `SECURITY_SUSPENSION`, escritura 423 `LICENSE_SECURITY_SUSPENSION` sin material, sesión y lectura siguen, evento `SYSTEM` sin `user_id` con solo `{license_id, kid, status, reason}`, artefacto intacto (no se borra ni se repara), restaurado → `VALID`; **tres reinicios con el mismo fallo → cero eventos nuevos**; carga alterada con firma intacta → `payload_hash`; artefacto de otra instalación bien firmado → `INSTALLATION_MISMATCH`; estado que señala una licencia sin artefacto → `artifact_missing`; **retirada A** → `KID_UNKNOWN` + suspensión; **recuperación por sync autenticado** con la autoridad real en proceso firmando con B (la configuración central es escritura bloqueada; `/licensing/sync` exenta) → `FULL_ACCESS`, vigente `kid` B, reinicio `VALID`; **restauración** (instalación, estado y artefacto copiados a una base nueva) con confianza solo A → `KID_UNKNOWN`, con A+B → `VALID`; base caída al arrancar → el proceso no cae, `ultimo_arranque` `None`, el gate decide; cinco reverificaciones → un resultado, artefacto byte a byte igual; status público solo `mode`+`license_url`, `/health/live` idéntico, `/health/ready` sin `verification`, diagnóstico 401 sin sesión y solo la clase con ella, **esquema sin columna**; conjunto de confianza roto (JSON inválido) → `TRUST_SET_INVALID` + suspensión, lo público sin el porqué | SQLite y PostgreSQL |
| Regresión dirigida | `test_license_access`, `test_process_flows`, `test_licensing_central`, `test_audit_integration`, `test_idempotency_concurrency`, `test_password_reset`, `test_approvals_api`, `test_security_integration`, `test_audit_tenant_isolation`, `test_homologation`, `test_qa_fixes`, `test_services`, `test_license_import_access`, `test_license_trust_anchor`, `test_license_period_rollback`, `test_license_key_rotation`, `test_license_revision_client`, `test_license_sync_client`: **279 passed** tras adaptar los mundos (§7) | SQLite |
| E2E | regresión global (el backend no se reinicia dentro del E2E; la reverificación de arranque ya corre en cada arranque de la corrida) | PostgreSQL + autoridad real |

**Mutaciones** (`evidence/licencia-estado-reverificado/mutaciones-backend.txt`, purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`, GOOD → PASS 35/35 antes de mutar): M-01 la firma no se comprueba · M-02 se
prueban todas las claves en vez de la del `kid` · M-03 `kid` desconocido cae a la primera clave · M-04 la
identidad de la instalación no se comprueba · M-05 la integridad (hash) no se comprueba · M-06 el vínculo
`license_id` no se comprueba · M-07 un estado sin artefacto se da por válido · M-08 un conjunto de
confianza inválido se da por válido · M-09 el gate no se aplica al modo · M-10 `KID_UNKNOWN` deja de ser
fallo · M-11 el arranque tumba el proceso si la base no responde · M-12 el evento se repite sin
deduplicar · M-13 el `lifespan` no reverifica. Resultado: **13/13 muertas**, RESTORED → PASS en las trece.

## 9. Resultados

| Gate | Resultado |
|---|---|
| Nuevas suites SQLite / PostgreSQL | RVR 20 + REVST 15 = **35** (SQLite) · ídem PostgreSQL (`34` en la primera pasada PG antes de REVST-15; 35 tras añadirla); regresión dirigida de 18 suites de licencia, sesión, auditoría y flujos: **279 passed** |
| Backend completo SQLite / PostgreSQL (`backend-sqlite-completo.txt`, `backend-postgres-completo.txt`) | **44 failed / 1368 passed / 1019 skipped** = 42 de documentos sin `clamscan` + el intermitente SQLite de `test_warehouse_structure` ya registrado + `test_sys_05` (contrato del diagnóstico: el bloque `license` gana `verification`; adaptado y verde en los dos motores, `regresion-test-system-access.txt` 14/14) / **38 failed / 2366 passed / 27 skipped** = línea base exacta de documentos (35 + 2 de `n9_integrity`) + ese mismo `test_sys_05`. **0 regresiones** una vez adaptado; +35 pruebas nuevas en cada motor |
| `ruff check app tests` · `mypy` (módulos tocados) | limpio · limpio (`app/main.py` arrastra 154 errores preexistentes de 18 ficheros, idénticos en `HEAD`) |
| Frontend `typecheck` · `lint` · `vitest` · `build` (`frontend-gates.txt`) | OK · OK · **459/459** · OK (cambio de producto **0**) |
| E2E global (`chromium` → `licencia-revision` → `licencia-sync` → `licencia-rotacion`; `e2e-global.txt`) | **231 passed, 0 failed, 40 skipped**; base `r20261008t023010…`, limpieza LIMPIA, autoridad real en 8010 durante la corrida; puertos 8000/8010/5173 libres al cierre |
| Bases de corrida al cierre | **0** |
| Esquema cliente / central / frontend de producto | **0 / 0 / 0** |

## 10. Deudas, veredicto y trazabilidad

| Deuda | Estado |
|---|---|
| `LICENCIA-ESTADO-SIN-REVERIFICAR` | **CLOSED / CONVERGED** (2026-10-07) |
| Límite declarado | fechas y derechos del estado derivado no se comparan con el artefacto (§2): el contrato no define reconstruir el estado y los mundos de prueba lo envejecen a propósito; si un día se quisiera, es un delta nuevo con decisión de la dueña, no una ampliación silenciosa |
| `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` y el resto del encargo | OPEN, sin cambio |
| Punteros | `NEXT TECHNICAL CYCLE` ejecutado · `NEXT MASTER SPEC = NOT YET PRIORITIZED` (sin cambio) |
| MASTER57 · SPEC057 · D0-07 · 039–043 · 056 | sin cambio (57; `PLANNED / NOT STARTED`; `NARROWED`; bloqueadas por validación; validación fiscal y liberación) |

Orquestación: 6 tareas, `CLAUDE_ONLY` 5, `DEEPSEEK_ELIGIBLE` 1 (T04: 1 llamada `deepseek-v4-flash`,
3237/3055 tokens, $0.001291, `AUDIT_PASS` a la primera, 0 reintentos, 0 parches rechazados; egress:
solo la firma de `evaluate_current_artifact`, las constantes de clase y claves sintéticas generadas en
la propia prueba — `ENV_FILES=0 REAL_PRIVATE_KEYS=0 REAL_PUBLIC_KEYS=0 REAL_LICENSES=0 REAL_SIGNATURES=0
REAL_INSTALLATION_IDS=0 REAL_DB_URLS=0 TOKENS=0 PASSWORDS=0 REAL_PII=0`). Todo lo demás (núcleo,
servicio, integración, `lifespan`, pruebas hostiles, mutaciones, adaptación de mundos, documentos, Git)
lo hizo Claude. `analyze` final: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; huérfanos 0;
`MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %:

| FR | Dónde | Prueba |
|---|---|---|
| 488–492 arranque: hay/no hay vigente; sin él `PENDING` intacto; con él reverificar antes de autorizar | `reverificar_al_arrancar`, `_lifespan`, `get_status` | REVST-01, 02, 12; M-13 |
| 493–499 `kid` firmado → clave exacta del conjunto actual; retirada → falla; nunca otras | `evaluate_current_artifact` + `resolve_trusted_owner_key` | RVR-05..07, REVST-09, 11; M-02, M-03, M-10 |
| 500–503 firma del propietario; identidad; integridad; vínculo | núcleo | RVR-01..04, 08, 10, 11; REVST-04, 06, 07, 08; M-01, M-04..07 |
| 504–508 no reimportar, no tocar `revision`/período/artefacto, no refirmar, política actual | núcleo puro sin escritura; `_vigente` intacto | REVST-04 (artefacto intacto), 13; RVR-13 |
| 509–515 fallo → sin autoridad de escritura (`SECURITY_SUSPENSION`); sesión, lectura, import y sync siguen | `get_status`, middleware y `require_write_allowed` existentes; exenciones existentes | REVST-04, 05, 09, 10, 15; M-09 |
| 516–518 válida vencida → `READ_ONLY`, nunca «firma inválida» | `compute_mode` primero; la reverificación no mira fechas | REVST-03 |
| 519–521 `America/Caracas`, UTC, sin TZ del anfitrión | sin cambio (fechas no intervienen) | REVST-03 (hitos UTC) |
| 522–524 restauración + arranque = misma reverificación | mismo camino por petición y por arranque | REVST-11 |
| 525–528 status mínimo; diagnóstico protegido con la clase; health sin internos | `LicensePublicStatus` (`extra="forbid"`), `system/api.py` | REVST-01, 14, 15; SYS-05 adaptada |
| 529–531 sync, rotación, anti-retroceso, renovación en `READ_ONLY`, setup sin cambio | sin cambio | regresión dirigida 279 + KEYROT/REVC/CSYNC; E2E global |
| 532–533 esquema cliente 0; central 0 | sin modelos ni migraciones | REVST-14 (sin columna); `alembic` sin revisión nueva |
| 534 el artefacto nunca se borra ni se repara | ninguna escritura sobre `LicenseArtifact` | REVST-04, 13 |
| 535 fallo auditable sin material, deduplicado | `_anotar_fallo` | REVST-04, 05; M-12 |
| 536 determinista e idempotente; multiproceso sin estado compartido | núcleo puro, sin caché | REVST-13; RVR-13 |
| 537 sin reverificación periódica; base caída no tumba el arranque | `reverificar_al_arrancar` | REVST-12; M-11 |

**Veredicto: CONVERGED.**
