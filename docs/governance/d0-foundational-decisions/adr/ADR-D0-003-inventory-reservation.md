# ADR-D0-003 — Momento y semántica de la reserva de inventario

| Campo | Valor |
|---|---|
| ID | D0-03 |
| Versión | **v2** (2026-09-02) — supera a v1 (2026-08-29) en R-D0-03-1 y R-D0-03-4; conserva el resto |
| Estado | **APPROVED · ACTIVE** |
| Clasificación de cierre | **CLOSED** |
| Responsable | Arquitecto de procesos · Gerente de ventas · Supervisor de inventario · Especialista en concurrencia |
| Extiende | `ADR-013 — Idempotencia y Concurrencia` · `ADR-D0-010 — Estados de mercancía` · `ADR-D0-009 — Unidad y presentación` |
| Specs afectadas | **030** (propietaria) · 003/023, 029, 031, 032, 033, 034, 035, 045, 047 |
| Checkpoint de cierre | `../d0-03-checkpoint/` (auditoría, opciones, flujos, concurrencia, decisión, trazabilidad, convergencia) |

## Contexto

El documento de proceso lo plantea como control explícito: *«determinar si al emitir el pedido el
sistema reserva inmediatamente el inventario o solamente muestra una existencia disponible. Esta
diferencia es crítica para evitar que dos vendedores comprometan el mismo stock.»*

El código reserva al aprobar el crédito (`transition_order(target="APPROVED")` →
`_reserve_order` → `RESERVED`). Nadie decidió que fuera ahí. Además lo hace sin bloqueo (carrera),
sin cantidad base, sin liberar al cancelar, sin vigencia, sin auditoría y en silencio cuando el
pedido no tiene almacén (auditoría completa en `d0-03-checkpoint/current-reservation-behavior.md`).

La v1 de este ADR cerró la arquitectura como «disparador configurable con defecto
`ORDER_RELEASED`». «Liberar el pedido» significaba a la vez «emitirlo» (`SUBMITTED`) y «después del
crédito» (`APPROVED`), y un disparador configurable sin valor elegido no es un contrato que la Spec
030 pueda implementar. El checkpoint maestro de las 56 Specs lo detectó y bloqueó 030.

## Decisión

> **RESERVATION TRIGGER = ORDER_CONFIRMATION**
>
> La reserva nace en la transición `DRAFT → SUBMITTED` del pedido de venta (emisión/confirmación
> comercial), de forma síncrona y en la misma transacción. Es un disparador **fijo** del producto,
> igual para pedidos de contado, a crédito y sin evaluación de crédito. No es configurable por
> empresa.

Lo que sí configura cada empresa: la vigencia de la reserva mientras se evalúa el crédito
(`reservation_ttl_days`, defecto desactivado), la sobreventa por almacén (`policies.allow_negative`,
defecto `false`) y si un pedido requiere crédito (políticas de la Spec 045).

## Alternativas consideradas

| Alt. | Disparador (transición) | Veredicto | Razón principal |
|---|---|---|---|
| A | Creación del pedido (`DRAFT`) | Rechazada | Borrador editable; la conversión de cotización reservaría (viola FR-029-035) |
| **B** | **Confirmación del pedido (`DRAFT → SUBMITTED`)** | **Elegida** | Punto que señala el negocio; primer compromiso formal no editable; la insuficiencia se conoce antes de comprometer al cliente |
| C | Aprobación de crédito (`CREDIT_PENDING → APPROVED`) — código actual | Rechazada | Deja abierta la ventana emisión→crédito; crédito aprobado sin stock no tiene salida sin backorder |
| D | Liberación a preparación (`APPROVED → RELEASED`) | Rechazada | Lo de C con ventana mayor; no protege la fase comercial |
| E | Configurable por empresa (v1) | Rechazada para 030 | Cada valor alternativo es inseguro sin backorder; multiplica máquinas de estado; cambiarlo reinterpreta reservas vivas; era el bloqueo real de 030 |
| F | Contado y crédito con triggers distintos | No procede | No hay atributo contado/crédito; la señal (045 abre solicitud) se conoce en la misma transición; sería E con otro nombre |

