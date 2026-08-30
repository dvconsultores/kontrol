# CLARIFICACIONES — SPEC 011

Regla de trabajo (§97): **primero se resuelve con la autoridad existente.** Solo
se escala lo que ninguna decisión previa cubre. Ocho de las nueve preguntas
clave del encargo ya tenían respuesta en `ADR-D0-009`, la Constitución o el
código real; una es decisión de producto y se escala **sin bloquear**.

---

## 1. Preguntas clave del §97 — resueltas por autoridad

| # | Pregunta | Respuesta | Autoridad |
|---|---|---|---|
| CL-011-01 | ¿UOM global o por empresa? | **Ambas.** Catálogo global de plataforma más unidades propias de cada empresa. La empresa no edita las globales. El catálogo global nace **vacío**: KONTROL no impone `UND`, `KG` ni ninguna otra | P8 (nada de negocio en código) + `company_id` nullable ya existente en `units_of_measure` |
| CL-011-02 | ¿Cuándo se fija el snapshot? | **Al emitir o aprobar.** Mientras el documento es editable, cambiar la presentación recalcula; una vez emitido, nada lo altera | R-D0-09-2 y R-D0-09-4 |
| CL-011-03 | ¿Puede cambiar la unidad base? | **Sin movimientos, sí. Con movimientos, no** por edición simple | P5 + la analogía directa con `structure_regime` de la Spec 008 |
| CL-011-04 | ¿Versionado o inmutable? | **Versionado por vigencia.** Cambiar un factor crea versión nueva; la anterior queda | R-D0-09-4 |
| CL-011-05 | ¿Solapamiento de versiones? | **Prohibido** por restricción de base de datos para el mismo par producto-presentación | P13 (integridad transaccional) |
| CL-011-06 | ¿Presentación es SKU? | **No.** Si una diferencia de presentación implica otro artículo, son variantes de la Spec 010 | `ADR-D0-009` §Principio + alcance de 010 |
| CL-011-07 | ¿Dónde se redondea? | **En el backend, una sola vez**, con `decimals` y `rounding_mode` de la unidad base. Ni frontend ni base de datos aplican regla propia | P6 (backend es la autoridad) |
| CL-011-08 | ¿Migración legada? | Clasificación en cuatro clases; `factor = 1` solo demostrado; lo fiscal irreconstruible no se toca | `ADR-D0-009` §Migración, **refinado** con la disciplina de las Specs 045 y 008 |
| CL-011-09 | ¿Cómo aplica a servicios? | Un servicio **no** requiere unidad base de inventario. Puede tener unidad de facturación (`HORA`, `DIA`, `SERVICIO`) | R-D0-09-3 (el inventario es de lo inventariable) + `billing_unit_id` ya existente |

## 2. Decisiones tomadas

