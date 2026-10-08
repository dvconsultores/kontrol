# SPEC 004 · DELTA DIRIGIDO — ROTACIÓN CONTROLADA DE LA CLAVE DE FIRMA DEL PROPIETARIO

> Iniciado el 2026-10-07. Dueño: **Spec 004 global — Licenciamiento** (`010-licenciamiento-central` +
> `001-fundacion`); componente central `central-authority/`; apoyo QA 054 y despliegue 052 (solo la
> documentación de la configuración externa). Deuda: `LICENCIA-SIN-ROTACION-DE-CLAVE`. MASTER57 se
> preserva; la 057 sigue `PLANNED / NOT STARTED`; la reconciliación fiscal no se toca.
>
> **Objetivo:** que el cliente mantenga un **conjunto de confianza** `kid → clave pública` y la autoridad
> un **conjunto de firma** `kid → clave privada` con **un solo `kid` activo**, para rotar A → B con
> solapamiento (R0 confianza A · R1 confianza A+B · R2 la autoridad firma con B · R3 reemisión bajo B ·
> R4 retirar A) sin distribuir privadas, sin confianza dinámica, sin que `kid` ordene nada y sin romper
> legacy ni el anti-retroceso.

## 1. Checkpoint, dueñas y decisión del puntero

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `5624769` / **`5624769`** / `5624769` / `develop` / limpio · `COMMITS_AFTER_5624769 = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END` · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` / central / QA / despliegue | SPEC004 / SPEC004 · Autoridad Central / SPEC054 / SPEC052 (documentación de configuración) · `OWNER_IDENTITY_CONFLICT = 0` |
| `NEXT-SPEC-POINTER-AMBIGUO` | **OWNER_DECIDED / CLOSED**: `NEXT SPEC = 029` deja de ser puntero operativo; se separan `NEXT TECHNICAL CYCLE = LICENCIA-SIN-ROTACION-DE-CLAVE` (este) y `NEXT MASTER SPEC = NOT YET PRIORITIZED` (018, 047, 048, 057 u otra: **no se elige aquí**). Actualización documental mínima en `next-spec-decision.md` y `master-57-reconciliation.md` |

## 2. Compuerta de descubrimiento — semántica de `kid` (W04–W09)

| Registro | Hallazgo físico |
|---|---|
| `CURRENT_KID_SOURCE` | Autoridad: `Settings.signing_kid` (`KONTROL_CENTRAL_SIGNING_KID`, por defecto `kontrol-lic-2026-01`), copiado al payload en `issue_license`; firmantes de QA lo escriben literal |
| `CURRENT_KID_FORMAT` | Etiqueta configurada (cadena libre), no huella ni UUID |
| `CURRENT_KID_SIGNED` | **Sí**: `payload["kid"]` forma parte del dict que `canonical_bytes` serializa y firma (`license_contract`); alterarlo invalida la firma |
| `CURRENT_KID_UNIQUENESS` | Un solo valor en Fase 1; la autoridad no verifica la relación `kid ↔ clave` (par por configuración) |
| `CURRENT_KID_SERVER_BINDING` | Por configuración: `signing_private_key_pem` + `signing_kid`; el libro guarda `kid` por emisión |
| `CURRENT_KID_CLIENT_USE` | `parse_license_payload` lo lee (`kid: str \| None`), `LicenseState.kid` lo guarda, `/license/detail` lo publica; **no participa** en la elección del ancla: `import_license` verifica contra la única `KONTROL_LICENSE_PUBLIC_KEY_PEM`. Existe `Settings.license_public_key_kid` (`kontrol-lic-2026-01`), sin uso |
| Contrato | DOC-07 §10.1: «Clave pública distribuida con KONTROL y **versionada mediante `kid`**»; §10.2: `kid` en el **contenido mínimo** del paquete; §15: «firma asimétrica y rotación de claves». Contrato central (`contracts/signed-license-package.md`): «identificador de la clave de firma» |
| Legacy sin `kid` | Fuera del contenido mínimo de DOC-07 §10.2. Todos los paquetes del repositorio (siembra, firmantes de QA, suites, emisor) llevan `kid`. Un paquete sin `kid` es un paquete fuera de contrato: se rechaza con código propio, no se inventa un `kid` por defecto |

**Compuertas:** `KID_SEMANTICS = PROVEN` (identidad de la clave de firma, por DOC-07 y por el contrato
central) · `KID_SIGNED = YES` · `LEGACY_TRUST_TRANSITION = PROVEN` (el par existente
`KONTROL_LICENSE_PUBLIC_KEY_PEM` + `KONTROL_LICENSE_PUBLIC_KEY_KID` es, de forma determinista, un
conjunto de confianza de **una** entrada bajo el contrato vigente; sin inventar semántica) ·
`PRIVATE_KEY_CUSTODY = PRESERVED`. Ningún `STOP` aplica.

## 3. `/speckit.specify` — FR-010-437..487 (= FR-KEYROT-001..051)

Cliente: conjunto de confianza externo `kid → pública` con `kid` canónico único; la clave se elige
**estrictamente** por el `kid` firmado; `kid` desconocido o ausente → rechazo; nunca se prueban todas
las claves; `kid` A con firma de B → rechazo (código de firma, sin decir qué otra clave verificaría); la
licencia no añade ni sustituye anclas; `kid` duplicado con otra clave o la misma clave bajo dos `kid`
→ error de configuración; transición del despliegue de una clave sin saltarse la identidad `kid`.
Autoridad: conjunto de firma externo `kid → privada`, **un `kid` activo explícito**; fallo cerrado si
el activo no tiene clave válida; cada emisión lleva el `kid` activo y se firma con su privada; sin
privadas en base ni en el cliente; prod no genera claves. Rotación: solapamiento A+B; A-firmadas
verifican mientras A esté en el conjunto; retirar A → una importación nueva con `kid` A se rechaza; el
estado ya persistido **no** se revalida (sigue `LICENCIA-ESTADO-SIN-REVERIFICAR`); período y `revision`
siguen mandando entre claves; `kid` no ordena; una reemisión por rotación recibe `revision` nueva; el
libro no se reescribe. Preservados: identidad de instalación, sesión + `license:create`, renovación en
`READ_ONLY`, sync autenticado, legacy y revisionadas, status mínimo, diagnóstico y health sin material;
esquema cliente 0; sin persistencia de privadas en central; agnóstico de proveedor; sin descarga
dinámica de anclas; runbook con pre-stage/activate/migrate/retire. MASTER57 y 057 sin cambio.

## 4. `/speckit.clarify` — 43 preguntas, `MATERIAL OQ = 0`

1–3, 11–14 §2 · 4 central: `KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM` + `KONTROL_CENTRAL_SIGNING_KID` · 5–7
cliente: `kid` guardado y publicado, sin uso en verificación; una sola `KONTROL_LICENSE_PUBLIC_KEY_PEM`
(+ `KONTROL_LICENSE_PUBLIC_KEY_KID` sin uso); cargador `trust_anchor.load_trust_anchor` · 8–9
cargador central `load_signing_key`, prod falla cerrado al cargar `Settings` · 10 QA: firmante por
corrida con `kid` literal `kontrol-lic-2026-01` · 15 mapa de una entrada: **sí**, con el par existente ·
16 conjunto de confianza: `KONTROL_LICENSE_TRUST_KEYS` (JSON `kid → PEM pública`, el tipo
`dict[str, str]` de pydantic-settings lo parsea) **unido** al par legacy; representación interna
`dict[kid, PEM normalizado]` · 17 conjunto de firma: `KONTROL_CENTRAL_SIGNING_KEYS` (JSON `kid → PEM
privada`) unido al par legacy · 18 `kid` activo: `KONTROL_CENTRAL_SIGNING_KID` (mismo nombre, misma
semántica: el `kid` que llevan las emisiones nuevas) · 19 `kid` duplicado con material distinto →
`TrustAnchorError("duplicate_kid")` / `SigningKeyError("duplicate_kid")`; igual material bajo el mismo
`kid` (el par legacy repetido en el JSON) se admite como la misma entrada · 20 misma clave bajo dos `kid`
→ `duplicate_key`: el contrato no define alias · 21 formato: PEM SPKI/PKCS8 Ed25519, lo demás `invalid`
· 22 arranque: cliente en `prod` exige un conjunto válido no vacío al cargar `Settings`; autoridad en
`prod` exige conjunto válido con el activo presente · 23–27 recarga: la configuración se lee al cargar
`Settings` (caché por proceso); la rotación es un redespliegue de configuración con reinicio; no hay ni
hace falta recarga en caliente · 28 misma período r1/A → r2/B: acepta (regla de `revision`) · 29 2027/r500/A
→ 2028/r1/B: acepta si B es de confianza · 30 anti-retroceso: intacto, `kid` no participa · 31 legacy:
igual, con su `kid` · 32 `READ_ONLY`: igual · 33 sync: independiente (dominio de claves de instalación)
· 34–36 status/diagnóstico/health: sin `kid` ni inventario de claves · 37 esquema: 0 (cliente y central)
· 38 despliegue: `.env.example`, `compose.central.yaml`, README central · 39 runbook:
`central-authority/runbook-rotacion-de-clave.md` · 40–42 pruebas hostiles, mutaciones con purga de
`.pyc`, E2E con dos firmantes por corrida en proyecto dependiente `licencia-rotacion` · 43 DeepSeek:
solo la matriz pura del conjunto de confianza.

## 5. `/speckit.plan`, compuerta, checklist, tareas

Cliente: `trust_anchor.load_trust_set` + `resolve_trusted_owner_key` (puro) · `Settings.license_trust_keys`
y validador de prod sobre el conjunto · `import_license` compuerta 2: conjunto → `kid` firmado → clave
exacta → firma; eventos `LICENSE_SIGNING_KEY_REJECTED`; códigos `LICENSE_SIGNING_KID_MISSING`,
`LICENSE_SIGNING_KID_UNKNOWN` (423) y el existente `LICENSE_SIGNATURE_INVALID`. Autoridad:
`Settings.signing_keys`, `load_signing_key_set`, `active_signing_pem`, validador de prod;
`issue_license` firma con la privada del `kid` activo. QA: segundo firmante B por corrida,
`licencia_firmada.py --kid/--firmante-b/--sin-kid`, `KONTROL_LICENSE_TRUST_KEYS` en el backend de la
corrida, proyecto Playwright `licencia-rotacion`. Documentos: contrato del paquete, README, compose,
`.env.example`, runbook, hoja de ruta, puntero.

**Compuerta G01–G41: PASS.** Tareas: T01 inventario/Spec Kit · T02 conjunto de confianza puro · T03
cliente · T04 autoridad · T05 **DeepSeek** matriz pura del conjunto (vectores de Claude) · T06 pruebas
cliente (rotación, hostiles, retiro, anti-retroceso entre claves, sync con B) · T07 pruebas autoridad ·
T08 QA/E2E · T09 documentos, runbook, puntero · T10 mutaciones, suites, Git. Todas `CLAUDE_ONLY` salvo
T05. `analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0,
`MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 %. **Autorización de `implement`:** la del encargo.

## 6. Implementación (T02–T04, T08, T09)

- **Cliente** · `app/core/trust_anchor.py`: `load_trust_set(trust_keys, legacy_pem, legacy_kid)` (JSON o mapa
  `kid → PEM` **más** el par de una clave; `missing`, `invalid`, `kid_missing`, `duplicate_kid`,
  `duplicate_key`; sin alias) y `resolve_trusted_owner_key(kid, conjunto)` (`kid_missing`, `unknown_kid`).
  `Settings.license_trust_keys` (`KONTROL_LICENSE_TRUST_KEYS`); el validador de `prod` exige un conjunto
  válido. `import_license` compuerta 1: conjunto (503 `LICENSE_TRUST_ANCHOR_<MOTIVO>`, sin evento);
  compuerta 2: clave **exacta** por el `kid` firmado (423 `LICENSE_SIGNING_KID_MISSING` /
  `LICENSE_SIGNING_KID_UNKNOWN`, evento `LICENSE_SIGNING_KEY_REJECTED` con `kid` y motivo) y firma contra
  esa clave (423 `LICENSE_SIGNATURE_INVALID`, sin decir qué otra verificaría). Todo lo demás —identidad,
  contrato, bloqueo, período, `revision`, persistencia— igual. `state.kid` sigue siendo el del paquete.
- **Autoridad** · `central_authority/config.py`: `Settings.signing_keys` (`KONTROL_CENTRAL_SIGNING_KEYS`),
  `signing_kid` pasa a ser el **activo**, `load_signing_key_set` (`missing`, `invalid`, `duplicate_kid`,
  `duplicate_key`, `active_kid_missing`; sin «primera clave por defecto»), `active_signing_pem`; el
  validador de `prod` exige el conjunto con el activo. `issue_license` firma con
  `load_signing_key(active_signing_pem(settings))`: el `kid` del paquete y la clave que firma son el mismo
  par, siempre. Libro y asignación de `revision` sin cambios. Sin persistencia de privadas.
- **QA** · `qa/e2e_corrida.py`: dos firmantes sintéticos por corrida (A firma la siembra y la autoridad;
  B solo es de confianza), `KONTROL_LICENSE_PUBLIC_KEY_KID` + `KONTROL_LICENSE_TRUST_KEYS` en el backend,
  proyecto Playwright `licencia-rotacion` (tras `licencia-sync`); `qa/licencia_firmada.py --kid /
  --sin-kid / --firmante-b`.
- **Despliegue y documentos** · `compose.central.yaml` (`SIGNING_KEYS`), `.env.example`
  (`PUBLIC_KEY_KID`, `TRUST_KEYS`), README central, contrato del paquete (`kid`), **runbook**
  `central-authority/runbook-rotacion-de-clave.md` (R0–R4, criterio de retiro del operador, lo que no
  se puede saltar), ADR-D0-006 (rotación implementada), hoja de ruta, `next-spec-decision.md`
  (puntero cerrado por decisión de la dueña). Esquema del cliente **0**; central **0** migraciones;
  frontend de producto **0**; sync autenticado intacto (dominio de claves distinto).

## 7. Pruebas y mutaciones (T05–T07, T10)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_trust_set_rules.py` (DeepSeek T05, `AUDIT_PASS` a la primera) | TSET-01..16: par de una clave, JSON y mapa, unión, entrada repetida, `duplicate_kid`, `duplicate_key`, vacío, `kid_missing`, nueve entradas inválidas, resolución exacta, conjunto de firma, `active_kid_missing`, duplicados, inválidas, `prod` | puro |
| `tests/test_license_key_rotation.py` | KEYROT-01..19: R0 par de una clave y `kid` = identidad; `kid` desconocido con firma válida; sin `kid`; B antes del pre-stage; R1 A y B cada una por su `kid`; `kid` A con firma de B; licencia que trae su clave; R2/R3 B activa firma con B y la reemisión recibe `revision` nueva; anti-retroceso entre claves y `kid` no ordena; entre períodos; libro intacto; R4 retiro de A (importación nueva rechazada, estado persistido intacto, frontera documentada); `kid` duplicado y clave duplicada fallan cerrado; vacío/JSON roto; `prod` del cliente; autoridad falla cerrada sin clave del activo; sesión, permiso, identidad, status, diagnóstico, health y esquema | SQLite y PostgreSQL |
| Adaptadas | CLA-01 (mensaje), TRUST-09 (texto del registro, restaurado), ROLLA-13 y REVC-08/09 (un `kid` arbitrario ya no es «etiqueta sin semántica»: desconocido → rechazo antes del período), `test_e2ecorrida_14` (cuarto proyecto) | — |
| E2E | `e2e/licencia-rotacion.spec.ts` (E2E-KEYROT-01..07) en el proyecto dependiente `licencia-rotacion` | PostgreSQL + dos firmantes |

