# CNT-01 · Fuentes leídas (2026-11-14)

## Normativa

`lcp.pdf` se descargó de nuevo de CEBM Miranda, en
<https://www.cebm.gob.ve/wp-content/uploads/2026/09/ley-de-contrataciones-y-administracion-financiera-del-sector-publico-2014.pdf>.
Su SHA-256, `a87a12d3b578d97f94bb639b852aad18e60bf238ef14a00f7554189fc32cb5d8`, es **idéntico** al de la copia verificada en
PROC-02 a PROC-10. El texto se extrajo fuera del repositorio.

N11 es el Decreto-Ley de Contrataciones Públicas: G.O. 6.154 Ext., 19-11-2014, Decreto 1.399.

| Regla | Fuente | Texto (literal, abreviado) | Consecuencia en CNT-01 |
|---|---|---|---|
| Qué es un contrato | LCP art. 6, num. 32 | «Instrumento jurídico que regula la ejecución de una obra, prestación de un servicio o suministro de bienes, incluidas las órdenes de compra u órdenes de servicio… Deberá contener: precio, cantidades, forma de pago, tiempo, forma de entrega, especificaciones contenidas en el pliego… y oferta» | Un instrumento con tres tipos: CONTRATO, ORDEN_COMPRA y ORDEN_SERVICIO. Precio = total declarado; tiempo = plazo del instrumento. La ley no asocia el tipo a la modalidad: lo elige el usuario |
| Disponibilidad para contratar | LCP art. 74, párr. 1 | «A los fines de la formalización del contrato, los contratantes deberán contar con la respectiva disponibilidad presupuestaria» | No se formaliza sin cobertura de CDP vigente |
| Disponibilidad parcial | LCP art. 74, párr. 3 | «podrán adjudicar… sin contar con la totalidad de la disponibilidad presupuestaria, suscribiendo el contrato por el monto disponible y el resto quedará sujeto a la disponibilidad… previa formalización de los contratos o adendas respectivas» | **OQ-CNT01-01**: no se construye. CNT-01 exige cobertura del monto completo |
| Plurianual | LCP art. 75 | «solo procederán a suscribir el contrato por el monto disponible para el primer ejercicio fiscal y el resto quedará sujeto a la disponibilidad… para cada ejercicio subsiguiente» | **OQ-CNT01-01**: no se construye. Las CDP del contrato son de un solo ejercicio |
| Documentos para formalizar | LCP art. 116 | «1. Documentos legales de la persona… 2. El pliego de condiciones y la oferta. 3. Solvencias y garantías requeridas. 4. Cronograma de desembolso… de ser necesario. 5. Certificados que establezcan las garantías respectivas y sus condiciones» | Instrumento firmado obligatorio y garantías vinculables (PROC-10). La pantalla no infiere cuáles son obligatorias |
| Firma | LCP art. 117 | «El lapso máximo para la firma del contrato será de ocho días hábiles contados a partir de la notificación de la adjudicación… no estarán sujetos a la formalidad de autenticación» | Se informa en la ficha. No bloquea: no existe el calendario hábil y la alerta de vencimiento es de CNT-09 |
| Control posterior | LCP art. 118 | «una vez formalizada la contratación… deberán garantizar… el cumplimiento… estableciendo controles» | Fuera de CNT-01 (CNT-03 y CNT-04) |
| Nulidad del contrato | LCP art. 121 | «El contratante deberá declarar la nulidad de los contratos…» | Fuera de CNT-01 (CNT-07 y CNT-08) |

## Requisito del sponsor

Fuente: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, §7.5.

> **GOV-CNT-001** (N11, N12, N03; P0): «Crear contrato/orden derivada de adjudicacion aprobada, preservando objeto, monto, moneda,
> plazo, garantia y fuente presupuestaria.»

La máquina de estados que propone el IR para el contrato es `DRAFT -> APPROVED -> ACTIVE -> SUSPENDED (opcional) -> COMPLETED/TERMINATED -> CLOSED`.

CNT-01 cubre solo el tramo inicial, que se corresponde así:

| CNT-01 | IR |
|---|---|
| BORRADOR | DRAFT |
| FORMALIZADO | APPROVED (instrumento suscrito) |

`ACTIVE` y los estados posteriores pertenecen a CNT-03, CNT-07 y CNT-08.

## Autoridades del repositorio que se reutilizan

| Dato | Autoridad | Código |
|---|---|---|
| Adjudicación | PROC-08 | `GovernmentProcurementDecision`: `estado=VIGENTE`, `resultado=ADJUDICADA`, `offer_id`. TERMINADA sustituye y NULIDAD anula (`service_decision_resolver`) |
| Contratista | PROC-06 | `GovernmentProcurementOffer.oferente_nombre`, `oferente_documento` y `representante` |
| Objeto | PROC-03 | `GovernmentProcurementFile.objeto` y `numero` |
| Monto y moneda | PROC-06 (OMA) | `GovernmentProcurementOfferAmount`, la última versión: `total_con_tributos` y `moneda` (VES, USD o EUR) |
| Fuente presupuestaria | BUD-06 | `GovernmentBudgetCertificate`: VIGENTE o ANULADA, con `monto`, `moneda` (= moneda funcional del ejercicio), `credit_id` y `procurement_file_id` |
| Garantías | PROC-10 | `GovernmentGuaranteeInstrument` del expediente y de la oferta, en estado `REGISTRADA` |
| Documento | DOC-08 | Documento vinculado al expediente (`DocumentLink`), con versión vigente y `sha256`; mismo patrón que PROC-10 |
| Firmante | ORG-03, ORG-04, ORG-06 y ORG-07 | `_autoridad_valida(…, "FIRMAR", "CONTRATACIONES")` y `exigir_autoridad_funcional`, como el firmante de BUD-06 |
| Límite del firmante | AAL (PROC-08) | `competencias_en_vigor` y la regla de comparación de `service_decision_limite` |
| SoD | CTL-01 y PROC-11 | Catálogo `CATALOGO_SOD["PROC-03"]`, ampliado como hizo PROC-10 con `PROC03_GARANTIA_*`. PROC-11 no tiene una función de firmante |
| Cronología | PROC-03 | `_evento` en `service_expedientes` con una clase nueva, `CONTRATO`; mismo patrón que `GARANTIA` en la migración 0096 |

## Hallazgo sobre la moneda

**OQ-CNT01-02.** Los dos dominios usan códigos distintos para el bolívar:
- Gobierno (límites, montos y garantías) usa `MONEDAS_LIMITE = ("VES", "USD", "EUR")`.
- La moneda funcional del ente y del ejercicio presupuestario es por defecto `VED` (`organization.models.Company.functional_currency`).

En ISO 4217, VES y VED son unidades distintas: 1 VED = 1.000.000 VES. CNT-01 **no** los equipara, porque eso sería una conversión.
Por eso, una oferta en VES no puede cubrirse con una CDP en VED hasta que la dueña decida la equivalencia de códigos o se cree la autoridad de tasas (TRE-09).
