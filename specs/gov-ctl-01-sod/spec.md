# Spec · GOV-CTL-01 Matriz de segregación de funciones (CTL-01, GOV-CTL-001)

## 1. Lo que podrá hacer Control Interno (vista del sponsor)

Cuando este ciclo termine, Control Interno podrá:
- definir qué dos acciones de un proceso de Gobierno no puede hacer la misma persona sobre el mismo acto o hallazgo (por ejemplo, «quien registra el acto no lo emite»);
- poner esa regla en vigor con su firma reforzada (MFA), desde una fecha;
- cerrarla cuando deje de aplicar, sin borrar su historia.

A partir de ahí:
- el sistema impide, antes de ejecutarla, la acción incompatible. Explica al usuario qué regla aplica, qué hizo antes y qué debe pasar: que lo haga otro usuario;
- Control Interno consulta los intentos bloqueados por regla, proceso, acción, usuario y periodo.

## 2. Fuentes y decisiones

- **Requisito:** GOV-CTL-001 «Definir matriz SoD por proceso y detectar incompatibilidades antes de ejecutar transacciones críticas», P0. Fuentes: N20 y N23.
- **Contexto en la IR:**
  - P-05: el backend decide la SoD.
  - P-09: control por diseño.
  - GOV-ORG-005: SoD configurable.
  - §12: el informe de Control Interno incluye «conflictos SoD».
- **Normativa:**
  - N20 (Normas Generales de Control Interno) exige segregación de funciones.
  - N23 (Ley contra la Corrupción) exige prevención y conflicto de interés.
  - Ninguna prescribe pares concretos de acciones.
  - GOV-PROC-017 (solicitante/adjudicador/pagador) pertenece a compras, un dominio que no existe en Gobierno: no se configura aquí.
- **Decisiones de la dueña (2026-11-04):**
  - **OD-CTL01-01:** alcance MISMO OBJETO.
  - **OD-CTL01-02:** solo bloquear, sin excepción ni override.
  - **OD-CTL01-03:** integración inicial en DOC-02 (actos) y CTL-06 (hallazgos).
  - **OD-CTL01-04:** capacidad `gobierno_sod` con `view`, `manage` y `activate`; esta última es SENSITIVE, con MFA. Las reglas vigentes no se editan: se cierran y se crea otra.

### Prueba de bloqueo material

| Pregunta | Respuesta |
|---|---|
| ¿Requiere ORG-06 (persona↔cargo)? | No. La SoD responde «¿puede este ACTOR hacer B después de haber hecho A?» y el actor es el usuario autenticado. ORG-03/ORG-07 siguen respondiendo, aparte, si el cargo tiene autoridad. |
| ¿Requiere CTL-02 (bitácora enriquecida)? | No. `AuditEvent` ya registra usuario, empresa, acción, tipo y id de entidad y momento para todas las acciones integradas. |
| ¿Basta el registro de auditoría como evidencia de la acción previa? | Sí. Cada acción integrada emite su evento con `entity_id` = id del acto o del hallazgo. |
| ¿N20/N23 imponen pares? | No. Las reglas las configura Control Interno. |
| ¿Hay operaciones reales para una E2E completa? | Sí. DOC-02 (registrar, editar, emitir, eficacia, corregir, revocar, anular) y CTL-06 (alta, recomendación, acción, plan, ejecución, avance, presentar, verificar, devolver). |
| ¿Requiere implantar la Spec 045? | No. Ver `evidence/CTL01_SPEC045_REUSE_MATRIX.md`. |

**Bloqueos:** SECURITY, DATA_INTEGRITY, LEGAL, NORMATIVE, ARCHITECTURAL, TESTABILITY y DOMAIN_DEPENDENCY, todos en 0. **MATERIAL_BLOCKER = 0.**

## 3. Catálogo de procesos y acciones (cerrado, en código)

Solo acciones de escritura ya implementadas y protegidas por la guarda. Cada entrada declara:
- **código:** el identificador estable que usan las reglas;
- **etiqueta:** el texto que ve el usuario;
- **acción de auditoría:** el evento que deja la acción y que prueba que el usuario la hizo;
- **tipo de objeto:** sobre qué entidad actúa.

**DOC-02 · Actos administrativos** (objeto `GovernmentAct`)

