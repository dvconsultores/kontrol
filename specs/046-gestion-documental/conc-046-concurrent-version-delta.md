# SPEC 046 · DELTA DIRIGIDO CONC-046 — DOS SUBIDAS SIMULTÁNEAS DE VERSIÓN

> Delta dirigido dentro de la **Spec 046 — Gestión documental**
> (`specs/046-gestion-documental`). No reabre la 046 ni crea una Spec nueva.
>
> **Veredicto: `CONC-046 — TARGETED DELTA COMPLETE / CONVERGED`** (2026-09-15).
> La 046 sigue `RECONVERGED`; esto es una reconvergencia dirigida. Evidencia en §13
> y en `evidence/conc-046/`.

## 0. Verificación física

| | |
|---|---|
| HEAD | `88c6903` (el esperado) |
| Rama | `develop` |
| Árbol | limpio |
| Entorno | sano desde el arranque de 2026-09-15 03:40: PostgreSQL 16.2 en 55440, backend 8000, Vite 5173 |
| PostgreSQL | **16.2** → `ENVIRONMENT_BASELINE_DEVIATION` frente a 18.6 |

## 1. Ficha de la deuda CONC-046

Recuperada de `docs/roadmap/next-spec-decision.md:1021`, no de memoria.

| Campo | Valor |
|---|---|
| Id | CONC-046 |
| Descripción registrada | «Una subida documental concurrente escapa como excepción» |
| Símbolos | `documents/service.py · _create_version` (asignación del correlativo y cambio de vigente) · `upload_version` · `documents/api.py · upload_version` |
| Operación | `POST /api/v1/documentos/{document_id}/versiones` (`documentos:upload`) |
| Comportamiento actual | en dos subidas simultáneas, la que pierde recibe una `UniqueViolation` **sin capturar**: un 500 |
| Comportamiento esperado | un solo correlativo nuevo y una sola vigente; la que pierde, un conflicto de dominio |
| Dueña | Spec 046 |
| Severidad | media: la unicidad se sostiene, el contrato no |
| Descubrimiento | regresión del delta de la Spec 004 (2026-09-13), advertencia `PytestUnhandledThreadExceptionWarning` en 1 de 4 ejecuciones |
| Prueba actual | `test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2`: dos hilos **sin forzar** la carrera, que aceptan cualquier respuesta distinta de 200 y ni siquiera ven la excepción del hilo |
| Pruebas que faltan | carrera forzada con prueba de que ocurrió; respuesta HTTP de la que pierde; efectos laterales contados; reintento con la misma clave; tres a la vez; aislamiento |
| Restricciones | `uq_document_versions_number (document_id, version_number)` · `uq_document_versions_active (document_id) WHERE status = 'ACTIVE'` — en el modelo y en `0023_document_model.py` |
| Consumidores | todo el que sube versión: pantalla de documentos, vínculos desde 045, 019, 027, 035, 044 |
| Última modificación | ni el módulo ni la prueba cambian desde `00d7cd2` |

## 2. Dueña — confirmada

| Fuente | Dice |
|---|---|
| Máster 56, fila 046 | Gestión documental · `RECONVERGED` |
| `code-to-specs-map.md` | `system.file_metadata` y el módulo documental → 046 |
| Carpeta | `specs/046-gestion-documental` con `SPEC_046_FINAL_CLOSEOUT.md` |
| Historia | `51cbb5a feat(046): gestión documental…` crea `_create_version` |
| Registro de la deuda | dueña 046 |

`OWNER_IDENTITY_CONFLICT = 0`.

## 3. El camino concurrente

```
POST /documentos/{id}/versiones
  └─ CompanyContext + documentos:upload + _get_document (empresa del contexto)
  └─ [Idempotency-Key] busca IdempotencyRecord por clave
  └─ service.upload_version
       temporal → tamaño → MIME → política → análisis → hash
       storage.put(key)            ← fuera de la base
       StoredFile + FileSecurityScan (flush)
       _create_version
         SELECT versión ACTIVE        ─┐
         SELECT max(version_number)    │ ventana de carrera
         UPDATE vigente → SUPERSEDED   │ ← la segunda se bloquea aquí (fila de la vigente)
         INSERT versión max+1 ACTIVE  ─┘ ← y aquí choca, cuando la primera confirma
         UPDATE documents.current_version_id
       auditoría DOCUMENT_FILE_UPLOADED (misma sesión, sin commit propio)
  └─ [Idempotency-Key] INSERT IdempotencyRecord
  └─ commit   ← la transacción empieza con la primera lectura y termina aquí
```

