# EL FIXTURE HOSTIL Y LA EVIDENCIA DE CLASIFICACIÓN — N8

Ejecutado sobre PostgreSQL 18.6, esquema en `0032` —el estado anterior a las
claves foráneas de N7, porque una instalación heredada no las tiene—, con las
columnas de transición ya retiradas del producto.

## Classification Matrix

| Caso | Semilla real | Ejecutado | Esperado | Obtenido | Cero escrituras | Repetible | Veredicto |
|---|---|---|---|---|---|---|---|
| `MC-A` | Tercero y serie de un tenant con una sola empresa en ese instante | Sí | `MC-A` | **3** | Sí | Sí | **PASS** |
| `MC-B` | Saldo sin empresa, deducible por su artículo | Sí | `MC-B` | **1** | Sí | Sí | **PASS** |
| `MC-C` | Fila creada tras la segunda empresa; y dos autoridades discrepantes | Sí | `MC-C` | **2** | Sí | Sí | **PASS** |
| `MC-D` | Tercero de un tenant **sin ninguna empresa** | Sí | `MC-D` | **1** | Sí | Sí | **PASS** |
| `MC-E` | Serie fiscal ambigua, dominio crítico | Sí | `MC-E` | **1** | Sí | Sí | **PASS** |
| `INVALID_LEGACY_SCOPE` | Tercero con un valor que no es tenant ni empresa | Sí | `INVALID_LEGACY_SCOPE` | **1** | Sí | Sí | **PASS** |
| `CROSS_TENANT` | Saldo con empresa real de **otro** cliente que su autoridad | Sí | `CROSS_TENANT` | **1** | Sí | Sí | **PASS** |
| `OK` | Filas que ya tenían empresa | Sí | `OK` | **6** | Sí | Sí | **PASS** |

## Master Strategies

| Estrategia | Fixture real | Condición de disparo | Obtenido | Cero escrituras | Repetible | Veredicto |
|---|---|---|---|---|---|---|
| `MASTER_ASSIGN` | Artículo con evidencia propia de una empresa | Una empresa, evidencia directa | **7** | Sí | Sí | **PASS** |
| `MASTER_CLONE` | Movimiento cuyo artículo y tipo son de **dos** empresas del mismo tenant | Dos empresas | **1** | Sí | Sí | **PASS** |
| `MASTER_DERIVE` | Fila sin empresa propia, resuelta por su relación obligatoria | Una empresa, por relación | **1** | Sí | Sí | **PASS** |
| `MASTER_MANUAL_REVIEW` | Artículo sin evidencia y sin relación | Ninguna empresa | **5** | Sí | Sí | **PASS** |

## Dos defectos reales que este sello destapó

Ninguno era una laguna de pruebas: eran capacidades declaradas y no
implementadas. La diferencia entre «la rama existe» y «hay ejecución» resultó ser
la diferencia entre un nombre y una función.

### `CROSS_TENANT` nunca se emitía

Una fila con empresa **real** pero de otro cliente entraba por la primera rama
del clasificador —«¿ya contiene una empresa real? entonces no hay nada que
reconstruir»— y se marcaba `OK`. Una integridad rota entre instalaciones se
informaba como correcta.

La función `cross_tenant()` existía, con `LIMIT 0` y un comentario que la
declaraba plantilla. Nadie la llamaba.

**Corregido**: cuando la fila tiene autoridad, se compara el tenant de su empresa
con el de la empresa que dice la autoridad. Sin autoridad no se puede saber, y
suponerlo sería inventar; con autoridad la comparación es exacta.

### Las estrategias de maestro no se calculaban

`MAESTROS` estaba definido y sin usar; `estrategia_de_maestro` no la invocaba el
ejecutor. Las cuatro estrategias eran nombres en un enum, comprobados con
conjuntos sintéticos.

Y `MASTER_DERIVE` **no podía devolverse nunca**: el enum lo definía —«se deduce
por una relación obligatoria»— y la función solo recibía el conjunto de
empresas, donde esa relación no cabe.

**Corregido**: el informe trae las estrategias por tabla, y la función distingue
la evidencia propia de la que llega por relación. Con una sola empresa,
`ASSIGN` si el dato es suyo y `DERIVE` si hubo que deducirlo — el dato resultante
es el mismo y la confianza no.

## Severidad preservada

| Clase | Severidad | Comprobación |
|---|---|---|
| `MC-D` | Sin evidencia, dominio **no** crítico | No absorbe a las demás: las cuatro conviven con recuento propio |
| `MC-E` | Sin evidencia **y** crítica | Emitida por la serie fiscal, con detalle |
| `INVALID_LEGACY_SCOPE` | Roto de antes, no incompleto | Emitida con detalle propio; **no** degradada a `MC-D` |
| `CROSS_TENANT` | Integridad rota entre clientes | Emitida con la explicación del cruce; **no** degradada a `MC-D` ni a `OK` |

La prueba `test_las_clases_criticas_no_se_confunden_entre_si` lo fija: si `MC-D`
hubiera absorbido a las otras tres, estarían en cero y `MC-D` inflado.

## Fixture Integrity

| | |
|---|---|
| Versionado en el repositorio | **Sí** — `qa/n4-legacy-hostile-seed.py` |
| Autocontenido | **Sí** — crea base, esquema y filas desde cero |
| Depende de una sesión temporal anterior | **No** |
| Aserciones de siembra | **Sí** — falla si `MC-D`, `INVALID`, `CROSS_TENANT` o los maestros no se crearon |
| Casos realmente sembrados | 8 clases + 4 estrategias |

La aserción de siembra existe por un motivo concreto: este proyecto ya vivió una
vez que el fixture estuviera vacío y las pruebas pasaran igual.

## Zero-write

| | Antes | Después |
|---|---|---|
| Conteos por tabla | idénticos | idénticos |
| `alembic_version` | `0032_mc_expand_tenant_scoped` | igual |
| Escrituras | — | **0** |

Doble garantía: el ejecutor solo emite `SELECT`, y la transacción se declara
`READ ONLY`, de modo que el motor rechazaría una escritura accidental. Confiar
solo en lo primero sería confiar en la disciplina del código.

## Repeatability

| | Corrida 1 | Corrida 2 |
|---|---|---|
| Clasificación por clase | idéntica | idéntica |
| Estrategias por tabla | idénticas | idénticas |
| Diferencias semánticas | — | **0** |

Se compara **por clase**, no por total: dos corridas que sumaran lo mismo con
clases distintas darían el mismo número y significarían cosas diferentes.

## Independencia del ORM final

El clasificador decide su conjunto de trabajo contra el catálogo del **destino**,
no contra el modelo de la versión que ejecuta el análisis. Se comprueba en el
mismo fixture: su esquema está en `0032` y el código vive en `0038`.
