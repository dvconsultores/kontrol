# Tarjeta de prueba de la dueña · CNT-08 · Expediente contractual completo

- **Dónde:** Gobierno · Contratos › **Expedientes contractuales**, o bien un contrato formalizado › **Expediente contractual**.
- **Quién:**
  - **Consultar:** «Contratos: ver».
  - **Ver la auditoría:** además, «Auditoría institucional: ver».
  - **Ver, descargar y verificar paquetes:** «Paquetes: ver».
  - **Generarlos:** «Paquetes: generar», que pide MFA.
  - **Incluir y descargar documentos:** el permiso documental de descarga. Los comprobantes de CDP y compromiso requieren además «Presupuesto: ver».
- **Qué demuestra:**
  - un expediente único y de solo lectura, en orden cronológico;
  - de dónde nació el contrato, quién lo adjudicó y con qué presupuesto y garantías;
  - qué modificaciones tuvo y quién lo supervisa;
  - qué documentos y actos existen, con sus huellas;
  - que se puede exportar un paquete y verificarlo.

## Preparación (datos sintéticos)

Un contrato **formalizado** de CNT-01 con CDP, al menos una modificación formalizada de CNT-02 y, si se quiere, un supervisor designado de CNT-04.

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | Menú › Gobierno · Contratos › **Expedientes contractuales** | Lista con el contrato, su monto vigente, la vigencia y el supervisor |
| 2 | Filtra por contratista y pulsa **Buscar** | Solo aparecen los contratos de ese contratista |
| 3 | Abre el contrato | «Expediente contractual · CT-…», con la navegación de 14 secciones y el aviso de solo lectura |
| 4 | **Origen de contratación** y **Adjudicación** | Expediente PROC-03, oferta adjudicada, decisión y acto, con enlaces a su pantalla |
| 5 | **Presupuesto** | CDP con lo asignado al contrato y por modificaciones, y compromisos del expediente. Nota: «no crea certificaciones ni compromisos…» |
| 6 | **Instrumento contractual** | «Condiciones originales» (sin cambios) junto a «Condiciones vigentes» (según la modificación) |
| 7 | **Modificaciones** y **Supervisión** | Historial de CNT-02 e historia del supervisor; consulta del supervisor en una fecha |
| 8 | **Ejecución** | La ejecución registrada en CNT-03 (o su estado vacío); CNT-05, CNT-06, CNT-07 y TRE-04 dicen «El módulo aún no está disponible…», nunca «no hubo» |
| 9 | **Actos y documentos** › **Descargar** de un comprobante de CDP | Se descarga por su autoridad. El instrumento sellado muestra «Sellado · la autoridad documental no lo entrega (huella registrada)» |
| 10 | **Integridad** › **Comprobar huellas** | Cada documento aparece como Verificada, Ausente, No coincide o No aplica |
| 11 | **Cronología**: filtra por CNT-02 | Solo aparecen las modificaciones, en orden de fecha jurídica |
| 12 | **Auditoría** | Eventos institucionales del expediente, con «Ver evento» |
| 13 | **Exportaciones**: escribe el propósito y pulsa **Generar paquete** (MFA) | «Paquete generado: EC-…» |
| 14 | **Descargar** el paquete | ZIP con manifest.json, expediente.json, cronologia.csv, indice.csv, referencias.json, LEEME.txt, SHA256SUMS y los documentos |
| 15 | **Verificar un paquete**: sube el ZIP descargado | «Válido», idéntico al registrado |
| 16 | Opcional: modifica cualquier fichero del ZIP y verifícalo otra vez | «Inválido», con el fichero alterado señalado |

## Fuera de alcance

Registrar ejecución (se hace en CNT-03, de P1), pagos, penalidades, terminación y el buscador global DOC-07.
