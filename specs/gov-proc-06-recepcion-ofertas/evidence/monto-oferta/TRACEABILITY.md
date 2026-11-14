# OMA · Trazabilidad

| Requisito | Implementación | Prueba |
|---|---|---|
| OMA-01 autoridad | `declarar_monto` (valores tal cual y soporte obligatorio) | `test_declarar_y_corregir`; E2E |
| OMA-02 exactitud | `MontoEntrada` (`texto_decimal`, NUMERIC(18,2)); `suma_coincide` y `diferencia` | `test_rechazos_no_escriben` (número JSON, 0, −1); `test_declarar_y_corregir` (diferencia «10.00») |
| OMA-03 moneda | `MONEDAS_LIMITE`; CHECK `moneda` | `test_rechazos_no_escriben` (COP) |
| OMA-04 soporte | `_soportes` (documento de la oferta no sellado o acta) | `test_rechazos_no_escriben` (soporte ajeno); `test_declarar_y_corregir` (ambos tipos) |
| OMA-05 confidencialidad | `_bloqueo` y `declarar_monto` (409 SEALED); sin importes en la cronología ni en la auditoría | `test_sellada_sin_apertura`; `test_cronologia_y_auditoria_sin_importes`; E2E (SELLADO por API) |
| OMA-06 frontera y no aplica | 409 CLOSED; 422 NOT_APPLICABLE | `test_cerrado_tras_evaluacion`; `test_calificacion_no_aplica`; E2E (bloqueo tras concluir) |
| OMA-07 corrección versionada | `reemplaza_id`, motivo, `version_anterior`; CHECK `correccion`; disparadores | `test_declarar_y_corregir`; `test_inmutable_en_postgresql`; Vitest e) y f); E2E |
| OMA-08 legado | Sin backfill; NO_DECLARADO | `test_sin_sello_desde_recepcion`; `test_rechazos_no_escriben` (estado inicial) |
| OMA-09 PROC-08 | `service_decision` (monto por oferta) y columna en la pantalla | `test_consumidores_rep03_y_proc08`; E2E |
| OMA-10 PROC-10 | `_criterio_moneda` y `_criterio_monto` (3 bandas) | `test_proc10_bandas_de_la_oferta`; pruebas existentes de PROC-10 |
| OMA-11 REP-03 | `service_reporte_contrataciones` (por moneda y CSV); sección de la pantalla | `test_consumidores_rep03_y_proc08`; `test_rc01` ajustada; Vitest de REP-03; E2E de REP-03 |
| OMA-12 PROC-09 | Documentación: `DOMAIN_DEPENDENCY_ON_AMOUNT` cerrada | `DECISIONES.md` de PROC-09 |
| OMA-13 aislamiento | Filtros por `company_id` | `test_aislamiento`; mutación |
| OMA-14 concurrencia | If-Match y bloqueo de la fila del expediente; UNIQUE | `test_carrera_de_declaraciones` |
| OMA-15 pantalla, E2E y UAT | `OfertaMonto.tsx` y la ficha | Vitest 6/6; E2E con Axe a 1280, 390 y 320; humo de la UAT |

Requisitos huérfanos: 0. Tareas huérfanas: 0. Trazabilidad: 100 %.
