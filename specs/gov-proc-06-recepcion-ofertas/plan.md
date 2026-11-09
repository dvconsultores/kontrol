# Plan PROC-06

`SHARED_CORE_CHANGE_REQUIRED = 1`: ver `evidence/SHARED_CORE_CHANGES.md`.

- **Núcleo documental:** tabla `document_seals`, reglas en servicio y API; sello activo = documento inexistente para `/documentos`; `verificar_integridad` sin entrega.
- **Gobierno:** `gov_procurement_offers` y `gov_procurement_offer_documents`, inmutables; dos columnas de conclusión en el expediente; clase de evento `OFERTA`; acción SoD `PROC03_RECIBIR`.
- **API:** `/gobierno/contrataciones/expedientes/{id}/ofertas`: listar, detalle, recibir, concluir.
- **Interfaz:** sección «Ofertas» en la ficha, sin ruta ni entrada de menú nueva.

**Constitution gate:** aislamiento por `company_id`; autorización del mandato; reglas con artículo citado y sin lapsos; `MATERIAL OQ = 0`. Decisiones de diseño, reversibles, en `OFFER_RECEPTION_STATE_CONTRACT.md`.
