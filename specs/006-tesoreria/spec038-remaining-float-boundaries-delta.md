# SPEC 038 · DELTA DIRIGIDO FLOAT-038-C — LAS SEIS FRONTERAS `float` RESTANTES

> Reconvergencia dirigida dentro de la Spec 038, ya `COMPLETE / CONVERGED`. No abre
> Spec nueva ni reabre ninguna decisión monetaria cerrada. Hereda entera la política
> ratificada en FLOAT-038-A y FLOAT-038-B y la aplica a las seis fronteras que aquellos
> dos deltas dejaron fuera por alcance.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `ab02bba` / `ab02bba` — coinciden |
| `COMMITS_AFTER_AB02BBA` | **0** |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | un fichero sin confirmar: `KONTROL_MASTER_COMPLETENESS_AUDIT.md` |
| PostgreSQL | 16.2 · objetivo 18.6 → `ENVIRONMENT_BASELINE_DEVIATION` |
| Alembic | 57 migraciones, cabeza única `0057_spec047_notifications` |

`KONTROL_MASTER_COMPLETENESS_AUDIT.md` sigue siendo el artefacto de la auditoría previa,
**ajeno a este delta**: no se borra, no se mueve y no entra en el commit.

## 1. Dueña canónica

**SPEC 038 — Tesorería**, cuyos artefactos viven en `specs/006-tesoreria`. Los seis
símbolos están en `app/modules/treasury/`, módulo que el mapa código↔Spec asigna a
013/038/041 y cuyo dinero gobierna la 038.

`OWNER_CONFLICT = 0`. Matiz declarado: el sexto símbolo pertenece al flujo **IGTF**,
cuya norma fiscal es de la **041** y sigue bloqueada por `D0-07`. Este delta toca la
**representación** del importe que entra, no la regla que lo grava (§9).

## 2. Inventario físico de las seis fronteras

Recontado sobre el código, no sobre la lista heredada. `TARGET_FLOAT_BOUNDARIES = 6`,
todas en `app/modules/treasury/api.py`:

| # | Símbolo | Línea | Regla de signo y cero **de hoy** |
|---:|---|---:|---|
| 1 | `SessionOpen.opened_amount` | 111 | `float = 0.0` — **ninguna restricción**: admite cero, admite negativo |
| 2 | `SessionMovementCreate.amount` | 116 | `Field(gt=0)` — estrictamente positivo |
| 3 | `TransferCreate.amount` | 227 | `Field(gt=0)` — estrictamente positivo |
| 4 | `ReconciliationCreate.opening_balance` | 241 | `float \| None` — opcional, cualquier signo |
| 5 | `ReconciliationCreate.closing_balance` | 242 | `float \| None` — opcional, cualquier signo |
| 6 | `IgftEvaluateBody.amount` | 272 | `Field(gt=0)` — estrictamente positivo |

### Lo demás que apareció, clasificado

| Hallazgo | Clase | Decisión |
|---|---|---|
| `Mapped[float]` en `cash_session_movements.amount`, `treasury_transfers.amount`, `reconciliations.opening/closing_balance`, `igft_events.amount` | **mismo camino** de los targets 2–6 | Se corrigen con su frontera: la anotación miente sobre una columna `Numeric` |
| `igft_events.igft_amount: Mapped[float]` y el cálculo `round(amount * rate * snapshot, 2)` | **mismo camino atómico** del target 6 | Entra: con el importe en `Decimal`, `Decimal * float` es un `TypeError`. Cambiarlo es obligatorio para que el target 6 exista, no una ampliación |
| `_rate_snapshot` devuelve `1.0` literal para VED/VES | mismo camino atómico del target 6 | Entra por la misma razón: un `Decimal` no se multiplica por un `float` |
| `reconciliations.match_score: Float` | **no monetario** (puntuación de coincidencia) | Fuera de alcance |
| `rate = float(params.get("rate"))` de la regla IGTF | tasa, no dinero, pero factor del target 6 | Se lee como `Decimal` sin cambiar la fórmula. La **regla** fiscal no se toca |
| `cash_sessions.opened_amount` ya es `Mapped[Decimal]` | cerrado por FLOAT-038-B | No se reabre |

