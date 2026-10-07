# SPEC 004 · DELTA DIRIGIDO — FASE A: ANTI-RETROCESO POR PERÍODO E IMPORTACIÓN SERIALIZADA

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Continúa `spec004-licencia-downgrade-delta.md`, que se detuvo
> ante la decisión de orden; la dueña decidió **la opción A**. No se crea otra Spec.
>
> Cierra `LICENCIA-IMPORT-SIN-BLOQUEO`; deja `LICENCIA-DOWNGRADE-FIRMADO` en
> **PARTIALLY_CONVERGED / OPEN** y registra el riesgo residual
> `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` (objetivo futuro: `revision` firmada, **no se
> implementa aquí**). Payload, DOC-07, emisor, esquema, criptografía, ancla, fechas y
> `America/Caracas`: intactos.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `65374ac` / **`65374ac`** / `65374ac` / `develop` / limpio · `COMMITS_AFTER_65374AC = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` · `SECURITY_OWNER` · `QA_OWNER` | **SPEC004** (`010` + `001`) · Master 002 → `001-fundacion` (la carrera es concurrencia, no sesión) · SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña (ratificada tras el bloqueo):** sin licencia → aceptar; mismo artefacto
firmado → idempotencia canónica; período posterior → aceptar; **período anterior → rechazar**;
mismo período con payload distinto → aceptar como reemisión **transitoria** (DOC-07 §7.1);
importaciones concurrentes → serializar para que un período menor nunca pise a uno mayor;
rollback de emergencia fuera. Objetivo futuro documentado: `revision` firmada, monótona, por
instalación y período (período primero; a igual período, `revision` mayor; igual `revision` e
igual payload → idempotente; igual `revision` y distinto payload → conflicto). **No ahora.**

## 2. Evidencia recuperada del ciclo bloqueado (W04–W14)

| Punto | Recuperado de `spec004-licencia-downgrade-delta.md` y `evidence/licencia-downgrade/` | Verificado hoy |
|---|---|---|
| Definición del período | `period_start` y `period_end` firmados; DOC-07 §5.1: anual, 1 abr → 31 mar, consecutivo; la renovación tardía no desplaza el ciclo; §10.4, §15.1, §18.2: «no retroceder el período» | `LicenseData.period_start/period_end` (obligatorios en `parse_license_payload`); `LicenseState.period_start/period_end` |
| Campos firmados usados | solo el período; `kid`, `license_id`, derechos, `imported_at` y reloj local quedan fuera por análisis O1–O9 | sin cambios en el modelo |
| Reproducción secuencial | siete variantes en `antes.txt`: período anterior, anterior con más derechos, vencida → `READ_ONLY`, reemisión del mismo período y su deshecho | ídem |
| Carrera | `carrera.txt`: A vigente, B (2027) y C (2028) concurrentes sobre PostgreSQL, retenidos tras leer el estado: **B gana 3/6** | ídem |
| Fuente de verdad | `LicenseState`, una fila por instalación (`installation_id` único); historial en `LicenseArtifact` (`payload_hash` canónico); sin caché | ídem |
| Bloqueo | **ninguno** en `import_license`; `with_for_update` existe en `identity_access`, `inventory`, `notifications` | ídem |
| Mismo artefacto | igualdad del payload canónico (`_payload_hash`, sha256 del JSON ordenado); hoy: estado igual, +1 artefacto, +1 evento | se preserva tal cual |

### Punto de bloqueo verificado físicamente (W14–W16)

`LicenseState` **no existe** antes de la primera activación: bloquearla no serializa dos primeras
activaciones concurrentes. La fila de `Installation` existe siempre (la crea el primer arranque;
`get_installation` la elige de forma canónica) y es una por despliegue: **es la fila que se
bloquea**. Después, y bajo ese bloqueo, se bloquea y relee `LicenseState` (si existe): el estado
que se compara es el autoritativo, no el leído antes. La transacción es una sola sesión con un
único `commit` al final (`get_db`): el bloqueo se mantiene desde la lectura hasta persistir. Las
comprobaciones sin estado (ancla, firma, identidad, parseo) van **antes** del bloqueo; bajo el
bloqueo solo quedan releer, comparar y persistir.

## 3. Modelo de amenaza

