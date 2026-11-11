# Conteo independiente en la recepción: análisis de autoridad

Encargo `SPEC018_CONTEO_INDEPENDIENTE`, del 2026-11-11. Spec dueña del conteo y de la confirmación: 021, cuyo ciclo está en `spec021-implementation-cycle.md` de esta carpeta. Fila de la matriz: «Conteo independiente» (`specs/018-importaciones/IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.md`), hoy PARTIAL.

## 1. Requisito literal y fuente

`requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, leído entero. Párrafos relevantes:
- §3, etapa 1: «Realizar conteo detallado por SKU o código.»
- «Controles críticos del proceso»: «Conteo independiente.»

La fuente no dice nada más:
- **no** dice independiente de quién (de quien recibe, de quien confirma o de los documentos);
- **no** dice si es obligatorio en toda circunstancia o si la empresa puede prescindir de él;
- **no** dice si el conteo debe hacerse «a ciegas», sin ver la cantidad esperada.

## 2. Actores que el producto registra hoy

Todos se guardan como el id del usuario.

| Momento | Campo |
|---|---|
| Alta de la recepción | `goods_receipts.created_by` |
| Arribo | `goods_receipts.arrival_confirmed_by` |
| Inspección y calidad | `goods_receipts.inspected_by` |
| Acta (aceptación) | `goods_receipts.record_issued_by` |
| Conteo por línea (Spec 021) | `goods_receipt_lines.counted_by` |
| Confirmación del inventario (Spec 021) | `goods_receipts.confirmed_by` y `receipt_confirmations.created_by` |

La cantidad recibida (`quantity_received`) se captura al crear la línea, que no guarda quién la creó. El «receptor» es, por tanto, `created_by` o `record_issued_by` de la recepción. Es otra ambigüedad.

Medido el 2026-11-11 en Chrome sobre PostgreSQL: el mismo usuario hace todo y el sistema lo acepta.

## 3. Precedentes encontrados

- **R-D0-12-5 (ADR-D0-012, Spec 033).** «Segregación configurable. La política `same_user_allowed` es un dato **por empresa y por proceso**. KONTROL fija el valor por defecto en `false` **para la confirmación respecto del picking** […] Una empresa pequeña puede habilitarlo conscientemente; la decisión queda auditada.» Es una decisión **de Ventas, para el par preparar/confirmar**, y declara que la política es por proceso. **No** autoriza por sí misma una regla en la recepción.
- **R-D0-12-6 (mismo ADR).** «No se codifica la política de ningún cliente concreto. Las reglas del proceso documentado son configuración de ese cliente, no reglas del producto.» El DOCX es el proceso documentado de un cliente, así que, según esta decisión vigente, el «conteo independiente» del DOCX **no** puede ser una regla fija del producto sin una decisión que lo justifique.
- **Spec 033** (`spec033-implementation-cycle.md`): «No se implementa conteo ciego. Ni el proceso ni el ADR lo piden, y `R-D0-12-6` prohíbe […]». Es un precedente de no inventar variantes del control.
- **Spec 021** (ciclo de implementación): trata la etapa «Realizar conteo detallado por SKU» (`counted_base_quantity`, `counted_by`). **No** aborda la independencia.
- **`docs/roadmap/false-completion-findings.md` (FC-05):** «No hay conteo independiente». Registra la brecha, pero no la define.

## 4. Diferencias entre Ventas e Importaciones

| | Ventas (Spec 033) | Recepción (Spec 021) |
|---|---|---|
| Qué se separa | preparar (picking) frente a confirmar | sin definir: recibir, contar o confirmar |
| Autoridad | ADR-D0-012, R-D0-12-5 | ninguna específica |
| Configuración | `companies.confirmation_same_user_allowed` (por empresa, para ese proceso) | no existe |

## 5. Conclusión

- **Independent count meaning:** NO DETERMINADO por las fuentes. Pueden ser A (receptor ≠ contador), B (contador ≠ confirmador), C (receptor ≠ confirmador) o D (las tres personas distintas).
- **Configurabilidad:** R-D0-12-6 apunta a que sea configuración por empresa, porque es la regla de un cliente. Pero ni el valor por defecto ni el par que se separa están decididos para este proceso. R-D0-12-5 solo fija el defecto `false` para el par de Ventas.
- **`MATERIAL_DECISION_REQUIRED = 1`.** No se escribe código semántico hasta que decida la dueña. Si el control se puede desactivar, hay que decidir además quién lo desactiva: con permiso administrativo, auditado y sin efecto retroactivo.

## 6. Decisión de la dueña (2026-11-11)

Consultada con AskUserQuestion, porque `MATERIAL_DECISION_REQUIRED = 1`:
- **Separación: receptor ≠ contador.** Quien registra la recepción (`created_by`) o la acepta (`record_issued_by`) no puede contar sus líneas.
- **Configurabilidad: sí, activa por defecto.** Cada empresa lo tiene activo. Solo se desactiva con permiso, la acción queda auditada (actor, fecha, valor anterior y nuevo) y no tiene efecto retroactivo: las recepciones ya confirmadas no se tocan. Es coherente con R-D0-12-5 y R-D0-12-6.

Resultado: `INDEPENDENT_COUNT_ACTORS = RECEIVER_NOT_COUNTER`, `INDEPENDENT_COUNT_DISABLE_ALLOWED = 1` (activo por defecto). El contrato está en `spec021-independent-count-delta.md`.
