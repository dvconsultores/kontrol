# SPEC 023 · Delta dirigida — INV-MOVTYPE-CARRERA

**Fecha** 2026-09-18 · **Dueña** SPEC023 (`specs/003-inventario-logistica`) ·
**Base** `26ca9bd` · **Rama** `develop` · **Tipo** reconvergencia dirigida

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `26ca9bd` |
| `ACTUAL_HEAD` | `26ca9bd` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_26CA9BD` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. Dueña canónica

**SPEC023 — Inventario / Kardex**, carpeta física `specs/003-inventario-logistica`
(`docs/roadmap/spec-equivalence-map.md:30`). La evidencia es física y converge:

- el modelo `MovementType` vive en `app/modules/inventory/models.py:57`;
- la ruta, en `app/modules/inventory/api.py:188`;
- la restricción `uq_movement_types_company_code`, en ese mismo modelo;
- y **ya existe** una prueba de carrera de este mismo asunto y de esta misma dueña:
  `tests/test_spec023_movement_type_race.py`.

`OWNER_IDENTITY_CONFLICT = 0`. SPEC025 no interviene: no toca tipos de movimiento.

## 3. El defecto, localizado

`create_movement_type` (`app/modules/inventory/api.py:188-202`):

```python
company_id = None if body.global_scope else ctx.company_id
dup = db.execute(select(MovementType).where(
    MovementType.company_id == company_id, MovementType.code == body.code)).scalars().first()
if dup:
    raise ConflictError(code="MOVEMENT_TYPE_DUPLICATE", …)