| Actor | Antes | Después |
|---|---|---|
| Administrador con `license:create` y una licencia firmada **vieja** de la instalación (respaldo, correo antiguo) | la aplica y la instalación retrocede, incluso a `READ_ONLY` | 423 `LICENSE_PERIOD_DOWNGRADE`, estado intacto, evento de rechazo |
| Dos renovaciones en vuelo (reintento, dos operadores) | la última en escribir gana: puede quedar la menor | pasan de una en una; la segunda compara contra la que quedó: siempre el período mayor |
| Reemisión del mismo período (ampliar/reducir límites) | se aplica | se aplica (transitorio, §7.1); **residual**: la reemisión anterior del mismo período también se aplicaría |
| Paquete con período incoherente (inicio posterior, fin anterior) | se aplicaba | 423 `LICENSE_PERIOD_CONFLICT`: no describe un período del contrato, no se ordena, no se aplica |

## 4. `/speckit.specify`

FR-010-200..231 (FR-ROLLA-001..032 del encargo):

| FR | Requisito |
|---|---|
| FR-010-200 · 204 · 205 | Una licencia de período anterior no sustituye a la vigente; una de período posterior se acepta; la primera activación sigue funcionando |
| FR-010-201 · 202 · 203 | La comparación usa la semántica contractual del período (inicio y fin firmados), no `period_end` aislado, ni `imported_at`, nombre de fichero, `kid` ni reloj local |
| FR-010-206 · 207 · 208 · 209 | Mismo artefacto → idempotencia canónica; mismo período con payload distinto → reemisión transitoria aceptada (§7.1), que **no** cierra el anti-retroceso; riesgo residual registrado como `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` |
| FR-010-210 · 211 · 212 | Importaciones concurrentes serializadas sobre el estado autoritativo (fila de instalación + estado, `with_for_update`); la comparación se hace sobre el estado releído bajo bloqueo; B y C de períodos distintos terminan siempre en el mayor |
| FR-010-213 | Un retroceso rechazado no muta el estado de licencia (ni período, ni derechos, ni modo, ni identidad); solo deja el evento de rechazo, como los demás rechazos de hoy |
| FR-010-214 · 215 · 216 | `READ_ONLY` se renueva con período posterior; `READ_ONLY` o vencida no admiten período anterior |
| FR-010-217 · 218 · 219 · 220 · 221 | Compuertas 1 y 2 intactas (`license:create`; ancla del propietario, nunca la de la instalación); firma inválida y otra instalación siguen rechazadas |
| FR-010-222 · 223 · 224 | Estado público mínimo, diagnóstico con `license:view`, health mínimos: sin cambios |
| FR-010-225 · 226 · 227 · 228 · 229 | Sin cambios en payload, criptografía, `America/Caracas`, esquema ni migración; sin `revision` |
| FR-010-230 · 231 | Pruebas de concurrencia reales en PostgreSQL; certificación E2E con `qa/e2e-run.py`, base efímera y ancla sintética explícita |

## 5. `/speckit.clarify` — 32 preguntas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC004; apoyos 002, 054 |
| 2–3 | Período canónico y campos | `(period_start, period_end)` firmados, normalizados a UTC para comparar; DOC-07 §5.1 |
| 4 | Fuente de verdad | `LicenseState` |
| 5 | Mismo artefacto | igualdad del payload canónico (`payload_hash`); no se introduce otra identidad |
| 6–9 | Sin licencia · posterior · anterior · reemisión | aceptar · aceptar · 423 `LICENSE_PERIOD_DOWNGRADE` · aceptar (transitorio) |
| 10–11 | `READ_ONLY` y vencida | el estado temporal no cambia la posición del período: posterior entra, anterior no |
| 12 | `LicenseState` | una fila por instalación, sin `payload_hash` propio (vive en `LicenseArtifact`) |
| 13 | Transacción | una sesión por petición, un `commit` final; los rechazos auditados hacen `commit` del evento y lanzan |
| 14–15 | Dónde bloquear y releer | tras las comprobaciones sin estado: `Installation` (siempre existe) con `with_for_update`, luego `LicenseState` con `with_for_update`; el estado comparado es ese |
| 16 | Persistencia | sin cambios: artefacto nuevo + estado sobrescrito + evento |
| 17 | Caché | no hay |
| 18 | Auditoría | los rechazos ya dejan evento; se añade `LICENSE_PERIOD_DOWNGRADE_REJECTED` con `license_id`, vigente, fines de período y resultado, con `user_id`; sin material sensible |
| 19–20 | Carrera y `with_for_update` en PostgreSQL | reproducida (3/6); el bloqueo de fila serializa; la segunda transacción espera y relee |
| 21 | SQLite | `with_for_update` no hace nada; lógica secuencial certificada en SQLite; concurrencia solo en PostgreSQL (marcador existente `skipif` sin `KONTROL_TEST_DB_URL`, patrón de `test_spec004_installation_race.py`) |
| 22 | Código de error | `KontrolError` 423 como `LICENSE_SIGNATURE_INVALID`/`LICENSE_INSTALLATION_MISMATCH`: `LICENSE_PERIOD_DOWNGRADE`; períodos incoherentes → `LICENSE_PERIOD_CONFLICT` (cerrado, no describe un período del contrato) |
| 23–27 | Regresiones | sin cambios: compuertas 1 y 2, identidad, estado público, diagnóstico, health |
| 28–29 | Esquema y migración | 0 |
| 30 | Mutaciones | 10 (§7) |
| 31 | E2E | `e2e/licencia-periodo.spec.ts` con el ayudante firmando períodos a medida; en una corrida compartida no se puede retroceder ni poner `READ_ONLY`: lo prueba el backend |
| 32 | DeepSeek | pruebas puras del comparador (T04) |

