# SPEC 001 · Delta dirigida — AUTH-ROTACION-SQLITE-HILOS

Dueña funcional: **002 · Seguridad / sesiones** (inventario MASTER57; REM-AUTH-ROUTE-CRAWL-001), alojada en
`specs/001-fundacion/` como las deltas de auth anteriores (`evidence/.../owner.md`). Apoyo: 054 (arnés). Fecha:
2026-10-14. Rama `develop`, HEAD `7c9c348`. Evidencia en `evidence/auth-rotacion-sqlite-hilos/`.

**Estado: `BLOCKED BY PRODUCT DECISION`.** El ciclo se detiene antes de `/speckit.implement`: producto 0, arnés 0,
pruebas 0, migraciones 0. Solo se añaden esta delta, su evidencia y las actualizaciones de roadmap, puntero y recuento.

## 1. Checkpoint — `checkpoint.md`

`7c9c348` = origin, `develop`, árbol limpio, 0/0/0, puertos libres; MASTER57 57; SPEC057 PLANNED / NOT STARTED; NEXT
MASTER SPEC NOT YET PRIORITIZED; producción fuera de alcance.

## 2. Descubrimiento (`specify` / `clarify` / `research`)

| Paso | Resultado | Evidencia |
|---|---|---|
| W02 dueña y contrato | dueña 002 (inventario) alojada en 001; contrato: exactamente un ganador, perdedor 401 `SESSION_REVOKED`; sin versión ni familia de tokens; `POSTGRES_ATOMICITY_MECHANISM` = bloqueo de fila `with_for_update()` (`bf0ba9e`) | `owner.md`, `contract.md` |
| W03 prueba objetivo | 2 hilos sin barrera de arranque; `TestClient` compartido; una `Session` por petición; aserciones `len == 2`, `200 in`, `count(200) == 1`, `401 in` | `target-test.md` |
| W04 servicio | `SELECT … FOR UPDATE` (ignorado en SQLite) → comprobar → `UPDATE revoked_at` → `INSERT` → `UPDATE hash` → `COMMIT` → auditoría + `COMMIT` | `contract.md` |
| P21/P25/REM | PostgreSQL es la autoridad; P25: forzar la carrera y nunca aceptar 500; precedente PG-only por `with_for_update` (`test_license_import_race.py`) | `p21-p25-rem.md` |
| W06/W07 arnés y TestClient | `make_engine()` = `:memory:` + `StaticPool` + `check_same_thread=False`; `motor_para_hilos` disponible (fichero temporal, una conexión por hilo, limpieza); `raise_server_exceptions=True` | `connection-topology.md` |
| W08–W10 frecuencia | sola ×20 SQLite **15/20 FAIL**; con sonda 9/10, **1 conexión DBAPI 10/10**; módulo ×10 3/10; PostgreSQL ×20 **20/20 PASS** | `frequency-study.md`, `frequency-series.txt` |
| W11 firmas | F1 `[200, 200]` dominante; F6/F8/F11 por la conexión compartida; F9 sesión huérfana; `UNKNOWN = 0` | `failure-signatures.md` |
| W12 topología | `CURRENT_TOPOLOGY = PROVEN`: C1 para todos los hilos; con `motor_para_hilos` C1/C2, mismo datastore | `connection-topology.md`, `topology-traces.txt` |
| W13 entrelazado actual | I1 forzada: 5/5 fallan (3× ganan las dos, 2× hilo muerto) | `controlled-interleaving.md` |
| W14/W15 `motor_para_hilos` | **I1 forzada: 5/5 `[200, 200]`; natural con barrera de arranque 18/20 `[200, 200]`**; 0 excepciones; 2 conexiones; sesión huérfana (+1). La prueba real con `motor_para_hilos` pasa 20/20 solo por escalonamiento (Experimento B) | `controlled-interleaving.md`, `poc-output.txt` |
| Exploración (c) | `BEGIN IMMEDIATE` por transacción serializa: 20/20 `[200, 401]`; no es corrección | `controlled-interleaving.md` |
| W16/W17 causa raíz | capa 1 `HARNESS_SHARED_CONNECTION` (ruido) + **capa 2 `PRODUCT_DEFECT` acotado a SQLite**: la garantía depende solo de `FOR UPDATE`; `CLASSIFICATION = FROZEN` | `root-cause.md` |