mtype = MovementType(…)
db.add(mtype)
db.commit()
```

Consultar y después insertar, sin nada entre medias. Dos peticiones simultáneas de la
misma empresa pasan ambas la consulta y compiten en el `INSERT`.

### El precedente que sí lo hace bien, en el mismo módulo

`_get_movement_type_by_code` (`service.py:1634-1659`) resuelve la misma carrera para la
auto-configuración de los tipos base: `begin_nested()`, `flush()`, y captura **solo** la
violación de esa restricción con `es_violacion_unica`. Su propio comentario describe el
caso y dice dónde se encontró. Es la convención del repositorio: el mismo patrón aparece
en `notifications` (×2), `documents` y `treasury/rates`.

La diferencia entre los dos caminos es de intención, no de mecanismo: la
auto-configuración es **idempotente** —quien pierde relee el tipo del otro— y el alta
explícita **no** lo es: quien pide crear algo que ya existe debe recibir un conflicto, no
la fila ajena.

## 4. Identidad lógica y garantía de la base, medidas

| Aspecto | Valor verificado |
|---|---|
| Tabla | `movement_types` |
| Clave lógica | `(company_id, code)` |
| Restricción | `uq_movement_types_company_code UNIQUE btree (company_id, code)` — **existe** en la base, comprobado con `\d movement_types` |
| `company_id` | **nullable**; el nulo es el interruptor de «tipo de toda la instalación» (`models.py:64-66`) |
| Estado | `StatusMixin`; la consulta previa **no** filtra por estado, así que un tipo inactivo con el mismo código bloquea el alta. **Se preserva** |
| Contrato de duplicado | `ConflictError(code="MOVEMENT_TYPE_DUPLICATE")` → **HTTP 409** (`app/core/errors.py:68`) |
| Discriminación de errores | `app/core/integrity.py::es_violacion_unica`: SQLSTATE **23505** *y* nombre de restricción |

## 5. Reproducción previa, sobre PostgreSQL real

Con el arnés del propio repositorio, `tests/concurrency.py::carrera`, que **fuerza** la
ventana —la primera transacción inserta sin confirmar, la segunda pasa la consulta y queda
bloqueada en el índice— y falla si la carrera no llega a ocurrir.

| Caso | Resultado medido |
|---|---|
| **Duplicado secuencial** (HTTP) | alta 1 → `200`; alta 2 → **`409 MOVEMENT_TYPE_DUPLICATE`**; filas: **1** |
| **Mismo código en otra empresa** | empresa A → `200`; empresa B → `200`. La identidad **incluye** la empresa |
| **Carrera concurrente** (lógica de la ruta) | primero → `CREADO`; segundo → **`IntegrityError` crudo**, `pgcode=23505`, restricción `uq_movement_types_company_code`; filas: **1** |
| **Carrera con alcance global** (`company_id NULL`) | el arnés informa «la segunda transacción nunca chocó»; filas: **2** |

De ahí salen las dos conclusiones que gobiernan el alcance de esta delta:

1. **La base protege la identidad por empresa y el contrato ya existe.** Lo que falta es
   traducir la colisión: el `IntegrityError` sube sin capturar y FastAPI responde **500**.
   No hace falta migración.
2. **El alcance global no está protegido** y eso **no** se corrige aquí (§10).

## 6. Causa raíz

| Clase | ¿Es? |
|---|---|
| `API_CONFLICT_MAPPING_DEFECT` | **SÍ** — la violación esperable no se traduce al conflicto de dominio que ya existe |
| `PRODUCT_RACE_DEFECT` | **SÍ**, en su forma: consultar y luego insertar sin protección entre medias |
| `DB_CONSTRAINT_DEFECT` | **No** para el caso de empresa: la restricción existe y funciona |
| `TRANSACTION_RECOVERY_DEFECT` | A verificar tras el arreglo: sin savepoint, la transacción queda abortada |
| `TEST_DEFECT` | No |

## 7. Lo que queda fuera, y por qué

**El alcance global (`company_id IS NULL`) no se corrige en esta delta.**

En PostgreSQL los nulos no colisionan entre sí, así que `UNIQUE (company_id, code)` no
garantiza nada cuando la empresa es nula: medido, dos altas concurrentes dejan **dos
filas**. Protegerlo exige un índice único parcial y, por tanto, una **migración**.

Antes de crearla hay que saber qué se está declarando, y la spec no lo dice: su modelo de
datos describe `MovementType` como «id, **company_id/global**, code, name, direction,
version, status» (`data-model.md:35`) y **no declara unicidad** del código, ni por empresa
ni global. La unicidad por empresa existe solo en el modelo del producto.

Decidir si dos tipos globales pueden compartir código es una decisión de identidad de
negocio, no una inferencia. Se escala: **`MOVTYPE-GLOBAL-SIN-UNICIDAD`**,
`MATERIAL_DECISION_REQUIRED`, dueña 023. Y se declara el efecto: tras esta delta el camino
de empresa queda protegido y el global **sigue como está**; el arreglo no lo empeora ni lo
mejora, porque allí no hay violación que capturar.

## 8. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-023-MOVTYPE-001 | Dos altas concurrentes del mismo código en la misma empresa no crean más de una fila |
| FR-023-MOVTYPE-002 | Quien pierde la carrera recibe el conflicto de dominio que ya existe: `MOVEMENT_TYPE_DUPLICATE`, HTTP 409 |
| FR-023-MOVTYPE-003 | Una carrera esperable no se convierte en HTTP 500 |
| FR-023-MOVTYPE-004 | Solo la violación de `uq_movement_types_company_code` se traduce a duplicado; cualquier otro error de integridad se propaga |
| FR-023-MOVTYPE-005 | Tras el conflicto la sesión sigue siendo utilizable: la transacción no queda abortada |
| FR-023-MOVTYPE-006 | El duplicado secuencial conserva exactamente su conducta actual |
| FR-023-MOVTYPE-007 | Códigos distintos siguen creándose en paralelo sin estorbarse |
| FR-023-MOVTYPE-008 | El mismo código en empresas distintas sigue siendo válido |
| FR-023-MOVTYPE-009 | El alta explícita **no** se vuelve idempotente: quien pide crear lo que ya existe recibe conflicto, no la fila ajena |
| FR-023-MOVTYPE-010 | Existe prueba de carrera forzada contra PostgreSQL que falla si la carrera no ocurre |
| FR-023-MOVTYPE-011 | Existe cobertura de mutación que detecta la reintroducción de la carrera |
| FR-023-MOVTYPE-012 | Sin migración, sin cambio de esquema y sin cambio de semántica de negocio |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta medida | ¿Material? |
|---|---|---|---|
| 1 | Dueña | SPEC023 | No |
| 2 | Endpoint | `POST /api/v1/inventory/movement-types` | No |
| 3 | Tabla | `movement_types` | No |
| 4 | Identidad lógica | `(company_id, code)`; medido con dos empresas | No |
| 5 | ¿Existe la restricción? | **Sí**, `uq_movement_types_company_code` | No |
| 6 | Contrato de duplicado | `MOVEMENT_TYPE_DUPLICATE` → **409**, medido por HTTP | No |
| 7 | ¿409 es suposición? | **No**: es lo que responde hoy el camino secuencial | No |
| 8 | Precedente seguro | `service.py:1634-1659`, y el mismo patrón en otros 3 módulos | No |
| 9 | ¿Reutilizable tal cual? | **No del todo**: aquel es idempotente y este no. Se reutiliza el *mecanismo*, no la intención | No |
| 10 | ¿Dónde vive la corrección? | En el servicio: la ruta confirma la transacción, y una carrera forzada exige que la creación no confirme | No |
| 11 | Estado / borrado lógico | La consulta previa no filtra por estado: un inactivo bloquea. **Se preserva** | No |
| 12 | ¿Migración? | **No** para el caso de empresa | No |
| 13 | ¿Datos duplicados? | No aplica: no se crea restricción | No |
| 14 | ¿Alcance global? | **Sin garantía**, medido: 2 filas. Identidad **no decidida** por la spec → se escala (§7) | Sí, **y por eso queda fuera** |
| 15 | ¿Idempotencia? | **No**: el contrato es conflicto | No |
| 16 | ¿Pruebas existentes? | `tests/test_spec023_movement_type_race.py` cubre la auto-configuración, no el alta explícita | No |
| 17 | ¿E2E? | `putaway` y `order-confirmation` ya esperan `MOVEMENT_TYPE_DUPLICATE` ante el 409 | No |

**MATERIAL OQ = 0 para el objetivo de esta delta.** La única decisión material encontrada
—unicidad del código global— se escala sin tocarla, y no bloquea el objetivo.

## 10. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 · 2 | Spec antes que código; autorización expresa con `MATERIAL OQ = 0` |
| 3 | Trazabilidad §16 |
| 10 | Carrera forzada, no observada por suerte |
| 13 — Integridad transaccional | Savepoint: el conflicto no aborta la unidad de trabajo |
| **25 — Las altas concurrentes las gobierna la base** | Es exactamente lo que esta delta viene a cumplir |
| 21 — Paridad del motor | La prueba corre sobre PostgreSQL real; el arnés se salta si no lo hay |
| 22 | Una sola manera de discriminar la violación: `es_violacion_unica` |
| 27 | Mutaciones que cambian lo observable |

**COMPUERTA: PASA.** `G-RACE-01`…`G-RACE-19` satisfechas.

## 11. `/speckit.plan` · `/speckit.tasks`

`W01` checkpoint · `W02` dueña · `W03` ruta · `W04` precedente · `W05` identidad ·
`W06` restricción · `W07` contrato · `W08` duplicado secuencial · `W09` carrera forzada ·
`W10` estado de la transacción · `W11` diseño · `W12` implementación · `W13` pruebas
secuenciales · `W14` carrera · `W15` multiempresa · `W16` discriminación de errores ·
`W17` mutaciones · `W18` regresión dirigida · `W19` regresión backend completa ·
`W20` E2E relacionada · `W21` E2E global · `W22` esquema · `W23` analyze ·
`W24` trazabilidad · `W25` convergencia.

| ID | Requisito | Acción | Aceptación | Mutación |
|---|---|---|---|---|
| T01 | FR-001..005 | `inv_service.crear_tipo_de_movimiento`: consulta previa + savepoint + captura precisa + conflicto | Carrera forzada: 1 alta, 1 conflicto, 1 fila | 01·02·03 |
| T02 | FR-006/009 | La ruta delega y confirma | Secuencial idéntico | 01 |
| T03 | FR-010 | Pruebas en `tests/test_spec023_movement_type_race.py` | Falla si no hay carrera | 01 |
| T04 | FR-007/008 | Códigos distintos y empresas distintas | Sin estorbo | 04 |
| T05 | FR-012 | Sin migración | `alembic check` 21 → 21 | — |

## 12. `/speckit.analyze` previo

| Búsqueda | Resultado |
|---|---|
| `check-then-insert` sin protección en tipos de movimiento | **1** (la ruta) |
| Captura amplia de `IntegrityError` | **0** |
| `retry` · `sleep` · cerrojo global · `SELECT FOR UPDATE` como defensa | 0 · 0 · 0 · 0 |
| Migraciones · cambios de esquema | 0 · 0 |
| Cambios de semántica de negocio o de permisos | 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` (del objetivo) · `UNKNOWN` | 0 · 0 |

