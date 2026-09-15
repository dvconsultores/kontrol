# SPEC 038 · DELTA DIRIGIDO FLOAT-038-B — ARQUEO Y CIERRE DE CAJA EXACTOS

> Delta dirigido dentro de la **Spec 038 — Tesorería** (carpeta `006-tesoreria`).
> No reabre la 038 ni crea una Spec nueva. Hereda las decisiones cerradas en
> FLOAT-038-A (`spec038-bank-amount-decimal-delta.md`).
>
> **Veredicto: `FLOAT-038-B — TARGETED DELTA COMPLETE / CONVERGED`** (2026-09-15).
> La Spec 038 sigue `COMPLETE / CONVERGED`; esto es una reconvergencia dirigida.
> Evidencia en §13 y en `evidence/float-038-b/`.

## 0. Verificación física

| | |
|---|---|
| HEAD | `788eb48` (el esperado) |
| Rama | `develop` |
| Árbol | limpio |
| Servicios | caídos al empezar: un reinicio de la máquina (arranque 2026-09-15 03:40) vació `/tmp`. Reconstruidos con la receta documentada: PostgreSQL 16.2 en 55440 con `kmc`, `ke2e` (57 migraciones y semilla) y `kontrol_legacy` sembrada; ClamAV 1.4.3; backend 8000 y Vite 5173 |
| PostgreSQL | **16.2** → `ENVIRONMENT_BASELINE_DEVIATION` frente a 18.6 |

## 1. Identidad del dueño — resuelta

| Eslabón | Hallazgo |
|---|---|
| Símbolos | `ArqueoBody.counted_amount` · `arqueo_session` · `close_session` · `_session_expected` · `session_dict` |
| Ficheros | `treasury/api.py:123` · `treasury/service.py:275`, `:423`, `:467`, `:490` · `treasury/models.py:285` |
| Rutas | `POST /treasury/cash-sessions/{id}/arqueo` (`tesoreria:approve`) · `…/close` (`tesoreria:approve`); la sesión se devuelve también en `GET /cash-sessions`, `POST /cash-sessions`, `GET /cash-sessions/{id}`, `…/pre-close`, `…/reject` |
| Persistencia | `cash_sessions.opened_amount`, `counted_amount`, `expected_amount`, `difference` — `numeric(18,2)` en PostgreSQL; `Mapped[float]` en el ORM |
| Auditoría | `CASH_SESSION_ARCHED` y `CASH_SESSION_CLOSED` en `audit_events.after` (columna JSON) |
| Frontend | `modules/tesoreria/cajas/CajasPage.tsx` · `CashSessionSummary` en `api/types.ts` |
| Pruebas | `test_treasury.py · TestCajas`, `test_spec038_treasury.py · test_el_arqueo_no_arrastra_error_binario`, `test_mc_treasury_ab.py`; ningún E2E de cajas |
| Mapa · máster | `spec-equivalence-map.md:45` 038 ↔ `006-tesoreria`; fila 038 `COMPLETE / CONVERGED`; programación en `next-spec-decision.md` «FLOAT-038-B · Arqueo y cierre de caja» |

**Dueña canónica: Spec 038.** `OWNER_IDENTITY_CONFLICT = 0`.

## 2. La deuda, bien dicha

La errata de `spec038-convergence.md` §14 se conserva: **la resta del arqueo ya es
`Decimal` exacta** desde el ciclo de la 038 —`_money(counted_amount) - _money(expected)`—
y la defiende `test_el_arqueo_no_arrastra_error_binario`. No se «corrige» otra vez.

| Deuda real | Dónde |
|---|---|
| A · `counted_amount` entra como `float` | `ArqueoBody.counted_amount: float = Field(ge=0)` y la firma de `arqueo_session` |
| B · el cierre compara con épsilon | `close_session`: `diff = session.difference or 0.0` · `abs(diff) > 1e-6` |
| C · la auditoría degrada a `float` | `after={"expected": float(…), "counted": float(…), "difference": float(…)}` en el arqueo; `after={"difference": float(…)}` en el cierre |

