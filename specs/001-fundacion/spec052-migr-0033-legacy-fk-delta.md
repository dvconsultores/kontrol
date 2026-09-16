# SPEC 052 · DELTA DIRIGIDO MIGR-0033-FK-HUERFANA

> Delta dirigido dentro de la Spec 052 —instalador, actualización y cadena de
> migraciones—, cuyos artefactos viven en `specs/001-fundacion` por el mapa de
> equivalencias. No abre Spec nueva. No cambia el estado global de la 052 ni de la 001.
>
> Corrige **un** bloqueante descubierto por `KONTROL_MASTER_COMPLETENESS_AUDIT`:
> la actualización de una base con histórico aborta al crear una clave foránea de
> empresa sobre una fila que una migración anterior preservó a propósito.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `cf11639` |
| `ACTUAL_HEAD` | `cf11639` — coincide |
| `COMMITS_AFTER_CF11639` | **0** |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | un fichero sin confirmar: `KONTROL_MASTER_COMPLETENESS_AUDIT.md` |
| PostgreSQL | 16.2 (`pgserver`), objetivo 18.6 → `ENVIRONMENT_BASELINE_DEVIATION` |

### Clasificación del fichero no confirmado

`KONTROL_MASTER_COMPLETENESS_AUDIT.md` es el producto de la auditoría de solo lectura
anterior, **ajeno a este delta**. La práctica documental del repositorio versiona las
auditorías bajo `qa/audits/<NOMBRE>/` (precedente: `qa/audits/KONTROL-AUDIT-20260812/`),
no en la raíz. Por tanto: **no se incorpora a este commit, no se borra y no se mueve**.
Queda como fichero preservado fuera del delta, y su ubicación definitiva es decisión
documental de la dueña.

## 1. Ficha de la deuda

| Campo | Contenido |
|---|---|
| Identificador | **MIGR-0033-FK-HUERFANA** |
| Origen | Auditoría maestra de completitud, §20 |
| Severidad | **BLOCKER** para cualquier instalación con histórico |
| Síntoma | `alembic upgrade head` aborta en `0033_n7_company_fk` con `ForeignKeyViolation` |
| Clase | `REFERENTIAL_INTEGRITY_FAILURE` en el camino de actualización |

## 2. Dueña canónica

| Papel | Spec | Justificación física |
|---|---|---|
| **Dueña principal** | **052** — instalador / actualización / migración | El contrato roto es el de actualización: `deployment-model.md:36` define `kontrol update` como «preflight, backup, pull, migrate, health, rollback». Lo que falla es `migrate` |
| Arquitectura de apoyo | **001** — fundación y cadena estructural | Misma carpeta documental; la cadena de migraciones es suya |
| Autora de la migración que falla | **ARCH-MC-001** | `0033_n7_company_fk` es la migración N7 de ARCH-MC-001 (`COMPLETE / GLOBALLY CONVERGED`) |
| Autora de la regla de preservación | **045** | `0016_approvals_backfill` preserva la fila legada (FR-045-074, AC-22) |
| Dueña del dato | **044** — regulación | `regulatory_approval_requests` nace en `0008_regulacion` y la renombra `0015_approvals` |

**`OWNER_IDENTITY_CONFLICT` = 0.** No hay disputa: la 052 posee el contrato de
actualización; ARCH-MC-001 y la 045 son autoras de las dos piezas que chocan, y la 044
es dueña del dato. Ninguna de las tres reclama el camino de actualización.

## 3. Reproducción previa a cualquier cambio

Escenario canónico, el mismo que usa `qa/pg-migration-validation.sh` (Caso B).

