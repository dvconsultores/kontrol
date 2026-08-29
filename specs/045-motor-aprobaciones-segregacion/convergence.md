# CONVERGENCIA — SPEC 045

| Campo | Valor |
|---|---|
| Iniciativa | `045-motor-aprobaciones-segregacion` |
| Fecha | 2026-08-29 |
| Rama | `develop` |
| Autorización | Expresa, mencionando `045` (P2) |
| Orden ejecutado | F1 → F2 → F3 → F4 → F7 → F5 → F6 |

`/speckit.converge` compara SPEC → PLAN → TASKS → CÓDIGO → FRONTEND → BACKEND →
POSTGRESQL → AUDITORÍA → PRUEBAS → E2E → EVIDENCIA.

## 1. Estado de implementación

| Área | Estado | Evidencia |
|---|---|---|
| Modelo (8 tablas) | ✔ | `app/modules/approvals/models.py` |
| Migración de esquema `0015_approvals` | ✔ compila en dialecto PostgreSQL | `tests/test_migrations_offline.py` |
| Migración de datos `0016_approvals_backfill` | ✔ idempotente (2 ejecuciones) | idem |
| Motor de evaluación | ✔ | `service.py`: `evaluate`, `ConditionEvaluator`, `compute_amount_base`, `compute_fingerprint`, `resolve_actors` |
| Ciclo de la solicitud | ✔ | `require`, `decide`, `cancel`, `mark_expired`, `document_changed` |
| Configuración de políticas | ✔ | `create_policy`, `update_policy`, `activate_policy`, `close_policy`, `add_rule`, `add_level` |
| Delegaciones | ✔ | `create_delegation`, `revoke_delegation` |
| API | ✔ 22 endpoints | `app/modules/approvals/api.py` |
| Frontend | ✔ 4 rutas + 1 panel embebido | `src/modules/aprobaciones/` |
| Integración de dominios | ✔ **los 4**: compras (requisición y orden), ventas (crédito), inventario (ajustes y conteos), regulatorio (flujo + datos) | `app/modules/approvals/integration.py` |
| Auditoría | ✔ vía `record_audit` (ADR-012), sin rastro paralelo | `test_audit_is_recorded` |
| Eventos de dominio | ✔ 6 tipos | `test_domain_events_are_emitted` |

## 2. Compuertas ejecutadas

| Compuerta | Antes de 045 | Después | Resultado |
|---|---|---|---|
| pytest | 223 | **276** | ✔ (+53) |
| vitest | 210 | **217** | ✔ (+7, puertas G1-G4 automáticas) |
| ruff · mypy | ✔ | ✔ | Sin hallazgos (75 archivos) |
| tsc · eslint | ✔ | ✔ | Sin hallazgos |
| Bundle | 375 KB | **377 KB** (gzip 115 KB) | +2 KB por 4 páginas con code-splitting |
| axe WCAG 2.2 AA | 19/19 | **22/22** | ✔ ejecutado — pero ver `CVG-045-07`: no prueba por sí solo que cada ruta renderizara |
| Verificación directa de las 3 pantallas nuevas | — | **3/3** | ✔ navegación SPA con espera de URL y `h1` |
| Responsive | 198/198 (33 rutas) | **216/216 (36 rutas)** | ✔ 0 scroll horizontal en 6 viewports |
| Regresión de los 4 dominios | — | ✔ | `test_purchasing`, `test_sales`, `test_inventory`, `test_regulatory`, `test_process_flows` sin cambio de expectativa |

## 3. Cobertura de los criterios de aceptación

| AC | Cubierto | Prueba |
|---|---|---|
| AC-01 política versionada no altera lo resuelto | ✔ | `test_policy_snapshot_is_frozen` |
| AC-02 sin dos políticas activas | ✔ | `test_policy_versioning_and_activation` |
| AC-03 monto en moneda base | ✔ | `test_amount_is_evaluated_in_base_currency` |
| AC-04 condición no evaluable | ✔ | `test_unevaluable_condition_never_passes_silently` |
| AC-05 segregación | ✔ | `test_segregation_excludes_creator` |
| AC-06 delegación no elude segregación | ✔ | `test_delegation_cannot_bypass_segregation` |
| AC-07 obsolescencia | ✔ | `test_document_change_marks_request_obsolete` |
| AC-08 cambio ajeno no invalida | ✔ | `test_unrelated_change_does_not_invalidate` |
| AC-09 concurrencia | **◐** | `test_version_conflict_on_concurrent_decision` (lógica). Falta PostgreSQL |
| AC-10 idempotencia | ✔ | `test_request_is_idempotent` |
| AC-11 cuórum N de M | ✔ | `test_quorum_n_of_m` |
| AC-12 una negativa basta | ✔ | `test_one_negative_closes_even_with_quorum_all` |
| AC-13 rechazo terminal | ✔ | `test_reject_is_terminal` |
| AC-14 devolución encadena | ✔ | `test_return_keeps_history_and_chains` |
| AC-15 motivo obligatorio | ✔ | `test_reason_required_on_negative` |
| AC-16 vencimiento no resuelve | ✔ | `test_expiry_marks_but_does_not_resolve` |
| AC-17 no avanza sin aprobación | ✔ | `test_blocks_advance_until_approved`, `test_domain_blocked_while_approval_pending` |
| AC-18 revocar no reescribe historia | ✔ | `test_revoked_delegation_does_not_invalidate_past_decisions` |
| AC-19 bandeja transversal | ✔ | `test_inbox_is_transversal_across_domains` |
| AC-20 migración sin cambio de comportamiento | ✔ | `test_domains_behave_identically_without_policy` + regresión |
| AC-21 ningún módulo con lógica propia | ✔ | `test_no_domain_keeps_its_own_approval_logic` |
| AC-22 histórico sin inventar política | ✔ | `test_approvals_data_migration_is_idempotent` |
| AC-23 nada de negocio en código | ✔ | Verificado por búsqueda (§6) |
| AC-24 accesibilidad y responsive | ✔ | axe 22/22 · responsive 216/216 |

