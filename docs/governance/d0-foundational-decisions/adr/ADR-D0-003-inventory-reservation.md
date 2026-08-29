# ADR-D0-003 — Momento y semántica de la reserva de inventario

| Campo | Valor |
|---|---|
| ID | D0-03 |
| Estado | **APPROVED** (arquitectura y valor por defecto) · elección del disparador por empresa pendiente |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de procesos · Gerente de ventas · Supervisor de inventario · Especialista en concurrencia |
| Extiende | `ADR-013 — Idempotencia y Concurrencia` |
| Specs afectadas | **030** (propietaria) · 023, 029, 031, 032, 033, 034, 035 |

## Problema

El documento de proceso plantea el control de forma explícita: *«determinar si al emitir el pedido
el sistema reserva inmediatamente el inventario o solamente muestra una existencia disponible. Esta
diferencia es crítica para evitar que dos vendedores comprometan el mismo stock.»*

El código reserva al aprobar la orden (`APPROVED → RESERVED`, `sales/service.py:189`). Nadie decidió
que fuera ahí: es donde quedó.

## Por qué debe decidirse ahora

Toda la cadena de preparación (031, 032, 033) se construye sobre el supuesto de que existe una
reserva firme cuando el pedido llega al almacén. Si la reserva nace más tarde de lo que el almacén
asume, se prepara mercancía que no estaba comprometida. Si nace antes, se bloquea stock por
cotizaciones que nunca se cerrarán.

Además, cambiar el disparador después de operar cambia la semántica de todas las reservas ya
existentes: es un cambio que no admite migración limpia.

## Evidencia

- DOCX Pedido §1, control explícito.
- `sales/service.py:184-193` — reserva en la transición a `APPROVED`.
- `inventory/models.py:133` — `Reservation` con `status` y `expires_at`, sin política de expiración automática.
- `specs/003-inventario-logistica/convergence.md` `CVG-003-04` — expiración por job **pendiente**.
- `tests/test_idempotency_concurrency.py` — 6 casos; cubren idempotencia de pagos y transiciones, **no** la carrera de dos vendedores sobre la misma unidad.

## Alternativas

| Alt. | Disparador | Sobre-reserva | Riesgo de venta doble | Veredicto |
|---|---|---|---|---|
| A | Al crear cotización | Muy alta | Nulo | Descartada: las cotizaciones se abandonan; bloquearía inventario sin compromiso comercial |
| B | Al aprobar cotización | Alta | Bajo | Descartada: aprobar una cotización no es un compromiso de compra del cliente |
| C | Al crear pedido (borrador) | Media | Bajo | Descartada: un borrador es editable y puede no emitirse |
| D | **Al liberar/emitir el pedido** | Baja | Bajo | **Base del valor por defecto** |
| E | Al aprobar crédito | Baja | **Medio** | Descartada como *única* opción: entre emisión y aprobación de crédito el stock queda libre, que es exactamente la ventana que el documento quiere cerrar |
| F | Configurable por empresa | — | — | **RECOMENDADA como arquitectura** |

## Alternativa recomendada

**Arquitectura F con valor por defecto D.**

KONTROL es un producto comercializable: no puede imponer el momento de reserva de una empresa
concreta. Pero tampoco puede dejarlo indefinido, porque la cadena de almacén depende de él. La
solución es un disparador configurable con un valor por defecto que el producto justifica.

El valor por defecto es **D — al liberar el pedido**, porque es el primer punto de la cadena en el
que existe un compromiso comercial formal y un documento no editable.

Nota sobre el estado actual: el código implementa hoy algo cercano a **E**. La diferencia con **D**
es la ventana entre emisión y aprobación de crédito. Al implementar 029 (pedido como entidad
distinta de la orden) esa ventana debe cerrarse: la reserva pasa a nacer con la liberación del
pedido, y el análisis de crédito ocurre **antes** de liberar, no después de reservar.

## Regla definitiva

