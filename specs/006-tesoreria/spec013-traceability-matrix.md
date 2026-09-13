# SPEC 013 · TRAZABILIDAD DE IMPLEMENTACIÓN

> Dueño: `specs/006-tesoreria` (`spec-equivalence-map.md` línea 20). La carpeta
> `013-gap-analysis-roadmap-maestro` es otra numeración y no se toca.

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| FR-013-001 · maestro de monedas | doc. maestro | `Currency` con `code`, `name`, `symbol`, `decimal_places` | `test_la_observacion_guarda_su_par_explicito` | ✔ |
| FR-013-002 · desactivar no borra historia | doctrina | `status`, único **parcial** sobre las activas | `test_una_fuente_desactivada_no_produce_tasas_pero_conserva_historia` | ✔ |
| FR-013-003 · maestro de fuentes | §14 del prompt | `ExchangeRateSource` | `test_la_resolucion_devuelve_la_procedencia_entera` | ✔ |
| FR-013-004 · identidad de la fuente | ídem | `code`, `name`, `source_type`, `authority_reference`, `provider_code`, `priority`, vigencia | ídem | ✔ |
| FR-013-005 · tipo de tasa | ídem | `rate_type`, texto del maestro | `test_la_api_resuelve_y_dice_lo_que_significa` | ✔ |
| FR-013-006 · observación con par explícito | §11 · §18 | `base_currency_id` / `quote_currency_id` | `test_la_observacion_guarda_su_par_explicito` · **M013-01** | ✔ |
| FR-013-007 · tiempos distinguidos | §19 | `effective_at`, `published_at`, `observed_at` | `test_una_tasa_de_manana_no_valora_una_operacion_de_ayer` | ✔ |
| FR-013-008 · el histórico no se reescribe | §20 | `correct_rate` crea versión | `test_corregir_una_tasa_sucede_a_la_anterior` · **M013-04** | ✔ |
| FR-013-009 · corrección por sucesión | ídem | `supersedes_id`, `version` | ídem | ✔ |
| FR-013-010 · alta manual | §29 | `register_rate` | `test_la_api_resuelve_y_dice_lo_que_significa` | ✔ |
| FR-013-011 · la manual deja rastro | §29 | `entered_by`, `reason`, `source_reference` | `test_corregir_exige_motivo` | ✔ |
| FR-013-012 · importación CSV | §31 | `import_rates` | `test_importar_crea_las_tasas_y_reimportar_no_duplica` | ✔ |
| FR-013-013 · contrato de proveedor | §35 | `ingest_provider_observations` | `test_el_proveedor_no_duplica_la_misma_observacion` | ✔ |
| FR-013-014 · el núcleo no depende de nadie externo | §8 · §37 | sin cliente HTTP en el módulo | revisión del módulo | ✔ |
| FR-013-015 · contrato de resolución | §21 | `resolve_rate` → `RateResolution` | `test_la_resolucion_devuelve_la_procedencia_entera` | ✔ |
| FR-013-016 · falta de tasa **no** es tasa uno | §9 · §23 | `MISSING_RATE` | `test_sin_observacion_el_par_no_se_resuelve` · **M013-01** · e2e P0 | ✔ |
| FR-013-017 · identidad de la misma moneda | §10 · §22 | `SAME_CURRENCY_IDENTITY`, sin fila | `test_la_misma_moneda_es_identidad_sin_fila_de_mercado` · e2e | ✔ |
| FR-013-018 · selección de fuente configurable | §38 | filtro por fuente activa y código | `test_una_fuente_desactivada_no_produce_tasas_pero_conserva_historia` · **M013-12** | ✔ |
| FR-013-019 · prioridad de fuente | §38 · §86 | `priority` del maestro | `test_entre_dos_fuentes_manda_la_prioridad_no_el_orden_de_la_tabla` | ✔ |
| FR-013-020 · fuente desactivada fuera de la resolución | §41 | filtro por `status` | ídem · **M013-12** | ✔ |
| FR-013-021 · caducidad por política | §26 | `max_age_days`, nulo = sin tope | `test_la_tasa_caduca_cuando_la_politica_lo_dice` | ✔ |
| FR-013-022 · falta de tasa como error de dominio | §23 | `ConflictError` con detalle del par | `test_la_api_no_inventa_una_tasa_que_falta` | ✔ |
| FR-013-023 · una tasa futura no valora el pasado | §73 | `effective_at <= momento` | `test_una_tasa_de_manana_no_valora_una_operacion_de_ayer` · **M013-03** | ✔ |
| FR-013-023b · preguntar por un día es el día entero | defecto hallado en e2e | `_momento_consulta` | `test_la_tasa_de_hoy_sirve_para_una_operacion_de_hoy` | ✔ |
| FR-013-024 · estados de la observación | §24 | `ACTIVE` · `PENDING_APPROVAL` · `SUPERSEDED` · `IDENTITY` | `test_con_politica_de_aprobacion_la_tasa_nace_pendiente_y_no_resuelve` | ✔ |
| FR-013-025 · alcance por empresa | `ARCH-MC-001` | `company_id` en todo | `test_la_tasa_de_una_empresa_no_resuelve_en_otra` · **M013-05** | ✔ |
| FR-013-026 · sin cruce entre empresas | ídem | guardia en maestro **y** en observación | `test_una_moneda_de_otra_empresa_no_sirve_para_registrar_aqui` | ✔ |
| FR-013-027 · auditable | §46 | `entered_by`, `approved_by`, `reason`, marcas de tiempo | `test_corregir_una_tasa_sucede_a_la_anterior` | ✔ |
| FR-013-028 · reproducibilidad histórica | §47 | `exchange_rate_id` en la instantánea de la 038 | `test_corregir_la_tasa_no_cambia_la_operacion_que_uso_la_anterior` · e2e | ✔ |
| FR-013-029 · metadatos suficientes para la 038 | §21 | `RateResolution` completa | `test_la_tesoreria_obtiene_la_tasa_real_y_congela_su_procedencia` | ✔ |
| FR-013-030 · importar es idempotente | §33 | `content_hash` único | `test_importar_crea_las_tasas_y_reimportar_no_duplica` · **M013-08** | ✔ |
| FR-013-031 · el proveedor no duplica | §42 | `provider_observation_id` | `test_el_proveedor_no_duplica_la_misma_observacion` | ✔ |
| FR-013-032 · tasa mayor que cero | §62 | validación + `CHECK` en la tabla | `test_una_tasa_no_positiva_se_rechaza` · **M013-06** · **M013-07** | ✔ |
| FR-013-033 · par no ambiguo | §11 | `base != quote`, y el contrato lo escribe | `test_una_moneda_no_cotiza_contra_si_misma` | ✔ |
| FR-013-034 · no se invierte sin política | §24 | `INVERSION_NOT_ALLOWED`, y `derived` cuando se permite | `test_sin_politica_no_se_invierte_una_tasa` · **M013-10** · e2e P0 | ✔ |
| FR-013-035 · no se triangula sin política | §25 | `allow_triangulation` + marca `TRIANGULATION` | `test_sin_politica_no_se_triangula` · **M013-11** | ✔ |
| FR-013-036 · institución financiera | §36 | `Bank` ya existe y es de la 038: **no se duplica** | revisión del diff | ✔ |
| FR-013-037 · frontera con métodos de pago | §37 | `PaymentMethod` sigue en la 038 | ídem | ✔ |
| FR-013-038 · contrato = OpenAPI | §51 | fixture regenerada, 522 rutas | `audit-completeness.test.ts` | ✔ |
| FR-013-039 · administración completa | §52-58 | pantallas de tasas y de fuentes | e2e de interfaz | ✔ |
| FR-013-040 · perfil venezolano configurable | §7 · §40 | moneda funcional de la empresa; BCV es una fuente del maestro | `test_la_moneda_funcional_sale_de_la_empresa_no_del_codigo` | ✔ |
| INV-013-A · sin `float` en la tasa | §12 | `Decimal` en borde, servicio y modelo | `test_la_tasa_no_pasa_por_coma_flotante` · **M013-02b** | ✔ |
| INV-013-B · escala del maestro, no cableada | §13 | `rate_scale` de la política | `test_la_tasa_conserva_todos_sus_decimales` | ✔ |
| INV-013-C · una sola moneda activa por código | defecto §2.1 | único parcial `(company_id, code)` | `test_una_moneda_de_otra_empresa_no_sirve_para_registrar_aqui` | ✔ |
| INV-013-D · una sola observación por coordenadas | defecto §2.2 | único parcial + comprobación | `test_dos_observaciones_en_las_mismas_coordenadas_no_conviven` | ✔ |
| INV-013-E · el arrastre coge la vigente | §27 | orden explícito por momento y versión | `test_el_arrastre_toma_la_ultima_anterior_no_la_primera` · **M013-09** | ✔ |
| INV-013-F · concurrencia real | §87 | índice único en PostgreSQL | `test_dos_registros_simultaneos_no_crean_dos_observaciones` | ✔ |
| INV-013-G · el universo se pagina entero | §60 · §61 | `page`/`page_size`, tope 100 | `test_el_universo_de_tasas_se_recorre_entero_por_paginas` · `test_la_api_pagina_el_historico_con_el_contrato_real` | ✔ |
| INV-013-H · quien registra no aprueba | §30 · §91 | `SELF_APPROVAL_FORBIDDEN` | `test_quien_registra_una_tasa_no_la_aprueba` | ✔ |
| INV-013-I · ninguna fila inválida en silencio | §34 | informe por fila, campo y motivo | `test_ninguna_fila_invalida_se_descarta_en_silencio` | ✔ |

