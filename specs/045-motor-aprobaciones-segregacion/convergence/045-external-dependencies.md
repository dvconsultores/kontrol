# DEPENDENCIAS EXTERNAS — RECLASIFICACIÓN FORMAL (§32)

| ID | Dependencia | ¿Pertenece realmente a 045? | Contrato listo | ¿Bloquea 045? | Clasificación | Spec destino |
|---|---|:--:|:--:|:--:|---|---|
| **CVG-045-04** | Adjuntos de evidencia en la solicitud | **No** | **Sí** | **No** | **`RESOLVED_BY_SPEC_046`** *(2026-08-30)* | **046** — cerrada |
| **CVG-045-05** | Notificación activa al aprobador | **No** | **Sí** | **No** | `DEFERRED_EXTERNAL_DEPENDENCY` | **047** |
| **CVG-045-07** | Plataforma general de QA | **Parcial** | n/a | **No** | `RESOLVED_IN_045` (instrumentación) + `DEFERRED_EXTERNAL_DEPENDENCY` (plataforma) | **054** |

## CVG-045-04 · Adjuntos — Spec 046

**Qué exigía 045.** `FR-045-067`: «Contrato de adjuntos de evidencia sobre
`ApprovalRequest` conforme a `ADR-D0-008`». Un contrato, no una implementación.
`CL-045-10` lo fijó desde la especificación: mientras 046 no exista, la evidencia
es `reason` y `observations` en texto.

**Verificación de los cuatro criterios del §29:**

| Criterio | Estado |
|---|---|
| El contrato existe | ✔ `AttachmentLink(entity_type='ApprovalRequest', entity_id=<request_id>)` |
| La integración está definida | ✔ `ADR-D0-008` fija el modelo; 045 no necesita cambios cuando llegue |
| 045 funciona por completo sin acoplamiento | ✔ 11 escenarios E2E y 276 pruebas sin un solo adjunto |
| Ningún requisito obligatorio de 045 exige archivos hoy | ✔ ninguno de los 40 FR |

**No se implementa 046 dentro de 045.**

### Cierre — 2026-08-30 · `RESOLVED_BY_SPEC_046`

`SPEC 046 COMPLETE_100` satisface el contrato. Verificado contra código y
pruebas ejecutadas, no contra el roadmap.

**Cadena de evidencia:**

| Eslabón | Artefacto |
|---|---|
| Requisito 045 | `FR-045-067` · «Contrato de adjuntos de evidencia sobre `ApprovalRequest` conforme a `ADR-D0-008`» |
| Contrato 046 | `resources.py:38` · `ResourceKind("ApprovalRequest", …, "aprobaciones:view", ("045",))` — registro **cerrado** |
| Modelo 046 | `DocumentLink(resource_type, resource_id, role, frozen_version_id, is_frozen)` |
| Código 046 | `service.attach` · `service.freeze_links` · `service.documents_for` |
| API 046 | `POST /documentos/{id}/vinculos` · `GET /documentos/por-recurso/ApprovalRequest/{id}` |
| Prueba | `test_documents.py::test_version_congelada_el_historico_no_se_reinterpreta` |
| Evidencia | La V1 vinculada se congela; se carga una V2; el histórico sigue devolviendo **los bytes de la V1** con su hash |

**Los cuatro criterios del §29, revisados tras el cierre:**

| Criterio | Estado |
|---|---|
| El contrato existe | ✔ implementado, no solo declarado |
| La integración está definida | ✔ y ejecutada |
| 045 funciona sin acoplamiento | ✔ |
| Ningún FR de 045 exige archivos | ✔ |

**`CL-045-10` cumplido literalmente: 0 cambios en el modelo de 045.**

| Comprobación | Resultado |
|---|---|
| `git diff 921aaa2..51cbb5a -- app/modules/approvals/` | **vacío** |
| `approvals` importando `documents` | **0** |
| `documents` importando `approvals` fuera del registro | **0** |
| `document_link_id` / `attachment_id` en `ApprovalRequest` | **ausentes**, comprobado por la propia prueba |

El nombre de la entidad pasó de `AttachmentLink` (nomenclatura del ADR-D0-008) a
`DocumentLink` (nomenclatura de 046). La semántica, las columnas y el contrato
son los mismos; se documenta la equivalencia para que no se lea como divergencia.

**La Spec 045 no se reabre.** Este cierre es de gobierno: no toca su código, sus
pruebas de negocio ni su arquitectura.

## CVG-045-05 · Notificaciones — Spec 047

**Qué exigía 045.** `FR-045-066`: «Emitir eventos de dominio para consumo futuro
de la Spec 047». Emitir, no notificar.

| Criterio | Estado |
|---|---|
| 045 emite eventos | ✔ tabla `approval_events`, 6 tipos verificados |
| Contrato documentado | ✔ `contracts/api-contracts.md` §Eventos |
| Sin acoplamiento | ✔ el módulo `approvals` no importa nada de notificación |
| El flujo funciona sin consumidor | ✔ la bandeja es el canal actual |

Eventos verificados: `approval.requested`, `approval.step_opened`,
`approval.decided`, `approval.resolved`, `approval.obsolete`, `approval.step_expired`.

**No se implementa correo, bandeja de notificaciones, push ni tareas dentro de 045.**

## CVG-045-07 · Herramientas de QA — parte 045, parte Spec 054

Separación exigida por el §31:

### A · QA necesario para aceptar 045 → **resuelto ahora**

| Capacidad | Estado |
|---|---|
| Instancia PostgreSQL para pruebas | ✔ `qa/pg-provision.sh` |
| Validación de migraciones sobre PG | ✔ `qa/pg-migration-validation.sh` |
| Siembra de datos para E2E | ✔ `qa/pg-e2e-seed.py` |
| Selección de motor en los fixtures | ✔ `make_engine()` con `KONTROL_TEST_DB_URL` |
| Siembra de la cadena organizacional | ✔ `seed_org_chain()` |
| Suite E2E del motor de aprobaciones | ✔ `e2e/approvals.spec.ts`, 11 escenarios |
| Instrumentación de axe que mide la ruta real | ✔ corregida y verificada |
| Crawler responsive que mide la ruta real | ✔ corregido y verificado |
| Pruebas de contrato de API | ✔ `test_approvals_api.py`, 11 casos |

### B · Plataforma general de QA → **Spec 054**

Matriz de navegadores en dispositivos reales (Edge, Opera, Safari en iOS) ·
pruebas de carga y estrés · dataset representativo para rendimiento · cobertura
de comportamiento de las 77 pantallas · CI con puertas · gestión de artefactos de
evidencia.

**No se construye la plataforma completa de QA dentro de 045.**
