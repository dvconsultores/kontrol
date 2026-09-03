# SPEC 030 — INTEGRACIÓN CON EL MOTOR DE APROBACIONES (SPEC 045)

| Campo | Valor |
|---|---|
| Proceso | `SALES_CREDIT` (`approvals_integration.PROCESS_SALES_CREDIT`) |
| Puntos de contacto | `require_for_document` (al confirmar) · `ensure_approved` (al liberar) · `approvals_service.status` + `cancel` (al rechazar, revertir, cancelar, expirar) |
| Motor duplicado | **Ninguno**: sin tablas, estados ni reglas de aprobación en ventas (`test_spec030_architecture.py`) |

## Quién decide si hace falta crédito

La Spec 045: política activa de `SALES_CREDIT` + reglas sobre el contexto del pedido
(`_order_credit_context`: monto, moneda, cliente, lista). Sin política activa, `require` responde
`requires_approval: False` y el pedido es **de contado** por definición. No existe `if
payment_term == CREDIT` en ventas (§45).

## Secuencia

| Paso | Contado | Crédito |
|---|---|---|
| confirmar | reserva → `SUBMITTED` → `require` (sin solicitud) → `RELEASED` en la misma transacción | reserva → `SUBMITTED` → `require` abre `ApprovalRequest` (`approval_ref`); TTL opcional en las reservas |
| decidir | — | el aprobador actúa en la bandeja de 045 (`/approvals/steps/{id}/approve|reject`) |
| liberar | ya hecho | `POST /sales/orders/{id}/release` → `ensure_approved`: `APPROVAL_PENDING` (409) si sigue viva, `APPROVAL_NOT_GRANTED` (409) si fue rechazada/obsoleta; aprobada → `RELEASED`, `expires_at := NULL` |
| rechazar | — | `POST …/reject {reason}`: si hay solicitud viva la cancela en 045 con el motivo; libera; `REJECTED` |
| revertir | libera; `DRAFT` | cancela la solicitud viva (`ORDER_REVERTED: motivo`); libera; `DRAFT`; reemitir abre una solicitud nueva (una aprobación no sobrevive a la reversión, §47) |
| expirar | — | cancela la solicitud viva (`EXPIRED`); reservas y pedido `EXPIRED` |

Es el mismo patrón que compras (015/017): el dominio avanza cuando 045 resolvió; el motor no llama
al dominio. Por eso liberar es una acción explícita del dominio con `ensure_approved` como compuerta.

## Pruebas

`test_con_credito_el_pedido_espera_en_submitted_con_la_reserva_hecha` (espera, bloqueo, aprobación
por `uab`, liberación sin re-reservar) · `test_rechazar_el_credito_libera_toda_la_reserva_en_la_misma_transaccion`
(rechazo en 045 → `release` 409 → `reject` libera) · `test_rechazar_desde_ventas_cierra_la_solicitud_viva_de_045`
(sin solicitudes huérfanas) · `test_revertir_libera_todo_y_reemitir_reserva_desde_cero` (la aprobación
previa no se reutiliza) · `test_ttl_opcional_…` (expirar cierra la solicitud).
