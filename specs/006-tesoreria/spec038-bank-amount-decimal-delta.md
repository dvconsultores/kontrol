# SPEC 038 · DELTA DIRIGIDO FLOAT-038-A — EL IMPORTE DEL MOVIMIENTO BANCARIO ENTRA COMO `float`

> Delta dirigido dentro de la **Spec 038 — Tesorería** (carpeta `006-tesoreria`).
> No reabre la 038 ni crea una Spec nueva.
>
> | Fecha | Hito |
> |---|---|
> | 2026-09-14 · `239259b` | `/speckit.specify` y `/speckit.clarify`; **detenido** con dos preguntas materiales |
> | 2026-09-14 | el owner cierra OQ-FLOAT-038-A-01 y -02 (opción A en ambas); el ciclo **continúa** desde `/speckit.plan` |
> | 2026-09-15 | implementado, probado y convergido |
>
> **Veredicto: `FLOAT-038-A — TARGETED DELTA COMPLETE / CONVERGED`.** La Spec 038
> sigue `COMPLETE / CONVERGED`; esto es una reconvergencia dirigida, no un ciclo
> global nuevo. Evidencia en §13 y en `evidence/float-038-a/`.

## 0. Verificación física

| | Primera parada | Continuación |
|---|---|---|
| HEAD | `d910b82` | `239259b` (el esperado) |
| Rama | `develop` | `develop` |
| Árbol | limpio | limpio |
| PostgreSQL medido | **16.2**; el objetivo 18.6 no es la versión instalada → `ENVIRONMENT_BASELINE_DEVIATION` | 16.2, sin cambio |

## 1. Identidad del dueño — resuelta

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
| Mapa de equivalencias | `spec-equivalence-map.md:45` — «038 Tesorería ↔ `006-tesoreria`» |
| Máster 56 | fila 038 · Tesorería · `COMPLETE / CONVERGED` |
| Historia | la clase nace en `e414677` «feat(006): implementacion de tesoreria» |
| Número local o histórico | «019» en `spec038-convergence.md` §12 — **errata** en §14; la Spec 019 global es Recepción física y **no se toca** |

**Dueña canónica: Spec 038.** `OWNER_IDENTITY_CONFLICT = 0`.

## 2. Flujo de tipos antes del delta, medido

| Capa | Tipo | Evidencia |
|---|---|---|
| Cliente | número JS (`double`) | `IngresosEgresosPage.tsx:101`: `amount: Number(amount) \|\| 0` |
| HTTP JSON | `number` | frontend, E2E y pruebas |
| Decodificación FastAPI | `float` | `json.loads` convierte todo número JSON antes de Pydantic |
| Pydantic | **`float`** `gt=0` | primer punto donde el tipo declara `float` |
| API → servicio | sin conversión | `amount=body.amount` |
| Servicio | anotado `float`; `amount <= 0` → `INVALID_AMOUNT` 422 | |
| ORM | `Mapped[float]` sobre `Numeric(18, 2)` | la anotación miente: SQLAlchemy devuelve `Decimal` |
| PostgreSQL | `numeric(18,2)` | `information_schema.columns` |
| Respuesta | `Decimal` → `jsonable_encoder` → **`float`** → `number` | `bank_transaction_dict` devuelve el `Decimal` crudo |
| OpenAPI | petición `{"type": "number", "exclusiveMinimum": 0}` · respuesta `{}` (la ruta no declara modelo) | `app.openapi()` |
| Frontend al leer | `BankTransactionSummary.amount: number`; `t.amount.toFixed(2)` (`ConciliacionPage.tsx:210`) | `types.ts` |

| Entrada medida | Resultado |
|---|---|
| `1234567890123456.78` como número JSON | persistido **`1234567890123456.80`** |
| `Decimal('1234567890123456.78')` al serializar la respuesta | **`1234567890123456.8`** |
| `0.001` | pasa `gt=0` y se guarda **`0.00`** |
| `0.005` | PostgreSQL guarda `0.01`; `_money` daría `0.00` |

## 3. `/speckit.specify`

Requisito raíz **FR-038-FLOAT-A-001**: todo importe recibido o devuelto por el
contrato de movimiento bancario conserva la exactitud decimal desde la frontera
hasta la persistencia, la respuesta y la pantalla. Tras cerrar las decisiones se
divide en (el detalle normativo vive en `spec.md` §6.7):