`MATERIAL OQ` abierta para la dueña: cómo cerrar la ventana (A/C/D) — ver `product-defect-report.md`.

## 3. Matriz de decisión

Caso **H2** del encargo: la topología actual falla; con `motor_para_hilos` (conexiones distintas, mismo datastore) las dos
renovaciones **siguen ganando** bajo concurrencia controlada válida → `PRODUCT_DEFECT = PROVEN candidate` → **STOP**.
No H1 (la primitiva no basta: pasaría por sincronización), no H3 (sin bloqueos), no H4 (falla sola), no H5 (reproducida).

## 4. `/speckit.specify` — FR-AR-001…031: estado

FR-AR-001/002/008/009/010/012 cumplidos (reproducida, contrato recuperado, topología medida). FR-AR-014/015 **activados**:
con sesiones y conexiones independientes ambas ganan → detenerse antes de modificar producto, veredicto BLOCKED BY PRODUCT
DECISION. FR-AR-013 no aplica (la primitiva no elimina la carrera incorrecta: la expone). FR-AR-006/007/019–025 y 026–031
respetados por no tocar nada. FR-AR-017/018: el error de bloqueo no se reinterpreta (no apareció fuera de la exploración);
no se añade captura amplia.

## 5. `/speckit.clarify` — preguntas cerradas y la abierta

| Pregunta | Respuesta |
|---|---|
| ¿Es la misma causa que almacenes? | Solo la capa de ruido. La aserción del contrato (`[200, 200]`) sobrevive al arnés corregido |
| ¿Es un bloqueo de SQLite? | No: ninguna serie produce `database is locked`; las escrituras se serializan y ambas confirman |
| ¿Es dependencia de orden? | No: 15/20 en proceso nuevo |
| ¿Puede el arnés emular `FOR UPDATE` (`BEGIN IMMEDIATE`)? | Puede (exploración (c)), pero daría verde sin garantía en el producto: descartado como corrección |
| **¿Cómo se cierra la ventana en el producto o se declara el contrato PostgreSQL-only?** | **MATERIAL OQ → dueña** (`product-defect-report.md`: A recomendada; D mínima) |

## 6. `/speckit.plan` y 7. CONSTITUTION GATE

Plan W01–W18 ejecutado; W19–W34 condicionados a la decisión. Gate: G01–G25 cumplidos; **G26 (producto 0 o STOP) → STOP**;
G36 `BLOCKER = 1` (decisión de producto), G42 `MATERIAL OQ = 1`. **GATE: NO PASA para implementar.** Sin autorización de
`implement` por el propio encargo (PRODUCT DEFECT GATE). `DEEPSEEK CALLS = 0`.

## 8. Tareas ejecutadas (todas CLAUDE_ONLY) y pendientes

| Tarea | Estado |
|---|---|
| T01 contrato/repositorio · T02 prueba y servicio · T03 topología · T04 reproducción determinista · T05 causa raíz y clasificación | **COMPLETE** |
| T06 implementación · T07 pruebas/mutaciones · T08 certificación/convergencia | **BLOCKED** hasta la decisión de la dueña (prompt de continuación en el informe) |

## 9. Trazabilidad

histórico → prueba → contrato → P21/P25/REM → servicio → mecanismo PostgreSQL → arnés → TestClient → topología → frecuencia →
firmas → entrelazado actual → entrelazado `motor_para_hilos` → natural ×20 → causa raíz → clasificación → **bloqueo**.
Cobertura 100 % hasta el bloqueo; `UNKNOWN = 0`; `CONTRADICTIONS = 0` (la afirmación «SQLite serializa» del cierre de
REM-AUTH se registra como OBS-05, no como contradicción de contrato: el contrato es «un ganador», y PostgreSQL lo cumple).

## 10. Cierre del ciclo (bloqueado)