| Código | Etiqueta | Acción de auditoría |
|---|---|---|
| `DOC02_REGISTRAR` | Registrar el acto | `GOV_ACT_CREATED` |
| `DOC02_EDITAR` | Editar el borrador del acto | `GOV_ACT_UPDATED` |
| `DOC02_EMITIR` | Emitir el acto | `GOV_ACT_ISSUED` |
| `DOC02_EFICACIA` | Registrar la eficacia del acto | `GOV_ACT_EFFECTIVENESS_RECORDED` |
| `DOC02_CORREGIR` | Corregir el acto | `GOV_ACT_CORRECTED` |
| `DOC02_REVOCAR` | Revocar el acto | `GOV_ACT_REVOKED` |
| `DOC02_ANULAR` | Anular el acto | `GOV_ACT_NULLIFIED` |

**CTL-06 · Hallazgos** (objeto `GovernmentFinding`)

| Código | Etiqueta | Acción de auditoría |
|---|---|---|
| `CTL06_REGISTRAR` | Registrar el hallazgo | `GOV_FINDING_CREATED` |
| `CTL06_RECOMENDAR` | Añadir una recomendación | `GOV_FINDING_RECOMMENDATION_ADDED` |
| `CTL06_ACCION` | Añadir una acción correctiva | `GOV_CORRECTIVE_ACTION_ADDED` |
| `CTL06_PLAN` | Registrar el plan de acción | `GOV_FINDING_PLAN_REGISTERED` |
| `CTL06_EJECUCION` | Iniciar la ejecución | `GOV_FINDING_REMEDIATION_STARTED` |
| `CTL06_AVANCE` | Registrar un avance | `GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED` |
| `CTL06_PRESENTAR` | Presentar a verificación | `GOV_FINDING_SUBMITTED` |
| `CTL06_VERIFICAR` | Verificar y cerrar | `GOV_FINDING_VERIFIED` |
| `CTL06_DEVOLVER` | Devolver a remediación | `GOV_FINDING_RETURNED` |

`DOC02_REGISTRAR` y `CTL06_REGISTRAR` **crean** el objeto: pueden ser la acción A, pero nunca la B de una regla unidireccional, porque antes de ellas el objeto no existe.

El catálogo es extensible: un proceso futuro añade sus entradas y llama a la guarda. No se registran acciones de procesos que no existen (pagos, compras, presupuesto, bienes, contratos).

## 4. Contratos

### 4.1 Regla SoD

| Campo | Contenido |
|---|---|
| código | `SOD-AAAA-NNNN` por empresa |
| nombre | 3–200 caracteres |
| descripción / razón | 10–2000 caracteres: por qué son incompatibles |
| proceso | `DOC-02` o `CTL-06` |
| `accion_a`, `accion_b` | del catálogo del proceso; distintas |
| bidireccional | sí/no |
| alcance | `MISMO_OBJETO`, único valor en este ciclo (OD-CTL01-01) |
| vigencia | `vigente_desde` (fecha civil, desde hoy de negocio) y `vigente_hasta` opcional (≥ `vigente_desde`) |
| modo | `BLOQUEAR`, único valor (OD-CTL01-02) |
| estado | `BORRADOR` → `VIGENTE` → `CERRADA` |
| control de versión | `version`, para concurrencia optimista |
| trazabilidad | creada por/en, activada por/en, cerrada por/en, motivo de cierre |
| historia | inmutable: CREADA, EDITADA, ACTIVADA, CERRADA, con quién, cuándo y el detalle |

**Validaciones:**
- unidireccional con `accion_b` creadora → 422 `GOV_SOD_RULE_INVALID`;
- acciones fuera del catálogo del proceso → 422;
- `accion_a == accion_b` → 422.

**Transiciones:**
- **Editar:** solo en BORRADOR.
- **Activar:** BORRADOR → VIGENTE; exige `gobierno_sod:activate`.
  - Si ya hay otra regla VIGENTE del mismo proceso con el mismo par (o el par invertido cuando alguna es bidireccional) → 409 `GOV_SOD_RULE_DUPLICATE`.
- **Cerrar:** VIGENTE → CERRADA, con motivo de 10–500 caracteres.
- **Lo que no existe:** no hay reapertura ni borrado. Una regla VIGENTE no se modifica: se cierra y se crea otra.

### 4.2 Guarda preventiva

`evaluar_antes_de_actuar(db, ctx, accion, objeto_tipo, objeto_id)`, una sola función en `service_sod`.

