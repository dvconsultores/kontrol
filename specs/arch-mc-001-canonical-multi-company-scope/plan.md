# PLAN — ARCH-MC-001

## Fases

| Fase | Contenido | Por qué va aquí |
|---|---|---|
| **N0** | Gobierno: ADR, matrices, plan de migración y de pruebas | Sin alcance canónico declarado, cada dominio decidiría el suyo |
| **N1** | `CompanyContext` en el backend | **Prerrequisito de todo.** Sin saber en qué empresa ocurre la petición no se puede escribir bien ni una fila |
| **N2** | Cortar la hemorragia | En cuanto haya contexto, ningún escritor puede seguir poniendo `tenant_id` en `company_id`. Cada día que pasa amplía el backfill |
| **N3** | Expandir el esquema | Columnas y relaciones nuevas **sin** destruir las heredadas |
| **N4** | Rellenar y verificar | Clasificación `MC-A`..`MC-E`, informe previo sin escribir, resolución manual auditable |
| **N5** | Migrar los dominios | Servicios, repositorios, API, consultas, eventos y auditoría, por olas |
| **N6** | Frontend | El contexto se propaga; la empresa **no** se añade a cada formulario |
| **N7** | Restringir | `NOT NULL`, FK, únicos e índices, una vez demostrada la integridad |
| **N8** | Contraer | Retirar columnas heredadas y ramas de compatibilidad. Sin modo dual permanente |

> **N1 antes que N2, y N2 antes que N3** no es preferencia. Migrar datos mientras
> se siguen escribiendo mal es rellenar un cubo agujereado.

## Olas de dominio en N5

Orden derivado de las FK reales, no impuesto:

| Ola | Dominio | Tablas | Depende de |
|---|---|---:|---|
| 1 | Organización y accesos | 8 | — |
| 2 | Maestros | 24 | 1 |
| 3 | **Fiscal** | 13 | 1, 2 |
| 4 | Compras | 21 | 2, 3 |
| 5 | Inventario | 13 | 2, 4 |
| 6 | Ventas | 14 | 2, 3, 5 |
| 7 | Tesorería | 15 | 3, 4, 6 |
| 8 | Regulatorio | 11 | 2, 5 |
| 9 | Transversales: auditoría, eventos, informes, documentos | 15 | todas |

Regla dura: **ninguna hija antes que su cabecera** (§106).

Fiscal va en la tercera ola pese a ser el riesgo mayor: necesita maestros
normalizados, y todo lo transaccional depende de sus series.

## Migraciones Alembic

Una por fase y dominio; **nunca** una monolítica para 82 tablas.

| Migración | Fase | Contenido |
|---|---|---|
| `00XX_mc_company_access` | N1 | Acceso usuario–empresa sobre la estructura existente |
| `00XX_mc_expand_<dominio>` | N3 | Columnas nuevas, anulables, sin tocar las heredadas |
| `00XX_mc_backfill_<dominio>` | N4 | Rellena y reporta; **aborta** con críticos sin resolver |
| `00XX_mc_constrain_<dominio>` | N7 | `NOT NULL`, FK, únicos |
| `00XX_mc_contract_<dominio>` | N8 | Retira lo heredado |

Cada `backfill` sigue el patrón de la `0024` de la Spec 046: lee, clasifica,
informa, comprueba sus invariantes y **se detiene** si las incumple.

## Módulos tocados

| Módulo | Naturaleza del cambio |
|---|---|
| `identity_access` | `CompanyContext`, resolución de acceso, dependencia de FastAPI |
| `organization` | Autoridad de empresa; imposición del plan |
| `licensing` | Límite de empresas según derechos |
| Los 8 de negocio | 100 escrituras y 75 lecturas reescritas |
| `documents` | `ResourceKind` declara alcance; 4 entradas nuevas |
| Frontend | Interceptor con la cabecera, selector, invalidación de caché |

## Lo que este plan **no** hace

Implementar la Spec 012, flujos nuevos, reglas fiscales nuevas, ni nada
intercompany. Corrige la propiedad de lo que ya existe.

---

# N7 — PLAN DE INTEGRIDAD ESTRUCTURAL

## 1. Estrategia

Cinco migraciones, separadas por naturaleza del cambio, no por dominio. La razón
es práctica: si una falla, se sabe qué clase de garantía quedó sin aplicar, y
revertir una clase es limpio mientras que revertir «lo de compras» no lo es.

| Nº | Migración | Qué hace |
|---|---|---|
| 0033 | `n7_company_fk` | Claves foráneas de `company_id` a `companies` en las 80 tablas que no las tienen |
| 0034 | `n7_tenant_fk` | Claves foráneas de `tenant_id` a `tenants` en las 3 que faltan |
| 0035 | `n7_not_null` | `company_id` obligatorio donde la evidencia dice que siempre existe |
| 0036 | `n7_consistency` | Coherencia empresa/almacén por clave foránea compuesta |
| 0037 | `n7_indexes` | Índices justificados por patrón de consulta real |

## 2. Esquema y datos, separados

Ninguna de las cinco migra datos. Son cambios de esquema puros, así que
`alembic upgrade --sql` produce SQL válido y se pueden revisar antes de
aplicarlas.

No hay backfill: `N4 Real Backfill` sigue `NOT_APPLICABLE` porque no existe
ninguna instalación desplegada. Es la ventana que N5 identificó y que sigue
abierta.

## 3. Orden y por qué importa

