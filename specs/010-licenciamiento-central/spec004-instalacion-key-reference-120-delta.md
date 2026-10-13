# SPEC 004 · Delta dirigida — INSTALACION-KEY-REFERENCE-120 (análisis; bloqueada por decisión)

**Fecha** 2026-10-13 · **Dueña** SPEC004 (identidad de la instalación y licenciamiento) · **Apoyo** SPEC001
(modelo `Installation`, `data-model.md`), SPEC052 (volumen de despliegue), SPEC054 (guarda del runner) ·
**Base** `7e8eb07` · **Rama** `develop` · **Evidencia** `evidence/instalacion-key-reference-120/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `7e8eb07` / `7e8eb07` / `7e8eb07` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_7E8EB07` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Inventario (`inventario.txt`)

`Installation.key_reference: String(120)`, nullable, sin índice, desde `0001_fundacion`. **Un** escritor: el
alta de la instalación persiste `os.path.join(settings.installation_volume_path, "installation_private_key.pem")`,
la ruta **absoluta del contenedor**. **Ningún** lector en el producto: la clave se carga siempre por
`_private_key_path()` (settings) —firma del desafío del sync, reverificación, diagnóstico, rotación de
confianza no tocan la columna—; la API, el OpenAPI y el diagnóstico no la exponen; una prueba la copia
tal cual al «restaurar»; el runner E2E aborta antes de crear la base si la ruta del estado efímero supera
120 (`LARGO_MAXIMO_DE_RUTA`). Despliegue canónico: `/data/license-state` → referencia de 48 caracteres,
margen 72: cualquier volumen configurado de más de 91 caracteres rompe el alta.

**Contrato documental:** la única autoridad es `specs/001-fundacion/data-model.md:29`: «`key_reference
(volumen)` · Identidad persistente; par de claves local». La Spec 010 no tiene ningún requisito sobre el
localizador de la clave; DOC-07 y los ADR no lo mencionan; el delta del sync describe dónde vive la clave
(`installation_volume_path/installation_private_key.pem`), que es la resolución por configuración, no el
contenido de la columna. `CONTRACT_SEMANTICS = UNDEFINED`: «(volumen)» dice dónde está la clave, no si la
referencia es una ruta absoluta, un nombre relativo o un identificador.

## 3. Reproducción (`reproduccion-head.txt`)

Flujo real (`setup.initialize` → alta de la instalación), rutas sintéticas bajo un temporal, sin material de
clave en la evidencia:

| Motor | Volumen | `key_reference` | Resultado |
|---|---|---|---|
| PostgreSQL | corto (18) | 47, absoluta | alta OK (control) |
| **PostgreSQL** | largo (126) | **155**, absoluta | **`sqlalchemy.exc.DataError` ← `psycopg2.errors.StringDataRightTruncation: value too long for type character varying(120)`**: la instalación no se crea |
| SQLite | largo (126) | 155, absoluta | alta OK: SQLite no hace cumplir `VARCHAR(120)` (no sirve como prueba de ausencia del defecto) |

`DEFECT_REPRODUCED = YES`. `ROOT_CAUSE = STORAGE_REFERENCE_COUPLED_TO_CONFIGURABLE_ABSOLUTE_PATH +
FIXED_COLUMN_LENGTH`: los 155 son volumen (126) + separador + `installation_private_key.pem` (28).

## 4. Decisión del ciclo: CAMINO A

El encargo fija la frontera: contrato `ABSOLUTE_PATH` o `UNDEFINED` → no se implementa, porque cambiar
la columna (migración) o cambiar el formato persistido del localizador de material criptográfico son
decisiones de la dueña, y «(volumen)» no basta para declarar ratificada una referencia relativa. No se
usa el límite de 120 como prueba de que «debía ser relativa», ni el nombre `key_reference` como prueba de
nada. **Veredicto: `INSTALACION-KEY-REFERENCE-120 — BLOCKED BY LICENSE STORAGE CONTRACT DECISION`.**
Producto 0, esquema 0, filas 0, runner 0 (la guarda sigue, porque el producto sigue persistiendo la ruta
absoluta).

Dos hechos que pesan en la decisión y no estaban en la hoja de ruta: (1) **la columna no tiene lectores**:
su valor es informativo, y ningún flujo de firma, sync, reverificación o rotación cambia con lo que se
persista en ella; (2) la ruta persistida es la **del contenedor**, no la del host: una reubicación del
volumen en el despliegue ya deja la columna desactualizada hoy, sin que nada lo note.

## 5. Opciones para la dueña

