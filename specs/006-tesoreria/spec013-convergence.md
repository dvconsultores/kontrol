# SPEC 013 · CONVERGENCIA

`SPEC 013 — COMPLETE / CONVERGED` (técnica y funcionalmente)

> 2026-09-11, sobre `f5ddc8d`. Ciclo completo desde `/speckit.specify`.
> Dueño: `specs/006-tesoreria`, compartido con la 038 y parcialmente con la 041.

## 1. La identidad del dueño, resuelta antes de tocar nada

La carpeta `specs/013-gap-analysis-roadmap-maestro` **no es** la Spec 013: es el
*gap analysis* del roadmap, de otra numeración. Es la misma colisión que ya se
resolvió con `004-compras ↔ Spec 028`, y el mapa de equivalencias la cierra sin
ambigüedad: **013 Maestros financieros ↔ `006-tesoreria`**.

## 2. Por qué tocaba ahora

La 038 dejó de inventar tasas. Al negarse a devolver `1,0` cuando faltaba una,
destapó una deuda que hasta entonces era teórica: **nadie registra tasas**. El
Máster ya lo anotaba —«013 · Tasa BCV depende de 048»— pero mientras el código
rellenaba el hueco solo, no se notaba. Al volverse honesto el sistema, se
convirtió en una parada operativa.

## 3. Lo que se encontró en lo que ya existía

Tres Specs seguidas encontraron el defecto grave en código ya escrito. Esta
encontró **siete**.

### 3.1 · El par no estaba escrito en ninguna parte · P0

`ExchangeRate` guardaba `currency_id` y `rate`. Contra qué moneda cotizaba lo
suponía el código, y lo suponía así:

```python
funcional = ("VED", "VES")
```

La moneda funcional escrita dentro del dominio de un producto que se vende como
parametrizable, cuando la empresa **ya la declara** en
`companies.functional_currency` y la política de la 038 también.

### 3.2 · Dos monedas con el mismo código · P0

Sin unicidad sobre `(company_id, code)`, dos «USD» podían convivir en una
empresa, y la resolución elegía con un `.first()` **sin orden declarado**. Si la
tasa se registró contra la otra, el resultado era «no hay tasa» teniéndola.

No era teórico: en la base de e2e había cuatro códigos duplicados el día que se
miró.

### 3.3 · Dos tasas del mismo día, y el desempate de PostgreSQL · P0

Sin unicidad de coordenadas, la consulta ordenaba por fecha y tomaba la primera.
Con dos filas de la misma fecha, la misma consulta podía devolver 40 o 60 según
el plan de ejecución.

### 3.4 y 3.5 · Inversión y triangulación silenciosas · P1 · **de la 038**

```python
if origen in funcional:
    return (Decimal(1) / inversa[0], inversa[1])
```

Una tasa USD→VED respondía VED→USD como `1/tasa`, y dos divisas se cruzaban por
la moneda funcional. Sin política que lo autorizara y sin que el resultado
dijera que era derivado —de modo que la instantánea apuntaba a la fila directa y
la reconstrucción histórica afirmaba «usó 40» cuando usó 0,025—.

**Las dos las introduje en el ciclo anterior.** La 038 corrigió que la tasa se
inventara y, al hacerlo, añadió dos formas nuevas de derivarla sin decirlo.

### 3.6 · Arrastre sin límite · P2

`rate_date <= día` sin tope: una tasa de 2020 valoraba una operación de 2026.
Arrastrar está bien —es lo que hay que hacer un domingo— pero sin política de
caducidad no se distingue «la del viernes» de «la del año pasado».

### 3.7 · La tasa viajaba como `float` por el borde · P1

`rate: float = Field(gt=0)` en la API y `Mapped[float]` en el modelo, sobre una
columna `Numeric(14, 6)` que siempre fue exacta. La anotación era la que mentía.
Y la pantalla lo agravaba desde el otro lado: `rate: Number(rate) || 0` convertía
un error de tecleo en un cero.

## 4. Un defecto que solo apareció de punta a punta

