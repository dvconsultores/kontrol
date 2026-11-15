# CNT-03 · Fuentes leídas (2026-11-15)

## Normativa

| Código | Instrumento | Copia leída |
|---|---|---|
| N11 | Decreto-Ley de Contrataciones Públicas (G.O. 6.154 Ext., 19-11-2014) | PDF sha256 `a87a12d3…` (texto extraído, fuera del repositorio) |
| N12 | Reglamento de la LCP (G.O. 39.181, 19-05-2009) | PDF sha256 `1aac01e1…` |
| N03 | LOAFSP (G.O. 6.210 Ext.) | fichada; solo marca la frontera: compromiso, causado y pago no son de CNT-03 |
| N06 | Reglamento N.º 4 de la LOAFSP | fichada; sus momentos del gasto quedan fuera |
| N20 | Normas Generales de Control Interno | escaneo sin capa de texto; no aporta reglas de ejecución contractual |

| Regla | Fuente | Texto (literal, abreviado) | Consecuencia en CNT-03 |
|---|---|---|---|
| Inicio | LCP art. 127 | «deberá dejarse constancia de la fecha en que se inicie efectivamente … mediante acta o documento que será firmado por las partes» | Inicio único, con fecha real y acta obligatoria |
| Inicio a cargo del supervisor | LCP art. 137.1 y 138.1 | «Verificar el inicio de la ejecución del contrato y suscribir los documentos necesarios»; «Elaborar y firmar el Acta de Inicio» | Lo registra el usuario del supervisor vigente en la fecha (OD-CNT03-03) |
| Avance | LCP art. 137.3 y 138.7 | «Informar por escrito el avance de la ejecución» | Valuaciones y entregas con fecha y soporte, y una cronología |
| Conformidad | LCP art. 137.5 | «Elaborar y firmar los documentos de conformidad de la ejecución del contrato» | Entregables, valuaciones, recepciones y facturas las conforma el supervisor |
| Pago | LCP art. 141 | «1. Verificación del cumplimiento … 2. Recepción y revisión de las facturas … 3. Conformación, por parte del supervisor … 4. Autorización del pago» | CNT-03 cubre 1–3: recepción conforme y factura conformada. El 4 (autorización del pago) y el pago son de TRE-04 y BUD-09 |
| Valuaciones | LCP art. 142 | «el contratista elaborará los formularios o valuaciones … reflejará la cantidad de obra o servicio ejecutado, en un periodo determinado … verificados por el supervisor» | Valuación = medición de un período, con monto, soporte y conformidad del supervisor |
| Reparos | LCP art. 143 | «El ingeniero inspector indicará al contratista los reparos que tenga que hacer a las valuaciones» | Resultado REPARADA, con reparos obligatorios |
| Bienes y servicios | LCP art. 146 | «Ejecutados los contratos de bienes y servicios a satisfacción … certificar el cumplimiento de todas las obligaciones» | La recepción definitiva certifica el cumplimiento (OD-CNT03-01) |
| Obras: terminación | LCP art. 147 | «Mediante acta suscrita por el ingeniero inspector … dejar constancia de la terminación de la obra» | Acta de terminación, solo en OBRAS |
| Obras: aceptación provisional | LCP art. 148 | «deberá constar en acta firmada por el representante del contratante, el ingeniero inspector …» | Recepción PROVISIONAL en OBRAS, con supervisor y representante del contratante |
| Obras: garantía | LCP art. 149 | «lapso de garantía … comenzará a contarse a partir de la fecha del acta de terminación» | La provisional declara el fin de la garantía |
| Obras: definitiva | LCP art. 150 | «Concluido el lapso … recepción definitiva … acta … suscrita por el representante del contratante, el ingeniero inspector» | DEFINITIVA en OBRAS solo con PROVISIONAL previa y la garantía vencida |
| Cierre | LCP art. 151; art. 145 | «certificar el cumplimiento … y realizar el cierre administrativo del contrato» | Cierre operativo tras la DEFINITIVA |
| Aprobación del cierre | RLCP, Comisión de Contrataciones (atribución 15) y Unidad Contratante (atribución 5) | «Aprobar el cierre del contrato y la evaluación sobre la actuación o desempeño del contratista» | Cierre con el acta de aprobación y la evaluación de desempeño, atribuido a la Comisión del expediente o a la Unidad Contratante (OD-CNT03-02) |
| Expediente | RLCP (administración del contrato) | «Actas de inicio, suspensión, terminación y recepción provisional o definitiva … Formularios para el pago o valuaciones … Finiquito» | Los soportes son documentos del expediente, reutilizando DOC (sin un segundo gestor documental) |
| Facturas | RLCP art. 177 | «presentar las facturas o valuaciones … debidamente conformadas por el supervisor» | Factura conformada por el supervisor y vinculada a hito y recepción (GOV-CNT-007) |
| Anticipos, retenciones, penalidades | LCP arts. 128 y ss.; RLCP art. 176 | — | Fuera: CNT-06 |
| Rescisión y resolución | LCP arts. 152-155 | — | Fuera: CNT-07 |