| Opción | Qué cambia | Migración | Compatibilidad | Seguridad | Despliegue | Pruebas | Valoración |
|---|---|---|---|---|---|---|---|
| **A1** `String(120)` → `String(512)` | solo la capacidad | **sí** (ALTER COLUMN, cliente) | total (mismo formato) | ninguna | ninguno; sigue acoplando la columna a la ruta configurable (un volumen > 483 vuelve a romper; improbable) | prueba de largo en PostgreSQL | mínima; no corrige el acoplamiento |
| **A2** `String(120)` → `Text` | capacidad ilimitada | **sí** | total | ninguna | ninguno; mismo acoplamiento, sin límite | ídem | como A1, sin cota |
| **A3** ratificar el contrato: la columna guarda una **referencia relativa al volumen** (`installation_private_key.pem`); las filas absolutas existentes se respetan tal cual; la resolución es «absoluta → se usa; relativa → `join(volumen configurado, ref)`» | el escritor (deja de incluir el volumen) y un resolutor canónico; **sin** migración, **sin** backfill | **no** | probada con fila antigua + fila nueva; hoy nadie lee la columna, así que el riesgo real es nulo | la referencia la genera el producto, no el usuario (sin recorrido de rutas); la clave sigue en el volumen con 0600 | la ubicación física vuelve a ser configuración, que es donde ya vive para los lectores; la guarda del runner se ajusta a lo que de verdad se persiste | KR-01…25 del encargo (largo, corto, formato, legado, resolución, firma, sync, arranque, sin backfill, sin migración) | **recomendada**: elimina el acoplamiento y el defecto sin tocar el esquema; coste: un cambio de contrato documentado en `data-model.md` y en la Spec 004 |
| **A4** (complementaria) declarar la columna informativa y dejar de persistir la ruta (`NULL` para altas nuevas) | el escritor | no | las filas antiguas conservan su valor | ninguna | ninguno | largo/corto | honesta con el hecho de que nadie la lee, pero pierde la trazabilidad de dónde se dejó la clave; solo si la dueña no quiere ningún localizador |

**Recomendación:** A3 (y, si se ratifica, el runner deja de medir la ruta absoluta y pasa a comprobar el
invariante real: la referencia persistida no depende del largo del volumen). A1/A2 solo si la dueña quiere
conservar la ruta absoluta como dato; entonces hay que autorizar la migración expresamente.

## 6. Spec Kit hasta la compuerta

`/speckit.specify`: FR-KR-001…029 del encargo, con 003 (nunca truncar en silencio) y 004 (las filas
absolutas siguen válidas) como invariantes de cualquier opción. `/speckit.clarify` 1–30: resueltos en §2–§3
salvo 17–19 y 23 (formato nuevo, regla de resolución, recorrido de rutas, compatibilidad), que dependen de
la opción elegida. Compuerta: G01–G18 ✔ (reproducción, control, SQLite, despliegue, guarda, exposición,
clasificación A, UNKNOWN 0); G19 **no se cumple** (el contrato no permite hoy una referencia relativa sin
decisión) → `IMPLEMENTATION_AUTHORIZED = NO`. `DEFECT_REPRODUCED YES · CONTRACT_SEMANTICS UNDEFINED
(probado) · READERS_COMPLETE YES · WRITERS_COMPLETE YES · PATH_DECISION A · SCHEMA_CHANGE 0 · ROW_REWRITE 0 ·
PRIVATE_KEY_MATERIAL_IN_EVIDENCE 0 · BLOCKER 1 (decisión de la dueña) · MATERIAL OQ 1 (la misma) · UNKNOWN 0`.
Orquestación: 0 DeepSeek. Trazabilidad: deuda → columna → escritor → (sin lectores) → contrato →
reproducción → camino A → opciones → decisión: 100 %.

## 7. Qué queda y qué no cambia

La deuda sigue **OPEN**, ahora con reproducción, inventario completo, contrato localizado y opciones.
Sin cambio: producto, esquema, filas, runner, pruebas, licencia, sync, rotación, reverificación, OpenAPI,
409 de picking, typecheck y captura E2E, omisiones de clamscan, keep-alive, versión, MASTER57, SPEC057,
puntero. `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` no se toca.

## 8. Decisión de la dueña y contrato ratificado (2026-10-13)

