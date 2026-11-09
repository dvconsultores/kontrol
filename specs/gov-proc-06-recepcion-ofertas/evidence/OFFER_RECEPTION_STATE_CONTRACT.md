# OFFER_RECEPTION_STATE_CONTRACT · PROC-06

## SOURCE_BACKED_STATE

La ley habla de **sobres sellados** y de **acto de recepción concluido** (LCP art. 92) y de **apertura** posterior (art. 93). No define estados de sistema.

## DERIVED_IMPLEMENTATION_STATE (sin efecto jurídico)

| Nombre interno | Etiqueta | Significado |
|---|---|---|
| `PENDIENTE_APERTURA` | Pendiente de apertura | Recibida y sin apertura; PROC-06 no tiene otro estado |
| `confidencial = true` | Sellada hasta la apertura | Sello activo en la capa documental |
| `confidencial = false` | Sin sello | Modalidad sin exigencia y decisión motivada |
| `recepcion_concluida_en` | Recepción concluida | No se admiten más ofertas |

La fila de oferta es inmutable por trigger. Backend = autoridad. `PROC07_OPENING_COMPLETE = 0`: nada abre ni levanta un sello en este ciclo.
