# MATRIZ DE TRAZABILIDAD — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-005-001 | FR-005-001 |
| US-005-002 | FR-005-002 |
| US-005-003 | FR-005-010, FR-005-012 |
| US-005-004 | FR-005-011, FR-005-020 |
| US-005-005 | FR-005-021 |
| US-005-006 | FR-005-023, FR-005-024 |
| US-005-007 | FR-005-022 |
| US-005-008 | FR-005-030, FR-005-031, FR-005-033, FR-005-034 |
| US-005-009 | FR-005-040, FR-005-041, FR-005-043, FR-005-044 |
| US-005-010 | FR-005-042, FR-005-045, FR-005-047 |
| US-005-011 | FR-005-046 |
| US-005-012 | FR-005-048, FR-005-100, FR-005-102 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-005-001/002 | T-005-001 | Test de flujo |
| FR-005-010/011/012 | T-005-002 | Test de crédito/máquina |
| FR-005-020/021/022/023/024 | T-005-003 | Test de integración 003 |
| FR-005-030/031/032/033/034 | T-005-004 | Test de estados/snapshot |
| FR-005-045/047 | T-005-005 | Test de nota/CxC |
| FR-005-040/100 | T-005-006 | Test de saldo |
| FR-005-041/102 | T-005-007 | Test de cobro/idempotencia |
| FR-005-042 | T-005-008 | Test de aplicación/saldo |
| FR-005-043/046 | T-005-009 | Test de aging/anticipo |
| FR-005-044 | T-005-010 | Test de retención |
| FR-005-048 | T-005-011 | Test de permisos |
| FR-005-101 | T-005-012/013 | Contract test |
| NFR multiempresa | T-005-019 | Pytest negativo |
| NFR concurrencia | T-005-020 | Pytest de concurrencia |
| NFR accesibilidad | T-005-021 | axe |
| CHK-005-DB-006 | T-005-022 | CI migración |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |

---

# TRAZABILIDAD — SPEC 029 · ORIGEN COMERCIAL

| Requisito | Código | Prueba | Evidencia |
|---|---|---|---|
| FR-029-017/018 · una sola autoridad de precio | `sales/service._origen_comercial` | `test_ventas_no_crea_un_segundo_resolutor_de_precio` | AST |
| FR-029-019 · se captura la resolución | `0042`, modelos | `test_una_linea_sin_precio_lo_resuelve_y_guarda_su_origen` | `pricing_source=RESOLVED` |
| FR-029-020 · origen del precio | `price_source_version_id` | ídem + `test_el_origen_apunta_a_la_version_no_a_la_lista` | versión, no lista |
| FR-029-021 · origen del descuento | `discount_policy_id/version` | `test_el_descuento_registra_su_politica` | política y versión |
| FR-029-022 · evidencia de versión | `price_source_item_id` | `test_toda_linea_comercial_conserva_su_evidencia` | 9 columnas |
| FR-029-025/026 · sin recálculo | — | `test_una_cotizacion_no_se_recalcula_cuando_cambia_la_lista` | V2 a 120, línea a 100 |
| FR-029-027 · la evidencia viaja | `convertir_en_pedido` | `test_la_conversion_lleva_la_evidencia_al_pedido` | precio y origen |
| FR-029-028 · sin reprecio silencioso | ídem | `test_la_conversion_no_reprecia_en_silencio`, `test_la_conversion_no_vuelve_a_resolver` | ejecución + AST |
| FR-029-029 · cambio manual auditable | `manual_reason` | `test_un_precio_manual_exige_motivo_y_conserva_el_resuelto` | `422` sin motivo |
| FR-029-031/032 · sin coma flotante | `Numeric(18,4)` | `test_ningun_importe_de_venta_es_de_coma_flotante`, `test_el_precio_de_la_linea_no_trunca_el_del_maestro` | escala ≥ maestro |
| FR-029-041/042 · vigencia | `_vencida` | `test_una_cotizacion_vencida_no_se_convierte` | `409` |
| FR-029-043/044 · una cotización, un pedido | índice único parcial | `test_convertir_dos_veces_no_crea_dos_pedidos` | `201` y luego `200` |
| FR-029-046 · vínculo con la cotización | `sales_orders.quote_id` | ídem | mismo id |
| FR-029-047 · pedido directo con origen | `add_order_line` | — | misma autoridad |
| FR-029-035/036 · sin reserva | — | `test_convertir_no_reserva_inventario` | reservado igual antes y después |
| FR-029-038..040 · sin picking ni factura | — | `test_convertir_no_crea_lista_de_preparacion_ni_factura` | 0 y 0 |
| FR-029-008..010 · líneas derivadas | `__scope_authority__` | `test_las_lineas_derivan_su_empresa_y_no_la_duplican` | sin `company_id` |
| FR-029-011..016 · multiempresa | `_owned`, `_require_quote` | `test_la_cotizacion_de_otra_empresa_no_se_lee_ni_se_convierte`, `test_el_usuario_con_acceso_a_las_dos_no_cruza_el_contexto` | `404` y el contraste en B |
| FR-029-060 · histórico autosuficiente | referencia + snapshot | `test_el_historico_sobrevive_al_archivado_de_su_version` | versión archivada |

Cobertura **100%** · Requisitos sin tarea **0** · Tareas sin requisito **0**.