`[X] A3` (`evidence/instalacion-key-reference-120/decision-de-la-duena.txt`, literal). Contrato:
`Installation.key_reference` es una referencia de almacenamiento al material criptográfico local; para
las altas nuevas es **relativa al volumen de instalación** (`installation_private_key.pem`); las filas
históricas con ruta absoluta siguen valiendo tal cual (sin migración, sin backfill, sin reescritura, sin
truncar); resolución: `None` → ruta canónica por configuración; absoluta → tal cual; relativa →
`installation_volume_path/ref`; nunca contra el directorio de trabajo; la referencia la genera el
producto; nunca material de clave en la base. Documentado en `specs/001-fundacion/data-model.md`
(fila `Installation`) y en este delta (artefacto de la Spec 004).

## 9. Spec Kit de la continuación

**Specify:** FR-KR-001…031 del encargo, tal cual. **Clarify (21 puntos):** 1–2 nombre canónico y constante
`INSTALLATION_PRIVATE_KEY_FILENAME` en `licensing/service.py` (la usan el escritor y `_private_key_path`);
3 escritor `get_or_create_installation`; 4 resolutor `resolve_key_reference` en el mismo módulo; 5 `None`
→ `_private_key_path()`; 6 absoluta → tal cual; 7 relativa → `join(volumen, ref)`; 8–9 seguridad: solo
un nombre de fichero simple (vacío, `.`, `..`, separadores → `INSTALLATION_KEY_REFERENCE_INVALID`, 500);
10 lectores en producto: 0, revalidado; 11 el resolutor **no** se introduce en los cargadores (siguen por
configuración: sin lectores nuevos); lo consumen las pruebas de compatibilidad; 12 runner: la guarda por
longitud desaparece y `verificar_backend` comprueba contra la base que la instalación de la corrida
persiste una referencia relativa (manifiesto `instalacion`); 13–15 migración 0, backfill 0, reescritura 0;
16–19 firma, sync, identidad y diagnóstico: por configuración, sin cambio; 20–21 KR-01…25 y M-01…M-12.
`MATERIAL OQ 0 · UNKNOWN 0`.

**Compuerta:** G01–G30 ✔ (G03 decisión explícita; G06 contrato actualizado; G07 referencia canónica; G08
escritor; G09 lectores 0; G10–G12 resolución; G13 seguridad; G14 invariante del runner; G15–G19 sin
migración, columna, backfill, reescritura ni cambio criptográfico; G20–G21 pruebas y mutaciones). **PASS.**
Autorización: la casilla `[X] A3`.

| Tarea | Requisito | Dueña | EXECUTOR | SEC | EGRESS | Ficheros | Acción | DONE_WHEN | Prueba | Mutación |
|---|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001/002/005–009/011–016 | 004 | CLAUDE | sí (clave) | n-a | `licensing/service.py` | constante, escritor relativo, `resolve_key_reference` con rechazo de recorridos | KR-01…09, 12, 16 | `test_installation_key_reference.py` | M-01…M-07, M-10, M-11 |
| T02 | FR-003/004 | 001/004 | CLAUDE | no | n-a | `data-model.md` | contrato ratificado | fila `Installation` | — | — |
| T03 | FR-022 | 054 | CLAUDE | no | n-a | `qa/e2e_corrida.py`, `tests/test_e2e_corrida.py` | guarda de longitud → `comprobar_referencia_de_clave` contra la base; pruebas 09 (ruta larga ya no bloquea) y 09b (ruta absoluta en la base → `SALIDA_PREPARACION`) | runner 19/19 | ídem | M-09 |
| T04 | FR-010/017–021/024–031 | 004 | CLAUDE | no | n-a | — | regresiones de licencia/sync/seguridad, diagnóstico, OpenAPI, picking | verdes | KR-21, suites dirigidas | M-08, M-12 |
| T05 | FR-030/031 | 004 | CLAUDE | no | n-a | hoja de ruta, puntero, recuento | cerrar; puntero; 57 | ficheros | — | — |

`CLAUDE_ONLY 5 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0`.

## 10. Implementación (Claude)

**`app/modules/licensing/service.py`** (+30/−3): `INSTALLATION_PRIVATE_KEY_FILENAME`;
`_private_key_path()` la usa; `resolve_key_reference(reference)` (`None` → canónica; absoluta → tal cual;
relativa → solo nombre simple, `join(volumen, ref)`; rechazo con `INSTALLATION_KEY_REFERENCE_INVALID`);
el alta persiste `key_reference=INSTALLATION_PRIVATE_KEY_FILENAME`. Los cargadores (`_installation_private_key`
y compañía) **no cambian**: siguen por configuración; no hay lectores nuevos de la columna.