1. **Bloqueo de fila.** La guarda **bloquea la fila del objeto** (`SELECT … FOR UPDATE` en PostgreSQL). Dos operaciones del mismo usuario sobre el mismo objeto se serializan: la segunda espera al commit de la primera y ve su evento de auditoría. Así no pueden pasar a la vez dos acciones incompatibles.
2. **Reglas aplicables.** Se toman las reglas VIGENTES de la empresa activa con `vigente_desde ≤ hoy de negocio ≤ vigente_hasta` (o sin fin) cuya acción B sea la que se intenta. Si la regla es bidireccional, también cuenta como B su acción A.
3. **Conflicto.** Para cada regla aplicable hay conflicto si existe un `AuditEvent` con:
   - la empresa de `ctx`;
   - `user_id` = el usuario actual;
   - `entity_type` y `entity_id` = el objeto;
   - `action` = el evento de auditoría de la acción previa.
4. **Si hay conflicto:**
   - **No hay mutación de negocio:** la guarda corre antes de cualquier escritura y se deshace la transacción.
   - Se registra `GOV_SOD_CONFLICT_BLOCKED` con `record_audit_after_rollback`, clase REJECTION. Sus campos son: código y versión de la regla, proceso, acción intentada, acción previa, tipo e id del objeto, id del evento previo.
   - Se responde 409 `GOV_SOD_CONFLICT`, con un mensaje de negocio y `details` seguros: `regla_codigo`, `regla_nombre`, `accion`, `accion_etiqueta`, `accion_previa`, `accion_previa_etiqueta`, `objeto_tipo`, `objeto_id` y `previa_en`.
5. **Mensaje:** «Operación bloqueada por segregación de funciones: usted ya realizó «{acción previa}» sobre este {objeto} (regla {código} · {nombre}). Esta acción debe realizarla otro usuario.»

**Orden en cada servicio integrado:**
- autenticación → permiso → empresa → módulo (dependencias de la API);
- carga del objeto y validaciones de dominio (estado, maker-checker de CTL-06, autoridad de DOC-02);
- **guarda SoD**;
- mutación;
- auditoría de éxito.

**Reglas de independencia:**
- El invariante de dominio de CTL-06 (quien presenta o registra avances no verifica) **se conserva y prevalece**: va antes y no depende de ninguna regla.
- Pasar la SoD no concede autoridad.
- Tener autoridad institucional no salta la SoD.
- El cliente no puede declarar «SoD superada»: la guarda es interna y no hay API de evaluación.

### 4.3 Evidencia y consulta de conflictos

- La evidencia es el propio `AuditEvent` `GOV_SOD_CONFLICT_BLOCKED`, sin tabla nueva: es inmutable, va por empresa y ya contiene usuario, momento y correlación.
- La consulta `GET /sod/conflictos` lo lee filtrando por la empresa activa, por regla, proceso, acción, usuario y periodo (fechas de Caracas), con paginación.
- Cada conflicto se muestra con: fecha, usuario, regla (código y nombre), proceso, acción intentada, acción previa y objeto (tipo y enlace al acto o hallazgo).

## 5. Campos (FIELD_CONTRACT)

| ID | Etiqueta | Tipo / BD / API | Req. | Validación | Visibilidad | Auditoría | Error | Ayuda |
|---|---|---|---|---|---|---|---|---|
| R01 | Código | String(20) | sistema | `SOD-AAAA-NNNN` único por empresa | view | sí | 409 GOV_SOD_RULE_CONFLICT | — |
| R02 | Nombre | String(200) | sí | 3–200 | view | sí | 422 | «Nombre corto de la incompatibilidad» |
| R03 | Razón | Text | sí | 10–2000 | view | no | 422 | «Por qué no puede hacer ambas la misma persona» |
| R04 | Proceso | String(10) | sí | `DOC-02` o `CTL-06` | view | sí | 422 | — |
| R05 | Acción A | String(32) | sí | del catálogo del proceso | view | sí | 422 GOV_SOD_RULE_INVALID | «Lo que hizo primero» |
| R06 | Acción B | String(32) | sí | del catálogo; ≠ A; no creadora si es unidireccional | view | sí | 422 GOV_SOD_RULE_INVALID | «Lo que ya no podrá hacer» |
| R07 | En ambos sentidos | Boolean | sí (por defecto no) | — | view | sí | — | «Si se marca, quien hizo B tampoco podrá hacer A» |
| R08 | Alcance | String(16) | sistema | `MISMO_OBJETO` | view | sí | — | «Sobre el mismo acto o hallazgo» |
| R09 | Vigente desde | Date | sí | ≥ hoy de negocio al crear o editar | view | sí | 422 | — |
| R10 | Vigente hasta | Date | no | ≥ vigente desde | view | sí | 422 | — |
| R11 | Estado | String(10) | sistema | BORRADOR, VIGENTE o CERRADA | view | sí | 409 GOV_SOD_RULE_INVALID_STATE | — |
| R12 | Motivo de cierre | String(500) | al cerrar | 10–500 | view | sí | 422 | — |
| R13 | Activada / cerrada por y en | — | sistema | — | view | sí | — | — |