`MATERIAL OQ = 0`: el mecanismo (`with_for_update`) y la definición del período existen.

## 6. `/speckit.plan` y compuerta

**Backend.** `core/license.py`: `compare_period(current_start, current_end, incoming_start,
incoming_end) → SAME_PERIOD | NEWER_PERIOD | OLDER_PERIOD | INCOMPARABLE_PERIOD`, puro.
`licensing/service.py::import_license`: tras ancla, firma, identidad y parseo → bloquear
`Installation` y `LicenseState` (`with_for_update`) → releer → comparar → `OLDER`/`INCOMPARABLE`
→ evento de rechazo + 423 sin tocar el estado → si no, el flujo de siempre. **QA**:
`qa/licencia_firmada.py` admite `--anio` y `--periodo`; `e2e/licencia-periodo.spec.ts`;
`e2e/licencia-import.spec.ts` reimporta con el período vigente (reemisión), para no depender del
orden entre pruebas.

**Compuerta (G01–G34):** HEAD, orquestación, dueña, evidencia previa ✅ · período probado y
firmado ✅ · fuente de verdad ✅ · downgrade y carrera reproducidos ✅ · mismo artefacto y mismo
período conocidos ✅ · `READ_ONLY` ✅ · transacción, fila de bloqueo (`Installation` + `LicenseState`),
`with_for_update`, relectura bajo bloqueo ✅ · comparador, contrato de rechazo, residual ✅ ·
compuertas 1 y 2, identidad, estado público, diagnóstico, health ✅ · esquema = migración = 0 ✅ ·
pruebas, carrera, mutaciones, tareas ✅ · `MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 % ✅.
Constitución: P1, P2, P3, P6, P10, P12, P13 (integridad transaccional), P21 (paridad: SQLite
secuencial, PostgreSQL concurrencia), P24, P25 (las altas concurrentes las gobierna la base), P27 ✅.

## 7. Pruebas y mutaciones

**`tests/test_license_period_rollback.py`** (SQLite y PostgreSQL): ROLLA-01 primera activación · 02
mismo artefacto: estado igual, +1 artefacto, +1 evento · 03 mismo período, otros derechos → acepta
(transitorio) · 04 período posterior → acepta · 05 período anterior → 423 `LICENSE_PERIOD_DOWNGRADE`
· 06 tras el rechazo: artefacto vigente, derechos, modo y período intactos; evento
`LICENSE_PERIOD_DOWNGRADE_REJECTED` con `user_id` · 07 activa B, llega A vencida que daría
`READ_ONLY` → rechazada, sigue `FULL_ACCESS` · 08 `READ_ONLY` + posterior → acepta · 09
`READ_ONLY` + anterior → rechaza · 10 vencida + anterior → rechaza · 11 el artefacto viejo
importado hoy sigue viejo · 12 el nombre (`license_id` distinto) no cambia el orden · 13 `kid`
distinto no cambia el orden · 14–16 llamador sin permiso, firma inválida, otra instalación · 17
autofirmada con la clave de la instalación → 423 firma · 18–20 estado público, diagnóstico, health
· 21 período incoherente → 423 `LICENSE_PERIOD_CONFLICT`, intacto.

**`tests/test_license_period_comparator.py`** (DeepSeek, puro): matriz del comparador.

**`tests/test_license_import_race.py`** (PostgreSQL): RACE-01 A vigente, B y C concurrentes
(barrera antes del bloqueo), 8 rondas → final C siempre y **nunca dos hilos dentro de la sección
crítica a la vez** · RACE-02 orden de llegada invertido · RACE-03 C confirma y después entra B →
B relee bajo bloqueo, ve C y recibe 423 · RACE-04 dos reemisiones del mismo período: ambas
admisibles, el resultado sigue el orden de serialización, **documentado como residual** · RACE-05
tras un rechazo la sesión queda limpia y la siguiente importación funciona.

**Mutaciones:** M-01 quitar la comparación → ROLLA-05 · M-02 invertir el comparador → ROLLA-04/05 ·
M-03 aceptar anterior en `READ_ONLY` → ROLLA-09 · M-04 ordenar por `imported_at`/ahora → ROLLA-11 ·
M-05 ordenar por `kid` → ROLLA-13 · M-06 quitar el bloqueo → RACE-01 (dos hilos dentro a la vez;
final B) · M-07 comparar con el estado leído antes del bloqueo → RACE-03 · M-08 persistir antes de
comparar → ROLLA-06 · M-09 rechazar la reemisión del mismo período → ROLLA-03 · M-10 volver a
confiar en la clave de la instalación → ROLLA-17.

## 8. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, recuperación de evidencia, verificación del punto de bloqueo, diseño | todos | CLAUDE | YES | n-a | este documento |
| T02 | `compare_period`; bloqueo, relectura, comparación y rechazo antes de persistir | 200–216 | CLAUDE | **YES** | n-a | `core/license.py`, `licensing/service.py` |
| T03 | `test_license_period_rollback.py` ROLLA-01..21 · `test_license_import_race.py` RACE-01..05 | 230 | CLAUDE | **YES** | n-a | `tests/` |
| T04 | `test_license_period_comparator.py` (matriz pura) | 201–203 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | nuevo |
| T05 | `qa/licencia_firmada.py` (`--anio`, `--periodo`); `e2e/licencia-periodo.spec.ts`; `licencia-import.spec.ts` reemisión | 231 | CLAUDE | **YES** | n-a | `qa/`, `e2e/` |
| T06 | Auditar y aplicar T04; mutaciones M-01..M-10 | 230 | CLAUDE | NO | n-a | — |
| T07 | Backend dirigido y completo (dos motores); E2E dirigido y dos globales | 231 | CLAUDE | NO | n-a | — |
| T08 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T04 (interfaces y fechas sintéticas). `analyze` previo: `BLOCKER` · `CRITICAL` ·
`CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0;
trazabilidad 100 % (§14).

