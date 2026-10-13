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
