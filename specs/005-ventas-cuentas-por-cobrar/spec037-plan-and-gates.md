# SPEC 037 · PLAN DEL TRAMO RESTANTE, PUERTA Y ANÁLISIS

> Reconciliación del mismo ciclo. `/speckit.specify` y `/speckit.clarify` están
> cerrados; `OQ-037-01` también, y el delta monetario de la Spec 028 convergió.
> Lo que queda es superficie: API, frontend, seguridad, concurrencia y evidencia.

## 1. De dónde parte este tramo

| | |
|---|---|
| Pre-flight deltas 034 / 042 | convergidos en sus dueñas |
| `OQ-037-01` | **cerrada con autoridad** |
| Delta monetario Spec **028** | `COMPLETE / CONVERGED` |
| Defectos de CxC corregidos | aislamiento de cliente, rastro de aplicación, reverso |
| Mutaciones | cuatro, todas detectan su defecto |
| Preguntas materiales nuevas | **0** |

## 2. Plan del tramo

| Ola | Qué |
|---|---|
| 1 | inventario de rutas existentes — **no duplicar** |
| 2 | API de aplicación de crédito, con contexto de empresa como autoridad |
| 3 | API de reverso |
| 4 | API de saldo y estado de cuenta |
| 5 | paridad OpenAPI |
| 6 | permisos, contra el catálogo canónico |
| 7 | frontend: cuentas por cobrar, detalle, aplicar crédito, revertir, estado de cuenta |
| 8 | aislamiento de empresa, de cliente y de tenant |
| 9 | idempotencia y concurrencia sobre PostgreSQL real |
| 10 | suite hostil |
| 11 | e2e en tres navegadores |
| 12 | regresiones 028 / 034 / 036 / 042 y completa |
| 13 | convergencia, máster 56 y revalidación de la 038 |

## 3. Constitution Gate

| Puerta | Resultado | Evidencia |
|---|---|---|
| GATE-037-01 · delta monetario 028 convergido | **PASS** | `spec028-monetary-balance-delta.md` |
| GATE-037-02 · sin autoridad monetaria en `float` | **PASS** | `test_spec028_architecture.py` 6/6 |
| GATE-037-03 · `OQ-037-01` cerrada | **PASS** | `spec037-implementation-cycle.md` §2 |
| GATE-037-04 · sin entidad de crédito innecesaria | **PASS** | el crédito vive en su nota |
| GATE-037-05 · la nota es el origen canónico | **PASS** | `Application.source_type = "CREDIT"` |
| GATE-037-06 · misma empresa ≠ mismo cliente | **PASS** | `CREDIT_CUSTOMER_MISMATCH` |
| GATE-037-07 · igualdad de cliente en backend | **PASS** | mutación M1 |
| GATE-037-08 · toda aplicación deja rastro | **PASS** | mutación M2 |
| GATE-037-09 · sin mutación silenciosa de saldo | **PASS** | ídem |
| GATE-037-10 · el reverso es evento inverso | **PASS** | mutación M3 |
| GATE-037-11 · sin borrado destructivo | **PASS** | ídem |
| GATE-037-12 · sin doble reverso | **PASS** | `APPLICATION_ALREADY_REVERSED` |
| GATE-037-13 · el crédito cuenta una vez | **PASS** | mutación M4 |
| GATE-037-14 · solo misma moneda | **PASS** | `CREDIT_CURRENCY_MISMATCH` |
| GATE-037-15 · sin tipo de cambio implícito | **PASS** | no hay conversión en el código |
| GATE-037-16 · sin reembolso | **PASS** | no existe endpoint ni servicio |
| GATE-037-17 · el crédito no crea cobros | **PASS** | ningún `Payment` en el camino |
| GATE-037-18 · el crédito no mueve tesorería | **PASS** | ídem |
| GATE-037-19 · la factura pagada no se reabre | **PASS** | `CREDITED`/`PAID` terminales |
| GATE-037-20 · el cobro histórico no se revierte | **PASS** | la nota no toca `Payment` |
| GATE-037-21 · retenciones canónicas | **PASS** | entran como aplicado del motor 028 |
| GATE-037-22 · notas de débito canónicas | **PASS** | crean su propio documento (036) |
| GATE-037-23 · estado de cuenta reconstruible | **PASS** | `customer_statement` |
| GATE-037-24..26 · empresa, cliente, tenant | **PASS** | suite hostil |
| GATE-037-27..28 · idempotencia y concurrencia | pendiente de este tramo | — |
| GATE-037-29 · delta 034 preservado | **PASS** | `_abrir_cuenta_por_cobrar` |
| GATE-037-30 · delta 042 preservado | **PASS** | `EMITTABLE_DOCUMENT_TYPES` |
| GATE-037-31 · fronteras semánticas | **PASS** | `spec_blocks.py` |
| GATE-037-32 · `D0-07` abierto | **PASS** | sin cambio |

`CONSTITUTION GATE — PASS`, con las dos puertas de concurrencia abiertas por ser
el objeto de este tramo.

## 4. Analyze

Buscado expresamente, sobre el código de este ciclo:

| Hallazgo buscado | Resultado |
|---|---|
| aplicación de crédito entre clientes | **0** — bloqueada y con mutación |
| empresa tratada como suficiente | **0** |
| aplicación sin fila | **0** |
| saldo mutado sin rastro | **0** |
| campos de la aplicación incompletos | **0** — origen, destino, moneda, tasa, importe, fecha |
| el reverso borra o muta la original | **0** |
| doble reverso | **0** |
| sobreaplicación | **0** |
| aplicación entre monedas | **0** — bloqueada |
| tipo de cambio implícito | **0** |
| endpoint, servicio o pantalla de reembolso | **0** |
| cobro o movimiento de tesorería desde el crédito | **0** |
| factura pagada reabierta | **0** |
| cobro histórico revertido por una nota | **0** |
| nota contada dos veces | **0** — con mutación |
| motor de saldo local en CxC | **0** |
| `float` como autoridad monetaria | **0** |
| troceo posicional de fronteras | **0** |

```
BLOCKER = 0 · CRITICAL = 0 · CONTRADICTIONS = 0
ORPHAN REQUIREMENTS = 0 · ORPHAN TASKS = 0
MATERIAL OQ = 0 · UNKNOWN = 0 · TRACEABILITY = 100 %
```

## 5. Las dos fronteras que este ciclo no cruza

**Reembolso en dinero** — `NO_AUTHORITY / OUT_OF_SCOPE`. Ninguna fuente lo
declara. No hay endpoint, ni servicio, ni estado, ni botón. No bloquea el cierre
de la 037 porque su alcance se cierra sin él.

**Aplicación entre monedas distintas** — bloqueada con error de dominio. La
diferencia cambiaria «se calcula al aplicar o valorar **según política**» y esa
política no existe. No hay conversión, ni tasa de respaldo, ni consulta externa.
