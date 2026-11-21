# Traceability · V4

| Requisito | Rebaseline | Código | Prueba | Mutación | E2E |
|---|---|---|---|---|---|
| V4-FR-01 cantidad | INV-05, INV-13 | `confirm_transfer_ship`, `confirm_transfer_receipt` | `test_transferencia_parcial_conserva_cantidad_y_valor` | M14 | E2E-V4-01 |
| V4-FR-02 valor | INV-05, INV-09, INV-13 | `_record_consumption`, `_restore_from_consumptions` | parcial, FIFO, landed manual, landed real (API importaciones) | M1, M2, M3, M4, M11 | E2E-V4-01; landed: corrida diagnóstica |
| V4-FR-03 recepción | INV-05 | `confirm_transfer_receipt`, `TransitionBody.received` | `test_recepcion_parcial_por_la_api_y_luego_completa`, `test_el_valor_en_transito_es_visible_y_vuelve_al_recibir` | M14 | E2E-V4-01 |
| V4-FR-04 ubicada | INV-05 | `_origin_pieces` | `test_se_transfiere_mercancia_ya_ubicada_...` | — | diagnóstica de importaciones (mercancía ubicada) |
| V4-FR-05 reverso | INV-06, INV-17 | `reverse_movement`, `_own_layers_for_reversal`, `_retire_layers` | entrada, salida, estado, doble, consumida, transferencia suelta | M5, M6 | — |
| V4-FR-06 reversión de transferencia | INV-05 | `reverse_transfer`, `/transfers/{id}/reverse` | restaura ambos almacenes, API con motivo, ya consumida | M6 | E2E-V4-01 |
| V4-FR-07 ajustes | INV-07, INV-18 | `adjustment_allowed_actions`, `apply_adjustment`, `current_unit_cost` | positivo, negativo, auditoría | M10, M10b | — |
| V4-FR-08 conteos | INV-08 | `count_allowed_actions`, `record_count_line`, `approve_count` | `test_conteo_recorre_su_ciclo_y_valora_la_diferencia` | M13 | — |
| V4-FR-09 recálculo | INV-01 | `recompute_balances_endpoint`, `recompute_balances` | 403 sin permiso; auditoría; reservas pendientes | M7, M15 | — |
| V4-FR-10 concurrencia | INV-03, INV-05 | `record_movement` (lock), `_origin_pieces` (ancla) | `test_dos_transferencias_no_sacan_mas_de_lo_que_hay[True/False]` | M9 | — |
| V4-FR-11 aislamiento | SEG-06 | `_require_warehouse`, `_get_owned` | cruza empresas, mismo almacén, otra empresa y otro tenant | M8 | — |
| V4-FR-12 auditoría | AUD-01 | `_audit` + catálogo | rastro de transferencia y ajuste | M12 | — |
| V4-FR-13 superficie | TRV-06 | `_nombres`, `_transfer_dict`, páginas | Vitest | — | E2E-V4-01 (nombres, estado, valor) + Axe 1280/390/320 |
