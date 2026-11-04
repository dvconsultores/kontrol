# Spec · GOV-CTL-06 Hallazgos, recomendaciones y planes de acción correctiva (CTL-06, GOV-CTL-008)

## 1. Lo que podrá hacer Control Interno (vista del sponsor)
Cuando este ciclo termine, Control Interno podrá:
- registrar un hallazgo a partir de una muestra de auditoría de CTL-04, o de forma independiente, con su condición, criterio, causa, efecto y riesgo;
- emitir una o varias recomendaciones por hallazgo;
- formular un plan de acción correctiva: una o varias acciones por recomendación, cada una con un **cargo responsable** y una **fecha objetivo**;
- registrar los avances de cada acción y adjuntar su evidencia;
- presentar el hallazgo a verificación;
- que **otro** usuario de Control Interno lo verifique y lo cierre, o lo devuelva con un motivo;
- ver de un vistazo los hallazgos abiertos, las acciones vencidas y lo pendiente de verificar;
- consultar la historia completa y exportar el plan de acción.

## 2. Fuentes y decisiones

| Fuente | Referencia | Qué aporta |
|---|---|---|
| IR Gobierno v1.0 §7.11 | GOV-CTL-008 (P1; N18, N20, N22) | «Gestionar hallazgos, recomendaciones, plan de acciones correctivas, responsable, fecha objetivo y evidencia de cierre» |
| IR §8 | Estados del dominio | Hallazgo: OPEN → ACTION_PLAN → IN_REMEDIATION → EVIDENCE_SUBMITTED → VERIFIED/CLOSED |
| IR §5 | Actores | Control Interno/Auditoría evalúa controles, actuaciones, cuentas y planes correctivos con acceso read-only a la operación |
| Biblioteca N18, N20, N22 | Controles derivados | «Responsables, actas de entrega, hallazgos y acciones correctivas»; papeles de trabajo y evidencia (N22) |
| Dueña | OD-CTL06-01 | El responsable es un **cargo VIGENTE de ORG-03**, con instantánea al asignarlo (código, denominación, unidad, ejercicio) |
| Dueña | OD-CTL06-02 | Control Interno registra avances y evidencia; verifica y cierra **otro** usuario con la capacidad de verificar (maker-checker), con MFA |
| Dueña | OD-CTL06-03 | Origen: muestra de CTL-04 (opcionalmente con sus partidas, como referencia inmutable) o independiente con origen descrito obligatorio |
| Dueña | OD-CTL06-04 | Título y condición, criterio, causa y efecto obligatorios; riesgo ALTO / MEDIO / BAJO |

**Prueba de bloqueo material**

| Pregunta | Respuesta |
|---|---|
| ¿Requiere ORG-06? | **No**, por OD-CTL06-01. El responsable es un cargo, no una persona |
| ¿Requiere CTL-02? | No. Consultar no se audita; las transiciones sí |
| ¿Puede nacer de CTL-04? | Sí, de una muestra (OD-CTL06-03) |
| ¿Hallazgo independiente? | Sí, con origen descrito (OD-CTL06-03) |
| ¿Cierra un actor distinto del responsable? | Sí: otro usuario con la capacidad de verificar, distinto de quien registró la evidencia (OD-CTL06-02) |
| ¿Requiere DOC-01 (expediente)? | No. La evidencia usa la infraestructura documental canónica (Spec 046) con el analizador |
| ¿N18/N20/N22 imponen categorías obligatorias? | No consta en la Biblioteca. Los atributos los fija OD-CTL06-04 |

MATERIAL_BLOCKER = 0 · MATERIAL_OQ = 0. OQ-ORG05-01 sigue abierta para ORG-05: OD-CTL06-01 rige solo CTL-06.

## 3. Modelo del proceso

