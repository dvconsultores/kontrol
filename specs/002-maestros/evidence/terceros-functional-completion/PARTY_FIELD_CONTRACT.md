# Contrato de campos

| Campo | Alta | Edición | Regla |
|---|---|---|---|
| code | obligatorio | **no editable** | Texto. Los documentos e informes lo muestran como identidad estable |
| name | obligatorio | sí | |
| person_type | JURIDICA por defecto | sí | Determina la validación del RIF; vocabulario JURIDICA, NATURAL, PUBLICA, EXTRANJERA, GUBERNAMENTAL |
| nationality, residence | opcional | sí | Antes el alta los ignoraba |
| legal_name, trade_name, economic_activity | opcional | sí | |
| tax_id | opcional | sí | Normalizado por `validate_tax_id`; unicidad por empresa |
| roles | al menos uno | por rutas de rol | Vocabulario cerrado |
| status | ACTIVE | por activar y desactivar | |
| version | 1 | +1 en cada cambio | `If-Match` obligatorio en PATCH y PUT; sin él 428 `VERSION_REQUIRED`; desfasada 409 `VERSION_CONFLICT` |
