# Plan PROC-08

Base: `develop` e0a2e44. Cabeza de Alembic medida: `0092_gov_proc07_evaluacion`. Nueva revisión: `0093_gov_proc08_decision`, que desciende de la cabeza real, re-medida antes de la migración.

## Datos (una migración, `0093_gov_proc08_decision`)

**`gov_procurement_recommendations`** (UUID, timestamps, `created_by`)
- Identificación y estado:
  - `company_id`, `file_id`, `committee_id`, `numero` (int; se muestra como «REC-01»);
  - `estado` EMITIDA | SUSTITUIDA;
  - `sustituye_id` (FK a sí misma, único), `motivo_sustitucion`, `sustituida_en`.
- Contenido:
  - `resultado_recomendado` ADJUDICAR | DECLARAR_DESIERTA | TERMINAR;
  - `causal_desierta` (LCP113_1 … LCP113_5; obligatoria solo con DECLARAR_DESIERTA);
  - `motivacion`, `examen_legal`, `examen_financiero`, `examen_tecnico`, `resultado_matriz` (texto, obligatorios);
  - `medidas_promocion` (texto, opcional).
- Instantánea de la evaluación:
  - `matrix_id`, `matrix_version`, `evaluacion_concluida_en`;
  - `snapshot` (JSON congelado).
- Informe:
  - `informe_storage_key`, `informe_sha256`, `informe_tamano`, `informe_nombre`.
- Emisión: `emitida_en`, `emitida_por`, `official_id` (si hay vínculo).
- Restricciones:
  - únicos `(company_id, file_id, numero)` y uno EMITIDA por expediente (índice único parcial);
  - check: causal solo con DECLARAR_DESIERTA.

**`gov_procurement_recommendation_signatories`**
- `recommendation_id`, `member_id`, `official_id`, `funcion`, `condicion`, `cuenta_voto`.
- Único `(recommendation_id, member_id)`.

**`gov_procurement_recommendation_options`**
- `recommendation_id`, `offer_id`, `posicion` 1..3.
- Únicos `(recommendation_id, posicion)` y `(recommendation_id, offer_id)`.

**`gov_procurement_recommendation_rejections`**
- `recommendation_id`, `offer_id`, `causal` (catálogo `CAUSALES_RECHAZO`: LCP76_1 … LCP76_8, RLCP102_1 … RLCP102_6), `motivacion`.
- Único `(recommendation_id, offer_id)`.

**`gov_procurement_decisions`** (UUID, timestamps, `created_by`)
- Identificación y vínculos:
  - `company_id`, `file_id`, `numero` (int; se muestra como «DEC-01»);
  - `recommendation_id` (obligatorio salvo en NULIDAD);
  - `resultado` ADJUDICADA | DESIERTA | TERMINADA | NULIDAD.
- Detalle según el resultado:
  - `offer_id` y `posicion` (solo con ADJUDICADA);
  - `causal_desierta` (solo con DESIERTA);
  - `causal_nulidad` INFORMACION_FALSA | VIOLACION_LEGAL y `anula_id` (FK a sí misma, solo con NULIDAD).
- Acto y autoridad: `act_id` (FK a `gov_acts`, único), `cargo_id`, `motivacion`.
- Registro: `decidida_en`, `decidida_por`, `official_id`.
- Estado: `estado` VIGENTE | ANULADA | SUSTITUIDA; `afectada_por_id`.
- Restricciones:
  - checks por resultado;
  - una decisión final vigente por expediente: índice único parcial `(file_id) WHERE estado = 'VIGENTE' AND resultado <> 'NULIDAD'`.

**Inmutabilidad** (triggers PG, patrón `kontrol_gov_eval_immutable`):
- Recomendaciones: sin DELETE. UPDATE solo de EMITIDA a SUSTITUIDA, con `sustituida_en`.
- Tablas hijas: sin UPDATE ni DELETE.
- Decisiones: sin DELETE. UPDATE solo de VIGENTE a ANULADA o SUSTITUIDA, con `afectada_por_id`.

**Cronología:** `CLASES_EVENTO_EXPEDIENTE` suma RECOMENDACION, RECHAZO_OFERTA, ADJUDICACION, DESIERTA, TERMINACION y NULIDAD (reescribir el check por nombre, como en 0092).

**Permisos:** `gobierno_decision` view, recommend y decide. Se siembran y se conceden a FUNCIONAL_COMPLETO, con el downgrade inverso.

## Servicio

Ficheros: `service_decision.py` (estado y recomendación) y `service_decision_resolver.py` (decisión).

**Reutiliza:**
- `_para_escribir`, `_abierto`, `_evento`, `_auditar` y `_err` (service_expedientes);
- `_politica_de`, `_funcionario_del_actor` y `exigir_autoridad_funcional` (service_identidad);
- `_autoridad_valida` (service_actos);
- `evaluar_antes_de_actuar` (service_sod);
- `_cadena_vigente` (service_evaluacion_resultados);
- `obtener_evaluacion` (service_evaluacion);
- reportlab y `get_storage` (patrón de `imports/difference_report.py`);
- `clave_identificacion` (service_notificaciones).

**Endpoints** (prefijo `/gobierno/contrataciones/expedientes/{id}/decision`):

| Método y ruta | Permiso | Cabecera | Respuesta |
|---|---|---|---|
| `GET ""` | view | — | estado (abajo) |
| `POST /recomendaciones` | recommend | If-Match | 201, estado |
| `GET /recomendaciones/{rid}/informe` | view | — | PDF |
| `POST /decisiones` | decide | If-Match | 201, estado |