**Filtros de conflictos:**
- regla;
- proceso;
- acción;
- usuario, por nombre exacto;
- desde y hasta.

MISSING_REQUIRED_FIELDS = 0.

## 6. Datos (migración `0072_gov_ctl01_sod`)

**`gov_sod_rules`** (empresa)
- **Columnas:** `id`, `tenant_id`, `company_id`, `codigo`, `nombre`, `descripcion`, `proceso`, `accion_a`, `accion_b`, `bidireccional`, `alcance`, `modo`, `vigente_desde`, `vigente_hasta`, `estado`, `version`, `created_by`, `activada_por`, `activada_en`, `cerrada_por`, `cerrada_en`, `motivo_cierre`, más los tiempos.
- **Restricciones:**
  - único (`company_id`, `codigo`);
  - CHECK de estado, alcance y modo;
  - CHECK `accion_a <> accion_b`;
  - CHECK `vigente_hasta IS NULL OR vigente_hasta >= vigente_desde`.
- **Disparador (PostgreSQL):** no se puede borrar.

**`gov_sod_rule_history`**
- **Columnas:** `id`, `rule_id`, `company_id`, `tipo`, `detalle` (JSON), `created_by` y los tiempos.
- **Disparadores (PostgreSQL):** rechazan UPDATE, DELETE y TRUNCATE.

**Permisos:** `gobierno_sod:view`, `manage` y `activate`, concedidos a FUNCIONAL_COMPLETO.

## 7. API (`/api/v1/gobierno/sod`; guardas: permiso → empresa → módulo `gobierno`)

| # | Método y ruta | Permiso | Respuesta | Errores |
|---|---|---|---|---|
| 1 | GET `/acciones` | sod:view | catálogo por proceso | — |
| 2 | GET `/reglas` (`estado?`, `proceso?`) | sod:view | listado con resumen (borradores, vigentes, cerradas, conflictos de los últimos 30 días) | 422 |
| 3 | POST `/reglas` | sod:manage + escritura de licencia | 201 detalle | 422 |
| 4 | GET `/reglas/{id}` | sod:view | detalle + historia | 404 GOV_SOD_RULE_NOT_FOUND |
| 5 | PATCH `/reglas/{id}` (If-Match) | sod:manage | detalle | 404, 409 STALE / INVALID_STATE, 422, 428 |
| 6 | POST `/reglas/{id}/activar` (If-Match) | sod:activate | detalle | 404, 409 STALE / INVALID_STATE / DUPLICATE, 428 |
| 7 | POST `/reglas/{id}/cerrar` (If-Match, `{motivo}`) | sod:activate | detalle | 404, 409, 422, 428 |
| 8 | GET `/conflictos` (`regla_id?`, `proceso?`, `accion?`, `usuario?`, `desde?`, `hasta?`, `pagina`, `por_pagina`) | sod:view | listado paginado | 422 |

- **Concurrencia de reglas:** `If-Match` obligatorio en las escrituras sobre la regla. Sin él, 428 `GOV_SOD_IF_MATCH_REQUIRED`; con una versión obsoleta, 409 `GOV_SOD_RULE_STALE`.
- **Guarda en negocio:** los endpoints de DOC-02 y CTL-06 no cambian su contrato. Solo pueden responder, además, 409 `GOV_SOD_CONFLICT`.

## 8. Roles, MFA y auditoría

**Permisos**
- `gobierno_sod:view` y `:manage` son STANDARD; `:activate` es SENSITIVE (MFA).
- ADMIN técnico no recibe autoridad funcional por serlo: se exige la capacidad.