Matriz de 14 criterios y evidencia E1–E10 en `d0-03-checkpoint/d0-03-reservation-options.md`.

## Por qué

1. **Evidencia de negocio**: el control pide decidir «al emitir el pedido» (E1).
2. **Semántica de estados**: `SUBMITTED` es el primer estado no editable con compromiso comercial y
   origen comercial completo (029).
3. **Sin backorder**, la insuficiencia solo tiene solución limpia antes de comprometer al cliente:
   editar el borrador. Cualquier disparador posterior descubre el problema tarde.
4. **Contado y crédito**: para contado todas las opciones coinciden en el tiempo; para crédito solo B
   protege el stock durante la evaluación, y el rechazo lo devuelve.
5. **Producto comercializable**: el producto impone la semántica de sus estados (como en cotizaciones,
   aprobaciones y mercancía); no impone la política de crédito, la vigencia ni la sobreventa, que
   siguen siendo configurables. Esto responde al argumento de la v1 a favor de la configurabilidad.
6. **Un punto, una regla, un evento**: auditable y probable.

## Reglas definitivas (v2)

> **R-D0-03-1.** `RESERVATION TRIGGER = ORDER_CONFIRMATION`: la reserva nace en `DRAFT → SUBMITTED`,
> fija, para todo pedido con líneas de inventario. Cotización y conversión no reservan. Las líneas
> de servicio no reservan. *(Supera a v1.)*
>
> **R-D0-03-2.** La confirmación es atómica con la reserva: sin reserva completa no hay `SUBMITTED`.
> La evaluación de crédito (Spec 045, `SALES_CREDIT`) ocurre **después** de reservar; el rechazo
> libera en la misma transacción; la aprobación no toca la reserva salvo para hacerla firme
> (`expires_at := NULL`). Sin política aplicable, `SUBMITTED → APPROVED → RELEASED` en la misma
> transacción.
>
> **R-D0-03-3.** Dos operaciones no pueden reservar la misma unidad. Garantía en PostgreSQL, dentro
> de la transacción: `SELECT … FOR UPDATE` sobre la fila de saldo antes de leer el disponible,
> unicidad sobre la clave del saldo, índice único parcial `(source_line_id) WHERE status = 'ACTIVE'`
> y `CHECK (qty_reserved >= 0)`. Bloqueos en orden determinista por producto. Prueba de carrera
> obligatoria sobre PostgreSQL. El frontend nunca es autoridad (P6). Toda reserva y liberación
> queda auditada con actor, empresa, pedido, línea, almacén, producto, cantidad tecleada y base,
> trigger, motivo y estados anterior/posterior.
>
> **R-D0-03-4.** Cantidad y disponibilidad se comparan en **unidad base** con el factor snapshot de
> la línea (Spec 011); la reserva persiste también la cantidad tecleada y su presentación. **Todo o
> nada por pedido**: sin reserva parcial, sin backorder, sin pedido sin reserva. Insuficiencia →
> `409 INSUFFICIENT_AVAILABLE` y el pedido sigue `DRAFT`. Sobreventa solo en almacenes con
> `policies.allow_negative = true`, marcada `oversell` y auditada; nunca por carrera. *(Absorbe y
> reemplaza la vigencia obligatoria de v1: ver R-D0-03-8.)*
>
> **R-D0-03-5.** Dimensión de la reserva: `(empresa, almacén del pedido, producto)`; lote o serial
> solo si la línea del pedido los exige. Nunca ubicación. Un almacén por pedido, sin abastecimiento
> automático desde otro. Solo consume saldo `DISPONIBLE` (R-D0-10-3). La reserva no cambia el estado
> de custodia: `RESERVADO`/`PICKING` del catálogo los escribe la preparación (031/032).
>
> **R-D0-03-6.** Liberación automática y atómica en: cancelación del pedido (desde cualquier estado
> vivo), rechazo de crédito, reversión a borrador, expiración por TTL, faltante de picking (la
> diferencia, con incidencia — 032). Consumo (`FULFILLED`) en la salida física (035). La
> facturación no toca la reserva. Liberación manual solo de reservas `MANUAL`, con permiso, motivo
> y auditoría; las de pedido se liberan cancelando o revirtiendo el pedido.
>
> **R-D0-03-7.** Un pedido es editable solo en `DRAFT`. Modificar un pedido emitido = `REVERT_TO_DRAFT`
> (desde `SUBMITTED`, `CREDIT_PENDING`, `APPROVED`, `RELEASED`; no desde `PREPARING`) con motivo:
> libera toda la reserva, declara obsoleta la solicitud de crédito (045) y, al reemitir, reserva de
> nuevo con la disponibilidad de ese momento. No hay ajuste por diferencias.
>
> **R-D0-03-8.** La vida de la reserva es la del pedido. Vencimiento por reloj solo si la empresa
> configura `reservation_ttl_days` (defecto `NULL`), y solo mientras el pedido espera crédito. Al
> expirar: reserva `EXPIRED` **y** pedido `EXPIRED` en la misma transacción. Invariante: nunca un
> pedido vivo sin reserva. Ejecución: endpoint de expiración existente; periodicidad = planificador
> de plataforma (propietaria Spec 047). 030 no implementa worker. *(Supera a v1.)*
>
> **R-D0-03-9.** La reserva no absorbe picking (ruta, ubicación, lote/serial), ni confirmación
> independiente (033), ni facturación (034), ni despacho (035). Entrega a 031 el pedido en
> `RELEASED` con sus filas de reserva por línea.
>
> **R-D0-03-10.** ARCH-MC-001: la empresa de la reserva es la del pedido cargado bajo
> `CompanyContext` y coincide con la del almacén; pedido o almacén de otra empresa o tenant → `404`;
> usuario con acceso A+B bajo contexto A no opera pedidos de B; ningún permiso otorga empresa.
>
> **R-D0-03-11.** Máquina de estados objetivo del pedido (Spec 030 la implementa):
> `DRAFT → SUBMITTED[reserva] → CREDIT_PENDING → APPROVED → RELEASED → PREPARING → SHIPPED → CLOSED`;
> terminales `CANCELLED`, `REJECTED`, `EXPIRED`; `REVERT_TO_DRAFT`. `RELEASED` renombra al actual
> `RESERVED`. `RELEASED` es el estado que habilita la cola de 031.
>
> **R-D0-03-12.** Backorder, sustitución, prioridad entre pedidos, pedido multi-almacén y reserva
> sobre mercancía en tránsito son **FUTURE**: el modelo (reserva por línea en base, `trigger`
> persistido) los admite sin rediseño; la Spec 030 no los implementa ni los insinúa con estados.