## Reanudación 2026-09-13 · atomicidad de altas y deriva ORM ↔ migración

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| INV-013-J · perder una carrera de registro es un error de dominio, no un 500 | contrato de errores · `ARCH` | `begin_nested` + `IntegrityError` → `DUPLICATE_OBSERVATION` | `test_dos_registros_simultaneos_no_crean_dos_observaciones` · **M013-13** | ✔ |
| INV-013-K · dos altas del mismo código de fuente | ídem | → `SOURCE_CODE_TAKEN` | `test_dos_altas_simultaneas_de_la_misma_fuente_no_dan_un_500` · **M013-14** | ✔ |
| INV-013-L · el camino corto devuelve la fuente que creó el otro | compatibilidad | relectura de la ganadora | `test_la_fuente_nombrada_por_texto_es_la_misma_aunque_lleguen_dos_a_la_vez` · **M013-15** | ✔ |
| INV-013-M · la moneda funcional se asegura una sola vez | FR-013-040 | relectura tras colisión | `test_la_moneda_funcional_se_asegura_una_sola_vez_aunque_lleguen_dos` · **M013-16** | ✔ |
| INV-013-N · subir dos veces el mismo fichero a la vez | FR-013-030 | → `IMPORT_DUPLICATE` | `test_subir_dos_veces_a_la_vez_el_mismo_fichero_no_da_un_500` · **M013-17** | ✔ |
| INV-013-O · dos versiones simultáneas de la misma política | FR-013-021 | → `RATE_POLICY_VERSION_CONFLICT` | `test_dos_versiones_simultaneas_de_la_misma_politica_no_dan_un_500` · **M013-18** | ✔ |
| INV-013-P · no se corrige una tasa ya sustituida | FR-013-009 | `RATE_ALREADY_SUPERSEDED` antes de insertar | `test_corregir_dos_veces_la_misma_tasa_original_no_da_un_500` · **M013-19** | ✔ |
| INV-013-Q · dos correcciones simultáneas | FR-013-009 | → `RATE_ALREADY_SUPERSEDED` | `test_dos_correcciones_simultaneas_de_la_misma_tasa_no_dan_un_500` · **M013-20** | ✔ |
| INV-013-R · la unicidad está en los modelos, no solo en la migración | §63 del prompt | `__table_args__` con los nombres de la `0056` | `test_los_modelos_declaran_la_misma_unicidad_que_la_migracion` · **M013-21** | ✔ |
| INV-013-S · la base de pruebas tiene esa unicidad de verdad | ídem | `create_all` la crea | `test_la_base_de_pruebas_tiene_de_verdad_la_unicidad_de_la_013` · **M013-21b** | ✔ |

