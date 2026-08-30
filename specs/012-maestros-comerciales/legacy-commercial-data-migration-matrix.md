# MATRIZ DE MIGRACIÓN DEL LEGADO COMERCIAL — SPEC 012

**Normativa.** Gobierna la migración de anotación, igual que
`legacy-document-migration-matrix.md` gobernó la `0024` de la Spec 046.

## 1. Principio

> **Anotar no es convertir.**

Una cadena como `"30 días"` no basta para afirmar que existe una condición de
pago de 30 días contados desde la emisión. Puede significar 30 días desde la
entrega, 30 días de la fecha de factura, o 30 días hábiles. Convertirla
automáticamente crearía un maestro que **parece** correcto y produce vencimientos
equivocados.

Es la lección de `R-046-5` aplicada al dominio comercial.

## 2. Columnas gobernadas

| Tabla | Columna | Clasificación base |
|---|---|---|
| `customers` | `price_list` | `AMBIGUOUS` |
| `customers` | `payment_term` | `AMBIGUOUS` |
| `customers` | `zone` | `DETERMINISTIC_CANDIDATE` |
| `customers` | `salesperson` | `MANUAL_REVIEW_REQUIRED` |
| `suppliers` | `payment_term` | `AMBIGUOUS` |
| `suppliers` | `category` | `DETERMINISTIC_CANDIDATE` |
| `sales_quotes` | `price_list` | `AMBIGUOUS` |

## 3. Vocabulario de clasificación

| Clase | Significado | Qué hace la migración |
|---|---|---|
| `EMPTY` | Nulo o cadena vacía | **Nada.** No es una referencia |
| `DETERMINISTIC_CANDIDATE` | Un valor distinto, repetido, sin ambigüedad de significado (una zona llamada «Centro») | **Anota** y propone; **no crea** el maestro |
| `AMBIGUOUS` | El texto admite más de una lectura («30 días», «Lista A») | **Anota** y marca `MANUAL_REVIEW_REQUIRED` |
| `MANUAL_REVIEW_REQUIRED` | Requiere que una persona decida | **Anota** y espera |
| `RECONSTRUCTIBLE` | Se puede derivar con certeza de otra columna | **Anota** el origen |
| `MIGRATION_BLOCKER` | Contradice un dato ya congelado | **Anota** y **detiene** |

## 4. Lo que la migración NO hace

| Prohibido | Por qué |
|---|---|
| Crear una `PaymentTerm` a partir de una cadena | Su semántica no está en el texto |
| Crear una `PriceList` a partir de un nombre | Un nombre no tiene precios |
| Asignar precios a documentos históricos | No se puede reconstruir lo que nunca se registró |
| Borrar o modificar la columna original | `P5` |
| Inventar `pricing_source = RESOLVED` en documentos viejos | Sería una mentira verificable |

## 5. Invariantes que la migración comprueba sobre sí misma

| Invariante | Valor exigido |
|---|---|
| `masters_created` | **0** |
| `columns_modified` | **0** |
| `documents_repriced` | **0** |
| Anotaciones duplicadas por `(tabla, columna, fila)` | **0** |

Si alguna se incumple, la migración **aborta**. Es el mismo mecanismo que
`0024` ejecuta al final de su `upgrade()`.

## 6. Documentos históricos

Toda línea transaccional existente recibe:

```
pricing_source = 'LEGACY_FREETEXT'
price_source_version_id = NULL
```

No se inventa un origen. Un documento emitido antes de 012 **no tenía** origen de
precio, y decir lo contrario sería peor que admitirlo.

## 7. Reporte obligatorio

La migración imprime, como hizo `0024`:

```
===== REPORTE DE ANOTACIÓN COMERCIAL LEGADA =====
{ "references_scanned": N, "empty": N, "deterministic_candidate": N,
  "ambiguous": N, "manual_review_required": N,
  "masters_created": 0, "columns_modified": 0, "documents_repriced": 0 }
```

Con `masters_created`, `columns_modified` y `documents_repriced` en **0**, o no
pasa.

## 8. Medición previa

Sobre una instalación recién creada: **0 filas** en las siete columnas. Eso no
autoriza a asumir que en producción también: la migración **mide y reporta**
sobre la instalación real. Asumir el cero sería exactamente el error que esta
matriz existe para evitar.