| ID | Requisito |
|---|---|
| FR-038-FLOAT-A-001 | `amount` y `commission` se reciben **solo** como texto decimal; un número JSON se rechaza con 422 |
| FR-038-FLOAT-A-002 | forma léxica: dígitos ASCII con parte fraccionaria opcional; sin notación científica, `NaN`, `Infinity`, espacios ni separadores. `amount` sin signo; `commission` admite `-` (hoy no tiene regla de signo y no se inventa una) |
| FR-038-FLOAT-A-003 | la escala no supera la de la columna (2) y los dígitos enteros no superan precisión − escala (16); si no, 422. Ni redondeo de PostgreSQL ni cuantización de `_money` |
| FR-038-FLOAT-A-004 | `amount > 0` se conserva: `"0.00"` y `"-1.00"` → 422 |
| FR-038-FLOAT-A-005 | por dentro, `Decimal`: servicio y ORM anotados `Decimal`; ninguna conversión a `float` entre la frontera y PostgreSQL |
| FR-038-FLOAT-A-006 | `POST` y `GET /treasury/bank-transactions` devuelven `amount` y `commission` como texto con escala 2 (`"10.50"`), mediante modelo de respuesta explícito; OpenAPI declara `string` en petición y respuesta |
| FR-038-FLOAT-A-007 | una petición rechazada no deja hecho económico: ni fila, ni cambio de saldo |
| FR-038-FLOAT-A-008 | el frontend envía texto canónico sin `Number`, `parseFloat` ni `+`; valida la escala como ayuda; muestra el importe sin convertirlo a número; tipos `string` |
| FR-038-FLOAT-A-009 | el cambio incompatible del contrato se declara en contratos, OpenAPI, pruebas y convergencia |

## 4. `/speckit.clarify`

| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| 1 | Dueña canónica | Spec 038 (§1) | RESUELTA |
| 2 | Representación actual en la API | `number` al entrar y al salir; la respuesta no declara esquema | RESUELTA |
| 3 | Tipo Pydantic | `float`, `gt=0` | RESUELTA |
| 4 | Tipo del servicio | anotado `float`; no llama a `float()` | RESUELTA |
| 5 | Tipo ORM | `Mapped[float]` sobre `Numeric(18, 2)` | RESUELTA |
| 6 | Tipo en PostgreSQL | `numeric(18,2)` | RESUELTA — sin migración |
| 7 | Precisión y escala | 18 y 2, de la columna; la validación las **lee de la columna**, no las repite | RESUELTA · exceso → OQ-02 cerrada |
| 8 | Semántica de signo | `direction` `IN`/`OUT` e importe positivo; `commission` sin regla de signo | RESUELTA |
| 9 | Serialización | hoy `number` vía `float` | OQ-01 **cerrada** |
| 10 | Frontend | envía `Number(amount)`; lee `number` y usa `toFixed(2)` | RESUELTA · se adapta en el mismo delta |
| 11 | Llamantes externos | en el repositorio no hay integración externa que llame a la ruta; fuera no hay inventario | RESUELTA · cambio incompatible autorizado |
| 12 | Consumidores aguas abajo | conciliación `Payment.amount == bt.amount` (`Decimal` contra `Decimal`); posición de caja con `_money`; pagos, cobros, conversión y reembolso con `Decimal`; transferencia con `TransferCreate.amount: float` (fuera); dashboard en `float` (049, no se toca) | RESUELTA |
| 13 | Pruebas actuales | envían números pequeños y ninguna distingue una ruta `float` | RESUELTA |

### OQ-FLOAT-038-A-01 · `CLOSED_BY_OWNER_DECISION` — opción A

**Elegida:** texto decimal en el contrato público, al entrar y al salir, para
`amount` y `commission`: comparten petición, respuesta, tipo de pantalla y columna,
y corregir solo uno dejaría el mismo objeto con dos políticas.
**Descartadas:** B, número con degradación documentada; C, número literal con
serializador propio. **Razón:** la exactitud tiene que sobrevivir a tres fronteras
—JavaScript, HTTP y Python— y un número JSON no sobrevive a la primera.

### OQ-FLOAT-038-A-02 · `CLOSED_BY_OWNER_DECISION` — opción A

