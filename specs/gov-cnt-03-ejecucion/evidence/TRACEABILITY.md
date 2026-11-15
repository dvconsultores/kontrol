# Trazabilidad · CNT-03

| Contrato | FR | Código | Prueba |
|---|---|---|---|
| C03-01 contrato formalizado | FR-01 | `_preparar` (FOR UPDATE; 409 NOT_FORMALIZED, CLOSED, NOT_STARTED) | PG precondiciones; Vitest e |
| C03-02 términos efectivos | FR-02 | `terminos_efectivos(db, contrato, fecha)` = CNT-01 + adenda CNT-02 vigente a la fecha | PG prórroga CNT-02 |
| C03-03 supervisor a la fecha | FR-03 | `_conformante`: `supervisor_en(fecha)` + `_funcionario_del_actor` (403 NOT_SUPERVISOR / 409 NO_SUPERVISOR + BLOCKED) | PG conformidad_solo_del_supervisor, supervisor_a_la_fecha_del_hecho |
| C03-04 inicio | FR-04 | `iniciar` (formalización ≤ fecha ≤ min(hoy, fin); acta; único) | PG precondiciones; E2E paso 3; Vitest b–c |
| C03-05 hitos | FR-05 | `crear_hito`, `anular_hito` (suma de montos ≤ monto efectivo; porcentaje ≤ 100; cumplido derivado) | PG recorrido, entregas_y_anulaciones; E2E paso 4 |
| C03-06 entregables | FR-06 | `crear_entregable`, `entregar`, `revisar_entrega` (una abierta y una conforme) | PG entregas_y_anulaciones; E2E paso 5-6 |
| C03-07 valuación | FR-07 | `presentar_valuacion`, `resolver_valuacion` (CONFORMADA/REPARADA), `anular_valuacion` | PG recorrido, tope; E2E paso 7; Vitest d |
| C03-08 tope acumulado | FR-08 | Σ presentada + conformada ≤ monto efectivo (Decimal, FOR UPDATE) | PG tope, concurrencia_valuaciones; E2E paso 8 |
| C03-09 recepción parcial | FR-09 | `registrar_recepcion` PARCIAL (bienes/servicios; entregables obligatorios conformes) | PG recorrido, factura; E2E paso 9 |
| C03-10 recepción definitiva | FR-10 | DEFINITIVA; obras: TERMINACIÓN → PROVISIONAL (representante + fin de garantía) → DEFINITIVA tras la garantía | PG flujo_obras_con_garantia, concurrencia_definitiva; E2E 12-13 |
| C03-11 factura | FR-11 | `vincular_factura` (hito + recepción conforme del contrato; tope por lo valuado; número único) | PG factura_requiere_recepcion_y_tope; E2E 10-11 |
| C03-12 sin efecto contable | FR-12 | ninguna escritura en presupuesto, tesorería, contabilidad ni pagos | PG recorrido (GovernmentBudgetCommitment sin cambios) |
| C03-13 cierre operativo | FR-13 | `cerrar` (definitiva; acta de aprobación + evaluación distintas; aprobador Comisión/Unidad) | PG recorrido; E2E paso 14 |
| C03-14 historia inmutable | FR-14 | `kontrol_gov_contract_exec_guard` (transiciones por TG_ARGV; sin DELETE ni TRUNCATE) | PG inmutable_en_base |
| C03-15 concurrencia | FR-15 | FOR UPDATE del contrato + índices únicos parciales (definitiva, provisional, entregas, facturas) | PG concurrencia_valuaciones, concurrencia_definitiva |
| C03-16 aislamiento | FR-16 | `company_id` en todas las consultas; 404 | PG aislamiento |
| C03-17 auditoría | FR-17 | 18 eventos GOV_CONTRACT_EXEC_* + cronología del expediente | PG recorrido, conformidad, tope; E2E paso 16 |
| C03-18 frontera CNT-02 | FR-02 | `_formalizadas` + `_vigente_a` (P2); ambos bloquean el contrato | PG prórroga CNT-02; E2E CNT-02 en verde tras el merge |
| C03-19 frontera almacén | FR-12 | recepción contractual ≠ movimiento de almacén (no se crea ninguno) | revisión de código; PG recorrido |
| C03-20 E2E / UAT | FR-18 | página «Ejecución del contrato»; CSV | E2E gobierno-contratos (16 pasos, 1280/390/320, Axe); humo UAT |
