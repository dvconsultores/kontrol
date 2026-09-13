# SPEC 013 · MAESTROS FINANCIEROS — CLARIFICACIONES

> Investigación contra el repositorio en `f5ddc8d`. Ningún dato procede de un
> informe anterior: los informes son entrada, el repositorio es la evidencia.

## 0. Identidad del dueño — resuelta antes de tocar nada

La carpeta `specs/013-gap-analysis-roadmap-maestro` **no es** la Spec 013. Es el
*gap analysis* del roadmap, otra numeración. Es la misma colisión que ya se
resolvió con `004-compras ↔ Spec 028`.

`spec-equivalence-map.md` línea 20:

> | 013 Maestros financieros | `006-tesoreria` | 85 % | — |

y línea 74:

> | `006-tesoreria` | 013, 038, 041(parc.) | M | KEEP | — |

**Dueño canónico: `specs/006-tesoreria`**, compartida con la 038 y parcialmente
con la 041. Los artefactos de este ciclo llevan prefijo `spec013-`, como los de
la 038 llevan `spec038-`.

## 1. Lo que ya existe

| Punto | Hallazgo |
|---|---|
| Modelo de moneda | `Currency` en `treasury/models.py`: `code`, `name`, `symbol`, `decimal_places`, `status`. Ámbito **empresa** |
| Precisión de importe | `Currency.decimal_places`, por defecto 2. **Existe autoridad** |
| Modelo de tasa | `ExchangeRate`: `currency_id`, `rate_date` (Date), `rate` `Numeric(14,6)`, `source` texto libre |
| Fuente de tasa | **No existe maestro.** `source` es `String(120)` sin catálogo |
| Tipo de tasa | **No existe** |
| Servicio de resolución | `_buscar_tasa` en `treasury/service.py` (lo escribió la 038) |
| Contrato con la 038 | `capture_rate_snapshot` → `TreasuryRateSnapshot.exchange_rate_id` FK a `exchange_rates` |
| Alta manual en interfaz | Una pestaña dentro de `MaestrosPage`: lista de monedas y una casilla de tasa |
| Importación | **No existe** |
| Proveedor externo | **No existe.** No hay módulo `integrations`; la 048 vive en `010-licenciamiento-central` |
| Planificador | **No existe** |
| `FinancialInstitution` | **No existe** con ese nombre. Lo más próximo es `Bank`, de tesorería |
| `PaymentMethod` | En `treasury/models.py`, ámbito empresa. **Dueña: 038**, no se toca |
| Aprobaciones | Spec 045, `COMPLETE / CONVERGED`. No hay motor local |
| Contexto de petición | `CompanyContext` + `get_company_context`, ya usado por las 12 rutas de la 038 |
| Catálogo de permisos | `setup/api.py`: `tesoreria: [view, create, approve]`, `maestros: [view, create, edit, deactivate]` |
| Catálogo de errores | Sin registro enumerado: `KontrolError(code=...)` en el sitio de lanzamiento |
| Outbox | La tabla `outbox_events` existe y **ningún servicio la usa**. Estrenarla aquí sería alcance ajeno |
| Notificaciones | Spec 047 `NOT_STARTED`. No hay a quién delegar |
| Consumidores de `currencies` | `exchange_rates`, `price_lists` (Spec 012) |

## 2. Los seis defectos que la investigación encontró en lo ya construido

Tres Specs seguidas encontraron el defecto grave **en código que ya existía**.
Esta no es la excepción.

### 2.1 · `currencies` no tiene unicidad de código · **P0**

No hay índice único sobre `(company_id, code)`. Dos monedas «USD» pueden
convivir en la misma empresa, y `_buscar_tasa` resuelve el código con
`.first()` **sin orden declarado**: elige una de las dos al azar.

Si la tasa se registró contra la otra, el resultado es `MISSING_RATE` teniendo
la tasa registrada. Y si ambas tienen tasa, el sistema devuelve una u otra sin
criterio.

No es teórico. En la base `ke2e`, hoy:

```
 code | count
------+-------
 QMT  |     2
 RMT  |     2
 TMT  |     2
 SMT  |     2
```

### 2.2 · `exchange_rates` no tiene unicidad ni desempate · **P0**

Sin restricción sobre `(company, moneda, fecha, fuente, tipo)`. Dos tasas del
mismo día conviven, y la resolución hace `ORDER BY rate_date DESC LIMIT 1`: con
dos filas de la misma fecha **el desempate lo decide PostgreSQL**. La misma
consulta puede devolver 40 o 60 según el plan.

### 2.3 · Venezuela cableada en el dominio · **P1**

```python
funcional = ("VED", "VES")
```

La moneda funcional está escrita en el servicio de resolución, cuando la empresa
la declara (`companies.functional_currency`) y la política de la 038 también
(`TreasuryFxPolicy.functional_currency`). Ninguna de las dos se consulta.

### 2.4 · Inversión silenciosa · **P1** · introducida por la Spec 038

```python
if origen in funcional:
    inversa = registrada(destino)
    return (Decimal(1) / inversa[0], inversa[1])
```

Una tasa USD→VED se usa para responder VED→USD como `1/tasa`, sin política que
lo autorice y sin que el resultado diga que es **derivado**. La instantánea que
la 038 guarda apunta a la fila directa, de modo que la reconstrucción histórica
dice «esta operación usó la tasa 40» cuando usó 0,025.

### 2.5 · Triangulación silenciosa · **P1** · introducida por la Spec 038

```python
a, b = registrada(origen), registrada(destino)
```

Divisa a divisa se resuelve pasando por la moneda funcional. Es una estrategia
económica —cruzar dos cotizaciones— tomada por el código, sin autoridad y sin
dejar rastro de que se cruzó.

**Ambas son mías, del ciclo anterior.** La 038 corrigió que la tasa se inventara
y, al hacerlo, añadió dos formas nuevas de derivarla sin decirlo.

### 2.6 · Arrastre sin límite · **P2**

`rate_date <= día ORDER BY rate_date DESC` arrastra la última tasa anterior sin
tope: una tasa de 2020 valora una operación de 2026 sin que nada avise. El
arrastre en sí es razonable —y es lo que hay que hacer un domingo—, pero sin
política de caducidad no se distingue «la de ayer» de «la del año pasado».

### 2.7 · La tasa viaja como `float` por el borde de la API · **P1**

```python
class ExchangeRateCreate(BaseModel):
    rate: float = Field(gt=0)
```

y `def set_exchange_rate(..., rate: float, ...)`, y en el modelo
`rate: Mapped[float] = mapped_column(Numeric(14, 6))`: la columna es exacta y la
anotación miente. Es la familia `KQA-100` en el borde que **sí** es de la 013.

La pantalla actual agrava lo mismo desde el otro lado:

```tsx
body: { ..., rate: Number(rate) || 0 }
```

Un valor no numérico se convierte en **cero** antes de salir del navegador. Hoy
lo salva que el servicio rechaza `rate <= 0` con `INVALID_RATE`, pero lo que
llega al usuario es un 422 sin campo señalado, no «eso no es un número».

## 3. Preguntas que **no** se reabren

**«¿Qué pasa si no hay tasa?»** Decidido y cerrado en la 038: entre monedas
distintas, `RATE_NOT_AVAILABLE`. Nunca `1,0`. Este ciclo lo refuerza, no lo
revisa.

## 4. Preguntas resueltas con autoridad existente — **ninguna material**