**Elegida:** más decimales que la escala de la columna → **422**.
**Descartadas:** redondeo de PostgreSQL; cuantización de `_money`.
**Razón:** ninguna transformación económica silenciosa. Para este contrato la
escala efectiva es **2**, la de `numeric(18,2)`. Una escala por moneda
(`Currency.decimal_places`) exigiría cambiar contrato, modelo y migración en otro
delta: aquí no se finge.

## 5. Contrato resultante

Detalle en `contracts/api-contracts.md` §3.1.

| | Antes | Después |
|---|---|---|
| Petición `amount` | `number > 0` | `string`, `^[0-9]+(\.[0-9]{1,2})?$`, > 0, hasta 16 dígitos enteros |
| Petición `commission` | `number \| null` | `string \| null`, `^-?[0-9]+(\.[0-9]{1,2})?$` |
| Respuesta `amount` | `number` (vía `float`) | `string` con dos decimales |
| Respuesta `commission` | `number \| null` | `string \| null` con dos decimales |
| OpenAPI de la respuesta | `{}` | `BankTransactionOut` · `BankTransactionPage` |
| Compatibilidad | — | **incompatible y autorizada**: un cliente que envíe número recibe 422 y uno que lea número recibe texto |

## 6. `/speckit.plan`

| Ola | Contenido | Tareas |
|---|---|---|
| W01 | Contratos y artefactos | T-FA-01 |
| W02 | Tipo de entrada solo texto | T-FA-02, T-FA-03 |
| W03 | Validación de escala y precisión desde la columna | T-FA-02 |
| W04 | Servicio anotado `Decimal` | T-FA-04 |
| W05 | Anotación ORM `Decimal` | T-FA-05 |
| W06 | Modelo de respuesta explícito | T-FA-06 |
| W07 | Serialización exacta con el patrón de la 038 (`str(_money(...))`) | T-FA-06 |
| W08 | `commission` con la misma política | T-FA-03, T-FA-06 |
| W09 | Tipos del frontend | T-FA-10 |
| W10 | Envío desde la pantalla | T-FA-09, T-FA-11 |
| W11 | Presentación sin `Number` | T-FA-11, T-FA-12 |
| W12 | OpenAPI | T-FA-06, T-FA-08 |
| W13 | Pruebas dirigidas de backend | T-FA-07, T-FA-08 |
| W14 | Pruebas dirigidas de frontend | T-FA-13 |
| W15 | Mutaciones M-FLOAT-038-A-01..04 | T-FA-15 |
| W16 | Guardas estáticas | T-FA-08, T-FA-13 |
| W17 | Consumidores y conciliación | T-FA-08, T-FA-16 |
| W18 | Regresión completa de backend, sola | T-FA-17 |
| W19 | Regresión de frontend y E2E en tres navegadores | T-FA-14, T-FA-18 |
| W20 | Analyze final | T-FA-19 |
| W21 | Trazabilidad | T-FA-19 |
| W22 | Convergencia dirigida | T-FA-19 |

Decisiones de diseño:

| Tema | Decisión | Base |
|---|---|---|
| Dónde vive el tipo de entrada | `app/shared/money.py`: es lógica genérica (texto → `Decimal` con escala y precisión dadas), no de bancos | §20 del prompt |
| De dónde salen escala y precisión | de la columna `BankTransaction.amount` (`Numeric(18, 2)`); el tipo no escribe `2` ni `18` | §12 · P-autoridad |
| Serialización de salida | `str(_money(valor))`, el mismo patrón de las respuestas de conversión y reembolso de la 038; no se crea otro formateador | §20 del prompt |
| Presentación en pantalla | `formatMoney` de `lib/format.ts`, que ya opera sobre texto | §23 del prompt |
| Envío desde pantalla | `lib/decimal.ts · toDecimalString`: normaliza sin `Number` | §49 del prompt |
| Ordenación | `DataTable` no ordena: no hay comparador que adaptar | §52 del prompt |
| Filtros | no hay filtro por importe | §53 del prompt |
| Versionado de API | el repositorio no tiene registro de cambios ni versionado: se documenta en contratos y convergencia, sin inventar `/api/v2` | §92 del prompt |

## 7. CONSTITUTION GATE

