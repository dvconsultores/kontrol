# SPEC 004 · DELTA DIRIGIDO — AUTORIDAD CENTRAL DE LICENCIAS, FASE 1 (EMISOR)

> Iniciado el 2026-10-07. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Continúa `spec004-licencia-revision-delta.md`. No se crea otra
> Spec: el componente vive en `specs/010-licenciamiento-central/central-authority/` (artefactos Spec
> Kit propios) y en `resources/backend/central_authority/` (código). Deudas:
> `EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR` (decisión tomada: construir), materialización de **D0-06**.
>
> **Veredicto: núcleo del emisor `CONVERGED`; API de sync productiva `BLOCKED —
> CENTRAL-SYNC-AUTHORITY-UNDEFINED (MATERIAL_DECISION_REQUIRED)`; D0-06 `CLOSED / IMPLEMENTED`
> en frontera y hospedaje lógico.** La autoridad es un servicio del propietario, separado del
> cliente, agnóstico de proveedor, con base, migraciones, secretos y clave de firma propios; registra
> instalaciones, lleva un libro de emisiones inmutable y emite paquetes firmados con `revision`
> monótona por instalación + período, segura en concurrencia. El cliente los verifica e importa sin
> cambiar un byte de las licencias legacy. No se afirma «production ready» para la sincronización.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `52b133c` / **`52b133c`** / `52b133c` / `develop` / limpio al abrir · `COMMITS_AFTER_52B133C = 0` · 0 bases de corrida |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2`. **`DEEPSEEK CALLS = 1`** (T06, aceptado a la primera) |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` |
| `ISSUER_OWNER` | **Autoridad Central de Licencias** — ahora `resources/backend/central_authority/` (componente del propietario, despliegue separado) |
| `INSTALLATION_OWNER` | Master 052: `Dockerfile.central` y `compose.central.yaml` en la raíz; la pila del cliente no cambia |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

Decisiones de la dueña ratificadas en este encargo: servicio del propietario, aislado del cliente y
agnóstico de proveedor; Python + FastAPI + PostgreSQL + Alembic + contenedor; sin Redis, Celery ni
trabajadores; registro de instalaciones; libro de emisiones *append-only*; `revision` firmada,
entera ≥ 1, primera = 1, reemisión > anterior, concurrentes distintas, sin reutilización para
cargas distintas, reinicio por período, huecos permitidos; `kid` solo identifica la clave (una
clave activa; `LICENCIA-SIN-ROTACION-DE-CLAVE` sigue **OPEN**); operación por CLI del propietario,
sin API de administración pública; esquema y migraciones del cliente = 0; nada contra producción.

## 2. Inventario

| Pieza | Dónde | Qué hace |
|---|---|---|
| Contrato puro | `resources/backend/app/core/license_contract.py` (nuevo) | Canonicalización (`sort_keys`, `ensure_ascii=False`, sobre el dict recibido), Ed25519, parser del paquete con `revision` opcional (ausente = legacy; presente: entero ≥ 1, ni `bool` ni `null`), comparador de período. **Sin SQLAlchemy, sin settings, sin red.** `app/core/license.py` reexporta y conserva `compute_mode`/`ensure_write_allowed` |
| Cliente | `app/modules/licensing/service.py` | `import_license` traduce `LicenseContractError` → 423 (`LICENSE_INVALID_REVISION`, …) y `_payload_hash` usa el contrato. Sin otro cambio; esquema 0 |
| Autoridad | `resources/backend/central_authority/` | `config.py` (prefijo `KONTROL_CENTRAL_`, `env_file .env.central`, prod sin clave Ed25519 válida → no arranca), `models.py` (`cla_installations`, `cla_period_lineages`, `cla_issuances`, `cla_audit_events`; únicos `uq_cla_lineage_installation_period`, `uq_cla_issuance_lineage_revision`, `license_id`), `database.py`, `service.py` (registro idempotente / `INSTALLATION_CONFLICT`; emisión en una transacción con `SELECT … FOR UPDATE` sobre instalación y linaje, `revision = last + 1`, paquete DOC-07 §10.2 + `revision` + `kid`, comprobación con el parser del contrato, firma, libro, auditoría; fallo de firma → `rollback`, la `revision` no se consume), `alembic/` (tabla `cla_alembic_version`, migración `0001_cla_fase1`), `main.py` (solo `/health/live` y `/health/ready`; sin `/docs`, sin `/openapi.json`, **sin sync**), `cli.py` (`register-installation`, `issue-license`, `reissue-license`, `show-issuance`, `list-issuances`; `--operator` obligatorio como etiqueta de atribución, no autenticación), `entrypoint.sh`, `README.md` |
| Despliegue | `Dockerfile.central`, `compose.central.yaml` (raíz) | Imagen que copia solo `app/__init__.py`, `app/core/__init__.py`, `app/core/license_contract.py` y `central_authority/`; usuario sin privilegios; puerto 8010; PostgreSQL propio; secretos por variables obligatorias (`:?`). `docker` no está instalado en la máquina: solo `bash -n` del entrypoint y validación sintáctica; la construcción real queda para el entorno del propietario |
| Pruebas | `resources/backend/tests/central/` | CLA-01..18 (SQLite y PostgreSQL), CLA-PG-01..03 (solo PostgreSQL), REV-01..07 (DeepSeek T06). Firmante **sintético y explícito** en `conftest.py`; nunca una clave real |
| Spec Kit | `central-authority/` | `spec.md` (FR-010-267..321), `clarifications.md`, `research.md`, `plan.md`, `data-model.md`, `contracts/`, `checklist.md`, `tasks.md`, `traceability-matrix.md`, `adr/ADR-004-CLA-001-frontera.md`, `convergence.md` |