**Autorización de `implement`:** la del encargo «LICENCIA-DOWNGRADE-FIRMADO · FASE A +
LICENCIA-IMPORT-SIN-BLOQUEO», cumplidas sus condiciones.

## 9. Implementación

**Backend (T02, Claude).** `core/license.py`: `compare_period(current_start, current_end,
incoming_start, incoming_end)` puro → `SAME_PERIOD | NEWER_PERIOD | OLDER_PERIOD |
INCOMPARABLE_PERIOD`; igual inicio e igual fin es el mismo período; inicio y fin ambos
posteriores, más nuevo; ambos anteriores, más viejo; cualquier otra forma no describe un período
del contrato y no se ordena. `licensing/service.py::import_license`: tras ancla, firma, identidad y
parseo, bloquea la fila de `Installation` (existe siempre, también antes de la primera licencia) y
la de `LicenseState` con `with_for_update`, relee el estado **bajo el bloqueo**, compara y, si el
resultado es `OLDER_PERIOD` o `INCOMPARABLE_PERIOD`, anota `LICENSE_PERIOD_DOWNGRADE_REJECTED`
(identificador entrante y vigente, fines de período, resultado, `user_id`) y responde 423
`LICENSE_PERIOD_DOWNGRADE` o `LICENSE_PERIOD_CONFLICT` **sin tocar el estado**; si no, el flujo de
siempre. El bloqueo dura hasta el único `commit` de la petición. `ruff` y `mypy` limpios. Sin
esquema, sin migración, sin `revision`, sin cambio de payload.