| Puerta | Diseño |
|---|---|
| G-A-01 dueña 038 confirmada | **PASS** — §1 |
| G-A-02 sin Spec nueva | **PASS** |
| G-A-03 `Decimal` por dentro | **PASS** — W02-W05 |
| G-A-04 texto decimal en el contrato público | **PASS** — OQ-01 |
| G-A-05 el número JSON deja de ser autoridad | **PASS** — FR-038-FLOAT-A-001 |
| G-A-06 más de 2 decimales se rechaza | **PASS** — OQ-02 |
| G-A-07 sin redondeo silencioso | **PASS** |
| G-A-08 almacenamiento sigue `numeric(18,2)` | **PASS** |
| G-A-09 sin migración innecesaria | **PASS** |
| G-A-10 frontend sin `Number`/`parseFloat` en el camino | **PASS** — W10 |
| G-A-11 OpenAPI explícito | **PASS** — W06, W12 |
| G-A-12 respuesta exacta | **PASS** — W07 |
| G-A-13 sin segundo motor monetario | **PASS** — `_money` y `formatMoney` reutilizados |
| G-A-14 sin FLOAT-038-B | **PASS** |
| G-A-15 sin tocar los otros siete `float` | **PASS** |
| G-A-16 multiempresa intacto | **PASS** — `CompanyContext` sin cambio |
| G-A-17 conciliación intacta | **PASS** |
| G-A-18 la mutación distingue el defecto | **PASS** en diseño — fixture `"1234567890123456.78"` |

**18 PASS · 0 condicionadas.**

## 8. `/speckit.checklist`

- [x] OQ-01 cerrada · [x] OQ-02 cerrada
- [x] contrato público de texto decimal documentado · [x] entrada estricta documentada · [x] serialización de salida documentada
- [x] alcance `amount` · [x] alcance `commission`
- [x] rechazo de escala > 2 definido · [x] signo conservado
- [x] base `numeric(18,2)` confirmada · [x] sin migración
- [x] servicio `Decimal` · [x] anotación ORM auditada · [x] modelo de respuesta auditado
- [x] `BankTransactionSummary` auditado · [x] tipos del frontend auditados
- [x] `Number(amount)` fuera del camino · [x] `toFixed` fuera del camino
- [x] OpenAPI explícito · [x] pruebas definidas · [x] mutaciones definidas · [x] regresión de consumidores definida
- [x] MATERIAL OQ = 0 · [x] UNKNOWN = 0 · [x] trazabilidad 100 %

## 9. `/speckit.tasks`

| ID | Requisito | Ficheros | Depende | Cambio | Aceptación y prueba |
|---|---|---|---|---|---|
| T-FA-01 | 001-009 | `spec.md`, `clarifications.md`, `research.md`, `contracts/api-contracts.md`, este documento | — | decisiones, requisitos, contrato, evidencia previa | revisión |
| T-FA-02 | 001-003 | `app/shared/money.py` | — | `texto_decimal(columna, positivo)`: solo `str`, léxico estricto, escala y dígitos enteros leídos de la columna, `> 0` opcional; esquema `string` con patrón | `test_spec038_float_a.py` · M-02 |
| T-FA-03 | 001-004 | `treasury/api.py` | 02 | `BankTransactionCreate.amount` y `.commission` con el tipo nuevo | pruebas de entrada · M-01 |
| T-FA-04 | 005 | `treasury/service.py` | — | `create_bank_transaction(amount: Decimal, commission: Decimal \| None)` | guarda de anotaciones |
| T-FA-05 | 005 | `treasury/models.py` | — | `Mapped[Decimal]` en `amount` y `commission`; columna igual | paridad del ámbito tocado |
| T-FA-06 | 006 | `treasury/api.py`, `treasury/service.py` | — | `BankTransactionOut`, `BankTransactionPage`; `bank_transaction_dict` con `str(_money(...))` | pruebas de respuesta y OpenAPI · M-03 |
| T-FA-07 | 001 | `test_mc_treasury_ab.py`, `test_n10_cross_company_writes.py` | 03 | los llamantes envían texto: el contrato cambió, las aserciones no | regresión multiempresa |
| T-FA-08 | 001-007 | `tests/test_spec038_float_a.py` | 02-06 | pruebas dirigidas, OpenAPI, guardas por inspección, conciliación exacta | verde · mutaciones rojas |
| T-FA-09 | 008 | `src/lib/decimal.ts` | — | `toDecimalString` sin `Number` | `decimal.test.ts` |
| T-FA-10 | 008 | `src/api/types.ts` | — | `amount: string`, `commission: string \| null` | `tsc` |
| T-FA-11 | 008 | `IngresosEgresosPage.tsx` | 09, 10 | envío con `toDecimalString`; celda con `formatMoney` | prueba de envío exacto · M-04 |
| T-FA-12 | 008 | `ConciliacionPage.tsx` | 10 | opción con `formatMoney(t.amount)` | prueba de presentación |
| T-FA-13 | 008 | `src/modules/tesoreria/importe-bancario.test.tsx` | 11, 12 | envío y presentación exactos; guarda del fuente | verde · M-04 roja |
| T-FA-14 | 001, 008, 009 | `e2e/treasury.spec.ts`, `e2e/rates.spec.ts` | 03, 11 | fondeos en texto; prueba de contrato por API y de pantalla exacta | tres navegadores |
| T-FA-15 | 001-008 | `evidence/float-038-a/` | 08, 13 | M-FLOAT-038-A-01..04 con motivo y fallo real | cuatro rojas y restauradas |
| T-FA-16 | 005, 007 | suites de tesorería | 03-06 | `test_treasury`, `test_spec038_treasury`, `test_mc_treasury_ab`, `test_n10_cross_company_writes`, `test_spec013*` | verde |
| T-FA-17 | todos | regresión completa | 16 | sola | 0 fallos, 0 errores, 0 omisiones inesperadas |
| T-FA-18 | 008 | frontend | 13 | Vitest, `tsc`, ESLint, build | EXIT 0 |
| T-FA-19 | 009 | convergencia, trazabilidad, máster, decisión siguiente | 17, 18 | analyze final y cierre | §15 |

