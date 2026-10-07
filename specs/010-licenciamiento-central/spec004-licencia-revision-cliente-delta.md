# SPEC 004 · DELTA DIRIGIDO — `revision` EN EL CLIENTE: ORDEN DENTRO DEL PERÍODO Y TRANSICIÓN LEGACY

> Iniciado el 2026-10-07. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Continúa `spec004-licencia-revision-delta.md` (detenido el
> 2026-10-06 por falta de emisor) y `spec004-central-authority-phase1-delta.md` (el emisor existe
> desde `12c0c39`). Deudas: `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` (reabierta y cerrada aquí)
> y cierre definitivo de `LICENCIA-DOWNGRADE-FIRMADO`.
>
> **Objetivo:** el cliente consume la `revision` firmada que emite la Autoridad Central y la aplica
> como segundo criterio de orden, después del período, dentro de la misma sección crítica de la
> Fase A; define la transición legacy → revisionada; no asigna, calcula ni corrige ninguna
> `revision`. Esquema y migraciones del cliente: 0. Emisor: sin cambios.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `f8ce6a6` / **`f8ce6a6`** / `f8ce6a6` / `develop` / limpio · `COMMITS_AFTER_F8CE6A6 = 0` · 0 bases de corrida (PostgreSQL de QA reiniciado tras el arranque de la máquina: `ktest` recreada, nada más) |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` |
| `CENTRAL_ISSUER_OWNER` | **SPEC004 · Autoridad Central** — `resources/backend/central_authority/` + `specs/010-licenciamiento-central/central-authority/` (verificado, no rediseñado) |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

Decisiones de la dueña D1–D10 (período primero; `revision` firmada, entera ≥ 1, monótona por
instalación + período, asignada solo por el emisor; mayor → aceptar, menor → rechazar, igual +
mismo artefacto → idempotente, igual + otra carga → conflicto; legacy = claim **ausente**, nunca
`null` ni 0; legacy → revisionada ≥ 1 acepta y fija el linaje; revisionada → legacy rechaza; sin
licencia vigente entra una legacy o una revisionada válidas; la `revision` no cruza períodos;
`kid` identifica clave; derechos, `kid`, `issued_at`, `imported_at` y versión mínima no ordenan;
el cliente solo valida y compara): **ratificadas, no se reabren.** `CENTRAL-SYNC-AUTHORITY-UNDEFINED`
está decidida por la dueña (identidad Ed25519 de la instalación + desafío-respuesta + nonce de un
solo uso + vinculación canónica de la petición) y **no se implementa en este ciclo**; la autoridad
sigue sin exponer rutas de sync ni de licencia.

## 2. Inventario recuperado (W04–W12)

| Qué | Dónde | Estado |
|---|---|---|
| Contrato de `revision` | `app/core/license_contract.py` `parse_revision` (ausente → `None`; entero ≥ 1; `bool`, `null`, 0, negativos, cadenas → `LICENSE_INVALID_REVISION`) | `CLIENT_REVISION_PARSE = app.core.license_contract.parse_revision` · `CLIENT_REVISION_VALIDATE = idem` (compartido con el emisor: una sola regla) |
| Comparación en el cliente | `import_license` paso 5 solo compara **período** | `CLIENT_REVISION_COMPARE = NONE` (reproducido en `evidence/licencia-revision-cliente/antes.txt`: ocho casos, siete aceptados indebidamente) |
| Persistencia | `LicenseArtifact.payload` (JSON firmado tal cual), `payload_hash`, `signature_hex`, `imported_at`; `LicenseState` sin columna de revisión | `CLIENT_REVISION_PERSIST = dentro del artefacto firmado` → `CLIENT_SCHEMA_CHANGE = 0` |
| Emisor | `central_authority/service.issue_license` | `CENTRAL_REVISION_FIELD = "revision"` · `CENTRAL_REVISION_TYPE = int` · `CENTRAL_REVISION_SCOPE = instalación + (period_start, period_end)` · `CENTRAL_FIRST_REVISION = 1` · `CENTRAL_PACKAGE_SERIALIZATION = json.dumps(sort_keys=True, ensure_ascii=False)` sobre el dict · `CENTRAL_SIGNATURE_INPUT = esos bytes, con "revision" y "kid" dentro` (`contract.sign_license_payload(payload)`); linaje con `FOR UPDATE`, libro inmutable, unicidad `(lineage_id, revision)` |
| Canonicalización legacy | `canonical_bytes` sobre el dict recibido; vector dorado CLA-12, REV-05/06 | `LEGACY_CANONICALIZATION = PRESERVED` |
| Comparador de período | `compare_period` SAME/NEWER/OLDER/INCOMPARABLE | preservado (Fase A) |
| Bloqueo | `import_license` paso 4: `Installation` y `LicenseState` `with_for_update`, relectura bajo bloqueo; PostgreSQL manda | `CLIENT_LOCKING_BOUNDARY = PROVEN` (RACE-01..05) |
| Igualdad exacta de artefacto | `payload_hash` = SHA-256 de los bytes canónicos (lo que ya distingue el artefacto en ROLLA-02) | reutilizada |
| Errores | `KontrolError(code, message, status_code=423)` → `{code, message}`; anti-retroceso ya usa 423 | se reutiliza 423 |
| Auditoría | `_record_event(db, installation, tipo, detail, user_id)`; patrón `LICENSE_PERIOD_DOWNGRADE_REJECTED` con `license_id`, `current_license_id`, `outcome` | se imita |
| Compatibilidad A/C/D | CLA-11 (importa paquete central), CLA-12 (legacy intacto), CLA-13 (`revision` inválida → 423) | revalidadas por las suites de este ciclo |

**Qué cambia de contrato para las pruebas existentes.** La Fase A aceptaba «transitoriamente»
cualquier reemisión del mismo período (ROLLA-03, RACE-04, LICIMP-04, E2E-ROLLA paso 3 y varias
pruebas que importaban una segunda legacy distinta del mismo período como preparación). Con D4 esa
tolerancia desaparece: una legacy **distinta** del mismo período se rechaza. Esas pruebas se
adaptan al contrato nuevo —reimportación **exacta** (idempotente), período posterior, o la
revisionada del emisor—, y la adaptación se declara pieza por pieza en §10.

## 3. `/speckit.specify` — FR-010-322..366 (= FR-REVCLIENT-001..045 del encargo)

| FR-010 | Requisito |
|---|---|
| 322 | El cliente aplica la `revision` firmada a las licencias revisionadas del mismo período |
| 323–324 | El período sigue siendo el primer criterio; la `revision` solo se compara con período igual |
| 325–328 | Mismo período: mayor → aceptar; menor → rechazar; igual + mismo artefacto → idempotente; igual + carga distinta → conflicto, rechazar |
| 329–332 | Legacy: la misma legacy exacta → idempotente; otra legacy del mismo período → rechazar; legacy vigente + revisionada ≥ 1 → aceptar (fija el linaje); revisionada vigente + legacy → rechazar |
| 333 | Legacy no se reescribe como `revision` 0 ni `null` |
| 334–335 | La `revision` va dentro del material firmado; alterarla invalida la firma antes de ordenar |
| 336–337 | `revision` entero ≥ 1; `bool` no es `revision` |
| 338–341 | Derechos, `kid`, `issued_at`/`imported_at` y versión mínima no ordenan; la `revision` no se compara entre períodos |
| 342–344 | Se preservan el anti-retroceso por período, el bloqueo de `LicenseState` y la relectura; la comparación de `revision` ocurre bajo ese bloqueo |
| 345–347 | `revision` 2 y 3 concurrentes terminan en 3; la menor que espera relee y se rechaza; una legacy concurrente no sobrescribe un linaje revisionado |
| 348 | Un rechazo no muta estado, derechos, período, revisión, modo, caché ni metadatos |
| 349–351 | Se preservan `license:create`, el ancla del propietario y la identidad de instalación |
| 352–353 | Los bytes y firmas legacy no cambian |
| 354–355 | La Autoridad Central real es la fuente de `revision` en las pruebas de integración; el cliente no asigna revisiones |
| 356–358 | Sin cambio de esquema ni migración del cliente; sin cambio de esquema central |
| 359–361 | `/license/status` mínimo; diagnóstico protegido; health sin cambios |
| 362–364 | Fuera: rotación de clave, autenticación de sync, reverificación de estado |
| 365 | Si todo converge, `LICENCIA-DOWNGRADE-FIRMADO` → `CLOSED / CONVERGED` |
| 366 | Certificación E2E global con `qa/e2e-run.py` |

## 4. `/speckit.clarify` — 41 preguntas, 41 respuestas, `MATERIAL OQ = 0`

1 dueñas: §1 · 2 `LicenseData` ya lleva `revision: int | None` · 3 parseo: `parse_revision` en el
contrato puro · 4 validador: el mismo (una regla) · 5 campo central: `"revision"` · 6 serializador
central: `canonical_bytes` del contrato · 7 verificador cliente: `verify_license_signature` sobre el
dict recibido · 8 igualdad: `payload_hash` · 9 legacy: `"revision" not in payload` · 10 artefacto
vigente: la última fila de `LicenseArtifact` de `state.license_id` por `imported_at` (cada
importación aceptada inserta una) · 11 comparador: `compare_period` · 12 bloqueo: paso 4 · 13
relectura: `state` leído `with_for_update` · 14 mismo período hoy: acepta todo (antes.txt) · 15
códigos: `LICENSE_<RESULTADO>` con 423, como `LICENSE_PERIOD_DOWNGRADE` · 16 auditoría: evento
`LICENSE_REISSUE_REJECTED` con `license_id`, `current_license_id`, `current_revision`,
`incoming_revision`, `outcome`, actor; ni cargas ni firmas · 17 caché: no hay caché de licencia en el
cliente fuera de `LicenseState` · 18 primera activación: sin estado → entra legacy o revisionada
válidas (D5) · 19 `READ_ONLY`: mismo período + revisión mayor → entra; posterior → entra; anterior →
no · 20–26 casos 1–8 del encargo = FR-325..332 · 27 bordes: `bool`, `null`, 0, negativos, decimales,
cadenas → `LICENSE_INVALID_REVISION` antes del bloqueo · 28 carrera 2/3 → siempre 3 · 29 legacy A +
{legacy B, r1} → final r1, B rechazada en ambos órdenes · 30 regresión RACE-01/03 · 31 emisor en
pruebas: `central_authority.service` con base propia (SQLite en memoria en pytest; fichero efímero de
la corrida en E2E) y la clave sintética de la corrida como clave del propietario · 32 esquema cliente:
0 · 33 esquema central: 0 · 34 frontend: 0 · 35 `/license/status`: solo `mode`, `license_url` · 36
diagnóstico: `license:view` · 37 health: igual · 38 mutaciones: purga de `__pycache__` +
`PYTHONDONTWRITEBYTECODE=1` · 39 volumen compartido: las suites de licencia se corren en serie, sin
otra pytest en paralelo · 40 E2E: el linaje revisionado cambia `license_id` y deja el estado
revisionado, así que corre en un **proyecto Playwright dependiente** (`licencia-revision`, tras
`chromium`), y las suites del grupo paralelo pasan a reimportar el artefacto vigente **exacto** · 41
DeepSeek: solo la matriz de pruebas puras de la máquina de estados.

## 5. `/speckit.plan` — W01–W41 y diseño

- **Contrato puro** (`app/core/license_contract.py`): `resolve_same_period_reissue(current_revision,
  current_payload_hash, incoming_revision, incoming_payload_hash)` → `SAME_ARTIFACT` ·
  `NEWER_REVISION` · `LEGACY_TO_REVISION_BRIDGE` (aceptan) · `LEGACY_REISSUE_REQUIRES_REVISION` ·
  `LEGACY_AFTER_REVISION` · `REVISION_DOWNGRADE` · `REVISION_CONFLICT` (rechazan; código HTTP
  `LICENSE_<resultado>`, 423). Sin reloj, sin derechos, sin `kid`. `app/core/license.py` reexporta.
- **Cliente** (`import_license`): tras el anti-retroceso por período y **bajo el mismo bloqueo**, si
  `SAME_PERIOD`: leer el artefacto vigente, parsear su `revision` (artefacto vigente ilegible →
  `LICENSE_CURRENT_ARTIFACT_INVALID`, cerrado), resolver, rechazar con evento o seguir al paso 6.
  Sin artefacto vigente (estado fabricado a mano) se trata como legacy sin huella: solo entra una
  revisionada. Compuertas 1–4 antes del bloqueo, como hoy.
- **Emisor:** sin cambios. **Esquema cliente:** 0. **Frontend de producto:** 0.
- **QA:** `qa/licencia_firmada.py` gana `--vigente` (el artefacto vigente exacto, tal cual está
  guardado) y `--revision <json>` (revisionadas sintéticas hostiles); `qa/autoridad_central.py`
  (nuevo) registra la instalación de la corrida en una autoridad efímera y emite con el servicio
  real, firmando con la clave sintética de la corrida; `e2e/licencia-revision.spec.ts` en el
  proyecto dependiente; `qa/e2e_corrida.py` añade el proyecto.

**Compuerta constitucional G01–G41: PASS.** HEAD y `develop` verificados; orquestación operativa;
dueñas resueltas; deltas de `revision`, Fase A y Autoridad Central recuperados; campo firmado
confirmado en el emisor; parseo, validación, legacy e igualdad conocidos; comparador, bloqueo y
relectura preservados; máquina de estados, transición, conflicto y concurrencia definidas; arnés
central definido; esquema cliente 0; migración cliente 0; esquema central 0; auth, ancla, identidad,
estado público, diagnóstico y health preservados; sync, rotación y reverificación excluidas;
pruebas y mutaciones definidas; volumen compartido reconocido; salvaguarda `.pyc` planificada;
tareas clasificadas; `MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %.