**`qa/e2e_corrida.py`** (+24/−7): desaparece `LARGO_MAXIMO_DE_RUTA` y el aborto por longitud de ruta;
`comprobar_referencia_de_clave()` lee `installations.key_reference` de la base de la corrida tras la
siembra y el arranque del backend y exige exactamente una instalación con referencia no nula, no absoluta,
sin separadores y ≤ 120 (`LARGO_MAXIMO_DE_REFERENCIA`); el resultado va al manifiesto
(`instalacion = {key_reference, relativa, largo_del_volumen}`).

**`tests/test_e2e_corrida.py`**: `09` pasa a probar que una ruta de estado de más de 120 caracteres ya no
impide la corrida y que el manifiesto registra la referencia relativa; `09b` simula el defecto (una ruta
absoluta en la base tras la siembra) y exige `SALIDA_PREPARACION` con el nombre de la deuda en el error.

**`tests/test_installation_key_reference.py`** (nuevo): KR-01/02/03/04 (alta con volumen corto, medio y
largo → siempre la referencia canónica, clave en el volumen con 0600), KR-25 (PostgreSQL, el volumen que
rompía), KR-05/06/15 (fila absoluta histórica se usa tal cual y no se reescribe tras un ciclo de alta),
KR-07/13 (relativa contra el volumen configurado y reubicado; `None` → canónica; nunca el cwd), KR-16
(siete referencias fuera del contrato rechazadas), KR-08…11 (clave sintética carga y firma el sobre del
desafío con referencia absoluta y relativa; el cargador canónico lee la misma), KR-12 (identidad y
`installation_request_payload` con absoluta, relativa y `None`, sin exponer la referencia), KR-18/19
(columna `String(120)` nullable y cabeza `0057_spec047_notifications`), KR-21 (`/system/diagnostics` con
`license:view` no trae `key_reference`, el nombre del fichero ni la ruta). `data-model.md`: contrato.

**Sin cambio:** esquema, migraciones, filas, protocolo del sync, algoritmo y ubicación de la clave,
reverificación, rotación, revisión, OpenAPI, frontend.

## 11. Resultados (`suites-dirigidas.txt`, `mutaciones.txt`, `frontend-gates.txt`)

| Gate | Resultado |
|---|---|
| KR SQLite | 20 pasan + 1 omitida por diseño (KR-25, autoridad PostgreSQL) |
| KR + runner PostgreSQL | **58/58**: KR 21/21 (incluida KR-25: el volumen de 126 que rompía el alta la completa) y `test_e2e_corrida` 19/19 (09 ruta larga ya no bloquea; 09b ruta absoluta en la base → `SALIDA_PREPARACION`) |
| Regresiones dirigidas PostgreSQL (sync, tasa, rotación, revisión, carrera de revisión, reverificación, ancla, acceso a licencia e importación, carrera de instalación, acceso al sistema, OpenAPI, picking 409) | verdes (ver listado) |
| `ruff` · `mypy` del módulo | limpio · sin incidencias |
| Frontend (producto 0): typecheck (src + herramientas + e2e) · lint · Vitest · build | ✔ · ✔ · **477/477** · ✔ |

**Mutaciones** (GOOD → PASS, MUTATED → FAIL, RESTORED → PASS; PostgreSQL; `__pycache__` purgado;
`PYTHONDONTWRITEBYTECODE=1`):

| Mutante | Lo mata | Resultado |
|---|---|---|
| M-01 el escritor vuelve a la ruta absoluta | KR-01/04, KR-25 | muere |
| M-02 la relativa se resuelve desde el cwd | KR-07, KR-08/09 | muere |
| M-03 la absoluta histórica se trata como relativa | KR-05/06 | muere |
| M-04 reescribe la fila histórica (en la rama tras el candado) | — | **equivalente por anclaje del guion** (esa rama nunca se alcanza: la primera comprobación devuelve antes); declarado y sustituido |
| M-04b reescribe la fila histórica en el retorno temprano | KR-05/06/15 | muere |
| M-05 trunca la referencia a 120 | KR-01/03/04 | muere |
| M-06 nombre de fichero equivocado | KR-07, KR-08/09 | muere |
| M-07 permite `..`/separadores | KR-16 | muere |
| M-08 el diagnóstico expone la referencia | KR-21 | muere |
| M-09 el runner deja de comprobar el invariante | `test_e2ecorrida_09b` | muere |
| M-10 rompe la carga de la clave del desafío | KR-08…11 | muere |
| M-11 la referencia nueva lleva el prefijo del volumen | KR-01/03/04 | muere |
| M-12 cambia el tipo de la columna | KR-18/19 | muere |

12 mutantes aplicables, **12 muertos**; 1 equivalente declarado y sustituido.

