# Recibido sin confirmar · autoridades

- **Ciclo:** `RECEIVED_UNCONFIRMED_PROJECTION`, 2026-11-13.
- **HEAD de entrada:** `434527e`.
- **Cabeza Alembic:** `0106_open_supply_by_warehouse`.

**Fuentes leídas:**
- `purchasing/{models,service,open_supply}.py`: `accept_receipt`, `confirmar_inventario`, `registrar_conteo` y las transiciones de la recepción;
- `inventory/{states,service}.py`: `ACTIVE_TRANSITIONS`, `SELLABLE_STATES` y `warehouse_sellable_on_hand`;
- `planning/{engine,replenishment,api}.py`.

## Autoridades

```text
PHYSICAL_RECEIPT_QUANTITY_AUTHORITY=goods_receipt_lines.base_quantity_received (coalesce quantity_received)   · Spec 019
ACCEPTED_QUANTITY_AUTHORITY=goods_receipt_lines.base_quantity_accepted (coalesce quantity_accepted)          · Spec 019
REJECTED_QUANTITY_AUTHORITY=goods_receipt_lines.base_quantity_rejected; no entra al inventario               · Spec 019
INVENTORY_CONFIRMATION_AUTHORITY=goods_receipts.confirmation_status (PENDIENTE → CONFIRMADA) +
                                 receipt_confirmations (decisiones RECIBIDO → DISPONIBLE | RECHAZADO)        · Spec 021
WAREHOUSE_AUTHORITY=goods_receipts.warehouse_id (donde está físicamente la mercancía)                         · Spec 019
AVAILABLE_STOCK_AUTHORITY=inventory_balances en estado DISPONIBLE (SELLABLE_STATES) − reservado              · Spec 023 / ADR-D0-010
```

## Lo que hace el código hoy

1. **`accept_receipt`** (Spec 019) hace, para cada línea con cantidad aceptada mayor que 0 y `needs_inventory`, en una sola transacción:
   - asienta `ENTRADA_RECEPCION` en el estado **`RECIBIDO`**, por la cantidad aceptada y en el almacén de la recepción;
   - suma lo aceptado en unidad base a `purchase_order_lines.quantity_received`.

   Por eso lo aceptado deja de ser suministro abierto **en la misma transacción** en la que entra en `RECIBIDO`. La recepción queda `ACCEPTED` o `PARTIALLY_ACCEPTED`, con `confirmation_status = PENDIENTE`.
2. **`RECIBIDO` no es vendible.** `SELLABLE_STATES = {DISPONIBLE}` (`R-D0-10-3`), y el disponible del motor lo lee de `warehouse_sellable_on_hand`.
3. **`confirmar_inventario`** (Spec 021) hace, en una sola transacción y bloqueando la fila de la recepción:
   - reclasifica `RECIBIDO` → `DISPONIBLE` o `RECHAZADO` por las cantidades decididas;
   - fija `confirmation_status = CONFIRMADA`.

   **Es atómica y de una sola vez por recepción:** volver a confirmar da `ALREADY_CONFIRMED`. Dentro de esa vez admite varias decisiones por línea, por ejemplo 90 liberadas y 10 rechazadas.
4. **Ninguna otra ruta de Compras saca mercancía de `RECIBIDO`.** `reclassify` solo se llama desde `confirmar_inventario`; las de Ventas parten de otros estados. Las aristas `RECIBIDO → CUARENTENA/BLOQUEADO` de la Spec 020 están declaradas en la tabla, pero hoy no tienen productor en Compras.
5. **Una recepción no puede cerrarse sin confirmar.** CLOSED exige CONFIRMADA. Una recepción REJECTED no asienta nada.

## Definición de dominio

```text
RECEIVED_UNCONFIRMED(empresa, almacén, producto) =
  Σ coalesce(base_quantity_accepted, quantity_accepted)
  de las líneas de recepción con quantity_accepted > 0 y línea de orden needs_inventory,
  cuya recepción es de la empresa, está en ese almacén (goods_receipts.warehouse_id),
  tiene estado ACCEPTED o PARTIALLY_ACCEPTED y confirmation_status = PENDIENTE
```

Es exactamente lo que la aceptación asentó en `RECIBIDO` y la confirmación todavía no ha decidido. Deja de estar pendiente cuando la Spec 021 confirma la recepción.

**¿Por qué no leer el saldo `RECIBIDO` del ledger?** Porque la confirmación es de una sola vez y puede decidir menos de lo aceptado. Lo que no decidió se queda en `RECIBIDO` en una recepción ya CONFIRMADA, y nadie puede volver a confirmarlo. Contarlo como «en camino» frenaría para siempre la reposición de unas unidades que no llegarán a disponible. Esto queda como deuda de la Spec 021 (`RECEIPT-CONFIRMATION-RESIDUE`) y no se absorbe.

## Sin solapamiento

| Par | Por qué no se solapan |
|---|---|
| AVAILABLE ∩ RECEIVED_UNCONFIRMED = ∅ | Lo pendiente está en `RECIBIDO`, y el disponible solo cuenta `DISPONIBLE`. La confirmación pasa una cantidad de `RECIBIDO` a `DISPONIBLE` y la recepción a CONFIRMADA en la misma transacción |
| OPEN_SUPPLY ∩ RECEIVED_UNCONFIRMED = ∅ | La aceptación suma lo aceptado a `quantity_received`, que es lo que el suministro abierto resta, en la misma transacción en la que lo asienta en `RECIBIDO` |
| AVAILABLE ∩ OPEN_SUPPLY = ∅ | Ya certificado en `OPEN_SUPPLY_BY_WAREHOUSE`: lo abierto todavía no se ha recibido |

**Concurrencia.** El suministro abierto y lo recibido sin confirmar se leen en **una sola sentencia** (`UNION ALL`), así que una aceptación concurrente nunca aparece en los dos. El disponible se lee en una sentencia anterior. Si una confirmación se confirma entre las dos lecturas, sus unidades faltan en ese tick (se cuentan de menos, nunca dos veces) y el tick siguiente converge.

## Rechazado, parcial y almacenes

- **Rechazado en la aceptación** (`quantity_rejected`): no entra al inventario ni a lo recibido sin confirmar. En el suministro abierto sigue la semántica ya certificada (pendiente mientras la orden no se cierre).
- **Rechazado en la confirmación:** pasa a `RECHAZADO`; como la recepción ya está CONFIRMADA, lo recibido sin confirmar es 0.
- **Aceptación parcial** (recibido 100, aceptado 80): lo recibido sin confirmar es 80.
- **Confirmación parcial:** no existe; la confirmación es atómica por recepción. Con aceptado 60, confirmar 40 a DISPONIBLE y 20 a RECHAZADO da disponible +40 y pendiente 0. Varias recepciones de la misma línea, cada una con su propia confirmación, sí dan la secuencia 40 → 30.
- **Almacén:** el de la recepción. Desde la `0106`, una línea con destino solo se recibe en su almacén.

## Decisión material

```text
ACCEPTED_QUANTITY_AUTHORITY_CLEAR=1  CONFIRMATION_AUTHORITY_CLEAR=1  WAREHOUSE_AUTHORITY_CLEAR=1
AVAILABLE_STOCK_AUTHORITY_CLEAR=1  DERIVATION_INSUFFICIENT=0  MIGRATION_REQUIRED=0
MATERIAL_DECISION_REQUIRED=0
```