Preguntar «qué tasa rige hoy» resolvía a las **cero horas** de hoy. Una tasa
registrada esta mañana no servía para una operación fechada hoy, y el sistema
respondía que faltaba una tasa que estaba delante.

Lo encontró la prueba e2e, no las unitarias: éstas registraban y consultaban con
el mismo instante. Ahora una fecha **empieza** a regir a las cero y **se
consulta** hasta el final de su día, que son dos preguntas distintas.

## 5. Lo que se construyó

| | |
|---|---|
| Par canónico | `base` / `quote`, con la frase escrita: **1 base = `rate` quote** |
| Fuentes | maestro con autoridad declarada, prioridad, estado y salud del canal |
| Política de **resolución** | inversión, triangulación, caducidad, arrastre, aprobación y escala |
| Observación | versión, sucesión, tiempos, procedencia, lote y autor |
| Importación | CSV validado, idempotente por hash, con informe por fila |
| Contrato de proveedor | `ingest_provider_observations`, para que la 048 entregue ya normalizado |
| Resolución | `resolve_rate`, que devuelve procedencia entera o se niega |

Inversión y triangulación **nacen denegadas**. Derivar una tasa de otra es una
decisión económica, y el código no la toma solo; cuando la política la permite,
el resultado va marcado como derivado y la instantánea de la 038 lo guarda.

## 6. Lo que **no** se hizo, a propósito

- **No se implementó ningún proveedor automático del BCV.** No hay en el
  repositorio ni canal oficial estable verificable. Inventar un *scraping*
  frágil y llamarlo integración habría sido peor que el hueco: la operación vive
  de alta manual e importación, y el contrato de proveedor queda definido para
  cuando la 048 tenga de dónde tirar.
- **No se estrenó el outbox.** La tabla existe y ningún servicio la usa; ser el
  primer productor es alcance de otra Spec.
- **No se tocó el IGTF** (041), ni `PaymentMethod` ni `Bank` (038).
- **No se tocó la Spec 019 global —Recepción física—** pese a que un
  identificador histórico del máster diga «019» junto a una deuda de tesorería.

## 7. Puerta

| Criterio | Resultado |
|---|---|
| Un par sin tasa se resuelve igual | **no** — `MISSING_RATE` |
| Falta de tasa se confunde con tasa uno | **no** |
| La identidad crea una fila de mercado | **no** |
| Se invierte el par sin política | **no** |
| Se triangula sin política | **no** |
| Al derivar, el resultado lo oculta | **no** |
| Una tasa futura valora el pasado | **no** |
| Una tasa de hoy no sirve para hoy | **no** (defecto corregido) |
| El arrastre coge una tasa más vieja que la vigente | **no** |
| La caducidad está cableada | **no** — política |
| Corregir reescribe el histórico | **no** |
| Una operación pasada se revalúa | **no** |
| Dos monedas activas con el mismo código | **no** |
| Dos observaciones en las mismas coordenadas | **no** |
| Se acepta tasa cero o negativa | **no** |
| Reimportar duplica | **no** |
| Una fila inválida desaparece en silencio | **no** |
| Una fuente desactivada sigue resolviendo | **no** |
| Desactivar una fuente borra su historia | **no** |
| El desempate lo decide el orden de la tabla | **no** — prioridad del maestro |
| Quien registra una tasa puede aprobarla | **no** |
| Una empresa ve o usa lo de otra | **no** |
| `float` en la tasa | **0** |
| Reglas legales venezolanas en el código | **0** |
| Llamadas a servicios externos desde el dominio | **0** |
| Permisos nuevos inventados | **0** |

## 8. Lo que se midió, no se supuso

Doce mutaciones. Once fallan donde deben:

| | Mutación | Qué rompe |
|---|---|---|
| M013-01 | falta de tasa devuelve uno | 7 pruebas |
| M013-02b | el contrato devuelve `float` | 13 |
| M013-03 | se ignora la fecha de vigencia | 3 |
| M013-04 | corregir reescribe en vez de suceder | 1 |
| M013-05 | se quita la guardia de empresa del maestro | 1 |
| M013-06 | se admite tasa cero | 2 |
| M013-07 | se admite tasa negativa | 4 |
| M013-08 | reimportar el mismo lote duplica | 1 |
| M013-09 | el arrastre coge la más antigua | 1 |
| M013-10 | se invierte el par en silencio | 1 |
| M013-11 | se triangula en silencio | 3 |
| M013-12 | una fuente desactivada sigue resolviendo | 2 |