## 10. `/speckit.analyze` previo a implementar

| Búsqueda | Hallazgo | Tarea |
|---|---|---|
| `amount: float` / `commission: float` en `BankTransactionCreate` | 2 | T-FA-03 |
| `amount: float` / `commission: float` en el servicio | 2 | T-FA-04 |
| `Mapped[float]` sobre `Numeric(18,2)` | 2 en el ámbito | T-FA-05 |
| respuesta `Decimal` → `float` · OpenAPI `{}` | 2 rutas | T-FA-06 |
| `Number(amount)` · `toFixed` sobre el importe bancario | 1 · 1 | T-FA-11, T-FA-12 |
| `parseFloat` | 0 en el camino | — |
| `amount: number` · `commission: number` en TS | 2 | T-FA-10 |
| redondeo implícito de PostgreSQL · `_money` corrigiendo entrada | ninguno después de T-FA-02 | T-FA-02 |
| épsilon | 0 en el camino (`1e-6` es de FLOAT-038-B) | — |
| otros siete `float` · FLOAT-038-B · dashboard | fuera; no se tocan | — |
| clientes que envían número | `test_mc_treasury_ab`, `test_n10`, `treasury.spec`, `rates.spec` | T-FA-07, T-FA-14 |

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRAZABILIDAD | 100 % |

**Autorización expresa consumida.** Se procede a `/speckit.implement`.

## 11. Deuda que sigue abierta y no se absorbe

| Deuda | Estado |
|---|---|
| Los otros siete `float` del borde de tesorería: `SessionOpen.opened_amount`, importe de movimiento de caja, importe de ejecución, `ArqueoBody.counted_amount`, `opening_balance` y `closing_balance` de conciliación, `TransferCreate.amount` | `OPEN`, dueña 038. La transferencia sigue llegando a `create_bank_transaction` con `float`: la firma dice `Decimal`, el llamante no, y se corrige en su delta |
| FLOAT-038-B · arqueo y cierre de caja | `OPEN / SCHEDULED`. La resta ya es exacta (errata §14 de `spec038-convergence.md`); quedan el épsilon `1e-6` de `close_session`, `counted_amount: float` y el `float(...)` de su auditoría |
| CLOCK-013 · cinco pruebas de `test_spec013_financial_masters.py` mezclan `date.today()` local con `datetime.now(UTC)` | `OPEN`, `PREEXISTING`, dueña 013 (§14) |
| E2E-031-RESERVAS · `picking.spec.ts:288` cuenta las reservas de toda la empresa porque `GET /inventory/reservations` ignora `source_order_id` | `OPEN`, `PREEXISTING`, dueñas 031 (prueba) y 023 (filtro) (§14) |
| CONC-046 | `OPEN` |
| E2E de la 045 (`approvals.spec.ts`, «Desactivar») | `OPEN` |
| Camino tras `EXPIRED` en la 045 | `OPEN` |
| Spec 049 y sus cinco defectos del dashboard | sin implementar |
| Deriva de esquema heredada | 21 operaciones en **10** Specs, sin tocar |