## 3. Auditoría de compatibilidad con el cliente

| Caso | Resultado | Prueba |
|---|---|---|
| A. El cliente **importa** el paquete emitido por la autoridad (`revision` presente, `kid` presente) | **Sí**: `parse_license_payload` admite `revision`, la firma se verifica sobre el dict recibido, `import_license` acepta y guarda | CLA-11 |
| B. El cliente **ordena** por `revision` dentro del período | **No todavía**: la Fase A solo compara períodos; `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` sigue **OPEN** y se reabre en un ciclo propio con este emisor como fuente | — (fuera de alcance, declarado) |
| C. Las licencias **legacy** siguen verificando byte a byte | **Sí**: el paquete legacy no se reconstruye con `revision: null`; vector dorado | CLA-12, REV-05/06 |
| D. Un paquete con `revision` inválida (`0`, negativa, `bool`, `null`, texto) | **Rechazo cerrado** 423 `LICENSE_INVALID_REVISION` antes de verificar firma | CLA-13, REV-03/04 |

## 4. Sincronización — BLOQUEADA, no expuesta

El cliente existente (`sync_license`, `default_sync_client`) llama a `/v1/license/sync` **sin
autenticación ligada a la instalación**: no firma la petición ni presenta un secreto propio. Una
autoridad que respondiera a esa llamada emitiría licencias a quien conozca un `installation_id`.
La única definición canónica de esa autenticación es una decisión material de la dueña
(`CENTRAL-SYNC-AUTHORITY-UNDEFINED — MATERIAL_DECISION_REQUIRED`). Por eso `main.py` no expone
sync ni rutas de licencia, y CLA-15 lo prueba. El núcleo del emisor **no depende** de ella.

## 5. Mutaciones (`evidence/central-licensing-authority-phase1/mutaciones.txt`)

Diez mutaciones, **10/10 muertas**, fichero restaurado tras cada una (`GOOD → PASS`, `MUTATED →
FAIL`, `RESTORED → PASS`): M-01 asignar la `revision` sin ningún bloqueo (CLA-PG-01, PostgreSQL) ·
M-02 firmar el paquete sin la `revision` · M-03 el linaje no reinicia por período · M-04 un fallo de
firma consume la `revision` · M-05 prod sin clave genera una · M-06 el `kid` se deriva de la
`revision` · M-07 el registro sobrescribe en silencio · M-08 el parser acepta `revision` 0 · M-09
health expone la URL de la base · M-10 la migración pierde la unicidad `(lineage_id, revision)`
(CLA-PG-02, PostgreSQL).

Dos incidencias de la campaña, resueltas antes de dar por buena ninguna cifra: (1) la primera
versión de M-01 quitaba solo el bloqueo de la instalación y **sobrevivió** porque el bloqueo del
linaje sigue serializando la emisión —mutante equivalente, no defecto—; se rediseñó para quitar
ambos y murió. (2) M-08 escribe un mutante del **mismo tamaño en el mismo segundo**, y Python
reutilizó el `.pyc` del mutante tras restaurar el fuente (dos `RESTORED → FAIL` falsos); la
campaña purga `__pycache__` y corre con `PYTHONDONTWRITEBYTECODE=1`. Se registra como aviso para
futuras campañas (`MUTACION-PYC-OBSOLETO`, nota, no deuda).