**No aparece un séptimo `float` monetario** fuera de esos caminos.

## 3. Flujo de tipos, medido

| Target | HTTP hoy | Servicio hoy | ORM hoy | DB real | Respuesta hoy | Frontend hoy |
|---|---|---|---|---|---|---|
| 1 `opened_amount` | `float` | `float` | **`Decimal`** | `numeric(18,2)` NOT NULL | ya texto (`session_dict`) | `Number(openedAmount) \|\| 0` |
| 2 movimiento `amount` | `float` | `float` | `float` | `numeric(18,2)` NOT NULL | ya texto (`session_dict`) | **sin interfaz** |
| 3 transferencia `amount` | `float` | `float` | `float` | `numeric(18,2)` NOT NULL | número crudo (`transfer_dict`) | `Number(amount) \|\| 0` |
| 4 `opening_balance` | `float\|None` | `float\|None` | `float\|None` | `numeric(18,2)` NULL | número crudo | **sin interfaz**: la pantalla no envía saldos |
| 5 `closing_balance` | `float\|None` | `float\|None` | `float\|None` | `numeric(18,2)` NULL | número crudo | **sin interfaz** |
| 6 IGTF `amount` | `float` | `float` | `float` | `numeric(18,2)` NOT NULL | número crudo (`igft_event_dict`) | `Number(amount) \|\| 0` y lee `igft_amount: number` |

**ORM ↔ DB**: ninguna contradicción de precisión o escala. Los ocho campos implicados
son `numeric(18,2)` salvo `rate_snapshot`, que es `numeric(14,6)` y no es dinero.
**`SCHEMA_CONTRACT_DRIFT = 0` · migración esperada: ninguna.**

## 4. `/speckit.specify`

| ID | Requisito | Prioridad |
|---|---|---|
| FR-038-FLOAT-C-001 | `SessionOpen.opened_amount` cruza HTTP como **texto decimal**, se convierte una sola vez a `Decimal` y se persiste sin pasar por `float` | P0 |
| FR-038-FLOAT-C-002 | `SessionMovementCreate.amount` cumple la misma política **conservando** su semántica de dirección (`IN`/`OUT`/`ADJUST`) y su regla `> 0` | P0 |
| FR-038-FLOAT-C-003 | `TransferCreate.amount` cumple la política exacta sin alterar origen, destino, moneda ni las comprobaciones de la transferencia | P0 |
| FR-038-FLOAT-C-004 | `ReconciliationCreate.opening_balance` es exacto, sigue siendo opcional y **conserva el signo** | P0 |
| FR-038-FLOAT-C-005 | `ReconciliationCreate.closing_balance`, ídem | P0 |
| FR-038-FLOAT-C-006 | `IgftEvaluateBody.amount` es exacto **sin alterar la fórmula IGTF, la tasa, las exenciones ni la selección de regla** | P0 |
| FR-038-FLOAT-C-007 | Un número JSON crudo **no es válido** en ninguna de las seis fronteras públicas | P0 |
| FR-038-FLOAT-C-008 | El exceso de escala produce **422** y **efecto económico cero** | P0 |
| FR-038-FLOAT-C-009 | Las respuestas y auditorías de esos caminos no degradan dinero a `float`: salen como texto decimal | P0 |
| FR-038-FLOAT-C-010 | Ningún consumidor de interfaz usa `Number()` ni `parseFloat()` como autoridad del valor enviado | P0 |
| FR-038-FLOAT-C-011 | La implementación **reutiliza** `app/shared/money.py` y `lib/decimal.ts`; no se crea un segundo contrato monetario | P0 |
| FR-038-FLOAT-C-012 | FLOAT-038-A y FLOAT-038-B siguen verdes | P0 |

