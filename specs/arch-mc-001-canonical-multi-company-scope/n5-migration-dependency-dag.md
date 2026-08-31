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

---

# LO QUE N5 EJECUTÓ REALMENTE

Añadido al cerrar N5. El orden planificado se respetó; lo que cambió fue el
tamaño de cada ola, porque varias dependencias resultaron estar ya resueltas y
otras aparecieron donde no se esperaban.

## Orden ejecutado

```
raíces de autoridad  →  maestros
      ↓
tesorería  →  compras/CxP  →  ventas/CxC  →  inventario
      ↓
regulatorio  →  fiscal P0
      ↓
auditoría y eventos (transversal)
      ↓
remediación 045  →  remediación 046
      ↓
barrido de seguridad  →  regresión global
```

## Dependencias que resultaron ser más baratas de lo previsto

**Ventas heredó la corrección de compras.** `apply_to_cxc` delega en el mismo
`apply_source`, así que arreglar el cruce de aplicaciones en CxP lo arregló
también en CxC. Se probó igualmente en ambas direcciones: delegar no es lo mismo
que estar probado.

**Fiscal encontró sus guardas ya puestas.** `reserve_number` y `assign_control`
comparaban la empresa desde antes. Las trece pruebas del bloque documentan que
funciona, sin haber requerido cambios.

## Dependencias que aparecieron donde no tocaba

**Inventario destapó organización.** La prueba de control —la que existía solo
para confirmar que el fixture funcionaba— reveló que el listado de almacenes
admitía cualquier empresa del tenant. Organización no estaba en la ola de
inventario; entró por la puerta de atrás.

**El barrido transversal destapó el rastro.** Seis dominios habían dado por
buena su auditoría antes de que se descubriera que organización no anotaba la
empresa en absoluto.

## Contratos que N5 deja escritos para otras fases

### Spec 052 — Instalador

`MANDATORY_PER_INSTALLATION_PREFLIGHT`

Toda instalación existente debe pasar el preflight de `app/core/mc/` antes de
actualizar. No es opcional y no depende de que el cliente crea tener una sola
empresa: el preflight es lo que decide si la tiene.

Hoy no hay ninguna instalación desplegada —`N4 Real Backfill = NOT_APPLICABLE`—
y por eso el contrato se escribe ahora, cuando aún no hay nada que migrar.

### Spec 053 — Actualizador

Respaldo verificado **antes** de cualquier migración que toque `company_id`. La
expansión de N3 es reversible; una normalización de datos, no.

### N8 — Contrato

`X-Kontrol-Company` no aparece en OpenAPI: la dependencia lee la cabecera del
`Request` en lugar de declararla como parámetro, así que FastAPI no la documenta.
Funciona, y 121 pruebas la usan, pero un consumidor que lea solo el contrato no
sabría que existe.
