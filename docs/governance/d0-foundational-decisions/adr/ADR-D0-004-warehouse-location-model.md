# ADR-D0-004 — Modelo físico genérico de almacén

| Campo | Valor |
|---|---|
| ID | D0-04 |
| Estado | **APPROVED** |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de datos · Supervisor de almacén · Especialista en picking · Product Owner |
| Specs afectadas | **008** (propietaria) · 019, 021, 022, 023, 024, 025, 031, 032, 036 |

## Problema

`Location` tiene hoy `zone`, `aisle`, `rack`, `capacity`, `restrictions` — y ningún proceso escribe
en ella. Faltan **nivel** y **posición**, que son los dos últimos tramos de la dirección física.
Y el documento de proceso describe zonas A–E de un cliente concreto, que no pueden convertirse en
el modelo del producto.

## Por qué debe decidirse ahora

Sin dirección física completa no hay put-away (022) ni ruta de picking (031/032), que son las dos
Specs que más valor operativo aportan. Y `location_id` ya existe como columna nullable en
movimientos y saldos: cada movimiento que se registre sin ubicación es historia que **no podrá
reconstruirse por posición**.

## Evidencia

- `organization/models.py:94` — `Location` sin `level` ni `position`.
- `inventory/models.py:59,122,194` — `location_id` nullable, nunca escrito.
- `purchasing/service.py:346` — `record_movement` sin `location_id`.
- `sales/models.py:88` — `PickListLine` sin ubicación.
- DOCX Importación §4 — zona → pasillo → rack → nivel → posición.

## Alternativas

**A. Ubicación como cadena estructurada (`"ZA-P03-R02-N04-P05"`).**
Simple. Descartada: no permite consultar por zona, ni calcular una ruta de picking, ni imponer
restricciones por nivel. Convierte una jerarquía en texto.

**B. Jerarquía completa con entidad por nivel (Zone, Aisle, Rack, Level, Position).**
Máxima expresividad. Descartada como modelo transaccional: cinco tablas y cuatro joins para
resolver una ubicación, en un dominio donde el 90 % de las consultas quieren la hoja.

**C. Jerarquía de zonas + `Location` como hoja con sus tramos denormalizados.** ← **RECOMENDADA**
`WarehouseZone` sí es entidad (tiene tipo, política y restricciones propias, y se consulta como
conjunto). Pasillo, rack, nivel y posición son atributos de la hoja `Location`, que es la única
entidad que las transacciones referencian. Una sola FK desde cualquier documento.

## Modelo conceptual

```
Company → Branch → Warehouse → WarehouseZone → Location(aisle, rack, level, position)
                                    │
                                    ├── LocationType        (catálogo por empresa)
                                    ├── LocationStatus      (enum de producto)
                                    └── LocationRestriction (0..n por ubicación o zona)
```

| Entidad | Naturaleza | Configurable por empresa |
|---|---|---|
| `Warehouse` | Existente | Sí |
| `WarehouseZone` | **Nueva** — código, nombre, `zone_type`, política de asignación, orden de recorrido | **Sí, íntegramente** |
| `Location` | Existente, se extiende con `zone_id`, `level`, `position`, `pick_sequence` | Sí |
| `LocationType` | **Nueva** — catálogo por empresa (estantería, piso, cámara, jaula…) | **Sí** |
| `LocationRestriction` | **Nueva** — restricción declarativa aplicable a zona o ubicación | Sí |

### Identificación de la ubicación

Cada `Location` tiene un `code` único por almacén y una **etiqueta legible derivada** de su
jerarquía, del estilo `ALM-01 / ZR-ALTA / P03 / R02 / N04 / POS-05`. La etiqueta es presentación
calculada, no una columna de negocio: el identificador es el `id`, y el `code` es el identificador
humano estable.

## Prohibición explícita de zonas fijas

