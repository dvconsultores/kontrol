# Tarjeta de prueba de la dueña · BUD-09 · Causado / devengado

- **Dónde:** Gobierno · Presupuesto › **Causados** y **Políticas de causado** (menú lateral).
- **Quién:**
  - **Consultar:** «Presupuesto: ver».
  - **Configurar políticas y numeración:** «Presupuesto: políticas de causado». Activar exige fundamento y MFA; el acto administrativo es opcional (OD-BUD09-02).
  - **Preparar, formalizar y anular causados:** «Presupuesto: causar». Formalizar y anular piden MFA.
  - **Autoridad:** un cargo con la competencia **Causar × Presupuesto** vigente (ORG-03). Nunca un nombre de cargo fijo.

## Preparación (datos sintéticos)

1. Un ejercicio **aprobado** con un crédito, una certificación (BUD-06) y un **compromiso vigente** (BUD-08), por ejemplo de 200,00.
2. Un cargo con la competencia Causar × Presupuesto, activo.
3. Un documento de soporte del tipo que exija la política, adjunto al ejercicio (también se puede subir desde la pantalla del causado).

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | **Políticas de causado** › **Nueva política**: tipo de gasto, nombre, disparador «Solo documentos exigidos», un documento obligatorio en la etapa Formalización, vigencia | La política queda en Borrador; el producto no trae ninguna precargada |
| 2 | Pulsa **Activar**, escribe el fundamento y confirma (MFA) | Estado **Vigente**, con historia |
| 3 | En la misma pantalla, revisa el **patrón de numeración** (por defecto `{ANIO}-{NUMERO:5}`) y cámbialo si el ente lo necesita | El patrón se valida antes de guardar |
| 4 | **Causados** › elige el ejercicio | Lista vacía: «Aún no hay causados en este ejercicio» |
| 5 | **Nuevo causado** › elige el compromiso | Tabla de líneas con comprometido, causado y pendiente |
| 6 | Escribe en «Monto a causar» más que el pendiente | Aviso «Supera el pendiente de la línea» y **Guardar borrador** deshabilitado |
| 7 | Corrige el monto (p. ej. 120,00) | «Pendiente tras este causado»: 80,00 |
| 8 | Elige la política | «Se exige» lista la evidencia y los documentos obligatorios |
| 9 | Marca el documento de soporte, escribe el concepto, elige la autoridad y pulsa **Guardar borrador** | Abre el detalle «Borrador de causado»; **Controles** muestra todo «✓ Cumplido» |
| 10 | Pulsa **Formalizar** y confirma (MFA) | El causado recibe su código según el patrón, queda **Formalizado** e inmutable; «Pendiente de orden de pago: 120,00» |
| 11 | Revisa **Imputación**, **Respaldo** e **Historia** | Líneas con el pendiente resultante; evidencia con huella; eventos de borrador y formalización |
| 12 | Intenta un segundo causado de 100,00 contra el mismo compromiso | Rechazo: supera el pendiente (80,00) |
| 13 | **Descargar CSV** en la lista | CSV con los causados del ejercicio y sus filtros |
| 14 | En el detalle, **Anular** con un motivo de al menos 10 caracteres (MFA) | Queda **Anulado**, con motivo y fecha; el saldo del compromiso se restablece |
| 15 | Opcional: en **Segregación de funciones** (CTL-01), activa una regla del proceso BUD-09 «comprometer → causar» | Quien emitió el compromiso no puede formalizar su causado (409) |

## Fuera de alcance

- Asiento contable (ACC-02; N36 pendiente): `ACCOUNTING_ENTRY=OUT_OF_SCOPE`.
- Orden de pago y pago (TRE-03, TRE-04). El causado ya expone `monto_ordenado` y `pendiente_de_ordenar` para TRE-03.
- Retenciones (TRE-05) y el modo de aviso (WARN) de CTL-01 (deuda SOD-WARN-MODE-01).