| # | Pregunta | Resuelta por |
|---|---|---|
| 1 | ¿Qué par representa una fila de `exchange_rates` ya existente? | El propio docstring: «las tasas se guardan contra la moneda funcional: divisa → bolívar», y `companies.functional_currency` lo declara por empresa. Base = la moneda de la fila; cotizada = la funcional de su empresa |
| 2 | ¿Se permite invertir? | `FR-013-034`: no automáticamente, **salvo política**. La política no existía, así que nace **denegando**, y ninguna prueba ni pantalla depende hoy de una inversión |
| 3 | ¿Se permite triangular? | `FR-013-035`, igual. Nace denegando |
| 4 | ¿Cuál es el umbral de caducidad? | `FR-013-021` pide **permitir** la política, no fijar un número. Sin política configurada no hay tope, que es el comportamiento de hoy |
| 5 | ¿Arrastre en día no hábil? | Ya está implementado de hecho (`rate_date <= día`). No se inventa: se hace explícito y configurable |
| 6 | ¿La tasa manual exige aprobación? | Spec 045 existe. Se ofrece por política, apagada por defecto: encenderla no es de este ciclo |
| 7 | ¿Precisión de la tasa? | `Numeric(14,6)` es lo que hay. La escala pasa a ser del maestro de la fuente/tipo, con 6 como valor heredado declarado, no cableado |
| 8 | ¿Permisos nuevos? | No. `tesoreria: view/create/approve` cubre consultar, registrar/importar y aprobar. Importar **es** crear |
| 9 | ¿Institución financiera? | `Bank` ya existe y es de tesorería (038). No se duplica ni se traslada |
| 10 | ¿Proveedor externo del BCV? | No hay canal oficial estable verificable en el repositorio. `§37`: no se inventa *scraping*. Queda el contrato de proveedor definido y **sin implementar**, y la operación vive de alta manual e importación |

**Conclusión: 0 preguntas materiales nuevas.** El ciclo continúa.

## 5. Frontera con las Specs vecinas

| Capacidad | Dueña |
|---|---|
| Monedas, fuentes, tipos, observaciones, histórico, importación, **resolución** | **013** |
| Cuentas, movimientos, conversión FX, `RateSnapshot` de una operación, conciliación, posición | 038 |
| Adaptador externo, transporte, credenciales, programación de sincronización | 048 |
| Aprobación y segregación | 045 |
| IGTF | 041 |
| Permisos y roles | 003 |

`_buscar_tasa` vive hoy en `treasury/service.py` y es **resolución**: pasa a ser
de la 013. `capture_rate_snapshot` es **operación**: sigue siendo de la 038 y
consume el contrato nuevo.

## 6. Deudas ajenas, localizadas y no absorbidas

| Deuda | Código | Dueña |
|---|---|---|
| `BankTransactionCreate.amount: float` | `treasury/api.py` | **038** — es su borde, no el de la 013. El identificador histórico «019» del máster corresponde a **Recepción física**, que no tiene nada que ver: no se toca |
| Arqueo con `round(float(a) - float(b), 6)` | `treasury/service.py::arqueo_session` | **038**, misma razón |

Ninguna de las dos es consumidora del contrato de tasas, así que **no bloquean
este ciclo**. Quedan anotadas con dueña resuelta, no con `OWNER_IDENTITY_CONFLICT_DEBT`.

## 7. Anexo de la reanudación — 2026-09-13

La sesión se interrumpió con la regresión final sin terminar. Al volver, el
entorno de QA había desaparecido entero —PostgreSQL, ClamAV, la base legada y
todas las utilidades temporales— y se reconstruyó desde `qa/pg-provision.sh`, las
semillas de `qa/` y la receta del ciclo. El árbol de trabajo estaba intacto.

Reconstruir obligó a **instalar la base de e2e de cero**, y eso destapó una
familia de defectos que ningún ciclo anterior había podido ver, porque todos
corrían sobre una base con meses de datos.

### 7.1 · Buscar y crear no es atómico · familia completa

El patrón «busco la fila; si no está, la inserto» sobre una tabla con índice
único deja una ventana: dos transacciones pasan la búsqueda y la segunda choca en
el índice. **No existe manejador global de `IntegrityError`**, así que esa
colisión sale por el `exception_handler(Exception)` como **500**.