> **R-D0-04-1.** KONTROL **no** define zonas A, B, C, D ni E, ni ninguna otra lista fija de zonas.
> `zone_type` es un catálogo por empresa. Las zonas del documento de proceso (alta / media / baja
> rotación, incidencias, sobredimensionados) son **datos de configuración de ese cliente** y se
> entregan, si acaso, como plantilla opcional de arranque — nunca como enum del producto ni como
> `CHECK` en la base de datos.

## Estados de ubicación

`ACTIVE` · `INACTIVE` · `BLOCKED` · `MAINTENANCE` · `FULL`

- `BLOCKED` impide entrada y salida (incidencia, inventario en disputa).
- `MAINTENANCE` impide entrada, permite salida (se está vaciando).
- `FULL` es **derivado de la capacidad, no editable a mano**; si no hay capacidad declarada, nunca se alcanza.

## MVP frente a capacidad futura

| MVP REQUIRED (Spec 008) | FUTURE CAPABILITY (no bloquea 008) |
|---|---|
| Jerarquía zona → ubicación con nivel y posición | Volumen y dimensiones |
| `zone_type` configurable | Clase de peligrosidad |
| Estado de ubicación | Rango de temperatura |
| Capacidad simple (unidades) y peso máximo | Reglas de compatibilidad entre productos |
| `pick_sequence` para ordenar el recorrido | Optimización de ruta (algoritmo) |
| Restricción por producto o categoría permitida | Slotting automático por rotación |

No sobreingenierizar: el modelo debe **admitir** lo futuro sin **implementarlo** ahora.

## Integración obligatoria con las transacciones

> **R-D0-04-2.** Un maestro de ubicaciones desconectado de las transacciones es una brecha, no un
> maestro. La ubicación debe llegar, con FK real, a:
> `GoodsReceiptLine` · `InventoryMovement` · `InventoryBalance` · `TransferLine` ·
> `StockCountLine` · `AdjustmentLine` · `PickListLine` · `ShipmentLine` · `Reservation` ·
> líneas de devolución.

> **R-D0-04-3.** La obligatoriedad de la ubicación es **por almacén**: un almacén declarado
> `location_managed = true` rechaza movimientos sin ubicación; uno declarado `false` los admite.
> Esto permite que un almacén simple siga operando sin ubicaciones y que la migración sea gradual.

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Pantallas de zonas y ubicaciones; selector jerárquico; ubicación en recepción, conteo, ajuste, picking |
| Backend | Módulo `organization` se extiende; `inventory` valida ubicación según el almacén |
| Base de datos | 3 tablas nuevas, `locations` extendida, ~10 columnas `location_id` pasan a FK real |
| Integraciones | Ninguna |
| QA | Integridad referencial; rechazo de movimiento sin ubicación en almacén gestionado |
| Seguridad | Ninguno |
| Fiscal | Ninguno |

## Migración / compatibilidad

**`SAFE_MIGRATION`** para el esquema (tablas y columnas nuevas, nullable).
**`BACKFILL_REQUIRED` con `MANUAL_REVIEW_REQUIRED`** para los datos: los movimientos históricos no
tienen ubicación y **no se les debe inventar una**. Se marcan como `location_unknown` y los almacenes
existentes arrancan con `location_managed = false` hasta que el cliente cargue su mapa físico.

## Criterios de aceptación

- [ ] Una ubicación se identifica hasta la posición y su etiqueta legible se deriva de la jerarquía.
- [ ] `zone_type` es catálogo por empresa; no existe ningún enum de zonas en el código.
- [ ] Un almacén `location_managed` rechaza un movimiento sin ubicación.
- [ ] `FULL` se deriva de capacidad y no es editable.
- [ ] Las diez referencias transaccionales son FK reales.

## Estado final

**APPROVED** — decisión técnica y de producto, con evidencia suficiente.
La zonificación real de cada cliente es configuración (OQ-05), no decisión pendiente.
