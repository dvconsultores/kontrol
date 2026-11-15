# CNT-02 · Trazabilidad (22/22)

| Contrato | Código | Prueba |
|---|---|---|
| C02-01 Contrato formalizado | `crear`: FORMALIZADO; `_contrato` filtra por empresa | P7 (NOT_FORMALIZED), P11 (404) |
| C02-02 Original inmutable | Sin escrituras en `gov_contracts`; guarda PG de CNT-01 | P1 (huella, monto y fin iguales), P10 (UPDATE gov_contracts → error) y E2E paso 4 |
| C02-03 Tipos | `TIPOS_MODIFICACION_CONTRATO`; la PRORROGA exige `nueva_fecha_fin` | P6 (INCOMPLETE), P7 (tipo inválido) |
| C02-04 Historia lineal | Índice único del borrador; UNIQUE de número y de la anterior; `base_numero` | P7 (DRAFT_EXISTS), P8 (`previous_amendment_id`), P9 (carrera) |
| C02-05 Proyección efectiva | `_vigente_a`, `historia(fecha)` y `_resumen_modificaciones` | P8 (programadas y fecha), P1, P2 y E2E paso 9 |
| C02-06 Plazo | R6 y CHECK `plazo` | P1, P6 (TERM_INVALID) |
| C02-07 Monto | `_monto_nuevo` y CHECK `montos`; delta con 2 decimales y distinto de 0 | P2 (0.001 y 0 → INVALID; 50000 → 60000) |
| C02-08 Cobertura en un aumento | R8, `_existente_valida` y `saldo_libre(…, None)` | P2 (INSUFFICIENT, EXCEEDS y saldo 5000), P12 y M1 |
| C02-09 Compromisos en una reducción | R9 y `control_compromisos` | P3 y M3; E2E paso 8 |
| C02-10 Objeto | No hay campo que lo cambie | Esquema `ModificacionUpdate` |
| C02-11 Contratista | No hay campo que lo cambie | Esquema `ModificacionUpdate` |
| C02-12 Moneda | `moneda = canonical(contrato)`; disparador sobre `moneda` | P10 (UPDATE moneda → error) |
| C02-13 Documento | `_documento_valido`, `sellar_documento` y `congelar_vinculo` | P1 (`documento_sellado`), E2E |
| C02-14 Autoridad | `_autoridad_valida`, `exigir_autoridad_funcional`, permisos y MFA (formalize SENSITIVE) | P11 (403), P4 |
| C02-15 Límite contra el monto nuevo | `control_firmante(monto_nuevo)` | P4 y M2; E2E paso 7 |
| C02-16 TRE-09 | `verificar_limite` y `conversion` en la fotografía | P5, H2 y M6 |
| C02-17 Fechas | R1, R5 y la validación del PATCH (F4) | P6 y P8 |
| C02-18 Concurrencia | Bloqueos contrato → modificación → expediente → CDP → estructura | P9 |
| C02-19 Aislamiento | `company_id` en cada consulta | P11; barrido ISO |
| C02-20 Auditoría | 5 eventos `GOV_CONTRACT_AMENDMENT_*` y cronología CONTRATO | P1, P4 y P7 |
| C02-21 Frontera con CNT-03 | Sin hitos, valuaciones, supervisores ni terminación | Revisión del código |
| C02-22 E2E/UAT | `e2e/gobierno-contratos-modificaciones.spec.ts` y OWNER_UAT_CARD | E2E 1/1 y humo UAT |
| Delta H01–H09 | `service_contratos.py` | H1–H7 en `test_gov_cnt01_moneda_cobertura.py`, CNT-01 13/13 y M4–M6 |