| Dato | Valor capturado |
|---|---|
| Revisión de partida | `0014_numeric_money_2` — 145 tablas |
| Objetivo | `0057_spec047_notifications` |
| Filas legadas sembradas | 4 (`leg-1..leg-4`), tres con empresa válida y una colgante |
| Fila huérfana | `leg-4`, `company_id = 'co-BORRADA'` |
| ¿Existe esa empresa? | **no** — `SELECT count(*) FROM companies WHERE id='co-BORRADA'` → `0` |
| Revisión que falla | **`0033_n7_company_fk`** |
| Tabla | `regulatory_approval_requests` |
| Restricción | `fk_regulatory_approval_requests_company` |
| Error | `psycopg2.errors.ForeignKeyViolation` — SQLSTATE **23503** |
| SQL | `ALTER TABLE regulatory_approval_requests ADD CONSTRAINT fk_… FOREIGN KEY(company_id) REFERENCES companies (id)` |
| Salida de `alembic` | **1** |
| Revisión final | `0014_numeric_money_2` — la actualización es atómica y revierte entera |
| Tablas al fallar | 145 (frente a 204 de la instalación limpia) |

Evidencia: `evidence/migr-0033/reproduccion-pre-fix.txt`.

## 4. Causa raíz

`0016_approvals_backfill` **sabía** de la fila colgante y la trató a propósito. Su
comentario, literal:

> «La tabla legada guarda `company_id` como texto **SIN clave foránea**; la nueva sí la
> tiene. Una fila legada con referencia colgante abortaría todo el upgrade, así que se
> omite y se deja constancia en el log de la migración.»

Es decir: 0016 protegió la tabla **nueva** (`approval_requests`, que sí tiene clave
foránea desde `0015`) dejando la fila en la tabla **legada**, apoyándose en una premisa
explícita: que la legada no tiene clave foránea.

Diecisiete revisiones después, `0033_n7_company_fk` añade `fk_<tabla>_company` a **80
tablas** en un bucle sin guarda alguna, y `regulatory_approval_requests` está en la
lista. La premisa de 0016 deja de ser cierta y su fila preservada se vuelve ilegal.

**Las dos decisiones son correctas por separado e incompatibles juntas.** Ninguna es un
descuido: 0016 documenta la suya y 0033 documenta la suya («esta migración se lo pide a
PostgreSQL, que no se puede olvidar de comprobarlo»).

## 5. Política de migraciones históricas — resuelta con evidencia

| Pregunta | Respuesta | Autoridad |
|---|---|---|
| ¿Prohíbe el proyecto modificar una migración ya escrita? | **No existe tal política.** Búsqueda en Constitución, ADR-001..015, gobernanza y documentos de la 052: sin regla de inmutabilidad de migraciones | ausencia verificada |
| ¿Hay instalaciones desplegadas que ya aplicaron `0033`? | **No.** Repetido y documentado: `0038_n8_drop_legacy_scope` («No existe ninguna instalación desplegada»), ARCH-MC-001 N4 (`NOT_APPLICABLE — sin instalaciones heredadas`), N8, y `specs/012-maestros-comerciales/migration-report.md:29` | tres fuentes |
| ¿Puede arreglarse con una migración **nueva**? | **No.** La actualización muere *en* `0033`; ninguna revisión posterior llega a ejecutarse. Una `0058` sería inalcanzable | demostrado en §3 |
| Si una base ya está en cabeza, ¿cambia algo? | **No.** Toda base que superó `0033` carece de huérfanas por construcción; con el código nuevo llega al mismo estado final (restricción validada) | razonamiento sobre el propio mecanismo |

**Escenario A del gate**: no hay releases externas y la política lo permite → *es válido
corregir `0033`*, y además es el **único** lugar donde la corrección es alcanzable.

## 6. `/speckit.specify`

Requisitos nuevos, numerados tras el máximo real de la Spec dueña (`FR-001-091`):

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-092 | Una base histórica con una referencia de empresa colgante, preservada deliberadamente por una migración anterior, **debe alcanzar la cabeza de Alembic** | P0 |
| FR-001-093 | La actualización **no elimina** el registro histórico ni ninguno de sus campos de negocio | P0 |
| FR-001-094 | La actualización **no fabrica** ninguna empresa ni **reasigna** en silencio la referencia histórica | P0 |
| FR-001-095 | Tras la actualización, una escritura nueva con empresa inexistente **es rechazada por PostgreSQL**; con empresa válida, aceptada | P0 |
| FR-001-096 | La instalación limpia de cero a cabeza sigue funcionando y termina con las restricciones **validadas** | P0 |
| FR-001-097 | El aislamiento multiempresa y multitenant no se degrada: una fila legada huérfana no abre ninguna lectura ni escritura cruzada | P0 |
| FR-001-098 | Existe **prueba permanente** que reproduce la actualización histórica real y falla si el conflicto vuelve | P0 |
| FR-001-099 | El tratamiento es **idempotente**: reejecutar `upgrade head` sobre una base ya en cabeza no cambia nada | P0 |
| FR-001-100 | No se introduce deriva de esquema nueva: `NEW_DRIFT_FROM_MIGR_0033 = 0` | P0 |
| FR-001-101 | El tratamiento del dato legado queda **anotado y auditable** en la salida de la migración | P1 |

