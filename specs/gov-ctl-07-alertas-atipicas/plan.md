# CTL-07 · Plan

## 1. Entrada y selección

- **Repositorio:** `ENTRY_HEAD=9566303` = origin = merge-base. Alembic `0108_gov_bud03_04_plan_fuentes`, una sola cabeza.
- **Recuento desde `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`:**
  - 122 procesos;
  - 32 en OWNER_UAT_READY;
  - 329 compuertas completas de 1273 aplicables;
  - 0 aceptados por la dueña.
- **De 1275 a 1273 compuertas:** atribuido a `f100c34` (P1). REPORTS pasa de FAIL a NOT_APPLICABLE en BUD-02 y BUD-04 (−1 cada uno). En BUD-03 el efecto neto es 0: DOCS pasa de N/A a PASS y REPORTS, de FAIL a N/A. BUD-03/04 lo justifican en su spec («los requisitos no piden reporte»). En BUD-02, el bloqueo anterior decía «pendiente decisión de la dueña». Queda señalado como **GATE-UNIVERSE-BUD02-REPORTS** para que la dueña lo confirme; P2 no lo cambia.
- **CTL-03:** OWNER_UAT_READY (`specs/gov-ctl-03-separacion-tecnica-funcional/evidence/CIERRE.md`). La pantalla, el menú, la API `GET /gobierno/control/separacion` y la E2E `gobierno-separacion.spec.ts` siguen en el HEAD. Ruta B: no se reabre.

### Candidatos (HEAD actual)

| Proceso | Prio | Estado | Bloqueo real | ¿Elegible? |
|---|---|---|---|---|
| CNT-01 | P0 | NOT_STARTED | La adjudicación no guarda monto, moneda, plazo ni fuente (OBS-PROC08-MONTO-01). La fuente presupuestaria exige BUD-08, que depende de BUD-05 | NO |
| CNT-02..08 | P0 | NOT_STARTED | CNT-01 | NO |
| CTL-08 | P0 | BLOCKED | OQ-CTL08-01 (de la dueña); maestro de proveedores, D-GOV-03 | NO |
| ORG-05 | P0 | BLOCKED | OQ-ORG05-01..03; 5 objetos sin modelo (contrato, almacén, cuenta contable, bien, caja) | NO |
| DOC-03 | P0 | BLOCKED | DOC-01 (N40); calendario sin fuente | NO |
| BUD-06/08/11/12, REQ-02 | P0 | NOT_STARTED | El presupuesto aprobado (BUD-05, de P1) | NO (excluidos) |
| REQ-01/04/05, PROC-01/04/05/12, WH-*, AST-*, TRE-03..08/10, ACC-* | P0 | NOT_STARTED o BLOCKED | N37, N15, N17, N36, N38, D-GOV-03/04/05 o dominio inexistente | NO |
| **CTL-07** | P1 | NOT_STARTED | Ninguno para duplicidad, proveedor relacionado y autoaprobación (datos reales de PROC-03, PROC-06, ORG-04, CTL-01 y PROC-11). Fraccionamiento y override se publican como no disponibles (OD-CTL07-05/06) | **SÍ** |
| TRE-09 | P1 | NOT_STARTED | Ninguna operación de Gobierno convierte moneda hoy: el requisito es condicional y no tiene consumidor | NO (sin valor visible) |
| HR-03 | P1 | NOT_STARTED | N33 (SISROE) no está fichada en el repositorio; el dominio de personal está bloqueado (D-GOV-07) | NO |
| REP-09 | P1 | NOT_STARTED | Duplica CTL-05 (precedente REP-10) | NO (reporte duplicado) |
| REP-04/05/06 | P1 | NOT_STARTED | Contratos, causado o pagos inexistentes | NO |
| PROC-09 | P1 | BLOCKED | Excluido por el encargo | NO |

`P2_VERTICAL=CTL-07`: no hay ningún P0 elegible, así que se toma el P1 de mayor valor con datos reales.

## 2. Separación de líneas de trabajo

| | P1 | P2 |
|---|---|---|
| Vertical | BUD-05 (formulación presupuestaria) | CTL-07 (alertas atípicas) |
| Ficheros esperados | `service_presupuesto*`, `models.py` (presupuesto), migración 0109, `presupuesto/*.tsx`, E2E de presupuesto | `service_alertas.py`, `schemas_alertas.py`, `api_alertas.py`, `models.py` (una clase al final), migración nueva, `control/AlertasAtipicasPage*.tsx`, E2E `gobierno-alertas.spec.ts` |
| Solape funcional | — | 0 |

**Ficheros compartidos, sin colisión semántica (la fusión es ordinaria):**