## 12. `/speckit.implement`

| Capa | Antes | Después | Fichero |
|---|---|---|---|
| Cliente | `Number(amount) \|\| 0` | `toDecimalString(amount)`: texto canónico, sin redondeo; más de dos decimales se avisa y no se envía | `src/lib/decimal.ts` · `IngresosEgresosPage.tsx` |
| HTTP · petición | número JSON | **texto decimal**; un número → 422 | — |
| Pydantic | `amount: float = Field(gt=0)` · `commission: float \| None` | `texto_decimal(columna, positivo=…)`: solo `str`, léxico estricto, escala y dígitos enteros leídos de `Numeric(18, 2)`, `> 0` para `amount` | `app/shared/money.py` · `treasury/api.py` |
| API → servicio | sin conversión | sin conversión | `treasury/api.py` |
| Servicio | `amount: float` · `commission: float \| None` | `Decimal` · `Decimal \| None`; `INVALID_AMOUNT` intacto | `treasury/service.py` |
| ORM | `Mapped[float]` | `Mapped[Decimal]`; la columna no cambia | `treasury/models.py` |
| PostgreSQL | `numeric(18,2)` | `numeric(18,2)` — **sin migración** | — |
| Respuesta | `Decimal` → `jsonable_encoder` → `float` → número | `str(_money(...))` → texto con dos decimales, validado por `BankTransactionOut` / `BankTransactionPage` | `treasury/service.py` · `treasury/api.py` |
| OpenAPI | petición `number`; respuesta `{}` | petición `string` con patrón; respuesta `$ref` a los dos modelos | — |
| Frontend · tipos | `amount: number` · `commission: number \| null` | `string` · `string \| null` | `src/api/types.ts` |
| Frontend · pantalla | tabla sin formato; `t.amount.toFixed(2)` en conciliación | `formatMoney(...)` sobre el texto, en las dos | `IngresosEgresosPage.tsx` · `ConciliacionPage.tsx` |

Llamantes adaptados al contrato, sin cambiar lo que comprueban:
`test_mc_treasury_ab.py` (6 importes), `test_n10_cross_company_writes.py` (1),
`e2e/treasury.spec.ts` (`fondear` y sus 10 llamadas) y `e2e/rates.spec.ts` (1).

## 13. Evidencia

### Pruebas dirigidas

| Ámbito | Pruebas | Resultado |
|---|---|---|
| Backend · `tests/test_spec038_float_a.py` | tipo en la frontera; importe de 18 dígitos exacto en base, respuesta, listado y saldo; escala de salida; `0.10 + 0.20`; número JSON; forma léxica; escala y dígitos enteros sin efecto económico; cero y negativo; regla del servicio; comisión; OpenAPI; conciliación exacta; multiempresa; tres guardas estáticas | **49/49** |
| Frontend · `decimal.test.ts` · `importe-bancario.test.tsx` | normalización sin `Number`; envío exacto; escala en la pantalla; presentación en tabla y en conciliación; guarda del fuente | **10/10** |
| E2E · `treasury.spec.ts` | contrato por API (número, `0.001`, `0.005`, `1e3` → 422 sin filas; exacto de ida y vuelta, comisión y saldo); pantalla que envía `"1234567890123456.78"` y lo muestra `1.234.567.890.123.456,78` | **6/6** en Chromium, Firefox y WebKit |

### Mutaciones