| Desde | Acción | Capacidad | Precondición | Hasta | Auditoría |
|---|---|---|---|---|---|
| — | Registrar hallazgo | manage | origen válido (§4.1) | ABIERTO | `GOV_FINDING_CREATED` |
| ABIERTO | Añadir recomendación | manage | — | ABIERTO | `GOV_FINDING_RECOMMENDATION_ADDED` |
| ABIERTO | Añadir acción correctiva | manage | recomendación del hallazgo; cargo VIGENTE hoy; fecha objetivo ≥ hoy | ABIERTO | `GOV_CORRECTIVE_ACTION_ADDED` |
| ABIERTO | Registrar plan | manage | ≥ 1 recomendación y cada recomendación con ≥ 1 acción | PLAN_DE_ACCION | `GOV_FINDING_PLAN_REGISTERED` |
| PLAN_DE_ACCION | Iniciar ejecución | manage | — | EN_REMEDIACION | `GOV_FINDING_REMEDIATION_STARTED` |
| EN_REMEDIACION | Registrar avance | manage | porcentaje ≥ el último de la acción; si llega a 100, la acción debe tener evidencia (§4.4) | EN_REMEDIACION | `GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED` |
| EN_REMEDIACION | Presentar a verificación | manage | todas las acciones COMPLETADA | EVIDENCIA_PRESENTADA | `GOV_FINDING_SUBMITTED` |
| EVIDENCIA_PRESENTADA | Verificar y cerrar | verify (MFA) | el verificador no registró ningún avance del hallazgo ni lo presentó | CERRADO | `GOV_FINDING_VERIFIED` |
| EVIDENCIA_PRESENTADA | Devolver | verify (MFA) | la misma regla del verificador; motivo obligatorio | EN_REMEDIACION | `GOV_FINDING_RETURNED` |

- Los estados son los de la IR §8: ABIERTO = OPEN, PLAN_DE_ACCION = ACTION_PLAN, EN_REMEDIACION = IN_REMEDIATION, EVIDENCIA_PRESENTADA = EVIDENCE_SUBMITTED, CERRADO = VERIFIED/CLOSED (verificar y cerrar es un solo acto).
- **Reabrir un hallazgo CERRADO no existe:** la IR no lo define. Un hallazgo nuevo puede referenciar la misma muestra.
- El plan queda **congelado** desde PLAN_DE_ACCION. No se añaden ni se borran recomendaciones ni acciones, y nada se edita después de registrado: todo es de solo adición.
- Una devolución no borra nada. Los avances siguen y se registran otros nuevos.

## 4. Contratos

### 4.1 Origen (OD-CTL06-03)
- **MUESTRA:**
  - `muestra_id` es una muestra de CTL-04 de la misma empresa y tenant. Si no, 422 `GOV_FINDING_SOURCE_INVALID`.
  - `partidas` es opcional: de 0 a 50 `audit_event_id`, cada uno partida de esa muestra. Si no, 422 `GOV_FINDING_SOURCE_INVALID`.
  - Se guardan como referencias inmutables y no se copia evidencia.
- **INDEPENDIENTE:**
  - `origen_descripcion` obligatoria (10–500);
  - `muestra_id` y `partidas` prohibidos (422 `VALIDATION_ERROR`).
- La muestra de CTL-04 no se altera: sus disparadores siguen intactos.

### 4.2 Hallazgo (OD-CTL06-04)
- `codigo`: `HA-<año>-<nnnn>`, correlativo por empresa y año civil de Caracas.
- `titulo` (3–200); `condicion`, `criterio`, `causa`, `efecto` (10–4000 cada uno, obligatorios).
- `riesgo`: ALTO | MEDIO | BAJO.
- `estado` y `version` (concurrencia).
- `presentado_por` / `presentado_en`; `verificado_por` / `verificado_en` / `nota_verificacion`.

### 4.3 Recomendación y acción correctiva
- **Recomendación:** `orden` (1..n por hallazgo), `texto` (10–2000), `created_by` y `created_at`. Inmutable.
- **Acción:**
  - `recomendacion_id` (del mismo hallazgo; si no, 422 `GOV_FINDING_RECOMMENDATION_INVALID`);
  - `orden` (1..n por hallazgo) y `descripcion` (10–2000);
  - `cargo_id` y su instantánea `cargo_codigo`, `cargo_denominacion`, `unidad_id`, `unidad_nombre`, `ejercicio`;
  - `fecha_objetivo`, `porcentaje` (0..100) y `estado`.
- **Responsable (OD-CTL06-01):**
  - el cargo debe ser de la empresa y de una estructura VIGENTE del ejercicio en curso (año de hoy en Caracas; ORG-02/ORG-03: ejercicio = año calendario);
  - el cargo debe estar VIGENTE y tener `valid_from ≤ hoy ≤ valid_to` (o `valid_to` nulo). Si no, 422 `GOV_FINDING_RESPONSIBLE_INVALID`;
  - otra empresa u otro tenant responden igual (no se revela su existencia);
  - la instantánea no cambia aunque el cargo cambie después.
