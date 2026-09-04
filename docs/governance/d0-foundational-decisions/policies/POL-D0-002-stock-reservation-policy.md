# POL-D0-002 — Política de reserva de inventario

> Deriva de `ADR-D0-003` **v2** (2026-09-02, ACTIVE). Vinculante para las Specs 003/023, 029, 030,
> 031, 032, 033, 034, 035, 045, 047. Versión anterior (2026-08-29) superada en §2 y §4.

## 1. Definiciones

| Término | Significado |
|---|---|
| Físico | Unidades presentes en el almacén, cualquiera sea su estado de custodia |
| Reservado | Unidades **base** comprometidas a líneas de pedido emitidas y no extraídas. Contador sobre el saldo `DISPONIBLE`; no es un estado de custodia |
| Bloqueado | Unidades en estados no vendibles del catálogo ADR-D0-010 (`CUARENTENA`, `BLOQUEADO`, `RECIBIDO`, `PENDIENTE_CONFIRMACION`, `TRANSITO`…) |
| **Disponible** | `físico − reservado − bloqueado` = `qty_on_hand − qty_reserved` de la fila `DISPONIBLE` |

Ningún proceso, pantalla o consulta presenta el físico como disponible.

## 2. Disparador

**`RESERVATION TRIGGER = ORDER_CONFIRMATION`** — transición `DRAFT → SUBMITTED` del pedido. Fijo.
Igual para contado, crédito y pedidos sin evaluación de crédito. Cotización y conversión no
reservan. Líneas de servicio no reservan. Reservas manuales (`MANUAL`) son del motor de 003 y no
dependen de pedidos.

| Tipo de pedido | ¿045 abre solicitud? | Trigger | Después |
|---|---|---|---|
| Contado / sin política aplicable | No | `ORDER_CONFIRMATION` | `APPROVED → RELEASED` en la misma transacción |
| A crédito con política aplicable | Sí | `ORDER_CONFIRMATION` | `CREDIT_PENDING`; aprobado → `RELEASED`; rechazado → `REJECTED` + liberación |
| Solo servicios | — | ninguno | sin reserva |

## 3. Precondiciones y cantidad

Almacén obligatorio (`422 WAREHOUSE_REQUIRED`), de la empresa del pedido (`404` si no); cantidad
base resuelta con factor snapshot (Spec 011; `422 UOM_NOT_RESOLVED`); comparación y reserva en
base; se persiste también la cantidad tecleada y su presentación. **Todo o nada por pedido.** Sin
reserva parcial. Sin backorder (FUTURE). Sin pedido sin reserva. Insuficiencia → `409
INSUFFICIENT_AVAILABLE` por línea; el pedido sigue `DRAFT`.

## 4. Vigencia

La reserva vive lo que vive el pedido. Vencimiento por reloj **solo** si la empresa configura
`reservation_ttl_days` (defecto `NULL` = sin expiración) y solo mientras el pedido espera crédito.
Al expirar, reserva y pedido pasan a `EXPIRED` en la misma transacción. Nunca un pedido vivo sin
reserva. Ejecución: endpoint de expiración; periodicidad: planificador de plataforma (Spec 047).

## 5. Concurrencia — regla dura

Dos operaciones no pueden reservar la misma unidad. Garantía en PostgreSQL dentro de la
transacción de confirmación: bloqueo de la fila de saldo (`FOR UPDATE`) antes de leer el
disponible, unicidad de la clave del saldo, índice único parcial por línea activa, `CHECK ≥ 0`,
bloqueos en orden determinista. Prueba automatizada de dos transacciones sobre la última unidad
con exactamente una ganadora. El frontend no es autoridad.

## 6. Sobreventa

Prohibida. Única excepción: almacén con `policies.allow_negative = true`; la reserva se marca
`oversell` y su evento registra el disponible previo. Nunca por carrera.

## 7. Dimensión

`(empresa, almacén del pedido, producto)`; lote/serial solo si la línea los exige. Nunca ubicación.
Un almacén por pedido; sin abastecimiento cruzado. Solo saldo `DISPONIBLE`. La reserva no cambia el
estado de custodia.

> **Consecuencia para el put-away (`D0-14`, 2026-09-04).** Si la ubicación no es dimensión de la
> reserva, entonces **mover mercancía entre ubicaciones no altera el compromiso comercial**. Un
> put-away puro conserva el reservado y el disponible **del almacén**, y no crea, libera, cancela ni
> reasigna reserva alguna. Que hoy el disponible se lea de la fila de ubicación nula es un artefacto
> de que la ubicación siempre fue nula, no una regla de esta política. Asignar una reserva concreta a
> una ubicación sigue siendo de la Spec 031 (§11).

## 8. Consumo, liberación y modificación

| Evento | Efecto |
|---|---|
| Despacho (salida física) | **Consume** → `FULFILLED` |
| Facturación | Ninguno |
| Cancelación del pedido (cualquier estado vivo) | Libera todo lo `ACTIVE`, atómico, idempotente, con motivo |
| Rechazo de crédito | Libera todo, atómico |
| Reversión a borrador (`REVERT_TO_DRAFT`, única forma de modificar) | Libera todo; aprobación obsoleta; reemitir re-reserva |
| Expiración (TTL) | Libera + pedido `EXPIRED` |
| Picking parcial (032) | Libera la diferencia y **genera incidencia**; nunca ajusta el pedido en silencio |
| Liberación manual | Solo reservas `MANUAL`, con `inventario:reserve`, motivo y auditoría |

## 9. Permisos y aislamiento

Emitir/revertir/cancelar: `ventas:submit` (030 lo separa de `ventas:approve`). La reserva es efecto
del sistema. Reserva/liberación manual: `inventario:reserve`. La empresa es la del contexto; el
permiso nunca la sustituye; cross-company, cross-tenant y usuario AB fuera de contexto → `404`.

## 10. Auditoría

`RESERVATION_CREATED / RELEASED / EXPIRED / FULFILLED` con actor, tenant, empresa, pedido, línea,
almacén, producto, cantidad tecleada y base con UOM/presentación/factor, trigger, motivo, estado
anterior y posterior, disponible previo y marca de sobreventa.

## 11. Handoff y fronteras

`RELEASED` habilita la cola de 031. 030 no crea listas de picking, no asigna ubicación, no elige
lote/serial, no confirma (033), no factura (034), no despacha (035).

## 12. Capacidades futuras

Backorder · sustitución · prioridad entre pedidos · pedido multi-almacén · reserva sobre mercancía
en tránsito. El modelo las admite; la Spec 030 no las implementa ni las insinúa.

## 13. Histórico

Toda reserva persiste su `trigger`. Las anteriores a 030 se marcan `LEGACY_CREDIT_APPROVAL` y no se
reinterpretan. Pedidos en vuelo sin reserva al migrar → revisión manual.

## 14. Pendiente

Ninguna decisión de negocio. Configuración de implantación: `reservation_ttl_days` por empresa
(opcional).