**Mutaciones** (`evidence/licencia-rotacion-de-clave/mutaciones-backend.txt`, purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`): M-01 probar todas las claves · M-02 `kid` desconocido cae a la primera ·
M-03 sin `kid` usa la primera · M-04 `kid` duplicado gana el último · M-05 alias admitidos · M-06 par
legacy sin `kid` inventa uno · M-07 la licencia que trae clave se vuelve de confianza · M-08 la autoridad
elige la primera clave si el activo no tiene · M-09 la autoridad firma con otra clave que la del `kid` ·
M-10 `kid` duplicado en el conjunto de firma gana el último · M-11 el `kid` pasa a ordenar. Resultado: **11/11 muertas** (`mutaciones-backend.txt` M-01..03 y `mutaciones-backend-m04-m11.txt` M-04..11: la primera pasada se detuvo en M-04 por una cadena de anclaje mal escrita en el propio guion, no por el código, y se repitió desde ahí).

## 8. Resultados

| Gate | Resultado |
|---|---|
| Nuevas suites SQLite / PostgreSQL | TSET 16 + KEYROT 19 = **35** (SQLite) · ídem PostgreSQL; regresiones CLA, TRUST, ROLLA, REVC, CSYNC, SYNC en verde |
| Backend completo SQLite / PostgreSQL | **43 failed / 1334 passed / 1019 skipped** (42 de documentos sin `clamscan` + un intermitente SQLite ya registrado; +35 nuevas) / **37 failed / 2332 passed / 27 skipped** (línea base exacta de documentos; 0 regresiones). Una primera pasada completa dejó 10 errores de preparación en tres suites cuyo mundo importaba una licencia con `kid` «k» (antes etiqueta libre; ahora identidad de clave) y los cuatro mensajes de `test_settings_trust_anchor`: adaptados y verdes; `test_e2ecorrida_01` falló una vez en la suite completa de PostgreSQL y pasó solo y en la repetición completa (intermitente de orden, anotado) |
| `ruff check` · `mypy` | limpio · limpio |
| Frontend `typecheck` · `lint` · `vitest` · `build` | OK · OK · **459/459** · build OK (`frontend-gates.txt`) (cambio de producto 0) |
| E2E dirigido (`licencia-rotacion` sola, `--no-deps`) | **1 passed** (E2E-KEYROT-01..07; base `r20261007t233013…`, limpieza LIMPIA; A y B por su `kid`, desconocido/ausente/cruzado rechazados, el período sigue primero) |
| E2E global (`chromium` → `licencia-revision` → `licencia-sync` → `licencia-rotacion`) | **231 passed, 0 failed, 40 skipped** (228 + linaje + sync + rotación; base `r20261007t234612…`, limpieza LIMPIA, puertos libres al cierre) |
| Bases de corrida al cierre | 0 |

## 9. Deudas, veredicto y trazabilidad

| Deuda | Estado |
|---|---|
| `LICENCIA-SIN-ROTACION-DE-CLAVE` | **CLOSED / CONVERGED** (2026-10-07) |
| `NEXT-SPEC-POINTER-AMBIGUO` | **OWNER_DECIDED / CLOSED** (`NEXT TECHNICAL CYCLE` ≠ `NEXT MASTER SPEC = NOT YET PRIORITIZED`) |
| `LICENCIA-ESTADO-SIN-REVERIFICAR` | OPEN (retirar una clave no revalida el estado persistido; declarado) |
| `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` y el resto del encargo | OPEN, sin cambio |
| MASTER57 · SPEC057 · D0-07 · 056 | sin cambio (57; `PLANNED / NOT STARTED`; `NARROWED`; validación fiscal y liberación) |

Orquestación: 10 tareas, `CLAUDE_ONLY` 9, `DEEPSEEK_ELIGIBLE` 1 (T05: 1 llamada `deepseek-v4-flash`,
2609/3247 tokens, $0.001239, `AUDIT_PASS`, 0 reintentos; egress: solo firmas de módulos y claves
sintéticas generadas en la prueba). `analyze` final: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER
CONFLICT = 0`; huérfanos 0; `MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %:

| FR-010 | Código | Prueba | Mutación |
|---|---|---|---|
| 437–443 (conjunto, `kid` único, firmado, selección estricta, desconocido, sin probar todas, A/B) | `load_trust_set`, `resolve_trusted_owner_key`, compuerta 2 | TSET-01..10, KEYROT-01..06, E2E-KEYROT 1–4 | M-01..05 |
| 444–447 (sin confianza dinámica; privadas fuera del cliente y de la base) | compuerta 1; sin persistencia | KEYROT-07, 16; CLA-17 | M-07 |
| 448–451 (`kid` activo explícito, fallo cerrado, emisión con el activo y su privada) | `load_signing_key_set`, `active_signing_pem`, `issue_license` | TSET-11..16, KEYROT-01, 08, 18 | M-08, M-09, M-10 |
| 452–460 (solapamiento, anti-retroceso entre claves, `kid` no ordena, `revision` nueva, libro intacto) | sin cambio en `import_license` 5/5b ni en el libro | KEYROT-05, 08, 09, 10, 11; E2E-KEYROT 5–6 | M-11 |
| 461–463 (retiro, sin revalidación, deuda separada) | conjunto sin A | KEYROT-12, 13 | — |
| 464–467 (transición del par de una clave, sin saltarse `kid`, duplicados) | `load_trust_set` | TSET-01, 04, 05, 06; KEYROT-01, 14, 15, 17 | M-04, M-05, M-06 |
| 468–472 (prod sin generar claves; identidad; sesión + `license:create`; `READ_ONLY`; sync) | sin cambio | KEYROT-18, 19; CSYNC-10; SYNC | — |
| 473–478 (esquema 0; sin privadas en base; status/diagnóstico/health) | — | KEYROT-19 | — |
| 479–482 (agnóstico; sin descarga dinámica; runbook con cuatro fases) | runbook, compose, `.env.example` | — | — |
| 483–487 (legacy, revisionadas, MASTER57, 057, puntero) | sin cambio; documentos | ROLLA, REVC; §9 | — |
