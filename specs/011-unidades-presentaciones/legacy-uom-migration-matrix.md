# MATRIZ DE MIGRACIÓN LEGADA — SPEC 011

**Obligatoria (§101).** Aplica al histórico la disciplina de clasificación que
las Specs 045 y 008 establecieron: **no se inventa historia; se clasifica y la
clase decide.**

---

## 1. Evidencia disponible — verificada, no supuesta

La pregunta que gobierna todo el backfill es: **¿pudo alguna línea histórica
haberse registrado en una presentación distinta de la unidad base?**

| Comprobación | Resultado | Consecuencia |
|---|---|---|
| ¿Existe endpoint que cree presentaciones? | **No.** `Presentation` no tiene una sola ruta en la API | Ninguna presentación pudo crearse por la aplicación |
| ¿Alguna migración o seed inserta presentaciones? | **No.** `0002_maestros` solo crea la tabla | Ninguna presentación pudo crearse por despliegue |
| ¿Alguna línea referencia `presentation_id`? | **No.** 0 de 21 líneas tienen la columna | Ninguna línea pudo declararla |
| ¿Se escribe `unit_id` en movimientos? | **No.** `inventory/service.py:382` pasa `unit_id=None` literal | La unidad nunca se capturó |
| ¿Se escribe `unit_id` en requisiciones? | Solo si el cliente lo envía; el frontend no lo envía | Casi con certeza nulo |
| ¿Lee alguien `unit_conversions`? | **No.** Un `POST` la escribe; nada la lee | El maestro de conversiones nunca se aplicó |

> **Conclusión probatoria.** No existiendo ningún camino por el que una
> presentación pudiera crearse ni referenciarse, **ninguna línea histórica pudo
> expresarse en una presentación**. La cantidad histórica está, necesariamente,
> en la unidad en que el usuario la tecleó, sin conversión aplicada.
>
> Esto **no** convierte el factor 1 en un valor seguro por defecto: lo convierte
> en una conclusión **demostrable para un caso concreto**, que es cosa distinta
> (§43). Y sigue sin decirnos *qué unidad* era.

## 2. Reconciliación con `ADR-D0-009`

El ADR autoriza el backfill con «unidad base del producto y
`conversion_factor_snapshot = 1`, marcadas `uom_source = LEGACY_ASSUMED_BASE`»,
y añade: **«Es una suposición, y queda registrada como tal.»**

Esta Spec **no contradice** el ADR: lo **refina** con la disciplina de clases que
no existía cuando se aprobó. La marca `LEGACY_ASSUMED_BASE` deja de aplicarse en
bloque y pasa a aplicarse **solo donde el producto tiene una unidad base
declarada**. Donde no la tiene, suponerla sería inventar.

> **R-011-4.** `conversion_factor_snapshot = 1` solo se escribe cuando puede
> demostrarse que la cantidad transaccional coincide con la unidad base de esa
> línea. Nunca como valor por defecto técnico.

## 3. Las cuatro clases

### A · `DETERMINISTIC_BACKFILL`

El producto de la línea tiene `base_unit_id` declarado, y no existe ni pudo
existir presentación alguna.

| | |
|---|---|
| **Acción** | `uom_id` = unidad base del producto · `presentation_id` = `NULL` · `conversion_factor_snapshot` = 1 · `base_quantity` = `quantity` |
| **Marca** | `uom_source = LEGACY_ASSUMED_BASE` |
| **Por qué es seguro** | La cantidad no pudo estar en otra unidad: no había forma de expresarla |

### B · `RECONSTRUCTIBLE_WITH_EVIDENCE`

El producto no declara unidad base, pero **una única** unidad puede derivarse de
evidencia existente y unívoca:

| Orden | Fuente | Condición |
|---|---|---|
| 1 | `inventory_movements.unit_id` del mismo producto | Un único valor no nulo para ese producto |
| 2 | `purchase_requisition_lines.unit_id` del mismo producto | Un único valor no nulo |
| 3 | `catalog_items.billing_unit_id` | Presente y única |

Dos valores distintos **no** se resuelven eligiendo el más frecuente: degradan a
clase C.

| | |
|---|---|
| **Acción** | `uom_id` = la unidad derivada · factor 1 · `base_quantity` = `quantity` |
| **Marca** | `uom_source = LEGACY_RECONSTRUCTED` |
| **Reporta** | Fila, tabla, unidad asignada y **la regla concreta** que la produjo |

### C · `AMBIGUOUS`

El producto no declara unidad base y la evidencia ofrece **más de una**
interpretación, o ninguna.

| | |
|---|---|
| **Acción** | `uom_id` = `NULL` · `base_quantity` = `NULL` · `quantity` **intacta** |
| **Marca** | `uom_source = LEGACY_UNRESOLVED` |
| **Consecuencia** | La línea queda **legible y marcada**, nunca reinterpretada. No entra en ningún cálculo de saldo base hasta que una persona la resuelva |
| **Reporta** | Fila, producto, candidatas encontradas, motivo de la ambigüedad |

> No se asigna «la unidad más probable». Una cantidad sin unidad conocida es un
> dato incompleto **honesto**; una cantidad con la unidad equivocada es un dato
> **falso**, y es peor.