**M013-02 tal como estaba enunciada —«convertir la tasa a `float`»— no puede
fallar, y se midió antes de afirmarlo.** Sobre `Numeric(14, 6)`, el viaje
`Decimal → float → str → Decimal` es exacto: 400 000 divisiones aleatorias
cuantizadas a seis decimales no dieron **ni una** diferencia entre el cálculo
exacto y el binario, ni siquiera subiendo la escala a doce. La familia `KQA-100`
muerde en la **resta de magnitudes parecidas**, que es lo que hace el arqueo de
caja —deuda de la 038— y no lo que hace este módulo.

En su lugar se ejerce **M013-02b**, que sí muerde: devolver la tasa como `float`
rompe trece pruebas. No se maquilló una mutación para que pareciera verde.

Dos mutaciones no fallaban al primer intento y **eso era un hueco de las
pruebas, no de la mutación**: M013-05 estaba tapada por una segunda guardia y
M013-09 no tenía quien distinguiera «la más reciente anterior» de «la más
antigua». Se escribieron las dos pruebas que faltaban.

## 9. Evidencia

> Instantánea del cierre del 2026-09-11, conservada tal cual. Las cifras
> definitivas —con la familia de carreras corregida, la deriva de la 013 en
> cero y la regresión final— están en §9-bis.

| Puerta | Resultado |
|---|---|
| `test_spec013_financial_masters.py` | **44 pruebas** al cierre del 2026-09-11 · **55** tras la reanudación (§9-bis) |
| Suites 013 + 038 | 77 al cierre del 2026-09-11 · ver §9-bis |
| Mutaciones | 11 muerden · 1 medida como no detectable |
| Concurrencia real sobre PostgreSQL | dos hilos, una sola fila |
| Volumen | 237 observaciones recorridas por páginas |
| Frontend | vitest **307/307** · `tsc`, ESLint, Ruff y build limpios |
| Puertas de completitud | **235 → 239** (4 nuevas por las dos pantallas) |
| E2E de la 013 | **39/39** en Chromium, Firefox y WebKit |
| Cadena operativa e2e | **243/243** en los tres navegadores |
| Migración `0056` | sube, baja y vuelve a subir limpia |
| Trazabilidad | **100 %**, 49 requisitos + 3 de delta, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

### 9.1 · Un intermitente, clasificado con evidencia

La primera corrida de la cadena dejó en rojo la prueba de interfaz del despacho,
en Firefox: el aviso «Mercancía despachada» no llegó en quince segundos con diez
suites en paralelo. Aislada, pasa **8/8**. Repetida la cadena entera, pasa
**243/243**. Clasificación: `EXTERNAL_ENVIRONMENT` —contención—, no regresión.
Es la misma prueba y el mismo síntoma que la 037 ya clasificó, y en una Spec que
este ciclo no toca. No se dio por buena diciendo «ya pasó antes»: se aisló, se
repitió y se comparó.

## 9-bis. Reanudación del 2026-09-13 · lo que apareció al instalar de cero

La sesión se interrumpió con la regresión final sin terminar, y el entorno de QA
desapareció entero. Reconstruirlo obligó a **instalar la base de e2e de cero**, y
esa instalación limpia —el primer día de un cliente real— encontró lo que ninguna
corrida sobre una base con meses de datos podía ver. Detalle completo en
`spec013-clarifications.md` §7.

### Una familia entera de 500 · buscar y crear no es atómico

Dos transacciones pasan la búsqueda, la segunda choca en el índice único, y como
**no hay manejador global de `IntegrityError`**, la colisión sale como 500.

- **023** · `_get_movement_type_by_code`: 500 en `recoger` al preparar a la vez en
  una empresa nueva. Delta dirigido, registrado en su convergencia.
