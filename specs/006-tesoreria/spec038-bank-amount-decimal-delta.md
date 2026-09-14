# SPEC 038 · DELTA DIRIGIDO FLOAT-038-A — EL IMPORTE DEL MOVIMIENTO BANCARIO ENTRA COMO `float`

> 2026-09-14. Delta dirigido dentro de la **Spec 038 — Tesorería** (carpeta
> `006-tesoreria`). No reabre la 038 ni crea una Spec nueva.
>
> **Veredicto: `FLOAT-038-A — BLOCKED BY MATERIAL DECISION`.** El ciclo se detuvo
> en `/speckit.clarify` con dos preguntas materiales sin autoridad (§4). No se
> ejecutó `/speckit.plan` ni `/speckit.implement`, no se consumió la autorización
> expresa y **no se tocó código**.

## 0. Verificación física

| | |
|---|---|
| HEAD | `d910b82` (el esperado) |
| Rama | `develop` |
| Árbol | limpio |
| PostgreSQL medido | **16.2** (`select version()`); el objetivo histórico 18.6 no es la versión instalada → `ENVIRONMENT_BASELINE_DEVIATION`, declarada |

## 1. Identidad del dueño — CASE A, resuelta

No se dedujo del nombre de la deuda. Se reconstruyó el camino del símbolo:

| Eslabón | Hallazgo |
|---|---|
| Símbolo | `BankTransactionCreate.amount: float = Field(gt=0)` |
| Fichero | `resources/backend/app/modules/treasury/api.py:135` |
| Módulo | `treasury` |
| Rutas | `POST /api/v1/treasury/bank-transactions` (`api.py:429`) · lectura `GET` (`api.py:418`) |
| Servicio | `treasury/service.py · create_bank_transaction(amount: float, commission: float)`; `bank_transaction_dict` |
| ORM | `BankTransaction.amount: Mapped[float] = mapped_column(Numeric(18, 2))` |
| Tabla | `bank_transactions.amount` — `numeric(18,2)` en `information_schema` |
| Migraciones | creada en `0006_tesoreria`; llevada a `Numeric` en `0012_numeric_money` |
| Llamantes | `IngresosEgresosPage.tsx:101`; `e2e/treasury.spec.ts:62`, `e2e/rates.spec.ts:335`; `test_mc_treasury_ab.py`, `test_n10_cross_company_writes.py:121`; dentro del servicio, `create_bank_transaction` también lo llaman la ejecución de pagos y cobros (`service.py:575`, `:616`), la transferencia (`:653`, `:657`), la conversión de la 038 (`:958`, `:962`) y el reembolso (`:1181`) |
| Marca de Spec | ninguna sobre la sección bancaria; las marcas de la 038 (`api.py:622`) y de la 013 (`api.py:831`) están en el mismo fichero |
| Mapa de equivalencias | `spec-equivalence-map.md:45` — «038 Tesorería ↔ `006-tesoreria`» (la carpeta también aloja 013 y 041) |
| Máster 56 | fila 038 · Tesorería · `COMPLETE / CONVERGED` |
| Historia | la clase nace en `e414677` «feat(006): implementacion de tesoreria» |
| Número local o histórico | «019» en `spec038-convergence.md` §12 — **errata** en §14: nunca existió; la Spec 019 global es Recepción física y **no se toca** |

**Dueña canónica: Spec 038.** Un movimiento bancario es operación de tesorería:
no es un maestro (013) ni el IGTF (041). `OWNER_IDENTITY_CONFLICT = 0`.

## 2. Flujo de tipos actual, medido