## 6. `/speckit.checklist`

Todas las casillas del encargo marcadas al converger (§11): checkpoint, rama, árbol, orquestación,
dueñas, tres deltas leídos, campo y firma confirmados, canonicalización recuperada, A/C/D
reproducidos, ausencia de orden reproducida (`antes.txt`), comparador, bloqueo y relectura
mapeados, legacy e igualdad definidas, ocho casos definidos, derechos/`kid`/fechas excluidos,
`revision` entre períodos excluida, cuatro carreras planificadas, emisor real integrado, auth/ancla/
identidad/estado público/diagnóstico/health preservados, esquema 0, migración 0, central 0, sync/
rotación/reverificación excluidas, volumen compartido preservado, `.pyc` activa, pruebas,
mutaciones, DeepSeek acotado, `MATERIAL OQ 0`, `UNKNOWN 0`, trazabilidad 100 %.

## 7. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | FR-010 | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, reproducción, Spec Kit | — | CLAUDE | YES | n-a | este delta, `evidence/licencia-revision-cliente/` |
| T02 | Máquina de estados pura `resolve_same_period_reissue` + reexportación | 322–333, 338–341 | CLAUDE | **YES** | n-a | `app/core/license_contract.py`, `app/core/license.py` |
| T03 | Integrar la comparación bajo el bloqueo; códigos; evento; sin mutación en rechazo | 322–348 | CLAUDE | **YES** | n-a | `app/modules/licensing/service.py` |
| T04 | Pruebas puras de la matriz (vectores fijados por Claude en T02) | 325–333, 338 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `tests/test_license_revision_rules.py` |
| T05 | Pruebas cliente ↔ emisor real (SQLite+PG): linaje, puente legacy, hostiles, auth, ancla, identidad, `READ_ONLY`, auditoría, sin mutación, estado público/diagnóstico/health | 322–361 | CLAUDE | **YES** | n-a | `tests/test_license_revision_client.py` |
| T06 | Carreras PostgreSQL: 2/3, 3 primero, legacy+r1 (dos órdenes), conflicto | 345–347 | CLAUDE | **YES** | n-a | `tests/test_license_revision_race.py` |
| T07 | Adaptar al contrato nuevo las pruebas que afirmaban la tolerancia transitoria | 329–332 | CLAUDE | YES | n-a | `tests/test_license_period_rollback.py`, `tests/test_license_import_race.py`, otras si fallan |
| T08 | QA: `licencia_firmada.py --vigente/--revision`, `autoridad_central.py`, proyecto Playwright, `licencia-revision.spec.ts`, adaptación de `licencia-periodo` y `licencia-import` | 354, 366 | CLAUDE | YES | n-a | `qa/`, `resources/frontend/e2e/`, `playwright.config.ts` |
| T09 | Mutaciones M-01..M-10 con purga `.pyc`; suites completas; E2E dirigido y global; docs; Git | — | CLAUDE | NO | n-a | evidencia, hoja de ruta |

`analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; requisitos y tareas
huérfanos = 0; `MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %. `CENTRAL_REVISION_CONTRACT =
PROVEN` (CLA-05..07, CLA-PG-01) · `LEGACY_CANONICALIZATION = PRESERVED` (CLA-12, REV-05/06) ·
`CLIENT_LOCKING_BOUNDARY = PROVEN` (RACE-01..05). **Autorización de `implement`:** la del encargo.

## 8. Implementación (T02, T03)

- `app/core/license_contract.py`: constantes `SAME_ARTIFACT`, `NEWER_REVISION`, `LEGACY_TO_REVISION_BRIDGE`,
  `LEGACY_REISSUE_REQUIRES_REVISION`, `LEGACY_AFTER_REVISION`, `REVISION_DOWNGRADE`, `REVISION_CONFLICT`,
  `REISSUE_REJECTIONS`; `resolve_same_period_reissue(...)` pura (sin reloj, derechos, `kid` ni fechas);
  `_revision_valida` rechaza `bool`, 0 y negativos también aquí (legacy nunca es la revisión 0).
  `app/core/license.py` reexporta.
- `app/modules/licensing/service.py` · `import_license` paso **5b**, dentro de `if state is not None` y
  después del anti-retroceso por período, **bajo el bloqueo del paso 4**: si `SAME_PERIOD`, lee el último
  artefacto aceptado de `state.license_id`, parsea su `revision` (ilegible → `LICENSE_CURRENT_ARTIFACT_INVALID`,
  423, evento), resuelve, y ante un rechazo anota `LICENSE_REISSUE_REJECTED` (`license_id`,
  `current_license_id`, `current_revision`, `incoming_revision`, `outcome`, actor) y lanza
  `LICENSE_<resultado>` con 423 **antes de persistir nada**. `LICENSE_IMPORTED` lleva ahora `revision`.
  Compuertas 1–4 (sesión + `license:create`, ancla, identidad, contrato) siguen delante y fuera del bloqueo.