Criterios de aceptación, tras `AC-012`:

| ID | Criterio |
|---|---|
| AC-013 | **Dado** un histórico con una fila de empresa colgante, **cuando** se actualiza a cabeza, **entonces** termina con éxito y la fila sigue ahí con su carga intacta |
| AC-014 | **Dado** ese mismo histórico ya actualizado, **cuando** se inserta una fila nueva con empresa inexistente, **entonces** PostgreSQL la rechaza |
| AC-015 | **Dado** una base vacía, **cuando** se actualiza a cabeza, **entonces** las 80 restricciones de empresa quedan **validadas** |
| AC-016 | **Dado** el histórico actualizado, **entonces** no existe ninguna empresa nueva creada por la migración y ninguna fila cambió de empresa |
| AC-017 | **Dado** varios huérfanos históricos, **entonces** todos se preservan y la actualización igualmente llega a cabeza |

## 7. `/speckit.clarify` — veinte puntos

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | Dueña canónica | 052; apoyo 001; autoras ARCH-MC-001 y 045; dato 044 (§2) | No |
| 2 | Origen funcional real de la tabla | `0008_regulacion` la crea; `0015_approvals` la renombra; módulo `regulatory` | No |
| 3 | Revisión que preserva el legado | `0016_approvals_backfill` | No |
| 4 | Revisión que falla | `0033_n7_company_fk` | No |
| 5 | Nulabilidad real de `company_id` | `String(36)`, **no nula** en la tabla legada; la clave foránea no exige nulabilidad | No |
| 6 | Semántica del registro huérfano | Aprobación regulatoria histórica de una empresa que ya no existe. **MC-D `NON_RECONSTRUCTIBLE`** en la matriz de ARCH-MC-001: «sin evidencia → anotar; no se rellena» | No |
| 7 | Política de migraciones históricas | No existe regla de inmutabilidad (§5) | No |
| 8 | ¿Puede modificarse `0033`? | Sí, y es el **único** punto alcanzable (§5) | No |
| 9 | ¿Releases externos? | Ninguno: sin instalaciones desplegadas, tres fuentes | No |
| 10 | Qué significa «preservar» en 0016 | La fila **permanece** en la tabla legada, íntegra, y **no** se migra al motor | No |
| 11 | ¿Existe mecanismo de cuarentena aprobado? | No hay tabla de cuarentena. El mecanismo aprobado es **anotar** (MC-D) y es el que se usa | No |
| 12 | Integridad esperada para datos nuevos | Obligatoria: la tabla legada **sigue siendo camino de escritura vivo** (`regulatory/service.py:335`) | No |
| 13 | Estado esperado de la restricción en instalación limpia | **Validada**, idéntica a hoy | No |
| 14 | Estado esperado en actualización con huérfana | **`NOT VALID`**: tolera lo histórico, exige integridad en toda escritura nueva | No |
| 15 | Contrato de `downgrade` | `0033.downgrade()` retira las 80 restricciones; se conserva sin cambio semántico | No |
| 16 | Impacto en paridad ORM ↔ base | Ninguno: una restricción `NOT VALID` aparece igual en la introspección; `test_el_orm_y_la_base_no_difieren_en_nada` compara presencia, no validación | No |
| 17 | Impacto en `alembic check` | Ninguno esperado: la comparación no distingue el estado de validación. Se mide (§13) | No |
| 18 | Impacto en la deriva de esquema | Baseline heredada 21 operaciones; exigencia: **ninguna nueva** | No |
| 19 | Impacto en seguridad de empresa/tenant | Ninguno: la fila huérfana no pertenece a ninguna empresa viva, así que ningún contexto la alcanza | No |
| 20 | Impacto en el instalador | Positivo y acotado: `migrate` deja de abortar. No se toca `install.sh` ni `update.sh` | No |