## 5. `/speckit.clarify`

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | ¿Siguen existiendo los seis? | Sí, verificados uno a uno en el código (§2) | No |
| 2 | ¿Alguno se corrigió de paso? | No. `opened_amount` tiene el ORM ya en `Decimal` por FLOAT-038-B, pero su frontera HTTP sigue en `float` | No |
| 3 | ¿Alguno no es monetario? | Los seis lo son. `match_score` y el `rate` de la regla no lo son y quedan fuera | No |
| 4 | Escala real por campo | `numeric(18,2)` en los seis, leída de PostgreSQL, no supuesta | No |
| 5 | Regla de signo de `opened_amount` | **Hoy no hay ninguna**: ni Pydantic, ni servicio, ni `CheckConstraint`. Se **preserva** tal cual (`positivo=False`) y se registra la observación | No |
| 6 | Regla de signo de los movimientos | `> 0`, y además el servicio lo revalida. Se preserva | No |
| 7 | Regla de signo de la transferencia | `> 0`, revalidada en el servicio. Se preserva | No |
| 8 | Regla de signo de los saldos de conciliación | Cualquier signo, opcional. Se preserva: un saldo bancario puede ser negativo | No |
| 9 | Regla de signo del importe IGTF | `> 0`, revalidada en el servicio. Se preserva | No |
| 10 | ¿El cero es válido? | En 1, 4 y 5 sí; en 2, 3 y 6 no. Reglas heredadas, no modificadas | No |
| 11 | ¿Cómo salen al cliente? | 1 y 2 ya salen como texto (FLOAT-038-B). 3, 4, 5 y 6 salen como número crudo: pasan a texto | No |
| 12 | ¿Es eso ruptura de contrato? | Sí, del mismo tipo y por la misma política que el owner ya cerró en `OQ-FLOAT-038-A-01`. **No es OQ nueva** | No |
| 13 | Auditoría | Ninguno de los seis flujos escribe eventos de auditoría monetarios propios; la sesión de caja ya los emite en texto desde B | No |
| 14 | Consumidores de interfaz | Cajas (apertura), Transferencias e IGTF usan `Number(...)`. Movimientos de caja y saldos de conciliación **no tienen interfaz**; se dirá así, sin fingir cobertura | No |
| 15 | OpenAPI | Los seis pasan a `type: string` con patrón; las respuestas tocadas, también | No |
| 16 | Permisos y alcance | Sin cambio: mismos `require_permission`, mismo `CompanyContext` | No |
| 17 | ¿Hace falta migración? | **No**: las columnas ya son `Numeric` con la escala correcta | No |
| 18 | ¿Se toca la fórmula IGTF? | **No.** La expresión y su `round(..., 2)` se conservan; solo dejan de mezclar `float` con `Decimal` | No |
| 19 | ¿Y el algoritmo de conciliación? | No se toca nada de emparejamiento, puntuación ni liquidación | No |
| 20 | ¿`igft_amount` entra? | Sí, por necesidad aritmética: es el resultado de multiplicar el target. Sin él, `Decimal * float` revienta | No |

**MATERIAL OQ = 0 · UNKNOWN = 0.** El ciclo continúa.

## 6. `/speckit.plan`

`W01` checkpoint · `W02` inventario de los seis · `W03` mapa de tipos · `W04` escala real en
PostgreSQL · `W05` reglas de signo · `W06` reutilización del helper · `W07`–`W12` los seis
targets · `W13` respuestas y OpenAPI · `W14` auditoría · `W15` consumidores de interfaz ·
`W16` paridad ORM · `W17` efecto cero del inválido · `W18` pruebas dirigidas de backend ·
`W19` pruebas dirigidas de frontend · `W20` regresión de A y B · `W21` multiempresa y
permisos · `W22` mutaciones · `W23` guardas estáticas · `W24` regresión completa ·
`W25` regresión de frontend · `W26` E2E de tesorería · `W27` analyze final · `W28`
trazabilidad · `W29` convergencia dirigida.