## 3. Flujo de tipos antes del delta

| Capa | Tipo | Evidencia |
|---|---|---|
| Frontend | `Number(countedAmount) \|\| 0` | `CajasPage.tsx:78` |
| HTTP | número JSON | ídem |
| Pydantic | **`float`**, `ge=0` | `api.py:124` |
| Servicio | `counted_amount: float`; `_session_expected(...) -> float` que en realidad devuelve `Decimal` | `service.py:275`, `:423` |
| Diferencia | `_money(counted) - _money(expected)` — **`Decimal`**, contado − esperado | `service.py:432` |
| ORM | `Mapped[float]` sobre `Numeric(18, 2)` en las cuatro columnas | `models.py:294-297` |
| PostgreSQL | `numeric(18,2)` | `information_schema` en `ke2e` |
| Cierre | `abs(diff) > 1e-6` | `service.py:475` |
| Auditoría | `float(...)` en `after` | `service.py:440`, `:486` |
| Respuesta | `session_dict` devuelve `Decimal` crudo → `jsonable_encoder` → número; OpenAPI `{}` | `service.py:490` |
| Pantalla | `expected_amount.toFixed(2)`, `diff.toFixed(2)`, `difference ?? 0 !== 0` | `CajasPage.tsx` |

## 4. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-038-FLOAT-B-001 | `counted_amount` se recibe **solo como texto decimal**; un número JSON → 422 |
| FR-038-FLOAT-B-002 | escala y dígitos enteros de `cash_sessions.counted_amount` (`numeric(18,2)`); la regla actual `≥ 0` se conserva: cero sí, signo no. Exceso de escala → 422, sin redondeo |
| FR-038-FLOAT-B-003 | un conteo rechazado no cambia la sesión —estado, conteo, esperado, diferencia— ni emite `CASH_SESSION_ARCHED` |
| FR-038-FLOAT-B-004 | la diferencia sigue siendo `contado − esperado` en `Decimal`: misma fórmula, mismo signo |
| FR-038-FLOAT-B-005 | el cierre decide con **cero exacto**: diferencia distinta de cero sin aprobación → 409 `DIFFERENCE_NOT_APPROVED`; sin épsilon ni tolerancia |
| FR-038-FLOAT-B-006 | `CASH_SESSION_ARCHED` y `CASH_SESSION_CLOSED` guardan sus importes como texto decimal con las claves de siempre; hacia adelante, sin reescribir eventos |
| FR-038-FLOAT-B-007 | las rutas que devuelven la sesión de caja la devuelven con todos sus importes en texto —fondo, esperado, conteo, diferencia e importes de movimientos— y con modelo publicado en OpenAPI |
| FR-038-FLOAT-B-008 | servicio y ORM del arqueo en `Decimal`: firma de `arqueo_session`, retorno de `_session_expected`, anotación de las cuatro columnas |
| FR-038-FLOAT-B-009 | la pantalla envía el conteo como texto sin `Number`, lo muestra sin convertirlo y decide si hay diferencia con cero exacto sobre el texto |
| FR-038-FLOAT-B-010 | el cambio incompatible del contrato de la sesión se declara en contratos, OpenAPI, pruebas y convergencia |

## 5. `/speckit.clarify`

| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| 1 | Ruta exacta | `POST /treasury/cash-sessions/{id}/arqueo` y `…/close` | RESUELTA |
| 2 | Modelo de petición | `ArqueoBody{counted_amount: float ge=0, notes}` · `CloseSessionBody{difference_approved, approval_note}` | RESUELTA |
| 3 | Modelo de respuesta | ninguno: `session_dict` crudo | RESUELTA → FR-B-007 |
| 4 | Escala del conteo | `numeric(18,2)`: 2 decimales y 16 enteros, de la columna | RESUELTA |
| 5 | Campo persistido | `cash_sessions.counted_amount`, `expected_amount`, `difference` | RESUELTA |
| 6 | Tipo ORM | `Mapped[float]` sobre `Numeric(18, 2)` | RESUELTA — solo la anotación; sin migración |
| 7 | Origen del esperado | `_session_expected`: fondo + entradas − salidas, en `Decimal` con `_money` | RESUELTA |
| 8 | Fórmula de la diferencia | `_money(counted_amount) - _money(expected)` | RESUELTA — se conserva |
| 9 | Signo de la diferencia | positivo = sobrante; negativo = faltante | RESUELTA — se conserva |
| 10 | Dónde está el épsilon | `close_session` | RESUELTA |
| 11 | Evento de auditoría | `CASH_SESSION_ARCHED` (`expected`, `counted`, `difference`) · `CASH_SESSION_CLOSED` (`difference`, `approved`) | RESUELTA |
| 12 | Consumidores de la auditoría | **ninguno lee esos valores**: ni `audit/api.py` ni `audit/service.py`, ni `AuditoriaPage`, ni `ReportesAuditoriaPage`, ni ninguna prueba; `test_mc_treasury_ab` solo comprueba empresa y usuario del evento | RESUELTA — sin contrato externo |
| 13 | Entrada en pantalla | `MoneyInput` (texto) → `Number(countedAmount) \|\| 0` | RESUELTA → FR-B-009 |
| 14 | Presentación en pantalla | `toFixed(2)` y comparación numérica de la diferencia | RESUELTA → FR-B-009 |
| 15 | OpenAPI | petición `number`; respuesta `{}` | RESUELTA → FR-B-001, 007 |
| 16 | Permiso | `tesoreria:approve` en arqueo y cierre; sin cambio | RESUELTA |
| 17 | Contexto de empresa | `_owned(..., ctx.company_id)` en cada ruta; sin cambio | RESUELTA |
| 18 | Concurrencia | el cierre es una transición de estado (`PRE_CLOSED → CLOSED`); un segundo cierre es `INVALID_STATE_TRANSITION`; no hay idempotencia ni bloqueo optimista que preservar | RESUELTA — se prueba el doble cierre |

**No se reabre** `Decimal` frente a `float`, el texto decimal en el contrato público,
el rechazo por exceso de escala ni el cero exacto: son decisiones cerradas.

### Perímetro

| Dentro | Por qué |
|---|---|
| `counted_amount` de entrada | es la deuda A |
| todos los importes **de la respuesta** de la sesión | salen del mismo `session_dict` en las siete rutas: corregir solo el conteo dejaría el mismo objeto con dos políticas, el criterio que FLOAT-038-A aplicó a la comisión |
| anotación ORM de las cuatro columnas de la sesión | son los saldos que el arqueo lee y escribe |

| Fuera, sigue `OPEN` | Por qué |
|---|---|
| `SessionOpen.opened_amount` y `SessionMovementCreate.amount` de entrada, y la respuesta de `POST …/movements` | son otros contratos de petición, dos de los siete `float` restantes; no impiden cerrar B |
| anotación ORM de `CashSessionMovement.amount` | pertenece al contrato de movimientos |

**MATERIAL OQ = 0.**

## 6. Contrato resultante

Detalle en `contracts/api-contracts.md` §2.1.

| | Antes | Después |
|---|---|---|
| Petición `counted_amount` | `number ≥ 0` | `string`, `^[0-9]+(\.[0-9]{1,2})?$`, `≥ 0`, hasta 16 enteros |
| Respuesta `opened_amount`, `expected_amount` | número | `string` con dos decimales |
| Respuesta `counted_amount`, `difference` | número o `null` | `string` con dos decimales o `null` |
| Respuesta `movements[].amount` | número | `string` con dos decimales |
| Auditoría | números | texto decimal |
| Compatibilidad | — | **incompatible y autorizada** por las decisiones heredadas |

## 7. `/speckit.plan`

