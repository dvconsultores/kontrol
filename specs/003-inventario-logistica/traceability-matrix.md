# MATRIZ DE TRAZABILIDAD — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-003-001 | FR-003-010, FR-003-012, FR-003-013 |
| US-003-002 | FR-003-090, FR-003-092 |
| US-003-003 | FR-003-030, FR-003-032, FR-003-034, FR-003-036 |
| US-003-004 | FR-003-031, FR-003-033, FR-003-036 |
| US-003-005 | FR-003-040, FR-003-041, FR-003-042, FR-003-043 |
| US-003-006 | FR-003-060, FR-003-061, FR-003-062 |
| US-003-007 | FR-003-070, FR-003-071 |
| US-003-008 | FR-003-072, FR-003-073 |
| US-003-009 | FR-003-080, FR-003-081, FR-003-082, FR-003-083 |
| US-003-010 | FR-003-050, FR-003-051, FR-003-052 |
| US-003-011 | FR-003-020, FR-003-021, FR-003-022, FR-003-024 |
| US-003-012 | FR-003-035 |
| US-003-013 | FR-003-092 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-003-001/002/003/004 | T-003-001 | Test de maestros/estados |
| FR-003-023/024 | T-003-002 | Test de tipos/seed |
| FR-003-020/021/022 | T-003-003 | Test de balanceo/reverso |
| FR-003-010/011/012/013 | T-003-004 | Test de reconstrucción |
| FR-003-030/032/035/036 | T-003-005 | Test de lote/unicidad |
| FR-003-031/033/035 | T-003-006 | Test de serial |
| FR-003-034 | T-003-007 | Test FEFO |
| FR-003-040/041/042/043 | T-003-008 | Test de reserva/concurrencia |
| FR-003-050/051/052 | T-003-009 | Test de picking/salida |
| FR-003-060/061/062 | T-003-010 | Test de máquina de estados |
| FR-003-070/071 | T-003-011 | Test de conteo |
| FR-003-072/073 | T-003-012 | Test de ajuste/segregación |
| FR-003-080/081/082/083 | T-003-013 | Test de capas/valoración |
| FR-003-090/091/092 | T-003-014 | Test de kardex/auditoría |
| FR-003-104 | T-003-015 | Contract test |
| FR-003-103 | T-003-016..021 | E2E + axe |
| NFR concurrencia | T-003-022 | Pytest de concurrencia |
| NFR multiempresa | T-003-023 | Pytest negativo |
| NFR rendimiento | T-003-024 | Prueba de rendimiento |
| NFR accesibilidad | T-003-025 | axe |
| CHK-003-DB-006 | T-003-026 | CI migración |
| CHK-003-OP-002 | T-003-027 | Test de reconstrucción |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |

---

# TRAZABILIDAD — CICLO DIRIGIDO DE SALDO MULTIESTADO (2026-09-03)

Ciclo de auditoría. **Cero código de producto.** La trazabilidad cubre lo auditado y lo decidido,
no lo implementado, porque el ciclo se detuvo antes de `/speckit.implement` por dos OQ materiales.