Con `READ COMMITTED`, las dos transacciones leen el mismo máximo. La segunda
queda esperando el bloqueo de fila de la vigente que la primera marcó; cuando la
primera confirma, la segunda sigue, inserta el mismo número y PostgreSQL la rechaza
en `uq_document_versions_number` o en `uq_document_versions_active` —cuál depende
del orden de comprobación de índices—. Si el documento no tenía versión, la
segunda espera directamente en el índice único y el resultado es el mismo.

Lo que ya estaba bien: **PostgreSQL decide**. No hay dos V2 ni dos vigentes. Lo
que falla es el contrato de quien pierde, y lo que deja detrás.

## 4. Clasificación

| Tipo | ¿Aplica? | Evidencia |
|---|---|---|
| RACE-C · versión duplicada | **sí** — la ventana entre `max()` e `INSERT` | §3 |
| RACE-E · vigente partida | contenida por `uq_document_versions_active`; mismo manejo | §3 |
| RACE-F · base y almacenamiento | **sí** — la perdedora ya escribió su binario: queda huérfano | `upload_version` escribe antes de `_create_version` |
| Reintento | **sí** — con la misma `Idempotency-Key` y en carrera, la perdedora debería recibir la versión ganadora (AC-046-13) y recibe un 500 | ruta |
| RACE-H · auditoría duplicada | no — `record_audit` escribe en la misma sesión y no confirma: la perdedora revierte su rastro | `app/shared/audit.py` |
| RACE-A, B, D, G | no en este camino | — |

Defecto preexistente en el mismo camino: el acierto idempotente devuelve
`document.current_version_id`, **no** la versión que creó esa clave. Tras otra
subida, un reintento recibiría una versión que no pidió. AC-046-13 dice «la misma
versión».

## 5. `/speckit.specify`

La numeración de la 046 llega a FR-046-114 y AC-046-50.

| ID | Requisito |
|---|---|
| FR-046-115 | Dos creaciones simultáneas de versión del mismo documento producen **exactamente una** versión nueva y una sola vigente; la que pierde recibe `409 VERSION_CONFLICT`, nunca un 500 ni una excepción sin capturar. Decide la restricción de PostgreSQL |
| FR-046-116 | La operación que pierde no deja efecto: ni versión, ni archivo registrado, ni análisis, ni auditoría, ni binario en el almacenamiento |
| FR-046-117 | Con la misma `Idempotency-Key`, la que pierde la carrera recibe la versión ganadora como acierto idempotente, no un conflicto |
| FR-046-118 | El acierto idempotente devuelve **la versión que creó esa clave en ese documento**: ni la vigente de después ni la de otro documento |
| FR-046-119 | Subidas a documentos distintos —misma empresa, otra empresa, otro tenant— no se bloquean entre sí; el aislamiento y los permisos no cambian |

## 6. `/speckit.clarify`

| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| 1 | Deuda exacta | §1 | RESUELTA |
| 2 | Símbolos | `_create_version`, `upload_version` (servicio y ruta) | RESUELTA |
| 3 | Ventana de carrera | entre `SELECT max(version_number)` e `INSERT` | RESUELTA |
| 4 | Clave lógica | `document_id` (el correlativo es por documento) | RESUELTA |
| 5 | Restricción | `uq_document_versions_number` y `uq_document_versions_active`, en modelo y migración | RESUELTA — sin migración |
| 6 | Transacción | de la primera lectura de la ruta al `commit` final | RESUELTA |
| 7 | Almacenamiento | `storage.put` antes de la base; sin transacción distribuida | RESUELTA — compensación: borrar el binario de la perdedora |
| 8 | Ganadora y perdedora | gana quien confirma primero; la otra recibe `409 VERSION_CONFLICT` | RESUELTA — AC-046-11, `test-plan.md` §5, `data-model.md` («impide dos V2»), aceptación registrada («conflicto de dominio»), código existente en `contracts/api-contracts.md` |
| 9 | Reintento | con la misma clave devuelve la misma versión | RESUELTA — AC-046-13, FR-046-047 |
| 10 | Idempotencia en carrera | la perdedora con la misma clave relee el registro que confirmó la ganadora | RESUELTA — mismo mecanismo, sin otro nuevo |
| 11 | Versiones | correlativo monótono, historial intacto, una sola vigente | RESUELTA |
| 12 | Auditoría | transaccional: un `DOCUMENT_FILE_UPLOADED` por versión real | RESUELTA |
| 13 | Estado HTTP | `409` con `VERSION_CONFLICT` —«la vigente cambió»—, el código ya documentado | RESUELTA — no se inventa código |
| 14 | Empresa | `_get_document` filtra por la empresa del contexto antes de todo; no se añade bloqueo nuevo | RESUELTA |
| 15 | Pruebas actuales | §1 | RESUELTA |
| 16 | Pruebas que faltan | §1 | RESUELTA |
| 17 | Migración | no | RESUELTA |
| 18 | Consumidores | el contrato de éxito no cambia; la perdedora pasa de 500 a 409 | RESUELTA |