**MATERIAL OQ = 0. UNKNOWN = 0.** El ciclo continúa.

## 8. `/speckit.plan`

| # | Paso |
|---|---|
| W01 | Checkpoint y entorno — **hecho** |
| W02 | Reproducir el fallo canónico — **hecho** |
| W03 | Dueña de la cadena de migraciones — **hecho** |
| W04 | Semántica del dato legado — **hecho** (MC-D) |
| W05 | Política de migraciones históricas — **hecho** |
| W06 | Análisis de alternativas — §9 |
| W07 | Diseño de la remediación elegida |
| W08 | Pruebas de preservación de datos |
| W09 | Pruebas de integridad futura |
| W10 | Cero → cabeza |
| W11 | Histórico → cabeza |
| W12 | Mixto válido/huérfano |
| W13 | Idempotencia y repetición |
| W14 | Paridad ORM/Alembic |
| W15 | Medición de deriva |
| W16 | Arranque de la aplicación |
| W17 | Pruebas dirigidas de backend |
| W18 | Regresión completa de backend, sola |
| W19 | Mutaciones M0033-01..05 |
| W20 | `analyze` final |
| W21 | Trazabilidad |
| W22 | Convergencia, commit, alto |

## 9. Alternativas evaluadas

| Opción | En qué consiste | Veredicto |
|---|---|---|
| **A · `NOT VALID`** | Crear la restricción sin verificar lo existente; PostgreSQL **sí** la exige en toda inserción o actualización posterior | **ELEGIDA** |
| B · Normalización con procedencia | Poner la referencia a nula y guardar el valor original en otra columna | Rechazada: exige cambiar el esquema de una tabla legada y **altera el dato histórico** para satisfacer una restricción |
| C · Cuarentena en tabla aparte | Mover las filas huérfanas a un almacén histórico | Rechazada: mueve el dato de sitio, rompe su identidad y crea esquema nuevo sin autoridad |
| D · Reparación previa | Rellenar la empresa antes de crear la restricción | **Prohibida** por la propia arquitectura: «No se inventa empresa» y MC-D «no se rellena» |
| E · Excluir la tabla de la lista | Dejar la tabla legada sin clave foránea | Rechazada: la tabla **sigue recibiendo escrituras nuevas**; renunciar a la integridad futura es peor que el problema |

**Por qué A.** Es la única que satisface a la vez las cinco invariantes: preserva el
histórico sin tocarlo, no inventa empresa, no reasigna, exige integridad a todo dato
nuevo, y deja la instalación limpia exactamente como está hoy. Además implementa
literalmente lo que la arquitectura ya había aprobado para MC-D: **anotar, no rellenar**.

### Detalle del diseño

Por cada una de las 80 tablas, en el mismo bucle:

1. `ADD CONSTRAINT … FOREIGN KEY (company_id) REFERENCES companies (id) NOT VALID`.
2. Contar referencias colgantes.
3. Si hay **cero** → `VALIDATE CONSTRAINT`: la instalación limpia y toda base sana
   terminan idénticas a hoy.
4. Si hay alguna → se deja `NOT VALID` y se **anota** por salida de la migración, igual
   que hace `0016`, diciendo tabla, cuántas y con qué valores.

Alembic 1.14.0 no expone `NOT VALID`, así que se usa `op.execute` con SQL explícito,
patrón ya presente en `0019`, `0020` y `0041`.

