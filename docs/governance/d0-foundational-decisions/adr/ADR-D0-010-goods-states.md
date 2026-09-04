# ADR-D0-010 — Estados de mercancía y su separación del estado del documento

| Campo | Valor |
|---|---|
| ID | D0-10 · Estado **APPROVED · ACTIVE** · v1 2026-08-29 · **v2 2026-09-03** |
| Responsable | Arquitecto de procesos · Supervisor de almacén · Auditor interno |
| Specs afectadas | **021, 023** · 019, 020, 022, 024, 025, 030, 031, 032, 035, 036 |
| v2 | Declara la matriz de transiciones que `R-D0-10-7` daba por existente y fija la invariante de reserva. Nada de v1 se revoca |

## Problema

El motor de inventario ya tiene una máquina de estados (`inventory/service.py:102`):
`DISPONIBLE → {RESERVADO, TRANSITO, CUARENTENA}` etc. Pero el flujo de recepción **no la usa**:
`accept_receipt` escribe directamente en `DISPONIBLE`. Faltan los estados que el proceso documentado
exige entre la llegada y la disponibilidad: recibido, pendiente de validación, bloqueado por incidencia.

## Principio central

> **R-D0-10-1.** El estado del **documento** y el estado de la **mercancía** son dimensiones
> independientes y no se derivan uno del otro.

Una `GoodsReceipt` en estado `CONFIRMED` **no** implica que su mercancía esté `DISPONIBLE`. Puede
existir una recepción confirmada cuya mercancía está en cuarentena esperando conteo, o bloqueada por
una incidencia abierta. Confundir ambas dimensiones es el origen del salto que hoy lleva la
recepción directamente a stock disponible.

## Decisión sobre el vocabulario

El conjunto actual está en español y **ya está persistido** en `inventory_balances.state`. Renombrar
a inglés exigiría migrar datos vivos sin ganancia funcional.

> **R-D0-10-2.** Se **extiende** el conjunto existente en español en lugar de renombrarlo. La
> coherencia con los datos ya escritos pesa más que la uniformidad idiomática con el resto del código.
> Si la internacionalización llega a ser requisito, se abordará como cambio propio, con su migración.

## Conjunto de estados de mercancía

| Estado | Significado | Disponible para venta |
|---|---|---|
| `ESPERADO` | Comprometido en orden o embarque; aún no llegó | No · **FUTURE** (Spec 018) |
| `RECIBIDO` | **Nuevo.** Físicamente recibido, aún no conciliado | No |
| `PENDIENTE_CONFIRMACION` | **Nuevo.** En conteo o conciliación | No |
| `CUARENTENA` | Retenido por calidad o inspección | No |
| `BLOQUEADO` | **Nuevo.** Retenido por incidencia abierta o disputa | No |
| `DISPONIBLE` | Liberado formalmente | **Sí** |
| `RESERVADO` | Comprometido a un pedido | No |
| `PICKING` | **Nuevo.** En proceso de extracción | No |
| `PREPARADO` | **Nuevo.** Extraído y consolidado, pendiente de confirmación | No |
| `TRANSITO` | En traslado entre almacenes | No |
| `DESPACHADO` | **Nuevo.** Salió físicamente | No (fuera de existencia) |
| `DEVUELTO` | **Nuevo.** Reingresado, pendiente de inspección | No |
| `RECHAZADO` | No apto; no se incorpora | No |
| `DESECHO` | Destruido o descartado | No |
| `VENDIDO` | Consumido por venta | No |

Estados existentes conservados: `DISPONIBLE`, `RESERVADO`, `TRANSITO`, `CUARENTENA`, `RECHAZADO`,
`DESECHO`, `VENDIDO`. Estados nuevos: 7.

## Reglas

| ID | Regla |
|---|---|
| R-D0-10-3 | `disponible para venta` es **exclusivamente** `DISPONIBLE`. Ningún otro estado se ofrece al vendedor. |
| R-D0-10-4 | El paso a `DISPONIBLE` desde la cadena de recepción exige **liberación formal** (Spec 021). No es automático. |
| R-D0-10-5 | Toda transición de estado es un **movimiento de inventario**, no una edición de campo. El saldo se reconstruye desde movimientos (P5). |
| R-D0-10-6 | `BLOQUEADO` solo se libera cerrando la incidencia que lo originó. |
| R-D0-10-7 | Las transiciones no declaradas están prohibidas; el motor las rechaza. |
| R-D0-10-8 | `ESPERADO` no computa como existencia física en ningún saldo ni valoración. |
| **R-D0-10-9** | Ninguna reclasificación puede dejar `qty_reserved > qty_on_hand` en el saldo origen. `allow_negative` es la política de sobreventa de un almacén (`POL-D0-002` §6) y **no** es la vía para admitir ese resultado: son problemas distintos. |
| **R-D0-10-10** | Activar la primera transición con origen `DISPONIBLE` hacia un estado no vendible exige, **en el ciclo de la Spec que la active**, elegir entre bloquear la transición completa o reclasificar solo lo no reservado devolviendo un conflicto estructurado. Liberar reservas automáticamente y reasignarlas quedan **rechazadas** (ver §Alternativas rechazadas). |