**Catálogo** (`owner_spec` `gov-ctl-01`)

| Acción | Entidad | Clase | Campos |
|---|---|---|---|
| `GOV_SOD_RULE_CREATED` | `GovernmentSoDRule` | BUSINESS_COMMIT | `codigo`, `proceso`, `accion_a`, `accion_b`, `bidireccional` |
| `GOV_SOD_RULE_UPDATED` | `GovernmentSoDRule` | BUSINESS_COMMIT | `codigo`, `campos` |
| `GOV_SOD_RULE_ACTIVATED` | `GovernmentSoDRule` | BUSINESS_COMMIT | `codigo`, `vigente_desde`, `vigente_hasta` |
| `GOV_SOD_RULE_CLOSED` | `GovernmentSoDRule` | BUSINESS_COMMIT | `codigo`, `motivo` |
| `GOV_SOD_CONFLICT_BLOCKED` | `GovernmentSoDRule` | REJECTION | `regla_codigo`, `regla_version`, `proceso`, `accion`, `accion_previa`, `objeto_tipo`, `objeto_id`, `evento_previo_id` |

**Integración con la auditoría institucional:** CTL-04 incorpora el proceso «CTL-01 · Segregación de funciones» y rastrea `GovernmentSoDRule` → `/gobierno/sod/{id}`.

## 9. Menú, pantallas y estados

**Menú:** Gobierno › Segregación de funciones (`/gobierno/sod`, `view`).

| Pantalla | Ruta | Contenido | Acciones |
|---|---|---|---|
| S1 · Reglas | `/gobierno/sod` | indicadores (vigentes, borradores, cerradas, conflictos de 30 días); tabla: código, nombre, proceso, «A ⇄/→ B» con etiquetas, vigencia, estado | «Nueva regla» (`manage`), «Ver conflictos» |
| S2 · Nueva regla | `/gobierno/sod/nueva` (`manage`) | proceso; acción A y acción B, cuyos selectores dependen del proceso y excluyen la creadora como B si es unidireccional; casilla «En ambos sentidos»; nombre; razón; vigente desde y hasta | crear, cancelar |
| S3 · Regla | `/gobierno/sod/:id` | datos e historia; en BORRADOR, edición (`manage`); conflictos de esta regla | «Activar regla» (`activate`), «Cerrar regla» con motivo (`activate`) |
| S4 · Conflictos | `/gobierno/sod/conflictos` | tabla: fecha, usuario, regla, proceso, acción intentada, acción previa, objeto con enlace | filtros |

**Mensaje del conflicto en DOC-02 (ficha del acto) y CTL-06 (ficha del hallazgo):**
- ante 409 `GOV_SOD_CONFLICT` aparece una alerta persistente (`role="alert"`) «Operación bloqueada por segregación de funciones»;
- muestra la regla (código y nombre), la acción previa que la causó y el siguiente paso: «Pida a otro usuario autorizado que realice esta acción»;
- el objeto no cambia y la pantalla se recarga.

**Estados:** cargando, sin acceso, módulo no habilitado, vacío, error con reintento, no encontrada, conflicto de versión, estado inválido y duplicada.

**Accesibilidad y responsive:** caption, regiones con nombre, etiquetas «(obligatorio)» y 320 px sin desbordamiento.

## 10. Escenario de éxito para la prueba de la dueña

1. Control Interno entra en Gobierno › Segregación de funciones y crea la regla «Quien registra el acto no lo emite»: proceso DOC-02, A = Registrar el acto, B = Emitir el acto, desde hoy.
2. La activa (con MFA). La regla aparece VIGENTE, con quién la activó y cuándo.
3. Un usuario con permisos de actos registra un acto y lo completa.
4. Intenta emitirlo: aparece «Operación bloqueada por segregación de funciones…» y el acto sigue en BORRADOR.
5. Otro usuario con permiso de emisión lo emite sin problema.
6. En «Conflictos», Control Interno ve el intento bloqueado: usuario, regla, acto y fecha. Sistema › Auditoría lo registra como «Conflicto SoD bloqueado».
7. **Negativas:**
   - cerrar la regla y repetir: ya no bloquea;
   - una regla con fecha futura no bloquea hoy;
   - otra empresa no ve las reglas ni los conflictos;
   - un usuario sin `gobierno_sod:activate` no puede activar.

OWNER_UAT_SCENARIO_DEFINED = 1.
