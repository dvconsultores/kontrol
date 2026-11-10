# PROC-09 · Decisiones y CONSTITUTION GATE (2026-11-11)

## Lo que la fuente resuelve (no se escala)

- PDD-PROC09-01. La aplicabilidad no es una configuración del ente: la fija la norma nacional (LCP art. 31; RLCP art. 34) con
  exclusiones tasadas (RLCP arts. 3, 40 y 48) y una inclusión expresa (art. 49). El ente no puede desactivarla.
- PDD-PROC09-02. El criterio es **cuantitativo**: el monto total de la **oferta**, incluidos los tributos, frente a 2.500 U.T.
  No depende de la modalidad (RLCP art. 34: «en todas las ofertas… así como en los procedimientos excluidos»).
- PDD-PROC09-03. El compromiso **no** se evalúa comparativamente (RLCP art. 46): no entra en la matriz de PROC-07.
- PDD-PROC09-04. Oportunidades del proceso, por fuente: pliego o condiciones (LCP art. 66 num. 15; RLCP art. 37) → declaración
  jurada con la oferta (RLCP art. 38) → rechazo si falta cuando es exigible (LCP art. 76 num. 8) → adjudicación publicada con el
  compromiso (RLCP art. 42) → obligación contractual garantizada (LCP art. 30) → seguimiento y cumplimiento antes del cierre
  administrativo del contrato (LCP arts. 32 y 118 num. 3; RLCP arts. 36 y 44).
- PDD-PROC09-05. El monto del compromiso se calcula sobre el monto del objeto del contrato sin IVA (RLCP art. 91).
- PDD-PROC09-06. El oferente y el adjudicatario son los de PROC-06 y PROC-08 (no Party de Enterprise).

## CONSTITUTION GATE

| Compuerta | Resultado | Motivo |
|---|---|---|
| SECURITY | PASS | Sin riesgo propio: capacidad específica, aislamiento por ente y MFA solo en la formalización seguirían el patrón de PROC-10 |
| DATA_INTEGRITY | PASS | El patrón append-only con triggers de PROC-08 y PROC-10 es aplicable |
| ARCHITECTURAL | PASS | Cabe en el módulo `government` y en la ficha del expediente; Documentos de la Spec 046 como soporte |
| TESTABILITY | PASS | Verificable en PostgreSQL y en Chromium **si** existen los datos de entrada |
| **LEGAL** | **BLOCKED** | Conflicto de porcentaje: LCP art. 31 (2014) fija «el tres por ciento (3%) sobre el monto de la contratación»; RLCP art. 35 (2009) fija un rango del 1 % al 5 % «del monto del contrato suscrito» que el ente gradúa. La transitoria de la LCP mantiene el reglamento para el «manejo» del compromiso. Decidir cuál rige es interpretación jurídica |
| **NORMATIVE** | **BLOCKED** | El umbral está en U.T. y la biblioteca prohíbe codificarlo como constante: su valor por fecha debe venir de la versión normativa aplicable. La fuente candidata, N38 (providencias del SENIAT), es de clase C; no hay copia oficial verificada del valor de la U.T. |
| **DOMAIN_DEPENDENCY** | **BLOCKED** | (1) `DOMAIN_DEPENDENCY_ON_AMOUNT = 1`: la oferta no registra monto total ni tributos (OBS-PROC08-MONTO-01, OPEN). (2) Las exclusiones necesitan la condición del oferente (órgano o ente del Estado; extranjero con o sin filial; servicio laboral excluido), que la oferta no registra. (3) La incorporación al pliego depende de PROC-04 (BLOCKED, D-GOV-03). (4) La obligación contractual y su cumplimiento dependen del contrato y su administración (CNT-01, CNT-03, CNT-08, NOT_STARTED) |

`CONSTITUTION_GATE = BLOCKED`. `DEEPSEEK_CALLS = 0`.

### Por qué no se construye una parte

Con las autoridades de hoy, toda evaluación daría `NO_DETERMINABLE` («falta el monto total de la oferta con tributos y el valor de
la U.T. a la fecha»). Solo serían determinables las exclusiones, y tampoco: falta la condición del oferente. El estado `APLICA`, que
es el que habilita el compromiso, sería inalcanzable sin inventar un monto o una U.T. Una sección que siempre dice «pendiente de
determinar» no controla nada: sería completitud falsa, contraria a `NO_PARTIAL_PRODUCT`. Tampoco se puede registrar «la declaración
jurada» como si fuera exigible sin saber si lo es (LCP art. 76 num. 8: «cuando éste sea exigible»).

## Preguntas abiertas

| Id | Tipo | Pregunta | Quién | Opciones |
|---|---|---|---|---|
| OQ-PROC09-01 | MATERIAL_DECISION_REQUIRED | ¿Registra la plataforma, al recibir cada oferta (PROC-06), el monto total con tributos y el monto del objeto sin IVA declarados en la oferta? Esto cerraría la parte de oferta de OBS-PROC08-MONTO-01 y también haría evaluables las garantías porcentuales de PROC-10 y los límites de monto de PROC-08 | Dueña | A. Sí, en un ciclo previo «monto de la oferta» (PROC-06, con soporte y sin recalcular el pasado). B. No; esperar al presupuesto base (PROC-04) o al contrato (CNT-01) |
| OQ-PROC09-02 | LEGAL_VALIDATION_REQUIRED | Fuente oficial y valor por fecha de la unidad tributaria para el umbral de 2.500 U.T. (copia oficial con Gaceta, hash y vigencia), o confirmación jurídica de otra referencia vigente | Sponsor / profesional del derecho | Pasar N38 (U.T.) a clase A o B con el histórico de valores |
| OQ-PROC09-03 | LEGAL_VALIDATION_REQUIRED | Porcentaje vigente: el 3 % fijo de la LCP art. 31 o el rango del 1 % al 5 % del RLCP art. 35 | Profesional del derecho | A. Rige el 3 % (jerarquía y ley posterior). B. Rige el rango del reglamento. C. Otra |
| OQ-PROC09-04 | MATERIAL_DECISION_REQUIRED | Alcance del primer corte una vez resueltas las anteriores: aplicabilidad, declaración jurada con la oferta, rechazo y publicación con la adjudicación (sin contrato), o esperar a CNT-01 para incluir la obligación contractual y el cumplimiento | Dueña | A. Corte de selección ahora; cumplimiento con CNT-03. B. Todo junto tras CNT-01 |

`MATERIAL_DECISION_REQUIRED = 1` (OQ-PROC09-01 y OQ-PROC09-04). `LEGAL_VALIDATION_REQUIRED = 2` (OQ-PROC09-02 y OQ-PROC09-03).