| Capa | Tipo | Evidencia |
|---|---|---|
| Cliente | número JS (`double`) | `IngresosEgresosPage.tsx:101`: `amount: Number(amount) \|\| 0` |
| HTTP JSON | `number` | frontend, E2E y pruebas |
| Decodificación FastAPI | `float` | `json.loads` convierte todo número JSON antes de Pydantic |
| Pydantic | **`float`** `gt=0` | **primer punto donde el tipo declara `float`** |
| API → servicio | sin conversión | `amount=body.amount` |
| Servicio | anotado `float`; `amount <= 0` → `INVALID_AMOUNT` 422 | `service.py · create_bank_transaction` |
| ORM | `Mapped[float]` sobre `Numeric(18, 2)` | la anotación miente: SQLAlchemy devuelve `Decimal` |
| Controlador → PostgreSQL | `float8` → `numeric(18,2)` | cast del parámetro |
| PostgreSQL | `numeric(18,2)` | `information_schema.columns` |
| Lectura | `Decimal` | |
| Respuesta | `Decimal` → `jsonable_encoder` → **`float`** → `number` | `bank_transaction_dict` devuelve el `Decimal` crudo |
| OpenAPI | petición: `{"type": "number", "exclusiveMinimum": 0}` · respuesta: `{}` (sin modelo) | `app.openapi()` |

Medido contra la base de pruebas:

| Entrada | Resultado |
|---|---|
| `1234567890123456.78` como número JSON | persistido **`1234567890123456.80`** |
| `"1234567890123456.78"` en un campo `Decimal` | `Decimal('1234567890123456.78')`, exacto |
| `Decimal('1234567890123456.78')` al serializar la respuesta | **`1234567890123456.8`** |
| `0.001` | pasa `gt=0` y se guarda **`0.00`** |
| `0.005` | PostgreSQL guarda `0.01` (mitad hacia arriba); `_money` daría `0.00` (mitad al par) |

**Almacenamiento correcto.** No hace falta migración, instalación limpia ni
roundtrip de migración: la columna ya es `numeric(18,2)`.

## 3. `/speckit.specify`

**FR-038-FLOAT-A-001.** Todo importe recibido mediante
`BankTransactionCreate.amount` preserva la exactitud decimal desde la frontera de
validación hasta la persistencia, la respuesta y los consumidores.

| Aceptación | Estado |
|---|---|
| sin `float` en el campo | definida |
| sin conversión a `float` en el camino | definida |
| `Decimal` de extremo a extremo | definida |
| persistencia exacta en PostgreSQL | definida |
| contrato de API coherente y OpenAPI igual a la ejecución | **depende de OQ-FLOAT-038-A-01** |
| límite de escala | **depende de OQ-FLOAT-038-A-02** |
| sin regresión funcional, multiempresa ni de conciliación | definida |

## 4. `/speckit.clarify`

| # | Pregunta | Respuesta | Autoridad | Estado |
|---|---|---|---|---|
| 1 | Dueña canónica | Spec 038 | §1 | RESUELTA |
| 2 | Representación actual en la API | `number` al entrar y al salir; la respuesta no declara esquema | §2 | RESUELTA |
| 3 | Tipo Pydantic | `float`, `gt=0` | `api.py:135` | RESUELTA |
| 4 | Tipo del servicio | anotado `float`; no llama a `float()` | `service.py` | RESUELTA |
| 5 | Tipo ORM | `Mapped[float]` sobre `Numeric(18, 2)` | `models.py` | RESUELTA |
| 6 | Tipo en PostgreSQL | `numeric(18,2)` | `information_schema` | RESUELTA — sin migración |
| 7 | Precisión y escala | 18 y 2: las fija la columna, cuya autoridad es `Currency.decimal_places` (013); `_MONEY_PLACES = 2` lo declara | `service.py:89-92`, `models.py:123` | RESUELTA para almacenar · **qué hacer con más decimales: OQ-02** |
| 8 | Semántica de signo | `direction` `IN`/`OUT` e importe **positivo** (`gt=0` y `INVALID_AMOUNT`); se conserva | `api.py`, `service.py` | RESUELTA |
| 9 | Serialización | `number` vía `float`: pierde dígitos por encima de unos 15 significativos | §2 | **OQ-01** |
| 10 | Frontend | envía `Number(amount)`, que degrada antes de la petición; lee `BankTransactionSummary.amount: number` y pinta `t.amount.toFixed(2)` (`ConciliacionPage.tsx:210`) | `types.ts` | RESUELTA como hecho · su cambio depende de OQ-01 |
| 11 | Compatibilidad con llamantes externos | en el repositorio no hay integración externa que llame a la ruta; `/api/v1` es contrato publicado sin registro de consumidores, así que **no puede afirmarse** que no existan | búsqueda | es la razón de que OQ-01 sea una decisión |
| 12 | Consumidores aguas abajo | conciliación: `Payment.amount == bt.amount`, `Decimal` contra `Decimal`; posición de caja de la 038 con `_money`; ejecución de pagos y cobros con `payment.amount` `Decimal`; conversión y reembolso de la 038 con `Decimal`; la transferencia llega desde `TransferCreate.amount: float` (mismo defecto, fuera de este delta); dashboard con suma en `float` (049, `PREEXISTING`, no se toca) | `service.py` | RESUELTA |
| 13 | Pruebas actuales | `test_treasury.py`, `test_spec038_treasury.py`, `test_mc_treasury_ab.py`, `test_n10_cross_company_writes.py`, E2E `treasury` y `rates`: todas envían números pequeños y **ninguna distingue** una ruta `float` | búsqueda | RESUELTA — faltan las dirigidas |