¿Debería la perdedora crear la V3 en vez de un conflicto? **No**: cambiaría el
resultado funcional —dos versiones donde el usuario pidió una— y ninguna fuente lo
autoriza, mientras que la aceptación registrada y el contrato piden conflicto.

**MATERIAL OQ = 0.**

### Fuera de alcance, registrado

| Hallazgo | Por qué no se absorbe |
|---|---|
| Con un tipo `SINGLE`, `VERSION_NOT_ALLOWED` se lanza después de escribir el binario: queda huérfano | no es una carrera; es otro camino de la 046 |
| `import_legacy_reference` también usa `_create_version` | trabaja sobre un documento recién creado en su propia transacción; queda cubierto sin tocarlo |

## 7. `/speckit.plan`

| Ola | Contenido | Tareas |
|---|---|---|
| W01-W05 | Deuda, camino, restricciones, semántica, artefactos | T-C46-01 |
| W06 | Estrategia de base: la restricción existente decide; sin migración | — |
| W07-W08 | Captura estrecha con `es_violacion_unica` dentro de un `SAVEPOINT` y `409 VERSION_CONFLICT` | T-C46-02 |
| W09 | Reintento en carrera y acierto idempotente correcto | T-C46-04 |
| W10 | Compensación del binario de la perdedora | T-C46-03 |
| W11 | Auditoría: se comprueba, no cambia | T-C46-06 |
| W12 | Empresa y tenant: se comprueban, no cambian | T-C46-06 |
| W13-W15 | Carrera forzada, reintento, tres a la vez, hostiles | T-C46-06, T-C46-07 |
| W16 | Mutaciones | T-C46-08 |
| W17 | Paridad ORM ↔ PostgreSQL | T-C46-09 |
| W18-W20 | Regresión dirigida 046, consumidores, regresión completa sola | T-C46-10, T-C46-11 |
| W21-W22 | Frontend: no se toca · E2E de documentos en tres navegadores | T-C46-12 |
| W23-W25 | Analyze final, trazabilidad, convergencia | T-C46-13 |

| Tema | Decisión | Por qué |
|---|---|---|
| Patrón | restricción única + recuperación controlada: `SAVEPOINT` (`begin_nested`) y `es_violacion_unica` | es el patrón canónico del repositorio (inventario, tasas de la 013); la base ya tiene la invariante |
| Sin bloqueo nuevo | no `SELECT FOR UPDATE`, no *advisory lock*, no candado de proceso | bloquear convertiría a la perdedora en V3, que no está autorizado; y la restricción ya serializa lo que importa |
| Dónde se traduce el conflicto | en `_create_version` | cubre los dos caminos que crean versión |
| Compensación | `storage.delete(key)` en `upload_version` ante `VERSION_CONFLICT`; si el borrado falla, queda el huérfano que el diseño ya declara recuperable | no hay transacción distribuida que fingir |
| Reintento en carrera | la ruta, ante `VERSION_CONFLICT` con clave, revierte, relee el registro idempotente y devuelve esa versión | reutiliza `IdempotencyRecord` |
| Acierto idempotente | por `response_payload.version_id`, comprobando que la versión es de ese documento | FR-046-118 |
| Prueba | `tests/concurrency.py · carrera` (bloqueo real en `pg_stat_activity`), más una espera por bloqueo para las rutas HTTP | lección de la 013: sin carrera demostrada no hay prueba |