Producto 0 · arnés 0 · pruebas 0 · suites completas y E2E no ejecutadas (ninguna fuente cambió; no hay nada que certificar
ni razón para repetir corridas) · evidencia enmascarada · roadmap: fila → **BLOCKED BY PRODUCT DECISION** · puntero y
recuento actualizados · MASTER57 57 · SPEC057 sin cambio · NEXT MASTER SPEC sin cambio.

---

# Continuación · decisión A ratificada (2026-10-14)

`[X] A — CONDITIONAL UPDATE + ROWCOUNT` (`evidence/.../owner-decision-a.md`). El bloqueo de producto queda resuelto por la
dueña; el ciclo continúa dentro de esta delta con autorización en dos etapas (diagnóstico → compuerta material →
implementación). HEAD de partida `123a190` = origin, limpio, 0/0/0, puertos libres.

## 11. `/speckit.specify` — FR-AR-A-001…033

Todos recogidos del encargo; los de contrato (001–009, 015–022, 024–028) se fijan en `conditional-update-contract.md`,
`operation-order.md` y `clock-contract.md`; los de no-cambio (010–014, 023, 029–033) se verifican en §15.

## 12. `/speckit.clarify` — congelado

| Registro | Valor |
|---|---|
| Modelo / tabla / columnas | `identity_access.models.Session` (`AuthSession`) / `sessions` / `id`, `revoked_at`, `updated_at` |
| `UPDATE_PRIMITIVE` | `db.execute(update(AuthSession).where(id == …, revoked_at.is_(None)).values(revoked_at=ahora, updated_at=ahora)).rowcount` — patrón ya existente en `notifications/service.py` |
| `EXECUTION_SITE` · orden | `rotate_session`, tras decode/hash/expiración/usuario y antes de `create_session`; perdedor → 401 `SESSION_REVOKED`; `rowcount ≠ 1` → `RuntimeError` |
| `SESSION_SYNCHRONIZE_OPTION` · ORM | por defecto (`evaluate`); la instancia cargada queda sincronizada y nadie reasigna `revoked_at` por atributo (SA-13) |
| `CLOCK_SOURCE` | `_now()` del servicio (`datetime.now(UTC)`) |
| `with_for_update()` | se conserva |
| Arnés | `motor_para_hilos("auth-session-rotation")` en el fixture del módulo objetivo; `motor_para_hilos("auth-rotacion-atomica")` en el módulo SA |
| OBS-05 | comentario del servicio y frase del cierre de REM-AUTH (`implementation.md`: antes/después) |
| `MATERIAL OQ` | 0 |

## 13. `/speckit.plan`, CONSTITUTION GATE (etapa 1) y `/speckit.tasks`

Plan W01–W30 del encargo. Gate etapa 1 (diagnóstico): G01–G36 cumplidos, `BLOCKER = 0`, `MATERIAL OQ = 0`, `UNKNOWN = 0`,
trazabilidad 100 % → **PASS para el diagnóstico**.

| Tarea | Ficheros | EXECUTOR / MODEL | SECURITY_SENSITIVE / EGRESS_SAFE | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| T01 decisión y contrato | evidencia | CLAUDE / n-a | sí / n-a | — | `owner-decision-a.md`, `conditional-update-contract.md` |
| T02 diseño de la escritura condicional | evidencia | CLAUDE / n-a | sí / n-a | — | `operation-order.md`, `clock-contract.md` |
| T03 diagnóstico rowcount + POC I1 | guion fuera del repo | CLAUDE / n-a | sí / n-a | `cas-poc.py` | 1→0 en los dos motores; I1 SQLite sin bloqueo |
| T04 producto | `app/modules/identity_access/service.py` | CLAUDE / n-a | **sí** / n-a | SA-01…16 | FR-AR-A-001…009, 015–022 |
| T05 arnés | `tests/test_auth_session_rotation.py` (solo el fixture) | CLAUDE / n-a | no / n-a | objetivo ×20, módulo ×10 | FR-AR-A-023/024 |
| T06 pruebas de seguridad | `tests/test_auth_rotacion_atomica.py` (nuevo) | CLAUDE / n-a | sí / n-a | SA-01…16 | verdes en los dos motores |
| T07 mutaciones | copias temporales | CLAUDE / n-a | — | M-01…M-14 | `mutation-campaign.md` |
| T08 certificación y convergencia | docs, roadmap, puntero | CLAUDE / n-a | — | suites, OpenAPI, E2E | §15–§16 |

