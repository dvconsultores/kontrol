# CNT-09 · Alertas de vencimientos (GOV-CNT-010)

**Requisito:** emitir alertas de vencimiento de contratos, garantías, hitos y entregables, sin sustituir la decisión de la autoridad. Prioridad P1. Fuentes: N11 y N20 (ver FUENTES.md).

**Principio:** ALERT ≠ DECISION. Una alerta informa. Nunca aprueba, prorroga, anula, formaliza, conforma, recibe, paga ni cierra, y no cambia ningún estado de negocio.

## Historias

- **US1:** como administrador de contrato o supervisor, veo en Alertas los contratos, hitos y entregables que vencen hoy o ya vencieron, sin revisar contrato por contrato.
- **US2:** veo las garantías que vencen en 15 días o menos, o ya vencidas, según la regla de PROC-10.
- **US3:** en la ficha del contrato veo sus alertas activas.
- **US4:** como responsable de la configuración (`notificaciones:configure`), fijo días de preaviso para contratos, hitos y entregables, o los desactivo.
- **US5:** cuando la condición desaparece, la alerta queda RESUELTA y se conserva. Por ejemplo:
  - el hito se cumple;
  - el entregable queda conforme;
  - la garantía se renueva, sustituye, libera o ejecuta;
  - una prórroga formalizada (CNT-02) cambia la fecha;
  - el contrato se cierra.

## Requisitos funcionales

| FR | Requisito |
|---|---|
| FR-01 | **Contrato:** solo contratos FORMALIZADO, sin acto CIERRE de CNT-03 y con fecha de fin efectiva (`terminos_efectivos`). Sin fecha, no hay alerta. |
| FR-02 | **Garantía:** solo instrumentos en estado REGISTRADA, que es la vigente: renovada, sustituida, liberada o ejecutada dejan de serlo. La fase sale de `_vigencia(instrumento, hoy)` de PROC-10: POR_VENCER con días = 0 → DUE_TODAY; POR_VENCER con días ≥ 1 → UPCOMING; VENCIDA → OVERDUE. VIGENTE y FUTURA no generan alerta. |
| FR-03 | **Hito:** estado VIGENTE, no cumplido (sin recepción CONFORME que lo incluya), contrato formalizado y sin cierre. Fecha: `fecha_prevista`. |
| FR-04 | **Entregable:** estado VIGENTE, sin entrega CONFORME (entregar sin conformar no cumple), contrato formalizado y sin cierre. Fecha: `fecha_vencimiento`. |
| FR-05 | **Fases** de contrato, hito y entregable: OVERDUE si hoy > fecha; DUE_TODAY si hoy = fecha; UPCOMING si 1 ≤ fecha − hoy ≤ días de la política activa. Sin política, no hay UPCOMING. |
| FR-06 | **Severidad** (operativa, no jurídica): UPCOMING → INFO (WARNING en garantías, por la semántica «por vencer» de PROC-10); DUE_TODAY → WARNING; OVERDUE → CRITICAL. Los mensajes no usan lenguaje sancionatorio. |
| FR-07 | **Clave de deduplicación:** `cnt09:<tipo>:<id>:<fecha ISO>:<fase>`, con tipo `contract`, `guarantee`, `milestone` o `deliverable`. Si esa clave ya está RESUELTA y la condición vuelve, se usa `:r<n>`. Es una sola alerta activa por condición, fecha y fase. |
| FR-08 | **Reconciliación** por empresa en cada tick. Se crean con `crear_alerta` las alertas deseadas que no existen. Las alertas ACTIVE de CNT-09 cuya clave ya no es deseada se resuelven con `resolver_alerta_de_sistema`. Nunca se borra nada. |
| FR-09 | **Planificador:** el manejador `gov_contract_deadline_alerts` (Spec dueña gov-cnt-09) se registra en `registry.py`, con política `OWNER_IDEMPOTENT`. Usa `hoy_de_negocio(contexto.now)`. |
| FR-10 | **Orígenes Spec 047** y permiso de visibilidad. Todos los de contrato van a `source_id = contrato`: `GovernmentContract` (route `gov_contract`), y `GovernmentContractMilestone` y `GovernmentContractDeliverable` (route `gov_contract_execution`, `source_item_id` = el elemento), los tres con `gobierno_contratos:view`. `GovernmentGuaranteeInstrument` va a `source_id` = expediente y `source_item_id` = instrumento (route `gov_procurement_file`), con `gobierno_garantias:view`. |
| FR-11 | **Contexto del contrato:** `GET /gobierno/contratos/{id}/alertas` (`gobierno_contratos:view`) devuelve las alertas del motor 047 del contrato, activas por defecto. Las de garantía se incluyen solo con `gobierno_garantias:view`. Un contrato de otra empresa responde 404. |
| FR-12 | **Política institucional:** `GET`/`PUT /gobierno/contratos-alertas/politicas`. GET exige `gobierno_contratos:view` y PUT exige `notificaciones:configure`. Hay una fila por fuente (CONTRATO, HITO, ENTREGABLE) con `activo` y `dias_anticipacion` (1–365). Se audita como GOV_CONTRACT_ALERT_POLICY_UPDATED, sin MFA. |
| FR-13 | **Mensajes:** catálogo `es` de `notifications/messages.py`, con código o referencia y fecha, sin PII ni contenido documental. |
| FR-14 | **Bandeja `/alertas`:** reutilizada, con filtros por severidad y por origen sobre la API existente. Los enlaces llevan al contrato, a su ejecución o al expediente. |
| FR-15 | **Sin efectos de negocio:** el contrato, los términos, hitos, entregables, garantías, presupuesto, pagos, contabilidad y almacén no cambian. |
| FR-16 | **Aislamiento y concurrencia:** se filtra por `company_id` en todo. Dos ticks simultáneos dejan una sola alerta, con `uq_alerts_company_dedupe` como última defensa. |
| FR-17 | **E2E del sponsor y UAT:** ver plan §E2E. |

## Fuera de alcance

- CNT-05, CNT-06, CNT-07 y CNT-08 (de P2); BUD-09, TRE-04, pagos, contabilidad y almacén.
- El plazo de firma en días hábiles: DEFERRED_BY_CALENDAR_AUTHORITY.
- Un segundo motor, una segunda bandeja o un segundo planificador.