## Ciclo de vida

```
 DRAFT ──confirmar──► SUBMITTED ──► CREDIT_PENDING ──► APPROVED ──► RELEASED ──► PREPARING ──► SHIPPED ──► CLOSED
   ▲      [reserva]       │              │               │            │            │            [FULFILLED]
   │                      │ rechazo      │ rechazo       │            │            │
   │                      ▼              ▼               │            │            │
   │                   REJECTED [libera]                 │            │            │
   │                      │ TTL          │ TTL           │            │            │
   │                      ▼              ▼               │            │            │
   │                   EXPIRED [libera + pedido EXPIRED]  │            │            │
   └────── REVERT_TO_DRAFT [libera, aprobación obsoleta] ◄┴────────────┘            │
                                                                                     │
        CANCELLED [libera todo lo ACTIVE] ◄── desde SUBMITTED · CREDIT_PENDING · APPROVED · RELEASED · PREPARING
```

## Consecuencias

| Dimensión | Impacto |
|---|---|
| Backend (030) | Mover el disparo; renombrar estado; `REVERT_TO_DRAFT`; cancelación desde estados de crédito; liberación atómica; `FULFILLED` en despacho; bloqueo de fila; permiso `ventas:submit`; `expire` consciente del pedido; auditoría en 003 |
| Base de datos (030 sobre 023) | `reservations`: `source_type`, `source_id`, `source_line_id`, `trigger`, `oversell`, `released_at`, `released_by`, `release_reason`; índice único parcial por línea activa; `CHECK ≥ 0`. `inventory_balances`: unicidad de clave. `companies`/configuración: `reservation_ttl_days`. Rename `RESERVED → RELEASED` en `sales_orders.status` |
| Frontend (030) | Mensaje de insuficiencia por línea al confirmar; reversión a borrador con motivo; disponible vs. reservado; pantalla de reservas con trigger y motivo |
| 031/032 | Reciben pedido `RELEASED` con reservas por línea; picking parcial libera diferencia con incidencia |
| 033/034/035 | Sin cambio de contrato; 035 consume (`FULFILLED`) |
| 047 | Propietaria del planificador para expiración periódica (solo relevante con TTL) |
| QA | Prueba de carrera en PostgreSQL; sobreventa autorizada; liberaciones; base con presentación; multiempresa; idempotencia |
| Seguridad | Refuerza P6 y ARCH-MC-001 |
| Fiscal | Ninguno |