Las claves foráneas van antes que los NOT NULL. Si se invirtiera, una fila con
`company_id` apuntando a nada pasaría el NOT NULL y fallaría después en la clave
foránea, con la mitad de las garantías aplicadas y la otra mitad no.

La coherencia compuesta va después de las claves foráneas simples porque
necesita que el padre tenga una clave única que incluya su empresa.

## 4. Claves foráneas

`company_id VARCHAR(36) → companies.id`, sin cascada.

Borrar una empresa con datos debe fallar. Una empresa es una persona jurídica
con histórico fiscal; que su borrado arrastre asientos, documentos y libros sería
lo contrario de lo que la ley obliga a conservar (P5).

## 5. Obligatoriedad

`company_id` pasa a NOT NULL en las tablas de empresa, con dos excepciones
documentadas: `units_of_measure`, porque Spec 011 estableció que las unidades del
sistema son globales y las de negocio de empresa, y `stored_files`, porque un
archivo existe antes de saber a qué documento pertenecerá.

En una instalación limpia no hay filas nulas que migrar. En una hipotética con
datos, la migración fallaría en vez de inventarse una empresa — que es el
comportamiento correcto y lo que el fixture hostil comprueba.

## 6. Unicidad

**No se cambia ninguna.** Las once que debían ser de empresa ya lo son porque N3
las creó así; las de padre heredan el alcance por la cadena. Cambiar una
restricción correcta para que parezca que N7 hizo algo sería trabajo inventado.

Lo que sí se hace es **probar** que se comportan como dicen: la misma clave en
dos empresas se acepta, repetida dentro de una se rechaza.

## 7. Coherencia entre columnas redundantes

Cinco tablas guardan `company_id` y `warehouse_id` a la vez —las de estructura de
almacén— y hoy nada impide que digan empresas distintas.

Se resuelve con una clave foránea **compuesta** contra una clave única del
almacén que incluya su empresa. No añade columnas: ambas ya existen. No usa
disparadores, que serían lógica escondida en la base para algo que el modelo
relacional expresa por sí solo.

`audit_events` guarda tenant y empresa, pero desde N5 el tenant se deduce de la
empresa al registrarlo, así que no pueden contradecirse por construcción.

## 8. Índices

PostgreSQL no crea índice al declarar una clave foránea. Se añaden solo donde
hay patrón de consulta real: filtrado por empresa en los listados de los dominios
que N5 probó. Se mide con `EXPLAIN` antes de añadir, y no se añade lo que ya
cubre un índice existente.

## 9. Comprobación

| Qué | Cómo |
|---|---|
| Instalación limpia | PostgreSQL 18.6 vacío → head → dos empresas → operar |
| SQL sin conexión | `alembic upgrade --sql` |
| Fixture hostil | Debe **fallar**: contiene filas inválidas a propósito |
| Aborto | Sin escrituras parciales, sin avanzar `alembic_version` |
| Catálogo | `pg_constraint`, `pg_indexes`, `information_schema` |
| Corrupción directa | `INSERT` a mano, comprobando el `SQLSTATE` concreto |
| Paridad fiscal | Mismas bases, importes y totales antes y después |
| Regresión | Las once de N5, las de N6, autenticación y frontend |

## 10. Recuperación

Cada migración tiene su `downgrade`. Como no migran datos, revertir es exacto: se
retira la restricción y el esquema vuelve al estado anterior sin pérdida.

## 11. Lo que no se toca

`legacy_scope_id`, `scope_backfill_class`, ningún mecanismo transicional, la
declaración de la cabecera en OpenAPI, `REM-046-001`, los tipos de recurso
pendientes, la Spec 012 y cualquier capacidad intercompany.

Las guardas de N5 se quedan donde están. N7 añade una cuarta capa a una defensa
que ya tiene tres; no sustituye ninguna.

## 12. CONSTITUTION GATE

| Principio | Verificación | Resultado |
|---|---|---|
| **P4** — núcleo fiscal separado y versionado | N7 no toca fórmulas ni importes; solo de quién es cada fila | PASS |
| **P5** — histórico protegido | Sin cascadas: borrar una empresa con datos falla | PASS |
| **P6** — el backend es la autoridad | N7 refuerza la base, que está por debajo del backend; no mueve autoridad al cliente | PASS |
| **P8** — nada codificado a mano | Las restricciones se derivan del alcance declarado, no de listas escritas a mano | PASS |
| **P13** — integridad transaccional | Las migraciones abortan enteras; sin escrituras parciales | PASS |
| **P17/P22** — autoridad única | Cada tabla mantiene una sola autoridad; las redundantes se hacen coherentes, no se duplican | PASS |
| **P21** — paridad de motor | Todo se valida sobre PostgreSQL 18.6, no sobre SQLite | PASS |
| PostgreSQL como fuente real | El inventario sale de `pg_constraint`, no del ORM | PASS |
| Separación tenant / empresa | Es literalmente el objetivo de la fase | PASS |
| Sin reinterpretación del histórico | No se migra ni se reescribe ningún dato | PASS |
| Sin repliegue silencioso | Una restricción rota falla; no degrada | PASS |
| Sin doble autoridad | Las columnas redundantes se atan entre sí, no compiten | PASS |
| Sin implementar antes de analizar | El ciclo Spec se ejecuta completo antes de la primera migración | PASS |
| Sin tocar Specs cerradas fuera de alcance | 045, 046 y 008 no se modifican | PASS |
| Coherente con ADR-D0-014 | N7 aplica la decisión del ADR a la capa estructural | PASS |

**`CONSTITUTION GATE: PASS`**