| SHARED_FILE | WHY_SHARED | SEMANTIC_COLLISION_RISK | MERGE_STRATEGY |
|---|---|---|---|
| `app/modules/government/models.py` | Las dos verticales añaden clases | Bajo (clases distintas, al final del fichero) | Fusión ordinaria; si hay conflicto, conservar las dos |
| `alembic/versions/*` | Las dos crean la siguiente revisión | Medio (dos `0109`) | Si P1 publica antes, la migración de P2, no publicada, se reencadena detrás |
| `app/main.py`, `app/shared/audit_catalog_entries.py`, `app/modules/setup/api.py`, `identity_access/mfa_policy.py` | Registro de routers, eventos y capacidades | Bajo (líneas añadidas) | Conservar las dos |
| `tests/test_audit_catalog_backup.py`, `test_delegation_ceiling.py`, `test_installation_key_reference.py`, `test_migraciones_url_porcentaje.py`, `test_spec018_migration_timestamps.py` | Recuentos y cabeza declarada | Alto en el literal (un número o un nombre) | Recalcular la suma y poner la cabeza final |
| Matrices de `docs/roadmap/government-product-completeness/` | Las dos actualizan su fila | Bajo (filas distintas) | Conservar las dos filas y recontar los totales |
| `Sidebar.tsx`, `router.tsx`, `pantallas.ts` | Una entrada cada una | Bajo | Conservar las dos |

## 3. Arquitectura y contrato

- **Servicio** `service_alertas.py`. Tres detectores sobre la sesión y `ctx`:
  - `_duplicidades` (expedientes);
  - `_proveedores_relacionados` (ofertas × funcionarios);
  - `_autoaprobaciones` (AuditEvent de las dos acciones SoD).

  `listar_alertas(db, ctx, *, tipo=None, estado=None, usuario_id)` une las derivadas con las revisiones guardadas, incluidas las que ya no se detectan (OD-CTL07-11). `revisar_alerta(db, ctx, *, user, clave, resultado, observacion)` recalcula, comprueba existencia, autorrevisión y unicidad, inserta, audita y hace commit. Una `IntegrityError` de unicidad acaba en rollback y 409.
- **Modelo** `GovernmentAtypicalAlertReview` (`gov_atypical_alert_reviews`):
  - campos: id, timestamps, created_by, company_id, `clave` String(200), `tipo` String(24), `resultado` String(24), `observacion` Text, `resumen` String(1000), `revisada_por` String(36) y `revisada_en` timestamptz;
  - `UNIQUE(company_id, clave)` y CHECK de `tipo` y `resultado`;
  - disparadores de inmutabilidad.
- **Migración** `0109_gov_ctl07_alertas` (tras `0108`): la tabla, sus índices, los disparadores y los permisos `gobierno_alertas:view` y `:review` concedidos a FUNCIONAL_COMPLETO (patrón 0070), con su downgrade.
- **API** (prefijo `/gobierno/control`, módulo `gobierno`):
  - `GET /alertas?tipo=&estado=`, con `gobierno_alertas:view`;
  - `POST /alertas/revisiones`, con `gobierno_alertas:review` (MFA por la política SENSITIVE): responde 201 con la alerta revisada.
- **Errores:**
  - 404 `GOV_ALERT_NOT_FOUND`;
  - 409 `GOV_ALERT_ALREADY_REVIEWED`;
  - 409 `GOV_ALERT_SELF_REVIEW`;
  - 422 de validación.
- **Auditoría:** `GOV_ATYPICAL_ALERT_REVIEWED` (entidad `GovernmentAtypicalAlertReview`, `gov-ctl-07`, COMPANY, SECURITY, BUSINESS_COMMIT; detalle `clave`, `resultado` y `tipo`).
- **Frontend:**
  - `AlertasAtipicasPage` en `/gobierno/control/alertas`;
  - menú «Alertas de operaciones atípicas»;
  - requisito de pantalla `gobierno_alertas:view`;
  - revisión visible solo con `gobierno_alertas:review`.

## 4. Constitution Gate

| Compuerta | Resultado |
|---|---|
| Spec dueña y autorización | Vertical de Gobierno nueva, `specs/gov-ctl-07-alertas-atipicas`, que nombra el encargo de reasignación (P2 → Gobierno) |
| Aislamiento de tenant y empresa | Todas las consultas filtran por `ctx.company_id` (y `tenant_id` en la auditoría). AC-07 |
| Seguridad | Capacidades nuevas, no técnicas; `review` con MFA; sin autorrevisión; sin PII en claro (documento enmascarado) |
| Integridad | Revisión inmutable (disparador y UNIQUE) |
| Concurrencia | La UNIQUE resuelve la carrera; prueba con `tests/concurrency.carrera` |
| Dinero y fiscal | No aplica: ningún monto (fraccionamiento queda no disponible) |
| Migración | Una revisión nueva tras `0108`; no se toca ninguna publicada |
| Motores duplicados | Ninguno: se reutilizan la auditoría, la SoD y los modelos de PROC-03, PROC-06 y ORG-04 |

`BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0 MATERIAL_OQ=0 UNKNOWN=0` → **PASS**.
