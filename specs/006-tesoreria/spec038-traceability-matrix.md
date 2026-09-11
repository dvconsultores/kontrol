# SPEC 038 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-038-001 · la tasa no se inventa | `OWNER-DECISION-038-02` · defecto §4.1 | `_rate_snapshot` devuelve `None`; `RATE_NOT_AVAILABLE` | `test_sin_tasa_registrada_la_conversion_se_niega` · **M6** · e2e P0 | ✔ |
| IMP-038-002 · la instantánea guarda su procedencia entera | doctrina de auditabilidad | `TreasuryRateSnapshot` con tasa, fuente, tipo, fecha, origen, versión y fila | `test_la_instantanea_guarda_la_procedencia_entera` | ✔ |
| IMP-038-003 · la tasa se busca **con fecha**, no «la más reciente» | doctrina · defecto §4.2 | `_buscar_tasa(… <= día)` | `test_una_tasa_de_hoy_no_valora_una_operacion_de_ayer` | ✔ |
| IMP-038-004 · una tasa posterior no revalúa lo ya hecho | ídem | instantánea congelada en la operación | `test_la_instantanea_sobrevive_al_cambio_de_tasa` | ✔ |
| IMP-038-005 · la tasa manual exige política **y** motivo | `OWNER-DECISION-038-02` | `MANUAL_RATE_NOT_ALLOWED` | `test_la_tasa_manual_exige_politica_y_motivo` | ✔ |
| IMP-038-006 · la política es parametrizable y versionada | `OWNER-DECISION-038-02` · §3 del prompt | `TreasuryFxPolicy` con versión y vigencia | `test_la_politica_anterior_no_se_borra_al_activar_otra` | ✔ |
| IMP-038-007 · ninguna regla legal venezolana está en el código | §3 del prompt · `D0-07` | `authority_reference` configurable | revisión del módulo · sin condicionales de país | ✔ |
| IMP-038-008 · la política nace en borrador; activarla es otro acto | doctrina de los controles | `create_fx_policy` → `DRAFT` | `test_la_api_activa_una_politica_y_sustituye_la_anterior` · e2e | ✔ |
| IMP-038-009 · activar **sustituye** sin borrar | ídem | la anterior queda `SUPERSEDED` | `test_la_politica_anterior_no_se_borra_al_activar_otra` | ✔ |
| IMP-038-010 · la conversión es explícita y deja dos movimientos | `OWNER-DECISION-038-02` | `convert_currency` | `test_la_conversion_deja_dos_movimientos_y_su_instantanea` · e2e | ✔ |
| IMP-038-011 · sin política activa no se convierte | ídem | `FX_POLICY_MISSING` | `test_sin_politica_no_hay_conversion` | ✔ |
| IMP-038-011b · sin política que lo permita no hay reembolso | `OWNER-DECISION-038-01` | `REFUND_NOT_ALLOWED` | `test_sin_politica_que_lo_permita_no_hay_reembolso` | ✔ |
| IMP-038-012 · no se convierte sin fondos | §71 «no negative cash by accident» | `INSUFFICIENT_FUNDS` | `test_no_se_convierte_sin_fondos` · **M8** | ✔ |
| IMP-038-013 · dos cuentas de la misma moneda no son una conversión | doctrina | `SAME_CURRENCY_CONVERSION` | `test_dos_cuentas_de_la_misma_moneda_no_son_una_conversion` | ✔ |
| IMP-038-014 · convertir dos veces con la misma clave no mueve dos veces | idempotencia | `idempotency_key` | `test_convertir_dos_veces_con_la_misma_clave_no_mueve_dos_veces` | ✔ |
| IMP-038-015 · el reembolso existe, no es automático | `OWNER-DECISION-038-01` | `request_refund` → `REQUESTED` | `test_la_api_recorre_el_reembolso_entero` · e2e | ✔ |
| IMP-038-016 · solicitar **reserva** el crédito | ídem | `refund_reserved` en la nota | `test_solicitar_reserva_el_credito_y_lo_quita_de_lo_aplicable` · e2e P0 | ✔ |
| IMP-038-017 · lo reservado deja de ser imputable | ídem · doble gasto | resta en `customer_credits` y `apply_credit_note` | `test_lo_reservado_no_puede_aplicarse_a_una_cuenta_por_cobrar` · **M5** | ✔ |
| IMP-038-018 · ejecutar exige aprobación previa | `OWNER-DECISION-038-01` | `REFUND_NOT_APPROVED` | `test_no_se_ejecuta_sin_aprobar` | ✔ |
| IMP-038-019 · aprobar no paga | ídem | el dinero sale en `settle_refund` | `test_ejecutar_saca_el_dinero_y_consume_el_credito` · e2e | ✔ |
| IMP-038-020 · denegar libera la reserva | ídem | `decide_refund(approved=False)` | `test_denegar_libera_la_reserva` · e2e | ✔ |
| IMP-038-021 · ejecutar consume la reserva y saca el dinero | ídem | reserva → `refunded` + movimiento `OUT` | `test_ejecutar_saca_el_dinero_y_consume_el_credito` · **M7** | ✔ |
| IMP-038-022 · ejecutar dos veces no paga dos veces | idempotencia · dinero | `settled_at` corta la repetición | `test_ejecutar_dos_veces_no_saca_el_dinero_dos_veces` · e2e P0 | ✔ |
| IMP-038-023 · no se reembolsa más de lo que queda | doble gasto | `REFUND_EXCEEDS_CREDIT` | `test_no_se_devuelve_mas_credito_del_que_queda` | ✔ |
| IMP-038-024 · no se ejecuta un reembolso sin fondos | §71 «no negative cash by accident» | `INSUFFICIENT_FUNDS` al ejecutar | `test_no_se_ejecuta_un_reembolso_sin_fondos` · **M8** | ✔ |
| IMP-038-025 · la cuenta pagadora es de la misma moneda | doctrina | `REFUND_CURRENCY_MISMATCH` | `test_no_se_devuelve_desde_una_cuenta_de_otra_moneda` | ✔ |
| IMP-038-026 · el crédito de otra empresa no se reembolsa | `ARCH-MC-001` | `_company` + pertenencia | `test_no_se_devuelve_un_credito_de_otra_empresa` · `test_la_api_no_devuelve_un_credito_de_otra_empresa` · **M9** | ✔ |
| IMP-038-027 · la comprobación de dueño va **antes** que la de política | lección de la Spec 035 | orden en `request_refund` | `test_el_credito_de_otra_empresa_no_existe_aunque_la_politica_prohiba` · **M9** | ✔ |
| IMP-038-028 · todo el dinero se calcula en `Decimal` | `MONETARY-BALANCE-INVARIANT` · `KQA-100` | `_money`, sin `float()` ni `1e-6` | `test_el_arqueo_no_arrastra_error_binario` | ✔ |
| IMP-038-029 · el saldo de una cuenta se calcula desde movimientos | «los saldos no se editan» | `account_balance` | `test_el_saldo_de_la_cuenta_sale_de_los_movimientos` | ✔ |
| IMP-038-030 · la posición no suma monedas distintas | doctrina · §78 | `cash_position` sin total | `test_la_posicion_de_caja_no_mezcla_monedas` · `test_la_api_expone_la_posicion_sin_mezclar_monedas` · e2e | ✔ |
| IMP-038-031 · la empresa la manda el contexto | `ARCH-MC-001` | `CompanyContext` en las 12 rutas | `test_la_api_no_devuelve_un_credito_de_otra_empresa` | ✔ |
| IMP-038-032 · los permisos existen en el catálogo | `ARCH-MC-001` | `tesoreria:view/create/approve` | catálogo de `setup/api.py` · sin permisos nuevos | ✔ |
| IMP-038-033 · el IGTF no se amplía | §5 del prompt · dueña 041 | módulo intacto | revisión del diff | ✔ |
| IMP-038-034 · no se consulta ninguna web para la tasa | §78 del prompt | solo el maestro de tasas | revisión del módulo · sin cliente HTTP | ✔ |

## Delta dirigido a la Spec 037

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-037-027 · «imputable» descuenta lo reservado y lo devuelto | `OWNER-DECISION-038-01` | `customer_credits` · `customer_balance` | `test_el_credito_reservado_deja_de_ofrecerse_como_disponible` | ✔ |
| IMP-037-028 · el saldo solo se mueve cuando el dinero sale | doctrina · deuda vs. forma de pago | `credit_refunded` en la resta del saldo | `test_el_saldo_solo_se_mueve_cuando_el_dinero_sale` | ✔ |

Sin huérfanos: 35 requisitos de la 038 y 2 del delta, todos con autoridad,
implementación y prueba.
