# Tareas · PROC-07/PROC-08-COMMISSION-POLICY

Todas las tareas tienen `RETRY_MAX: 2`.

El tope global de DeepSeek es de 18 llamadas (OD-CP-01).

**Reclasificación del 2026-11-17, para no pasar del tope:**

- T08 se une a T07, en un solo fichero de pruebas PG por proceso.
- T11 se reparte entre T09 y T10: cada pantalla con su Vitest.
- La E2E de T12 incluye el ayudante común de política para las specs que crean comisiones.

| Tarea | Requisitos | Ejecutor | Modelo | Sensible | Egreso | Ficheros | Prueba | Hecho cuando |
|---|---|---|---|---|---|---|---|---|
| T01 · migración, modelos, permiso y registro documental | FR-CP-01..03, 06..10, 13 | CLAUDE (migración) | n-a | YES | n-a | `alembic/versions/0124_gov_commission_policy.py`, `models.py`, `setup/api.py`, `mfa_policy.py`, `documents/resources.py`, catálogo de auditoría | upgrade, downgrade y upgrade en PG; `test_n10_convergence` sin divergencias nuevas | Una cabeza; ORM igual a la base |
| T02 · autoridad `service_comision_regla.py` | FR-CP-04, 05, 07 | DEEPSEEK | v4-pro | NO | SAFE | `service_comision_regla.py` (nuevo) | T07 | Funciones puras de umbral, quórum y decisión; ruff y mypy limpios |
| T03 · servicio, esquemas y API de políticas | FR-CP-01..03, 10, 11, 13 | DEEPSEEK | v4-pro | NO | SAFE | `service_comision_politicas.py`, `schemas_comision_politicas.py` y `api_comision_politicas.py` (nuevos); registro del router | T07 | CRUD, activación, cierre y versiones con historia |
| T04 · PROC-02 consume la autoridad | FR-CP-05..07 | DEEPSEEK | v4-pro | NO | SAFE | `service_comisiones.py`, `schemas_comisiones.py`, `api_comisiones.py` | T08 | `crear` exige política; `activar` congela la regla; presidencia; inhibición con expediente |
| T05 · PROC-07 consume la autoridad | FR-CP-05, 07, 08 | DEEPSEEK | v4-pro | NO | SAFE | `service_evaluacion.py`, `schemas_evaluacion.py` | T08 | Quórum de la regla, inhibidos excluidos, modo sin comisión |
| T06 · PROC-08 consume la autoridad | FR-CP-05, 07, 09 | DEEPSEEK | v4-pro | NO | SAFE | `service_decision.py`, `schemas_decision.py` | T08 | Decisión de la regla, inhibidos excluidos, modo sin comisión |
| T07 · pruebas PG de políticas y autoridad | FR-CP-01..05, 10, 13 | DEEPSEEK | v4-pro | NO | SAFE | `tests/test_gov_comision_politicas.py` | La prueba misma | Pasan y matan M1, M4, M5 y M8 |
| T08 · pruebas PG de integración PROC-02, PROC-07 y PROC-08 | FR-CP-06..09 | DEEPSEEK | v4-pro | NO | SAFE | `tests/test_gov_comision_politica_procesos.py` | La prueba misma | Pasan y matan M2, M3, M6 y M7 |
| T09 · pantallas de políticas | FR-CP-12 | DEEPSEEK | v4-pro | NO | SAFE | `PoliticasComisionPage.tsx`, `PoliticaComisionFormPage.tsx`, `PoliticaComisionPage.tsx`, `api.ts`, rutas, menú y `pantallas.ts` | tsc, lint y T11 | Operable desde el menú |
| T10 · comisión y expediente en pantalla | FR-CP-12 | DEEPSEEK | v4-pro | NO | SAFE | `ComisionFormPage.tsx`, `ComisionPage.tsx`, `ComisionPaneles.tsx`, `ExpedienteEvaluacion.tsx`, `ExpedienteDecision.tsx` | tsc, lint y Vitest | Política, regla, faltantes y modo sin comisión visibles |
| T11 · Vitest | FR-CP-12 | DEEPSEEK | v4-pro | NO | SAFE | `PoliticasComision*.test.tsx` y pruebas hermanas | Vitest | Cubre los casos del §21 |
| T12 · E2E | Todos | DEEPSEEK | v4-pro | NO | SAFE | `e2e/gobierno-comision-politica.spec.ts` | `qa/e2e-run.py --con-analizador` | Recorrido del §22, anchos 1280, 390 y 320, Axe 0 serious y 0 critical |

