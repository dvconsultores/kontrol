# DAG DE DEPENDENCIAS PARA N5

Derivado de las claves foráneas reales, no del número de Spec.

## 1. Regla

> Ninguna entidad se migra antes que su autoridad.

Una hija que deriva su empresa de la cabecera necesita que la cabecera esté
normalizada primero. Migrarla antes daría por buena una empresa que aún no es
correcta.

## 2. Grafo

```
                    ┌─ companies · branches · warehouses   (ya correctas, Spec 008)
OLA A · autoridades ┤
                    └─ user_scopes · user_roles            (acceso)
                              │
OLA B · maestros ─────────────┤ parties · catalog_items · units_of_measure
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
OLA C · compras        OLA D · inventario    OLA E · ventas
 requisitions           balances              quotes
 orders                 movements             orders
 receipts               lots · serials        shipments
 supplier_invoices      counts                invoices
        │                     │                     │
        └─────────┬───────────┴─────────────────────┘
                  ▼
        OLA F · financiero
         ap_payments · bank_accounts
         bank_transactions · cash_sessions
         reconciliations
                  │
                  ▼
        OLA G · FISCAL  (P0)
         tax_profiles · fiscal_number_series
         control_number_batches · control_numbers
         fiscal_documents · fiscal_periods
         withholding_rules · tax_return_batches
                  │
                  ▼
        OLA H · regulatorio · auditoría · eventos · informes
```

## 3. Por qué fiscal no va primero, siendo P0

Fiscal tiene **prioridad de validación**, no de ejecución.

Un `FiscalDocument` alcanza su empresa a través de la factura de venta, que la
alcanza a través de su sucursal. Migrar el documento fiscal antes que esa cadena
sería atribuirle una empresa que todavía no es correcta: exactamente el error que
esta remediación corrige, cometido con la mejor intención.

Fiscal se migra **en cuanto sus autoridades estén normalizadas**, no al final por
inercia.

## 4. Prerrequisitos de la ola fiscal

| Prerrequisito | Estado |
|---|---|
| `companies`, `branches`, `warehouses` correctas | ✅ ya lo estaban |
| Maestros normalizados (ola B) | ⏳ pendiente de N5 |
| Ventas normalizada (ola E) | ⏳ pendiente de N5 |
| Compras normalizada (ola C) | ⏳ pendiente de N5 |
| Financiero normalizado (ola F) | ⏳ pendiente de N5 |
| **0 `MC-E` fiscal sin resolver** | ⛔ **hay 1 en el fixture** |

El último es el que manda: mientras exista un `MC-E` fiscal, su ola no se
ejecuta, aunque todo lo demás esté listo.

## 5. Puertas entre olas

Tras cada ola, antes de la siguiente:

1. Migraciones aplicadas sin error.
2. Pruebas del dominio en verde.
3. Aislamiento A/B probado en ese dominio.
4. Ningún escritor incorrecto nuevo.

No se espera al final para descubrir una mezcla.
