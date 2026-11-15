# Tarjeta de prueba de la dueña · CNT-02 · Adendas, prórrogas, modificaciones y variaciones

- **Dónde:** Gobierno · Contratos › **Contratos y órdenes** › un contrato **formalizado** › enlace **Modificaciones (n)**.
- **Quién:**
  - **Preparar el borrador:** «Contratos: gestionar».
  - **Formalizar:** «Contratos: formalizar» (pide MFA) y un cargo con la competencia **Firmar · Contrataciones**.
- **Qué demuestra:**
  - El contrato original nunca se sobrescribe y cada cambio es un instrumento nuevo, versionado y sellado.
  - Las condiciones vigentes se derivan de la historia.
  - Una ampliación exige cobertura de CDP real.
  - El firmante se controla contra el **monto efectivo nuevo**.
  - Una reducción no puede dejar los compromisos BUD-08 por encima del contrato.

## Preparación (datos sintéticos, una vez)

1. Un contrato **formalizado** de CNT-01 en USD: 50000.00 USD, con plazo de 180 días y cobertura de una CDP de 50000.00 del expediente.
2. Crédito presupuestario libre de al menos 10000.00 USD para emitir otra CDP del mismo expediente.
3. Tres cargos con **Firmar · Contrataciones**:
   - **A**, sin límite;
   - **B**, con límite de 55000.00 USD;
   - **C**, con límite en **EUR**, para ver la conversión TRE-09. Si no hay tasa BCV aprobada, el sistema la pide.
4. Un documento firmado nuevo, vinculado al expediente, para cada instrumento.

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | Abre el contrato formalizado y pulsa **Modificaciones (0)** | Se ven «Condiciones originales» (50000.00 USD y el plazo original) y «Condiciones vigentes al …», iguales a las originales |
| 2 | Elige **Prórroga** y pulsa **Nueva modificación** | Se abre «Borrador · CT-…» con «Falta para formalizar» |
| 3 | Completa la fecha del instrumento (hoy), Vigente desde (hoy), el motivo, la nueva fecha de fin (+30 días), la referencia y el documento, y pulsa **Guardar datos** | «Cambios guardados.»; el cambio propuesto muestra el fin anterior y el nuevo |
| 4 | Elige el firmante A y pulsa **Formalizar**; confirma con MFA | «Formalizada: CT-…/PR-001»; el documento queda sellado y se muestra la huella |
| 5 | Vuelve a **Modificaciones** | El original sigue con el plazo inicial. Las vigentes muestran el plazo nuevo. El historial dice «Contrato original → Prórroga …/PR-001» |
| 6 | Crea una **Adenda** con el cambio de monto **10000.00** e intenta formalizarla | Alerta: «Falta cubrir 10000.00 USD con certificaciones de disponibilidad» |
| 7 | Emite una CDP de 10000.00 del expediente (Presupuesto › Certificaciones), recarga, asigna 10000.00 en «Cobertura adicional» y pulsa **Guardar cobertura** | «Cobertura completa» |
| 8 | Elige el firmante **B** (55000.00 USD) | El control dice «Excede el límite»: el monto efectivo nuevo es 60000.00, aunque el aumento sea solo de 10000.00 |
| 9 | Formaliza con B | Alerta: «… excede el límite de firma …» |
| 10 | Formaliza con A | «Formalizada: …/AD-002». Vigentes: 60000.00 USD. El monto del contrato original sigue en 50000.00 |
| 11 | Opcional: elige el firmante C (límite en EUR) | Sin tasa BCV aprobada, «Sin tasa oficial aprobada». Tras aprobar las tasas USD y EUR en Tesorería › Tasas oficiales, el control compara en VES y la ficha formalizada muestra la conversión |
| 12 | Registra en Presupuesto › Compromisos (con otro usuario) un compromiso del expediente de 56000.00. Después crea una **Modificación** con el cambio de monto **-5000.00** e intenta formalizarla | Alerta: «Los compromisos presupuestarios vigentes del expediente (56000.00 USD) superan el monto del contrato (55000.00 USD) …» |
| 13 | **Descartar borrador** | El borrador desaparece y el historial no cambia |
| 14 | Abre la ficha de AD-002 | Instrumento formalizado, de solo lectura: motivo, monto anterior, cambio y nuevo, documento con versión y huella, firmante y huella del instrumento |

## Fuera de alcance

Ejecución (CNT-03), supervisor (CNT-04, de P1), penalidades (CNT-06), terminación (CNT-07), anulación de una modificación formalizada (OQ-CNT02-02) y acortar el plazo.
