# Tarjeta de prueba de la dueña · CNT-01 · Contrato u orden desde la adjudicación

- **Dónde:** Gobierno › Contrataciones › Expedientes › un expediente adjudicado › sección **Recomendación y decisión** › **Crear contrato u orden**. La consulta general está en Gobierno · Contratos › **Contratos y órdenes**.
- **Quién:**
  - **Preparar:** «Contratos: gestionar».
  - **Formalizar:** «Contratos: formalizar», que pide MFA, y ejercer un cargo con la competencia **Firmar · Contrataciones**.
- **Qué demuestra:**
  - El contrato nace de una adjudicación real.
  - Contratista, objeto, monto y moneda salen de la oferta y no se editan.
  - La cobertura presupuestaria se demuestra con CDP de BUD-06 sin consumirlas.
  - Se formaliza con autoridad y límite.
  - Después queda congelado.

## Preparación (datos sintéticos, una vez)

1. Un ente cuya moneda funcional sea la de la oferta. En la UAT de P2 se usa **USD** (ver «Límites declarados»).
2. Un expediente con decisión **ADJUDICADA** vigente (PROC-08). La oferta tiene monto declarado: 43103.45 + 6896.55 = **50000.00 USD**.
3. Un ejercicio presupuestario aprobado con crédito suficiente, y una **CDP de 50000.00 USD** (BUD-06), si es posible asociada al expediente.
4. Dos cargos con **Firmar · Contrataciones**:
   - **Firmante A**, sin límite;
   - **Firmante B**, con límite de 40000.00 USD.
5. Opcional: una garantía de fiel cumplimiento registrada para la oferta adjudicada (PROC-10).
6. El documento firmado del contrato, vinculado al expediente (sección de documentos).

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | En la decisión del expediente, pulsa **Crear contrato u orden** | Se abre «Borrador · EXP-… · DEC-01», con el origen en solo lectura: contratista, objeto y **50000.00 USD** |
| 2 | Elige el tipo **Contrato**, el plazo, la referencia y el instrumento firmado, y pulsa **Guardar datos** | «Cambios guardados.»; los pendientes se reducen |
| 3 | En Cobertura, asigna **40000.00** a la CDP y pulsa **Guardar cobertura** | «Asignado: 40000.00 USD · Falta: 10000.00 USD» |
| 4 | Elige el Firmante A y pulsa **Formalizar** → **Formalizar** | Aviso: «La cobertura presupuestaria (40000.00 USD) no es igual al monto del contrato…». No se formaliza |
| 5 | Asigna **50000.00** y guarda | «Cobertura completa» |
| 6 | Marca la garantía (si existe) y pulsa **Guardar garantías** | Queda vinculada |
| 7 | Elige el Firmante B | Panel: «Excede el límite» |
| 8 | Pulsa **Formalizar** → **Formalizar** | Aviso: «El monto del contrato (50000.00 USD) excede el límite de firma de …». Sigue en borrador; no hay forma de saltarse el bloqueo |
| 9 | Elige el Firmante A y formaliza | «Formalizado: CT-AAAA-0001». La ficha queda congelada: código, plazo, documento con huella, firmante, cobertura y garantías |
| 10 | Vuelve al expediente | El panel de la decisión muestra el código y el enlace «Ver contrato u orden». La cronología registra «Contrato CT-… formalizado» |
| 11 | Abre Gobierno · Contratos › Contratos y órdenes | Aparece la fila con el código; el filtro «Formalizado» la encuentra |
| 12 | Revisa la auditoría o la bitácora | «Borrador de contrato u orden creado», «…modificado», «Formalización bloqueada por la autoridad del firmante» y «Contrato u orden formalizado», sin importes |
| 13 | En BUD-06, revisa la CDP | Sigue VIGENTE y con el mismo monto: CNT-01 no la consume |
| 14 | Prueba en el móvil (390 o 320 px) | Una columna, sin desplazamiento horizontal de página |

## Límites declarados (no son fallos)

- **Moneda (OQ-CNT01-02).** Gobierno usa VES, USD o EUR, y la moneda funcional del presupuesto es VED. No se equiparan, porque sería una conversión. Una oferta en VES no puede cubrirse con una CDP en VED hasta que la dueña decida o exista TRE-09.
- **Disponibilidad parcial y contratos plurianuales (LCP arts. 74 y 75, OQ-CNT01-01).** No se construyen: CNT-01 exige cobertura completa y un solo ejercicio.
- **Adendas, ejecución, supervisor y compromiso presupuestario.** Pertenecen a CNT-02, CNT-03, CNT-04 y BUD-08.
- **Plazo de firma de 8 días hábiles (LCP art. 117).** No se bloquea; la alerta es de CNT-09.

`OWNER_ACCEPTED`: NO. Solo la dueña lo concede.