## Gobierno de las transiciones (v2)

`R-D0-10-7` fijaba el régimen —**deny-by-default**— sin declarar la tabla contra la que decidir. La
v2 la declara, en `d0-10-checkpoint/d0-10-merchandise-state-transition-matrix.md`, con la regla:

> `can_transition(origen, destino, contexto)` responde `ALLOWED` si y solo si el par está en la tabla
> de transiciones activas y el contexto cumple el permiso, la aprobación y el motivo declarados. En
> cualquier otro caso, `DENIED`. Sin inferencia por parecido semántico.

Nueve transiciones activas, todas con evidencia documental. Las demás quedan `DENIED`, y la Spec que
necesite una la activa **en su propio ciclo**, enmendando la matriz con su evidencia. Ni el motor ni
el implementador activan aristas.

**Quién pide y quién ejecuta son distintos.** La Spec del proceso decide que la transición debe
ocurrir y aporta evento, motivo y documento; la Spec 023 valida contra la matriz y ejecuta; la Spec
030 sigue siendo la única autoridad sobre compromisos comerciales.

Ninguna de las nueve transiciones activas tiene `DISPONIBLE` como origen, y las reservas viven
exclusivamente en filas `DISPONIBLE`. En consecuencia **ninguna transición activa puede producir el
conflicto de R-D0-10-9**, que se cumple hoy por construcción.

## Alternativas rechazadas (v2)

| Alternativa | Por qué se rechaza |
|---|---|
| Derivar el grafo del significado de los nombres | Produciría aristas sin proceso que las respalde. Una transición existe cuando un requisito, proceso, ADR o política la declara |
| Declarar hoy las 15×15 transiciones | Decidiría por las Specs 022, 025, 031, 032, 035 y 036 antes de auditarlas |
| **Liberar reservas automáticamente al reclasificar** | `POL-D0-002` §8 enumera en tabla cerrada los eventos que modifican una reserva y la reclasificación no está en ella. Sería una segunda autoridad sobre compromisos que `D0-03` asignó a la Spec 030 |
| **Reasignar la reserva a otro stock elegible** | Exige abastecimiento cruzado, que `POL-D0-002` §7 excluye hoy («un almacén por pedido; sin abastecimiento cruzado») |
| Usar `allow_negative` para admitir el disponible negativo | Convertiría una decisión de calidad en una autorización comercial que nadie dio |
| Crear un estado o un motor nuevos para la custodia reservada | `RESERVADO` ya existe en el catálogo sin dueño; el reservado real es un contador sobre `DISPONIBLE` (`POL-D0-002` §1) |

## Consecuencias (v2)

- **`R-D0-10-7` pasa de vinculante-inimplementable a ejecutable.** Era el bloqueo real.
- **La Spec 021 tiene su capacidad definida**: necesita cuatro transiciones, las cuatro con autoridad,
  ninguna con origen `DISPONIBLE` y ninguna que pueda toparse con una reserva viva.
- **El movimiento de inventario deberá conservar estado de origen y destino.** Hoy no lo hace, y por
  eso `recompute_balances` colapsaría cualquier saldo multiestado en `DISPONIBLE`, contra R-D0-10-5.
  Es delta estructural del próximo ciclo de la Spec 023, no decisión.
- **`confirm_transfer_receipt` queda clasificado como defecto vivo**: decide
  `destination_state = CUARENTENA` ante una diferencia y el motor lo ignora. La transición #9 le da
  autoridad —`FR-003-062`, con aprobación—; la corrección técnica es de la Spec 023.
- **El estado de lote y serial no participa.** `FR-003-035` gobierna otra entidad con otras siete
  etiquetas; seis nombres coinciden y ninguna semántica se comparte.

## Impacto

Frontend: el estado de mercancía debe ser visible y filtrable en existencias · Backend: máquina de
estados ampliada; recepción y picking dejan de escribir `DISPONIBLE` directamente · DB: sin tablas
nuevas; valores nuevos en `state` · QA: cada transición y cada prohibición · Fiscal: la mercancía en
cuarentena sigue siendo del inventario a efectos de valoración; la despachada no.

## Migración

**`SAFE_MIGRATION`** — los valores nuevos son aditivos. Los saldos existentes conservan su estado.
El cambio de comportamiento (recepción ya no salta a `DISPONIBLE`) llega con la Spec 021, no con esta decisión.

## Criterios de aceptación

- [ ] Existe una recepción confirmada con mercancía en cuarentena (probado).
- [ ] Un saldo `BLOQUEADO` no aparece como disponible en la consulta del vendedor.
- [ ] Toda transición genera movimiento y es reconstruible.
- [ ] Una transición no declarada se rechaza.

## Estado final

**APPROVED** — **CLOSED**.