**La entrada no es una pregunta abierta.** Un campo `Decimal` acepta número y
cadena (OpenAPI pasa a `anyOf: number | string`). Es un cambio aditivo, con
precedente en el mismo módulo: `source_amount` y el `amount` del reembolso de la
038 (`api.py:647`, `:656`), y `rate` de la 013. Los números siguen comportándose
como hoy y las cadenas llegan exactas. Lo que no cabe en el contrato actual es
**la salida**.

### OQ-FLOAT-038-A-01 · Cómo sale el importe en la respuesta — MATERIAL

**Hecho.** `POST` y `GET /treasury/bank-transactions` devuelven `amount` como
número JSON, y FastAPI lo obtiene convirtiendo el `Decimal` a `float`. Un importe
de 16 a 18 dígitos que la columna guarda bien sale mal:
`1234567890123456.78` → `1234567890123456.8`. El prompt exige degradación de
respuesta **0** (§36, §76) y prohíbe cambiar de número a cadena sin autoridad
(§14, §23).

**Por qué no hay autoridad.** Las rutas nuevas de la 038, la 037, la 036, la 034
y la 030 ya devuelven dinero como cadena (`str(_money(...))`), pero **siempre en
campos nuevos**: ningún commit cambió un campo existente de número a cadena, y
ningún documento de gobierno fija la representación del dinero en la API.

| Opción | Qué implica |
|---|---|
| **A · cadena decimal** (`"1234567890123456.78"`), el patrón de las rutas convergidas | exacto. **Cambio público**: rompe a quien lea número. En el repositorio: `BankTransactionSummary.amount`, `toFixed(2)` en conciliación y la tabla de ingresos y egresos. Fuera: desconocido. `commission`, fuera de este delta, quedaría como número en el mismo objeto salvo que la decisión cubra el recurso entero |
| B · número, degradación documentada | sin cambio público. Acepta que importes de más de unos 15 dígitos significativos salgan redondeados; contradice «degradación de respuesta 0» |
| C · número JSON literal exacto con serializador propio | conserva `number`, pero es un mecanismo de serialización que ninguna ruta usa, y los clientes JavaScript lo vuelven a leer como `double` |

**Recomendación: A**, con el frontend adaptado en el mismo delta y extendida a
todo el recurso (`amount` y `commission`), porque es el patrón que tesorería ya
usa. Decide el owner.

### OQ-FLOAT-038-A-02 · Un importe con más decimales que la escala — MATERIAL

