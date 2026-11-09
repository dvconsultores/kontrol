# Contrato de gastos y distribución de costo de importación

**Spec dueña:** 018 Importaciones, sobre la autoridad de costos de la Spec 003/026 (`CostLayer`, `CostingProfile`).
**Estado:** gastos, distribución y aplicación entregados (ciclo 4B, 2026-11-09). Diseño técnico en `spec018-landed-cost-delta.md`.

Clasificación usada:

- `SOURCE_BACKED`: lo dice una fuente del sponsor o una norma vinculante.
- `DERIVED_TECHNICAL_DECISION`: la decide Claude porque no altera un resultado de negocio. Se puede revisar sin rehacer datos.
- `MATERIAL_BUSINESS_DECISION`: cambia cuánto cuesta un producto. No se elige en silencio; `DEFAULT = NONE`.
- `OWNER_PRODUCT_DECISION`: la decidió la dueña. No es `SPONSOR_SOURCE_BACKED`: las fuentes del sponsor no lo dicen.

## Qué dicen las fuentes

| Fuente | Qué aporta |
|---|---|
| DOCX de Importaciones | Nada sobre gastos, distribución ni costos. Solo cita anticipo o pago, factura proforma y factura |
| Modelo de Datos §5 | `CostLayer` tiene `quantity_in`, `quantity_remaining`, `unit_cost`, `currency`, `fiscal_rate`, `landed_cost`. No define su fórmula |
| Documento Maestro | Exige moneda de denominación, moneda de pago y tasa histórica |
| Roadmap B-032 | «Gastos de importación distribuidos por criterio configurable e incorporados a las capas de costo». No enumera criterios |
| Roadmap DEC-09 | Costos de importación: decisión abierta |

## Campos

| Campo | Regla | Clase |
|---|---|---|
| `EXPENSE_TYPE` | `DIRECT_IMPORT_EXPENSE` o `LINKED_SUPPLIER_INVOICE`. El concepto es texto del usuario: no hay catálogo de tipos inventado | Encargo de la dueña; lista `DERIVED_TECHNICAL_DECISION` |
| `SOURCE` | Registro directo en el expediente, o factura de proveedor existente sin duplicarla | Encargo de la dueña |
| `CURRENCY` | Código del maestro de monedas de la empresa. En factura vinculada, la de la factura | `SOURCE_BACKED` |
| `AMOUNT` | Decimal exacto, mayor que cero, dos decimales. En factura vinculada lo declara el operador, y la suma de lo asignado no supera el total de la factura | `DERIVED_TECHNICAL_DECISION` |
| `EXCHANGE_RATE` | Instantánea de la Spec 038 (`capture_rate_snapshot`) hacia la moneda funcional, a la fecha del gasto. Sin tasa, rechazo `RATE_NOT_AVAILABLE`. Misma moneda: identidad declarada como tal, no una tasa supuesta | Norma `SOURCE_BACKED`; fecha `DERIVED_TECHNICAL_DECISION` |
| `FUNCTIONAL_AMOUNT` | `AMOUNT × tasa`, a dos decimales con el redondeo de Tesorería (`ROUND_HALF_EVEN`) | `DERIVED_TECHNICAL_DECISION` |
| `ALLOCATION_CRITERION` | `VALUE`, `QUANTITY` o `MANUAL`, por gasto, sin default | `OWNER_PRODUCT_DECISION` DM-IMP-COST-01 |
| `CRITERION_SOURCE` | Selección explícita del usuario autorizado antes del preview | `OWNER_PRODUCT_DECISION` DM-IMP-COST-01 |
| `ALLOCATION_BASE` | Valor o cantidad por línea, o importe manual. Peso y volumen no disponibles: el maestro no los guarda de forma confiable | `OWNER_PRODUCT_DECISION` DM-IMP-COST-01 |
| `ROUNDING_POLICY` | Conversión de moneda: definida arriba. Reparto: `LARGEST_REMAINDER` | `OWNER_PRODUCT_DECISION` DM-IMP-COST-02 |
| `RESIDUAL_POLICY` | Mayor fracción residual; empate por orden o id estable de línea; `SUM(asignado) = gasto` | `OWNER_PRODUCT_DECISION` DM-IMP-COST-02 |
| `TARGET_LINES` | Capas con `receipt_ref = RECEIPT:<id>` de las recepciones de la orden del expediente | `DERIVED_TECHNICAL_DECISION` |
| `APPLICATION_STATUS` | `APPLIED` o `REVERSED` por aplicación; doble aplicación vigente impedida por índice único parcial | `DERIVED_TECHNICAL_DECISION` |
| `APPLIED_AT`, `APPLIED_BY` | Se registran al aplicar; también `REVERSED_AT`, `REVERSED_BY` y motivo | `DERIVED_TECHNICAL_DECISION` |
| `REVERSIBILITY` | Gasto: se anula con motivo, sin borrarse. Aplicación: reversible solo si ninguna capa afectada se consumió y no hay dependencia posterior incompatible | Gasto `DERIVED_TECHNICAL_DECISION`; aplicación `OWNER_PRODUCT_DECISION` DM-IMP-COST-03 |
| `AUDIT_EVENT` | `IMPORT_EXPENSE_REGISTERED`, `IMPORT_EXPENSE_VOIDED` | `DERIVED_TECHNICAL_DECISION` |