## Requisitos del sponsor

`requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, §7.5:

- **GOV-CNT-003** (N11, N12, N20; P0): «Controlar inicio, hitos, entregables, valuaciones, actas, recepciones parciales/definitivas y cierre.»
- **GOV-CNT-007** (N11, N03, N06; P0): «Relacionar cada factura/cuenta de cobro con recepcion conforme y hito contractual aplicable.»
- IR §5: «Administrador/Supervisor de contrato: controla hitos, entregables, valuaciones, recepciones y garantías».
- IR §3: «v1.0 cubre contratación, hitos, valuaciones y control documental» (obras, sin BIM).

## Decisiones de la dueña (2026-11-15)

- **OD-CNT03-01:** dos flujos según el tipo de contratación del expediente: OBRAS por un lado, BIENES y SERVICIOS por otro.
- **OD-CNT03-02:** el cierre exige el acta de aprobación más la evaluación de desempeño, atribuido a la Comisión del expediente o a la Unidad Contratante.
- **OD-CNT03-03:** conforma el usuario vinculado al funcionario que era supervisor en la fecha del hecho.
- **OD-CNT03-04:** la suma de facturas de un hito no puede superar lo valuado y conformado de ese hito.

## Autoridades del repositorio que se reutilizan

| Dato | Autoridad | Código |
|---|---|---|
| Contrato y términos | CNT-01 | `GovernmentContract` FORMALIZADO, con `monto`, `moneda`, `fecha_inicio`, `fecha_fin` y `fecha_formalizacion`. Se bloquea con FOR UPDATE y nunca se escribe |
| Tipo de contratación | PROC-03 | `GovernmentProcurementFile.tipo_contratacion` (BIENES, SERVICIOS u OBRAS), `committee_id` y `unidad_nombre` |
| Supervisor a la fecha | CNT-04 | `service_contratos_supervision.supervisor_en(db, ctx, contrato_id, fecha)` |
| Identidad del actor | ORG-04 / CTL-03 | `service_identidad._funcionario_del_actor(db, ctx)` |
| Representante del contratante (obras) | ORG-03/07 | `_autoridad_valida(db, company, cargo_id, fecha, "APROBAR", "CONTRATACIONES")` |
| Documentos | DOC | `Document`, `DocumentVersion` y `DocumentLink` del expediente; `sellar_documento` y `congelar_vinculo` |
| Cronología | PROC-03 | `_evento(..., "CONTRATO", ...)` |
| SoD | CTL-01 | `CATALOGO_SOD["PROC-03"]` y `evaluar_antes_de_actuar` |
| Auditoría | CTL-02 | `record_audit` / `record_audit_after_rollback` sobre `GovernmentProcurementFile` |
| Comisión | PROC-02 | `GovernmentProcurementCommittee` (nombre) |
