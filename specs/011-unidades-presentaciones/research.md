# INVESTIGACIÓN — SPEC 011

## 1. Matriz de estado actual (§7) — leída del código

| Concepto | Existe | Entidad actual | Uso real | Problema | Acción propuesta |
|---|:---:|---|---|---|---|
| Unidad de medida | **Sí** | `units_of_measure` | Un endpoint de listado/alta | Sin `rounding_mode`; `decimals` no se aplica en ningún cálculo | **Extender**: modo de redondeo, dimensión validada |
| Conversión física | **Sí** | `unit_conversions` | `POST` que la escribe; **nada la lee** | `factor` en `Float`; sin validar que ambas unidades compartan dimensión | **Corregir**: `NUMERIC`, restricción de dimensión, y **consumirla** |
| Presentación | **Sí** | `presentations` | **Ninguno: cero endpoints** | Sin factor explícito (`content` es `Float` y ambiguo), sin versión, sin estado, sin `company_id` | **Extender y versionar**; conservar los datos existentes |
| Presentación genérica | No | — | — | «Caja» no existe como concepto reutilizable | **No crear**: el factor es del par producto-presentación (§12). Una presentación genérica sin factor no aporta |
| Factor a unidad base | **No** | — | — | No existe columna alguna | **Crear** en `product_presentation_versions` |
| Unidad base de producto | **Sí** | `catalog_items.base_unit_id` | Se escribe al crear; **nunca se lee** | *Nullable*; ningún cálculo la usa | **Hacer obligatoria** en inventariables; consumirla |
| Unidad de facturación | **Sí** | `catalog_items.billing_unit_id` | Se escribe al crear | No se usa | **Conservar**: es la vía para servicios (CL-011-09) |
| Unidad de compra | No | — | — | — | **No crear entidad**: es la marca `buyable` de la presentación |
| Unidad de venta | No | — | — | — | Marca `sellable` |
| Unidad de inventario | No | — | — | — | Es la unidad base; no necesita entidad propia |
| Código de barras | **Sí** | `barcodes` | Modelo con FK a presentación | — | **No tocar**: pertenece a maestros/025 |
| Snapshot de conversión | **No** | — | — | **0 de 21 líneas** | **Crear**: es el objeto de esta Spec |

### El dato que resume la Spec

`unit_conversions` y `presentations` son maestros **write-only**: uno se escribe
y nadie lo lee; el otro ni siquiera se puede escribir. Es el mismo patrón que el
GAP Analysis bautizó con las Sucursales, y aquí cuesta más caro porque el dato
que falta —la unidad de una transacción— **no es recuperable después**.

---

## 2. Alternativas de modelo (§96)

### Modelo A · Factor directo en el producto

Un `conversion_factor` en `catalog_items`.

**Descartado.** Un producto tiene varias presentaciones a la vez: caja, bolsa y
pallet. Un solo factor no las representa, y forzaría un producto por presentación
—exactamente la duplicación de SKU que §16 prohíbe.

### Modelo B · `ProductPresentation` sin versión

Tabla producto × presentación con `factor_to_base`.

**Descartado como final, adoptado como base.** Resuelve la multiplicidad, pero
editar el factor reescribe el significado de todo el histórico: es precisamente
lo que R-D0-09-4 prohíbe. Sirve de esqueleto, no de solución.

### Modelo C · Conversión de UOM global + conversión de presentación

Dos mecanismos separados: `KG ↔ G` por un lado; `CAJA → 100 UND` por otro.

**Adoptado como capa.** Son conceptos distintos (§33): la conversión física es
universal e inmutable —un kilo siempre serán mil gramos—; la comercial es del
producto y cambia. Mezclarlas obligaría a versionar `KG ↔ G`, que es absurdo, o a
no versionar la caja, que es peligroso.

### Modelo D · Versionado por vigencia

`ProductPresentationVersion` con `factor_to_base`, `valid_from`, `valid_to`.

**Adoptado.** Es lo único que permite que la caja pase de 100 a 120 sin que la
compra del año pasado cambie de significado.

### Decisión: **C + D**

```
UnitConversion                 (física, misma dimensión, sin versión)
ProductPresentation            (qué presentaciones admite el producto)
  └─ ProductPresentationVersion (factor + vigencia)   ← versionado aquí
```

Con **doble protección**: el versionado permite reconstruir el factor de una
fecha, y el snapshot en la línea hace que ni siquiera haga falta consultarlo. El
snapshot es la garantía; el versionado es la trazabilidad. Uno solo no basta:
sin snapshot, un borrado de versión rompería el histórico; sin versionado, no
habría forma de auditar qué factor estuvo vigente cuándo.