### D · `NON_RECONSTRUCTIBLE_FISCAL`

La línea pertenece a un **documento fiscal emitido** (`sales_invoice_lines`,
`supplier_invoice_lines`) y cae en clase C.

| | |
|---|---|
| **Acción** | **Ninguna escritura sobre la línea.** Se registra la incidencia |
| **Marca** | `uom_source = LEGACY_UNVERSIONED` |
| **Bloqueo** | Si el recuento supera el umbral declarado en `plan.md`, la migración **aborta** y exige revisión manual |

Un documento fiscal emitido es una declaración ante la administración tributaria.
Anotarle una unidad supuesta altera el significado de un documento que ya produjo
efectos legales. **No se toca** (§47).

---

## 4. Matriz por tabla

| Tabla | Campo actual | Evidencia disponible | Backfill esperado | Riesgo | Estrategia |
|---|---|---|---|---|---|
| `inventory_movements` | `quantity` `Float`, `unit_id` nulo | `base_unit_id` del producto | A, si no B | Medio | Clasificar; es la fuente para reconstruir otras |
| `reservations` | `quantity` | Producto | A / B / C | Bajo | Reserva viva: si queda C, se marca y se revisa |
| `transfer_lines` | 2 cantidades | Producto | A / B / C | Medio | Ambas cantidades comparten unidad |
| `stock_count_lines` | 3 cantidades | Producto + `warehouse_locations` | A / B / C | Medio | Conteos cerrados no se reescriben |
| `inventory_adjustments` | `quantity` | Producto | A / B / C | Medio | — |
| `purchase_requisition_lines` | `quantity`, `unit_id` opcional | **`unit_id` propio si existe** | A directa si `unit_id` presente | Bajo | Única tabla con evidencia propia |
| `supplier_quote_lines` | `quantity` | Producto | A / B / C | Bajo | — |
| `purchase_order_lines` | 2 cantidades, `snapshot` Text | Producto; `snapshot` **no es fuente** | A / B / C | Medio | El `snapshot` lo envía el cliente: no es autoridad |
| `goods_receipt_lines` | 3 cantidades | Producto + orden | A / B / C | Medio | Debe cuadrar con la orden |
| `supplier_invoice_lines` | `quantity` | Producto | A / B / **D** | **Alto** | Documento fiscal: clase C degrada a D |
| `purchase_return_lines` | `quantity` | Producto + recepción | A / B / C | Bajo | — |
| `sales_quote_lines` | `quantity` | Producto | A / B / C | Bajo | — |
| `sales_order_lines` | `quantity`, `snapshot` Text | Producto | A / B / C | Medio | — |
| `pick_list_lines` | `quantity` | Producto + pedido | A / B / C | Bajo | — |
| `shipment_lines` | `quantity` | Producto + pedido | A / B / C | Medio | — |
| `sales_invoice_lines` | `quantity` | Producto | A / B / **D** | **Alto** | Documento fiscal emitido |
| `sales_return_lines` | `quantity` | Producto + factura | A / B / **D** si la factura es D | **Alto** | Nota de crédito: efecto fiscal |
| `permit_instances` | `quantity` | Permiso regulatorio | `uom_id` solo | Bajo | `CONTRACT_ONLY` |

---

## 5. Conversión de tipo — riesgo independiente

Las **31 columnas** de cantidad y factor son `Float`. Convertirlas a `NUMERIC`
es un cambio de esquema con riesgo propio, distinto del backfill semántico:

- `Float` puede haber almacenado `0.30000000000000004` donde el usuario escribió
  `0.3`. La conversión **no** debe redondear en silencio: se convierte con la
  precisión declarada y se **reporta** toda fila cuyo valor cambie al convertir.
- Es la misma familia de defecto que `KQA-100` (`Decimal + float`), que SQLite
  ocultó y solo apareció en una corrida funcional.
- Va en una migración **separada** de la de columnas nuevas, para que un fallo en
  una no arrastre a la otra.

---

## 6. Reporte de backfill (§46)

| Campo | Contenido |
|---|---|
| `total_lines_checked` | Todas las líneas de las 17 tablas |
| `deterministic` | Clase A |
| `reconstructed` | Clase B, con la regla aplicada |
| `ambiguous` | Clase C, con las candidatas encontradas |
| `non_reconstructible` | Clase D, fiscales intactas |
| `assigned_base_unit` | Recuento por unidad asignada |
| `assigned_presentation` | Debe ser **0**: ninguna presentación pudo existir |
| `factor_snapshot` | Distribución; debe ser 1 en A y B |
| `manual_review` | Filas que exigen decisión humana |
| `migration_blocked` | Booleano |
| `float_precision_changes` | Filas cuyo valor numérico cambió al pasar a `NUMERIC` |

Detalle por fila para todo lo que no sea clase A: tabla, `row_id`, `company_id`,
producto, clase, acción, justificación. Sin importes, nombres de tercero ni datos
comerciales: no son necesarios para auditar una unidad.

Invariante: `deterministic + reconstructed + ambiguous + non_reconstructible =
total_lines_checked`.

---

## 7. Qué se prueba

Los seis casos de `test-plan.md` §5, sobre PostgreSQL real y con datos sembrados
a propósito, incluido el caso que debe **bloquear**.
