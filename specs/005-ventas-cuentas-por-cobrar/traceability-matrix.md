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

---

# TRAZABILIDAD — SPEC 030 · CRÉDITO / APROBACIÓN / RESERVA

Formato exigido: `| Requirement | D0-03 Rule | Plan | Task | Migration/Code | Test | Evidence | Status |`.
Abreviaturas: **M** `0043_spec030_reservation` · **INV** `inventory/service.py` · **SAL** `sales/service.py` ·
**API** `sales/api.py` / `inventory/api.py` · **FE** frontend · **T-R** `test_spec030_reservation.py` ·
**T-C** `test_spec030_concurrency.py` · **T-H** `test_spec030_postgres_hostile.py` · **T-A**
`test_spec030_architecture.py` · **T-M** `test_spec030_migration_0043.py` · **E2E** `e2e/sales-orders.spec.ts`.

## Requisitos funcionales FR-030

| Requirement | D0-03 Rule | Plan | Task | Migration/Code | Test | Evidence | Status |
|---|---|---|---|---|---|---|---|
| FR-030-001 trigger fijo `ORDER_CONFIRMATION` | R-1 | ola 7 | T-030-I-017 | SAL `confirmar_pedido`, `RESERVATION_TRIGGER` | T-R contado · T-A trigger | `reservation-state-machine-report.md` | ✔ |
| FR-030-002 máquina de estados | R-11 | ola 2 | T-030-I-005 | SAL `ORDER_TRANSITIONS`, M (estados) | T-A máquina · T-R compat · T-M estados | ídem | ✔ |
| FR-030-003 `APPROVED` no reserva; `RELEASED` | R-2 | ola 7-8 | T-030-I-018 | SAL `_a_released`, `liberar_pedido` | T-R contado/crédito | `credit-approval-integration-report.md` | ✔ |
| FR-030-004 sin solicitud → `RELEASED` | R-2 | ola 7 | T-030-I-018 | SAL `confirmar_pedido` | T-R contado | ídem | ✔ |
| FR-030-005 crédito vía 045 | R-2 | ola 8 | T-030-I-019 | SAL `require_for_document` | T-R crédito | ídem | ✔ |
| FR-030-006 aprobar solo hace firme | R-2 | ola 8 | T-030-I-020 | SAL `_a_released` (`expires_at := NULL`) | T-R crédito | ídem | ✔ |
| FR-030-007 rechazo libera | R-6 | ola 9 | T-030-I-021 | SAL `rechazar_pedido` | T-R rechazo ×2 | ídem | ✔ |
| FR-030-010 insuficiencia 409 con detalle | R-4 | ola 7 | T-030-I-039 | SAL faltantes → `ConflictError(details)` | T-R insuficiencia · E2E | `reservation-concurrency-report.md` | ✔ |
| FR-030-011 todo-o-nada | R-4 | ola 7 | T-030-I-040 | SAL dos fases bajo bloqueo | T-R multilínea | ídem | ✔ |
| FR-030-012 backorder OUT_OF_SCOPE | R-12 | — | — | sin estados ni colas | T-A guardias · T-R multilínea | `spec030-boundary-report.md` | ✔ |
| FR-030-013 almacén obligatorio | R-5 | ola 7 | T-030-I-003 | SAL `WAREHOUSE_REQUIRED` | T-R sin almacén | — | ✔ |
| FR-030-014 un almacén, sin cruzado | R-5 | ola 7 | T-030-I-015 | SAL usa `order.warehouse_id` | T-R almacén ajeno | `multi-company-evidence.md` | ✔ |
| FR-030-015 cantidad base con snapshot | R-4 | ola 6-7 | T-030-I-016 | SAL `_unidad`, `_asegurar_unidad`; INV `reserve(base_quantity)` | T-R caja ×12 | — | ✔ |
| FR-030-016 sin recálculo | R-4 | ola 6 | T-030-I-016 | copia del snapshot de la línea | T-R caja ×12 (cambio de factor) | — | ✔ |
| FR-030-017 solo `DISPONIBLE` | R-5 | ola 6 | T-030-I-012 | INV `lock_balance(state="DISPONIBLE")` | T-R saldos | — | ✔ |
| FR-030-018 lote/serial solo si la línea; ubicación nunca | R-5 | ola 6 | T-030-I-016 | INV sin `location_id`; SAL sin lote (la línea aún no lo modela) | T-A modelo | `spec030-boundary-report.md` | ✔ |
| FR-030-020 solo `DRAFT` editable | R-7 | ola 9 | T-030-I-022 | SAL `add_order_line` → `ORDER_NOT_EDITABLE` | T-R no edit | — | ✔ |
| FR-030-021 `REVERT_TO_DRAFT` libera y obsoleta | R-7 | ola 9 | T-030-I-022 | SAL `revertir_pedido` + `approvals.cancel` | T-R revertir | `credit-approval-integration-report.md` | ✔ |
| FR-030-022 sin deltas | R-7 | ola 9 | T-030-I-022 | ídem | T-R revertir (4+8) | — | ✔ |
| FR-030-023 cancelar libera, idempotente | R-6 | ola 9 | T-030-I-023 | SAL `cancelar_pedido`, INV `release_if_active` | T-R cancelar · E2E | `reservation-idempotency-report.md` | ✔ |
| FR-030-024 TTL por empresa, defecto NULL | R-8 | ola 10 | T-030-I-025 | M `companies.reservation_ttl_days`; API `/settings/reservation` | T-R TTL · E2E política | — | ✔ |
| FR-030-025 expirar pedido y reserva; sin worker | R-8 | ola 10 | T-030-I-024 | SAL `expirar_reservas_de_pedidos`; INV `expire_due_reservations` | T-R TTL · T-A sin planificador | — | ✔ |
| FR-030-026 nunca pedido vivo sin reserva | R-8 | ola 10 | T-030-I-024 | expirar cierra el pedido; manual bloqueada | T-R TTL · T-R manual | — | ✔ |
| FR-030-027 liberación manual con motivo, solo MANUAL | R-6 | ola 6 | T-030-I-027 | API `ReleaseBody`, `RESERVATION_ORDER_BOUND` | T-R manual | — | ✔ |
| FR-030-030..034 multiempresa | R-10 | ola 17 | T-030-I-036..038 | cadena `_owned` + `_require_warehouse`; cuerpos estrictos | T-R AB/tenant/almacén/cuerpo | `multi-company-evidence.md` | ✔ |
| FR-030-035 `ventas:submit` | R-10 | ola 12 | T-030-I-026 | M permiso; `setup/api.py`; API rutas | T-A permisos · T-M permiso | — | ✔ |
| FR-030-040 `FOR UPDATE` + orden determinista | R-3 | ola 6, 15 | T-030-I-012/013 | INV `lock_balance`; SAL `sorted` | T-C carrera · T-A bloqueo | `reservation-concurrency-report.md` | ✔ |
| FR-030-041 unicidad de saldo + `CHECK ≥ 0` | R-3 | ola 5 | T-030-I-008 | ORM + M | T-H 6/7/10 | `postgresql-integrity-report.md` | ✔ |
| FR-030-042 índice parcial por línea activa | R-3 | ola 5 | T-030-I-007 | ORM + M | T-H 5 | ídem | ✔ |
| FR-030-043 liberar/expirar/consumir dos veces = no-op | R-3 | ola 16 | T-030-I-043 | INV `_close_reservation` + guardas | T-R cancelar/manual/TTL | `reservation-idempotency-report.md` | ✔ |
| FR-030-044 prueba de carrera PostgreSQL | R-3 | ola 15 | T-030-I-042 | — | T-C (2 casos) | `reservation-concurrency-report.md` | ✔ |
| FR-030-050 `RELEASED` entrega a 031 | R-9, R-11 | ola 18 | T-030-I-052 | SAL `order_dict` (reservas por línea, `eligible_for_picking`) | T-R contado · E2E | — | ✔ |
| FR-030-051/052 sin picklist, ubicación ni custodia | R-9 | ola 18 | T-030-I-049 | — | T-R no-efectos | `spec030-boundary-report.md` | ✔ |
| FR-030-053 factura no toca reserva | R-9 | ola 18 | T-030-I-050 | — | T-R no-efectos | ídem | ✔ |
| FR-030-054 despacho consume `FULFILLED` | R-6 | ola 6 | T-030-I-015 | SAL `confirm_shipment` → INV `fulfill_reservation` | T-R despacho · T-A | ídem | ✔ |
| FR-030-060 eventos de reserva | R-3 | ola 11 | T-030-I-028 | INV `_audit_reservation` | T-R auditoría · T-C (rastro único) | — | ✔ |
| FR-030-061 motivo en el pedido | R-6 | ola 11 | T-030-I-028 | SAL `_audit(reason=…)` | T-R auditoría | — | ✔ |
| FR-030-062 columnas de identidad | R-3 | ola 3 | T-030-I-006 | ORM + M | T-A modelo · T-M columnas | `reservation-migration-report.md` | ✔ |
| FR-030-063 migración SAFE + MANUAL_REVIEW | — | ola 4 | T-030-I-009/010 | M (clasificación, estados) | T-M (7 casos) · instalación limpia | ídem | ✔ |