| Requisito | Regla ADR | Estado del catálogo | Evidencia | Resultado |
|---|---|---|---|---|
| IMP-023-MS-001 · el estado es autoridad de inventario | R-D0-10-1 | los 15 | `uq_inventory_balances_key` incluye `state` | **Ya cumplido** |
| IMP-023-MS-002 · los estados vienen del ADR | R-D0-10-2 | los 15 | catálogo extraído, §4 del ciclo | **Verificado** |
| IMP-023-MS-003 · no hay estados inventados | — | los 15 | `VENCIDO` es de lote/serial (`FR-003-035`), no de mercancía | **Verificado** |
| IMP-023-MS-004 · vendibilidad definida | R-D0-10-3 | los 15 | exclusivamente `DISPONIBLE` | **Cerrado por el ADR** |
| IMP-023-MS-005 · reservabilidad definida | R-D0-03-5 · POL-D0-002 §7 | los 15 | solo `DISPONIBLE`; la reserva no cambia custodia | **Cerrado por autoridad** |
| IMP-023-MS-006 · disponible excluye lo no vendible | POL-D0-002 §1 | `DISPONIBLE` | la consulta ya filtra por estado | **Ya cumplido** |
| IMP-023-MS-007 · la 030 no reserva lo no reservable | R-D0-03-5 | `DISPONIBLE` | `lock_balance` por defecto `DISPONIBLE`; así lo llama ventas | **Ya cumplido** |
| IMP-023-MS-008 · el movimiento conserva el estado | R-D0-10-5 | — | `InventoryMovement` **no tiene columna de estado** | **HUECO ESTRUCTURAL** |
| IMP-023-MS-009 · el saldo diferencia por estado | R-D0-10-5 | los 15 | la clave ya lo permite; solo hay filas `DISPONIBLE` | **Parcial: capacidad sin ejercicio** |
| IMP-023-MS-010 · la clave incluye las dimensiones | — | los 15 | empresa, almacén, ubicación, producto, lote, serial, estado | **Ya cumplido** |
| IMP-023-MS-011 · la reclasificación conserva físico | R-D0-10-5 | — | derivable, no requiere decisión | **Definido, no implementado** |
| IMP-023-MS-012 · la reclasificación deja rastro | R-D0-10-5 | — | imposible sin IMP-023-MS-008 | **Bloqueado por el hueco** |
| IMP-023-MS-013 · no altera unidad ni cantidad base | Spec 011 | — | el saldo ya acumula base desde la Spec 019 | **Ya cumplido** |
| IMP-023-MS-014/015/016/017 · preserva almacén, ubicación, `NULL`, lote y serial | Spec 008 · 024 | — | la clave los lleva; `COALESCE` los hace únicos | **Ya cumplido** |
| IMP-023-MS-018 · sin negativo ilegal | — | — | derivable de la conservación | **Definido, no implementado** |
| IMP-023-MS-019/020 · idempotencia y concurrencia | POL-D0-002 §5 | — | patrón de la Spec 030 disponible y probado | **Definido, no implementado** |
| IMP-023-MS-021..024 · empresa, tenant, usuario AB, contexto | ARCH-MC-001 | — | el saldo es `Scope.COMPANY`; sin cambios | **Ya cumplido** |
| IMP-023-MS-025/026 · un solo motor y un solo disponible | — | — | Constitution Gate PASS | **Verificado** |
| IMP-023-MS-027 · los llamantes siguen funcionando | — | — | diez puntos localizados y atribuidos | **Verificado** |
| IMP-023-MS-028 · la caja ×12 de la Spec 019 | Spec 011 · 019 | `DISPONIBLE` | sin cambios de código; regresión intacta | **Ya cumplido** |
| IMP-023-MS-029 · la reserva solo sobre elegible | R-D0-03-5 | `DISPONIBLE` | la suma nunca cruza estados | **Ya cumplido** |
| IMP-023-MS-030 · el total se reconstruye del ledger | R-D0-10-5 | — | `recompute_balances` colapsaría todo en `DISPONIBLE` | **HUECO ESTRUCTURAL** |
| IMP-023-MS-031/032 · paridad ORM/Alembic/OpenAPI | — | — | sin delta: no se tocó nada | **N/A en este ciclo** |
| IMP-023-MS-033 · trazabilidad | — | — | esta tabla | **100 % de lo auditado** |
| IMP-023-MS-034 · deuda P0 propia | — | — | el ciclo no introduce código | **0** |
| IMP-023-MS-035 · la 021 puede consumir estados no vendibles | R-D0-10-4 | — | **exige OQ-023-MS-01 y OQ-023-MS-02** | **BLOQUEADO** |

**Cobertura del alcance auditado: 100 %. Huérfanos: 0. OQ materiales: 2.**

---

## Cierre de las dos OQ materiales — 2026-09-03

El checkpoint `D0-10` (`docs/governance/d0-foundational-decisions/d0-10-checkpoint/`) cerró las dos
preguntas que dejaron `IMP-023-MS-035` bloqueado. La fila se actualiza:

| Requisito | Estado anterior | Estado |
|---|---|---|
| IMP-023-MS-035 · la 021 puede consumir estados no vendibles | **BLOQUEADO** por `OQ-023-MS-01` y `-02` | **DESBLOQUEADO** — `ADR-D0-010` v2 declara las cuatro transiciones que la 021 necesita |

Y se añade lo que el próximo ciclo de implementación hereda ya decidido:

| Requisito | Regla | Artefacto |
|---|---|---|
| Validación de transición contra matriz declarada | R-D0-10-7 + §Gobierno v2 | `d0-10-merchandise-state-transition-matrix.md` |
| Nueve transiciones activas con permiso, aprobación y motivo | v2 | ídem |
| Aprobación de la transición #9 vía Spec 045 | `FR-003-062` | ídem |
| Invariante `qty_reserved > qty_on_hand` prohibida | **R-D0-10-9** | `ADR-D0-010` v2 |
| Quién decide la política de conflicto y cuándo | **R-D0-10-10** | `d0-10-reserved-stock-conflict-analysis.md` |
| `InventoryMovement` con estado de origen y destino | R-D0-10-5 | `ADR-D0-010` v2 §Consecuencias |
| `recompute_balances` sin asumir `DISPONIBLE` | R-D0-10-5 | ídem |
| `confirm_transfer_receipt` respeta `destination_state` | `FR-003-062` · transición #9 | ídem |

---

# TRAZABILIDAD — CAPACIDAD MULTIESTADO IMPLEMENTADA (2026-09-04)