**Estado** (lo que devuelve el GET):
- `evaluacion_concluida_en`, `recomendacion_vigente`, `recomendaciones`, `decision_vigente`, `decisiones`;
- `resultado` (de la decisión final vigente);
- `ofertas` (abiertas, con «rechazada» según la recomendación vigente), `miembros`;
- `actos_elegibles` (actos DOC-02 que cumplen FR-005 y no están usados);
- `notificaciones` (por oferente, para el acto de la decisión final vigente, más el estado del acto);
- `siguiente_accion` y catálogos con etiquetas.

**Errores** (409 salvo los indicados):

| Código | Cuándo |
|---|---|
| `GOV_DECISION_EVALUATION_PENDING` | Evaluación no concluida |
| `GOV_DECISION_IF_MATCH_REQUIRED` (428) | Falta If-Match |
| `GOV_PROCUREMENT_FILE_STALE` | Versión vieja (la da `_para_escribir`) |
| `GOV_RECOMMENDATION_ALREADY_ISSUED` | Ya hay una vigente y no se indica a cuál sustituye |
| `GOV_RECOMMENDATION_LOCKED_BY_DECISION` | Hay una decisión final vigente |
| `GOV_RECOMMENDATION_QUORUM` (422) | Los firmantes no alcanzan la mayoría |
| `GOV_DECISION_RECOMMENDATION_REQUIRED` | No hay recomendación vigente, o la indicada no es la vigente |
| `GOV_DECISION_ALREADY_FINAL` | Ya hay una decisión final vigente |
| `GOV_DECISION_INVALID_ACT` (422) | El acto no cumple FR-005 |
| `GOV_DECISION_ACT_IN_USE` | El acto ya sostiene otra decisión |
| `GOV_DECISION_OPTION_ORDER` (422) | La oferta no es la opción que corresponde |
| `GOV_DECISION_COMMISSION_SIGNATORY` (403) | Quien decide firmó la recomendación |
| `GOV_DECISION_NOTHING_TO_ANNUL` | No hay decisión vigente que anular |

Los datos inválidos dan 422 `GOV_PROCUREMENT_FILE_INVALID`, con el campo afectado.

**Siguiente acción** (en este orden):
1. «Preparar recomendación».
2. «Decidir el resultado».
3. «Notificar a los oferentes».
4. «Resultado notificado».
5. Con DESIERTA o TERMINADA notificada: «Procedimiento concluido: <resultado>».

**Auditoría:** 4 entradas nuevas de catálogo (catálogo 433 → 437):
- `GOV_PROCUREMENT_RECOMMENDATION_ISSUED`
- `GOV_PROCUREMENT_RECOMMENDATION_SUPERSEDED`
- `GOV_PROCUREMENT_DECISION_ISSUED`
- `GOV_PROCUREMENT_DECISION_NULLIFIED`

**SoD:** `PROC03_RECOMENDAR` (con la auditoría de recomendación emitida) y `PROC03_RESOLVER` (con la de decisión emitida), dentro de «PROC-03».

## Interfaz

- `ExpedienteDecision.tsx` (`SeccionDecision`) se inserta tras `SeccionEvaluacion` en `ExpedientePage.tsx`.
- Llamadas con `apiFetch` e `ifMatch`, como en PROC-07.
- Enlace al acto: `/gobierno/actos/:actoId`, que es donde se registran las notificaciones DOC-04.

## Constitution gate

| Principio | Reconciliación | Resultado |
|---|---|---|
| P1 Spec antes que código | Esta Spec, el plan y las tareas, antes de cualquier llamada | PASS |
| P2 Autorización | El mandato de la dueña nombra PROC-08 | PASS |
| P3 Trazabilidad | `traceability.md`: GOV-PROC-010/011 → FR → tareas → pruebas | PASS |
| P5 Historia protegida | Append-only con triggers; sustitución y nulidad sin borrar | PASS |
| P6 Seguridad en backend | Permiso + ente + identidad ORG-06 + cargo y competencia en la fecha del acto (ORG-03/07) + SoD CTL-01 + estado del expediente, todo en el servidor | PASS |
| P8 y P19 Reglas con fuente | Causales de los arts. 76, 102, 112 y 113 con artículo citado; sin ranking ni promedio | PASS |
| P11 Accesibilidad y responsive | Axe y 390/320 en la E2E | PASS (por demostrar) |
| P13 Integridad transaccional | If-Match, bloqueo de fila e índices únicos parciales | PASS |
| P18 Modales | Confirmaciones en línea, como en PROC-07 | PASS |
| P21 y P26 Paridad | Modelos y migración en la misma entrega; pruebas en PostgreSQL | PASS |
| P22 Autoridad única | Actos solo de DOC-02, notificaciones solo de DOC-04, autoridad solo de ORG-03/04/06/07, cronología de PROC-03, auditoría de CTL-02 | PASS |
| P24 Instalación limpia | Alembic desde cero, down y up | PASS (por demostrar) |

`BLOCKER = 0`, `CRITICAL = 0`, `CONTRADICTIONS = 0`, `OWNER CONFLICT = 0`, `MATERIAL OQ = 0`, `UNKNOWN = 0`.
Gaps declarados (no bloquean): OBS-PROC08-PARCIAL-01, OBS-PROC08-MONTO-01.

**CONSTITUTION_GATE = PASS**