## 10. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-MIGR-01 | Dueña canónica resuelta | **PASA** — §2 |
| G-MIGR-02 | Fallo original reproducido | **PASA** — §3 |
| G-MIGR-03 | Semántica del legado entendida | **PASA** — MC-D |
| G-MIGR-04 | Política de migraciones históricas entendida | **PASA** — §5 |
| G-MIGR-05 | Sin remediación destructiva | **PASA** — no hay `DELETE`, `DROP` ni `TRUNCATE` |
| G-MIGR-06 | Sin reasignación silenciosa | **PASA** — no se escribe `company_id` |
| G-MIGR-07 | Sin empresa fabricada | **PASA** — no se inserta en `companies` |
| G-MIGR-08 | Integridad futura preservada | **PASA** — `NOT VALID` exige a las escrituras nuevas |
| G-MIGR-09 | Cero → cabeza preservado | **PASA** — validada igual que hoy |
| G-MIGR-10 | Histórico → cabeza definido | **PASA** — contrato B |
| G-MIGR-11 | Invariante multiempresa preservada | **PASA** |
| G-MIGR-12 | Sin limpieza de esquema ajena | **PASA** — no se toca la deriva heredada |
| G-MIGR-13 | Sin requerir D0-06 ni D0-07 | **PASA** |
| G-MIGR-14 | `downgrade` conocido | **PASA** — §7 punto 15 |
| G-MIGR-15 | Estrategia de mutación significativa | **PASA** — §12 |
| G-MIGR-16 | Material OQ = 0 | **PASA** |
| G-MIGR-17 | UNKNOWN = 0 | **PASA** |
| G-MIGR-18 | Trazabilidad 100 % | **PASA** — §14 |

## 11. `/speckit.checklist`

- [ ] HEAD verificado · árbol clasificado · dueña resuelta · dueña del dato resuelta
- [ ] `0016` y `0033` leídas enteras; historial revisado
- [ ] Fallo reproducido; fila huérfana capturada; ausencia de la empresa probada
- [ ] Restricción exacta capturada; política de migraciones resuelta
- [ ] Remediación con autoridad; sin borrado, sin empresa falsa, sin reasignación
- [ ] Escritura futura inválida rechazada; válida aceptada
- [ ] Instalación limpia, actualización histórica, mixto y múltiples huérfanos diseñados
- [ ] Repetición, paridad ORM, deriva y arranque diseñados
- [ ] Mutaciones definidas; Material OQ = 0; UNKNOWN = 0; trazabilidad 100 %

## 12. `/speckit.tasks`

| ID | Tarea | Fichero | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Restricción `NOT VALID` + validación condicional + anotación | `alembic/versions/0033_n7_company_fk.py` | FR-001-092, 095, 096, 101 | M0033-01, 03, 04, 05 |
| T-02 | Prueba permanente de actualización histórica | `tests/test_spec052_migration_0033_legacy.py` | FR-001-092, 093, 098 | M0033-01, 02 |
| T-03 | Casos mixto, múltiples huérfanos y repetición | mismo fichero | FR-001-097, 099 | M0033-02 |
| T-04 | Casos de integridad futura (válida y inválida) | mismo fichero | FR-001-095 | M0033-04 |
| T-05 | Guarda de instalación limpia: 80 restricciones validadas | mismo fichero | FR-001-096 | M0033-05 |
| T-06 | Caso B del guion canónico pasa a esperarse PASS | `qa/pg-migration-validation.sh` | FR-001-092 | — |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 13. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---:|
| BLOCKER interno no entendido | 0 |
| CRITICAL no clasificado | 0 |
| CONTRADICTIONS | 0 |
| OWNER_IDENTITY_CONFLICT | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRACEABILITY | 100 % |

Se consume la autorización expresa del §5 del encargo y se implementa.

## 14. `/speckit.implement`

| Fichero | Cambio |
|---|---|
| `resources/backend/alembic/versions/0033_n7_company_fk.py` | El bucle llama a `_clave_de_empresa(tabla)`: crea la restricción `NOT VALID`, cuenta las referencias colgantes, **valida** si no hay ninguna y **anota** si las hay |
| `resources/backend/tests/test_spec052_migration_0033_legacy.py` | Prueba permanente, 10 casos sobre PostgreSQL real |

**Ficheros de producto de la aplicación: 0.** No se tocan modelos, servicios, rutas ni
frontend. El cambio vive entero en la cadena de migraciones y su prueba.

`0016` **no se modifica**: su decisión era correcta y sigue siéndolo. Lo que se corrige
es la migración que invalidó su premisa.

### Por qué se modifica una migración ya escrita

Tres razones, todas verificadas en §5:

1. No existe política de inmutabilidad de migraciones en el repositorio.
2. No hay ninguna instalación desplegada que la haya aplicado.
3. **Es el único punto alcanzable.** Una migración nueva jamás se ejecutaría: la
   actualización muere en `0033`.

Y una garantía sobre lo ya existente: cualquier base que hoy esté en cabeza superó
`0033` con el código anterior, lo que demuestra que no tenía referencias colgantes; con
el código nuevo habría llegado al mismo estado final —restricción **validada**—. El
cambio no altera ninguna base existente.

## 15. Evidencia — `evidence/migr-0033/`

| Fichero | Contenido |
|---|---|
| `reproduccion-pre-fix.txt` | El fallo con el código anterior: `0033`, SQLSTATE 23503, vuelta a `0014`, 145 tablas |
| `invariantes-post-fix.txt` | Histórico íntegro, 0 empresas fabricadas, 0 reasignaciones, estados de validación, integridad futura y arranque |
| `guion-canonico-post-fix.txt` | `qa/pg-migration-validation.sh` completo: Caso A y Caso B, ambos en verde |
| `mutaciones.txt` | M0033-01..05 con restauración verificada por `cmp` |

### Matriz de migración

| Contrato | Resultado |
|---|---|
| Cero → cabeza | **PASS** — 204 tablas, `current == heads`, una sola cabeza |
| Histórico canónico (1 huérfana) → cabeza | **PASS** — antes abortaba |
| Histórico válido (sin huérfanas) → cabeza | **PASS** — incluido en el caso mixto |
| Mixto válido + huérfano → cabeza | **PASS** — 3 válidas y 3 huérfanas de **dos** empresas distintas |
| Múltiples huérfanos → cabeza | **PASS** — `leg-huerf-1..3` |
| Cabeza → cabeza (repetición) | **PASS** — sin cambios en ningún conteo |
| `downgrade` | Sin cambio semántico: `0033.downgrade()` sigue retirando las 80 restricciones |

### Integridad y preservación

| Comprobación | Resultado |
|---|---|
| Filas legadas antes / después | 6 / 6 — ninguna borrada |
| Campos de negocio (id, empresa, referencia, importe, decisión, estado) | idénticos, campo a campo |
| Empresas fabricadas | **0** |
| Reasignaciones silenciosas | **0** — cada fila conserva su empresa original |
| Migradas al motor | solo las 3 de empresa viva, como manda la `0016` |
| Restricciones `NOT VALID` tras la actualización | **1**, `regulatory_approval_requests` |
| Restricciones validadas | 90 |
| Instalación limpia: `NOT VALID` | **0** |
| `INSERT` con empresa inexistente | **rechazado** (23503) |
| `UPDATE` hacia empresa inexistente | **rechazado** (23503) |
| `INSERT` con empresa real | aceptado |

### Mutaciones

| Mutación | Qué altera | Resultado |
|---|---|---|
| M0033-01 | Retira la remediación (restricción sin `NOT VALID`) | **muere** — la actualización histórica no llega a cabeza |
| M0033-02 | Resuelve borrando las filas huérfanas | **muere** — cae la preservación del histórico |
| M0033-03 | Fabrica la empresa que falta | **muere** — cae «no se fabrica ninguna empresa» |
| M0033-04 | Debilita la integridad futura (retira la restricción) | **muere** — la escritura inválida deja de rechazarse |
| M0033-05 | Deja la instalación limpia sin validar | **muere** — cae la guarda de instalación limpia |

5/5 semánticamente efectivas; restauración `cmp` idéntica en las cinco.

### Deriva de esquema

| Medición | Valor |
|---|---:|
| `alembic check` sobre base limpia en cabeza, antes | 21 operaciones |
| `alembic check` sobre base limpia en cabeza, después | **21 operaciones**, la misma lista |
| **`NEW_DRIFT_FROM_MIGR_0033`** | **0** |

Una restricción `NOT VALID` se introspecciona igual que una validada, de modo que ni
`alembic check` ni la prueba de paridad ORM ↔ base ven diferencia alguna.

### El guion canónico de QA