## 7. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G038-C-01 | Dueña resuelta | **PASA** |
| G038-C-02 | Seis targets inventariados | **PASA** — 6/6 |
| G038-C-03 | Política A/B heredada, no reabierta | **PASA** |
| G038-C-04 | Escala real conocida por campo | **PASA** — leída de PostgreSQL |
| G038-C-05 | Regla de signo conocida por campo | **PASA** — tres reglas distintas, preservadas |
| G038-C-06 | Sin cambio de fórmula ni de regla de negocio | **PASA** |
| G038-C-07 | Dinero público en texto | **PASA** |
| G038-C-08 | Número JSON crudo rechazado | **PASA** |
| G038-C-09 | Dinero interno en `Decimal` | **PASA** |
| G038-C-10 | ORM `Decimal` donde la base es `Numeric` | **PASA** |
| G038-C-11 | Exceso de escala → 422 | **PASA** |
| G038-C-12 | Redondeo silencioso | **PASA** — 0 |
| G038-C-13 | Entrada inválida sin efecto económico | **PASA** |
| G038-C-14 | Contrato de respuesta alineado | **PASA** |
| G038-C-15 | Sin `float(...)` monetario en el camino | **PASA** |
| G038-C-16 | Sin autoridad numérica en el frontend | **PASA** |
| G038-C-17 | Sin cambio de regla fiscal | **PASA** — `D0-07` sigue abierta |
| G038-C-18 | Sin limpieza ajena de tesorería | **PASA** |
| G038-C-19 | Sin migración salvo necesidad probada | **PASA** — ninguna |
| G038-C-20 | Multiempresa preservada | **PASA** |
| G038-C-21 | Regresión de A preservada | **PASA** |
| G038-C-22 | Regresión de B preservada | **PASA** |
| G038-C-23 | Mutaciones significativas | **PASA** — 8 |
| G038-C-24 | Material OQ = 0 | **PASA** |
| G038-C-25 | UNKNOWN = 0 | **PASA** |
| G038-C-26 | Trazabilidad 100 % | **PASA** |

## 8. `/speckit.tasks`

| ID | Tarea | Fichero | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | `SessionOpen.opened_amount` → texto exacto; firma del servicio en `Decimal` | `treasury/api.py`, `service.py` | C-001 | M038-C-01 |
| T-02 | Movimiento de caja: frontera, servicio y ORM | `api.py`, `service.py`, `models.py` | C-002 | M038-C-02 |
| T-03 | Transferencia: frontera, servicio, ORM y respuesta | ídem | C-003, C-009 | M038-C-03 |
| T-04 | Conciliación: los dos saldos, servicio, ORM y respuesta | ídem | C-004, C-005, C-009 | M038-C-04 |
| T-05 | IGTF: frontera, servicio, ORM, cálculo sin mezcla de tipos y respuesta | ídem | C-006, C-009 | M038-C-05 |
| T-06 | Modelos de salida y OpenAPI de los caminos tocados | `api.py` | C-009 | — |
| T-07 | Interfaz: cajas, transferencias e IGTF dejan de usar `Number()` | `CajasPage.tsx`, `TransferenciasPage.tsx`, `IgftPage.tsx`, `api/types.ts` | C-010 | M038-C-07 |
| T-08 | Pruebas dirigidas de backend, nueve casos por campo | `tests/test_spec038_float_c.py` | todos | todas |
| T-09 | Pruebas dirigidas de frontend sobre el cuerpo real | `src/modules/tesoreria/*.test.tsx` | C-010 | M038-C-07 |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 9. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---:|
| BLOCKER / CRITICAL | 0 / 0 |
| CONTRADICTIONS | 0 |
| OWNER_CONFLICT | 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRACEABILITY | 100 % |

Se consume la autorización expresa y se implementa.

## 10. `/speckit.implement`