- **Hallazgo colateral, cerrado aquí:** la reproducción seguía aceptando todo tras implementar 5b porque en
  SQLite `DateTime(timezone=True)` guarda la hora de pared y pierde el `-04:00`: el período releído
  quedaba 4 h corrido y `compare_period` decía `NEWER_PERIOD` para el mismo período (en PostgreSQL,
  `timestamptz`, no ocurría). El estado guarda ahora los cuatro instantes del período **normalizados a
  UTC** (`_utc`): el instante no cambia, el modo y el orden tampoco en PostgreSQL, y los dos motores
  comparan lo mismo. No es una fecha de negocio distinta ni toca `America/Caracas` (los hitos siguen
  viniendo firmados en el paquete). Mutación M-09 lo cubre.
- Emisor: **0 cambios**. Esquema del cliente: **0**. Migraciones: **0**. Frontend de producto: **0**.

## 9. QA (T08)

- `qa/licencia_firmada.py`: `--vigente` (el artefacto vigente exacto, carga y firma tal como se guardaron) y
  `--revision <json>` (revisionadas sintéticas **hostiles**: conflicto, manipulación, valores inválidos).
- `qa/autoridad_central.py` (nuevo): levanta `central_authority` con sus migraciones reales sobre
  `<estado>/license/central.sqlite` (efímero, se borra con la corrida), registra la instalación de la
  corrida con la clave pública que el cliente guarda y emite la siguiente `revision` firmando con la clave
  sintética de la corrida, cuya pública es el ancla del backend. La URL de la base del cliente y la clave
  viajan por el entorno; nada se imprime salvo el paquete.