Doble aplicación: la impide un índice único parcial en base de datos, verificado también con dos aplicaciones concurrentes.

## Decisiones de la dueña

Todas `OWNER_PRODUCT_DECISION`, 2026-11-09. `MATERIAL_DECISION_REQUIRED = 0`. Las fuentes del sponsor no las fijan.

| Decisión | Estado | Regla |
|---|---|---|
| DM-IMP-COST-01 | RESOLVED | Criterio configurable por gasto: `VALUE`, `QUANTITY` o `MANUAL`. `DEFAULT_ALLOCATION_CRITERION = NONE`: se elige de forma explícita antes del preview. `WEIGHT` y `VOLUME` no disponibles; esos atributos no se inventan |
| DM-IMP-COST-02 | RESOLVED | `LARGEST_REMAINDER`: asignación exacta, redondeo a la precisión contractual, residuo por mayor fracción y empate estable por orden o id de línea. `SUM(ALLOCATIONS) = EXPENSE_AMOUNT` |
| DM-IMP-COST-03 | RESOLVED | `BLOCK_RETROACTIVE_APPLICATION`: si alguna capa afectada tiene `quantity_remaining < quantity_in`, la aplicación se bloquea y se explica por qué. No se reescribe el costo de venta ni se crean variaciones ficticias. Reversión solo sin consumo y sin dependencia posterior incompatible |
| DM-IMP-COST-04 | RESOLVED | Solo importes marcados de forma explícita como `CAPITALIZABLE` entran al landed cost. `TAX_CAPITALIZATION_DEFAULT = NONE`. Lo indeterminado no se aplica. Se convierte a la moneda de valoración con la tasa histórica válida y se incorpora a `CostLayer`, sin un segundo cálculo de costo de venta. Se conservan importe y moneda originales, tasa, importe de valoración, clasificación y trazabilidad |

**Resuelto en el ciclo 4B:** `landed_cost` es el importe total de la capa; el motor existente (`_consume_cost`, `valuation`) usa el costo efectivo `unit_cost + landed_cost / quantity_in`, sin un segundo motor.

## Lo que ya existe

- Registro y anulación de gastos, directos o vinculados a factura, con moneda, tasa histórica y documento de soporte del expediente.
- Totales por moneda y en moneda funcional.
- Vista de las capas de costo afectables: producto, cantidad, restante, costo actual, moneda y consumo.
- Aviso visible: «Distribución aún no disponible», sin simular ningún reparto.

## Defecto corregido durante el inventario

`accept_receipt` creaba la capa con `currency="VED"` fijo, aunque la orden estuviera en otra moneda: el costo quedaba con la moneda equivocada. Pasa a usar la moneda de la orden. Las capas ya existentes no se reparan: reparar datos exige decisión aparte.

## Atribución de ubicación (IMPORT-PUTAWAY-ATRIBUCION)

La capa se enlaza por la recepción (`RECEIPT:<id>`), no por el movimiento de ubicación. Un put-away fuera del expediente no afecta el costo ni su trazabilidad, así que la deuda se conserva sin resolverla aquí.