| Fichero | Cambio |
|---|---|
| `treasury/api.py` | Cinco alias de entrada y tres de salida sobre `app/shared/money.py`; los seis campos pasan a texto decimal; `TreasuryTransferOut` y `TreasuryTransferPage` declaran el importe como texto |
| `treasury/service.py` | Firmas en `Decimal`; `_rate_snapshot` devuelve `Decimal` y su uno de VED/VES deja de ser `1.0`; el IGTF calcula con los mismos factores sin mezclar tipos; transferencia, conciliación e IGTF serializan su dinero como texto |
| `treasury/models.py` | Seis anotaciones `Mapped[float]` sobre columnas `Numeric` pasan a `Decimal`; `match_score`, que es `Float` de verdad y no es dinero, no se toca |
| `CajasPage.tsx`, `TransferenciasPage.tsx`, `IgftPage.tsx`, `api/types.ts` | `Number(...)` deja de ser autoridad del valor enviado; los importes se muestran con `formatMoney` sobre el texto del servidor |
| `tests/test_spec038_float_c.py` | 39 pruebas: nueve formas por campo |
| `src/modules/tesoreria/importes-float-c.test.tsx` | 4 pruebas sobre el **cuerpo real** de red |
| `e2e/treasury.spec.ts` | Dos escenarios nuevos: las seis fronteras por API y la interfaz de transferencias |

**Migración: ninguna.** Ninguna columna cambia; sólo la anotación que las describía mal.

### Lo que expresamente no cambia

La fórmula del IGTF —`importe × tasa × instantánea`, redondeada a dos decimales— es la
misma expresión, con el mismo redondeo; lo único que cambia es que sus tres factores
dejan de ser `float`. No se toca la tasa, ni las exenciones, ni la selección de regla,
ni la homologación: **`D0-07` sigue abierta**. Tampoco se toca el emparejamiento de la
conciliación, ni la semántica de dirección de los movimientos de caja, ni las
comprobaciones de la transferencia.

### Adaptaciones de pruebas existentes

`test_treasury.py`, `test_spec038_float_b.py`, `test_mc_treasury_ab.py` y
`e2e/treasury.spec.ts` enviaban estos importes como número porque **entonces** ese era
el contrato. Ahora envían texto. Es adaptación al contrato nuevo, no relajación: ninguna
aserción se debilita y ninguna se elimina.

## 11. Evidencia — `evidence/float-038-c/`

| Fichero | Contenido |
|---|---|
| `contrato-de-columnas.txt` | Precisión, escala, nulabilidad y regla de signo de cada campo, leídas de PostgreSQL |
| `openapi.txt` | Las seis fronteras declaradas `string` en el contrato publicado |
| `ejecuciones.txt` | Dirigidas, regresión de A y B, regresión completa, frontend y E2E |
| `mutaciones.txt` | M038-C-01..08 con restauración verificada |
| `frontend-vitest.txt`, `e2e-tres-navegadores.txt` | Salidas literales |

### Matriz de pruebas por campo

Los seis campos tienen, cada uno: texto válido aceptado · número JSON rechazado · entero
JSON rechazado · escala excesiva rechazada · efecto económico cero al rechazar ·
persistencia exacta · respuesta exacta · valor grande exacto (`1234567890123456.78`) ·
regla de signo propia · regla de cero propia.

| Campo | Signo | Cero | Comprobado por |
|---|---|---|---|
| `opened_amount` | admite | admite | `[opened_amount]` en las paramétricas + `test_el_fondo_de_apertura_vuelve_exacto` |
| movimiento `amount` | exige positivo | no | `[movement.amount]` + `test_el_movimiento_de_caja_vuelve_exacto` |
| transferencia `amount` | exige positivo | no | `[transfer.amount]` + `test_la_transferencia_vuelve_exacta` |
| `opening_balance` / `closing_balance` | admiten | admiten | `[reconciliation.opening_balance]` + `test_los_saldos_de_conciliacion_vuelven_exactos` (`-0.01` conservado) |
| IGTF `amount` | exige positivo | no | `[igtf.amount]` + `test_la_base_del_igtf_vuelve_exacta` y `…_sale_como_texto_y_no_como_numero` |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| M038-C-01 | `float` en `opened_amount` | **muere** — 3 pruebas |
| M038-C-02 | `float` en el movimiento de caja | **muere** — 4 pruebas |
| M038-C-03 | `float` en la transferencia | **muere** — 4 pruebas |
| M038-C-04 | `float` en los saldos de conciliación | **muere** — 3 pruebas |
| M038-C-05 | `float` en la base del IGTF | **muere** — 3 pruebas |
| M038-C-06 | El helper deja de rechazar el exceso de escala | **muere** — 3 pruebas |
| M038-C-07 | `Number()` en el cuerpo de la transferencia | **muere** — la prueba de frontend |
| M038-C-08 | `float(...)` en la respuesta monetaria | **muere** — la respuesta exacta |