## 8. CONSTITUTION GATE

| Puerta | Diseño |
|---|---|
| G-CONC-046-01 deuda exacta recuperada | **PASS** |
| G-CONC-046-02 dueña 046 probada | **PASS** |
| G-CONC-046-03 sin Spec nueva | **PASS** |
| G-CONC-046-04 ventana de carrera conocida | **PASS** |
| G-CONC-046-05 semántica de negocio conocida | **PASS** — §6.8 |
| G-CONC-046-06 PostgreSQL autoridad | **PASS** |
| G-CONC-046-07 sin candado solo de proceso | **PASS** |
| G-CONC-046-08 sin bloqueo global | **PASS** — ninguno nuevo |
| G-CONC-046-09 conflicto esperado ≠ 500 | **PASS** |
| G-CONC-046-10 idempotencia definida | **PASS** |
| G-CONC-046-11 multiempresa | **PASS** |
| G-CONC-046-12 multitenant | **PASS** |
| G-CONC-046-13 historial intacto | **PASS** |
| G-CONC-046-14 auditoría coherente | **PASS** |
| G-CONC-046-15 carrera real planificada | **PASS** |
| G-CONC-046-16 mutaciones con semántica | **PASS** — §9 |
| G-CONC-046-17 estrategia de esquema | **PASS** — sin migración |
| G-CONC-046-18 sin otra limpieza de la 046 | **PASS** — §6 fuera de alcance |

**18 PASS · 0 condicionadas.**

## 9. `/speckit.checklist`

- [x] texto de la deuda · [x] símbolos · [x] dueña · [x] tipo de carrera
- [x] clave lógica · [x] frontera de transacción · [x] restricciones · [x] frontera de almacenamiento
- [x] ganadora · [x] perdedora · [x] reintento · [x] idempotencia · [x] respuesta HTTP y de dominio
- [x] auditoría · [x] empresa · [x] tenant
- [x] carrera real diseñada · [x] mutaciones diseñadas · [x] sin migración · [x] consumidores
- [x] MATERIAL OQ = 0 · [x] UNKNOWN = 0 · [x] trazabilidad 100 %

| Mutación | Qué reintroduce | Debe caer |
|---|---|---|
| M046-CONC-01 | sin captura: `_create_version` sin `SAVEPOINT` ni traducción | la perdedora recibe `IntegrityError` o un 500 |
| M046-CONC-02 | sin la invariante de base: el modelo pierde `uq_document_versions_number` y `uq_document_versions_active` | aparecen dos V2 y dos vigentes |
| M046-CONC-03 | clave idempotente sin el documento: ni en el ámbito ni en la comprobación | otro documento recibe una versión ajena |
| M046-CONC-04 | sin recuperación del reintento en carrera | la misma clave recibe 409 en vez de su versión |
| M046-CONC-05 | sin compensación del binario | queda un binario huérfano |

Una mutación de «auditoría duplicada» no se usa: la auditoría es transaccional por
diseño y no puede duplicarse sin cambiar ese diseño; su invariante se prueba igual.

## 10. `/speckit.tasks`

| ID | Requisito | Ficheros | Depende | Cambio | Prueba |
|---|---|---|---|---|---|
| T-C46-01 | 115-119 | este documento, `spec.md`, `acceptance-criteria.md`, `clarifications.md`, `contracts/api-contracts.md` | — | requisitos, semántica, contrato | revisión |
| T-C46-02 | 115 | `documents/service.py · _create_version` | — | `SAVEPOINT` + `es_violacion_unica` → `ConflictError(VERSION_CONFLICT)` | carrera forzada · M-01, M-02 |
| T-C46-03 | 116 | `documents/service.py · upload_version` | 02 | borrar el binario de la perdedora | huérfano · M-05 |
| T-C46-04 | 117, 118 | `documents/api.py · upload_version` | 02 | acierto idempotente por el registro y recuperación en carrera | reintento · M-03, M-04 |
| T-C46-05 | 115 | `tests/concurrency.py` | — | espera por procesos bloqueados (para rutas HTTP y tres a la vez) | — |
| T-C46-06 | 115, 116, 119 | `tests/test_documents_security.py` | 02-05 | sustituir la prueba débil por carreras forzadas; efectos contados; aislamiento | verde |
| T-C46-07 | 117, 118 | `tests/test_documents_security.py` | 04 | reintento en carrera, acierto correcto, clave en otro documento | verde |
| T-C46-08 | 115-119 | `evidence/conc-046/` | 06, 07 | cinco mutaciones | rojas y restauradas |
| T-C46-09 | 115 | — | 02 | paridad del ámbito | 0 diferencias |
| T-C46-10 | todos | `tests/test_documents*.py` y consumidores | 06 | regresión dirigida | verde |
| T-C46-11 | todos | regresión completa | 10 | sola | 0 fallos, 0 errores, 0 omisiones inesperadas |
| T-C46-12 | 119 | `e2e/documents.spec.ts`, `documents-a11y.spec.ts` | 11 | tres navegadores | verde |
| T-C46-13 | todos | cierre, trazabilidad, máster, decisión siguiente | 11, 12 | analyze final y convergencia | §15 |