**AUTORIZACIÓN EXPRESA CONSUMIDA.**

## 13. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `app/modules/inventory/service.py` | modificado | `crear_tipo_de_movimiento`: consulta previa, inserción en savepoint, captura de **esa** violación y conflicto de dominio. Más `_tipo_por_codigo`, que resuelve el alcance —empresa o global— y no filtra por estado |
| `app/modules/inventory/api.py` | modificado | La ruta delega y se queda con lo suyo: confirmar |
| `tests/test_spec023_movement_type_race.py` | ampliado | Ocho casos nuevos sobre el alta explícita, junto a los dos que ya cubrían la auto-configuración |

**Migraciones = 0 · esquema = 0 · contrato de API = 0 · semántica de negocio = 0.**

### Por qué la creación baja al servicio

Porque la ruta **confirma** la transacción, y una carrera forzada exige que quien inserta
no confirme: el arnés necesita mantener la primera transacción abierta para que la segunda
llegue a chocar de verdad. Dejar la lógica en la ruta obligaba a probarla por el camino
cómodo —la segunda ve la fila ya confirmada y se rechaza en la consulta previa—, que es
exactamente la prueba que pasa aunque la captura no exista.

Además es donde vive el precedente: el mismo módulo ya resolvía así la carrera de la
auto-configuración.

