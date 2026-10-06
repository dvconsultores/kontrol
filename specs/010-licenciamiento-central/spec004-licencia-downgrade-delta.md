# SPEC 004 · DELTA DIRIGIDO — UNA LICENCIA ANTERIOR NO SUSTITUYE A LA VIGENTE (DETENIDO ANTES DE IMPLEMENTAR)

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Vive junto a `spec004-licencia-ancla-delta.md`. No se crea
> otra Spec. Deuda: `LICENCIA-DOWNGRADE-FIRMADO`.
>
> **Veredicto: `LICENCIA-DOWNGRADE-FIRMADO — BLOCKED BY LICENSE ORDERING AUTHORITY DECISION`.**
> El modelo real de la licencia ordena las licencias **por período**, y ese orden está en el
> contrato; pero dentro de un mismo período el contrato permite reemitir la licencia (ampliar o
> reducir límites) y ningún campo firmado dice cuál reemisión es la más reciente. Dos licencias
> válidas del mismo período no se pueden ordenar: decisión material de la dueña (§9). No se
> implementó nada; no se creó campo, esquema ni migración.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `3360a50` / **`3360a50`** / `3360a50` / `develop` / limpio · `COMMITS_AFTER_3360A50 = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2`. **`DEEPSEEK CALLS = 0`**: la compuerta no se superó, no hay delegación |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` (FR-001-050..052; DOC-07) |
| `SECURITY_OWNER` | Master 002 → `001-fundacion`: participa (la carrera de importación es una regresión por concurrencia, no por sesión) |
| `INSTALLATION_OWNER` | Master 052: **no aplica** (ningún guion de instalación compara licencias) |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña, ya tomada:** una licencia válida pero objetivamente anterior a la
vigente no puede reemplazarla por el flujo ordinario; misma licencia → idempotencia canónica;
posterior → aceptar; el rollback de emergencia no es parte de este flujo ni se diseña aquí. **Y la
condición crítica:** no inventar qué significa «más nueva», «igual» o «más vieja»; si el modelo no
lo define sin ambigüedad, parar antes de implementar.

**Modelo de seguridad vigente, preservado e intacto:** compuerta 1 (sesión + `license:create`),
compuerta 2 (ancla del propietario, sin fallback). La compuerta 3 (monotonicidad) es la que
queda pendiente de decisión.

## 2. Inventario (W05–W09, W14–W16)

### El paquete firmado (DOC-07 §10.2; `app/core/license.py::LicenseData`)

| Campo | Tipo | Obligatorio | Firmado | Origen | Semántica | Vigencia | Identidad | **Orden** |
|---|---|---|---|---|---|---|---|---|
| `license_id` | texto (`LIC-000142` en el ejemplo del contrato) | sí | sí | autoridad | identificador del paquete; **ninguna regla** lo declara secuencial ni comparable | no | sí (del paquete) | **no** |
| `installation_id` | texto | sí | sí | autoridad | ligadura a la instalación | no | sí | no |
| `customer_id` · `contract_id` · `company_tax_id` | texto | no | sí | autoridad | comerciales | no | no | no |
| `period_start` · `period_end` | fecha-hora con zona | sí | sí | autoridad | **período anual pagado**: 1 abr → 31 mar, `America/Caracas` (§5.1) | sí | no | **sí, parcial** (ver §3) |
| `critical_warning_start` · `read_only_start` | fecha-hora | no (derivan de `period_end`) | sí | autoridad | hitos del mismo período (21 abr, 1 may) | sí | no | derivados del período |
| `entitlements` | objeto | no | sí | autoridad | derechos; **cambian dentro de un período** por reemisión (§7.1) | no | no | no |
| `minimum_version` | texto | no | sí | autoridad | versión mínima de KONTROL | no | no | no |
| `kid` | texto | no | sí | autoridad | identificador de la **clave** (§10.1); `LICENCIA-SIN-ROTACION-DE-CLAVE` sigue abierta; no ordena licencias | no | no | **no** |
| `issuer`, `plan` | texto | no | sí (si vienen) | autoridad | no parseados | no | no | no |
| `issued_at` · `sequence` · `revision` · `serial` · `generation` | — | **no existen** en el paquete ni en el modelo | | | | | | |

### Dónde vive la licencia vigente

`CURRENT_LICENSE_SOURCE_OF_TRUTH = LicenseState` (una fila por instalación, `installation_id`
único): `license_id`, `mode`, las cuatro fechas, `entitlements`, `minimum_version`, `kid`,
`verified_at`, `last_reliable_date`. `LicenseArtifact` guarda **todos** los paquetes importados
(`payload`, `signature_hex`, `payload_hash`, `kid`, `imported_at`, `replaced_at` —nunca se
rellena—): historial versionado, como pide DOC-07 §1. Sin caché. `imported_at` y `created_at` son
locales: no son versión del artefacto.

### El flujo de importación (`service.import_license`)

sesión + `license:create` (dependencia) → cuerpo → ancla del propietario → firma →
`installation_id` → `parse_license_payload` → **leer `LicenseState` sin bloqueo** → calcular modo →
insertar `LicenseArtifact` → **sobrescribir `LicenseState`** → evento `LICENSE_IMPORTED` →
`commit`. **No compara nada con la licencia vigente.** Transaccional en una sesión; sin
`with_for_update` (el mecanismo existe en el repositorio: `identity_access`, `inventory`,
`notifications`), sin versión optimista, sin bloqueo de fichero.

### Lo que dice el contrato (DOC-07)

| Dónde | Texto | Consecuencia para el orden |
|---|---|---|
| §1 Principios | «Las licencias, períodos y derechos **se versionan**. No se sobrescribe el historial de períodos anteriores» | el historial se conserva (lo hace `LicenseArtifact`); «versionar» no define un número de versión en el paquete |
| §5.1 Calendario | período 1 abr → 31 mar; «**Regla de renovación tardía**: … el período renovado sigue siendo del 1 de abril al 31 de marzo. La fecha tardía **no desplaza el ciclo**» | los períodos son anuales, consecutivos y alineados: una renovación tiene **siempre** un `period_start` posterior |
| §7.1 Varias empresas | «El propietario puede **ampliar o reducir el límite mediante una nueva licencia firmada**» | **dentro del mismo período** puede haber más de una licencia válida, con derechos distintos: reemisión legítima |
| §8.2 Propietario | «Al confirmar, crea el **nuevo período anual** … Emite una **nueva licencia firmada**»; «Confirmación duplicada: la operación idempotente devuelve la renovación existente y **no crea otro período**» | renovar = nuevo período; la idempotencia se define en la autoridad por período |
| §10.4 Protección contra retroceso | «Una restauración de backup antigua debe activar reconciliación y **no retroceder el vencimiento**» | el contrato **prohíbe retroceder el vencimiento**: el período es la dimensión protegida |
| §15.1 Manipulación | «Base restaurada con licencia antigua → reconciliar con volumen y autoridad; **no retroceder período**» | ídem |
| §18.2 Aceptación | «La restauración **no retrocede el período**» | ídem |
| §10.2 Contenido mínimo | el paquete de ejemplo | **sin** fecha de emisión ni número de secuencia |
| §11.1 Autoridad central | `license_artifacts`: «paquetes firmados, hash, kid, **fecha** y reemplazo»; `license_periods.renewed_at` | la autoridad **sí** conoce la fecha de cada emisión, pero **no la firma dentro del paquete** que recibe la instalación |

### Reproducción (`evidence/licencia-downgrade/antes.txt`, `carrera.txt`)

Ancla sintética explícita, administrador con `license:create`, licencias anuales DOC-07:

| # | Caso | Hoy |
|---|---|---|
| 2 | A (2026-27) vigente → B (2027-28) | 200, vigente B ✓ |
| 3 | B vigente → **A otra vez** (período anterior) | **200, vigente A**: `DOWNGRADE_ACCEPTED = True` |
| 5 | B sobre B (misma licencia) | 200, estado igual, **+1 artefacto, +1 evento**: `SAME_LICENSE_BEHAVIOR_BEFORE = estado idempotente, historial no deduplicado` |
| 6 | B vigente → A **ampliada** (período anterior, más derechos) | **200**: regresión de período aunque «suba» derechos |
| 8 | B vigente → licencia **vencida** (2024-25) | **200, `READ_ONLY`**: la instalación activa queda en solo lectura |
| 10 | B (2027-28) → B **reducida** (mismo período, menos derechos) | 200 ✓ (reemisión §7.1) |
| 11 | B reducida → **B original** otra vez | **200**: nada en el paquete dice cuál reemisión es la última |
| carrera | A vigente; B (2027) y C (2028) **concurrentes** sobre PostgreSQL, retenidos tras leer el estado | **en 3 de 6 rondas gana B**: `LOST_UPDATE = PROVEN`; gana el último en escribir |

`CURRENT_LICENSE = LicenseState` · `INCOMING_LICENSE = paquete firmado` · `ORDERING_FIELDS =
period_start, period_end (firmados); ningún campo de emisión` · `BEFORE_STATE/AFTER_STATE` en la
evidencia.

## 3. La autoridad de orden, examinada contra O1–O9

| Candidato | O1 firmado | O2 autoridad | O3 no lo controla la instalación | O4 distingue igual/posterior/anterior | O5 histórico | O6–O8 sin nombre de fichero, sin reloj local, sin orden de llegada | O9 determinista | Veredicto |
|---|---|---|---|---|---|---|---|---|
| **Período** (`period_start`/`period_end`) | ✅ | ✅ | ✅ | **entre períodos sí** (anuales, consecutivos, §5.1); **dentro del período no** (§7.1 permite reemitir con otros derechos) | ✅ todas las licencias lo traen | ✅ | ✅ | **orden parcial probado**; insuficiente para el caso intra-período |
| `license_id` | ✅ | ✅ | ✅ | ❌ identificador sin regla de orden en el contrato | — | ✅ | ❌ | descartado |
| `kid` | ✅ | ✅ | ✅ | ❌ identifica la clave, no la licencia | — | — | — | descartado (y `LICENCIA-SIN-ROTACION-DE-CLAVE` sigue abierta) |
| `entitlements` | ✅ | ✅ | ✅ | ❌ ampliar o reducir son ambos legítimos (§7.1) | — | — | — | descartado |
| `imported_at` / `created_at` | ❌ locales | ❌ | ❌ | — | — | ❌ | — | descartado (FR-ROLL-003) |
| Hash del payload | ✅ | — | ✅ | solo **igualdad** («misma licencia») | ✅ | ✅ | ✅ | sirve para «misma licencia», no para orden |
| `issued_at` / `sequence` / `revision` firmados | **no existen** | | | | | | | **no se crean sin decisión** |

**Conclusión:** el modelo da un **orden parcial**. Entre períodos distintos el orden es
inequívoco y el contrato lo protege expresamente («no retroceder el período»). Dentro de un mismo
período, dos licencias válidas y distintas (reemisión §7.1) **no se pueden ordenar** con lo que
viaja firmado. `LICENSE_ORDERING_AUTHORITY = PARTIAL`, no `PROVEN`. `MATERIAL OQ = 1`.

## 4. Por qué no se implementa el tramo probado por separado

El comparador debe devolver `SAME`, `NEWER`, `OLDER` o `INCOMPARABLE`, y «no convertir conflicto
en `NEWER` por defecto». Para el caso intra-período hay que elegir **algo**:

- **aceptar** la reemisión (lo que §7.1 exige para ampliar o reducir límites) es exactamente
  resolver un par no ordenable con «la que llegó después», prohibido por el encargo; además deja
  abierto el retroceso intra-período (#11);
- **rechazar** (cerrado) rompe §7.1: el propietario no podría ampliar ni reducir derechos sin
  esperar al siguiente período;
- **distinguir** la reemisión más reciente exige un dato firmado que el paquete no trae.

Cualquiera de las tres fija el comportamiento de un caso que el contrato no define: decisión de la
dueña. Por eso no se implementa ni siquiera el rechazo entre períodos, que llevaría implícita la
regla intra-período. `MATERIAL_DECISION_REQUIRED`.

## 5. `/speckit.specify` (preparada, no autorizada para `implement`)

FR-010-172..199 (FR-ROLL-001..028 del encargo), **pendientes de la decisión de §9**:

| FR | Requisito |
|---|---|
| 172 · 178 · 179 · 180 · 181 | Una licencia auténtica pero anterior no sustituye a la vigente por el flujo ordinario; se rechaza **antes** de cualquier mutación; licencia, estado efectivo e identidad quedan intactos |
| 173 · 174 · 175 · 176 | La autoridad de orden sale del artefacto firmado; nunca del `imported_at`, del nombre del fichero ni del `kid` |
| 177 | Reimportar el mismo artefacto conserva la idempotencia canónica |
| 182 · 183 · 184 · 185 | Compuertas 1 y 2 intactas (`license:create`; ancla del propietario sin fallback); otra instalación y firma inválida siguen rechazadas |
| 186 | La primera activación sigue funcionando sin licencia vigente |
| 187 · 188 | `READ_ONLY` se renueva con una posterior; vencida o en solo lectura no autoriza importar una **aún más vieja** |
| 189 · 190 · 191 · 192 · 193 · 194 | Concurrencia: sin downgrade por *lost update* (mecanismo existente `with_for_update` sobre `LicenseState`); sin rollback de emergencia, rotación, cambios de vigencia, zona horaria, esquema ni migración |
| 195 · 196 · 197 · 198 · 199 | Pruebas hostiles (ROLL-01..24), prueba de carrera (ROLL-18/19), E2E con `qa/e2e-run.py` y ancla sintética explícita; parar si dos licencias no se ordenan (**es lo que ocurre**) |

## 6. `/speckit.clarify` — 37 preguntas, las resueltas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC004; apoyos 002 y 054 |
| 2–3 | Modelo y campos firmados | §2: el paquete entero se firma; `LicenseData` |
| 4 | Fuente de verdad | `LicenseState`; historial en `LicenseArtifact` |
| 5–8 | Candidatos, semántica, firmados, repetibles | §3: período (parcial), resto descartado; `period_*` se repite legítimamente entre reemisiones |
| 9 | «Misma licencia» | igualdad del payload canónico (`payload_hash`, ya calculado y guardado); `license_id` igual **y** payload distinto no está definido |
| 10 | Idempotencia hoy | estado igual; artefacto y evento añadidos cada vez |
| 11 | Posterior | período posterior: aceptar (probado en el contrato) |
| 12 | Anterior | período anterior: rechazar (contrato «no retroceder el período») |
| 13 | **Mismo período, otro payload** | **permitido por §7.1 y no ordenable: decisión material** |
| 14 | Compatibilidad histórica | todas las licencias traen período (campo obligatorio del parser); ningún paquete trae emisión |
| 15 | Campo de orden ausente | no aplica al período; aplicaría a cualquier campo nuevo (regla de compatibilidad por decidir) |
| 16 | Estado vigente inválido/corrupto | el estado no se re-verifica al importar; DOC-07 §16.2 pide «validar identidad, licencia y última fecha confiable» al restaurar: **no implementado**; se registra (§10), no bloquea |
| 17–20 | Sin licencia · `READ_ONLY` · vencida · aviso | §2 reproducción: hoy todo se acepta; la decisión fija el resto |
| 21–22 | Transacción y bloqueo | una sesión, `commit` al final; **sin bloqueo**; carrera probada |
| 23 | Caché | no hay |
| 24 | Auditoría | `LICENSE_IMPORTED` con `user_id`; los rechazos de firma e identidad dejan evento; un rechazo por orden seguiría el mismo patrón (`LICENSE_ROLLBACK_REJECTED`) **cuando se decida** |
| 25–30 | Regresiones | sin cambios: compuertas 1 y 2, identidad, estado público, diagnóstico, health |
| 31 | Frontend | sin UI de importación (revalidado: ningún `apiFetch` a `activate`/`import`) |
| 32 | Esquema | 0 hoy; la opción B de §9 no exige columna (el payload va en `LicenseArtifact.payload`), pero sí cambio de contrato |
| 33–37 | Estrategia de pruebas, carrera, E2E, mutaciones, DeepSeek | diseñadas en §5/§7 del encargo; **no se ejecutan**: no hay implementación |

`MATERIAL OQ = 1` (#13). `UNKNOWN = 0`.

## 7. Compuerta constitucional

G01–G07 ✅ (HEAD, orquestación, dueña, downgrade reproducido en siete variantes, paquete mapeado,
fuente de verdad, candidatos) · **G08 autoridad de orden probada: ❌ parcial** · G09 el campo
probado (período) está firmado ✅ · G10 «misma licencia» = hash ✅ · **G11 conflicto de igual
orden: ❌ sin contrato** · G12 compatibilidad histórica ✅ (período) · G13–G15 ✅ · G16 transacción
✅ · G17 concurrencia ✅ conocida · **G18 lost update: ❌ probado, sin protección** · G19–G24
preservados ✅ · G25–G26 fuera de alcance ✅ · G27–G28 esquema = migración = 0 ✅ · G29–G31 pruebas,
mutaciones y tareas definidas pero no clasificables para ejecución ✅ · **G32 `MATERIAL OQ = 0`: ❌**
· G33 ✅ · G34 trazabilidad del análisis 100 % ✅.

**COMPUERTA: NO SUPERADA.** `BLOCKER = 1` (decisión material). Sin autorización de `implement`;
`DEEPSEEK CALLS = 0`.

## 8. `/speckit.tasks` (preparadas, sin ejecutar)

| ID | Tarea | EXECUTOR | Estado |
|---|---|---|---|
| T01 | Reconciliación, inventario, contrato, reproducción secuencial y de carrera, análisis O1–O9 | CLAUDE | **hecha** |
| T02 | Comparador `SAME/NEWER/OLDER/INCOMPARABLE` y rechazo antes de mutar, con `with_for_update` sobre `LicenseState` | CLAUDE | bloqueada por §9 |
| T03 | Pruebas ROLL-01..24 y carrera ROLL-18/19 | CLAUDE | bloqueada |
| T04 | Fixtures y matriz mecánica | DEEPSEEK `deepseek-v4-flash` | bloqueada (no se delega sin compuerta) |
| T05 | E2E dirigido y globales; convergencia | CLAUDE | bloqueada |

## 9. Informe para la dueña — `BLOCKED BY LICENSE ORDERING AUTHORITY DECISION`

1. **Campos existentes:** `license_id`, `installation_id`, `customer_id`, `contract_id`,
   `company_tax_id`, `period_start`, `period_end`, `critical_warning_start`, `read_only_start`,
   `entitlements`, `minimum_version`, `kid` (y `issuer`, `plan` sin parsear).
2. **Qué significan:** §2. Solo el período describe **tiempo contractual**; `license_id` es un
   identificador sin regla de orden; `kid` es la clave; los derechos suben y bajan legítimamente.
3. **Cuáles están firmados:** todos (se firma el payload canónico completo).
4. **Cuáles son confiables como orden:** el **período**, entre períodos distintos (contrato
   §5.1, §10.4, §15.1, §18.2). Ninguno dentro del mismo período.
5. **Por qué no bastan:** DOC-07 §7.1 permite reemitir la licencia dentro del período para ampliar
   o reducir límites, y el paquete no lleva fecha ni número de emisión: dos reemisiones del mismo
   período son indistinguibles en orden (reproducido: #10 y #11). Y hoy, además, dos importaciones
   concurrentes pueden dejar la más vieja (carrera, 3/6).
6. **Alternativas concretas:**
   - **A. Orden por período, hoy.** Rechazar `period_end` (y `period_start`) anterior al vigente;
     aceptar período posterior; mismo período con payload distinto → **aceptar** como reemisión
     (§7.1) y anotarlo; mismo payload → idempotente. Más `SELECT … FOR UPDATE` sobre
     `LicenseState`. Sin esquema, sin cambio de paquete, compatible con toda licencia emitida.
     **Deja abierto** el retroceso dentro del período (#11), documentado.
   - **B. Emisión firmada.** La autoridad central añade al paquete un claim firmado de emisión
     (`issued_at` del reloj de la autoridad, o `revision` por instalación, que ya conoce: §11.1
     «fecha y reemplazo», `renewed_at`). Orden total: período, luego emisión; mismo período y
     emisión posterior → aceptar; anterior → rechazar. Exige cambiar DOC-07 §10.2 y el emisor, y
     una **regla de compatibilidad** para paquetes sin el claim (p. ej. tratarlos como emisión 0,
     o rechazarlos tras una fecha). No exige columna: el payload vive en `LicenseArtifact`.
   - **C. Cerrado dentro del período.** Rechazar todo payload distinto del mismo período.
     Contradice §7.1; **no recomendable**.
   - **D. Ordenar por `license_id`.** Sin respaldo contractual; **descartada**.
7. **Riesgos:** A deja el hueco intra-período; B toca contrato y emisor (coordinación con la
   autoridad central, `LICENCIA-SIN-ROTACION-DE-CLAVE` convive); C bloquea la operación comercial
   del propietario; no decidir deja el downgrade entre períodos y la carrera abiertos.
8. **Recomendación:** **A ahora** (cierra el retroceso entre períodos y la carrera, que son los
   casos demostrados graves —`READ_ONLY` por una licencia vieja—, sin tocar contrato ni esquema) y
   **B como objetivo** para el orden total, decidido junto con la autoridad central. Ambas con el
   bloqueo de fila existente.
9. **Compatibilidad histórica:** A es compatible con cualquier licencia emitida (el período es
   obligatorio). B necesita la regla para paquetes anteriores al claim.
10. **Impacto sobre licencias ya emitidas:** ninguna deja de verificar; con A, una licencia
    anterior a la vigente deja de poder importarse (que es el objetivo); con B, las reemisiones
    futuras llevan el claim.

**Hasta la decisión:** el flujo sigue como está, con compuertas 1 y 2 vigentes: solo un
administrador con `license:create` y una licencia firmada por el propietario pueden provocar el
retroceso.

## 10. Deudas

- `LICENCIA-DOWNGRADE-FIRMADO`: **OPEN — BLOCKED BY LICENSE ORDERING AUTHORITY DECISION** (§9).
- **Nueva:** `LICENCIA-IMPORT-SIN-BLOQUEO` — dos importaciones concurrentes leen el mismo estado y
  gana la última en escribir (carrera probada en PostgreSQL, 3/6). Se resolverá con la decisión
  anterior usando `with_for_update` sobre `LicenseState`; se registra aparte porque es un defecto
  de concurrencia, no de orden.
- **Nueva (observación):** `LICENCIA-ESTADO-SIN-REVERIFICAR` — el estado vigente no se vuelve a
  verificar al importar ni al restaurar; DOC-07 §16.2 pide «validar identidad, licencia y última
  fecha confiable» al restaurar. Sin contrato de recuperación en el código; no bloquea este ciclo.
- Siguen abiertas, sin tocar: `LICENCIA-SIN-ROTACION-DE-CLAVE` (el `kid` no ordena ni se
  verifica), `INSTALACION-KEY-REFERENCE-120`.

## 11. Veredicto

**`LICENCIA-DOWNGRADE-FIRMADO — BLOCKED BY LICENSE ORDERING AUTHORITY DECISION`.** Downgrade
reproducido en siete variantes y la carrera en PostgreSQL. El período es la única autoridad de
orden que el contrato sustenta, y es parcial: dentro de un período el contrato permite reemitir y
nada firmado ordena las reemisiones. Sin orden total ni regla contractual para el empate, no se
fija comportamiento. Nada implementado; `DEEPSEEK CALLS = 0`; esquema y migración 0; compuertas
1 y 2, estado público, diagnóstico y health intactos. `NEXT SPEC = 029` no cambia.