`qa/pg-migration-validation.sh` **no se modifica**. Su Caso B ya sembraba la fila
huérfana y ya esperaba conteos completos; lo que ocurría es que fallaba. Ahora pasa y
produce exactamente lo que la Spec 045 publicó en su día: 4 filas legadas íntegras y 3
migradas. No se ha retirado la condición adversa ni se ha debilitado nada.

## 16. Paridad, arranque y prueba de no interferencia

| Comprobación | Resultado |
|---|---|
| `test_el_orm_y_la_base_no_difieren_en_nada` | **PASA** |
| `test_migrations_offline`, `test_documents_migration_0024`, `test_architecture_scope` | **PASAN** (43 pruebas dirigidas en conjunto) |
| Multiempresa: `test_mc_security_045_046`, `test_mc_purchasing_ap_ab`, `test_mc_inventory_ab` | **PASAN** (40 pruebas) |
| Arranque sobre instalación limpia | `live=200 ready=200 {"database":"ok"}` |
| Arranque sobre instalación histórica ya actualizada | `live=200 ready=200 {"database":"ok"}` |

### El esquema producido es idéntico

Para descartar de raíz que este cambio pueda alterar el comportamiento de cualquier
prueba, se construyeron dos bases desde cero —una con el código anterior de `0033` y
otra con el nuevo— y se compararon sus volcados de esquema completos:

```
líneas comparadas: 5144 vs 5144
diferencias: 0
restricciones de empresa sin validar: 0 en ambas
```

La única diferencia bruta era el propietario de las tablas, consecuencia de qué usuario
creó cada base, no del cambio. **En una instalación limpia el resultado es exactamente
el de antes**, lo que hace imposible que este delta afecte a ninguna prueba de dominio.

## 17. Clasificación de lo encontrado

| Hallazgo | Clase | Tratamiento |
|---|---|---|
| El conflicto `0016` ↔ `0033` | `REFERENTIAL_INTEGRITY_FAILURE` en la actualización | **Corregido** en este delta |
| 37 fallos de documentos en la primera tanda de regresión | `EXTERNAL_ENVIRONMENT` | Mi guion de entorno omitió las variables de ClamAV: todas las respuestas eran `SCAN_FAILED`. Con el antivirus configurado, las 65 pruebas de documentos pasan. Corregido el guion, repetida la tanda |
| `test_ttl_opcional…` (Spec 030) en una de las tres tandas | `TEST_DEFECT` intermitente, **no absorbido** | Ver abajo |

### El fallo intermitente de la Spec 030

Falló **una** vez de tres, con un `401` al pedir `/inventory/balances` dentro del arnés
multiempresa compartido. Tres hechos lo sitúan fuera de este delta:

1. **Pasó con este mismo cambio** en otra tanda completa: mismo código, resultado
   distinto ⇒ intermitente, no determinista.
2. **Pasa aislado**: 26/26 en su fichero.
3. **El esquema es idéntico** con y sin el cambio (§16), de modo que no existe mecanismo
   por el que una migración pueda alterar una respuesta de autenticación.

Se registra como deuda nueva **no absorbida**: `AUTH-MC-INTERMITENTE` — el arnés
`conftest_multicompany` pide un token nuevo en cada llamada y, en tandas largas, alguna
petición recibe `401`. Dueña sugerida: 054 (QA integral). No se toca aquí.

## 18. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación que lo mata | Evidencia |
|---|---|---|---|
| FR-001-092 | `test_una_instalacion_con_historico_huerfano_llega_a_la_cabeza` | M0033-01 | `guion-canonico-post-fix.txt` |
| FR-001-093 | `test_el_historico_sobrevive_entero_y_sin_un_solo_cambio` | M0033-02 | `invariantes-post-fix.txt` |
| FR-001-094 | `test_no_se_fabrica_ninguna_empresa` + preservación de empresa por fila | M0033-03 | ídem |
| FR-001-095 | `test_una_escritura_nueva_con_empresa_inexistente_es_rechazada`, `…_mover_una_fila…`, `…_con_empresa_real_se_acepta` | M0033-04 | ídem |
| FR-001-096 | `test_una_instalacion_limpia_termina_con_todo_validado` | M0033-05 | `guion-canonico-post-fix.txt` |
| FR-001-097 | Suites multiempresa + preservación sin reasignación | M0033-03 | §16 |
| FR-001-098 | El fichero entero es la prueba permanente | M0033-01 | `tests/test_spec052_migration_0033_legacy.py` |
| FR-001-099 | `test_repetir_la_actualizacion_no_cambia_nada` | M0033-02 | `invariantes-post-fix.txt` |
| FR-001-100 | `alembic check` antes y después | — | §15 |
| FR-001-101 | Anotación `[0033]` en la salida de la migración | M0033-01 | `guion-canonico-post-fix.txt` |

