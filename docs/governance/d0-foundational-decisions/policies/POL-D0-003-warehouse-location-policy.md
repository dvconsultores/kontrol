# POL-D0-003 — Política de almacenes y ubicaciones

> Deriva de `ADR-D0-004`. Vinculante para las Specs 008, 019, 021, 022, 023, 025, 031, 032.

## 1. Jerarquía

`Company → Branch → Warehouse → WarehouseZone → Location(aisle, rack, level, position)`

`Location` es la **hoja** y la única entidad que las transacciones referencian.

## 2. Zonas — prohibición de valores fijos

KONTROL **no** define zonas A, B, C, D ni E, ni ninguna lista fija. `zone_type` es catálogo por
empresa. Las zonas del documento de proceso son datos de configuración de ese cliente y, si se
entregan, es como plantilla opcional de arranque — nunca como enum ni como restricción de esquema.

## 3. Modo de gestión por almacén

| `location_managed` | Comportamiento |
|---|---|
| `true` | Todo movimiento exige ubicación; sin ella se rechaza |
| `false` | Los movimientos operan a nivel de almacén |

Permite que un almacén simple siga operando y que la adopción sea gradual, almacén por almacén.

## 4. Estados de ubicación

`ACTIVE` · `INACTIVE` · `BLOCKED` (ni entra ni sale) · `MAINTENANCE` (no entra, sí sale) ·
`FULL` (derivado de capacidad, no editable).

## 5. Alcance de la primera implementación

**MVP:** jerarquía con nivel y posición · `zone_type` configurable · estado · capacidad en unidades
y peso máximo · `pick_sequence` · restricción por producto o categoría.

**Futuro:** volumen y dimensiones · peligrosidad · temperatura · compatibilidad entre productos ·
slotting automático · optimización algorítmica de ruta.

## 6. Integración obligatoria

La ubicación debe llegar con FK real a: `GoodsReceiptLine`, `InventoryMovement`, `InventoryBalance`,
`TransferLine`, `StockCountLine`, `AdjustmentLine`, `PickListLine`, `ShipmentLine`, `Reservation` y
líneas de devolución.

Un maestro de ubicaciones desconectado de las transacciones es una brecha, no un maestro.

## 7. Pendiente

**Configuración de cliente** — OQ-05: mapa físico real del almacén. No es decisión pendiente.
