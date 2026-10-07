# SPEC 004 · DELTA DIRIGIDO — `revision` FIRMADA POR PERÍODO (DETENIDO ANTES DE IMPLEMENTAR)

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Continúa `spec004-licencia-downgrade-fase-a-delta.md`. No se
> crea otra Spec. Deuda: `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`; cierre definitivo de
> `LICENCIA-DOWNGRADE-FIRMADO` condicionado a ella.
>
> **Veredicto: `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN — BLOCKED BY ISSUER IMPLEMENTATION
> AVAILABILITY`.** La compatibilidad canónica de las licencias ya emitidas está **probada** (§3). El
> emisor que debe asignar la `revision` —la Autoridad Central de Licencias del propietario— **no
> existe** en este repositorio ni en ninguno accesible: aquí solo hay el cliente y firmantes
> sintéticos de QA, y el hospedaje de la autoridad sigue en `BUSINESS_DECISION_PENDING` (D0-06).
> Implementar solo el lado cliente sería fingir el cierre. Nada implementado; `DEEPSEEK CALLS = 0`.
> `LICENCIA-DOWNGRADE-FIRMADO` sigue `PARTIALLY_CONVERGED / OPEN`.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `2007eae` / **`2007eae`** / `2007eae` / `develop` / limpio · `COMMITS_AFTER_2007EAE = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2`. **`DEEPSEEK CALLS = 0`** |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` |
| `ISSUER_OWNER` | **Autoridad Central de Licencias** (DOC-07 §4.1, §11.1, §12.1; ADR-D0-006): **componente externo, no presente en el repositorio**; hospedaje `BUSINESS_DECISION_PENDING` (D0-06) |
| `INSTALLATION_OWNER` | Master 052: no aplica (el aprovisionamiento del paquete lo hace el emisor) |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisiones de la dueña (D1–D10), ratificadas y recogidas íntegras en §5 para cuando el emisor
exista:** período primero; `revision` entera positiva, firmada, monótona por instalación + período,
asignada por el emisor (1, 2, 3…); `kid` no ordena; transición legacy (misma legacy idempotente,
otra legacy del mismo período rechazada, revisionada ≥ 1 aceptada, legacy tras revisionada
rechazada); sin licencia, legacy o revisionada válidas entran; `revision` no se compara entre
períodos; este ciclo podía modificar DOC-07, el paquete, el canonicalizador, el emisor y el QA;
migración solo si el emisor la necesita y se demuestra inevitable.

## 2. Inventario (W04–W12)

### El paquete y el modelo (`app/core/license.py::LicenseData`, `parse_license_payload`)

| Campo | Tipo | Obligatorio | Firmado | En legacy | Emisor | Consumidor cliente |
|---|---|---|---|---|---|---|
| `license_id`, `installation_id` | texto | sí | sí | sí | autoridad | identidad del paquete; ligadura |
| `customer_id`, `contract_id`, `company_tax_id` | texto | no | sí | sí | autoridad | informativos |
| `period_start`, `period_end` | fecha-hora | sí | sí | sí | autoridad | **orden entre períodos (Fase A)**, modo |
| `critical_warning_start`, `read_only_start` | fecha-hora | no (derivan de `period_end`) | sí | sí | autoridad | modo |
| `entitlements`, `minimum_version` | objeto, texto | no | sí | sí | autoridad | derechos, versión |
| `kid` | texto | no | sí | sí | autoridad | identificador de **clave**; no ordena (D3) |
| `issuer`, `plan` | texto | no | sí (si vienen) | sí | autoridad | no parseados |
| **`revision`** | — | **no existe** | — | **ausente** | — | — |

### Canonicalización y verificación

| | |
|---|---|
| `CANONICALIZER` · `SERIALIZER` | `json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")` (`core/license.py:86`; igual en `service._payload_hash`) sobre **el diccionario recibido** |
| `FIELD_ORDERING` | alfabético por clave (`sort_keys`) |
| `NULL_HANDLING` · `UNSET_HANDLING` | una clave con `None` **sí** se serializa (`"revision": null`); una clave **ausente** no aparece. El modelo (`LicenseData`) **no** participa en los bytes |
| `DATETIME_FORMAT` · `NUMBER_FORMAT` · `UTF8_RULE` · `JSON_SEPARATOR_RULE` | las cadenas tal como vienen en el payload; enteros JSON; `ensure_ascii=False`, UTF-8; separadores por defecto de `json.dumps` (`, ` y `: `) |
| `VERIFIER` | `verify_license_signature(payload, firma, pem)`: canoniza el dict recibido y verifica Ed25519; `parse_license_payload` se ejecuta **después** y no puede quitar claves antes de verificar |
| `ARTIFACT_EQUALITY` | `payload_hash` = sha256 de los mismos bytes canónicos (Fase A lo usa como «misma licencia») |