`DEEPSEEK CALLS = 0` (todo es seguridad/concurrencia: CLAUDE_ONLY).

## 14. Diagnóstico (etapa 1) y compuerta material

| Registro | Valor | Evidencia |
|---|---|---|
| `SQLITE_ROWCOUNT_1 / _2` | 1 / 0 (fichero y `:memory:`) | `rowcount-sqlite.md` |
| `POSTGRES_ROWCOUNT_1 / _2` | 1 / 0 | `rowcount-postgres.md` |
| `SQLITE_I1_CAS_BEHAVIOR` | **PROVEN**: 10/10 un `rowcount 1` y un `rowcount 0` con las dos lecturas antes de la primera escritura; 0 excepciones; 0 `database is locked`; un reemplazo por ronda | `sqlite-i1-poc.md` |
| PostgreSQL I1 | `FOR UPDATE` serializa: el segundo lee ya revocada (5/5) | ídem |
| `SQLITE_LOCK_BLOCKER` · `NEW_MATERIAL_DECISION` | 0 · 0 | — |

**Compuerta material: PASS** → autorización etapa 2 consumida → `/speckit.implement`.

## 15. `/speckit.implement` y resultados

Implementación en `implementation.md` (producto 27 líneas en un fichero; fixture; módulo SA nuevo; REM-AUTH acotado).

| Gate | Resultado | Evidencia |
|---|---|---|
| SA-01 I1 SQLite ×10 · SA-02 PostgreSQL ×5 | 10/10 · 5/5 `[200, 401]`, un reemplazo, 0 excepciones | `controlled-i1-sqlite.md`, `controlled-i1-postgres.md` |
| SA-03 natural SQLite ×20 · módulo ×10 · SA-04 PostgreSQL ×20 | 20/20 · 10/10 · 20/20 (antes: 15/20 fallos sola) | `directed-series-after.txt` |
| SA-05…SA-16 | 17/17 en SQLite y PostgreSQL (módulo SA + módulo objetivo) | `security-directed-tests.md` |
| SA-17/18/19 | ACS 8/8, almacenes PASS, OpenAPI 544/533/11 `BearerAccessToken` sin cambio | `openapi.md` |
| SA-20 | migración 0, esquema 0, modelo 0 | `git diff --stat -- alembic/ models.py` vacío |
| Mutaciones | 14/14 muertas (M-11 con SA-15 añadida tras sobrevivir) | `mutation-campaign.md` |
| Suites completas y E2E | véase §16 | `sqlite-full-1.md`, `sqlite-full-2.md`, `postgres-full.md`, `global-e2e.md` |

## 16. Suites completas, E2E, `/speckit.analyze` final y veredicto

| Corrida | Resultado | Clasificación |
|---|---|---|
| SQLite completa #1 | 1627 / 42 / 1040 (289 s) | 42 = ClamAV (BASELINE); AUTH target 0; +11 pasadas; TARGET_REGRESSION 0; UNKNOWN 0 |
| SQLite completa #2 | 1627 / 42 / 1040 (764 s, carga de máquina) | idéntica prueba por prueba |
| PostgreSQL completa | 2644 / 37 / 28 (860 s) | 35 ClamAV + 2 n9 (BASELINE); +10; TARGET_REGRESSION 0; UNKNOWN 0 |
| OpenAPI | 544 / 533 / 11 · `BearerAccessToken` | sin cambio |
| E2E global | 280 / 0 / 4 (`r20261014t010119…`) | limpia; red y reloj estables |

`final-analyze.md`: todas las métricas a 0, trazabilidad 100 %. **Veredicto: `AUTH-ROTACION-SQLITE-HILOS — CLOSED /
CONVERGED`** (`convergence.md`). OBS-05 cerrada en su punto exacto; OBS-01/02/04/06/07 abiertas. MASTER57 57; SPEC057
PLANNED / NOT STARTED; NEXT MASTER SPEC NOT YET PRIORITIZED; producción fuera de alcance.
