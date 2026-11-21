# Tarjeta de prueba de la dueña · TRE-05 · Retenciones y comprobantes

- **Dónde:**
  - Gobierno · Tesorería › **Políticas de retención** y **Retenciones**, en el menú lateral (perfil KONTROL Gobierno o mixto).
  - Además, la sección **«Retenciones»** en el detalle de cada pago (TRE-04).
- **Quién:**
  - **Consultar:** permiso de retenciones «ver».
  - **Catálogo y numeración:** permiso «gestionar».
  - **Políticas:** permiso «políticas». Activar y cerrar piden fundamento o motivo y MFA.
  - **Calcular y ajustar (maker):** permiso «calcular».
  - **Aprobar (checker):** permiso «aprobar», con MFA. Lo hace **otra persona**: quien calculó o ajustó nunca aprueba.
  - **Anular una liquidación o un comprobante:** permiso «anular», con MFA.
- **Autoridad del checker:** un cargo con la competencia que fija la política, por ejemplo **Pagar × Tesorería**. Debe estar vigente hoy (ORG-03), con su ocupación, encargaduría o suplencia. Nunca un nombre de cargo fijo.
- **Qué NO hace KONTROL:**
  - No trae alícuotas, umbrales ni conceptos precargados, y no afirma cumplimiento fiscal.
  - Toda regla es del ente, con su fuente. Se muestra como «adoptada por el ente; verificación normativa pendiente».
  - No declara ante el SENIAT ni genera archivos de declaración.

## Preparación (datos sintéticos)

1. Un **pago en borrador** (TRE-04) de 100.00 sobre una orden emitida (TRE-03). Para el recorrido F, otro de 200.00.
2. Dos usuarios:
   - el maker, con «calcular» y «políticas»;
   - el checker, con «aprobar» y «anular».
   - Los dos con permiso de pagos «ver».
3. Un cargo con **Pagar × Tesorería** vigente para el checker.

## A · Catálogo y numeración

| N.º | Acción | Resultado esperado |
|---|---|---|
| A1 | Abre **Políticas de retención** | Tres secciones: tabla de políticas, «Catálogo del ente» y «Numeración de comprobantes». Vacías: nada viene precargado |
| A2 | Rellena el concepto: código, nombre y clase «Tributaria». Pulsa **Añadir concepto** | Aparece en «Conceptos de retención» como Activo |
| A3 | Rellena una condición (p. ej. «Exento por acto») y pulsa **Añadir condición** | Aparece en «Condiciones del beneficiario» |
| A4 | Escribe un **Patrón** con `{ANIO}` y `{NUMERO:n}`. Pulsa **Guardar patrón** | Muestra el ejemplo del próximo número |

## B · Política versionada

| N.º | Acción | Resultado esperado |
|---|---|---|
| B1 | **Nueva política**, con estos datos:<br>• código, nombre y moneda;<br>• clasificación «Política institucional»;<br>• fuente (descripción y artículo);<br>• competencia del aprobador Pagar × Tesorería;<br>• vigente desde | Guardada en **Borrador** |
| B2 | **Añadir regla**:<br>• concepto del A2;<br>• base «Monto bruto del pago»;<br>• alícuota 5;<br>• umbral «Sin umbral»;<br>• marca «exige comprobante» | Campos condicionales:<br>• «Porcentaje de la base» solo con «Porcentaje del bruto»;<br>• «Monto del umbral» solo con «Monto fijo»;<br>• «Múltiplo de una tasa oficial» deshabilitado si la moneda no es VES |
| B3 | Pulsa **Activar**, con un fundamento de al menos 20 caracteres (MFA) | Estado **Vigente**. Los campos quedan de solo lectura; aparecen **Cerrar** y **Nueva versión** |
| B4 | Abre el desplegable «Clasificación» | Solo ofrece «Política institucional» y «Configuración operativa». La obligación legal no se puede elegir: exige una fuente verificada y no hay ninguna custodiada (N38) |

## C · Cálculo en el pago

