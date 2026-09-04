# D0-10 · MATRIZ DE TRANSICIONES DE ESTADO DE MERCANCÍA

> Responde `OQ-D010-01`. Cada arista activa lleva su evidencia documental. Ninguna se deriva del
> significado del nombre: sin requisito, proceso, ADR o política que la sostenga, la arista **no
> existe**.

## Gobierno

`R-D0-10-7` ya fija el régimen y no hace falta inventarlo: *«las transiciones no declaradas están
prohibidas; el motor las rechaza»*. Es **deny-by-default**, y este documento es la declaración que
esa regla daba por existente.

> **Regla de gobierno.** `can_transition(origen, destino, contexto)` responde `ALLOWED` si y solo si
> el par aparece en la tabla de transiciones activas y su contexto cumple el permiso, la aprobación y
> el motivo declarados. En cualquier otro caso responde `DENIED`. No hay respuesta intermedia ni
> inferencia por parecido semántico.

> **Regla de ampliación.** Una Spec que necesite una arista no declarada la activa **en su propio
> ciclo**, enmendando esta matriz con su evidencia. No la activa el motor, ni el implementador, ni el
> parecido con otra arista ya activa.

## Quién pide y quién ejecuta

| Rol | Quién | Qué hace |
|---|---|---|
| Decide que la transición debe ocurrir | la Spec del proceso (019, 020, 021, 025…) | aporta evento, motivo y documento origen |
| Valida contra esta matriz y ejecuta | **Spec 023**, motor canónico | comprueba el par, el permiso y la aprobación; registra movimiento; materializa saldo |
| Registra el compromiso comercial | **Spec 030** | única autoridad sobre reservas; la matriz no se la disputa |

## Transiciones ACTIVAS

Nueve. Son las que tienen autoridad documental hoy.

| # | Origen | Destino | Evento | Owner del evento | Permiso | Aprobación | Motivo | Regla de reserva | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| 1 | *(entrada)* | `RECIBIDO` | aceptación de la recepción física | 019 (destino elegido por 021) | `compras:receive` | no | no | n/a — sin origen | R-D0-10-4 · ADR §Migración · flujo objetivo del checkpoint operativo |
| 2 | `RECIBIDO` | `DISPONIBLE` | **liberación formal** tras confirmación | **021** | `inventario:release` | no | no | n/a — el origen no es reservable | **R-D0-10-4** · flujo «liberación formal de los 90 a DISPONIBLE» |
| 3 | `RECIBIDO` | `RECHAZADO` | confirmación con rechazo | **021** | `inventario:release` | no | **sí** | n/a | flujo «Confirmación: aceptado 90, rechazado 10» · ADR: «no apto; no se incorpora» |
| 4 | `RECIBIDO` | `CUARENTENA` | resolución de incidencia con tratamiento `CUARENTENA` | 020 → 021 | `compras:incident` | no | **sí** | n/a | flujo «resolución [aceptar / reclamar / devolver / **cuarentena**]» · `INCIDENT_RESOLUTIONS` de la Spec 020 |
| 5 | `RECIBIDO` | `BLOQUEADO` | se abre incidencia sobre esa mercancía | **020** | `compras:incident` | no | **sí** | n/a | ADR §Problema «bloqueado por incidencia» · R-D0-10-6 |
| 6 | `BLOQUEADO` | `RECIBIDO` | cierre de la incidencia sin cambio de destino | **020** | `compras:incident` | no | **sí** | n/a | **R-D0-10-6** «solo se libera cerrando la incidencia que lo originó» |
| 7 | `CUARENTENA` | `DISPONIBLE` | liberación formal tras inspección | **021** | `inventario:release` | no | **sí** | n/a | **R-D0-10-4** — la cuarentena está en la cadena de recepción |
| 8 | `CUARENTENA` | `RECHAZADO` | inspección concluye que no es apta | **021** | `inventario:release` | no | **sí** | n/a | ADR: significados de ambos estados · flujo de confirmación |
| 9 | *(entrada por transferencia)* | `CUARENTENA` | diferencia en la recepción de una transferencia | **025** | `inventario:transfer` | **sí (Spec 045)** | **sí** | n/a — sin origen | **`FR-003-062`**: «diferencias en recepción de transferencia con destino definido (cuarentena/ajuste) **y aprobación**» |

**Ninguna arista activa tiene `DISPONIBLE` como origen.** Es el hecho que gobierna todo el análisis
de `OQ-D010-02` y no es casualidad: la cadena que la Spec 021 necesita va *hacia* lo vendible, nunca
al revés.

## Transiciones FUTURE_OWNER

Existen en el catálogo, no tienen evidencia hoy, y su Spec las activará. **Comportamiento actual:
`DENIED`.**

| Origen | Destino | Dueño futuro | Por qué no se declara hoy |
|---|---|---|---|
| `RECIBIDO` | `PENDIENTE_CONFIRMACION` | 021 | El ADR sitúa el estado «entre la llegada y la disponibilidad», pero ninguna fuente declara la arista. Si el conteo por SKU necesita aparcar la mercancía, la 021 lo declara en su ciclo |
| `PENDIENTE_CONFIRMACION` | cualquiera | 021 | Igual |
| **`DISPONIBLE`** | **cualquier no vendible** | **025** (ajustes) y calidad | Requiere resolver `OQ-D010-02`. Ver el análisis de conflicto |
| `DISPONIBLE` | `PICKING` → `PREPARADO` | 031, 032 | Specs no construidas |
| `PREPARADO` | `DESPACHADO` → `VENDIDO` | 035 | Spec no construida |
| `DESPACHADO` | `DEVUELTO` | 036 | Spec no construida |
| `DEVUELTO` | `DISPONIBLE` · `RECHAZADO` | 036 | Requiere la inspección previa al reingreso que 036 define |
| *(entrada)* · `TRANSITO` | `TRANSITO` · destino | 025 | El motor no escribe `TRANSITO` hoy; la salida de transferencia es su dueña |
| `RECHAZADO` · `CUARENTENA` | `DESECHO` | 025 | Baja de inventario: es un ajuste, con su aprobación |
| cualquiera | `ESPERADO` | 018 | `FUTURE` por el propio ADR (R-D0-10-8) |

## Transiciones DENIED sin dueño previsible

- **Cualquier par que no aparezca arriba.** Es el efecto de la regla de gobierno, no una lista.
- **`DISPONIBLE` → `DISPONIBLE`** y todo par origen = destino: no es transición, es ausencia de ella.
- **Salida de estados terminales.** `VENDIDO`, `DESECHO` y `DESPACHADO` describen mercancía que ya no
  está en existencia (el ADR lo dice de `DESPACHADO`: «fuera de existencia»). Ninguna fuente declara
  salida desde ellos.
- **Cualquier arista hacia o desde `RESERVADO`**, que no tiene dueño.

## Transiciones que la Spec 021 necesita

Exactamente cuatro: **#2, #3, #7 y #8**, más la #1 que la 019 ejecuta con el destino que la 021
determine. Las cuatro tienen autoridad. Ninguna toca `DISPONIBLE` como origen, ninguna requiere
aprobación de la Spec 045 y ninguna puede encontrarse con una reserva viva.

**Con esta matriz, la Spec 021 tiene su capacidad completamente definida.**