### El emisor

| | |
|---|---|
| `ISSUER_PRESENT_IN_REPO` | **NO**. En `app/` la única clave privada que se genera es la de la **instalación** (`get_or_create_installation`), que identifica a la instalación y no emite licencias. En `qa/` y `scripts/` hay **firmantes sintéticos** (`licencia_firmada.py`, `pg-e2e-seed.py`, `e2e_corrida.py`, `activate-test-license.sh`, `setup.sh`, bootstraps): stand-ins de prueba, no un emisor |
| `ISSUER_SERVICE` | la **Autoridad Central de Licencias** (DOC-07 §4.1: «plataforma separada, administrada por el propietario»; §12.1 API central: `POST /licensing/installations/{id}/activate`, `/payments/{id}/confirm`, `/licenses/{id}/revoke`, `GET /licenses/{id}/artifact`…). **Ninguna de esas rutas existe en el repositorio**; `sync_license` es un **cliente** (`urllib`) de ese servidor remoto y el contrato v1 solo devuelve estado, vencimiento y derechos |
| `ISSUANCE_HISTORY_EXISTS` | solo en el modelo **central** descrito en DOC-07 §11.1 (`license_artifacts`: «paquetes firmados, hash, kid, fecha y reemplazo»; `license_periods.renewed_at`), **no implementado aquí** |
| `CURRENT_PERSISTENT_STATE` · `CONCURRENT_REISSUE_PROTECTION` | **no evaluables**: no hay emisor |
| ADR-D0-006 | «Clave privada: solo en la autoridad; nunca en imagen, repositorio ni instalación» · «Hospedaje — decisión empresarial … **BUSINESS_DECISION_PENDING**» (D0-06) |

### Fase A recuperada (`spec004-licencia-downgrade-fase-a-delta.md`)

`compare_period` (período firmado, cuatro resultados); bloqueo de `Installation` + `LicenseState`
con `with_for_update` y relectura bajo el bloqueo; rechazo antes de persistir; misma licencia =
`payload_hash`; reemisión del mismo período aceptada; ancla del propietario; firmante sintético por
corrida. Todo ello queda **intacto** y es la base sobre la que la `revision` encajaría.

## 3. Compatibilidad canónica — PROBADA (`evidence/licencia-revision/canonicalizacion.txt`)

Con una legacy **sintética** firmada hoy (441 bytes canónicos):

1. verifica con el verificador actual; `LicenseData` la parsea sin `revision`;
2. **camino compatible:** una revisionada trae `"revision": 1` **dentro** del dict firmado; la
   legacy no lo trae y sus bytes **no cambian** (misma función, mismo dict → `True`); quitar
   `revision` del dict antes de verificar invalida la firma de la revisionada;
3. **camino incompatible, el que no debe hacerse:** reconstruir el payload desde un modelo con
   `revision=None` añade `"revision": null`, cambia los bytes y **rompe la firma legacy**.

`LEGACY_CANONICALIZATION_COMPATIBILITY = PROVEN` mientras `revision` viva solo en el dict firmado
y el verificador siga trabajando sobre el dict recibido (así es hoy): un campo **opcional** en
`LicenseData`, poblado con `payload.get("revision")`, no toca los bytes. Golden fixture: la legacy
sintética de la evidencia (no hay licencias reales en el repositorio).