| Sitio | Dueña | Síntoma |
|---|---|---|
| `_get_movement_type_by_code` | 023 | 500 en `recoger` al preparar dos pedidos a la vez en una empresa nueva |
| `asegurar_moneda_funcional` | **013** | 500 al registrar dos tasas a la vez en una empresa nueva |
| `create_source` | **013** | 500 en vez de `SOURCE_CODE_TAKEN` |
| `fuente_por_texto` · `fuente_por_omision` | **013** | el camino corto fallaba en vez de devolver la fuente que creó el otro |
| `register_rate` | **013** | 500 en vez de `DUPLICATE_OBSERVATION` |
| `import_rates` | **013** | 500 en vez de `IMPORT_DUPLICATE` |
| `create_policy` | **013** | 500 al calcular dos veces «la mayor versión más uno» |
| `correct_rate` | **013** | 500 **sin concurrencia**: corregir dos veces la misma original creaba una segunda «versión siguiente» |

Cinco de los ocho sitios son míos, escritos en este mismo ciclo. La prueba de
concurrencia que los debía cubrir **aceptaba `IntegrityError` como rechazo
válido**: a nivel de servicio lo parece; por la API es un 500.

Todos se corrigen con el idioma que el repositorio ya usa en aprobaciones y en el
saldo de inventario —`begin_nested()` + `IntegrityError`—, traduciendo la
colisión al mismo error de dominio que habría recibido quien llegara tarde, o
releyendo a la ganadora cuando la operación es un «asegurar».

### 7.2 · La unicidad de la 013 vivía solo en la migración

La `0056` crea cinco índices únicos y un `CHECK`; los modelos no declaraban
**ninguno**. La base de pruebas se construye con `create_all` desde los modelos,
así que ninguna prueba unitaria ejerció nunca esa unicidad. Lo reveló la primera
carrera forzada: la segunda transacción **insertó con éxito** lo que en
producción el índice habría rechazado.

`alembic check` sobre la base migrada, medido antes y después:

| | Operaciones de deriva |
|---|---|
| Antes | **27** |
| Después | **21** — ninguna en tablas de la 013 |

Las 21 restantes son **anteriores** a este ciclo y se registran como deuda con
dueño en la convergencia. **No se afirma deriva cero** del esquema: se afirma
cero en la 013.

### 7.3 · Tres afirmaciones intermedias que hubo que corregir

Se dejan escritas porque cambiaban conclusiones:

1. Una consulta a la base de pruebas mostró «cero restricciones» y se tomó por
   prueba de la deriva. Estaba vacía por otro motivo: el *fixture* destruye el
   esquema al terminar. La deriva se probó después como corresponde, construyendo
   el esquema desde los modelos en una base aparte.
2. Se llamó defecto al nombre `ck_exchange_rates_ck_exchange_rates_rate_positive`.
   No lo es: la convención `ck_%(table_name)s_%(constraint_name)s` produce el
   mismo nombre en el ORM y en Alembic, igual que en la 038 y en migraciones
   anteriores.
3. Se contaron 54 operaciones de deriva. Alembic imprime la misma lista dos veces
   —en la línea `ERROR` y en la `FAILED`—; eran **27**.

### 7.4 · Preguntas materiales nuevas

**Ninguna.** Todo lo anterior tiene autoridad en el propio repositorio: el
índice único existía, el idioma de captura existía, y el contrato de errores de
dominio también.

## 8. Anexo del cierre formal — 2026-09-13

Revalidación de toda la evidencia antes de declarar el cierre, a partir de los
registros que sobrevivieron y volviendo a ejecutar lo que no tenía código de
salida registrado.

### 8.1 · Entorno

| | |
|---|---|
| PostgreSQL ejecutado | **16.2** (`pgserver`) — objetivo histórico 18.6 → **`ENVIRONMENT_BASELINE_DEVIATION`** |
| Reconstrucción | PostgreSQL, ClamAV 1.4.3 (firma EICAR de prueba), bases `kmc`, `ke2e` y `kontrol_legacy`, semilla hostil del legado, backend y Vite, todo desde `qa/pg-provision.sh`, `qa/n4-legacy-hostile-seed.py` y `qa/pg-e2e-seed.py` |
| Base de e2e | reinstalada **de cero a la cabeza** (56 migraciones) antes de cada cadena de evidencia |

