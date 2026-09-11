# SPEC 037 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-037-001 · el saldo es `documentos + débitos − cobros − retenciones − créditos` | arq. funcional §9 | `customer_balance` | `test_el_saldo_del_cliente_resta_los_creditos_sin_aplicar` | ✔ |
| IMP-037-002 · los saldos se calculan, no se editan | doc. maestro | consultas, sin campo guardado | ídem | ✔ |
| IMP-037-003 · el crédito se resta **una vez** | §9 · P0 de doble conteo | `credit_available` | `test_aplicar_el_credito_no_lo_resta_dos_veces` · **M4** | ✔ |
| IMP-037-004 · el crédito es del cliente que lo tiene | doctrina · `ARCH-MC-001` | `CREDIT_CUSTOMER_MISMATCH` | `test_el_credito_de_un_cliente_no_se_aplica_al_documento_de_otro` · **M1** | ✔ |
| IMP-037-005 · la misma empresa no basta | ídem | comprobación de `party_id` | `test_la_api_bloquea_la_aplicacion_entre_clientes` | ✔ |
| IMP-037-006 · cada aplicación deja su fila | §9 «cada aplicación relaciona…» | `Application` canónica | `test_el_credito_se_aplica_al_documento_de_su_propio_cliente` · **M2** | ✔ |
| IMP-037-007 · la fila lleva origen, destino, moneda, tasa, importe y fecha | §9 | ídem | ídem | ✔ |
| IMP-037-008 · el reverso no elimina | §9 «los reversos no eliminan» | `reverse_credit_application` | `test_el_reverso_no_borra_la_aplicacion_original` · **M3** | ✔ |
| IMP-037-009 · el reverso crea evento inverso | ídem | fila con importe contrario | ídem | ✔ |
| IMP-037-010 · reapertura controlada | ídem | el documento vuelve a `OPEN` por tener saldo | ídem | ✔ |
| IMP-037-011 · no se revierte dos veces | doctrina | `APPLICATION_ALREADY_REVERSED` | `test_una_aplicacion_no_se_revierte_dos_veces` | ✔ |
| IMP-037-012 · revertir exige motivo | doctrina de los controles | `REVERSAL_REASON_REQUIRED` | `test_revertir_exige_motivo` | ✔ |
| IMP-037-013 · solo misma moneda | §9 «según **política**», inexistente | `CREDIT_CURRENCY_MISMATCH` | `test_no_se_aplica_un_credito_en_otra_moneda` | ✔ |
| IMP-037-014 · sin tipo de cambio implícito | ídem | no hay conversión | ídem | ✔ |
| IMP-037-015 · no se aplica más de lo que queda | §9 | `APPLICATION_EXCEEDS_SOURCE` | `test_no_se_aplica_mas_credito_del_que_queda` | ✔ |
| IMP-037-016 · un crédito se reparte entre documentos | §9 «soporta parcial, múltiple» | varias aplicaciones | `test_un_credito_se_reparte_entre_varios_documentos_del_mismo_cliente` | ✔ |
| IMP-037-017 · el estado de cuenta reconstruye la cronología | CxC «Documentos; Cobros; Aplicaciones…» | `customer_statement` | `test_el_estado_de_cuenta_reconstruye_la_cronologia` | ✔ |
| IMP-037-018 · el saldo no cruza empresas | `ARCH-MC-001` | `_company` en cada entrada | `test_el_saldo_del_cliente_no_cruza_empresas` | ✔ |
| IMP-037-019 · aplicar un crédito no crea cobros | §4 del prompt · doctrina | ningún `Payment` | `test_la_api_no_crea_cobros_ni_movimientos_de_tesoreria` | ✔ |
| IMP-037-020 · aplicar un crédito no mueve tesorería | ídem | ídem | ídem · e2e | ✔ |
| IMP-037-021 · la respuesta dice el estado real | doctrina | saldo y remanente en el cuerpo | `test_la_api_aplica_y_devuelve_el_estado_real` | ✔ |
| IMP-037-022 · la empresa la manda el contexto | `ARCH-MC-001` | `CompanyContext` | `test_la_api_no_aplica_un_credito_de_otra_empresa` | ✔ |
| IMP-037-023 · el reverso respeta la empresa | ídem | `_company` | `test_no_se_revierte_una_aplicacion_de_otra_empresa` | ✔ |
| IMP-037-024 · la nota de débito entra como documento propio | Spec 036 | `OpenItem` propio | `test_la_nota_de_debito_aumenta_la_cuenta_por_cobrar` (036) | ✔ |
| IMP-037-025 · las retenciones entran como aplicado | §9 | motor de la 028 | `test_purchasing.py` · aging | ✔ |
| IMP-037-026 · los permisos existen en el catálogo | `ARCH-MC-001` | `ventas:view/apply/approve` | catálogo de `setup/api.py` | ✔ |
| IMP-037-027 · no hay reembolso | **sin autoridad** | — | 0 endpoints, 0 pantallas | ✔ |
| IMP-037-028 · el selector de clientes no trunca | lección de la 031 | paginación hasta agotar `total` | e2e de interfaz | ✔ |

## Delta dirigido sobre otra Spec

| Delta | Dueña | Por qué |
|---|---|---|
| El saldo deja de calcularse en `float` | **028** (`004-compras`) | `open_item_balance` es el motor compartido de CxP, CxC, tesorería y conciliación. `ADR-D0-001` ya registraba `KQA-100` como defecto CRÍTICO y este motor nunca lo recibió. Convergido en `spec028-monetary-balance-delta.md` |

## Deltas heredados, verificados en este ciclo

| Delta | Dueña | Estado |
|---|---|---|
| `issue_invoice` abre la cuenta por cobrar | 034 | convergido · `IMP-034-041` |
| `emit_document` emite los tres tipos | 042 (`007-nucleo-fiscal`) | convergido en este ciclo · `FR-007-020-D1` |

## Cobertura

| | |
|---|---:|
| Requisitos funcionales | 28 |
| Con implementación y prueba | **28** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
| Mutaciones permanentes | **4** (M1–M4) |