## 4. El emisor — NO DISPONIBLE

`ISSUER_REVISION_AUTHORITY` e `ISSUER_CONCURRENCY_CONTRACT` **no pueden probarse**: no hay
código que asigne `revision`, ni estado persistente de emisión, ni transacción que proteger. D8
dice que **el emisor** asigna la `revision` y que la instalación **no** la calcula. Lo único que
este repositorio podría hacer es (a) verificar y ordenar `revision` en el cliente y (b) hacer que el
**firmante sintético de QA** la genere. Eso es exactamente «implementar solamente el lado cliente y
fingir cierre»: la monotonicidad real dependería de un emisor que no existe, y el QA se probaría a
sí mismo. **STOP.**

## 5. Lo que queda especificado para cuando el emisor exista (`/speckit.specify`, sin autorización)

FR-010-232..266 (FR-REV-001..035 del encargo), preparados y **no implementados**:

| Bloque | Contenido |
|---|---|
| Paquete (232–234, 258–259) | `revision` entera ≥ 1, dentro del material firmado; legacy = clave **ausente** (bytes intactos); `revision: null`, 0, negativos, decimales, booleanos y cadenas → `LICENSE_INVALID_REVISION` |
| Emisor (235–238, 265) | asignación monótona por instalación + período: 1, 2, 3…; dos reemisiones concurrentes → N+1 y N+2; nunca la misma `revision` para payloads distintos; migración del emisor solo si se demuestra inevitable |
| Orden cliente (239–240, 245–248) | período primero (Fase A); mismo período: `revision` mayor → aceptar; menor → `LICENSE_REVISION_DOWNGRADE`; igual + mismo `payload_hash` → idempotente; igual + distinto payload → `LICENSE_REVISION_CONFLICT`; `revision` no se compara entre períodos |
| Transición legacy (241–244) | misma legacy → idempotente; otra legacy del mismo período → `LICENSE_LEGACY_REISSUE_REQUIRES_REVISION`; legacy vigente + revisionada ≥ 1 → aceptar (fija el linaje); revisionada vigente + legacy → `LICENSE_LEGACY_AFTER_REVISION` |
| Lo que no ordena (249–251) | derechos, `kid`, `imported_at` |
| Lo que se preserva (252–257) | anti-retroceso por período; bloqueo y relectura (la comparación de `revision` dentro de la misma sección crítica); ancla; `license:create`; identidad |
| Concurrencia (254) | `revision` 2 y 3 concurrentes → siempre 3; legacy vigente con `revision` 1 y otra legacy concurrentes → tras serializar, la legacy queda rechazada; regresión de la carrera entre períodos |
| QA (260–261) | el firmante sintético emite revisionadas **y** legacy, explícitamente |
| Fuera (262–264) | rotación de claves, `America/Caracas`, reverificación del estado |
| Certificación (266) | `qa/e2e-run.py`, base efímera, ancla sintética |

Las 38 preguntas de `clarify` tienen respuesta en §2–§4 salvo las del emisor (2, 8, 9, 10, 13,
14, 32–34): **sin emisor no se pueden responder**. `MATERIAL OQ = 1` (disponibilidad del emisor).

## 6. Compuerta constitucional

G01–G03 ✅ · **G04 emisor disponible: ❌** · G05–G06 modelo y canonicalizador ✅ · **G07–G08
compatibilidad legacy y firmas: ✅ probadas** · G09 colocación de `revision` en el material firmado
✅ definida · **G10–G12 persistencia, fuente monótona y concurrencia del emisor: ❌ no evaluables** ·
**G13 migración: ❌ indecidible sin emisor** · G14–G20 reglas cliente y carreras ✅ definidas (sin
implementar) · G21–G23 ✅ preservados · G24 delta de DOC-07 definido, **no aplicado** · G25–G29 ✅ ·
G30–G32 definidos · **G33 `MATERIAL OQ = 0`: ❌** · G34 ✅ · G35 ✅ para el análisis.