| ID | Mutación | Fixture | Prueba que cae | Fallo real | Restaurada |
|---|---|---|---|---|---|
| M-FLOAT-038-A-01 | `amount: ImporteBancario` → `amount: float = Field(gt=0)` | `"1234567890123456.78"` | `test_un_importe_de_dieciocho_digitos_…` y `test_un_numero_json_se_rechaza` (5 de 7) | la base y la respuesta dicen `1234567890123456.80`; `123.45` y `100` entran con 200 | sí |
| M-FLOAT-038-A-02 | se quita el rechazo por escala | `"0.001"`, `"0.005"`, `"10.000"` | `test_mas_decimales_que_la_columna_…` (4 de 4) | 200 con `"0.00"` y `"0.01"`: PostgreSQL redondea en silencio | sí |
| M-FLOAT-038-A-03 | se quitan los modelos de respuesta y el dict devuelve el `Decimal` crudo | `"1234567890123456.78"`, `"10.50"` | `test_un_importe_de_dieciocho_digitos_…` y `test_la_respuesta_dice_…` (10 de 11) | la respuesta es el número `1234567890123456.8` y `10.5` | sí |
| M-FLOAT-038-A-04 | `amount: importe` → `amount: Number(importe)` en la pantalla | `"1234567890123456.78"` tecleado | «envía el importe como texto exacto» y la guarda del fuente | el cuerpo lleva `number`, no `string` | sí |

Tras restaurar: 49/49 (`evidence/float-038-a/restauracion.txt`).

### Paridad, migración e instalación limpia

| | |
|---|---|
| ORM ↔ PostgreSQL en `bank_transactions` | **0** diferencias (`compare_metadata` contra `ke2e` migrada); heredadas globales 21, sin cambio |
| Migración | **no** hace falta: la columna ya era `numeric(18,2)` y solo cambia la anotación |
| Instalación limpia | no obligatoria; aun así la base del E2E se reinstaló de cero: 57 migraciones, exit 0 |

### Regresión de backend, sola

| | |
|---|---|
| Entorno | PostgreSQL 16.2 (`ENVIRONMENT_BASELINE_DEVIATION` frente a 18.6) · `TZ=UTC` |
| Total | 1544 |
| Pasan | **1536** |
| Fallan | **0** |
| Errores | **0** |
| Omitidas | 8 — S3 real sin configurar, las mismas de la 047 |
| Omisiones inesperadas | **0** |
| Avisos | 0 |
| Exit | 0 |

Hubo una primera ejecución con la zona local que cruzó la medianoche y sin la base
legacy, perdida en un reinicio de la máquina: 1515/5/24. Sus cinco fallos y sus
dieciséis omisiones de más se clasifican en §14.

### Frontend

| | |
|---|---|
| Vitest | **359/359** en cinco ejecuciones seguidas, sin errores no capturados |
| `tsc` | exit 0 |
| ESLint | exit 0 |
| Build | exit 0 |

### E2E canónico, tres navegadores, después de la regresión

| | |
|---|---|
| Pruebas | 249 (243 de la cadena + 6 de este delta) |
| Pasan | 248 |
| Fallan | 1 — `picking.spec.ts:288` en Firefox, `PREEXISTING` (§14); aislada, **3/3** |
| FLOAT-038-A | 6/6 |
| Trazas y respuestas 500 en el backend | 0 · 0 |

## 14. Clasificación de lo encontrado

| Hallazgo | Clasificación | Dueña | Evidencia | Qué se hizo |
|---|---|---|---|---|
| 5 fallos en `test_spec013_financial_masters.py` con la zona local entre las 00:00 y las 02:00 CEST | `PREEXISTING` · defecto de prueba dependiente del reloj: registra con `datetime.now(UTC)` y consulta con `date.today()` local | 013 | `HEAD 239259b`: 5 fallos con zona local y 0 con `TZ=UTC`; el árbol del delta, idéntico (`reloj-spec013.txt`) | registrado como CLOCK-013; no absorbido |
| 16 omisiones «no hay base legacy sembrada» | `EXTERNAL_ENVIRONMENT`: un reinicio de la máquina vació `/tmp` y con él la base legacy | — | segunda regresión con `kontrol_legacy` sembrada: 8 omisiones | entorno reconstruido con la misma configuración |
| `picking.spec.ts:288` en Firefox: 54 → 55 reservas activas | `PREEXISTING` · defecto de prueba: `GET /inventory/reservations` no filtra por `source_order_id` y la prueba cuenta toda la empresa mientras otros navegadores crean reservas | 031 · 023 | aislada en Firefox 3/3; ni la prueba ni ventas ni inventario están en el diff | registrado como E2E-031-RESERVAS; no absorbido |
| Rechazo no capturado `window is not defined` desde `AsyncButton` | `TEST_DEFECT` latente de `AsyncButton.test.tsx` («previene doble envío» terminaba sin esperar su acción de 20 ms), aflorado al cambiar el reparto de ficheros | 005 | `HEAD` 0/5; delta 2/5; corregido 0/5 | **corregido** como delta dirigido recibido por la 005: la prueba ahora espera; se fortalece, no se debilita |
| Una aserción de `decimal.test.ts` mal planteada y un fixture de conciliación sin fecha | `TEST_DEFECT` de las pruebas de este delta | 038 | falló antes de la primera ejecución verde | corregidos |
| PostgreSQL 16.2 | `ENVIRONMENT_BASELINE_DEVIATION` | — | `show server_version` | declarado |