- **013** · cinco sitios **míos, de este ciclo**: moneda funcional, alta de fuente
  (y los dos caminos cortos que la llaman), registro de tasa, importación y
  versión de política. Y uno sin concurrencia: corregir dos veces la misma tasa
  original chocaba siempre.

La prueba de concurrencia de la 013 **aceptaba `IntegrityError` como rechazo
válido**. En el servicio lo parece; por la API es un 500. Se sustituyó por
carreras **forzadas** (`tests/concurrency.py`): la segunda transacción queda
bloqueada en el índice antes de que la primera confirme, y si nunca llega a
bloquearse la prueba falla.

### La unicidad de la 013 vivía solo en la migración

Los modelos no declaraban ninguno de los cinco índices únicos ni el `CHECK` de la
`0056`. La base de pruebas se construye desde los modelos: **ninguna prueba
unitaria ejerció nunca esa unicidad**. La primera carrera forzada insertó dos
veces lo que en producción el índice habría rechazado. Ahora se declaran en el
ORM con los mismos nombres, y dos guardias impiden que vuelvan a separarse.

`alembic check` sobre la base migrada: **27 operaciones de deriva antes, 21
después, ninguna en la 013.** Las 21 son anteriores (§11).

### Defectos de prueba en otras dueñas, corregidos en su sitio

| Prueba | Dueña | Defecto | Arreglo |
|---|---|---|---|
| `ENTRADA_RECEPCION` en 9 ficheros e2e | 022 · 031 · 032 · 033 · 034 · 035 · 036 · 037 · 038 | buscar-y-crear el tipo con carrera: 409 legítimo tomado por fallo | releer tras `MOVEMENT_TYPE_DUPLICATE`; cualquier otro error sí rompe |
| posición de caja | 038 | medía la diferencia de bolívares **de toda la empresa** mientras otras pruebas los movían: 540 = 100 propios + 440 ajenos | saldo de **sus** cuentas; agregado solo en su divisa propia |
| confirmación de pedido | 033 | `isDisabled()` sobre un paginador que no existe cuando la cola cabe en una página: falló **también aislada**, 2 de 3 | el mismo arreglo que ya llevaban `billing` y `dispatch` |

El rojo de la 033 **no** se clasificó como `EXTERNAL_ENVIRONMENT`: falló solo, así
que el defecto era de la prueba. Tras el arreglo, 5/5 aislada en Firefox y 21/21
en los tres navegadores.

### Mutaciones de la reanudación

Las once caen, cada una con la firma exacta que la prueba debe ver:

| | Mutación | Qué rompe |
|---|---|---|
| M013-13 | registrar sin capturar la colisión | la carrera recibe `IntegrityError` |
| M013-14 | alta de fuente sin capturar | ídem |
| M013-15 | el camino corto no relee a la ganadora | devuelve `SOURCE_CODE_TAKEN` en vez de la fuente |
| M013-16 | moneda funcional sin capturar | `IntegrityError` |
| M013-17 | importación sin capturar | `IntegrityError` |
| M013-18 | versión de política sin capturar | `IntegrityError` |
| M013-19 | corregir sin mirar si ya fue sustituida | `IntegrityError` sin concurrencia |
| M013-20 | corrección concurrente sin capturar | `IntegrityError` |
| M013-21 | la unicidad vuelve a vivir solo en la migración | la guardia de deriva |
| M013-21b | la misma deriva, vista desde la carrera | «la segunda transacción nunca chocó» |
| M023-D1 | tipo de movimiento sin capturar | `IntegrityError` en la carrera |

Las primeras ejecuciones no dieron resultado legible: con `-q` más el
`addopts = "-q"` del proyecto, pytest suprime el resumen. Se repitieron leyendo
el **código de salida**, que no depende de la verbosidad. Una mutación sin
resultado no se contó.

### Evidencia de la reanudación