## 11. `/speckit.analyze` previo a implementar

| Búsqueda | Hallazgo | Tarea |
|---|---|---|
| comprobar-e-insertar sin recuperación | `_create_version` (`max()` → `INSERT`) | T-C46-02 |
| `IntegrityError` que escapa | 1 camino | T-C46-02 |
| `StaleDataError` | 0 — sin columna de versión en el camino | — |
| versión duplicada · vigente duplicada | impedidas por PostgreSQL | se conservan |
| vínculo duplicado | fuera de este camino (`uq_document_links_unique`) | — |
| auditoría duplicada | 0 — transaccional | se prueba |
| binario huérfano | 1 en carrera | T-C46-03 |
| bloqueo global · candado de proceso | 0 | — |
| empresa o tenant ausentes | 0 — `_get_document` por contexto | se prueba |
| reintento sin idempotencia correcta | acierto por vigente, no por clave | T-C46-04 |
| prueba que acepta el fallo · `sleep` en vez de barrera | `test_dos_subidas_simultaneas_no_producen_dos_v2` | T-C46-06 |
| deriva modelo ↔ migración | 0 en las dos restricciones | T-C46-09 |

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRAZABILIDAD | 100 % — 5 requisitos, 13 tareas, 5 mutaciones |

**Autorización expresa consumida.** Se procede a `/speckit.implement`.

## 12. `/speckit.implement`

| Punto | Antes | Después | Fichero |
|---|---|---|---|
| Cambio de vigente e inserción | sin protección: la violación única escapaba | dentro de un `SAVEPOINT`; `es_violacion_unica` sobre `uq_document_versions_number` o `uq_document_versions_active` → `ConflictError(VERSION_CONFLICT)` 409 con `reason`, `dependencies` y `allowed_actions` | `documents/service.py · _create_version` |
| Binario de la perdedora | quedaba huérfano | `storage.delete(key)` ante `VERSION_CONFLICT`; si el borrado falla, basura recuperable como antes | `documents/service.py · upload_version` |
| Acierto idempotente | devolvía `document.current_version_id` | devuelve la versión del registro (`response_payload.version_id`) y solo si es de ese documento | `documents/api.py · _acierto_idempotente` |
| Misma clave en carrera | 500 | la ruta revierte, relee el registro que confirmó la ganadora y devuelve su versión | `documents/api.py · upload_version` |
| Clave idempotente | cadena repetida en dos sitios | `_clave_idempotente`, mismo formato | `documents/api.py` |
| Carreras en pruebas | — | `esperar_bloqueados`: espera a que N conexiones estén bloqueadas en PostgreSQL | `tests/concurrency.py` |
| Prueba de concurrencia | dos hilos sin forzar que aceptaban cualquier respuesta | 11 pruebas con carrera forzada y efectos contados (§13) | `tests/test_documents_security.py` |
| Login del E2E documental | «Activar» sin `exact` casaba con «Desactivar» y desactivaba la empresa | `exact: true` en los dos botones; ninguna aserción cambia | `e2e/documents.spec.ts`, `e2e/documents-a11y.spec.ts` |

Sin migración, sin bloqueo nuevo, sin cambio de frontend de producto.

## 13. Evidencia

### Pruebas dirigidas

