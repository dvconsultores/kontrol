# CNT-07 · Trazabilidad (28/28)

- **Pruebas PG:** `tests/test_gov_cnt07_terminacion.py` (19).
- **Vitest:** `TerminacionContratoPage.test.tsx` (5) y la sección del expediente en `ExpedienteContractualPage.test.tsx`.
- **E2E:** `e2e/gobierno-contratos-terminacion.spec.ts`.

| Contrato | Código | Prueba |
|---|---|---|
| C07-01 Solo FORMALIZADO; 404 a otra empresa | `_formalizado`, `_contrato`, `vista` | `test_catalogo_situacion_y_contrato_no_formalizado`; E2E 16(c) |
| C07-02 Figura respaldada (LCP 145) | `FIGURAS_TERMINACION_CONTRATO`, `CATALOGO`, `_aplicar` | `test_catalogo_situacion_y_contrato_no_formalizado`; `test_borrador_if_match_y_validaciones` (CADUCIDAD → 422) |
| C07-03 Causal tasada por figura | `CATALOGO[...]["causales"]`; LCP_155_9 solo OBRAS; CLAUSULA con referencia | `test_causales_por_figura`; M2 muerta |
| C07-04 Motivación (LOPA 9) | `MOTIVACION` y acto con hechos y fundamentos | `test_borrador_if_match_y_validaciones` |
| C07-05 Acto DOC-02 particular y eficaz | `_acto_valido`, requisito `ACTO_EFICAZ` | `test_borrador_if_match_y_validaciones` (EMITIDO y GENERAL → 422); M3 muerta |
| C07-06 Autoridad APROBAR × CONTRATACIONES | `_autoridad`, `exigir_autoridad_funcional`, `GOV_CONTRACT_TERMINATION_BLOCKED` | `test_autoridad_y_notificaciones` |
| C07-07 Eficacia separada del registro | `fecha_acto`, `fecha_eficacia` (DOC-04), `formalizado_en` | `test_eficacia_juridica_no_es_fecha_de_registro`; M4 muerta |
| C07-08 Notificaciones DOC-04 | `_notificaciones`, `NOTIFICACION_CONTRATISTA`, `NOTIFICACION_GARANTES` | `test_autoridad_y_notificaciones`; `test_garantes_y_garantia_no_se_ejecuta`; E2E 2 y 8 |
| C07-09 Una extinción por contrato | Índices únicos parciales, FOR UPDATE, `If-Match` | `test_rescision_no_imputable_formalizada` (409); M1 muerta; E2E 16(a) |
| C07-10 Historia inmutable | Trigger `kontrol_gov_contract_termination_guard` | `test_inmutable` |
| C07-11 Consecuencias sin efectos | `_consecuencias` (FINANCIAL_EXECUTION_BASE) | `test_rescision_no_imputable_formalizada`; `test_compromiso_presupuestario_no_se_anula`; M7 muerta; E2E 9 |
| C07-12 CNT-06 no absorbido | `indemnizacion.estado = CONSECUENCIA_PENDIENTE_CNT06` | `test_rescision_no_imputable_formalizada` |
| C07-13 Garantías en PROC-10 | `_garantias_vista`, obligación `REVISAR_GARANTIAS_PROC10` | `test_garantes_y_garantia_no_se_ejecuta`; M6 muerta |
| C07-14 Situación por fecha | `situacion_contractual.situacion_contractual` | `test_rescision_no_imputable_formalizada`; `test_conclusion_autorizada` |
| C07-15 Guardas posteriores | `exigir_vigente_en` (CNT-03 y CNT-04) y `exigir_vigente_para_modificacion` (CNT-02) | `test_guardas_posteriores`; `test_conclusion_autorizada`; M5 muerta; E2E 11 |
| C07-16 Aislamiento | `company_id` en cada consulta | `test_catalogo_situacion_y_contrato_no_formalizado` (empresa B → 404); E2E 16(c) |
| C07-17 Concurrencia | FOR UPDATE + versión + índice | `test_concurrencia_formalizacion` |
| C07-18 CNT-08 | `ORDEN_PROCESO`, `_eventos_cnt07`, `_terminacion_publica`, `ids_del_expediente` | `test_expediente_cnt08_proyecta_la_terminacion`; M8 muerta; E2E 13 |
| C07-19 CNT-09 | `condiciones` excluye el contrato extinguido; `reconciliar` resuelve | `test_alertas_cnt09_se_reconcilian` |
| C07-20 Reporte | `reporte_csv` | `test_reporte_csv`; E2E 15 |
| C07-21 Permiso `terminate` SENSITIVE | `CATALOGO_DE_PERMISOS`, `SENSITIVE_PERMISSIONS`, migración 0122 | `test_permiso_terminate_sensible`; MFA-G00; E2E 16(b) |
| C07-22 SoD y auditoría | `PROC03_TERMINACION_*`; 5 eventos | `test_rescision_no_imputable_formalizada`; `test_autoridad_y_notificaciones`; E2E 14 |
| C07-23 Imputable con apertura | Requisito `APERTURA` | `test_rescision_imputable_con_apertura` |
| C07-24 Mutuo acuerdo con documento | `DOCUMENTO_ACUERDO`, `sellar_documento` | Requisito cubierto en el servicio; sin prueba PG propia (ver CIERRE) |
| C07-25 Conclusión autorizada | Requisito `CONCLUSION`; `fecha_limite` | `test_conclusion_autorizada` |
| C07-26 Coherencia con lo registrado | `_hechos_posteriores` → `GOV_CONTRACT_TERMINATION_LATER_FACTS` | `test_hechos_posteriores_impiden_formalizar` |
| C07-27 Obligaciones informativas | `obligaciones` (LCP 51 y 8, BUD-08 y PROC-10) | `test_rescision_no_imputable_formalizada`; `test_rescision_imputable_con_apertura` |
| C07-28 UI y E2E | `TerminacionContratoPage`, enlace en la ficha, sección 10 del expediente | Vitest 5/5; E2E del sponsor |