## Requisitos de implementación IMP-030

| IMP | Garantía | Código | Prueba | Status |
|---|---|---|---|---|
| 001 | `DRAFT` no reserva | SAL | T-R contado (antes de confirmar) | ✔ |
| 002 | conversión 029 no reserva | — | `test_convertir_no_reserva_inventario` | ✔ |
| 003/004 | único disparador; `DRAFT→SUBMITTED` | SAL | T-A · T-R | ✔ |
| 005/006 | almacén obligatorio y de la empresa | SAL | T-R sin almacén · almacén ajeno | ✔ |
| 007/008 | base snapshot, sin recálculo | SAL/INV | T-R caja ×12 | ✔ |
| 009..012 | todo-o-nada, 409, `DRAFT`, sin parcial | SAL | T-R insuficiencia · multilínea | ✔ |
| 013 | sin backorder | — | T-A · boundary | ✔ |
| 014/015 | oversell solo `allow_negative`, auditado | INV | T-R sobreventa · T-C | ✔ |
| 016/017/018 | identidad pedido/línea; una ACTIVE por línea | ORM/M | T-R contado · T-H 5 | ✔ |
| 019/020 | sin duplicar por reintento; sin negativo | SAL/INV/DB | T-R doble · T-H 6/7 | ✔ |
| 021/022/023 | lock real, sin sobre-reserva, orden determinista | INV/SAL | T-C · T-A | ✔ |
| 024/025 | contado → `RELEASED`; crédito espera en `SUBMITTED` | SAL | T-R | ✔ |
| 026/027 | `SALES_CREDIT`; sin segundo motor | SAL | T-R crédito · T-A | ✔ |
| 028/029/030 | aprobar no re-reserva, hace firme, `RELEASED` | SAL | T-R crédito | ✔ |
| 031/032/033 | rechazo libera, `REJECTED`, transaccional | SAL | T-R rechazo | ✔ |
| 034/035 | cancelar libera; motivo obligatorio | SAL/API | T-R cancelar · E2E | ✔ |
| 036..039 | revertir libera todo, sin deltas, reemitir reserva | SAL | T-R revertir | ✔ |
| 040/041 | TTL opcional, defecto NULL | M/API | T-R TTL · E2E | ✔ |
| 042/043/044 | sin planificador; expirar idempotente; pedido `EXPIRED` | SAL/INV | T-A · T-R TTL | ✔ |
| 045..049 | AB, cross-tenant, permiso ≠ contexto, cuerpo, URL | API | T-R multiempresa | ✔ |
| 050/051/052 | auditoría completa | INV/SAL | T-R auditoría | ✔ |
| 053..057 | handoff `RELEASED`; sin picklist, ubicación, factura, CxC | SAL | T-R no-efectos | ✔ |
| 058/059/060 | unicidad en DB; reservado ≥ 0; ORM = Alembic = PostgreSQL | ORM/M | T-H · T-M · instalación limpia | ✔ |
| 061 | OpenAPI con contrato de empresa | API | fixture regenerado; `audit-completeness.test.ts` | ✔ |
| 062 | frontend respeta contexto y máquina | FE | `architecture-company.test.ts` · E2E ×3 navegadores | ✔ |
| 063 | deuda interna P0 = 0 | — | `convergence.md` §SPEC 030 | ✔ |

**Cobertura: FR-030 100 % · IMP-030 63/63 · Huérfanos: 0.**
