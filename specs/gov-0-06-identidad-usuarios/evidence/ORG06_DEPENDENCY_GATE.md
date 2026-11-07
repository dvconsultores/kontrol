# ORG-06 — Gate de dependencias (GOV-ORG-FUNCTIONAL-06)

**Resultado: ORG06_FULL_PROCESS_IMPLEMENTABLE = 0. ROUTING_DECISION = PREREQUISITE_ORG04. No se construyó producto.**

## La pregunta

CAN_ORG06_REPRESENT_ALL_VALID_CURRENT_OCCUPANTS_WITHOUT_ORG04 = **NO**. ORG04_REQUIRED_FOR_ORG06 = **1**.

## Evidencia

| # | Fuente | Regla | Por qué exige ORG-04 |
|---|---|---|---|
| 1 | N24 LOPPM, G.O. 6.015 Ext., art. 87 | «Las ausencias temporales del alcalde o alcaldesa serán suplidas por el funcionario de alto nivel de dirección, que él mismo o ella misma designe»; más de 15 días, autorización del Concejo; más de 90, el Concejo evalúa; detención judicial, designa el Concejo; ausencia absoluta, encargado el Presidente del Concejo | La máxima autoridad del piloto puede ejercerla legítimamente otra persona. Solo con titulares, ORG-06 mostraría a quien no la ejerce |
| 2 | N02 LOAP, G.O. 6.147 Ext., arts. 34, 35, 37, 40, 41 | Las alcaldesas y alcaldes pueden delegar atribuciones y firma; los actos se tienen como dictados por el delegante; el acto fija fecha de inicio y culminación; la eficacia depende de su publicación; cabe avocación | La autoridad ejercida no siempre coincide con el titular y cambia por acto |
| 3 | N32 LEFP, G.O. 37.522, arts. 1, 71, 72 | Comisión de servicio: ejercicio temporal de otro cargo, máximo un año. La ley rige también a municipios | Una persona puede ejercer un cargo distinto del que es titular |
| 4 | Gaceta Municipal 512 Ext., 10-12-2025, art. 120 | «El Alcalde o la Alcaldesa, mediante acto delegatorio, podrá…» | El acto delegatorio se usa en el derecho local vigente |
| 5 | DOC-02, `gov_acts.titularidad` | TITULAR, DELEGACION, ENCARGADURIA, SUPLENCIA | KONTROL ya registra actos suscritos por no titulares, con el nombre transcrito y sin vínculo |
| 6 | IR GOV-ORG-004 | «designaciones con acto soporte, vigencia y autoridad emisora» | **Incluso el titular se designa en ORG-04.** ORG-06 no tiene de dónde leer al ocupante |
| 7 | Decreto 5.233, G.O. 6.977 Ext. | Designación «en condición de Encargada» | La encargaduría también se usa a nivel nacional |

Un vínculo «usuario → cargo» sin esas figuras confundiría cargo titular con persona autorizada a ejercerlo. Construirlo solo para titulares es el producto parcial prohibido (§1 y §14).

## Orden correcto

ORG-04 responde **quién ocupa o ejerce un cargo, con qué acto y hasta cuándo**. ORG-06 responde **qué cuenta de usuario corresponde a esa persona, con qué alcance y qué separación de roles**. No hay ciclo: ORG-04 no depende de ORG-06, pero debe fijar la identidad institucional que ORG-06 usará.

## Fronteras

| Frontera | Resultado |
|---|---|
| N40 | N40_BLOCKS_ORG06 = 0. Sin regla nueva |
| ORG-03 | Sigue siendo la autoridad de cargos y límites. ORG-06 no la redefine |
| ORG-05 | Sin absorber. OQ-ORG05-01..03 siguen abiertas |
| ORG-07 | Debe mostrar cargo + ocupante actual tras ORG-04 y ORG-06, sin cambiar la autoridad base. Su «quién» sigue siendo el cargo |
| CTL-01 | No se duplica. Su actor sigue siendo el usuario autenticado; ORG-06 aporta el contexto institucional |
| CTL-03 | ADMIN ya no tiene capacidades de negocio (`authority.py`, OD-DEL-10). TECH_ADMIN_GAINS_FUNCTIONAL_AUTHORITY = NO por capacidades; falta comprobarlo frente a la autoridad institucional cuando exista |
| DOC-02 | Reutilizable como soporte del acto; sin duplicar documentos. Qué vínculos exigen acto eficaz se decide en ORG-04 por tipo de designación |
| Atenea | PAYROLL_SYSTEM. No es proveedor de identidad, directorio ni RBAC. Frontera en HR-01, HR-02 e INT-01 |
| Núcleo compartido | SHARED_CORE_CHANGE_REQUIRED = 0: tabla de Gobierno con referencia a `users` (baseline, frontera de identidad) |

## Decisión

| Condición | Exigido | Medido |
|---|---|---|
| REQUIREMENTS_FROZEN | 1 | 1 |
| NORMATIVE_BASIS_SUFFICIENT | 1 | 1 |
| N40_BLOCKS_ORG06 | 0 | 0 |
| ORG04_REQUIRED_FOR_ORG06 | 0 o satisfecho | **1, no satisfecho** |
| SHARED_CORE_CHANGE_REQUIRED | 0 | 0 |
| MATERIAL_OWNER_DECISIONS_PENDING | 0 | 0 |
| SECURITY, INTEGRITY, TESTABILITY_BLOCKER | 0 | 0 |

## ORG06_FIELD_CONTRACT (provisional, sujeto a ORG-04)

| Campo | Decisión | Origen |
|---|---|---|
| `user_id` | Sí, FK a `users` | Shared Core; sin duplicar autenticación |
| `company_id` | Sí, del contexto del servidor | Nunca del cliente |
| `institutional_identity` | Referencia a la identidad que fije ORG-04 | PII mínima |
| `position_id` | No propio si la ocupación de ORG-04 ya lo trae | Evita dos verdades |
| `organizational_unit_id` | Derivada del cargo | ORG-03 |
| `scope` | Derivado de ente y cargo | Sin alcance libre |
| `effective_from`, `effective_to`, `status` | Sí | Vigencia del vínculo, distinta de la de la ocupación |
| Soporte | Acto de ORG-04 | DOC-02 |
| `created_by`, versión | Sí | Concurrencia e historia |

Las invariantes se fijan al implementar: un vínculo vigente por cuenta y ocupación, historia inmutable con valores anterior y nuevo, sin autoasignación.