## 6. Resultados

| Gate | Resultado |
|---|---|
| `tests/central` SQLite / PostgreSQL | **38 passed, 3 skipped** / **41 passed** |
| Backend completo SQLite | **43 failed, 1180 passed, 1012 skipped** (línea base: 42 de documentos sin `clamscan` + `test_dos_renovaciones_simultaneas…`, que falla igual sobre `git archive 52b133c`, 3/3; +38 pruebas nuevas verdes) · `evidence/…/backend-sqlite-completo.txt` |
| Backend completo PostgreSQL | **37 failed, 2171 passed, 27 skipped** (línea base: 37 de documentos sin `clamscan`; +41 pruebas nuevas verdes; 0 regresiones) · `evidence/…/backend-postgres-completo.txt` |
| `ruff check` · `mypy` (autoridad, contrato, cliente) | limpio · limpio (11 ficheros) |
| Frontend `typecheck` · `lint` · `vitest` | OK · OK · **459/459** (34 ficheros); cambio de producto **0** |
| E2E dirigido (`licencia-import`, `licencia-periodo`) | **22 passed, 0 failed** (`licencia-import`, `licencia-periodo`, `licencia`; base `r20261007t042555…`, limpieza LIMPIA) · `evidence/…/e2e-dirigido.txt` |
| E2E global (`qa/e2e-run.py`, base nueva, ancla sintética) | **228 passed, 0 failed, 40 skipped** (base `r20261007t042614…`, limpieza LIMPIA; igual que la línea base 228/0/40) · `evidence/…/e2e-global.txt` |
| Bases de corrida al cierre | 0 |

## 7. Orquestación

8 tareas: `CLAUDE_ONLY` 7 (T01–T05, T07, T08: diseño, seguridad, criptografía, concurrencia,
migraciones, integración), `DEEPSEEK_ELIGIBLE` 1 (T06, pruebas puras del parser de `revision` con
vectores fijados por Claude). DeepSeek `deepseek-v4-flash`: 1 llamada, 1768/1541 tokens,
$0.000679, `AUDIT_PASS` a la primera, 0 reintentos, 0 rechazos. `EGRESS_CHECK` de T06:
`ENV_FILES=0 SECRETS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PUBLIC_KEYS=0 REAL_LICENSE_FILES=0
REAL_SIGNATURES=0 REAL_INSTALLATION_IDS=0 REAL_LICENSE_PAYLOADS=0 REAL_CUSTOMER_DATA=0
REAL_DB_URLS=0 REAL_QA_HOSTS=0 REAL_PII=0` (solo el contrato puro y vectores sintéticos).

## 8. Seguridad de la clave (verificado)

No está en el repositorio (solo variables de entorno; `.env.central` ignorado por `.gitignore`
del patrón `.env*`), no se guarda en la base, no se genera en prod (CLA-01/01b), no se envía al
cliente (el paquete lleva solo `kid` y firma), no se registra (CLA-17: ni PEM, ni firma, ni URL de
base en los registros), no la devuelve `health` (CLA-15), no hay API que la exponga, y en la
evidencia solo hay claves sintéticas de prueba.

## 9. Deudas y estados

| Deuda | Estado |
|---|---|
| `EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR` | **FASE 1 IMPLEMENTADA** — emisor + registro + libro + CLI + despliegue; sync bloqueada aparte |
| `CENTRAL-SYNC-AUTHORITY-UNDEFINED` | **NUEVA — MATERIAL_DECISION_REQUIRED** (dueña) |
| `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN` | **OPEN** — el emisor ya existe; ciclo del cliente pendiente (no se reabre aquí) |
| `LICENCIA-DOWNGRADE-FIRMADO` | `PARTIALLY_CONVERGED / OPEN` (sin cambio) |
| `LICENCIA-SIN-ROTACION-DE-CLAVE` | **OPEN** (sin cambio; la autoridad opera con una clave y `kid` fijo) |
| D0-06 | **CLOSED / IMPLEMENTED** (frontera y hospedaje lógico; el proveedor físico es operación del propietario) |

`MASTER56`: 56 filas, sin cambio. `NEXT SPEC = 029`, no iniciada.