| Requisito | Regla D0-10 | Transición | Código / migración | Prueba | Estado |
|---|---|---|---|---|---|
| IMP-023-MS-001 · el estado es autoridad de inventario | R-D0-10-1 | — | `states.py` · clave del saldo | `test_el_catalogo_tiene_los_quince_estados_del_adr` | ✔ |
| IMP-023-MS-002 · catálogo = `ADR-D0-010` v2 | R-D0-10-2 | — | `MERCHANDISE_STATES` | ídem | ✔ |
| IMP-023-MS-003 · lote/serial separado | — | — | `LOT_SERIAL_TRANSITIONS` intacto | `test_los_vocabularios_no_se_mezclan` | ✔ |
| IMP-023-MS-004 · lo no declarado se rechaza | **R-D0-10-7** | todas | `assert_transition` | `test_una_transicion_no_declarada_se_rechaza_por_nombre` | ✔ |
| IMP-023-MS-005 · la activa se acepta con su contrato | R-D0-10-7 | 10 | `ACTIVE_TRANSITIONS` | `test_cada_arista_declara_su_evidencia` | ✔ |
| IMP-023-MS-006/007/008 · dueño, permiso y aprobación | v2 §Gobierno | 10 | `Transition` · `ensure_approved` | guardia estructural + `test_una_transicion_que_exige_motivo…` | ✔ |
| IMP-023-MS-009 · procedencia en el ledger | **R-D0-10-5** | todas | `source_state` · `target_state` · `0046` | `test_el_movimiento_guarda_de_donde_sale_y_a_donde_entra` | ✔ |
| IMP-023-MS-010 · el saldo materializa el estado | R-D0-10-5 | todas | `record_movement(state=…)` | `test_el_motor_escribe_el_estado_que_le_piden` | ✔ |
| IMP-023-MS-011/012 · reconstrucción fiel y paridad | **R-D0-10-5** | todas | `recompute_balances` | `test_reconstruir_da_exactamente_lo_mismo_que_el_camino_incremental` | ✔ |
| IMP-023-MS-013 · conservación física | R-D0-10-5 | reclasificación | `reclassify` | `test_la_reclasificacion_conserva_el_fisico` | ✔ |
| IMP-023-MS-014 · sin mutación directa del estado | — | — | — | `test_nadie_asigna_el_estado_del_saldo_a_mano` | ✔ |
| IMP-023-MS-015 · la transferencia aplica `CUARENTENA` | `FR-003-062` | #9 | `confirm_transfer_receipt` | `test_la_recepcion_de_transferencia_usa_el_destino_que_decide` | ✔ |
| IMP-023-MS-016 · disponible excluye lo no vendible | R-D0-10-3 | — | `get_available` (sin cambios) | `test_lo_no_vendible_no_se_ofrece_ni_se_reserva` | ✔ |
| IMP-023-MS-017 · la 030 no reserva lo no reservable | R-D0-03-5 | — | `lock_balance` por defecto | ídem | ✔ |
| IMP-023-MS-018/019 · un solo motor y un solo disponible | Gate B03-B05 | — | — | `test_no_hay_segundo_motor_de_saldos_ni_de_disponible` | ✔ |
| IMP-023-MS-020..023 · empresa, tenant y usuario AB | ARCH-MC-001 | — | `Scope.COMPANY` | `test_una_empresa_no_reclasifica_el_saldo_de_otra` | ✔ |
| IMP-023-MS-024..027 · almacén, ubicación nula, lote y serial | Spec 008 · 024 | — | clave del saldo | regresión de 008 y 011 | ✔ |
| IMP-023-MS-028 · estado inválido no es 500 | — | — | `assert_valid_state` → 422 | `test_un_estado_inventado_no_pasa_de_la_puerta` | ✔ |
| IMP-023-MS-029 · transición inválida determinista | R-D0-10-7 | — | `MERCHANDISE_TRANSITION_DENIED` | `test_una_entrada_en_estado_no_declarado_no_deja_rastro` | ✔ |
| IMP-023-MS-030..032 · atómica, sin crear ni destruir | R-D0-10-5 | reclasificación | `reclassify` | conservación + `no_deja_rastro` | ✔ |
| IMP-023-MS-033/034 · concurrencia y orden de bloqueo | POL-D0-002 §5 | reclasificación | orden determinista por estado | `test_dos_reclasificaciones_simultaneas…` | ✔ |
| IMP-023-MS-035 · la caja ×12 de la 019 | Spec 011 · 019 | — | `recompute_balances` | `test_reconstruir_no_reintroduce_la_caja_por_doce` | ✔ |
| IMP-023-MS-036/037 · 020 y 030 siguen convergidas | — | — | — | regresión completa | ✔ |
| IMP-023-MS-038 · paridad ORM / Alembic / PostgreSQL | P21 · N7 | — | `0046` + ORM | `test_la_aplicacion_puede_insertar_en_la_tabla_que_crea_la_migracion` | ✔ |
| IMP-023-MS-039 · sin deriva de OpenAPI | — | — | API sin cambios | — | ✔ |
| IMP-023-MS-040 · deuda P0 propia | — | — | — | — | **0** |
| IMP-023-MS-041 · desbloquea la 021 tras revalidar | R-D0-10-4 | #2, #3, #7, #8 | `reclassify` | `test_las_cuatro_transiciones_que_necesita_la_021_estan_declaradas` | ✔ |

**Cobertura: 100 %. Huérfanos: 0. OQ materiales: 0.**

---

# TRAZABILIDAD — SPEC 022 · PUT-AWAY (2026-09-04)