---

## 3. ¿Dónde nace el snapshot? (§67, §68)

| Alternativa | Problema |
|---|---|
| Al añadir la línea | Un borrador de hace tres meses quedaría con un factor obsoleto que el usuario nunca vio |
| Al guardar el documento | Igual, con menos margen |
| **Al emitir o aprobar** | **Adoptada.** Coincide con el momento en que el documento adquiere efecto |
| Nunca (recalcular siempre) | Prohibido por R-D0-09-2 |

Mientras el documento es **editable**, la línea muestra y usa la versión vigente,
y cambiar la presentación recalcula. Al **emitir**, el factor se congela y ya no
cambia jamás. Es coherente con cómo KONTROL trata el resto de los snapshots
fiscales.

Caso del §67 resuelto: un borrador con factor 100 al que se le activa el factor
120 antes de aprobarse **se recalcula a 120**, porque el documento todavía no
significaba nada. Una vez aprobado, 120 queda congelado para siempre.

---

## 4. Fecha efectiva (§66)

Se usa la **fecha del documento** (`document_date`), no `created_at`. Una factura
registrada el día 5 con fecha del día 1 debe usar el factor vigente el día 1: es
la fecha que tiene efecto fiscal y comercial. `created_at` es metadato de sistema.

Donde no exista fecha de documento, se usa `occurred_at` del movimiento. Ambas
las declara la Spec propietaria del documento; 011 fija el contrato.

---

## 5. Redondeo (§15, §51)

| Dónde | Papel |
|---|---|
| `UnitOfMeasure.decimals` y `rounding_mode` | **Autoridad.** Definen precisión y modo |
| Producto | Puede **restringir** (menos decimales), nunca ampliar |
| Backend | **Único lugar** donde se aplica |
| Frontend | Muestra; su cálculo no vincula |
| Base de datos | `NUMERIC` conserva; no redondea por su cuenta |

No se codifica ninguna regla por nombre de unidad: que `UND` no admita fracciones
es un `decimals = 0` **declarado en el dato**, no un `if code == "UND"`.

R-D0-09-5 se traduce en que una presentación cuyo factor produzca fracciones en
la unidad base debe declararlo: el sistema no redondea en silencio.

---

## 6. Precisión de `NUMERIC`

| Uso | Tipo | Razón |
|---|---|---|
| Cantidad transaccional | `NUMERIC(18,6)` | 6 decimales cubre gramos sobre kilos y mililitros sobre litros |
| `factor_to_base` | `NUMERIC(18,6)` | Un saco de 25,5 KG y un factor de 1/3 |
| `base_quantity` | `NUMERIC(18,6)` | Debe poder representar el producto de los dos anteriores |

`Float` queda prohibido (FR-011-061). El precedente es `KQA-100`: una regresión
`Decimal + float` que rompió factura, pago, cobro, notas y CxC/CxP, que SQLite
ocultó y que apareció por casualidad en una corrida funcional.

---

## 7. Rendimiento (§85)

Resolver la conversión línea a línea produciría N+1 en cualquier documento
grande. Estrategia:

1. **Resolución masiva**: una consulta por documento que trae las versiones
   aplicables de todos sus productos y presentaciones.
2. **Índice** `(product_id, presentation_id, valid_from, valid_to)`.
3. **Caché por petición**, nunca entre peticiones: una caché persistente podría
   servir un factor obsoleto y alterar la precisión histórica (NFR-011-02).

El snapshot elimina el problema en lectura: reimprimir mil facturas no consulta
ni una vez el maestro de conversiones.

---

## 8. Solapamiento de versiones (§26, §83)

Dos versiones vigentes del mismo par producto-presentación en la misma fecha
harían la conversión no determinista. Se impide **en la base de datos**, no en el
servicio: dos transacciones simultáneas pueden pasar ambas una comprobación
previa.

La herramienta natural en PostgreSQL es una restricción de exclusión sobre un
rango de fechas (`daterange` con `EXCLUDE USING gist`), que expresa exactamente
«no se solapan» sin lógica aplicativa. Requiere `btree_gist`, hoy fuera de la
lista blanca de `ADR-D0-001`. **Alternativa sin extensión**: índice único parcial
sobre `(product_id, presentation_id) WHERE valid_to IS NULL`, que garantiza una
sola versión abierta, más validación de rango en servicio dentro de la
transacción. Se adopta la segunda para no exigir enmienda del ADR por una
comodidad.