**COMPUERTA: NO SUPERADA.** `BLOCKER = 1`. Sin autorización de `implement`; `DEEPSEEK CALLS = 0`.

## 7. Informe para la dueña

1. **Qué está resuelto:** la compatibilidad del paquete (§3): la `revision` puede añadirse sin
   romper una sola licencia emitida, con una regla de una línea (vive en el dict firmado; el modelo
   la lee como opcional; nunca se reconstruye el payload). Las reglas de orden y transición (§5)
   están cerradas y son implementables en el cliente en cuanto exista quién asigne la `revision`.
2. **Qué falta y por qué para:** el **emisor**. DOC-07 lo define como la Autoridad Central de
   Licencias, una plataforma del propietario con su clave privada, su historial de emisiones y su
   API (§12.1). En el repositorio no hay ni una línea de ella, y su hospedaje es la decisión
   empresarial D0-06, aún pendiente. La `revision` es, por D8, **del emisor**; asignarla desde el
   cliente o desde el firmante de QA no es monotonicidad, es apariencia.
3. **Opciones:**
   - **A. Construir el emisor** (la autoridad central o, como mínimo, su herramienta de emisión
     fuera de la instalación): clave privada custodiada (D0-06), historial de emisiones por
     instalación + período, asignación atómica de `revision` (bloqueo o secuencia, con su propia
     persistencia: ahí sí cabe la migración condicional de D10), API o CLI del propietario. Es un
     componente nuevo con su propia Spec: no cabe en un delta de la 004.
   - **B. Herramienta mínima de emisión del propietario** (CLI firmante con un libro de emisiones
     local, fuera del cliente): resuelve la `revision` para pocos clientes sin esperar a la
     plataforma; sigue siendo un emisor con custodia de clave y estado, también fuera de este
     repositorio y de este delta.
   - **C. Esperar a D0-06** y mantener la Fase A tal cual (con el residual documentado).
4. **Recomendación:** decidir **D0-06 y la Spec del emisor** antes de reabrir este ciclo; cuando
   exista el emisor, este delta se ejecuta en una sesión con §3 y §5 como entrada y el cliente se
   cierra en un ciclo (comparador de `revision` dentro de la sección crítica ya existente, errores
   nuevos con la convención de 423, QA emitiendo legacy y revisionadas).
5. **Riesgo mientras tanto:** el residual de la Fase A (`LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`):
   dentro de un período, la reemisión anterior puede volver a importarse; solo puede provocarlo un
   administrador con `license:create` con una licencia firmada por el propietario.

## 8. Deudas y estados

- `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`: **OPEN — BLOCKED BY ISSUER IMPLEMENTATION
  AVAILABILITY**. Compatibilidad canónica probada; reglas cerradas; falta el emisor.
- `LICENCIA-DOWNGRADE-FIRMADO`: sigue **PARTIALLY_CONVERGED / OPEN** (sin cierre falso).
- Nueva decisión de la dueña: **`EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR`** — la Autoridad Central
  (DOC-07 §4.1, §11.1, §12.1) no existe en ningún repositorio accesible; de ella dependen la
  `revision`, la rotación de claves (`LICENCIA-SIN-ROTACION-DE-CLAVE`) y la activación en línea
  (FR-010-002). Opciones A/B/C en §7.
- Sin tocar: `LICENCIA-SIN-ROTACION-DE-CLAVE`, `LICENCIA-ESTADO-SIN-REVERIFICAR`,
  `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`.

## 9. Veredicto

**`LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN — BLOCKED BY ISSUER IMPLEMENTATION AVAILABILITY`.**
Nada implementado; sin cambios en payload, canonicalizador, DOC-07, esquema ni migración; Fase A,
compuertas 1 y 2, estado público, diagnóstico y health intactos; `DEEPSEEK CALLS = 0`;
`NEXT SPEC = 029` no cambia.