| Ola | Contenido | Tareas |
|---|---|---|
| W01-W02 | Auditoría del flujo y artefactos | T-FB-01 |
| W03-W04 | `counted_amount` solo texto, con el mismo helper | T-FB-02, T-FB-03 |
| W05-W06 | Servicio y anotación ORM | T-FB-04, T-FB-05 |
| W07 | Cero exacto en el cierre | T-FB-06 |
| W08 | Auditoría en texto | T-FB-07 |
| W09, W12 | Respuesta y OpenAPI | T-FB-08 |
| W10-W11 | Frontend: envío y presentación | T-FB-11, T-FB-12, T-FB-13 |
| W13-W15 | Pruebas dirigidas de backend, auditoría y frontend | T-FB-09, T-FB-10, T-FB-14 |
| W16-W17 | Mutaciones y guardas | T-FB-09, T-FB-14, T-FB-16 |
| W18-W19 | Tesorería y consumidores; FLOAT-038-A | T-FB-17 |
| W20-W22 | Regresión completa sola, frontend y E2E | T-FB-15, T-FB-18, T-FB-19, T-FB-20 |
| W23-W25 | Analyze final, trazabilidad y convergencia | T-FB-21 |

| Tema | Decisión |
|---|---|
| Helper de entrada | se reutiliza `texto_decimal` de `app/shared/money.py`; se le añade `admite_cero` para la regla `≥ 0`. No hay un segundo validador |
| Autoridad de escala | la columna `CashSession.counted_amount` |
| Cero exacto | `_money(session.difference) != 0`: `_money` es el helper canónico y `None` sigue valiendo cero, como hacía `or 0.0` |
| Auditoría | `str(_money(...))`, el mismo formateador de las respuestas de la 038 |
| Respuesta | modelos `CashSessionOut`, `CashSessionPage`, `CashSessionMovementOut` con el tipo de salida de FLOAT-038-A |
| Frontend | `toDecimalString` para enviar; `formatMoney` para mostrar; `isZeroDecimal` nuevo en `lib/decimal.ts` para decidir sin `Number` |
| Varianza en pantalla | la pantalla no calcula la diferencia: muestra la del servidor |

## 8. CONSTITUTION GATE

| Puerta | Diseño |
|---|---|
| G-B-01 dueña 038 | **PASS** |
| G-B-02 sin Spec nueva | **PASS** |
| G-B-03 resta intacta | **PASS** — FR-B-004 |
| G-B-04 `counted_amount` en `Decimal` | **PASS** |
| G-B-05 política de texto heredada | **PASS** |
| G-B-06 sin número JSON como autoridad | **PASS** |
| G-B-07 exceso de escala rechazado | **PASS** |
| G-B-08 cero exacto | **PASS** |
| G-B-09 sin épsilon | **PASS** |
| G-B-10 sin `float` en la auditoría | **PASS** |
| G-B-11 auditoría en texto | **PASS** |
| G-B-12 sin otra limpieza de tesorería | **PASS** — §5 perímetro |
| G-B-13 sin cambio de esquema | **PASS** |
| G-B-14 OpenAPI igual a la ejecución | **PASS** |
| G-B-15 multiempresa intacto | **PASS** |
| G-B-16 mutaciones con semántica | **PASS** en diseño — §9 |

**16 PASS · 0 condicionadas.**

## 9. `/speckit.checklist`

- [x] `counted_amount` localizado · [x] `close_session` localizado · [x] resta confirmada `Decimal` · [x] fórmula conservada
- [x] épsilon localizado · [x] `float` de la auditoría localizado · [x] inventario de consumidores de la auditoría: 0
- [x] contrato de petición conocido · [x] contrato de respuesta conocido · [x] pantalla conocida
- [x] escala confirmada en ORM y PostgreSQL · [x] reutilización del helper confirmada · [x] política de texto reutilizada
- [x] rechazo del número JSON definido · [x] rechazo del exceso de escala definido · [x] regla del cero exacto definida
- [x] representación de la auditoría definida · [x] pruebas definidas · [x] mutaciones con semántica definidas
- [x] regresión de la dueña definida · [x] sin migración · [x] MATERIAL OQ = 0 · [x] UNKNOWN = 0 · [x] trazabilidad 100 %

Mutaciones previstas:

| ID | Mutación | Fixture | Debe caer |
|---|---|---|---|
| M038-B-01 | `counted_amount: float` | `"1234567890123456.78"` | exactitud en base, respuesta y auditoría |
| M038-B-02 | cero exacto → `abs(diferencia) > Decimal("0.01")` | esperado `"100.00"`, contado `"99.99"` | el cierre sin aprobación debe dar 409 |
| M038-B-03 | `float(...)` de vuelta en la auditoría | `"1234567890123456.78"` | la auditoría debe decir el texto exacto |
| M038-B-04 | sin rechazo por escala | `"100.005"` | 422 y sesión intacta |
| M038-B-05 | `Number(countedAmount)` en la pantalla | `"1234567890123456.78"` | el cuerpo debe llevar texto |

El `1e-6` literal no se usa como mutación: con importes de escala 2 no cambia
ningún resultado, y una mutación que no se observa no cuenta.

## 10. `/speckit.tasks`

| ID | Requisito | Ficheros | Depende | Cambio | Aceptación y prueba |
|---|---|---|---|---|---|
| T-FB-01 | 001-010 | este documento, `spec.md`, `clarifications.md`, `research.md`, `contracts/api-contracts.md` | — | requisitos, perímetro, contrato | revisión |
| T-FB-02 | 002 | `app/shared/money.py` | — | `admite_cero` en `texto_decimal` | pruebas de cero · FLOAT-038-A intacto |
| T-FB-03 | 001-002 | `treasury/api.py` | 02 | `ArqueoBody.counted_amount` con el helper y la columna | entrada · M-01, M-04 |
| T-FB-04 | 008 | `treasury/service.py` | — | `arqueo_session(counted_amount: Decimal)`; `_session_expected -> Decimal` | guarda AST |
| T-FB-05 | 008 | `treasury/models.py` | — | `Mapped[Decimal]` en cuatro columnas | paridad |
| T-FB-06 | 005 | `treasury/service.py` | — | cero exacto en `close_session` | un céntimo · M-02 |
| T-FB-07 | 006 | `treasury/service.py` | — | auditoría con `str(_money(...))` | auditoría · M-03 |
| T-FB-08 | 007 | `treasury/api.py`, `treasury/service.py` | — | modelos de sesión y `response_model` en las siete rutas; `session_dict` en texto | respuesta · OpenAPI |
| T-FB-09 | 001-008 | `tests/test_spec038_float_b.py` | 02-08 | pruebas dirigidas y guardas | verde · mutaciones rojas |
| T-FB-10 | 001, 004 | `test_mc_treasury_ab.py`, `test_treasury.py` | 03, 04 | llamantes con texto o `Decimal`; aserciones iguales | regresión |
| T-FB-11 | 009 | `src/lib/decimal.ts` | — | `isZeroDecimal` | `decimal.test.ts` |
| T-FB-12 | 009 | `src/api/types.ts` | — | `CashSessionSummary` y `CashSessionMovement` en texto | `tsc` |
| T-FB-13 | 009 | `CajasPage.tsx` | 11, 12 | envío con `toDecimalString`; `formatMoney`; `isZeroDecimal` | prueba de pantalla · M-05 |
| T-FB-14 | 009 | `src/modules/tesoreria/arqueo-caja.test.tsx` | 13 | envío exacto, escala, diferencia de un céntimo, guarda | verde · M-05 roja |
| T-FB-15 | 001, 003, 005, 009 | `e2e/treasury.spec.ts` | 03-13 | contrato por API y pantalla de arqueo | tres navegadores |
| T-FB-16 | 001-009 | `evidence/float-038-b/` | 09, 14 | cinco mutaciones con fallo real | rojas y restauradas |
| T-FB-17 | 004, 005 | suites de tesorería y FLOAT-038-A | 03-08 | regresión dirigida | verde |
| T-FB-18 | todos | regresión completa | 17 | sola | 0 fallos, 0 errores, 0 omisiones inesperadas |
| T-FB-19 | 009 | frontend | 14 | Vitest, `tsc`, ESLint, build | EXIT 0 |
| T-FB-20 | 009 | E2E canónico | 15, 18 | tres navegadores, sin nada en paralelo | verde |
| T-FB-21 | 010 | convergencia, trazabilidad, máster, decisión siguiente | 18-20 | analyze final y cierre | §15 |