| Puerta | Resultado |
|---|---|
| `test_spec013_financial_masters.py` | **55** casos |
| `test_spec023_movement_type_race.py` | **2** |
| Carreras, deriva y suites de 013 · 023 · 038 · tesorería · inventario · picking | **184/184** |
| Modelos ↔ migración en la 013 | **idénticos**, restricción a restricción |
| Frontend | vitest **307/307** · `tsc`, ESLint y build limpios |
| Base de e2e instalada de cero, cadena de diez suites | **243/243** en Chromium, Firefox y WebKit |
| Trazas en el backend durante esa cadena | **0** |
| Tipos de movimiento tras la cadena | 12 creados · **0 repetidos** |
| Regresión completa del backend | **1401** · **1393 pasan · 8 saltos · 0 fallos · 0 errores** · `EXIT=0` |
| Saltos esperados / reales | **8 / 8**, todos S3 en `test_documents_storage.py` |

## 9-ter. Cierre formal · 2026-09-13

Revalidación completa antes de sostener el veredicto. Detalle en
`spec013-clarifications.md` §8.

### Lo que la revalidación encontró

- **Las capturas de carrera traducían cualquier `IntegrityError`** —también un
  `CHECK` o una clave foránea— a conflicto de dominio.
  `NEW_REGRESSION_CURRENT_DELTA`, corregido con `app/core/integrity.py` y
  defendido por dos pruebas con errores reales de PostgreSQL.
- **Los sitios de carrera son 9 funciones, 10 protecciones y 6 restricciones**,
  no «ocho sitios».
- **Las doce mutaciones de la primera pasada nunca se habían repetido contra el
  código final.** Un primer intento terminó con código 4 (argumentos mal pasados)
  y no se contó. Repetidas bien, M013-08 sobrevive y se sustituye.
- CORRECTION-013-04 (diez Specs con deriva heredada, no doce) y CORRECTION-013-05
  (el «019» salió de los documentos de la 038, no del máster).

### Mutaciones sobre el código final

Ejecutadas en serie, leyendo el código de salida de pytest, con las fuentes
restauradas byte a byte después de cada una.

| | Mutación | Resultado | Motivo observado |
|---|---|---|---|
| M013-01 | falta de tasa devuelve uno | cae · 4 | no se lanza `ConflictError` |
| M013-02b | el contrato devuelve `float` | cae · 3 | `0.3 ≠ Decimal` |
| M013-03 | se ignora la fecha de vigencia | cae · 3 | usó una tasa futura |
| M013-04 | corregir reescribe | cae · 1 | la original sigue `ACTIVE` |
| M013-05 | sin guardia de empresa del maestro | cae · 1 | `MISSING_RATE` en vez de `CURRENCY_INACTIVE` |
| M013-06 | se admite tasa cero | cae · 2 | `CheckViolation` de la base |
| M013-07 | se admite tasa negativa | cae · 3 | `CheckViolation` de la base |
| M013-08b | la huella no identifica el fichero | cae · 2 | no se detecta la reimportación |
| M013-09 | el arrastre coge la más antigua | cae · 1 | tasa más vieja que la vigente |
| M013-10 | invertir en silencio | cae · 1 | no se lanza `INVERSION_NOT_ALLOWED` |
| M013-11 | triangular en silencio | cae · 1 | no se lanza `MISSING_RATE` |
| M013-12 | fuente desactivada resuelve | cae · 1 | no se lanza `MISSING_RATE` |
| M013-13 | registrar sin capturar | cae · 1 | `IntegrityError` a quien pierde |
| M013-14 | alta de fuente sin capturar | cae · 1 | ídem |
| M013-15 | el camino corto no relee | cae · 1 | `SOURCE_CODE_TAKEN` en vez de la fuente |
| M013-16 | moneda funcional sin capturar | cae · 1 | `IntegrityError` |
| M013-17 | importación sin capturar | cae · 1 | ídem |
| M013-18 | versión de política sin capturar | cae · 1 | ídem |
| M013-19 | corregir sin mirar el estado | cae · 1 | `UniqueViolation` sin concurrencia |
| M013-20 | corrección concurrente sin capturar | cae · 1 | `IntegrityError` |
| M013-21 | unicidad solo en la migración | cae · 1 | la guardia de paridad |
| M013-21b | la misma deriva, desde la carrera | cae · 1 | «la segunda transacción nunca chocó» |
| M013-22 | el clasificador todo lo toma por colisión | cae · 2 | `assert not True` |
| M013-23 | el clasificador ignora la restricción | cae · 1 | ídem |
| M023-D1 | tipo de movimiento sin capturar | cae · 1 | `IntegrityError` a quien pierde |
| M013-24 | el alta de fuente pierde la prioridad | cae · 1 | «la respuesta del alta perdió `priority`» |