**23 de 24 cubiertos; 1 parcial por ausencia de PostgreSQL.**

## 4. Desviaciones respecto a la Spec, y su resolución

Ninguna amplía el alcance. Todas quedan documentadas y los artefactos de la Spec fueron corregidos.

| # | Desviación | Resolución |
|---|---|---|
| **D-01** | `data-model.md` declaraba 7 tablas; el motor tiene **8** | Inconsistencia **interna de la Spec**: `plan.md` §5 y FR-045-066 ya exigían tabla de eventos. Resuelta a favor de `plan.md`; `data-model.md` corregido |
| **D-02** | **Colisión de nombre de tabla**: `regulatory.approval_requests` ya ocupaba el nombre que el motor necesita | La Spec ya decidía retirar esa tabla (FR-045-073). Se renombra a `regulatory_approval_requests` en `0015`, **sin cambiar el comportamiento del módulo regulatorio**, y su histórico se traslada en `0016`. No es alcance nuevo: es el destino que la Spec ya había fijado, adelantado a F1 porque sin él el motor no puede existir |
| **D-03** | La migración `0015` mezclaba esquema y datos | Separada: `0015` esquema puro, `0016` datos. No era estética: una migración de datos rompe `alembic upgrade --sql`, que es cómo se valida el dialecto PostgreSQL sin instancia. El proyecto ya aplicaba esta separación en 0013 |
| **D-04** | `ConfirmationDialog` no admitía contenido, y el motivo de rechazo debe capturarse en la confirmación | Se **extendió el componente compartido** con un slot `children` en lugar de crear una variante local (P17). El modal sigue siendo de confirmación breve; los formularios complejos siguen en pantalla completa (ADR-015) |
| **D-05** | `apiFetch` no admitía `If-Match`, exigido por el control optimista | Añadido `ifMatch` al **cliente HTTP compartido**. ADR-013 ya requería ETag/versión; la capacidad faltaba en la plataforma, no en esta Spec |
| **D-06** | El contexto de la requisición no puede llevar `amount`: `RequisitionLine` no tiene precio | La política de ese proceso se configura sobre cantidad, centro de costo o solicitante. No se inventó un precio. Registrado como observación funcional (§7) |

## 5. Brechas abiertas

| ID | Brecha | Tipo | Bloquea |
|---|---|---|---|
| **CVG-045-01** | **Concurrencia real no verificada**: no hay servidor PostgreSQL en el entorno (BLK-D0-01). `SELECT … FOR UPDATE` se emite sólo en dialecto PostgreSQL y el índice parcial de solicitud viva es condicional | TECHNICAL | `COMPLETE_100` |
| **CVG-045-02** | `alembic upgrade head` y `alembic check` no ejecutados contra PostgreSQL real | TECHNICAL | `COMPLETE_100` |
| CVG-045-03 | E2E de flujo completo (configurar → disparar → aprobar → documento avanza) no automatizado en Playwright; cubierto por integración in-process | QA | No |
| CVG-045-04 | Evidencia adjunta a la solicitud: contrato declarado, inactivo hasta la Spec 046 | DEPENDENCIA | No (CL-045-10) |
| CVG-045-05 | Notificación activa al aprobador: el motor emite eventos; el envío es de la Spec 047 | DEPENDENCIA | No (CL-045-11) |
| CVG-045-06 | Cross-browser (firefox/webkit) de las 3 pantallas nuevas no ejecutado en esta pasada | QA | No |
| **CVG-045-07** | **Las herramientas de QA del proyecto miden menos de lo que declaran**: el crawler de rutas y el spec de axe navegan con `page.goto`, que redirige a `/` porque el token vive en memoria (ADR-004). Verificado sobre rutas preexistentes y sobre los JSON históricos. Las cifras «71/71» y «19/19» del expediente no prueban que cada ruta renderizara | **QA — Spec 054** | No bloquea 045 (las pantallas nuevas se verificaron por navegación SPA), pero **invalida evidencia histórica del proyecto** |