### La consulta previa se queda

No es la protección —no puede serlo— pero sigue valiendo: contesta el caso normal sin
gastar un savepoint, da el mismo mensaje de siempre y, en el alcance global, es lo único
que hay. Lo que cambia es que ya no está sola.

## 14. Resultados

| Caso | Requisito | Resultado |
|---|---|---|
| Duplicado secuencial por HTTP | FR-006 | `200` y luego **`409 MOVEMENT_TYPE_DUPLICATE`**, 1 fila |
| Carrera forzada, misma empresa | FR-001/002/003 | **1 alta, 1 `ConflictError` (409), 1 fila**, 0 respuestas 500 |
| Carrera repetida 8 veces | FR-010 | 8/8 igual: una entra, una choca; 8 filas en total |
| Otro error de integridad (clave foránea rota) | FR-004 | `IntegrityError` se propaga; **no** se disfraza de duplicado |
| Sesión tras el conflicto de la consulta previa | FR-005 | sigue trabajando |
| Sesión tras la **colisión real** | FR-005 | sigue trabajando: el savepoint la salva |
| Códigos distintos en paralelo | FR-007 | entran los dos; no se serializa de más |
| Mismo código en dos empresas | FR-008 | `200` y `200`: la identidad incluye la empresa |
| El alta no se vuelve idempotente | FR-009 | quien repite recibe conflicto, no la fila ajena |

## 15. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| MOVTYPE-01 | La colisión deja de traducirse | **muere** — las tres pruebas de carrera |
| MOVTYPE-02 | Cualquier error de integridad pasa por «ya existe» | **muere** — la de la clave foránea |
| MOVTYPE-03 | Sin savepoint | **muere** — la sesión queda abortada tras la colisión real |
| MOVTYPE-04 | El alta explícita se vuelve idempotente | **muere** — el duplicado secuencial y la recuperación |
| MOVTYPE-05 | Se vigila el nombre de otra restricción | **muere** — las tres de carrera |
| MOVTYPE-06 | La consulta previa se olvida de la empresa | **muere** — el mismo código en dos empresas |