**QA (T05, Claude).** `qa/licencia_firmada.py`: `--anio <AAAA>` (período anual del contrato) y
`--periodo <inicio> <fin>` (fechas exactas, para reemitir el vigente). `e2e/licencia-periodo.spec.ts`
(4 pruebas; el escenario ordenado en una sola, porque el período vigente es estado compartido de
la corrida y solo avanza). `e2e/licencia-import.spec.ts`: E2E-LICIMP-04 reimporta `LIC-E2E` con el
período **vigente** leído del detalle (una reemisión), para no depender del orden entre pruebas.

**T04 (DeepSeek `deepseek-v4-flash`).** Intento 1: `AUDIT_REJECT` — en CMP-05 construía el
equivalente UTC sumando cuatro horas a un instante con zona, lo que lo desplaza (el propio puente
lo señaló). Reintento 1 con el motivo exacto: `AUDIT_PASS`, 12/12. Coste total $0,0016
(848 + 751 micro-dólares). Egress: fechas sintéticas e interfaz.

**Hallazgo de armado de pruebas, no de producto:** SQLite guarda `DateTime(timezone=True)` sin
zona, y la Fase A lo hace visible: el mismo período se compara como «cuatro horas más nuevo» (se
acepta igual; `SAME_PERIOD` solo se observa en PostgreSQL) y el detector de empates exactos no
aplica allí. Es la misma raíz que `OFFLINE-NAIVE-EN-SQLITE`; se anota en esa fila. La igualdad y la
concurrencia se certifican en PostgreSQL.

**Una prueba existente simulaba la expiración importando una licencia regresiva.**
`tests/test_process_flows.py::test_read_only_blocks_business_writes` importaba, sobre la vigente,
otra con el mismo inicio y fin en el pasado para forzar `READ_ONLY`: justo lo que la Fase A
rechaza (`LICENSE_PERIOD_CONFLICT`). Ahora simula la expiración como ocurre de verdad —el estado
vigente envejece, con fechas coherentes— y vuelve a `FULL_ACCESS` importando una licencia
posterior. Las pruebas de `test_license_import_access.py` y `test_license_trust_anchor.py`
congelan el instante del módulo: sus licencias sintéticas son reemisiones del mismo período, no
retrocesos por segundos.

