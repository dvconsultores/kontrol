# Plan PROC-07

- **Datos (una migración):** `gov_procurement_eval_matrices`, `gov_procurement_eval_criteria`, `gov_procurement_openings`, `gov_procurement_opening_attendees`, `gov_procurement_opening_offers`, `gov_procurement_eval_contributions`, `gov_procurement_eval_results`; columnas de levantamiento en `document_seals`; conclusión en el expediente; clases de evento `APERTURA_OFERTA` y `EVALUACION`. Inmutables por trigger salvo la matriz en borrador.
- **Servicio:** `service_evaluacion.py`; reutiliza ofertas, sello, comisiones, identidad, SoD, auditoría y cronología.
- **API:** `/gobierno/contrataciones/expedientes/{id}/evaluacion`.
- **Interfaz:** sección «Apertura y evaluación» en la ficha.
- **Gate:** fuentes citadas, `MATERIAL OQ = 0` tras las decisiones de la dueña, aislamiento por `company_id`.