8/8 semánticamente efectivas; restauración `cmp` idéntica. Las mutaciones 02 y 03
hubo que reescribirlas: sus primeros patrones eran prefijo de los alias de salida
(`ImporteDeMovimientoDeCaja`, `ImporteDeTransferenciaSalida`) y no llegaban a aplicarse.
Una mutación que no se aplica no demuestra nada, así que se repitieron con contexto.

## 12. Clasificación de lo encontrado

| Hallazgo | Clase | Tratamiento |
|---|---|---|
| Las seis fronteras `float` | deuda conocida de la 038 | **Cerradas** |
| `igft_amount`, `rate_snapshot` y el uno de VED/VES | mismo camino aritmético | Corregidos con su frontera; sin ellos el target 6 no compila |
| Pruebas que enviaban número | adaptación al contrato | Adaptadas, no debilitadas |
| `match_score` en `Float` | no monetario | Fuera de alcance, declarado |
| PostgreSQL 16.2 frente a 18.6 | `ENVIRONMENT_BASELINE_DEVIATION` | Vigente |

`NEW_REGRESSION_FLOAT_038_C = 0` · `AUTH_MC_INTERMITTENT = 0` en estas tandas ·
`UNKNOWN = 0`.

## 13. Cobertura declarada sin adornos

Los **movimientos de caja** y los **saldos de conciliación** no tienen productor en la
interfaz: la pantalla de cajas no registra movimientos y la de conciliación no envía
saldos. Su frontera queda certificada por API y por E2E de API, **no** por interfaz, y
así se dice en vez de fingir una cobertura que no existe.

## 14. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación |
|---|---|---|
| C-001 | `[opened_amount]` ×4 + fondo exacto | M038-C-01 |
| C-002 | `[movement.amount]` ×4 + movimiento exacto | M038-C-02 |
| C-003 | `[transfer.amount]` ×4 + transferencia exacta | M038-C-03 |
| C-004 / C-005 | `[reconciliation.opening_balance]` ×4 + saldos exactos con signo | M038-C-04 |
| C-006 | `[igtf.amount]` ×4 + base exacta + IGTF en texto | M038-C-05 |
| C-007 | `test_un_numero_json_no_es_dinero` y `test_un_entero_json_tampoco` (×5) | M038-C-01..05 |
| C-008 | `test_mas_decimales_…` (×5) y `test_lo_rechazado_no_deja_rastro` | M038-C-06 |
| C-009 | respuestas exactas + `test_lo_que_se_guarda_es_decimal_y_no_float` | M038-C-08 |
| C-010 | 4 pruebas de frontend + 1 E2E de interfaz | M038-C-07 |
| C-011 | Los alias salen todos de `app/shared/money.py`; guarda estática `test_ninguna_de_las_seis_fronteras_declara_float` | — |
| C-012 | `test_spec038_float_a.py` y `_b.py` en verde | — |

| Contador | Valor |
|---|---:|
| Números públicos en los targets | **0** |
| `float` interno en los targets | **0** |
| `Mapped[float]` monetario en los targets | **0** |
| `float` en auditoría/respuesta de los targets | **0** |
| Autoridad numérica en el frontend de los targets | **0** |
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| **TRACEABILITY** | **100 %** |

## 15. Estado resultante

| | |
|---|---|
| **FLOAT-038-C** | **CLOSED / CONVERGED** |
| Las seis fronteras `float` de tesorería | **CERRADAS**: la deuda genérica deja de existir |
| Spec 038 | sigue **`COMPLETE / CONVERGED`**; ésta es su tercera reconvergencia dirigida |
| Spec 041 · `D0-07` | **abiertas**: este delta no homologa nada |
| Migración / deriva | ninguna migración; deriva sigue en 21 operaciones, **nueva 0** |
