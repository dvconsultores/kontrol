# CNT-01 · Trazabilidad

| Contrato | Código | Prueba |
|---|---|---|
| C01-01 Requisito de adjudicación | `service_contratos.crear` (`_decision_vigente`, ADJUDICADA, `offer_id`, `_abierto`) | `test_vector_b` (crear tras TERMINADA → AWARD_REQUIRED) |
| C01-02 Adjudicación vigente | `_adjudicacion_vigente` y `_exigir_adjudicacion_vigente` en la edición y la formalización | `test_vector_b`; mutación M1 |
| C01-03 Oferta adjudicada | `crear`: oferta y monto vigente (`_monto_vigente`) | `test_sin_monto_no_se_prepara` |
| C01-04 Contratista | Fotografía `contratista_*` | `test_vector_a` y `test_vector_c` |
| C01-05 Objeto | Fotografía de `objeto`; `descripcion_complementaria` aparte | `test_vector_a`; disparador `kontrol_gov_contract_guard` |
| C01-06 Monto | `monto = total_con_tributos` y `amount_id`; formalizar comprueba SOURCE_CHANGED | `test_vector_c` (el monto del cliente se ignora) |
| C01-07 Moneda | `moneda` de la oferta; sin conversión | `test_vector_c` y `test_vector_g` |
| C01-08 Tipo de instrumento | `TIPOS_INSTRUMENTO_CONTRATO`; PATCH `tipo` | `test_vector_a`; E2E |
| C01-09 Plazo | PATCH con fechas; CHECK `plazo`; INCOMPLETE al formalizar | `test_vector_a`; E2E |
| C01-10 Vínculo con la CDP | `_motivo_certificado` (ente, VIGENTE, moneda, ejercicio, expediente) | `test_vector_e` y `test_vector_g`; mutación M2 |
| C01-11 Asignación de cobertura | `actualizar_cobertura` (saldo libre, un solo ejercicio, ≤ monto); formalizar exige suma = monto | `test_vector_d`; mutación M4 |
| C01-12 Sin efecto en BUD-08 | No hay escrituras en `gov_budget_certificates` | `test_vector_a` (la CDP queda igual) |
| C01-13 Garantías | `actualizar_garantias` (expediente, oferta, REGISTRADA); formalizar comprueba GUARANTEE_NOT_ACTIVE | `test_vector_a`; E2E |
| C01-14 Documento | `_documento_valido`; versión y sha256; sellado y congelado al formalizar | `test_vector_a` (`documento_sellado`) |
| C01-15 Autoridad funcional | `_autoridad_valida(FIRMAR, CONTRATACIONES)` y `exigir_autoridad_funcional` | `test_vector_f` (cargo sin FIRMAR → SIGNER_INVALID) |
| C01-16 Límite del firmante | `clasificar_monto` (AAL generalizado) y `GOV_CONTRACT_SIGNER_BLOCKED` | `test_vector_f`, `test_vector_g` y E2E; mutación M3; AAL 12/12 sin cambios |
| C01-17 Ciclo | BORRADOR → FORMALIZADO; CHECK `completitud` | `test_vector_a` |
| C01-18 Formalización | `formalizar` (pasos 1–10), código, fotografía y huella | `test_vector_a` y E2E |
| C01-19 Inmutabilidad | Disparadores de contrato y vínculos | `test_inmutable_en_base` |
| C01-20 Concurrencia | Expediente, contrato, CDP y estructura con `FOR UPDATE`; `UNIQUE(decision_id)`; bloqueo consultivo | `test_vector_h` (doble creación y doble formalización) |
| C01-21 Aislamiento | Filtro `company_id` | `test_vector_i` |
| C01-22 Auditoría | 4 eventos, sin importes, entidad expediente | `test_vector_a`, `test_vector_f` y `test_permisos_mfa_y_ctl01` (CTL-01) |
| C01-23 Frontera con CNT-02 | Sin endpoints sobre un FORMALIZADO (409 ALREADY_FORMALIZED) | `test_vector_a` y E2E (doble formalización → 409) |
| C01-24 E2E y UAT | `gobierno-contratos.spec.ts`, `OWNER_UAT_CARD.md` y humo en la UAT | E2E (recorrido, negativas, Axe y 1280/390/320) |

Cobertura: 24 de 24 contratos (100 %).
