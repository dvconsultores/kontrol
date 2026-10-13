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