## 11. `/speckit.analyze` previo a implementar

| Búsqueda | Hallazgo | Tarea |
|---|---|---|
| `counted_amount: float` | 2 (esquema y servicio) | T-FB-03, T-FB-04 |
| `float(counted…)` · `float(expected…)` · `float(difference)` | 4 en la auditoría | T-FB-07 |
| `abs(diff) > 1e-6` | 1 | T-FB-06 |
| `isclose` · `math.isclose` | 0 | — |
| número en la respuesta · OpenAPI `{}` | 7 rutas | T-FB-08 |
| `Number(countedAmount)` · `toFixed` · comparación numérica de la diferencia | 1 · 3 · 3 | T-FB-13 |
| `parseFloat` | 0 | — |
| `Mapped[float]` sobre `Numeric` | 4 en la sesión | T-FB-05 |
| redondeo de PostgreSQL · cuantización local nueva | 0 · 0 — `_money` ya existía en la resta y no se añade otra | — |
| cambio de fórmula o de signo | ninguno previsto | FR-B-004 |
| otros siete `float` · FLOAT-038-A | fuera; FLOAT-038-A se reutiliza y se regresa | T-FB-17 |

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| ORPHAN REQUIREMENTS | 0 |
| ORPHAN TASKS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRAZABILIDAD | 100 % — 10 requisitos, 21 tareas, 5 mutaciones |

**Autorización expresa consumida.** Se procede a `/speckit.implement`.

## 12. `/speckit.implement`

| Capa | Antes | Después | Fichero |
|---|---|---|---|
| Pantalla · envío | `Number(countedAmount) \|\| 0` | `toDecimalString(countedAmount)`; más de dos decimales se avisa y no se envía | `CajasPage.tsx` |
| HTTP · petición | número JSON | **texto decimal**; un número → 422 | — |
| Pydantic | `counted_amount: float = Field(ge=0)` | `ConteoDeCaja` = `texto_decimal(counted_amount, positivo=True, admite_cero=True)` | `treasury/api.py` · `app/shared/money.py` |
| Servicio | `counted_amount: float`; `_session_expected -> float` | `Decimal` en los dos | `treasury/service.py` |
| Diferencia | `_money(counted_amount) - _money(expected)` | **sin cambio** | `treasury/service.py` |
| Cierre | `abs(session.difference or 0.0) > 1e-6` | `_money(session.difference) != 0` | `treasury/service.py` |
| ORM | `Mapped[float]` en cuatro columnas | `Mapped[Decimal]`; columnas sin cambio | `treasury/models.py` |
| PostgreSQL | `numeric(18,2)` | `numeric(18,2)` — **sin migración** | — |
| Auditoría | `float(...)` | `str(_money(...))`, mismas claves | `treasury/service.py` |
| Respuesta | `Decimal` crudo → número; OpenAPI `{}` | texto con dos decimales; `CashSessionOut`, `CashSessionPage`, `CashSessionMovementOut` en siete rutas | `treasury/api.py` · `treasury/service.py` |
| Pantalla · tipos y presentación | `number`; `toFixed(2)`; `difference ?? 0 !== 0` | `string`; `formatMoney`; `isZeroDecimal` | `api/types.ts` · `lib/decimal.ts` · `CajasPage.tsx` |

**Defecto preexistente corregido dentro del camino.** En `CajasPage.tsx`, el botón
«arqueo» solo aparece con la sesión en `OPEN`, pero el panel solo mostraba el
formulario de conteo con `ARCHED`: el arqueo era **inalcanzable** desde la pantalla,
y el título decía «Cierre» a una sesión abierta. Sin corregirlo no había camino de
pantalla que probar. Se cambiaron la condición (`OPEN`) y el título; nada más.

Llamantes adaptados al contrato, con aserciones igual de estrictas:
`test_mc_treasury_ab.py` (2 conteos en texto), `test_treasury.py` (3 conteos en
`Decimal`, 3 comparaciones de `expected_amount` con su texto exacto).

## 13. Evidencia