| Clase | Número |
|---|---|
| NEW_REGRESSION_FLOAT_038_A | **0** |
| PREEXISTING_SEALED | 2 — CLOCK-013, E2E-031-RESERVAS |
| TEST_DEFECT | 3 — corregidos (1 de la 005, 2 propios) |
| EXTERNAL_ENVIRONMENT | 1 — reinicio de la máquina |
| ENVIRONMENT_BASELINE_DEVIATION | 1 — PostgreSQL 16.2 |
| OWNER_DEPENDENCY · OWNER_IDENTITY_CONFLICT_DEBT · MATERIAL_DECISION_REQUIRED | 0 |
| UNKNOWN | **0** |

## 15. `/speckit.analyze` final y convergencia

| Búsqueda | Resultado |
|---|---|
| número JSON aceptado en `amount` o `commission` | no — M-01 lo demuestra por contraste |
| anotación `float` en esquema, servicio u ORM del importe bancario | 0 (guarda AST) |
| `float(...)` o `round(...)` en la ruta o la serialización | 0 (guarda AST) |
| respuesta `Decimal` → `float` | 0 — modelos declarados; M-03 por contraste |
| exceso de escala aceptado · redondeo de PostgreSQL como validador · `_money` corrigiendo entrada | no · 0 · 0 |
| `Number(amount)` · `parseFloat` · `toFixed` sobre el importe bancario | 0 · 0 · 0 |
| OpenAPI `{}` en las rutas del movimiento bancario | 0 |
| comisión con otra política | no |
| otros siete `float` tocados · FLOAT-038-B tocado · dashboard tocado | no · no · no |

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRAZABILIDAD | 100 % — 9 requisitos, 19 tareas, 4 mutaciones (`spec038-traceability-matrix.md`) |

Puerta de convergencia dirigida:

| Condición | |
|---|---|
| OQ-01 y OQ-02 cerradas | ✔ |
| `amount` de entrada y de salida en texto; `Decimal` dentro; `numeric(18,2)` en base | ✔ |
| `commission` con la misma política | ✔ |
| número JSON aceptado · más de dos decimales aceptado · redondeo implícito | no · no · 0 |
| `float` en anotaciones, conversiones y respuesta del camino | 0 |
| `Number` · `parseFloat` en el frontend del camino | 0 · 0 |
| valor de 18 dígitos exacto · `0.001` → 422 · `0.005` → 422 · efecto económico cero | ✔ |
| OpenAPI igual a la ejecución; respuesta `{}` corregida | ✔ |
| migración · deriva ORM/base en el ámbito | no hace falta · 0 |
| regresiones nuevas · mutaciones con semántica | 0 · 4/4 |
| backend: fallos · errores · omisiones inesperadas | 0 · 0 · 0 |
| frontend · E2E | ✔ · ✔ (el único fallo es preexistente y aislado pasa) |

**`FLOAT-038-A — TARGETED DELTA COMPLETE / CONVERGED`.**

## 16. Cambio incompatible del contrato

El contrato público de `POST` y `GET /treasury/bank-transactions` cambió **a
propósito**: `amount` y `commission` pasaron de número JSON a texto decimal, al
entrar y al salir. Lo autorizó el owner (`OQ-FLOAT-038-A-01`). El frontend del
repositorio se adaptó en el mismo cambio. Fuera del repositorio no hay inventario
de consumidores, así que no puede afirmarse que no existan: un cliente externo que
envíe número recibirá 422, y uno que lea número recibirá texto. El repositorio no
tiene registro de cambios ni política de versionado de API; el cambio queda
declarado en `contracts/api-contracts.md` §3.1, en OpenAPI, en las pruebas y en
`spec038-convergence.md` §15.