- **Fecha objetivo:** ≥ hoy (Caracas) al registrarla. Si no, 422 `GOV_FINDING_TARGET_DATE_INVALID`.
- **Estado de la acción**, derivado del último avance: 0 % → PENDIENTE; 1–99 % → EN_CURSO; 100 % → COMPLETADA.
- **Vencida** (calculado, no persistido): `fecha_objetivo < hoy (Caracas)` y estado ≠ COMPLETADA. Sigue visible mientras no se complete. En un hallazgo CERRADO todas las acciones están COMPLETADA, así que ninguna figura vencida.

### 4.4 Avance y evidencia
- **Avance:**
  - `nota` (10–2000) y `porcentaje` (0..100, ≥ el último avance de la acción; si no, 422 `GOV_FINDING_PROGRESS_INVALID`);
  - `documento_id` opcional, `created_by` y `created_at`;
  - solo se añade (disparador en PostgreSQL).
- **Evidencia:**
  - documentos del módulo canónico vinculados a la acción con `DocumentLink(resource_type="GovernmentCorrectiveAction")`, nuevo `ResourceKind` con permiso `gobierno_hallazgos:view`;
  - se suben desde `AdjuntosPanel`, con el analizador de Spec 046;
  - un `documento_id` de avance debe estar ACTIVE, ser de la empresa y estar vinculado a esa acción. Si no, 422 `GOV_FINDING_EVIDENCE_INVALID`.
- **Acción COMPLETADA:** un avance de 100 % exige al menos un documento ACTIVE vinculado a la acción (422 `GOV_FINDING_EVIDENCE_REQUIRED`).
- **Al cerrar:** `freeze_links` congela los vínculos de cada acción en la versión vigente.

### 4.5 Verificación (OD-CTL06-02)
- Verificar y devolver exigen `gobierno_hallazgos:verify` (SENSITIVE → MFA reciente, según la política vigente).
- **Maker-checker:** el verificador no puede ser `presentado_por` ni el autor de ningún avance del hallazgo. Si lo es, 409 `GOV_FINDING_SELF_VERIFICATION`.
- `nota` de verificación (10–2000) y `motivo` de devolución (10–2000) son obligatorios.

### 4.6 Concurrencia
- Toda escritura sobre un hallazgo (recomendación, acción, avance y transiciones) exige `If-Match: <version>` y la incrementa.
- Sin cabecera: 428 `GOV_FINDING_IF_MATCH_REQUIRED`. Versión obsoleta: 409 `GOV_FINDING_STALE` con `details.version_actual`. Es el patrón de `acto_para_escribir` en DOC-02, con bloqueo `FOR UPDATE`.
- Dos transiciones simultáneas: una gana y la otra recibe 409 `GOV_FINDING_STALE`. No hay actualizaciones perdidas.

### 4.7 Historia
- `gov_finding_history`: `tipo`, `estado_desde`, `estado_hasta`, `detalle` (JSON seguro), `created_by` y `created_at`.
- Una fila por cada escritura de §3. Solo se añade (disparador en PostgreSQL).
- La pantalla la muestra en orden cronológico, con su autor.

## 5. Campos (FIELD_CONTRACT)

| Id | Etiqueta | Tipo (BD / API) | Obligatorio | Validación | Editable |
|---|---|---|---|---|---|
| H01 | Código | String(20) / str | sistema | `HA-AAAA-nnnn` | nunca |
| H02 | Título | String(200) / str | sí | 3–200, recorte | al crear |
| H03 | Condición | Text / str | sí | 10–4000 | al crear |
| H04 | Criterio | Text / str | sí | 10–4000 | al crear |
| H05 | Causa | Text / str | sí | 10–4000 | al crear |
| H06 | Efecto | Text / str | sí | 10–4000 | al crear |
| H07 | Riesgo | String(5) / enum | sí | ALTO, MEDIO, BAJO | al crear |
| H08 | Origen | String(12) / enum | sí | MUESTRA, INDEPENDIENTE | al crear |
| H09 | Muestra | FK gov_audit_samples / str | si MUESTRA | misma empresa | al crear |
| H10 | Partidas | FK audit_events (tabla) / list[str] | no | ⊆ partidas de la muestra, ≤ 50 | al crear |
| H11 | Origen descrito | String(500) / str | si INDEPENDIENTE | 10–500 | al crear |
| H12 | Estado | String(24) / enum | sistema | §3 | por transición |
| R01 | Recomendación | Text / str | sí | 10–2000 | al añadir (ABIERTO) |
| A01 | Recomendación de la acción | FK / str | sí | del hallazgo | al añadir (ABIERTO) |
| A02 | Acción | Text / str | sí | 10–2000 | al añadir (ABIERTO) |
| A03 | Cargo responsable | FK gov_positions / str + instantánea | sí | §4.3 | al añadir (ABIERTO) |
| A04 | Fecha objetivo | Date / date | sí | ≥ hoy Caracas | al añadir (ABIERTO) |
| P01 | Nota del avance | Text / str | sí | 10–2000 | al añadir (EN_REMEDIACION) |
| P02 | Porcentaje | Integer / int | sí | 0–100, no decreciente | al añadir |
| P03 | Documento de evidencia | FK documents / str | no (sí para cerrar la acción, §4.4) | ACTIVE, vinculado a la acción | al añadir |
| V01 | Nota de verificación | Text / str | sí | 10–2000 | al verificar |
| V02 | Motivo de devolución | Text / str | sí | 10–2000 | al devolver |