## 6. Verificaciones de prohibición

| Prohibición | Verificación | Resultado |
|---|---|---|
| Sin montos, umbrales, niveles, roles ni monedas hardcodeados (P8) | Búsqueda de literales de negocio en `app/modules/approvals/` | **0 coincidencias** — los únicos valores literales son constantes de integración (`PROCESS_*`) y catálogos de operadores/cuórum, que son vocabulario, no política |
| Ningún módulo con aprobación propia (P22) | `test_no_domain_keeps_its_own_approval_logic` | ✔ |
| Sin políticas de clientes concretos en seeds | El seed sólo añade permisos, ninguna política | ✔ |
| Sin modales para configuración | Configuración en `/aprobaciones/politicas/:id`, pantalla completa | ✔ |
| Sin lógica de notificación en el motor | El motor escribe `approval_events`; no envía nada | ✔ |
| Sin almacenamiento de archivos en el motor | Contrato declarado, sin implementación | ✔ |

## 7. Observaciones funcionales para las Specs consumidoras

No son brechas de 045; son consecuencias que sus Specs deben recoger.

1. **Requisición sin monto.** `PurchaseRequisition` no lleva importe. Su política se configura sobre
   cantidad, centro de costo o solicitante. Si el negocio quiere aprobar requisiciones por monto,
   eso exige un costo estimado por línea — alcance de la **Spec 015**, no de ésta.
2. **`cost_center_id` sigue siendo texto libre.** El motor puede evaluar sobre él, pero sin la
   **Spec 007** no hay maestro que valide el valor.
3. **Sin ubicación en el contexto de inventario.** Cuando llegue la **Spec 008/022**, las políticas
   de ajuste podrán condicionarse por ubicación. El motor ya admite la dimensión.

## 7bis. Corrección aplicada durante la propia convergencia

La primera pasada de converge detectó dos incumplimientos de mi propia implementación, que
corregí antes de cerrar:

1. **Conteos de inventario sin integrar.** T-045-064 dice «ajustes **y conteos**»; sólo había
   integrado los ajustes. Corregido: `transition_count` y `approve_count` delegan en el motor.
2. **Regulatorio migrado sólo en datos.** El histórico se trasladaba en `0016`, pero su flujo en
   ejecución seguía siendo propio, lo que incumple FR-045-075 y el Principio 22. Corregido:
   `create_approval_request` y `transition_approval_request` delegan en el motor.

Además, `test_no_domain_keeps_its_own_approval_logic` **excluía `regulatory`**: estaba escrito para
pasar, no para comprobar. Ampliado a los cuatro dominios más una verificación de que ningún módulo
declara modelo de política propio.

## 8bis. CIERRE DEFINITIVO (2026-08-29)

Este documento recoge la **primera** pasada de convergencia, cuando no había
PostgreSQL en el entorno. El cierre definitivo está en
[`convergence/045-final-convergence.md`](convergence/045-final-convergence.md) y
[`SPEC_045_FINAL_CLOSEOUT.md`](SPEC_045_FINAL_CLOSEOUT.md).

Estado final de las brechas que este documento dejó abiertas:

| Brecha | Estado final |
|---|---|
| CVG-045-01 concurrencia | **RESOLVED_IN_045** — PostgreSQL 16.2, suite 276/276, E2E de concurrencia |
| CVG-045-02 `alembic upgrade`/`check` | **RESOLVED_IN_045** — Casos A y B, drift de 045 = 0 |
| CVG-045-03 E2E Playwright | **RESOLVED_IN_045** — 11 escenarios, 3 navegadores |
| CVG-045-04 adjuntos | **DEFERRED_EXTERNAL_DEPENDENCY — 046** |
| CVG-045-05 notificaciones | **DEFERRED_EXTERNAL_DEPENDENCY — 047** |
| CVG-045-06 cross-browser | **RESOLVED_IN_045** — Chromium, Firefox, WebKit |
| CVG-045-07 herramientas de QA | **RESOLVED_IN_045** (instrumentación) + **DEFERRED — 054** (plataforma) |

**Veredicto: `SPEC 045 COMPLETE_100`.**

## 8. Veredicto de convergencia (primera pasada, superado)

La Spec **converge en alcance y en trazabilidad**: 0 requisitos sin implementación, 0 tareas
abiertas obligatorias, 0 contradicciones con la Constitución v1.1 ni con los 29 ADR.

**No converge en evidencia de persistencia**: dos brechas técnicas (`CVG-045-01`, `CVG-045-02`)
dependen de una instancia PostgreSQL que este entorno no tiene. Ambas son la misma dependencia
—BLK-D0-01— que la Constitución v1.1 P21 convirtió en condición de `COMPLETE_100` para las 56 Specs.

Por tanto **no se declara `COMPLETE_100`**.