## 12. Suites completas y E2E (`backend-*-completo.txt`, `intermitente-licensing-central.txt`, `e2e-global-{1,2}.txt`)

| Motor | Resultado | Frente a la base (44/1507/1021 · 37/2508/27) | Clasificación |
|---|---|---|---|
| SQLite | **43 / 1553 / 1040** | lista `FAILED` idéntica salvo −1 (`test_auth_session_rotation::test_dos_renovaciones…`, KNOWN_INTERMITTENT de hilos, pasó esta vez); +46 pasan (suites de los ciclos del día incluida esta) | 42 documentales sin `clamscan` + carrera de almacenes = BASELINE |
| PostgreSQL | **38 / 2570 / 28** | +1: `test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event` (KNOWN_INTERMITTENT de tiempo; dirigido **PASSED ×3**) | 35 documentales + 2 `test_n9_integrity` = BASELINE |

`TARGET_REGRESSION 0 · NEW_INDEPENDENT_DEBT 0 · UNKNOWN 0`.

| Corrida | Id | passed | failed | skipped | Suite | Manifiesto `instalacion` | Limpieza |
|---|---|---|---|---|---|---|---|
| Global 1 | `r20261013t040745p4055406ndacea7` | **273** | **0** | **4** | 275 s | `{key_reference: installation_private_key.pem, relativa: true, largo_del_volumen: 56}` | LIMPIA |
| Global 2 | `r20261013t041232p4081801n710b10` | **273** | **0** | **4** | 274 s | ídem | LIMPIA |

Las 4 omitidas son las de `ENTORNO-SIN-CLAMSCAN`; bases residuales **0**; corridas adicionales ninguna. El
runner ya comprueba contra la base el invariante del producto en lugar de esquivar el defecto por la
longitud de su ruta. (Las dos globales tardaron ≈40 s más que las de ayer: corrieron inmediatamente
después de las suites completas; `E2E-PANTALLA-SIN-PINTAR` no se manifestó.)

## 13. `/speckit.analyze` final, trazabilidad y veredicto

`LONG_PATH_BOOT_FAILURE 0 · NEW_REFERENCE_DEPENDS_ON_VOLUME_LENGTH 0 · LEGACY_ABSOLUTE_REFERENCE_REGRESSION 0 ·
RELATIVE_REFERENCE_RESOLUTION_FAILURE 0 · PRIVATE_KEY_LOAD_REGRESSION 0 · CHALLENGE_SIGNATURE_REGRESSION 0 ·
STARTUP_IDENTITY_REGRESSION 0 · ROW_REWRITE 0 · BACKFILL 0 · MIGRATION_ADDED 0 · COLUMN_TYPE_CHANGE 0 ·
TRUNCATION_WORKAROUND 0 · PATH_TRAVERSAL 0 · PRIVATE_KEY_EXPOSURE 0 · KEY_REFERENCE_PUBLIC_EXPOSURE 0 ·
TEST_VOLUME_SHARED_DEBT_ABSORBED 0 · AUTH/OPENAPI/LICENSING/CENTRAL_SYNC/RATE_LIMIT/KEY_ROTATION/
STARTUP_REVERIFY/PICKLIST_409/E2E_TYPECHECK/E2E_CAPTURE/CLAMSCAN_SKIP/KEEPALIVE_75/VERSION_PANEL_REGRESSION 0 ·
E2E_PANTALLA_ABSORBED 0 · PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 · NEXT_MASTER_SPEC_SELECTED 0 ·
SECRET_EXPOSURE 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 ·
ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.`

Decisión A3 → contrato (`data-model.md`, este delta) → escritor → referencia relativa → compatibilidad
absoluta → resolutor → PostgreSQL con volumen largo → carga de clave → firma del desafío → identidad →
sync/reverificación/rotación (regresiones) → invariante del runner → KR-01…25 → M-01…M-12 → suites
completas → frontend → E2E ×2 → convergencia. FR-KR-001…031 → T01–T05 → pruebas → mutaciones → evidencia:
100 %.

**`INSTALACION-KEY-REFERENCE-120 — CLOSED / CONVERGED`.** Orquestación: 5 tareas `CLAUDE_ONLY`, 0 DeepSeek.
Hoja de ruta, `next-spec-decision.md`, recuento MASTER57 (57) y `data-model.md` actualizados; SPEC057 y NEXT
MASTER SPEC sin cambio; `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`, `E2E-PANTALLA-SIN-PINTAR` y
`ROLES-SIN-TECHO-DE-DELEGACION` siguen OPEN.