## 6. Datos (migración `0070_gov_ctl06_hallazgos`)
- `gov_findings`:
  - id, tenant_id, company_id, codigo, titulo, condicion, criterio, causa, efecto, riesgo, origen, sample_id (FK nula), origen_descripcion, estado, version;
  - presentado_por/en, verificado_por/en, nota_verificacion, created_by, created_at, updated_at;
  - UNIQUE(company_id, codigo); CHECK de riesgo, origen, estado y coherencia del origen.
- `gov_finding_events`: id, finding_id, company_id, audit_event_id (FK `audit_events`); UNIQUE(finding_id, audit_event_id).
- `gov_finding_recommendations`: id, finding_id, company_id, orden, texto, created_by, created_at; UNIQUE(finding_id, orden).
- `gov_corrective_actions`:
  - id, finding_id, recommendation_id, company_id, orden, descripcion, position_id (FK `gov_positions`);
  - instantánea: cargo_codigo, cargo_denominacion, unidad_id, unidad_nombre, ejercicio;
  - fecha_objetivo, porcentaje, estado, created_by, created_at;
  - UNIQUE(finding_id, orden).
- `gov_corrective_action_progress`: id, action_id, company_id, nota, porcentaje, document_id (FK nula a `documents`), created_by, created_at.
- `gov_finding_history`: id, finding_id, company_id, tipo, estado_desde, estado_hasta, detalle (JSON), created_by, created_at.
- **Disparadores PostgreSQL** (rechazan UPDATE, DELETE y TRUNCATE): recomendaciones, partidas, avances e historia.
  - Hallazgo y acción admiten UPDATE: estado, versión, porcentaje y verificación.
  - Ninguno de los dos admite DELETE: el disparador lo rechaza.
- **Permisos:** `gobierno_hallazgos:view`, `:manage` y `:verify`, concedidos a FUNCIONAL_COMPLETO. ADMIN no los recibe por ser ADMIN.

## 7. API (`/api/v1/gobierno/hallazgos`; guardas: permiso → empresa → módulo `gobierno`)

| Operación | Ruta | Capacidad | Respuesta / errores |
|---|---|---|---|
| Listado | `GET /?estado&riesgo&origen&vencidas&texto&pagina&por_pagina` | view | `{items, total, pagina, por_pagina, resumen: {abiertos, pendientes_verificacion, acciones_vencidas, cerrados}}` |
| Cargos responsables | `GET /cargos-responsables` | manage | cargos que cumplen §4.3 hoy: `{id, codigo, denominacion, unidad_nombre, ejercicio}` |
| Registrar | `POST /` | manage (+ escritura permitida) | 201 Hallazgo; 422 §4.1–§4.2 |
| Detalle | `GET /{id}` | view | Hallazgo, origen (muestra con código y partidas), recomendaciones, acciones (con avances y `vencida`), historia; 404 `GOV_FINDING_NOT_FOUND` |
| Recomendación | `POST /{id}/recomendaciones` | manage, If-Match | 201; 409 `GOV_FINDING_INVALID_STATE` |
| Acción | `POST /{id}/acciones` | manage, If-Match | 201; 422 §4.3; 409 estado |
| Registrar plan | `POST /{id}/plan` | manage, If-Match | 200; 409 `GOV_FINDING_PLAN_INCOMPLETE` o estado |
| Iniciar ejecución | `POST /{id}/ejecucion` | manage, If-Match | 200; 409 estado |
| Avance | `POST /{id}/acciones/{accion_id}/avances` | manage, If-Match | 201; 422 §4.4; 409 estado; 404 acción ajena |
| Presentar | `POST /{id}/presentar` | manage, If-Match | 200; 409 `GOV_FINDING_ACTIONS_INCOMPLETE` o estado |
| Verificar y cerrar | `POST /{id}/verificar` | verify (MFA), If-Match | 200; 409 `GOV_FINDING_SELF_VERIFICATION` o estado |
| Devolver | `POST /{id}/devolver` | verify (MFA), If-Match | 200; 409 ídem |
| Exportar plan | `GET /exportar?…filtros del listado` | view | CSV `plan-acciones-<fecha>.csv` (una fila por acción); audita `GOV_FINDINGS_EXPORTED` |