| Contador final | Valor |
|---|---:|
| BLOCKER no explicado | 0 |
| CRITICAL no explicado | 0 |
| CONTRADICTIONS | 0 |
| OWNER_IDENTITY_CONFLICT | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| **TRACEABILITY** | **100 %** |

## 19. Deudas no absorbidas

Seis `float` de tesorería · CLOCK-013 · E2E-031-RESERVAS · E2E-HELPER-EMPRESA-AMBIGUO ·
INBOX-045-AISLAMIENTO · E2E-046-TIPOS · ORPHAN-046-SINGLE · IDEM-046-TRUNC · paginación
de la bandeja · DT-03, 04, 06, 07, 10, 11, 12, 13, 14, 15, 16, 17, 18 · D0-06 · D0-07 ·
OQ-048-01/02/03 · MD-049-01/02 · camino tras `EXPIRED` · deriva heredada de 21
operaciones · Spec 018 · certificación de compras.
Y la nueva: **AUTH-MC-INTERMITENTE**.

## 20. Estado resultante

| | |
|---|---|
| **MIGR-0033-FK-HUERFANA** | **CLOSED / CONVERGED** |
| Spec 052 | sigue `PARTIALLY_IMPLEMENTED`: quedan ejecución de instalador y actualizador, etiqueta `latest` y validación operativa |
| Spec 001 | sin cambio de estado |
| ARCH-MC-001 | sin cambio de estado; su migración N7 conserva intención y alcance |
| Spec 045 | su evidencia del Caso B **vuelve a reproducir** |

## 21. Regresión completa de backend

Ejecutada **sola**, con el cambio puesto, sobre PostgreSQL 16.2 y `TZ=UTC`.

| Métrica | Valor |
|---|---:|
| TOTAL recogidas | **1.597** |
| PASSED | **1.573** |
| FAILED | **0** |
| ERRORS | **0** |
| SKIPPED | **24** |
| Saltos esperados | 24 — 8 de S3 (dependencia externa declarada) y 16 que exigen la base legada hostil, ausente en esa tanda |
| Saltos inesperados | **0** |
| WARNINGS | **0** |
| EXIT | **0** |
| Duración | 26:50 |

El denominador se remide, no se hereda: la tanda anterior documentada tenía 1.587
pruebas (1.579 + 8); este delta añade las **10** de su prueba permanente, de donde
1.597.

Los 16 saltos por base legada **no se dejaron sin verificar**: sembrada la base hostil
con `qa/n4-legacy-hostile-seed.py`, la suite que los contiene pasa entera —
`test_mc_preflight.py` **32/32**—, que es justamente el camino de migración de una
instalación heredada, el más pertinente para este delta.

### Las tres tandas completas de esta sesión

| # | Código | Entorno | Resultado | Lectura |
|---|---|---|---|---|
| 1 | con el cambio | sin ClamAV | 37 fallos, todos de documentos | `EXTERNAL_ENVIRONMENT`: mi guion omitía el antivirus. La Spec 030 **pasó** |
| 2 | con el cambio | completo | 1 fallo: `test_ttl_opcional…` con un `401` | `TEST_DEFECT` intermitente del arnés multiempresa |
| 3 | con el cambio | completo | **1.573 pasadas, 0 fallos** | La tanda de referencia |
| — | **en HEAD**, sin el cambio | completo | sin fallos | Contraste para clasificar el nº 2 |

La Spec 030 pasó en dos de las tres tandas con este mismo código y falla en ninguna al
ejecutarse aislada: es intermitente, y §17 lo registra como deuda ajena.