**6/6 significativas**, cada una en un camino distinto. Restauración verificada con `cmp`.

Una observación que salió de intentarlo: la primera versión de la prueba de recuperación
**no** mataba MOVTYPE-03, porque resolvía el conflicto con la consulta previa y nunca
llegaba a la violación. La prueba que sí lo mata hace que la sesión perdedora, tras recibir
el conflicto, siga trabajando. Sin esa distinción, el savepoint habría quedado sin cubrir y
la mutación habría sobrevivido por el motivo equivocado.

## 16. Regresión

| Suite | Resultado |
|---|---|
| Dirigida de tipos de movimiento | **10 / 10** |
| Dirigida de inventario (`multiestado`, `putaway`, `multiempresa`) | **56 / 56** |
| **Regresión completa de backend** | **1672 recolectadas · 1648 pasan · 0 fallan · 0 errores · 24 omitidas · 0 avisos · salida 0** |
| Las 16 omitidas por no haber base legacy | sembrada y ejecutadas aparte: `test_mc_preflight.py` **32 / 32** |
| Omitidas que quedan | 8, todas por `KONTROL_S3_ENDPOINT` sin configurar: igual que la línea base registrada |
| `ruff` sobre lo tocado | sin hallazgos |
| `mypy` sobre los dos módulos | **12 avisos antes y 12 después**: ninguno introducido; los 12 son preexistentes |
| Deriva de esquema | **21 → 21**, `NEW_DRIFT = 0` |
| Migraciones · cabeza | **57** · `0057_spec047_notifications` |

La cuenta cuadra con la línea base del ciclo anterior: 1664 recolectadas + 8 pruebas nuevas
= **1672**, y la diferencia entre 1656 y 1648 que pasan son exactamente las 16 de legado,
omitidas por entorno y verificadas después.

### Un fallo de entorno, mío, declarado

La primera ejecución de la regresión dio **37 fallos**, todos en documentos
(`FILE_NOT_SCANNED`, `SCAN_FAILED`). No eran regresión: `/tmp` se recicló entre sesiones y
el `testenv.sh` que reconstruí no exportaba las variables de ClamAV, así que el analizador
no estaba configurado. Reinstalado ClamAV 1.4.3, reconstruida la firma de prueba sobre los
bytes exactos que sube la suite y completado el lanzador, la regresión quedó en 0 fallos.
Nada de esto tocó el repositorio.

## 17. Suite E2E global

| Medida | Valor |
|---|---|
| Ficheros | 30 |
| Pruebas ejecutadas (Chromium) | **224** |
| Pasan | **223** |
| Fallan | **1** |
| Omitidas · sin ejecutar | 0 · 0 |

### El fallo, clasificado

`documents.spec.ts:309` → **`E2E_046_TIPOS`**. Reproducida y medida con precisión: la base
tiene **exactamente 10** tipos documentales y la tabla pagina de diez en diez, así que no
existe «Página siguiente» y `isEnabled()` sobre un botón que no está espera hasta agotar la
prueba. Es lo que su registro describe. Aislada falla igual.

**No es regresión de esta delta**: no se ha tocado ningún fichero de documentos, y el
cambio vive en inventario. **No se cierra aquí** —lo dice el encargo y lo dice el
sentido común: cerrarla exige su propio ciclo—. Solo se reporta: **reproducida**.

| Clase | N.º |
|---|---|
| `PRODUCT_RACE_DEFECT` · `API_CONFLICT_MAPPING_DEFECT` | **0** · **0** |
| `DB_CONSTRAINT_DEFECT` · `TRANSACTION_RECOVERY_DEFECT` | **0** · **0** |
| `NEW_REGRESSION_MOVTYPE` | **0** |
| `E2E_046_TIPOS` | **1** — reproducida, no absorbida |
| `TEST_DEFECT` · `EXTERNAL_ENVIRONMENT` · `PREEXISTING_SEALED` · `AUTH_MC_INTERMITTENT` | 0 · 0 · 0 · 0 |
| `MATERIAL_DECISION_REQUIRED` | **1**, fuera del objetivo: `MOVTYPE-GLOBAL-SIN-UNICIDAD` (§7) |
| `OWNER_IDENTITY_CONFLICT` · `UNKNOWN` | **0** · **0** |