**26 mutaciones válidas, las 26 caen.** Dos no válidas en todo el ciclo, ambas
sustituidas: **M013-02** (sin diferencia observable a esta escala) y **M013-08**
(compensada por el índice). M013-21 y M013-21b son un mismo defecto visto por dos
detectores. M023-D1 pertenece al delta de la 023, no a la 013.

La cifra «23» que se dio antes era anterior al estrechamiento y contaba a M013-08,
que ya no es válida.
M013-24 se añadió con la prueba de FR-013-004, que la verificación de
trazabilidad encontró sin cubrir.

### Evidencia del cierre formal

| Puerta | Comando | Resultado |
|---|---|---|
| Regresión completa del backend | `pytest -p no:cacheprovider -rs` | `EXIT=0` · **1403** · **1395 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | — | **8 / 8**, todos S3 en `test_documents_storage.py` · fuera de S3: **0** |
| Frontend | `tsc --noEmit` · `eslint src e2e` · `vitest run` · `npm run build` | exit 0 · exit 0 · **307/307** exit 0 · exit 0 |
| Ruff | `ruff check app tests alembic` | exit 0 |
| Migraciones sobre base nueva | `alembic upgrade head` | exit 0 · 56 migraciones |
| Tipos de movimiento tras la cadena | consulta directa | 12 · **0 repetidos** |
| Trazas y 5xx del backend en la cadena | registro de uvicorn | **0** · **0** |

La regresión cubre las dos pruebas nuevas del clasificador (1401 → 1403). **No**
incluye la prueba de FR-013-004, añadida después; su evidencia es dirigida y la
regresión completa de la Spec 004 la cubre.

### E2E sobre base instalada de cero

| Cadena | Condición | Resultado |
|---|---|---|
| Primera | `ke2e` recién migrada, **con la regresión completa corriendo en paralelo** | **242/243** · Chromium 81 · Firefox 80 · WebKit 81 · 0 trazas · 0 5xx · 12 tipos de movimiento, 0 repetidos |
| Segunda | misma base, **sin la regresión en paralelo** | **243/243** · 81 por navegador · 0 trazas · 0 5xx |

El único rojo —`picking.spec.ts · el pedido liberado aparece en la cola con su
puesto`, en Firefox— no llegó a ejercer ninguna regla: el primer
`POST /auth/login` recibió `read ECONNRESET`. El servidor arrancó una sola vez,
no se reinició, no registró advertencias, errores ni respuestas 5xx. Aislada,
la prueba pasó **3 de 3**; la suite 031 completa en Firefox, **8/8**; la cadena
entera sin la regresión en paralelo, **243/243**.

Clasificación: **`EXTERNAL_ENVIRONMENT`** — reinicio de conexión en transporte con
un uvicorn de un solo proceso atendiendo tres navegadores mientras corría la
regresión completa. No se dio por buena por haber pasado antes: se aisló, se
repitió y se comparó con la cadena sin carga.

### Pruebas dirigidas tras añadir FR-013-004

`test_spec013_financial_masters.py` + `test_spec023_movement_type_race.py`:
**60/60**, Ruff limpio.

### `/speckit.analyze` final

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 — las cifras intermedias contradictorias quedan corregidas por errata, no borradas |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRACEABILITY | 100 % |

## 10. Las separaciones que hay que conservar

**Maestro ≠ operación.** La 013 dice cuánto vale una moneda; la 038 mueve el
dinero y congela la tasa que usó. `resolve_rate` es de la 013; el `RateSnapshot`
es de la 038.

**Dominio ≠ integración.** La 013 no llama a nadie. El adaptador externo, el
transporte, las credenciales y la programación son de la 048.

