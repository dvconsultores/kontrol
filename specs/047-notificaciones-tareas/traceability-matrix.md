# Matriz de trazabilidad — SPEC 047

> Final de implementación (2026-09-14). Rutas de backend relativas a
> `resources/backend`; `N` = `tests/test_spec047_notifications.py`,
> `T` = `…_tasks.py`, `S` = `…_scheduler.py`, `M` = `…_messages.py`,
> `A` = `…_architecture.py`, `E` = `…_schema.py`, `E2E` = `e2e/notifications.spec.ts`.
> Evidencia de ejecución: `convergence.md` §3-§7.

| FR | Código | Prueba dirigida | Hostil / carrera | Mutación | E2E |
|---|---|---|---|---|---|
| 001 | `notifications/service.py · crear_notificacion`; `sources.py · aplicar_hecho_de_aprobacion` | N `test_flujo_a_una_aprobacion_real_notifica_una_vez_a_cada_elegible` | — | — | campana y lectura |
| 002 | `service._usuarios_del_tenant`; elegibles fijados por la 045 | N `test_flujo_a…` | N `test_un_usuario_de_otro_tenant_nunca_llega_a_destinatario` | M047-02 | — |
| 003 | `service.marcar_leida`, `archivar` | N `test_flujo_g…`, `test_leer_dos_veces…`, `test_archivar_no_borra…` | — | M047-04 | lectura |
| 004 | `severity`, `mandatory`; sin caducidad | N `test_una_notificacion_critica_no_caduca_sola` | — | — | — |
| 005 | `service.crear_tarea`; efecto `TASK` | T `test_la_tarea_nace_con_los_elegibles_que_fijo_la_045` | — | — | tarea |
| 006 | `service.reasignar_tarea`; `TaskCandidate` | T `test_flujo_h…`, `test_reasignar_exige_version…` | T `test_dos_reasignaciones_con_la_misma_version…` | M047-09 | reasignación |
| 007 | `iniciar_tarea`, `completar_tarea`, `cancelar_tarea`, `resolver_por_origen` | T `test_flujo_i…`, `test_la_tarea_y_la_alerta_se_cierran…`, `test_sin_auto_close…` | T `test_dos_completados_forzados…`, `test_completar_dos_veces…` | M047-05 | completar no aprueba |
| 008 | `asegurar_zona`; `overdue` | T `test_la_tarea_vencida_se_cuenta_con_el_reloj_con_zona` | T `test_un_vencimiento_sin_zona_se_rechaza` | M047-10 | — |
| 009 | `TaskPriority`; `crear_prioridad` | T `test_las_prioridades_son_de_la_empresa_y_se_validan` | — | — | — |
| 010 | `crear_alerta`, `listar_alertas` | N `test_flujo_e_la_alerta_se_ve_con_permiso_y_no_crea_tarea` | 403 sin `alertas:view` | — | — |
| 011 | `_enlace`; frontend `destinoDeEnlace` | N `test_flujo_a…` (enlace) · vitest `destinoDeEnlace` | — | — | enlace |
| 012 | filtros por `ctx.company_id` | N `test_flujo_l…` · T `test_la_tarea_de_a_no_se_ve…` | N `test_un_id_ajeno_responde_igual…` | M047-03 | aislamiento de empresa |
| 013 | tenant en destinatarios, candidatos y escaladas | N `test_un_usuario_de_otro_tenant…` · T `test_un_candidato_de_otro_tenant…` | S `test_la_escalada_llega_una_vez…` | M047-02 | — |
| 014 | `catalogo.tipos_prohibidos` | N `test_flujo_j…` | usuario sin `aprobaciones:view` | M047-07 | — |
| 015 | `dedupe_key` + `notification_event_receipts` | N `test_el_mismo_hecho_no_duplica…`, `test_diez_reintentos…` · T `test_repetir_el_hecho…` | N `test_dos_publicaciones_forzadas…` | M047-01, M047-08b, M047-12 | reintento del planificador |
| 016 | `source_event_id`, `correlation_id`, `run_correlation_id` | S `test_el_efecto_guarda_el_hecho_de_origen_y_el_tick_que_lo_produjo` | — | — | — |
| 017 | `_auditar` en cada transición | N `test_el_planificador_audita_como_sistema…` · T `test_flujo_h…` (auditoría) | — | M047-09 | — |
| 018 | `guardar_preferencia`, `_filtrar_por_preferencia` | N `test_una_preferencia_opcional_apagada…`, `test_una_notificacion_obligatoria_no_se_desactiva` | — | — | — |
| 019 | canal `INTERNAL`; `CHANNEL_UNAVAILABLE` | N `test_sin_proveedor_el_canal_externo_no_esta_disponible` | — | — | — |
| 020 | `delivery.PROVEEDORES` vacío | A `test_la_047_no_contiene_proveedores_externos` | — | — | — |
| 021 | `delivery.entregar` reintento | N `test_una_entrega_enviada_no_se_reenvia…`, `test_flujo_k…` | — | — | — |
| 022 | estado de entrega separado | N `test_flujo_k_el_fallo_del_canal_externo_no_toca_la_notificacion_interna` | — | M047-06 | — |
| 023 | un único planificador (ADR-D0-015) | A `test_el_registro_declara_duena…`, `test_el_planificador_cita_su_adr_aprobado` | — | — | — |
| 024 | `handlers.recordatorios`; `ventana_de_recordatorio` | S `test_flujo_a_un_recordatorio…`, `test_antes_de_su_ventana…` | — | M047-14 | — |
| 025 | `handlers.escaladas`; `usuarios_con_rol` | S `test_la_escalada_llega_una_vez_a_quien_tiene_el_rol_en_esa_empresa` | — | — | — |
| 026 | `sources` solo lee lo que fijó la 045 | T `test_flujo_i…` | — | M047-05 | completar no aprueba |
| 027 | `LOTE_POR_TICK` | S `test_un_hecho_masivo_se_consume_por_lotes_sin_duplicar` | — | — | — |
| 028 | `_pagina` (`page`, `page_size` ≤ 100) | N `test_flujo_m…` · T `test_mas_de_cien_tareas…` | 422 con `page_size=101` | — | página 3 |
| 029 | filtros de `listar_*` | N `test_flujo_m…`, `test_archivar…` · T `test_la_tarea_vencida…`, `test_las_prioridades…` | T `scope=all` sin permiso → 403 | — | filtro de estado |
| 030 | `service.contadores`; `NotificationBell` | N `test_flujo_l…` · vitest `NotificationBell` | contador de otra empresa | M047-11 | campana |
| 031 | `EnlaceOrigen` | N `test_flujo_j…` (permitido) | — | — | enlace al origen |
| 032 | invisibilidad sin permiso; 404 idéntico | N `test_flujo_j…`, `test_un_id_ajeno…` | IDOR | M047-07 | — |
| 033 | catálogo por clave estable | M `test_toda_clave_citada…`, `test_cada_efecto_consumible…` | — | — | — |
| 034 | `messages.IDIOMAS`; `src/i18n` | M `test_el_ingles_esta_diferido…` · vitest `i18n.test.ts` | — | — | — |
| 035 | sin rutas de borrado | A `test_la_api_de_la_047_no_borra_nada` · N `test_archivar_no_borra…` | — | — | — |
| 036 | `GET /notifications/counts` | N `test_flujo_k_la_049_puede_leer_los_cuatro_contadores` | — | M047-11 | campana |
| 037 | `scheduler/__main__.py` | S `test_la_orden_devuelve_su_estado_y_su_codigo_de_salida` | — | — | — |
| 038 | `scripts/scheduler/*`, `kontrol.py · cmd_scheduler_tick` | A `test_el_temporizador_solo_invoca_la_orden_canonica` | — | M047-16 | — |
| 039 | sin cola, hilo ni bucle | A `test_ninguna_libreria_de_cola…`, `test_el_planificador_no_duerme…` | — | — | — |
| 040 | `scheduler/service._tomar_bloqueo` | S `test_flujo_b…` | S `test_dos_ticks_reales_a_la_vez…` | M047-13 | — |
| 041 | `SchedulerRun`, `SchedulerHandlerRun` | S `test_el_tick_deja_registro…` | — | — | — |
| 042 | `scheduler/registry.py` | A `test_el_registro_declara_duena…`, `test_la_orden_no_acepta_argumentos…` | — | — | — |
| 043 | claves lógicas de efecto | S `test_flujo_a_un_recordatorio…` | — | M047-14 | reintento |
| 044 | política `LATEST_WINDOW` | S `test_flujo_c…` | — | M047-15 | — |
| 045 | `Actor` `SYSTEM`; `source="SCHEDULER"` | S `test_los_efectos_del_planificador_son_del_sistema…` | — | — | — |
| 046 | efecto con la empresa de su tarea | S `test_cada_efecto_se_crea_en_la_empresa_de_su_tarea` | — | M047-17 | — |
| 047 | códigos 0 / 2 / 1 | S `test_la_orden_devuelve…`, `test_un_manejador_que_falla…` | — | — | — |
| 048 | `install-scheduler.sh` con instancia e intervalo obligatorios | A `test_el_temporizador_solo_invoca…` | — | — | — |
| 049 | manejador 045 deshabilitado que llama a `mark_expired` | S `test_flujo_d…` | — | — | — |
| 050 | `message_key` + `message_params`; sin columna de texto | A `test_ninguna_tabla_de_mensajes…` · N `test_flujo_f…` | — | M047-19 | — |
| 051 | `messages.renderizar`; `src/i18n` | M `test_clave_conocida…` · N `test_flujo_f…` | — | — | — |
| 052 | contrato de parámetros | M 12 casos | — | M047-18 | — |
| 053 | mensajes de error y UI por catálogo | A `test_ningun_error_de_la_047…` · vitest `spec047-strings.test.ts` | — | — | — |
| 054 | consumo de `approval_events` con recibo | N `test_flujo_a…`, `test_el_mismo_hecho…` | — | M047-01 | todos los escenarios |

Esquema (NFR-047-07): E `test_el_orm_y_la_base_migrada_declaran_lo_mismo`, `test_la_unicidad_y_los_checks…`,
`test_zz_la_migracion_se_deshace_y_se_rehace`, `test_la_migracion_concede_los_permisos…`.
Volumen y N+1 (NFR-047-02): N `test_la_lista_no_hace_una_consulta_por_fila`.

| | |
|---|---|
| Requisitos con código y prueba | **54 / 54** |
| Mutaciones válidas que caen | **19 / 19** (M047-08 original inválida, sustituida por M047-08b) |
| Tareas sin requisito | 0 de 58 |