### Pruebas dirigidas

| Ámbito | Resultado |
|---|---|
| Backend · `tests/test_spec038_float_b.py` — tipo, texto exacto, 18 dígitos en base, respuesta y auditoría, número JSON, escala, forma léxica, cero, fórmula y signo, cuadre exacto, un céntimo de menos y de más, doble cierre, auditoría, respuesta completa, OpenAPI, empresa, tres guardas | **33/33** |
| Backend · regresión dirigida: `test_spec038_float_a.py`, `test_treasury.py`, `test_spec038_treasury.py`, `test_mc_treasury_ab.py`, `test_n10_cross_company_writes.py` | verde |
| Frontend · `arqueo-caja.test.tsx` (7) · `decimal.test.ts` (+2) | **9/9** nuevas |
| E2E · `treasury.spec.ts` — contrato por API (número, `100.001`, `100.005` → 422 sin tocar la sesión; `99.99` → `-0.01` → 409 sin aprobar; cuadre exacto cierra) y pantalla (envía `"1234567890123456.78"`, muestra `-0,01`, no deja cerrar sin aprobar) | **6/6** en Chromium, Firefox y WebKit |

### Mutaciones

| ID | Mutación | Fixture | Fallo real | Restaurada |
|---|---|---|---|---|
| M038-B-01 | `counted_amount: float = Field(ge=0)` | `"1234567890123456.78"`; `100.00` y `100` como número | la respuesta dice `1234567890123456.80`; los números entran con 200 | sí |
| M038-B-02 | `abs(diferencia) > Decimal("0.01")` en el cierre | esperado `100.00`, contado `99.99` y `100.01` | la caja cierra con 200 sin aprobación | sí |
| M038-B-03 | `"counted": float(...)` en la auditoría | `"1234567890123456.78"`, `"99.99"` | la auditoría guarda un número y no el texto | sí |
| M038-B-04 | sin rechazo por escala | `"100.001"`, `"100.005"`, `"0.005"`, `"100.000"` | entran con 200 y PostgreSQL redondea | sí |
| M038-B-05 | `counted_amount: Number(conteo)` en la pantalla | `"1234567890123456.78"` tecleado | el cuerpo lleva `number` | sí |

El literal `1e-6` no se usó como mutación: con escala 2 no cambia ningún resultado.

### Paridad, migración e instalación limpia

| | |
|---|---|
| ORM ↔ PostgreSQL en `cash_sessions`, `cash_session_movements` y `bank_transactions` | **0** diferencias; heredadas globales sin cambio (`paridad.txt`) |
| Migración | **no**: solo cambian anotaciones |
| Instalación limpia | no obligatoria; la base del E2E se reinstaló de cero: 57 migraciones, exit 0 |

### Regresión de backend, sola

| | |
|---|---|
| Entorno | PostgreSQL 16.2 · `TZ=UTC` (declarado por CLOCK-013; la ejecución fue a las 17:41 CEST, fuera de su ventana) |
| Total | 1577 |
| Pasan | **1569** |
| Fallan · errores | **0 · 0** |
| Omitidas | 8 — S3 real sin configurar, las esperadas |
| Omisiones inesperadas · avisos | 0 · 0 |
| Exit | 0 |

### Frontend

| | |
|---|---|
| Vitest | **368/368** en tres ejecuciones seguidas, sin errores no capturados |
| `tsc` · ESLint · build | exit 0 · 0 · 0 |

### E2E canónico, tres navegadores, después de la regresión

| | |
|---|---|
| Pruebas | **255/255** (85 por navegador) |
| FLOAT-038-A y FLOAT-038-B | 12/12 |
| Trazas y respuestas 500 en el backend | 0 · 0 |

## 14. Clasificación de lo encontrado