**Interferencia entre procesos, no producto:** `test_trust_12` falló 3 veces en 9 corridas
dirigidas mientras la suite completa corría en segundo plano, y 0 en 10 sin ella: `conftest.py`
pone la clave de la instalación en un camino **compartido por todos los procesos**
(`tempfile.gettempdir()/kontrol-test-license`), y el otro proceso la reescribía. Registrado como
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` (QA); las certificaciones de este delta se repiten sin
nada en paralelo.

Reintentos: 1 (T04). Rechazos: 1. Coste DeepSeek: **$0,0016**.

## 10. Pruebas y mutaciones

`tests/test_license_period_rollback.py` (18 ejecuciones, SQLite y PostgreSQL) ·
`tests/test_license_period_comparator.py` (12, puras) · `tests/test_license_import_race.py` (4,
PostgreSQL; barrera determinista antes del bloqueo y contador de hilos en la sección crítica, que
entra al releer bajo el bloqueo y sale justo antes de confirmar). Las pruebas ROLLA encadenan
estado (el período solo avanza), así que las mutaciones corren el fichero entero.

`evidence/licencia-downgrade-a/mutaciones-backend.txt`, cada una GOOD→PASS, MUTATED→FAIL, RESTORED→PASS:

| Mutación | La mata |
|---|---|
| M-01 sin comprobación de período | ROLLA (8 fallos) |
| M-02 comparador invertido | ROLLA (10) |
| M-03 se acepta período anterior en `READ_ONLY` | ROLLA-09 |
| M-04 orden por fecha de verificación/importación local | ROLLA (12) |
| M-05 orden por `kid` | ROLLA (10) |
| M-06 sin bloqueo de fila (PostgreSQL) | RACE-01 y 04: dos hilos dentro a la vez |
| M-07 comparar con el estado leído al entrar, antes del bloqueo (PostgreSQL) | RACE-03 (B entra sobre C) y RACE-01 |
| M-08 mutar antes de comparar | ROLLA (8): el rechazo deja rastro |
| M-09 rechazar la reemisión del mismo período (PostgreSQL, donde `SAME_PERIOD` existe) | ROLLA-02, 03 y 21 |
| M-10 volver a confiar en la clave de la instalación además del ancla | ROLLA-17 |

**10/10 muertas.** M-06 y M-07 demuestran que la carrera queda cubierta: sin bloqueo, el contador ve
dos hilos en la sección crítica; comparando con el estado leído antes del bloqueo, B pisa a C.

## 11. Resultados

### El contrato, después (`evidence/licencia-downgrade-a/despues.txt`)

Las mismas importaciones del ciclo bloqueado: período anterior → 423 `LICENSE_PERIOD_DOWNGRADE`
(también con más derechos, también la vencida que dejaba `READ_ONLY`); misma licencia → 200, estado
igual, artefacto y evento añadidos; período posterior → 200; reemisión del mismo período → 200
(transitorio) y su artefacto anterior otra vez → 200 (**residual**); período incoherente → 423
`LICENSE_PERIOD_CONFLICT`. Eventos de rechazo con identificador, vigente y resultado.

### Certificación E2E, base nueva por corrida y ancla explícita (`corridas-globales.txt`)

| Corrida | Resultado |
|---|---|
| Dirigida: `licencia-periodo` + `licencia-import` + `licencia` + `diagnostico` | **28/28** |
| Global 1 | **228 / 0 / 40** (224 + 4 nuevas) |
| Global 2 | **228 / 0 / 40** |

La concurrencia no se prueba desde el navegador: la autoridad es `test_license_import_race.py`
sobre PostgreSQL.

### Backend (`backend-y-frontend.txt`)

| Suite | Resultado | Línea base |
|---|---|---|
| Backend SQLite, completa | **43 fallos / 1 142 pasan / 1 009 omitidas** (122 s): 42 de documentos sin `clamscan` + la intermitente de hilo `test_auth_session_rotation`; las 4 omitidas nuevas son la carrera, que solo corre en PostgreSQL. Composición de línea base. (Una corrida previa, con `test_process_flows` aún importando una licencia regresiva, dio 44: ese fallo era el contrato nuevo y la prueba se adaptó) | 42 docs sin `clamscan` + 1–2 intermitentes de hilo |
| Backend PostgreSQL, completa | **37 fallos / 2 130 pasan / 27 omitidas** (21 min): 10 + 25 de documentos sin `clamscan`, 2 de `test_n9_integrity`. Composición idéntica a la línea base; +34 ejecuciones nuevas | 37: docs sin `clamscan` + 2 de `test_n9_integrity` |
| Licenciamiento dirigido (rollback, comparador, carrera, import, ancla, status, central, engine) | **184 pasan + 4 omitidas (la carrera) ×3 en SQLite · 188 pasan ×2 en PostgreSQL**, sin nada en paralelo; once ficheros | |
| Frontend de producto | **0 cambios**; `eslint` de los E2E limpio | |

## 12. Deudas

**Cerrada:** `LICENCIA-IMPORT-SIN-BLOQUEO`.

**`LICENCIA-DOWNGRADE-FIRMADO`: PARTIALLY_CONVERGED / OPEN.** Cerrado el retroceso **entre
períodos** y la carrera; abierto el orden **dentro** del período.

**Nueva, registrada (`SECURITY_RESIDUAL`):** `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` — dos
reemisiones distintas del mismo período no se ordenan con lo que viaja firmado; la Fase A acepta
ambas (DOC-07 §7.1) y, en concurrencia, la que queda es la última serializada. Objetivo ratificado
por la dueña, **sin implementar**: `revision` firmada, monótona, por instalación y período (período
primero; a igual período, `revision` mayor; igual `revision` e igual payload, idempotente; igual
`revision` y distinto payload, conflicto). Exige cambiar DOC-07 §10.2 y el emisor, y una regla de
compatibilidad para paquetes sin `revision`.

**Anotado en `OFFLINE-NAIVE-EN-SQLITE`:** SQLite guarda las fechas con zona sin zona; el mismo
período se ve «cuatro horas más nuevo» en SQLite.

**Siguen abiertas, sin tocar:** `LICENCIA-SIN-ROTACION-DE-CLAVE`, `LICENCIA-ESTADO-SIN-REVERIFICAR`.

## 13. Veredicto

**Fase A convergida.** Una licencia firmada de período anterior ya no sustituye a la vigente —ni
cuando la vigente está vencida o en solo lectura—; una posterior sigue entrando; la misma licencia
sigue siendo idempotente; la reemisión del mismo período entra como permite el contrato, y queda
dicho que ese tramo no está ordenado. Las importaciones pasan de una en una sobre la fila de la
instalación, releyendo el estado bajo el bloqueo: B y C concurrentes terminan siempre en C.
Compuertas 1 y 2, identidad, criptografía, payload, fechas, zona horaria, estado público,
diagnóstico, health, esquema y migraciones: intactos.

| | |
|---|---|
| `OLD_PERIOD_ACCEPTED` · `COMPARATOR_REVERSED` · `CURRENT_READ_BEFORE_LOCK` · `MISSING_FOR_UPDATE` · `LOCK_RELEASED_BEFORE_PERSIST` · `COMMIT_BETWEEN_COMPARE_AND_PERSIST` | 0 |
| `LOST_UPDATE` · `CONCURRENT_B_OVERWRITES_C` · `MUTATION_BEFORE_CHECK` · `PARTIAL_STATE_ON_REJECT` | 0 |
| `SAME_PERIOD_REISSUE_REJECTED` (§7.1) · `SAME_ARTIFACT_IDEMPOTENCY_BROKEN` | 0 |
| `IMPORT_TIMESTAMP_AS_VERSION` · `FILENAME_AS_VERSION` · `KID_AS_VERSION` · `LOCAL_CLOCK_AS_VERSION` | 0 |
| `CALLER_AUTH_REGRESSION` · `TRUST_ANCHOR_REGRESSION` · `INSTALLATION_IDENTITY_REGRESSION` · `PUBLIC_STATUS_REGRESSION` · `DIAGNOSTICS_REGRESSION` · `HEALTH_REGRESSION` | 0 |
| `REVISION_IMPLEMENTED` · `PAYLOAD_CHANGE` · `DOC07_CHANGE` · `EMITTER_CHANGE` · `SCHEMA_CHANGE` · `MIGRATION` · `CRYPTO_CHANGE` · `TIMEZONE_CHANGE` | 0 |
| `SECURITY_RESIDUAL` | `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` (registrada) |
| `RETRY_WORKAROUND` · `SLEEP_WORKAROUND` · `SKIP_WORKAROUND` (el `skipif` de la carrera sin PostgreSQL es el marcador existente del repositorio) | 0 |
| `STATUS` | `LICENCIA-IMPORT-SIN-BLOQUEO` **CONVERGED** · `LICENCIA-DOWNGRADE-FIRMADO` **PARTIALLY_CONVERGED** |

## 14. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| FR-010-200 período anterior no sustituye | ROLLA-05, 07, 09, 10; E2E-ROLLA-01..08; M-01 | ✅ |
| FR-010-201..203 semántica del período, no `period_end` aislado, ni reloj, nombre o `kid` | CMP-01..10; ROLLA-11, 12, 13; M-02, M-04, M-05 | ✅ |
| FR-010-204 · 205 posterior entra; primera activación | ROLLA-04, 01; RACE-05; E2E-ROLLA-01 (paso 4) | ✅ |
| FR-010-206..209 mismo artefacto; reemisión transitoria; residual registrado | ROLLA-02, 03; RACE-04; E2E-ROLLA-01 (paso 3); M-09; §12 | ✅ |
| FR-010-210..212 serialización, relectura bajo bloqueo, B/C → C | RACE-01, 03; M-06, M-07 | ✅ |
| FR-010-213 rechazo sin mutación | ROLLA-06, 21; M-08 | ✅ |
| FR-010-214..216 `READ_ONLY` renueva; `READ_ONLY` y vencida no retroceden | ROLLA-08, 09, 10; M-03 | ✅ |
| FR-010-217..221 compuertas 1 y 2; firma; identidad | ROLLA-14..17; E2E-ROLLA-09, 10; M-10 | ✅ |
| FR-010-222..224 estado público, diagnóstico, health | ROLLA-18..20; E2E-ROLLA-11 | ✅ |
| FR-010-225..229 payload, criptografía, zona, esquema, sin `revision` | diff: `models.py`, `alembic/`, `parse_license_payload`, `verify_license_signature` sin cambios | ✅ |
| FR-010-230 concurrencia real en PostgreSQL | RACE-01..05, estables en tres pasadas | ✅ |
| FR-010-231 E2E con base efímera y ancla explícita | dirigida 28/28; dos globales | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0;
`UNKNOWN` = 0; trazabilidad 100 %.