| ID | Decisión | Razón |
|---|---|---|
| CL-011-10 | El factor vive en `ProductPresentation`, no en `Presentation` | Una «caja» no tiene contenido universal: la caja de un producto son 100 unidades y la de otro 24. El factor pertenece a la relación (§12) |
| CL-011-11 | `Presentation` actual se **conserva y se extiende**, no se sustituye | Ya tiene `product_id`, `unit_id`, `buyable`, `sellable`, `storable`. Le faltan factor explícito, versión y estado. Reemplazarla destruiría los pocos datos que pudiera haber |
| CL-011-12 | La conversión física y la comercial se modelan **separadas** | Son cosas distintas: `KG → G` es física e inmutable; `CAJA → 100 UND` es comercial y cambia (§33) |
| CL-011-13 | El motor de conversión acepta ambas y las resuelve en cadena | Una presentación puede declararse en una unidad distinta de la base (saco de 25,5 KG con base en G): primero la conversión comercial, después la física |
| CL-011-14 | La unidad y la presentación se declaran **por línea**, no por cantidad | `goods_receipt_lines` tiene tres cantidades; permitir una unidad por cantidad dejaría aceptar en cajas lo recibido en unidades |
| CL-011-15 | `uom_source` es columna de la línea, no metadato del reporte | Debe poder distinguirse una línea capturada de una supuesta **para siempre**, no solo el día de la migración |
| CL-011-16 | La conversión de `Float` a `NUMERIC` va en migración **separada** del backfill | Riesgos independientes: un fallo de tipo no debe arrastrar al backfill semántico ni al revés |
| CL-011-17 | El símbolo de unidad y la etiqueta de presentación se congelan **solo** en documentos emitidos | Guardar el texto en toda línea sería duplicación; en un documento fiscal es requisito de reimpresión fiel (§24) |
| CL-011-18 | `inventory_balances` **no** recibe presentación | Es proyección del ledger en unidad base. Añadirle presentación crearía la unidad de existencia paralela que R-D0-09-3 prohíbe |
| CL-011-19 | Alias de unidad y peso variable: `FUTURE_CAPABILITY` | No son necesarios para el MVP y añadirlos ahora es sobreingeniería (§31, §34). El modelo no los bloquea |
| CL-011-20 | El vocabulario de dimensiones es **cerrado**, el de unidades **abierto** | Las dimensiones físicas no las inventa un cliente; las unidades sí (`BULTO`, `SACO`, `TAMBOR`) |

## 3. Escalado — no bloqueante

| ID | Cuestión | Por qué se escala | Efecto si no se responde |
|---|---|---|---|
| **ESC-011-01** | **Umbral de bloqueo del backfill fiscal.** ¿A partir de cuántas líneas de factura irreconstruibles debe abortar la migración: una sola, un porcentaje, o cualquier número con revisión previa obligatoria? | Es una decisión de **producto y de riesgo fiscal**, no técnica. La arquitectura soporta las tres | Se implementa configurable con valor por defecto **1** —la opción más conservadora, coherente con la Spec 008— y se ajusta sin cambio de esquema |

Las otras dos cuestiones que parecían escalables se resolvieron con autoridad
existente y **no** se elevan:

- *¿Debe KONTROL entregar un catálogo estándar de unidades?* — No. P8 lo
  resuelve: sería un valor de negocio en el código. El catálogo nace vacío y cada
  empresa carga el suyo.
- *¿El precio se expresa por unidad o por presentación?* — La línea conserva
  **qué unidad o presentación sustentó el precio**; decidir la política de precios
  es de la Spec 012 (§52). 011 solo fija el contrato.

## 4. Tensión detectada con `ADR-D0-009`, y su resolución

El ADR autoriza rellenar el histórico con «unidad base del producto y
`conversion_factor_snapshot = 1`, marcadas `LEGACY_ASSUMED_BASE`». El encargo
(§42, §43, §107) prohíbe suponer factor 1 indiscriminadamente.

**No hay contradicción, sino una precisión que el ADR ya anticipaba** al escribir
«es una suposición, y queda registrada como tal». Esta Spec la hace verificable:

| El ADR dice | 011 lo refina en |
|---|---|
| Rellenar con la unidad base del producto | Solo cuando el producto **tiene** unidad base declarada → clase A |
| Marcar `LEGACY_ASSUMED_BASE` | Se conserva, y se añaden `LEGACY_RECONSTRUCTED`, `LEGACY_UNRESOLVED` y `LEGACY_UNVERSIONED` |
| «Si alguna línea se registró en otra presentación, ese dato es irrecuperable» | **Se demuestra que no pudo ocurrir**: no existe endpoint ni seed que cree presentaciones (§1 de la matriz de migración) |

El refinamiento **no** requiere enmienda del ADR: no cambia ninguna de sus cinco
reglas, las hace comprobables.

## 5. Confirmación de que no se escala lo ya resuelto

No se pregunta al usuario por: motor de persistencia (`ADR-D0-001`), aprobaciones
(Spec 045), auditoría (`ADR-012`), permisos (Spec 003), concurrencia
(`ADR-013`), ni por el principio de captura temprana (P23). Todo ello está
cerrado y se **consume**, no se redecide.