| N.º | Acción | Resultado esperado |
|---|---|---|
| C1 | Abre el pago de 100.00 y ve a la sección **Retenciones** | Bruto 100.00, Retenciones 0.00, Neto 100.00, «Preliminar» y botón **Calcular retenciones** |
| C2 | Pulsa **Calcular retenciones** y completa:<br>• la política;<br>• el concepto (casilla «código · nombre»);<br>• el beneficiario: nombre, identificación fiscal y tipo de persona.<br>Luego pulsa **Calcular** | Tabla «Retenciones calculadas» con base 100.00, alícuota 5 y monto 5.00. Resumen: Neto **95.00**, estado **Calculada**, política y versión, fuente con su rótulo |
| C3 | Con el maker, intenta **Aprobar retenciones** | No le aparece el botón si no tiene «aprobar». Si lo tiene, recibe un rechazo: quien calculó no aprueba |

## D · Aprobación (checker)

| N.º | Acción | Resultado esperado |
|---|---|---|
| D1 | Entra con el checker al mismo pago y pulsa **Aprobar retenciones** | Diálogo «Aprobar retenciones» con «Cargo que aprueba». El cargo competente se marca «(competente)» |
| D2 | Elige el cargo y pulsa **Aprobar** (MFA) | Estado **Aprobada** |

## E · Aplicación y comprobante

| N.º | Acción | Resultado esperado |
|---|---|---|
| E1 | Antes de aprobar (estado Calculada), intenta registrar el pago ejecutado | Rechazo: «La liquidación de retenciones del pago está pendiente de aprobación» |
| E2 | Ya aprobada, envía, autoriza y **registra** el pago (TRE-04) | Retenciones queda **Aplicada**, «Definitivo». Aparece «Comprobantes» con su código y **Descargar PDF** |
| E3 | Descarga el PDF | Comprobante con concepto, base, alícuota, monto, beneficiario declarado, pago y huella |

## F · Varias reglas, umbral y exclusión

| N.º | Acción | Resultado esperado |
|---|---|---|
| F1 | Política con tres reglas al 5, 2 y 1 % sobre 100.00 | Total retenido **8.00** y neto **92.00**; aplican las tres líneas |
| F2 | Regla al 5 % con umbral «Monto fijo» 150. Pago de 100.00 | La línea no aplica: «Por debajo del umbral». Total 0.00. Con un pago de 200.00, total 10.00 |
| F3 | Regla excluida por la condición del A3, con un beneficiario que la tiene | «Excluido por condición»; las demás reglas sí aplican |

## G · Versión congelada

| N.º | Acción | Resultado esperado |
|---|---|---|
| G1 | Con una liquidación ya calculada con la v1 (5 %), pulsa **Nueva versión**. Cambia la alícuota a 10 con vigencia hoy y actívala | La v1 queda **Cerrada**. La liquidación ya calculada sigue en 5.00 y versión 1 |
| G2 | Calcula otro pago con la v2 | 10.00 y versión 2 |

## H · Anulación, sustitución y consulta

| N.º | Acción | Resultado esperado |
|---|---|---|
| H1 | **Retenciones › Comprobantes**, sobre un comprobante emitido: **Anular** con motivo, «Emitir un comprobante sustituto» y nombre corregido (MFA) | El original queda **Anulado** y aparece un sustituto **Emitido** con el nombre corregido |
| H2 | Pestaña **Liquidaciones**: filtra por estado y fechas y pulsa **Descargar CSV** | Filas con pago, beneficiario, política, bruto, retenido, neto y comprobantes |
| H3 | Bitácora institucional (CTL-02), filtrada por el proceso **TRE-05 · Retenciones** | Eventos de política, cálculo, aprobación, aplicación y comprobante |

## Lo que queda fuera (decidido)

- **Declaración ante el SENIAT y archivos de declaración:** fuera del alcance.
- **Alícuotas legales precargadas:** ninguna. Exigen custodiar N38 con hash antes del freeze.
- **Datos fiscales del beneficiario:** se declaran en cada liquidación (OD-TRE05-01). Un maestro de terceros llegará con ACC-06/PROC-05.