## Mutaciones

| Mutación | Qué rompe |
|---|---|
| M1 | Se salta el filtro de tenant o empresa en las políticas |
| M2 | Se salta la cardinalidad (máximo de principales) |
| M3 | Se salta el requisito de competencia o cargo |
| M4 | El umbral de quórum devuelve 1 |
| M5 | Se admite una política vencida o cerrada al crear la comisión |
| M6 | Un miembro inhibido cuenta en el quórum |
| M7 | Se salta el documento obligatorio de CONSTITUCION |
| M8 | Se permite editar una política VIGENTE |

## Trazabilidad

| Requisito | Implementación | Pruebas |
|---|---|---|
| FR-CP-01 · Política | `models.GovernmentCommissionPolicy*`, `0124`, `service_comision_politicas` | `test_politica_ciclo_y_aislamiento`, `test_piso_lcp_no_se_rebaja`, `test_validacion_responde_422`; Vitest del formulario, la lista y la ficha |
| FR-CP-02 · Versiones | `nueva_version`, `activar` (sustituye la anterior) e índice único de la vigente | `test_nueva_version_sustituye`, `test_historia_inmutable_pg` |
| FR-CP-03 · Requisitos | `cumple_requisito`, con el tipo AREA, CARGO, UNIDAD, COMPETENCIA o FUNCIONARIO | `test_requisito_de_competencia`; Vitest (e) |
| FR-CP-04 · Quórum y decisión | `umbral`, `evaluar_quorum`, `evaluar_decision`, `cuenta_voto` | `test_umbral_quorum_decision`, `test_quorum_por_unanimidad`, `test_mayoria_calificada_en_la_recomendacion`, `test_suplente_con_su_principal_no_cuenta_voto` |
| FR-CP-05 · Autoridad única | `service_comision_regla`, que consumen PROC-02, PROC-07 y PROC-08; el frontend sin cálculo propio | La auditoría de hardcode (0 `Math.floor`); las pruebas de PROC-07 y PROC-08 |
| FR-CP-06 · Comisión desde la política | `service_comisiones.crear` y `activar` (regla congelada), con presidencia | `test_comision_exige_politica_vigente`, `test_maximo_de_principales`, `test_documento_de_constitucion`, `test_regla_congelada`, `test_presidencia_unica`; COM-E2E-01; CP-E2E-01 |
| FR-CP-07 · Inhibición por expediente | `file_id` en la inhibición, `inhibidos()` y su exclusión en PROC-07 y PROC-08 | `test_inhibicion_con_expediente_ajeno`, `test_inhibido_no_asiste_y_actua_su_suplente`, `test_firmante_inhibido_se_rechaza` |
| FR-CP-08 · PROC-07 | `abrir_ofertas`, en modo COMISION o UNIDAD_CONTRATANTE; aportes y resultados por responsable | `test_ciclo_sin_comision_por_responsables`, `test_apertura_sin_comision_y_sin_motivo_se_rechaza`, `test_responsable_no_evalua_con_comision`; regresión de PROC-07 |
| FR-CP-09 · PROC-08 | `emitir_recomendacion`, con regla y modo sin comisión | `test_ciclo_sin_comision_por_responsables`, `test_mayoria_calificada_en_la_recomendacion`; regresión de PROC-08 |
| FR-CP-10 · Permisos | `gobierno_comisiones:configure`, que no pide MFA; activar y cerrar sí lo piden | `test_permisos_de_configuracion`, `test_mfa_policy` (81), `authority-surfaces` |
| FR-CP-11 · Auditoría | 6 eventos nuevos en el catálogo | `test_audit_catalog_guard` |
| FR-CP-12 · Pantallas | Las páginas de políticas, la comisión y el expediente | Vitest (lista 5, ficha 7, formulario 9, comisión); CP-E2E-01 con Axe en 1280, 390 y 320 |
| FR-CP-13 · Aislamiento | `company_id` en todas las consultas | `test_politica_ciclo_y_aislamiento`; aislamiento en CP-E2E-01; mutación M1 |

**Trazabilidad:** 13 de 13 requisitos con implementación y prueba (100 %).