| Prueba | Qué demuestra | Resultado |
|---|---|---|
| `test_dos_subidas_simultaneas_no_producen_dos_v2` ×3 | carrera forzada tres veces: una V2, una vigente, la perdedora `ConflictError(VERSION_CONFLICT)`; archivos, análisis, auditoría y binarios +1 exactos | ✔ |
| `test_la_primera_version_simultanea_tampoco_da_un_500` | la carrera sobre el índice único, sin versión previa | ✔ |
| `test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500` | la ruta real bloqueada en PostgreSQL recibe 409 | ✔ |
| `test_tres_subidas_simultaneas_crean_una_sola_version` | dos perdedoras bloqueadas a la vez, las dos 409, un solo efecto | ✔ |
| `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora` | reintento en carrera → acierto con la versión ganadora | ✔ |
| `test_un_reintento_devuelve_la_version_de_su_clave_aunque_haya_otra_despues` | acierto por la clave, no por la vigente | ✔ |
| `test_la_misma_clave_en_otro_documento_no_devuelve_una_version_ajena` | la clave no cruza documentos | ✔ |
| `test_subidas_a_documentos_distintos_no_se_esperan` | ni el documento vecino ni el de otro tenant esperan a la carrera | ✔ |
| `test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera` | 404 inmediato, sin esperar ni filtrar el conflicto | ✔ |

`test_documents_security.py` y `test_documents.py`: **62/62**, con
`PytestUnhandledThreadExceptionWarning` convertido en error.

### Mutaciones

| ID | Mutación | Prueba que cae | Fallo real | Restaurada |
|---|---|---|---|---|
| M046-CONC-01 | la captura vuelve a relanzar | carreras de servicio (×3) y HTTP | la perdedora escapa como `IntegrityError` de `uq_document_versions_number` | sí |
| M046-CONC-02 | el modelo pierde las dos restricciones | carreras de servicio (×3) | la perdedora **crea otra versión** | sí |
| M046-CONC-03 | clave sin documento ni comprobación | clave en otro documento | otro documento recibe una versión ajena como acierto | sí |
| M046-CONC-04 | sin recuperación del reintento | misma clave en carrera | la misma clave recibe 409 | sí |
| M046-CONC-05 | sin compensación del binario | carreras de servicio y HTTP | binarios +2 en vez de +1 | sí |

Tras restaurar, la suite de seguridad documental vuelve a pasar completa.

### Paridad, migración e instalación limpia

| | |
|---|---|
| ORM ↔ PostgreSQL en las tablas documentales | **0** diferencias; `uq_document_versions_active` y `uq_document_versions_number` idénticos en `ke2e` migrada de cero; heredadas globales 21, sin cambio |
| Migración | no |
| Base del E2E | reinstalada de cero: 57 migraciones, exit 0 |

### Regresión

| | |
|---|---|
| Dirigida (046 y consumidores: `test_documents*`, `test_mc_security_045_046`, `test_n9_*`, `test_n10_convergence`, `test_spec020_*`, `test_spec037_receivables`) | verde salvo `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada`, ERROR solo dentro de ese subconjunto; sola 5/5 y en la completa sin fallos (§14) |
| Completa, sola · PostgreSQL 16.2 · `TZ=UTC` | **1579 pasan · 0 fallan · 0 errores · 8 omitidas (S3) · 0 inesperadas · 0 avisos** · exit 0 |
| Frontend | solo cambian dos ficheros E2E; ESLint 0 sobre ellos |

### E2E de documentos, tres navegadores, después de la regresión

| | |
|---|---|
| Resultado | **35/36** — Chromium 11/12, Firefox 12/12, WebKit 12/12 |
| El que falla | `documents.spec.ts:309` en Chromium, `PREEXISTING` (§14); aislado **3/3** |
| Backend | 0 trazas · 0 respuestas 500 |
| Contra `HEAD 88c6903` sin el delta | las dos pruebas probadas fallan igual en el login (`e2e-documentos-base-head.txt`) |

## 14. Clasificación de lo encontrado

