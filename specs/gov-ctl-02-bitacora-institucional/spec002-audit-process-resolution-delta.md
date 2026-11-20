# Delta CTL-02 · Resolución canónica de procesos (CTL-02-AUDIT-PROCESS-RESOLUTION)

**Spec dueña:** `specs/gov-ctl-02-bitacora-institucional/spec.md`. **Encargo:** «P2 — CTL-02 · Bitácora institucional con resolución canónica de procesos» (2026-11-19). **Prioridad:** P1, ciclo dirigido, sin rediseño.

## 1. Defecto vigente

- La bitácora asocia el evento a su proceso con `service_auditoria.PROCESOS`, una lista manual de 19 procesos.
- **Medición a la entrada (9f2c3dde):**
  - 125 de los 317 eventos de Gobierno del catálogo no resuelven proceso;
  - pertenecen a 20 de los 39 `owner_spec`: BUD-01/03/05/06/08/09, CNT-01/02/03/04/07/08/09, CTL-07, PROC-11, REP-03, REP-10 y TRE-03/04/09.
  - La auditoría de parametrización solo citaba parte de ellos.
- **Síntoma en pantalla:** el proceso sale vacío y la lista muestra como nombre el `owner_spec` en bruto (por ejemplo «gov-bud-08»).
- **Reproducción:** `test_ctl02_p01_defecto_bud08_sin_proceso` falla contra 9f2c3dde.
- **Misma causa en CTL-04:** su filtro por proceso rechaza con `GOV_AUDIT_INVALID_FILTER` todo proceso ausente de la lista.

## 2. Arqueología (§5)

| Elemento | Estado de entrada |
|---|---|
| CURRENT_PROCESS_CATALOG | `service_auditoria.PROCESOS` (código, nombre y `owner_spec`) |
| CURRENT_PROCESS_COUNT | 19 |
| CURRENT_EVENT_COUNT | 317 eventos de Gobierno en el catálogo cerrado de auditoría (39 `owner_spec`) |
| EVENTS_WITH_PROCESS | 192 |
| EVENTS_WITHOUT_PROCESS | 125 |
| CURRENT_RESOLUTION_FUNCTION | `service_auditoria._proceso_de(owner_spec)`. Con un `owner_spec` desconocido devuelve `("", owner_spec)` |
| Consumidores de la lista | CTL-02 (`service_bitacora._resumen`), CTL-04 (filtros, resúmenes y CSV de la muestra), CTL-07 / REP-10 (`service_sod_eventos._etiqueta_proceso`, `service_reporte_control._etiqueta_proceso`) y CTL-05 (`service_rendicion`, `api_rendicion`) |
| CURRENT_DUPLICATE_CATALOGS | 1 lista parcial compartida. Del dominio SoD (no son de auditoría): `models.PROCESOS_SOD` (restricción en la base), `CATALOGO_SOD` y `ETIQUETAS_PROCESO_SOD` en el frontend |
| Metadata explícita disponible | Cada entrada del catálogo de eventos (`AuditActionSpec`) declara `owner_module` y `owner_spec`: es el enlace explícito del evento con su Spec dueña |
| Catálogo de procesos del roadmap | `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv` (PROCESS_ID, MODULE y PROCESS_NAME, 122 procesos): es documentación y no se lee en ejecución |
| Persistencia del proceso | Ninguna. El proceso se deriva al leer; `AuditEvent` no guarda `process_id` |

## 3. Decisión de la dueña (2026-11-19)

| Id | Decisión |
|---|---|
| OD-PR-01 | **Certificar CTL-04 en este ciclo.** La autoridad única sustituye la lista de `service_auditoria`, así que el filtro de CTL-04 deja de rechazar procesos reales. Se prueba aquí (PG, mutación M9 y paso E2E) y la fila de CTL-04 del roadmap pasa a sin defecto |

## 4. Decisiones de diseño de Claude

