# D0-03 — CONVERGENCIA DEL CHECKPOINT

| Puerta | Exigido | Resultado |
|---|---|---|
| Decisión | explícita, literal | `RESERVATION TRIGGER = ORDER_CONFIRMATION` (ADR-D0-003 v2 §Decisión) |
| ADR | ACTIVE si cierra | `ADR-D0-003` v2 · **APPROVED · ACTIVE** (2026-09-02); v1 superada en R-D0-03-1 y R-D0-03-4 |
| Requisitos | 30 cubiertos | 30/30 (`traceability-matrix.md`) |
| Trazabilidad | 100 % | 100 %, 0 huérfanos |
| OQ materiales | 0 | 0 — OQ-03 resuelta por decisión de producto (residuo `reservation_ttl_days` es CONFIG); OQ-04 FUTURE explícito |
| Estado de Spec 030 | justificado | `READY_FOR_IMPLEMENTATION` — ver revalidación abajo |
| Cambios de código | 0 | `git diff --stat -- resources/backend resources/frontend resources/backend/alembic` = 0 archivos |
| Nueva Spec / Gate | ninguna | ninguna creada |
| Criterio §79 (20 elementos) | todos decididos | 20/20 (Decision §2, §3, §6, §7) |

## Revalidación de bloqueos de la Spec 030

| Bloqueo | Estado | Evidencia |
|---|---|---|
| Dependencia 012 (maestros comerciales, política de crédito) | satisfecha | `SPEC 012 — COMPLETE / CONVERGED` |
| Dependencia 045 (motor de aprobaciones) | satisfecha | `COMPLETE / CONVERGED`; `SALES_CREDIT` integrado |
| Dependencia 023 (motor de saldos y reservas) | satisfecha para lo que 030 necesita | `reserve/release/expire/get_available` existen; 030 añade unicidad, bloqueo y columnas sobre ese motor, no otro |
| Dependencia 029 (pedido con origen) | satisfecha | `SPEC 029 — COMPLETE / CONVERGED` |
| Dependencia 011 (cantidad base) | satisfecha | columnas Spec 011 presentes en líneas y reservas |
| D0-03 | **CLOSED** | este checkpoint |
| Bloqueo legal | ninguno | la reserva no es hecho imponible |
| Bloqueo externo | ninguno | sin servicio externo; TTL desactivado por defecto no requiere planificador |
| Bloqueo de arquitectura | ninguno | CONSTITUTION GATE: PASS |
| OQ material | ninguna | — |

## Lo que cambió de verdad

Antes: D0-03 tenía una arquitectura aprobada («configurable con defecto `ORDER_RELEASED`») cuya
palabra clave significaba dos estados distintos, y una Spec 030 que no podía escribirse sobre cinco
disparadores posibles. El código reservaba tras el crédito porque ahí quedó.

Ahora: un disparador, atado a una transición concreta, con política completa (precondiciones,
cantidad base, todo-o-nada, almacén único, sin parcial ni backorder, sobreventa solo por política de
almacén, reversión a borrador como única modificación, liberación atómica en cancelación/rechazo/
reversión/expiración, consumo en despacho, TTL opcional con dueño, bloqueo en PostgreSQL con prueba
de carrera, idempotencia por línea, auditoría por evento, `RELEASED` como entrega a 031) y catorce
hechos del código clasificados como defectos que la Spec 030 debe corregir.

## Veredicto

`D0-03 — CLOSED`

`SPEC 030 — READY_FOR_IMPLEMENTATION`

La Spec 030 **no** se implementa en este ciclo. Requiere autorización expresa.