**Certificación técnica ≠ homologación legal.** `D0-07` sigue **abierto**. Que
el BCV pueda configurarse como fuente oficial no es una afirmación legal: es una
fila del maestro con su referencia de autoridad declarada, y la referencia dice
lo que es.

## 11. Deuda anotada, no absorbida

| Hallazgo | Dueña |
|---|---|
| `BankTransactionCreate.amount: float` en el borde de la API | **038** |
| Arqueo de caja con `round(float(a) − float(b), 6)` | **038** |
| Proveedor automático de tasas (BCV u otro) | **048**, cuando exista canal usable |
| Notificar «tasa pendiente de aprobación» o «sincronización fallida» | **047**, `NOT_STARTED` |

| Deriva ORM ↔ migración heredada: **21** operaciones de `alembic check` | ver abajo |
| `get_or_create_installation` busca-y-crea sin capturar la carrera | **004** — no se toca licenciamiento |

La deriva heredada, por tabla y módulo dueño:

| Módulo | Tablas | Operaciones |
|---|---|---|
| `master_data` | `parties`, `customers`, `suppliers`, `carriers`, `drivers`, `products`, `services`, `attribute_applicabilities` | 8 |
| `sales` | `pick_list_lines` (2), `sales_order_lines`, `sales_quote_lines` | 4 |
| `inventory` | `inventory_balances`, `inventory_movements` | 2 |
| `audit` | `audit_events` | 2 |
| `homologation` | `release_versions` | 2 |
| `licensing` | `license_states` | 1 |
| `purchasing` | `receipt_confirmations` | 1 |
| `treasury` (IGTF) | `fiscal_rules` | 1 |

No se absorben: son de doce Specs distintas y cada una necesita decidir si manda
el modelo o la migración. **No se afirma deriva cero del esquema.**

Ninguna de ellas consume el contrato de tasas, así que ninguna bloqueó este
ciclo. El identificador histórico «019» del máster **no** es la Spec 019 global
—Recepción física—, que no se ha tocado.

## 12. Estado resultante

| | |
|---|---|
| Spec 013 | **COMPLETE / CONVERGED** (técnica y funcional) |
| Spec 038 | con sus dos deltas dirigidos convergidos: instantánea con derivación, y camino corto con par |
| Spec 007 | con su delta: la empresa publica su moneda funcional |
| Spec 023 | con su delta: el alta automática del tipo de movimiento base ya no da 500 en carrera |
| Spec 037 · 033 | con la errata de evidencia registrada (`EVIDENCE_CORRECTION`); la 033, además, con su prueba de interfaz corregida |

## 13. Anexo posterior al cierre · un rojo intermitente de las propias pruebas — 2026-09-13

La regresión completa corrida para el delta de la Spec 004 terminó con **un
fallo**: `test_sin_politica_no_se_triangula`, con `DUPLICATE_OBSERVATION` al
registrar la segunda tasa. No es de la 004 ni del producto.

**Causa.** `_codigo()` generaba `Z` + **dos** caracteres hexadecimales: 256 códigos
posibles. La prueba pide dos monedas; si los dos sorteos coinciden —1 de cada 256
por prueba, y varias pruebas del fichero sortean dos—, `_moneda` reutiliza la misma
moneda y la segunda tasa repite par, fuente y fecha. Por eso pasó en las ejecuciones
anteriores y no en ésta.

**Demostración.** Forzando que `_codigo()` devuelva el mismo valor dos veces, la
prueba falla **siempre** con ese mismo error. El mecanismo no es una suposición.

**Misma familia.** `_divisa()` en `test_spec038_treasury.py` y un código `Q…`
suelto del mismo fichero usaban también dos caracteres.

**Corrección.** Los tres pasan a **cinco** caracteres hexadecimales (1 048 576
valores; 6 caracteres con el prefijo, dentro del límite de 8 de las columnas de
moneda y del borde de la API). Los auxiliares e2e usan tres caracteres en base 36
(46 656 valores), no han fallado y no se tocan; quedan anotados como la misma
familia.

Clasificación: **`TEST_DEFECT`**. La regresión se repite completa con el arreglo.

