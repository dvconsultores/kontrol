# FUENTES · CNT-08 Expediente contractual completo (GOV-CNT-009)

| Id | Fuente | Uso en CNT-08 |
|---|---|---|
| GOV-CNT-009 | Ingeniería de Requerimientos v1.0, P0: «Conservar expediente contractual completo disponible para control fiscal y rendición de cuentas.» | Requisito del sponsor |
| N18 | LOCGRSNCF, G.O. 6.013 Ext. («expediente de cuenta y evidencia reproducible») | El órgano de control fiscal accede a los soportes sin modificarlos; la evidencia debe poder reproducirse |
| N21 | Resolución CGR N.º 01-00-000167, G.O. 40.492 (leída para CTL-05, `specs/gov-ctl-05-expediente-de-cuenta/FUENTES.md`) | Art. 7: soportes resguardados y a disposición del órgano de control. Art. 12: «organizados, enumerados y clasificados». Disposición final segunda: conservación de 10 años |
| N22 | Normas Generales de Auditoría de Estado, G.O. 40.172 | Evidencia suficiente, trazable y verificable (papeles de trabajo) |

## Autoridades dueñas que el expediente proyecta (sin copiar su semántica)

| Proceso | Autoridad en el código | Qué aporta |
|---|---|---|
| PROC-03 | `service_expedientes.cronologia`, `GovernmentProcurementFile`, folios `GovernmentProcurementFileFolio` | Origen, cronología de la contratación e índice documental del procedimiento |
| PROC-06 | `GovernmentProcurementOffer` (`gov_contracts.offer_id`) | Oferta adjudicada |
| PROC-08 | `GovernmentProcurementDecision` (`gov_contracts.decision_id`) | Adjudicación, acto y cargo |
| PROC-10 | `GovernmentGuaranteeInstrument` y `GovernmentGuaranteeEvent`, vínculo `gov_contract_guarantees` | Garantías del contrato y sus eventos |
| BUD-06 | `GovernmentBudgetCertificate` (comprobante con huella) | CDP del expediente y asignaciones de CNT-01 y CNT-02 |
| BUD-08 | `GovernmentBudgetCommitment` y sus líneas (comprobante con huella) | Compromisos del mismo expediente |
| CNT-01 | `service_contratos.ficha` y `GovernmentContract` | Raíz contractual: instrumento original e inmutable |
| CNT-02 | `service_contratos_modificaciones.historia` | Condiciones vigentes e historial de modificaciones |
| CNT-04 | `service_contratos_supervision.supervision` y `supervisor_en` | Supervisor vigente, historia y supervisor en una fecha |
| CNT-03 | P1, no publicado al abrir el ciclo | Contrato de consumo: `SOURCE_PROCESS_NOT_AVAILABLE` hasta su publicación |
| DOC-02 | `GovernmentAct` | Actos de adjudicación, de designación y de los folios |
| DOC-08 | `service_paquetes` (ZIP determinista, SHA256SUMS, control documental, verificación) | Primitivas que reutiliza el paquete contractual |
| Documentos | `documents.service` (`puede_leer_archivo`, `assert_deliverable`) y `storage` (`exists`, `verify`) | Descarga e integridad de los binarios |
| CTL-02 | `AuditEvent` y `service_auditoria._resumenes` | Eventos institucionales del expediente; navegación a `/gobierno/auditoria?evento=` |

`MATERIAL_BLOCKER_FOUND = 0`. Ninguna fuente fija un formato de exportación. Se adopta el de DOC-08, que es reproducible y verificable.