| Hallazgo | Clasificación | Evidencia | Qué se hizo |
|---|---|---|---|
| El `uiLogin` del E2E documental pulsaba «Desactivar» | `PREEXISTING` · `TEST_DEFECT` del E2E de la 046, desde N6 | reproducido contra el backend de `HEAD` | **corregido**: `exact: true`; bloqueaba toda la evidencia E2E de la dueña |
| 18 trazas `PermissionError: '/data'` en la primera ejecución E2E | `EXTERNAL_ENVIRONMENT`: el entorno reconstruido tras el reinicio no fijaba las rutas de almacenamiento | `e2e-documentos-primera.txt` | rutas `KONTROL_*_PATH` en `/tmp`, como la receta original |
| `documents.spec.ts:309` en Chromium | `PREEXISTING` · `TEST_DEFECT`: espera «Página siguiente», que solo existe con más de 10 filas; depende de cuántos tipos creen los otros navegadores | aislada 3/3 | registrado como E2E-046-TIPOS; no absorbido |
| `test_n10_convergence` en la regresión dirigida | `PREEXISTING` · orden de invocación, mismo patrón que en la 047 | sola 5/5; completa sin errores (`n10-orden.txt`) | registrado; no absorbido |
| `VERSION_NOT_ALLOWED` tras escribir el binario | `PREEXISTING` · huérfano sin carrera | lectura de `upload_version` | registrado como ORPHAN-046-SINGLE |
| La clave idempotente se trunca a 64 caracteres: con un documento de 36, solo 10 caracteres de la clave distinguen | `PREEXISTING` · observación | `_clave_idempotente` | registrado como IDEM-046-TRUNC; el formato no cambia |
| PostgreSQL 16.2 | `ENVIRONMENT_BASELINE_DEVIATION` | `show server_version` | declarado |

| Clase | Número |
|---|---|
| NEW_REGRESSION_CONC_046 | **0** |
| PREEXISTING_SEALED | 4 registrados · 1 corregido (el login E2E) |
| TEST_DEFECT | incluido arriba |
| EXTERNAL_ENVIRONMENT | 1 |
| ENVIRONMENT_BASELINE_DEVIATION | 1 |
| OWNER_DEPENDENCY · OWNER_IDENTITY_CONFLICT_DEBT · MATERIAL_DECISION_REQUIRED | 0 |
| UNKNOWN | **0** |

## 15. `/speckit.analyze` final y convergencia

| Búsqueda | Resultado |
|---|---|
| comprobar-e-insertar sin recuperación · `IntegrityError` que escapa | 0 · 0 (M-01 por contraste) |
| versión o vigente duplicada | 0 (M-02 por contraste) |
| auditoría duplicada · éxito auditado tras revertir | 0 · 0 (conteos exactos) |
| binario huérfano en carrera | 0 (M-05 por contraste) |
| bloqueo global · candado de proceso | 0 |
| empresa o tenant ausentes | 0 (pruebas de aislamiento en carrera) |
| reintento que devuelve otra versión | 0 (M-03, M-04 por contraste) |
| prueba que acepta el 500 · `sleep` como barrera | 0 · 0 |
| deriva modelo ↔ base en el ámbito | 0 |

| | |
|---|---|
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 |
| ORPHAN REQUIREMENTS · ORPHAN TASKS | 0 · 0 |
| MATERIAL OQ · UNKNOWN | 0 · 0 |
| TRAZABILIDAD | 100 % — 5 requisitos, 5 criterios, 13 tareas, 5 mutaciones (`traceability-matrix.md` §7) |

| Condición de convergencia | |
|---|---|
| deuda exacta · dueña probada · sin Spec nueva | ✔ |
| carrera forzada y demostrada · repetida · de tres | ✔ |
| perdedora 409, nunca 500 · una versión, una vigente | ✔ |
| sin efectos de la perdedora (archivo, análisis, auditoría, binario) | ✔ |
| reintento con la misma clave → la misma versión | ✔ |
| aislamiento de empresa y tenant durante la carrera | ✔ |
| PostgreSQL autoridad · sin bloqueo nuevo | ✔ |
| mutaciones que caen | 5/5 |
| paridad · migración | 0 · ninguna |
| regresión completa 0/0, omisiones inesperadas 0 | ✔ |
| E2E de documentos | ✔ — el único fallo es preexistente y aislado pasa |

**`CONC-046 — TARGETED DELTA COMPLETE / CONVERGED`.**

## 16. Contrato

El contrato de éxito no cambia. Cambian dos cosas, las dos hacia lo documentado: la
perdedora de una carrera recibe `409 VERSION_CONFLICT` en vez de un 500, y un
reintento con la misma `Idempotency-Key` devuelve la versión de esa clave aunque
después se hayan subido otras. Declarado en `contracts/api-contracts.md` y en
AC-046-51..55.
