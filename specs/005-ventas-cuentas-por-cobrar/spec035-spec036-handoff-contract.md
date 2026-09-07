# SPEC 035 → SPEC 036 · CONTRATO DE ENTREGA

> Qué queda tras el despacho y qué le corresponde a las devoluciones. No
> implementa la Spec 036.

## Lo que la Spec 035 deja

Un pedido en `SHIPPED`, un `Shipment` en `SHIPPED` con su sello de salida y su
factura, y la mercancía en estado de custodia **`DESPACHADO`** en el Área de
Confirmación de la que salió, con su procedencia entera en el ledger: de qué
ubicación, en qué estado, en qué cantidad base, con qué lote y serial.

| Dato | Dónde |
|---|---|
| Con qué factura salió | `Shipment.invoice_id` |
| Quién autorizó y cuándo | `validated_by` · `validated_at` |
| Quién despachó y cuándo | `dispatched_by` · `dispatched_at` |
| Resultado regulatorio | `regulatory_status` y las `RegulatoryEvaluation` de cada línea |
| A dónde fue y con quién | `destination` · `transport` · `vehicle_id` · `driver_id` |
| Qué salió | `ShipmentLine` en cantidad **base**, con lote y serial |
| La vista comercial de lo que salió | `SalesInvoice`, que es el documento que acompaña a la mercancía (¶106) |

La distinción de las dos últimas filas importa para la 036. La línea de
despacho no lleva presentación ni factor: la derivan de lo que la Spec 032
consolidó, que trabaja en unidad base. Quien quiera saber que fueron *dos cajas
de doce* lo lee en la factura. Una devolución que quiera comparar cantidades
tiene que comparar bases con bases.

## Lo que la Spec 036 tendrá que decidir

`DESPACHADO` es, según el `ADR-D0-010`, mercancía «fuera de existencia». La
matriz de `D0-10` declara **`DESPACHADO → DEVUELTO`** con dueña **036** y la deja
denegada por Spec no construida: es la única salida declarada de un estado
terminal, y su ciclo la activará.

| Cuestión | Por qué no se decide aquí |
|---|---|
| Cuándo y cómo vuelve la mercancía | Es su arista |
| Qué inspección precede al reingreso | La matriz lo dice: `DEVUELTO → DISPONIBLE` · `RECHAZADO` «requiere la inspección previa al reingreso que 036 define» |
| Nota de crédito y su relación con la factura | Es su alcance |
| Qué pasa con la reserva ya `FULFILLED` | La salida la consumió; deshacerlo es su decisión |

**La Spec 035 no revierte un despacho.** No hay «deshacer salida» que borre
historia: lo que salió salió, y corregirlo es una devolución.

## Lo que sigue abierto y no es de la 036

- **`PICKING → DISPONIBLE`**: cómo deshacer una preparación empezada y rechazada.
  Dueña **Spec 032**.
- **`D0-07`**: la emisión fiscal no está homologada legalmente. Dueña la
  validación normativa, no una Spec.
- **Spec 044 sin API oficial**: la validación regulatoria es contra lo
  registrado. `BLOCKED_BY_EXTERNAL_SERVICE`.