Las pruebas de carrera usan `tests/concurrency.py`: la segunda transacción queda
**bloqueada en el índice** antes de que confirme la primera, y si nunca llega a
bloquearse la prueba falla. No hay carrera dejada al azar.

## Delta dirigido a la Spec 023

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-023-0xx · el alta del tipo de movimiento base no da 500 en carrera | contrato de errores | `begin_nested` + relectura en `_get_movement_type_by_code` | `test_dos_operaciones_simultaneas_no_crean_dos_tipos_ni_dan_un_500` · **M023-D1** | ✔ |
| IMP-023-0xy · un código que no es base sigue sin inventarse | doctrina | `MOVEMENT_TYPE_NOT_FOUND` | `test_un_tipo_que_no_es_base_sigue_sin_inventarse` | ✔ |

## Delta dirigido a la Spec 038

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-038-035 · la instantánea dice si la tasa fue derivada | §24 del prompt | `derivation`, `derived_from` | `test_la_tesoreria_marca_la_tasa_derivada_en_su_instantanea` | ✔ |
| IMP-038-036 · el camino corto escribe el par | compatibilidad | `set_exchange_rate` → `register_rate` | `test_el_camino_antiguo_sigue_funcionando_y_ya_escribe_el_par` | ✔ |

## Delta dirigido a la Spec 007

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-007-0xx · la empresa publica su moneda funcional | FR-013-040 | `functional_currency` en el listado | e2e de la 013 (la usa para armar cada par) | ✔ |

Sin huérfanos: 59 requisitos de la 013 y 5 de delta, todos con autoridad,
implementación y prueba existente y verificada.