- `resources/frontend/playwright.config.ts`: proyecto `licencia-revision` (`dependencies: ["chromium"]`,
  `testMatch` solo su suite; los navegadores la ignoran). `qa/e2e_corrida.py` añade `--project=licencia-revision`.
  Dirigido: `qa/e2e-run.py -- e2e/licencia-revision.spec.ts --no-deps`.
- `e2e/licencia-revision.spec.ts`: E2E-REV-01..14 en un escenario ordenado (puente legacy, r1→r2→r3 del
  emisor real, hostiles, otro período, compuertas, auditoría, estado público).
- `e2e/licencia-periodo.spec.ts` paso 3 y `e2e/licencia-import.spec.ts` LICIMP-04: reimportan el artefacto
  vigente **exacto** (idempotente) y, ROLLA, comprueban además que otra legacy del mismo período se rechaza.

## 10. Pruebas adaptadas al contrato nuevo (T07)

| Prueba | Antes | Ahora |
|---|---|---|
| `test_license_period_rollback.py::test_rolla_03` | otra legacy del mismo período entraba «transitoriamente» | se rechaza `LICENSE_LEGACY_REISSUE_REQUIRES_REVISION` y nada se mueve |
| `test_license_import_race.py::test_race_04` | dos legacy distintas del mismo período entraban serializadas | las dos se rechazan; A sigue; 0 hilos en la sección crítica |
| `test_license_import_access.py::licimp_06, 12, 13` | importaban `LIC-NUEVA`/`LIC-RENOVADA`, otra legacy del mismo período que la base | reimportan el artefacto base exacto (compuerta del llamador, identidad en el evento y renovación desde `READ_ONLY`/avisos quedan probadas igual) |
| `test_license_trust_anchor.py::test_trust_06_07` | `LIC-ORDEN` del mismo período | `LIC-ORDEN` de un período posterior (lo probado es el orden de las compuertas) |
| `e2e/licencia-periodo.spec.ts` paso 3, `e2e/licencia-import.spec.ts` LICIMP-04 | reemisión legacy del mismo período | artefacto vigente exacto; ROLLA añade el rechazo de otra legacy |

