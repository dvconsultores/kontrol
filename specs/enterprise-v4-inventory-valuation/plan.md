# Plan · V4 Inventory ledger & valuation integrity

## Constitution gate

| Control | Resultado |
|---|---|
| Spec dueña y autorización | 003-inventario-logistica; prompt de V4 (P2) |
| BLOCKER / CRITICAL / CONTRADICTIONS / OWNER CONFLICT | 0 / 0 / 0 / 0 |
| MATERIAL OQ | 0 para el núcleo. Las decisiones abiertas (congelamiento, pérdida en tránsito, RECHAZADO, histórico) quedan fuera de alcance y no se resuelven en silencio |
| Inmutabilidad (P5) | Ningún movimiento se edita ni se borra; toda corrección es un reverso vinculado |
| Decimal exacto | Valor en `Decimal`; capas con la composición real; sin promedios redondeados que pierdan céntimos |
| Multiempresa | Toda consulta filtra por empresa; almacenes y productos validados por empresa |
| Histórico | `AUTOMATIC_HISTORICAL_RECALCULATION=NO`: sin backfill; los movimientos anteriores a V4 sin registro de consumo se tratan con reglas explícitas o se rechazan |

## Diseño

1. **Registro de consumo.** Cada salida por `record_movement` persiste, por capa consumida, cantidad, costo base,
   parte de landed cost y costo efectivo (`inventory_cost_consumptions`, migración 0129). Las capas guardan su
   movimiento de origen (`cost_layers.source_movement_id`).
2. **Traslado de valor.** La recepción de transferencia restaura en destino ese consumo con la composición real
   (`_restore_from_sources`). `quantity_restored` impide devolver dos veces el mismo costo.
3. **Reverso simétrico.** Entrada → retira sus capas intactas; salida → restaura su consumo; mismo estado,
   ubicación y presentación. Transferencia → `reverse_transfer` (destino retira, origen recupera en cada ubicación).
4. **Concurrencia.** `record_movement` bloquea la fila que descuenta; la transferencia bloquea el ancla del almacén
   (punto de serialización de las reservas) y comprueba el disponible del almacén.
5. **Mercancía ubicada.** La salida de transferencia toma de lo no ubicado libre de reservas y de las ubicaciones
   en orden de secuencia, una salida por ubicación.
6. **Ajustes y conteos.** `apply` en APPROVED; lo encontrado entra al costo vigente del almacén (capas); lo esperado
   del conteo puede salir del ledger; acción `start` para FROZEN → COUNTING.
7. **Recálculo.** `inventario:recompute` (nuevo), auditoría y reservas pendientes de extraer.
8. **Orden FIFO.** Marca de orden estrictamente creciente en capas y consumos (el `now()` del servidor empata
   dentro de la transacción).
9. **Superficie.** Nombres en lugar de UUID en transferencias, movimientos, ajustes y conteos; valor enviado y en
   tránsito; recepción por línea; reversión con motivo.

## Migración

`0130_v4_cost_consumptions` sobre `0129_gov_tre05_retencion` (reencadenada tras integrar TRE-05 de P1; originalmente 0129 sobre 0128): tabla nueva, columna nueva nula, permiso nuevo. Sin
backfill. Probada en PostgreSQL vacío: upgrade → downgrade → upgrade, cabeza única; y la rama de otorgamiento del
permiso con un rol aprobador existente.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Doble consumo de costo (salida + restauración) | `cost_handled_by_caller` solo en recepción y reversión; mutación M5 |
| Devolver costo dos veces | `quantity_restored` con `CHECK`; mutación M6 |
| Interbloqueos | Orden único: saldo → capas (igual que reservas y despacho) |
| Mercancía reservada transferida | Disponible del almacén descuenta reservas; lo no ubicado solo aporta lo libre |