## Configuración

| Parámetro | Ámbito | Valores | Defecto |
|---|---|---|---|
| `reservation_ttl_days` | empresa | entero ≥ 1 o `NULL` | `NULL` |
| `policies.allow_negative` | almacén (existente) | booleano | `false` |
| Políticas `SALES_CREDIT` | empresa (Spec 045) | según 045 | sin política = contado |

No configurable: disparador, parcial, backorder, prioridad, dimensión.

## Migración / compatibilidad

`SAFE_MIGRATION`: columnas nuevas con defecto, backfill de `source_*` desde `source_document`,
`trigger = LEGACY_CREDIT_APPROVAL` en reservas existentes (conservan su semántica), rename
`RESERVED → RELEASED`. `MANUAL_REVIEW_REQUIRED`: pedidos en `SUBMITTED`/`CREDIT_PENDING` en el
momento de migrar carecen de reserva bajo la nueva semántica; se listan y se revierten/cancelan a
mano. La migración no reserva por ellos. Las reservas históricas nunca se reinterpretan (P5).

## Implicaciones de prueba (criterios de aceptación de 030)

- [ ] Dos transacciones concurrentes sobre la última unidad en PostgreSQL: exactamente una confirma.
- [ ] `qty_available` nunca negativo sin `allow_negative`; con él, ambas reservas `oversell = true`.
- [ ] Confirmar reserva en cantidad base con presentación (caja ×12 → 12).
- [ ] Confirmar sin almacén → `422 WAREHOUSE_REQUIRED`; sin base → `422 UOM_NOT_RESOLVED`.
- [ ] Insuficiencia en una línea → nada reservado, pedido `DRAFT`, detalle por línea.
- [ ] Cancelar, rechazar crédito y revertir liberan en la misma transacción; reintentos no restan dos veces.
- [ ] Revertir obsoleta la solicitud de crédito (045) y reemitir la vuelve a abrir.
- [ ] Despacho deja la reserva `FULFILLED`.
- [ ] Con TTL: expirar deja reserva `EXPIRED` y pedido `EXPIRED`; sin TTL: nada expira.
- [ ] Contexto A + pedido B (usuario AB) → `404`; almacén de B bajo pedido A → `404`; cross-tenant → `404`.
- [ ] Convertir cotización sigue sin reservar (029).
- [ ] Cada reserva/liberación produce su evento de auditoría con el contrato completo.
- [ ] Migración: reservas legadas marcadas y conservadas; pedidos en vuelo listados para revisión.

## Alternativas rechazadas (registro)

A, C, D, E, F — ver tabla de alternativas y `d0-03-checkpoint/d0-03-reservation-options.md`.

## Historial

| Versión | Fecha | Estado | Contenido |
|---|---|---|---|
| v1 | 2026-08-29 | APPROVED · CLOSED_WITH_CONFIGURATION_PENDING | Arquitectura F (configurable) con defecto D («liberar el pedido»); OQ-03 abierta |
| **v2** | **2026-09-02** | **APPROVED · ACTIVE · CLOSED** | Disparador fijo `ORDER_CONFIRMATION`; política completa; OQ-03 resuelta; OQ-04 FUTURE |

## Estado final

**APPROVED · ACTIVE.** Clasificación de cierre: **CLOSED**.