| Hallazgo | Clasificación | Qué se hizo |
|---|---|---|
| Formulario de arqueo inalcanzable en `CajasPage.tsx` | `PREEXISTING`, dentro del camino objetivo | corregido (§12) |
| Tres aserciones de `test_treasury.py` comparaban `expected_amount` con un número | adaptación al contrato, no defecto | comparan con el texto exacto |
| Reinicio de la máquina: `/tmp` vacío, servicios caídos | `EXTERNAL_ENVIRONMENT` | entorno reconstruido con la receta documentada |
| PostgreSQL 16.2 | `ENVIRONMENT_BASELINE_DEVIATION` | declarado |

| Clase | Número |
|---|---|
| NEW_REGRESSION_FLOAT_038_B | **0** |
| PREEXISTING_SEALED | 0 abiertos (1 corregido en el camino) |
| TEST_DEFECT | 0 |
| EXTERNAL_ENVIRONMENT | 1 |
| ENVIRONMENT_BASELINE_DEVIATION | 1 |
| OWNER_DEPENDENCY · OWNER_IDENTITY_CONFLICT_DEBT · MATERIAL_DECISION_REQUIRED | 0 |
| UNKNOWN | **0** |

## 15. `/speckit.analyze` final y convergencia

| Búsqueda | Resultado |
|---|---|
| `counted_amount` `float` en esquema, servicio u ORM | 0 (guardas AST) |
| número JSON aceptado · escala mayor aceptada | no · no (M-01, M-04 por contraste) |
| `1e-6` · `isclose` · tolerancia en el cierre | 0 · 0 · 0 (guarda AST; M-02) |
| `float(...)` en auditoría, arqueo, cierre o sesión | 0 (guarda AST; M-03) |
| respuesta `Decimal` → `float` · OpenAPI `{}` en la sesión | 0 · 0 |
| `Number(countedAmount)` · `parseFloat` · `toFixed` en la pantalla de cajas | 0 · 0 · 0 (M-05) |
| fórmula o signo de la diferencia cambiados | no — `_money(counted_amount) - _money(expected)` intacta |
| entradas `opened_amount` y de movimiento tocadas | no |
| FLOAT-038-A regresada | no — su suite y su E2E en verde con el helper ampliado |

| | |
|---|---|
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 |
| ORPHAN REQUIREMENTS · ORPHAN TASKS | 0 · 0 |
| MATERIAL OQ · UNKNOWN | 0 · 0 |
| TRAZABILIDAD | 100 % — 10 requisitos, 21 tareas, 5 mutaciones (`spec038-traceability-matrix.md`) |

Puerta de convergencia dirigida:

| Condición | |
|---|---|
| conteo de entrada en texto · `Decimal` dentro · sin `float` en el camino | ✔ |
| número JSON aceptado · exceso de escala aceptado · redondeo silencioso | no · no · 0 |
| diferencia `Decimal` · fórmula cambiada | ✔ · no |
| cero exacto · épsilon · tolerancia | sí · 0 · 0 |
| auditoría sin `float` y con texto exacto | ✔ |
| rechazo sin cambio de estado ni auditoría de arqueo | ✔ |
| pantalla sin `Number` ni `parseFloat` | ✔ |
| OpenAPI igual a la ejecución · FLOAT-038-A intacto · multiempresa intacto | ✔ · ✔ · ✔ |
| deriva ORM/base en el ámbito · migración | 0 · ninguna |
| mutaciones que caen | 5/5 |
| backend 0/0 · frontend y build exit 0 · E2E verde · omisiones inesperadas 0 | ✔ |

**`FLOAT-038-B — TARGETED DELTA COMPLETE / CONVERGED`.**

## 16. Cambio incompatible del contrato

El contrato de la sesión de caja cambió **a propósito**: `counted_amount` se envía
como texto decimal, y todos los importes de la sesión —en las siete rutas que la
devuelven— salen como texto. Lo autorizan las decisiones heredadas de FLOAT-038-A.
El frontend del repositorio se adaptó en el mismo cambio. Fuera del repositorio no
hay inventario de consumidores: un cliente que envíe el conteo como número recibirá
422, y uno que lea números recibirá texto. Los eventos de auditoría nuevos guardan
texto; los anteriores no se reescriben. Declarado en `contracts/api-contracts.md`
§2.1, en OpenAPI, en las pruebas y en `spec038-convergence.md` §16.