## 18. `/speckit.analyze` final

| Búsqueda | Resultado |
|---|---|
| `check-then-insert` sin protección | **0** en el camino corregido |
| Captura amplia de `IntegrityError` | **0** |
| Violación silenciada · 500 por carrera esperable | **0** · **0** |
| Filas duplicadas tras la carrera | **0** |
| Transacción abortada que se escapa | **0** |
| `retry` · `sleep` · cerrojo de proceso · bloqueo de más | 0 · 0 · 0 · 0 (probado: códigos distintos entran en paralelo) |
| Migraciones · cambios de esquema · deriva nueva | 0 · 0 · 0 |
| Semántica de negocio o de permisos cambiada | **0** |
| Pruebas omitidas o `xfail` añadidas | 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` del objetivo · `UNKNOWN` | 0 · 0 |

## 19. Trazabilidad

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-023-MOVTYPE-001 | Carrera forzada: 1 fila | 01 · 05 |
| FR-023-MOVTYPE-002 | El perdedor recibe `ConflictError` 409 `MOVEMENT_TYPE_DUPLICATE` | 01 · 05 |
| FR-023-MOVTYPE-003 | Ninguna respuesta 500; antes el `IntegrityError` subía crudo | 01 |
| FR-023-MOVTYPE-004 | Clave foránea rota se propaga | 02 |
| FR-023-MOVTYPE-005 | La sesión sigue sirviendo tras la colisión real | 03 |
| FR-023-MOVTYPE-006 | Duplicado secuencial: 200 y 409, 1 fila | 04 |
| FR-023-MOVTYPE-007 | Códigos distintos entran los dos | — |
| FR-023-MOVTYPE-008 | Mismo código en dos empresas: 200 y 200 | 06 |
| FR-023-MOVTYPE-009 | El alta no devuelve la fila ajena | 04 |
| FR-023-MOVTYPE-010 | `tests/concurrency.py::carrera`, que falla si no hubo carrera | 01 |
| FR-023-MOVTYPE-011 | 6 mutaciones, 6 muertas | — |
| FR-023-MOVTYPE-012 | `alembic check` 21 → 21; 57 migraciones; regresión completa en 0 fallos | — |

Cobertura **100 %**, huérfanos **0**.

## 20. Convergencia

| Criterio | Estado |
|---|---|
| Dueña | **RESUELTA** — SPEC023 |
| Identidad lógica | **VERIFICADA** — `(company_id, code)`, medida con dos empresas |
| Contrato de duplicado | **VERIFICADO** — 409 `MOVEMENT_TYPE_DUPLICATE`, medido antes de tocar nada |
| Duplicado secuencial | **CONTROLADO** |
| Carrera forzada | **1 alta · 1 conflicto · 1 fila**, ocho veces seguidas |
| HTTP 500 en la carrera objetivo | **0** |
| Otro error de integridad | **no se disfraza** |
| Recuperación de la transacción | **PASA** |
| Concurrencia de claves distintas | **PASA** |
| Semántica de empresa y de estado | **PRESERVADAS** |
| Migraciones · esquema · deriva nueva | 0 · sin cambios · 0 |
| Regresión dirigida · completa de backend | PASAN · **0 fallos** |
| E2E global | 224 · 223 · 1, clasificada y no absorbida |
| Mutaciones | **6/6 mueren**, restauradas |
| `NEW_REGRESSION_MOVTYPE` · `MATERIAL OQ` (objetivo) · `UNKNOWN` | 0 · 0 · 0 |

**VEREDICTO: CASO A — `INV-MOVTYPE-CARRERA` COMPLETE / CONVERGED.**

SPEC023 sigue `PARTIALLY_IMPLEMENTED`: cerrar esta deuda no la convierte en completa.