- Un hallazgo de otra empresa o tenant responde 404.
- Los errores de negocio esperados nunca responden 500.
- PATCH, PUT y DELETE no existen: responden 405.

## 8. Roles, MFA y auditoría
- `gobierno_hallazgos:view` y `:manage` son STANDARD; `:verify` es SENSITIVE, porque verifica y cierra (OD-CTL06-02).
- Las tres se conceden a FUNCIONAL_COMPLETO. ADMIN no las recibe por ser ADMIN.
- Auditoría: las 10 acciones de §3 y §7 (entidad `GovernmentFinding`, `owner_spec` `gov-ctl-06`), con detalles seguros (código, estado, ids, porcentaje, cargo y fecha objetivo; nunca los textos largos).
- **CTL-04:**
  - incorpora el proceso «CTL-06 · Hallazgos y acciones correctivas» a su población;
  - rastrea `GovernmentFinding` → `/gobierno/hallazgos/{id}` (capacidad `gobierno_hallazgos:view`).

## 9. Menú, pantallas y estados
- Menú: **Gobierno › Hallazgos y acciones correctivas** (`/gobierno/hallazgos`).
- **Acceso contextual:** en la muestra de CTL-04, «Registrar hallazgo» (con `:manage`) abre `/gobierno/hallazgos/nuevo?muestra=<id>`.
- **`HallazgosPage`:**
  - resumen con 4 indicadores (abiertos, acciones vencidas, pendientes de verificación, cerrados), que actúan como filtros;
  - filtros y tabla: código, título, riesgo, estado, acciones vencidas y origen;
  - «Registrar hallazgo» y «Exportar plan (CSV)».
- **`RegistrarHallazgoPage`:** origen (muestra con sus partidas como casillas, o independiente) y los campos H02–H07.
- **`HallazgoPage`:**
  - cabecera con el estado y la siguiente acción posible;
  - secciones: Hallazgo, Origen (enlace a la muestra y a la evidencia de cada partida), Recomendaciones, Plan de acción y Verificación;
  - en Plan de acción, por cada acción: cargo, unidad, fecha objetivo, «Vencida», porcentaje, avances, evidencia con `AdjuntosPanel` y formulario de avance;
  - en Verificación: presentado por y verificado por;
  - Historia.
  - Botones según estado y capacidad: Registrar plan, Iniciar ejecución, Presentar a verificación, Verificar y cerrar, Devolver.
- Sin modales: formularios en la página.
- Estados: cargando; sin acceso; módulo no habilitado; vacío, con o sin filtros; error con reintento; no encontrado; errores de campo; conflicto de versión (recargar); autoverificación rechazada.
- Accesible a 1280, 768 y 320 px.

## 10. Escenario de éxito para la prueba de la dueña
1. En Gobierno › Auditoría institucional, abra una muestra y pulse «Registrar hallazgo».
   - Complete condición, criterio, causa, efecto y riesgo, y marque una partida.
   - Resultado: el hallazgo HA-<año>-<nnnn> queda ABIERTO.
2. Añada una recomendación y una acción con un cargo responsable y una fecha objetivo.
   - Registre el plan e inicie la ejecución.
3. Adjunte la evidencia a la acción y registre un avance del 100 %.
   - La acción queda COMPLETADA. Presente el hallazgo a verificación.
4. Con el mismo usuario, «Verificar y cerrar» se rechaza (autoverificación).
   - Con otro usuario de Control Interno, verifique y cierre: el hallazgo queda CERRADO, con su historia.
5. Gobierno › Hallazgos y acciones correctivas: el resumen y la exportación del plan reflejan el cambio.
6. Negativas:
   - sin capacidad no hay menú;
   - otro ente no ve el hallazgo;
   - sin evidencia la acción no llega al 100 %;
   - un cargo no vigente se rechaza.