### 8.2 · Los sitios de carrera, contados desde el código

El «ocho» de la §7.1 contaba **filas de tabla**, y una fila agrupaba dos
funciones. Contado sobre el código final:

| Dueña | Función | Restricción | Protección |
|---|---|---|---|
| 013 | `asegurar_moneda_funcional` | `uq_currencies_company_code_active` | captura + relectura |
| 013 | `create_source` | `uq_rate_sources_company_code` | captura → `SOURCE_CODE_TAKEN` |
| 013 | `fuente_por_texto` | ídem | relectura de la ganadora |
| 013 | `fuente_por_omision` | ídem | relectura de la ganadora |
| 013 | `create_policy` | `uq_rate_policies_company_code_version` | captura → `RATE_POLICY_VERSION_CONFLICT` |
| 013 | `register_rate` | `uq_exchange_rates_observation` | captura → `DUPLICATE_OBSERVATION` |
| 013 | `correct_rate` | ídem | guarda de estado **y** captura → `RATE_ALREADY_SUPERSEDED` |
| 013 | `import_rates` | `uq_rate_import_company_hash` | captura → `IMPORT_DUPLICATE` |
| 023 | `_get_movement_type_by_code` | `uq_movement_types_company_code` | captura + relectura |

**9 funciones, 10 protecciones, 6 restricciones.** Antes: 500 en las ocho
funciones de alta directa bajo carrera, y en `correct_rate` también sin carrera.
Después: 0.

### 8.3 · Un defecto nuevo en las propias capturas · `NEW_REGRESSION_CURRENT_DELTA`

Las siete capturas añadidas en la §7.1 traducían **cualquier** `IntegrityError`
al conflicto de dominio. Un `CHECK` incumplido o una clave foránea rota se
contestaban como «ya existe». Lo destapó la revalidación de mutaciones: con la
validación de tasa positiva retirada, la base rechazaba la tasa cero y el
servicio respondía `DUPLICATE_OBSERVATION`.

Corregido con un clasificador compartido, `app/core/integrity.py ·
es_violacion_unica(error, restriccion)`, que solo reconoce la violación única
(`SQLSTATE 23505`) **de esa restricción**; todo lo demás se vuelve a lanzar. Lo
defienden dos pruebas con errores reales de PostgreSQL —única, `CHECK` y foránea—
y dos mutaciones (§8.5). Hoy no se alcanzaba por el camino normal; la defensa en
profundidad, sin embargo, mentía.

### 8.4 · Correcciones de evidencia adicionales

**CORRECTION-013-04 · «doce Specs».** La deriva heredada se atribuyó a doce Specs
sin mapearla. Mapeada por la migración que creó cada tabla y por el mapa de
equivalencias, son **diez**: 004, 006, 009, 010, 021, 023, 029, 031, 041 y 056.
Las 21 operaciones cuadran.

**CORRECTION-013-05 · el «019».** La §6 llamó a ese número «identificador
histórico del máster». No venía del máster: lo escribió la Spec 038 en sus
propios documentos como dueño de dos deudas, y era un error. La dueña es la 038
(errata en `spec038-convergence.md` §14).

**CORRECTION-013-06 · las mutaciones de la primera pasada.** Las doce primeras
se ejecutaron **antes** de la paridad y del endurecimiento, y nunca se repitieron
contra el código final. Repetidas:

- Un primer intento no dio resultado alguno: la expresión `-k` se partió en
  palabras, pytest salió con **código 4 (error de uso)** y el guion lo etiquetó
  como «sobrevive». No contó ni como detectada ni como superviviente (P27).
- Repetidas bien, **M013-08 sobrevive**: con el índice único y su captura en la
  base de pruebas, quitar la comprobación previa de reimportación ya no cambia
  nada observable. Deja de contar y se sustituye por **M013-08b**, que rompe la
  identidad del lote.

### 8.5 · Preguntas materiales

**Ninguna nueva.** El clasificador, las restricciones y los códigos de dominio
tienen autoridad en el propio repositorio.
