# D0-10 · MATRIZ DE ESTADOS, PRODUCTORES Y CONSUMIDORES

> Extraída de `ADR-D0-010`, no reconstruida de memoria. Quince estados de **mercancía**. Los siete
> de lote y serial (`FR-003-035`) son otro vocabulario sobre otra entidad y no aparecen aquí.

## Separación de vocabularios

| | Estados de mercancía | Estados de lote y serial |
|---|---|---|
| Autoridad | `ADR-D0-010` | `FR-003-035` |
| Entidad | `InventoryBalance.state` | `InventoryLot.status` · `InventorySerial.status` |
| Cuántos | 15 | 7 |
| Máquina en código | **ninguna** | `LOT_SERIAL_TRANSITIONS` (`inventory/service.py:105`) |
| Etiquetas compartidas | `DISPONIBLE`, `RESERVADO`, `TRANSITO`, `CUARENTENA`, `RECHAZADO`, `DESECHO` | las mismas seis |
| Exclusivas | `ESPERADO`, `RECIBIDO`, `PENDIENTE_CONFIRMACION`, `BLOQUEADO`, `PICKING`, `PREPARADO`, `DESPACHADO`, `DEVUELTO`, `VENDIDO` | `VENCIDO` |

Seis etiquetas coinciden y **ninguna semántica se comparte**: un lote `CUARENTENA` describe el lote
completo; un saldo `CUARENTENA` describe una cantidad en una combinación de almacén, ubicación,
producto, lote y serial. Colisiones de nombre: 6. Mezclas de vocabulario en este documento: 0.

## Catálogo

| Estado | Significado (literal del ADR) | Vendible | Reservable | Productor | Consumidor | Estado |
|---|---|---|---|---|---|---|
| `ESPERADO` | Comprometido en orden o embarque; aún no llegó | No | No | Spec 018 | — | **FUTURE** (R-D0-10-8) |
| `RECIBIDO` | Físicamente recibido, aún no conciliado | No | No | aceptación de recepción (019), cuando 021 cambie el destino | Spec 021 | **ACTIVO al implementar** |
| `PENDIENTE_CONFIRMACION` | En conteo o conciliación | No | No | Spec 021 | Spec 021 | **FUTURE_OWNER** — sin arista declarada |
| `CUARENTENA` | Retenido por calidad o inspección | No | No | resolución de incidencia (020) · diferencia de transferencia (025) | Spec 021 | **ACTIVO** |
| `BLOQUEADO` | Retenido por incidencia abierta o disputa | No | No | Spec 020 | Spec 020 | **ACTIVO** |
| `DISPONIBLE` | Liberado formalmente | **Sí** | **Sí** | liberación formal (021); hoy los diez call sites | 030, ventas, reportes | **ACTIVO** |
| `RESERVADO` | Comprometido a un pedido | No | No | **ninguno** | **ninguno** | **SIN DUEÑO** — ver abajo |
| `PICKING` | En proceso de extracción | No | No | Spec 031/032 | Spec 032 | **FUTURE** |
| `PREPARADO` | Extraído y consolidado, pendiente de confirmación | No | No | Spec 032 | Spec 033 | **FUTURE** |
| `TRANSITO` | En traslado entre almacenes | No | No | Spec 025 | Spec 025 | **FUTURE_OWNER** |
| `DESPACHADO` | Salió físicamente | No | No | Spec 035 | — | **FUTURE** |
| `DEVUELTO` | Reingresado, pendiente de inspección | No | No | Spec 036 | Spec 036 | **FUTURE** |
| `RECHAZADO` | No apto; no se incorpora | No | No | confirmación (021) | Spec 036 | **ACTIVO** |
| `DESECHO` | Destruido o descartado | No | No | Spec 025 | — | **FUTURE** |
| `VENDIDO` | Consumido por venta | No | No | Spec 035 | — | **FUTURE** |

## Estados sin productor

`ESPERADO`, `RESERVADO`, `PENDIENTE_CONFIRMACION`, `PICKING`, `PREPARADO`, `TRANSITO`,
`DESPACHADO`, `DEVUELTO`, `DESECHO`, `VENDIDO`. Diez de quince. Ninguno es defecto: nueve esperan a
su Spec. El décimo, `RESERVADO`, es distinto.

## Estados sin consumidor

`ESPERADO`, `RESERVADO`, `PICKING`, `DESPACHADO`, `DESECHO`, `VENDIDO`.

## `RESERVADO` no tiene dueño y no debe fabricársele uno

`POL-D0-002` §1 lo dice sin ambigüedad: el reservado es «contador sobre el saldo `DISPONIBLE`; **no
es un estado de custodia**». `ADR-D0-003 v2` R-D0-03-5 añade que la reserva «no cambia el estado».

El estado `RESERVADO` del catálogo del ADR es, por tanto, una etiqueta sin proceso que la escriba ni
proceso que la lea. Este checkpoint **no le inventa uno**: queda registrado como estado declarado sin
dueño activo, y ninguna transición de la matriz lo toca. Si alguna vez lo necesita un proceso de
custodia física —mercancía apartada en un muelle, por ejemplo—, será su Spec quien lo active.