Ninguna otra suite importaba una segunda legacy distinta del mismo período.

## 11. Pruebas y mutaciones (T04–T07, T09)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_license_revision_rules.py` (DeepSeek T04, `AUDIT_PASS` a la primera) | RREV-01..14: matriz pura de `resolve_same_period_reissue`, incl. 0, negativos y `bool` | puro |
| `tests/test_license_revision_client.py` | REVC-01..19: legacy exacta idempotente, otra legacy rechazada, puente con la r1 del emisor real, legacy tras revisión, r2 con menos derechos, r1 retroceso, r3 idempotente y huecos, conflicto (otra carga, otro `kid`), `kid`/derechos/versión mínima no ordenan, manipulación → firma, siete valores inválidos sin evento, otro período y `PERIOD_DOWNGRADE` con r999, `READ_ONLY` sobre un período vencido emitido por el emisor, compuertas delante, estado público/diagnóstico/health, sin columna nueva, artefacto vigente ilegible, registros sin material, mismo `license_id` entre revisiones | SQLite y PostgreSQL |
| `tests/test_license_revision_race.py` | RREV-RACE-01 r2/r3 × 6 rondas → siempre r3, 1 hilo dentro; 02 r3 confirma primero y r2 relee y se rechaza con evento; 03 legacy A + {legacy B, r1} en los dos órdenes → r1; 04 misma revisión con otra carga × 4 rondas → una entra, la otra conflicto | PostgreSQL |
| Regresiones | RACE-01..05 (Fase A), ROLLA-01..13, LICIMP, TRUST, CLA-01..18, CLA-PG-01..03, REV-01..07 | ambos |