| Requisito | Regla `D0-14` | Código / migración | Prueba | Estado |
|---|---|---|---|---|
| IMP-022-R-001..003 · la reserva sigue siendo de almacén y la ubicación no la dimensiona | R-D0-14-1 | `warehouse_sellable_on_hand` · el ancla conserva `qty_reserved` | `test_el_reservado_sigue_en_el_ancla…` | ✔ |
| IMP-022-R-004..007 · el put-away no crea, libera, borra ni asigna reservas | R-D0-14-2/4 | `putaway` no menciona `qty_reserved` | `test_el_putaway_no_toca_el_reservado` · `…no_asigna_una_reserva…` | ✔ |
| IMP-022-R-008/009 · reservado y disponible del almacén invariantes | R-D0-14-2 | — | `test_ubicar_no_toca_el_reservado_ni_el_disponible_del_almacen` | ✔ |
| IMP-022-R-010 · `lock_balance` deja de ser la autoridad del físico | R-D0-14-3 | ancla parametrizada por ubicación | guardia estructural | ✔ |
| IMP-022-R-011 · `get_available` refleja el almacén | R-D0-14-3 | `warehouse_sellable_on_hand` | `test_el_disponible_suma_todas_las_ubicaciones` | ✔ |
| IMP-022-R-012 · lo no vendible sigue excluido | `D0-10` R-D0-10-3 | `SELLABLE_STATES` en la suma | `test_lo_no_vendible_no_entra_en_el_disponible…` | ✔ |
| IMP-022-R-013 · la representación cumple las cinco invariantes | R-D0-14-5 | opción A: ancla + `recompute` ya coincidente | suite de reconstrucción | ✔ |
| IMP-022-R-014/015 · un solo motor de reservas y de inventario | — | — | `test_no_hay_segunda_verdad_fisica` | ✔ |
| IMP-022-R-016..018 · capacidad informativa, sin bloqueo ni aviso calculado | R-D0-14-6/7 | `"enforced": false` | `test_la_capacidad_no_bloquea` · guardia | ✔ |
| IMP-022-R-019/020 · selección manual con candidatas del backend | R-D0-14-8/9 | `putaway_candidates` | `test_las_candidatas_son_las_activas…` | ✔ |
| IMP-022-R-021/022 · misma empresa y mismo almacén | R-D0-14-9 | `_require_candidate_location` | `test_no_se_ubica_en_el_almacen_de_al_lado` · `…otra_empresa…` | ✔ |
| IMP-022-R-023 · ubicación inactiva bloqueada | R-D0-14-9 | ídem | `test_una_ubicacion_inactiva_no_admite_mercancia` | ✔ |
| IMP-022-R-024/025 · sin slotting ni recomendación | R-D0-14-10 | — | `test_no_hay_slotting_automatico` | ✔ |
| IMP-022-R-026/027 · origen nulo legítimo, destino real | — | `putaway` | `test_el_movimiento_guarda_de_que_ubicacion_sale…` | ✔ |
| IMP-022-R-028..033 · almacén, producto, estado, lote, serial y base intactos | R-D0-14-13 | `source_state=estado, target_state=estado` | `test_el_putaway_no_cambia_el_estado_de_mercancia` | ✔ |
| IMP-022-R-034 · conservación física | — | — | suma 100 antes y después | ✔ |
| IMP-022-R-035 · procedencia de ubicación en el ledger | **R-D0-14-11** | migración `0048` | `test_la_direccion_historica_la_da_el_signo…` | ✔ |
| IMP-022-R-036/037 · reconstrucción fiel, deriva cero | **R-D0-14-12** | `recompute_balances` | `test_reconstruir_da_lo_mismo_que_el_camino_incremental` | ✔ |
| IMP-022-R-038..042 · atomicidad, concurrencia y orden de bloqueo | POL-D0-002 §5 | orden determinista por ubicación | dos carreras reales sobre PostgreSQL | ✔ |
| IMP-022-R-043..046 · empresa, tenant, usuario AB y cadenas mezcladas | ARCH-MC-001 | `CompanyContext` | multiempresa | ✔ |
| IMP-022-R-047 · el permiso existe en el catálogo | — | `inventario:create` | `test_el_permiso_del_putaway_existe_en_el_catalogo` | ✔ |
| IMP-022-R-048..051 · sin reabrir la 021, sin 025, sin 031, sin 032 | — | — | guardias estructurales | ✔ |
| IMP-022-R-052 · la caja ×12 llega ubicada como 24 | Spec 011 · 019 | — | `test_la_caja_por_doce_llega_ubicada_como_veinticuatro` | ✔ |
| IMP-022-R-053..060 · sin regresión de 008, 011, 019, 020, 021, 023, 030 y ARCH-MC | — | — | regresión completa | ✔ |
| IMP-022-R-061/062 · paridad ORM/Alembic/PostgreSQL y OpenAPI | P21 | `0048` · fixture regenerada | `test_la_aplicacion_puede_insertar…` | ✔ |
| IMP-022-R-064 · deuda P0 propia | — | — | — | **0** |

**Cobertura: 100 %. Huérfanos: 0. OQ materiales: 0.**
