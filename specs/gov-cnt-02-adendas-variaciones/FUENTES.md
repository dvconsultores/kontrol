# CNT-02 · Fuentes leídas (2026-11-15)

## Normativa

Se usó la copia verificada de `lcp.pdf` (N11, Decreto-Ley de Contrataciones Públicas, G.O. 6.154 Ext., 19-11-2014). Es la misma de CNT-01, con SHA-256 `a87a12d3b578d97f94bb639b852aad18e60bf238ef14a00f7554189fc32cb5d8`. El texto se extrajo fuera del repositorio.

| Regla | Fuente | Texto (literal, abreviado) | Consecuencia en CNT-02 |
|---|---|---|---|
| Facultad de modificar | LCP art. 130, párr. 1 | «El contratante podrá, antes o después de iniciado el suministro…, introducir las modificaciones que estime necesarias, las cuales serán notificadas por escrito al contratista» | La modificación es un instrumento nuevo, por escrito (DOC-08); no se reescribe el contrato |
| Autorización escrita | LCP art. 130, párr. 1 | «El contratista sólo podrá realizar las modificaciones propuestas cuando reciba autorización por escrito del contratante, debidamente firmada por la máxima autoridad o de quien éste delegue» | Firmante con FIRMAR × CONTRATACIONES (ORG-03/04/06/07, delegación incluida) y soporte firmado obligatorio. No hace falta un segundo acto DOC-02: la autorización escrita es el propio instrumento |
| Reconocimiento | LCP art. 130, párr. 2 | «El contratante solo procederá a reconocer y pagará las modificaciones… cuando las haya autorizado expresamente» | Solo cuenta lo FORMALIZADO; un borrador no tiene efecto |
| Causas | LCP art. 131 | «1. El incremento o reducción en la cantidad…; 2. Que surjan nuevas partidas…; 3. Se modifique la fecha de entrega…; 4. Variaciones en los montos…; 5. Las establecidas en el Reglamento» | Cambios admitidos: monto (aumento o reducción), plazo y condiciones textuales. El tipo clasifica el instrumento; no determina el efecto |
| Variación del presupuesto | LCP art. 132 | «variaciones del presupuesto original las fundamentadas por el contratista, por hechos posteriores imprevisibles…, debidamente aprobadas por el contratante» | Tipo VARIACION, con motivo obligatorio |
| Variaciones de precios | LCP art. 133 | «se reconocerán y pagarán… de acuerdo a los mecanismos establecidos en los contratos» | Fuera de alcance: no hay fórmula escalatoria (CNT-06 / N38) |
| Prórroga | LCP art. 135 | «A solicitud expresa del contratista, el contratante podrá acordar prórrogas del plazo… por razones plenamente justificadas» | Tipo PRORROGA: nueva fecha de fin posterior a la vigente y motivo obligatorio |
| Disponibilidad | LCP art. 74 | «A los fines de la formalización del contrato, los contratantes deberán contar con la respectiva disponibilidad presupuestaria»; «…previa formalización de los contratos o adendas respectivas» | Un aumento exige cobertura BUD-06 adicional antes de formalizar |
| Control | LCP art. 136 | «asignando el o los supervisores o ingenieros inspectores» | CNT-04 es de P1: no se toca |

**Límite de fuente.** No hay copia local de `rlcp.pdf` (N12, Reglamento) y no se descargó. CNT-02 no deriva ninguna regla del Reglamento, por ejemplo topes porcentuales de aumento o plazos de solicitud. Queda como **OQ-CNT02-01**: si el Reglamento fija topes, se añadirán en un delta. No se inventan.

N20 (NGCI, G.O. 40.851) aporta segregación, trazabilidad y conservación de la historia. Se aplica con CTL-01/PROC-11, con la auditoría y con la inmutabilidad.

## Requisito del sponsor

Fuente: IR (`requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`), §7.5, tal como figura en `GOVERNMENT_REQUIREMENTS_PRODUCT_MATRIX.md`.

> **GOV-CNT-002** (N11, N12, N20; P0): «Versionar adendas, prorrogas, modificaciones y variaciones sin sobrescribir el texto/condiciones originales.»

## Autoridades del repositorio que se reutilizan

| Dato | Autoridad | Código |
|---|---|---|
| Contrato de origen | CNT-01 | `GovernmentContract` FORMALIZADO, con `snapshot` y `huella` (guarda PG: inmutable) |
| Cobertura | BUD-06 | `GovernmentBudgetCertificate` VIGENTE; saldo libre según el delta H07 de CNT-01 |
| Compromisos | BUD-08 | `GovernmentBudgetCommitment` VIGENTE y sus líneas, `procurement_file_id` (solo lectura) |
| Tasas | TRE-09 | `service_tasas.verificar_limite`, `canonical_currency` |
| Firmante | ORG-03/04/06/07 | `_autoridad_valida`, `exigir_autoridad_funcional`, `competencia_en_vigor` |
| Documento | DOC-08 | El mismo patrón que CNT-01 (`_documento_valido`, `sellar_documento`, `congelar_vinculo`) |
| SoD | CTL-01 / PROC-11 | `CATALOGO_SOD["PROC-03"]`, ampliado con `PROC03_MODIFICACION_*` |
| Cronología | PROC-03 | `_evento`, clase `CONTRATO` existente (sin cambiar el CHECK) |