**Hecho.** Hoy `0.001` pasa la validación `gt=0` y PostgreSQL guarda un
movimiento bancario de **`0.00`**. Además hay dos redondeos distintos en el mismo
módulo: PostgreSQL lleva `0.005` a `0.01`, y `_money` (cuantización `Decimal`,
mitad al par) lo llevaría a `0.00`.

**Por qué no hay autoridad.** `service.py:89-92` fija la escala y dice
expresamente «Aquí no se decide ninguna política de redondeo». Ninguna fuente dice
si el exceso se rechaza o se redondea.

| Opción | Qué implica |
|---|---|
| **A · rechazar con 422** | sin política de redondeo; coherente con la escala del maestro de monedas. Cambia la respuesta a una entrada que hoy se acepta |
| B · conservar el redondeo de PostgreSQL | declara una política —mitad hacia arriba— que nadie eligió; el movimiento de `0.00` sigue siendo posible |
| C · cuantizar con `_money` | declara la mitad al par y cambia el valor guardado respecto de hoy |

**Recomendación: A.** Decide el owner.

## 5. Parada

Según la secuencia del prompt (§85): una pregunta material detiene el ciclo
después de `/speckit.clarify`.

| Etapa | Estado |
|---|---|
| `/speckit.specify` | **HECHA** (§3) |
| `/speckit.clarify` | **HECHA**: 11 resueltas, 2 materiales |
| `/speckit.plan` · CONSTITUTION GATE · `/speckit.checklist` · `/speckit.tasks` · `/speckit.analyze` | **no ejecutadas** |
| Autorización expresa | **no consumida**: `MATERIAL OQ = 2` |
| `/speckit.implement` · pruebas · `/speckit.converge` | **no ejecutadas** |

Lo que las respuestas desbloquean, para no volver a medir:

| Puerta | Hoy |
|---|---|
| G-FLOAT-A-01 dueña · 02 sin 019 global · 03 sin Spec nueva · 04 `Decimal` canónico · 05 sin segundo motor · 09 ORM y base conocidos · 10 sin FLOAT-038-B · 11 contexto de empresa intacto · 13 consumidores identificados | cumplibles en diseño |
| G-FLOAT-A-06 autoridad de precisión · 07 escala no arbitraria | **esperan OQ-02** |
| G-FLOAT-A-08 compatibilidad de API · 12 OpenAPI | **esperan OQ-01** |
| G-FLOAT-A-14 mutación con semántica | diseño listo: `"1234567890123456.78"` enviado como cadena; con `amount: float` se guarda `…56.80` y la prueba cae |

## 6. Recuento

| | |
|---|---|
| OWNER_IDENTITY_CONFLICT | 0 |
| MATERIAL OQ | **2** — OQ-FLOAT-038-A-01, OQ-FLOAT-038-A-02 |
| UNKNOWN | 0 |
| CONTRADICTIONS | 0 |
| Migración necesaria | no |
| Código modificado | ninguno |

## 7. Deuda que sigue abierta y no se absorbe

| Deuda | Estado |
|---|---|
| FLOAT-038-A · los otros siete `float` del borde de tesorería (`commission`, `opened_amount`, importes de movimiento de caja, de ejecución y de transferencia, saldos de conciliación) | `OPEN`, misma dueña, mismas dos preguntas |
| FLOAT-038-B · arqueo y cierre de caja | `OPEN / SCHEDULED`. La resta ya es exacta (errata §14 de `spec038-convergence.md`); lo que queda es el épsilon `1e-6` de `close_session`, `counted_amount: float` y el `float(...)` de su auditoría |
| CONC-046 | `OPEN` |
| E2E de la 045 (`approvals.spec.ts`, «Desactivar») | `OPEN` |
| Camino tras `EXPIRED` en la 045 | `OPEN` |
| Spec 049 y sus cinco defectos del dashboard | sin implementar |
| Deriva de esquema heredada | 21 operaciones en **10** Specs (`next-spec-decision.md`), sin tocar |