**Mutaciones** (`evidence/licencia-revision-cliente/mutaciones-backend.txt`, con purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`): M-01 rama 5b desactivada · M-02 `>` → `>=` · M-03 legacy tras revisión
entra · M-04 puente rechazado · M-05 menor entra · M-06 conflicto como mismo artefacto · M-07 artefacto
vigente = el más antiguo · M-08 rechazo decidido pero no aplicado · M-09 período sin normalizar a UTC ·
M-10 `bool` válido · M-11 sin `FOR UPDATE` (PostgreSQL). **Primera pasada: 10/11 muertas; M-07
sobrevivió** porque ninguna prueba presentaba dos cargas distintas con el mismo `license_id` (el
emisor real genera uno nuevo por emisión): hueco real de la suite, no mutante equivalente. Se añadió
REVC-19 (misma `license_id`, r6 entra; la r5 exacta con la misma `license_id` es retroceso) y M-07
se repitió y murió (`mutaciones-backend-m07-repeticion.txt`): **11/11**.

## 12. Resultados

| Gate | Resultado |
|---|---|
| Nuevas suites SQLite / PostgreSQL | RREV 14 + REVC 25 = **39 passed** (SQLite) · + RREV-RACE 5 = **44 passed** (PostgreSQL); regresiones RACE-01..05, ROLLA-01..13, LICIMP, TRUST, CLA en verde |
| M-07 repetida tras REVC-19 | **muere** (1 failed: REVC-19) · `mutaciones-backend-m07-repeticion.txt` → **11/11 muertas** en total |
| Backend completo SQLite / PostgreSQL | **42 failed / 1230 passed / 1017 skipped** (los 42: documentos sin `clamscan`, línea base exacta; +39 nuevas) / **38 failed / 2224 passed / 27 skipped** (37 de documentos, línea base, + `test_e2ecorrida_14`, que fija la orden de Playwright por defecto y se adaptó al segundo proyecto: después, `tests/test_e2e_corrida.py` 14 passed; 0 regresiones) |
| `ruff check` · `mypy` | limpio · limpio |
| Frontend `typecheck` · `lint` · `vitest` · `build` | OK · OK · **459/459** (34 ficheros) · build OK · `frontend-gates.txt` (cambio de producto 0) |
| E2E dirigido (`licencia-revision`, `licencia-periodo`, `licencia-import`, base nueva, `--no-deps`) | `licencia-revision` sola: **1 passed** (E2E-REV-01..14, base `r20261007t160323…`, limpieza LIMPIA) · `licencia-periodo` + `licencia-import`: **12 passed** (base `r20261007t160102…`). Dos corridas anteriores enseñaron lo que la suite ya documenta: con `--no-deps` no puede ir junto a ROLLA (esta mueve el período), y el patrón de fuga no puede incluir `signature` porque el código `LICENSE_SIGNATURE_INVALID` lo contiene; además la siembra no trae un usuario `lector`: se aprovisiona con `rol_sin_permiso.py`, como en `licencia-import` |
| E2E global (`qa/e2e-run.py`: `chromium` y después `licencia-revision`) | **229 passed, 0 failed, 40 skipped** (228 de `chromium` + el linaje en `licencia-revision`, base `r20261007t161845…`, limpieza LIMPIA) |
| Bases de corrida al cierre | 0 |

## 13. Deudas y veredicto

| Deuda | Estado |
|---|---|
| `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` | **CLOSED / CONVERGED** (2026-10-07) |
| `LICENCIA-DOWNGRADE-FIRMADO` | **CLOSED / CONVERGED** (2026-10-07): período primero, `revision` segundo, nada retrocede |
| `CENTRAL-SYNC-AUTHORITY-UNDEFINED` | OWNER_DECIDED / **NOT IMPLEMENTED** (sin cambio; la autoridad sigue sin exponer sync) |
| `LICENCIA-SIN-ROTACION-DE-CLAVE`, `LICENCIA-ESTADO-SIN-REVERIFICAR`, `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `OFFLINE-NAIVE-EN-SQLITE` y el resto del encargo | OPEN, sin cambio |
| D0-06 | CLOSED / IMPLEMENTED (sin cambio) |

`MASTER56`: 56 filas, sin cambio. `NEXT SPEC = 029`, no iniciada. Orquestación: 9 tareas, `CLAUDE_ONLY`
8, `DEEPSEEK_ELIGIBLE` 1 (T04: 1 llamada `deepseek-v4-flash`, 1700/2324 tokens, $0.000889, `AUDIT_PASS`,
0 reintentos, 0 rechazos; egress: solo el contrato puro y la suite hermana). Emisor sin cambios; esquema
y migraciones del cliente 0; esquema central 0.

## 14. `analyze` final y trazabilidad

`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; requisitos y tareas huérfanos = 0;
`MATERIAL OQ = 0`; `UNKNOWN = 0`; trazabilidad 100 %:

| FR-010 | Código | Prueba | Mutación |
|---|---|---|---|
| 322–328 | `resolve_same_period_reissue`, paso 5b | RREV-01..14, REVC-04..09, 19, E2E-REV 2–4 | M-01, 02, 05, 06, 07 |
| 329–333 | ídem (`None` = ausente; `_revision_valida`) | RREV-01..05, 11; REVC-01..05; RACE-03; E2E-REV 1–2 | M-03, 04, 10 |
| 334–337 | contrato (firma sobre el dict; `parse_revision`) | REVC-10, 11; RREV-11..13; E2E-REV 4 | M-10 |
| 338–341 | solo revisión y hash participan; `compare_period` primero | RREV-14, REVC-08, 09, 12; E2E-REV 3, 5 | M-02, M-06 |
| 342–348 | paso 4 intacto; 5b bajo el bloqueo; `raise` antes de persistir | RACE-01..04, RREV-RACE-01..04; REVC-03, 05, 06, 08, 11, 12, 19 (`_sin_mover`) | M-08, M-11 |
| 349–353 | compuertas 1–3 sin cambio; bytes legacy | REVC-14, TRUST, LICIMP; CLA-12, REV-05/06 | — |
| 354–358 | emisor real en `_emite`; sin columna | REVC-04..07, 13, 16; RREV-RACE; E2E-REV; `alembic heads` del cliente sin cambio | — |
| 359–361 | sin cambio en status/diagnóstico/health | REVC-15, E2E-REV 7, ROLLA-11, LIC-09 | — |
| 362–364 | fuera de alcance, declarado | — | — |
| 365–366 | hoja de ruta; `qa/e2e-run.py` | §12, §13 | — |