| Id | Decisión |
|---|---|
| D-PR-01 | **Autoridad única:** `app/modules/government/procesos.py`. Ofrece `resolver_proceso(action, entity_type)`, que devuelve clase, código, nombre, módulo, nombre del módulo y fuente, y además `es_proceso`, `nombre_de`, `owner_specs_de` y `proceso_de_owner_spec`. AUDIT_PROCESS_AUTHORITIES=1 |
| D-PR-02 | **Fuente de la relación (§8, orden 1):** la metadata explícita del catálogo de eventos (`owner_spec`) más el registro de procesos, que dice a qué proceso pertenece cada Spec. No se infiere por prefijos de acción |
| D-PR-03 | **El registro vive en Gobierno, no en CTL-02.** Un proceso nuevo se registra una vez en `procesos.py`. La guardia `test_ctl02_p05_*` falla si un evento de Gobierno no resuelve, y `test_ctl02_p06_*` exige que cada proceso tenga eventos, que cada `owner_spec` tenga un solo dueño y que el código exista en la matriz del roadmap |
| D-PR-04 | **Spec que cubre varios procesos** (por ejemplo `gov-bud-01`, de BUD-01 y BUD-02): se registra en su proceso principal, el primero del título de la Spec. El catálogo de eventos solo declara la Spec dueña |
| D-PR-05 | **Clases (§9):** PROCESS_EVENT (Gobierno, con proceso), AUTH_EVENT (autenticación: sin proceso por diseño; la bitácora mantiene su etiqueta «Autenticación»), PLATFORM_EVENT (otros módulos) y SYSTEM_EVENT (par no catalogado) |
| D-PR-06 | **Módulo:** sale del prefijo del código del proceso. El nombre sigue las secciones del menú: Organización y autoridad, Expedientes y actos administrativos, Presupuesto, Contrataciones, Contratos, Tesorería, Control interno y Reportes |
| D-PR-07 | **Nombres:** los 19 procesos existentes conservan su nombre. Los nuevos usan la etiqueta del menú o de la Spec. PROC-11 conserva «Funciones incompatibles en contrataciones», que ya mostraba REP-10 |
| D-PR-08 | **Sin migración ni backfill:** el proceso se deriva al leer; los eventos append-only no se tocan. MIGRATION_REQUIRED=0 |
| D-PR-09 | **Contrato:** `BitacoraEvento` gana `modulo` y `modulo_nombre` (opcionales, aditivos). Un evento de Gobierno sin registro mostraría «Proceso no especificado», nunca el `owner_spec`. No hay rutas nuevas |
| D-PR-10 | **Consumidores:** CTL-02, CTL-04, CTL-07 y REP-10 (`service_sod_eventos`, `service_reporte_control`) y CTL-05 (`service_rendicion`, `api_rendicion`) leen la autoridad. La bitácora no tiene filtro de proceso ni exportación propia: la paridad de exportación se prueba en el CSV de la muestra de CTL-04 |

## 5. Requisitos

| Id | Requisito |
|---|---|
| FR-PR-01 | Todo evento de Gobierno del catálogo resuelve su proceso y su módulo en la bitácora (lista y detalle) |
| FR-PR-02 | BUD-06, BUD-08, CNT, CTL-07, PROC-11, REP-03, REP-10 y TRE-09 aparecen con su proceso correcto |
| FR-PR-03 | Los procesos que ya resolvían bien no cambian (ORG, DOC, PROC-03, TRE-01 y CTL-06) |
| FR-PR-04 | Autenticación, plataforma y sistema se clasifican sin proceso por diseño |
| FR-PR-05 | Una guardia falla ante un evento de Gobierno sin proceso registrado, sin depender de un recuento fijo |
| FR-PR-06 | CTL-04: el filtro y el catálogo de procesos aceptan todo proceso canónico; un código inexistente sigue dando 422 |
| FR-PR-07 | La exportación (CSV de la muestra de CTL-04) lleva el mismo proceso que la pantalla |
| FR-PR-08 | Se conservan el aislamiento de tenant y empresa, el actor, la autoridad, la unidad y la correlación |
| FR-PR-09 | Frontend: la lista muestra «Módulo · Proceso» y el detalle añade «Módulo». Pruebas: PG, mutaciones, Vitest y E2E |

## 6. Gate

BLOCKER=0 · CRITICAL=0 · CONTRADICTIONS=0 (el alcance de CTL-04 lo resolvió la dueña con OD-PR-01) · OWNER CONFLICT=0 · MATERIAL OQ=0 · UNKNOWN=0 · trazabilidad 9/9.

## 7. Observaciones fuera de alcance

- **OBS-SOD-PROCESS-LABELS:** el dominio SoD (CTL-01) mantiene su propio catálogo de procesos sujetos a reglas (`PROCESOS_SOD`, con restricción en la base) y sus etiquetas en el frontend (`ETIQUETAS_PROCESO_SOD`). Es un catálogo legítimo de otro dominio, pero sus nombres repiten los de la autoridad. Podría consumirla en un ciclo de CTL-01.
- **OBS-CTL05-PROCESO-ENTIDAD:** en los expedientes de cuenta (CTL-05), el «proceso» de una pieza candidata es el `entity_type` del evento y el filtro compara contra él, así que la lista de procesos que se ofrece no coincide con ese filtro. El comportamiento era el mismo antes del ciclo y no cambia.