> **R-D0-03-1.** El disparador de reserva es configurable por empresa mediante
> `reservation_trigger` ∈ {`ORDER_RELEASED` (defecto), `ORDER_CREATED`, `CREDIT_APPROVED`,
> `QUOTE_APPROVED`, `MANUAL`}.
>
> **R-D0-03-2.** La disponibilidad se calcula siempre como
> `disponible = físico − reservado − bloqueado`. Ningún proceso lee el físico como disponible.
>
> **R-D0-03-3.** **Dos operaciones no pueden reservar la misma unidad.** La garantía se implementa
> en la base de datos dentro de la transacción que crea la reserva: bloqueo de la fila de saldo
> (`SELECT … FOR UPDATE`) más una restricción que impide `reservado > físico`. El frontend nunca es
> autoridad sobre disponibilidad (P6).
>
> **R-D0-03-4.** Toda reserva tiene vigencia. Vencida, se libera automáticamente y el evento queda
> auditado. La duración es configuración por empresa; que exista vigencia es decisión de producto.
>
> **R-D0-03-5.** La reserva se hace a la mínima dimensión conocida en el momento de reservar
> (almacén, y además lote, serial o ubicación cuando el producto o el pedido lo determinen).
> Una reserva sin dimensión suficiente no puede consumirse en picking dirigido.
>
> **R-D0-03-6.** La reserva es idempotente por documento de origen: reintentar la liberación de un
> pedido no duplica reservas (ADR-013).
>
> **R-D0-03-7.** El consumo de la reserva ocurre en la **salida física** (despacho), no en la
> facturación. Facturar no mueve inventario.

## Ciclo de vida

```
        (sin reserva)
             │  liberación del pedido
             ▼
   AVAILABLE ──► RESERVED ──► PICKING ──► PICKED ──► CONFIRMED ──► DISPATCHED
                    │            │           │           │
                    │ cancelación/expiración │ faltante  │ no conforme
                    ▼            ▼           ▼           ▼
                AVAILABLE    (parcial: la parte no encontrada vuelve a AVAILABLE
                              y genera incidencia — Spec 032)
```

Reserva parcial: cuando el picking encuentra menos de lo reservado, la diferencia se libera y se
registra incidencia. **La cantidad no encontrada nunca se descuenta silenciosamente del pedido.**

## Casos que la política debe cubrir

Reserva manual · prioridad entre pedidos · backorder ante stock insuficiente · sustitución de
producto · reserva sobre mercancía en transferencia · reserva por lote y por serial · reserva por
ubicación (disponible tras 022) · liberación por cancelación del pedido.

`backorder` y `sustitución` se declaran **FUTURE CAPABILITY**: el modelo debe admitirlos sin
rediseño, la Spec 030 no está obligada a implementarlos.

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Indicador de disponible vs. reservado; aviso de reserva parcial; pantalla de reservas |
| Backend | Cambio del punto de disparo en `sales`; política por empresa; job de expiración (`CVG-003-04`) |
| Base de datos | `Reservation` gana dimensión de ubicación y vínculo al documento; restricción de no sobre-reserva |
| Integraciones | Ninguna |
| QA | **Prueba obligatoria de carrera**: dos transacciones concurrentes sobre la última unidad; exactamente una gana |
| Seguridad | Refuerza P6 |
| Fiscal | Ninguno — la reserva no es hecho imponible |

## Migración / compatibilidad

**`SAFE_MIGRATION`** para la configuración (columna nueva con defecto que reproduce el
comportamiento actual).
**`MANUAL_REVIEW_REQUIRED`** para las reservas activas si una empresa cambia de disparador: las
reservas vivas se mantienen bajo la semántica con la que nacieron y se marcan con el disparador que
las originó.

## Criterios de aceptación

- [ ] La prueba de concurrencia sobre PostgreSQL demuestra que solo una de dos transacciones reserva la última unidad.
- [ ] `disponible` nunca es negativo bajo carga concurrente.
- [ ] La reserva expira y se libera automáticamente, con evento auditado.
- [ ] El picking parcial libera la diferencia y genera incidencia.
- [ ] Cambiar `reservation_trigger` no altera reservas existentes.

## Preguntas pendientes

**BUSINESS_VALIDATION_REQUIRED** — ver `D0-open-questions.md` OQ-03:
qué disparador usa el cliente, duración de la vigencia, política de prioridad entre pedidos.
Ninguna impide construir el motor.

## Estado final

**APPROVED** — arquitectura y valor por defecto cerrados.
Clasificación de cierre: **CLOSED_WITH_CONFIGURATION_PENDING**.
