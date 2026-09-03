# SPEC 030 — INFORME DE IDEMPOTENCIA

| Operación repetida | Garantía | Mecanismo | Prueba |
|---|---|---|---|
| Confirmar dos veces el mismo pedido | una reserva por línea | `_lock_order` (`FOR UPDATE` sobre el pedido) + máquina de estados (`SUBMITTED` no admite `SUBMITTED`) + índice único parcial `uq_reservations_active_line` | `test_confirmar_dos_veces_no_duplica_la_reserva` · hostil `test_5` (SQLSTATE 23505) |
| Reintento HTTP de la confirmación | ídem | `Idempotency-Key` vigente en escrituras (ADR-013) + lo anterior | — (cubierto por la máquina) |
| Cancelar dos veces | segundo intento `409`; sin segunda resta | máquina de estados; `release_if_active` ignora lo no `ACTIVE` | `test_cancelar_libera_y_el_segundo_intento_choca_sin_restar_dos_veces` |
| Liberar dos veces una manual | `409 RESERVATION_NOT_ACTIVE` | `release_reservation` exige `ACTIVE` | `test_la_reserva_de_un_pedido_no_se_libera_a_mano` |
| Expirar dos veces | `{0, 0}` | `expire_due_reservations` filtra `ACTIVE` y `expires_at < now` | `test_ttl_opcional_…` |
| Consumir dos veces (despacho) | no-op | `fulfill_reservation` exige `ACTIVE` | `test_liberar_a_preparacion_…` |
| Restar por debajo de cero | imposible | `max(…, 0)` en servicio **y** `CHECK (qty_reserved >= 0)` en PostgreSQL | hostiles `test_6`, `test_7` (SQLSTATE 23514) |
| Dos transacciones sobre el mismo saldo | una gana | `SELECT … FOR UPDATE` (`lock_balance`) | `test_spec030_concurrency.py` |

La liberación en los flujos del pedido usa `release_if_active` (idempotente por diseño); la
liberación manual usa `release_reservation` (estricta, porque el usuario debe saber que ya no había
nada que liberar). Son la misma primitiva `_close_reservation` con distinta política de error.
