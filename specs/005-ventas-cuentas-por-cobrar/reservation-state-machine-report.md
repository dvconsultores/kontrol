# SPEC 030 — INFORME DE LA MÁQUINA DE ESTADOS DEL PEDIDO

| Campo | Valor |
|---|---|
| Autoridad | `ADR-D0-003` v2 R-D0-03-11 · FR-030-002 |
| Código | `resources/backend/app/modules/sales/service.py` (`ORDER_TRANSITIONS`, `order_allowed_actions`) |
| Guardia | `tests/test_spec030_architecture.py::test_la_maquina_de_estados_es_la_de_d0_03` |

## Antes (legado)

```
DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED → PREPARING → SHIPPED → CLOSED
                       (reserva aquí, tras el crédito; APPROVED nunca observable)
```

## Ahora

```
DRAFT ──confirmar [reserva todo-o-nada]──► SUBMITTED ──sin solicitud 045──► RELEASED ──► PREPARING ──► SHIPPED ──► CLOSED
                                              │  con solicitud: espera
                                              ├─ release (045 aprobó) ──► RELEASED
                                              ├─ reject  (motivo)     ──► REJECTED   [libera]
                                              ├─ expire  (TTL)        ──► EXPIRED    [libera]
                                              ├─ revert  (motivo)     ──► DRAFT      [libera, solicitud cancelada]
                                              └─ cancel  (motivo)     ──► CANCELLED  [libera]
RELEASED ── revert / cancel ──► DRAFT / CANCELLED [libera]
PREPARING ── cancel ──► CANCELLED [libera lo ACTIVE; 032 deshace lo apartado]
```

| Desde | Destinos | Reserva |
|---|---|---|
| `DRAFT` | `SUBMITTED`, `CANCELLED` | nace en `SUBMITTED` |
| `SUBMITTED` | `RELEASED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `DRAFT` | viva; se libera en todos menos `RELEASED` |
| `RELEASED` | `PREPARING`, `SHIPPED`, `CANCELLED`, `DRAFT` | firme (`expires_at = NULL`) |
| `PREPARING` | `SHIPPED`, `CANCELLED` | viva; el despacho la consume |
| `SHIPPED` | `CLOSED` | `FULFILLED` |
| `CLOSED`, `CANCELLED`, `REJECTED`, `EXPIRED` | — | cerrada |

## Estados eliminados y su migración (0043)

| Estado | Destino | Motivo | Revisión manual |
|---|---|---|---|
| `RESERVED` | `RELEASED` | mismo significado: aprobado y con reserva | no |
| `APPROVED` | `RELEASED` | nunca fue observable (se sobrescribía en la misma llamada) | sí, si existiera alguno |
| `CREDIT_PENDING` | `SUBMITTED` | emitido a la espera de crédito; **sin reserva** bajo el legado | sí: listado en el log de la migración |

## `allowed_actions` (contrato para el frontend)

`confirm`/`submit` (`DRAFT`) · `release` y `reject` (`SUBMITTED`) · `revert` (`SUBMITTED`, `RELEASED`)
· `cancel` (`DRAFT`, `SUBMITTED`, `RELEASED`, `PREPARING`) · `prepare` (`RELEASED`) · `ship`
(`RELEASED`, `PREPARING`) · `close` (`SHIPPED`). `credit`, `approve` y `reserve` desaparecen.

## Invariantes verificados

- Un pedido en `SUBMITTED`/`RELEASED`/`PREPARING` tiene exactamente una reserva `ACTIVE` por línea de
  inventario (`test_spec030_reservation.py`, `test_spec030_postgres_hostile.py::test_5`).
- Ningún estado terminal conserva reservas `ACTIVE` (cancel/reject/revert/expire liberan en la misma
  transacción; `test_cancelar_…`, `test_rechazar_…`, `test_revertir_…`, `test_ttl_…`).
- El despacho no libera: consume (`test_liberar_a_preparacion_no_crea_picking_…`).
- La ruta genérica `/transition` delega: los destinos viejos responden `409`
  (`test_la_transicion_generica_delega_y_los_estados_viejos_no_existen`).
