# Spec · GOV-CTL-04 Consulta y muestreo read-only del auditor (CTL-04, GOV-CTL-005) + FIND-ORG07-01

## 1. Lo que podrá hacer el auditor (vista del sponsor)

Cuando este ciclo termine, el auditor interno o externo podrá abrir **Gobierno › Auditoría institucional** y:
- ver la **población** de eventos auditados de Gobierno del ente activo (ORG-01/02/03/07, DOC-02, DOC-04), filtrada por período, proceso,
  acción, usuario y texto;
- abrir cada evento y leer su **evidencia segura** (qué cambió, por qué, quién, cuándo, en qué proceso y sobre qué objeto), ir al objeto de
  negocio si tiene permiso y abrir los documentos citados;
- **registrar una muestra** como papel de trabajo, con su criterio y su justificación, por uno de tres medios: todas las partidas (100 %),
  partidas específicas elegidas a mano, o selección aleatoria simple reproducible (semilla visible);
- reabrir las muestras guardadas, que no cambian nunca, y **exportarlas** a CSV con su definición.

Nada de lo anterior modifica la evidencia ni los registros de negocio.

## 2. Fuentes y decisiones

| Tipo | Id | Contenido |
|---|---|---|
| Requisito | GOV-CTL-005 (P0; N18, N22) | «Soportar muestreo y consulta read-only para auditor interno/externo sin alterar evidencia» (IR §7.11) |
| Actor | IR §5 | Control Interno/Auditoría: evalúa controles y actuaciones «con acceso read-only» |
| Norma | N22 · Manual de Normas y Procedimientos en materia de Auditoría de Estado (CGR) | Normas §1 «Muestra de auditoría»: el criterio de selección «quedará expresado y justificado en los papeles de trabajo»; el equipo «escogerá el método de muestreo estadístico o no estadístico». Anexo 3: medios = todas las partidas (100 %), partidas específicas (claves, representativas, informativas) o muestreo. **No prescribe un método ni fórmulas de tamaño** |
| OWNER | OD-CTL04-01 | Tres medios: TODAS, ESPECIFICA (manual), ALEATORIA (simple, reproducible, semilla visible); criterio y justificación obligatorios |
| OWNER | OD-CTL04-02 | La muestra se **guarda** como papel de trabajo inmutable (solo inserción), con referencias a los eventos, sin copiar evidencia |
| OWNER | OD-CTL04-03 | Capacidad propia `gobierno_auditoria` (`view`, `sample`); no da la bitácora privada (`audit:view`) |
| OWNER | OD-CTL04-04 | Auditor interno y externo con la misma capacidad |
| Hallazgo | FIND-ORG07-01 (MEDIUM, dueña) | DOC-02 debe validar la autoridad a la **fecha del acto**, no con las competencias de hoy |

**Prueba de bloqueo material: 0.**
- SECURITY 0: reutiliza el alcance de tenant y empresa y la proyección segura `safe_details`.
- DATA_INTEGRITY 0: la evidencia no se toca; la muestra es de solo inserción.
- LEGAL / NORMATIVE 0: la CGR deja el método al auditor.
- ARCHITECTURAL 0.
- TESTABILITY 0.
- DOMAIN_DEPENDENCY 0:
  - CTL-02 no hace falta, porque la consulta se hace sobre la bitácora append-only ya certificada; no se declara CTL-02;
  - ORG-06 no hace falta: el auditor es un usuario con la capacidad (OD-CTL04-04);
  - no hace falta un sistema de papeles de trabajo completo: la muestra con su criterio es el papel de trabajo que exige la norma para la selección.

## 3. Modelo del proceso

| Elemento | Valor |
|---|---|
| PROCESS_ID | CTL-04 · Consulta y muestreo read-only del auditor |
| Propósito | Examinar la actividad de Gobierno del ente y fijar, con criterio documentado, qué partidas se examinan |
| Actor principal | Auditor interno o externo (`gobierno_auditoria:view`; `:sample` para registrar muestras) |
| Secundarios | Control Interno; Máxima autoridad (lectura) |
| Disparador | Una actuación de auditoría o de control |
| Precondiciones | Sesión; licencia con `gobierno`; empresa (ente) activa; eventos de Gobierno en el período |
| Población | Eventos de `audit_events` del tenant y de la empresa activa cuya acción pertenece al catálogo de Gobierno (§4.1) |
| Filtros | desde/hasta (día civil Caracas), proceso, acción, usuario, texto |
| Método | TODAS · ESPECIFICA · ALEATORIA (§4.2) |
| Resultado | Muestra inmutable: definición + lista ordenada de eventos |
| Evidencia | Detalle seguro del evento, motivo, documentos citados (§4.3) |
| Rastreo | Enlace al objeto de negocio si existe y el usuario tiene su capacidad (§4.4) |
| Exportación | CSV de la muestra con su definición (auditado) |
| Estado final | No aplica: la consulta no tiene estado y la muestra nace terminada (no se edita, no se borra) |

## 4. Contratos

### 4.1 Alcance de Gobierno (GOVERNMENT_AUDIT_EVENT_SCOPE)
- Un evento es de Gobierno si su par (acción, entidad) está en el catálogo cerrado con `owner_module == "government"`.
- El proceso sale del `owner_spec` de esa entrada:

  | `owner_spec` | Proceso |
  |---|---|
  | `gov-0-01` | ORG-01 Configuración del ente |
  | `gov-0-02` | ORG-02 Estructura organizativa |
  | `gov-0-03` | ORG-03 Cargos y competencias |
  | `gov-org-07` | ORG-07 Matriz de autoridad |
  | `gov-doc-02` | DOC-02 Actos administrativos |
  | `gov-doc-04` | DOC-04 Notificaciones administrativas |
  | `gov-ctl-04` | CTL-04 Auditoría institucional |

- Siempre se aplican `tenant_id = tenant del usuario` y `company_id = empresa activa`.
- Los eventos privados, los del tenant sin empresa y los de otra empresa nunca entran. Un id ajeno responde 404.

### 4.2 Muestreo (OD-CTL04-01)
- **Población ordenada:** por `event_time` ascendente y después por `id` ascendente.
- **TODAS:** todos los eventos de la población. Población entre 1 y 2000; si no, 422 `GOV_AUDIT_POPULATION_TOO_LARGE` o `GOV_AUDIT_EMPTY_POPULATION`.
- **ESPECIFICA:** de 1 a 500 ids elegidos. Cada uno debe pertenecer a la población filtrada (si no, 422 `GOV_AUDIT_EVENT_OUTSIDE_POPULATION`). Se guardan en el orden de la población.
- **ALEATORIA:**
  - `tamano` entre 1 y min(500, población); si no, 422 `GOV_AUDIT_INVALID_SAMPLE_SIZE`;
  - `semilla` entera entre 1 y 999 999 999; si no viene, la genera el sistema;
  - selección: `random.Random(semilla).sample(range(N), tamano)` sobre la población ordenada, y después se ordena por posición.
  - **Reproducible:** los mismos filtros, la misma semilla y la misma población dan siempre la misma muestra.
  - Se guardan la semilla, el tamaño de la población y los filtros.
- **Papel de trabajo:**
  - `criterio` (10–2000) y `justificacion` (10–2000) obligatorios: Normas §1 de la CGR;
  - `titulo` (3–200).
- **Inmutable:** no hay API de cambio ni de borrado. En PostgreSQL, un disparador rechaza UPDATE y DELETE en las dos tablas, como `audit_events`.

### 4.3 Evidencia
- Del evento se muestran:
  - `motivo`;
  - `request_id`;
  - la acción con su etiqueta;
  - el proceso, la entidad y el usuario;
  - la fecha;
  - `safe_details` (antes, después, evidencia), presentado como tabla de campo y valor.
- Nunca se muestran los valores crudos `before`/`after`.
- **Documentos citados:** los valores de las claves seguras que terminan en `documento_id` o `documento_<x>_id`. Se enlazan a `/documentos/{id}`, cuya autorización es la del módulo de documentos. El enlace solo aparece con `documentos:view`.

### 4.4 Rastreo al objeto (`objeto`)
`{tipo, id, ruta, capacidad}` solo si el objeto existe en la misma empresa:

| Entidad | Ruta | Capacidad |
|---|---|---|
| GovernmentEntity | `/gobierno/ente` | `gobierno_ente:view` |
| GovernmentStructure | `/gobierno/estructura/{ejercicio}` | `gobierno_estructura:view` |
| GovernmentUnit | `/gobierno/estructura/{ejercicio}` | `gobierno_estructura:view` |
| GovernmentPosition | `/gobierno/cargos/{ejercicio}/{id}` | `gobierno_cargos:view` |
| GovernmentAct | `/gobierno/actos/{id}` | `gobierno_actos:view` |
| GovernmentNotification | `/gobierno/notificaciones/{id}` | `gobierno_notificaciones:view` |
| GovernmentAuditSample | `/gobierno/auditoria/muestras/{id}` | `gobierno_auditoria:view` |

En cualquier otro caso, `objeto` es null. El enlace se pinta solo si el usuario tiene la capacidad.

### 4.5 FIND-ORG07-01 · autoridad a la fecha del acto
- Se crea un ayudante único `competencias_en_vigor(db, cargo, fecha)` en `service_autoridad.py`. Usa la misma regla de versión en vigor que la matriz (ORG-07 §4.2).
- DOC-02, en `_validar_autoridad`, comprueba (acción, materia) contra esas competencias. Se mantienen la ventana de vigencia del cargo y el ejercicio de la fecha.
- `GET /gobierno/actos/autoridades?fecha=D` lista las competencias a la fecha D con el mismo ayudante.
- La instantánea del acto (`competencia`) no cambia al alterar después las competencias del cargo.

## 5. Campos (FIELD_CONTRACT)

| Id | Etiqueta | Fuente | Filtra | CSV |
|---|---|---|---|---|
| E01 | Fecha y hora | `event_time` (Caracas) | desde/hasta (día civil) | `fecha` |
| E02 | Proceso | catálogo `owner_spec` → §4.1 | sí | `proceso` |
| E03 | Acción | `action` + etiqueta del catálogo | sí | `accion`, `accion_etiqueta` |
| E04 | Objeto | `entity_type`, `entity_id` | — | `entidad`, `entidad_id` |
| E05 | Usuario | `users.username` del tenant | sí (exacto) | `usuario` |
| E06 | Motivo | `reason` | por texto | `motivo` |
| E07 | Evidencia | `safe_details` | — | `detalle` (JSON seguro en una celda) |
| E08 | Correlación | `request_id` | — | `request_id` |
| M01 | Título | muestra | — | cabecera |
| M02 | Criterio | muestra (10–2000) | — | cabecera |
| M03 | Justificación | muestra (10–2000) | — | cabecera |
| M04 | Método | TODAS / ESPECIFICA / ALEATORIA | — | cabecera |
| M05 | Semilla | ALEATORIA | — | cabecera |
| M06 | Tamaño de la población / de la muestra | cálculo | — | cabecera |
| M07 | Filtros de la población | definición guardada | — | cabecera |
| M08 | Registrada por / el | `created_by`, `created_at` | — | cabecera |

Texto: búsqueda sin distinguir mayúsculas en el motivo, el nombre de usuario y la etiqueta y el código de la acción.

## 6. Datos
- Sin tablas de eventos nuevas.
- Migración `0069_gov_ctl04_auditoria`:
  - `gov_audit_samples`: id, tenant_id, company_id, titulo, criterio, justificacion, metodo, semilla, tamano, poblacion, filtros (JSON), created_by, created_at;
  - `gov_audit_sample_items`: id, sample_id, company_id, audit_event_id (FK a `audit_events`), orden; UNIQUE(sample_id, audit_event_id) y UNIQUE(sample_id, orden);
  - CHECK de método y de la coherencia semilla/tamaño;
  - disparadores de inmutabilidad en PostgreSQL;
  - permisos `gobierno_auditoria:view` y `:sample`, concedidos a FUNCIONAL_COMPLETO.
- La muestra referencia eventos inmutables: no copia evidencia.

## 7. API (`/api/v1/gobierno/auditoria`; guardas: permiso → empresa → módulo `gobierno`)

| Operación | Ruta | Capacidad | Respuesta / errores |
|---|---|---|---|
| Filtros | `GET /filtros` | view | `{procesos: [{codigo, nombre}], acciones: [{codigo, entidad, etiqueta, proceso}]}` |
| Población | `GET /eventos?desde&hasta&proceso&accion&usuario&texto&pagina&por_pagina` | view | `{items: [EventoResumen], total, pagina, por_pagina}`; 422 `INVALID_DATE_RANGE`; 422 proceso/acción fuera del catálogo de Gobierno |
| Evento | `GET /eventos/{id}` | view | `EventoDetalle {…, detalle, documentos: [ids], objeto}`; 404 `GOV_AUDIT_EVENT_NOT_FOUND` (ajeno, privado o inexistente) |
| Muestras | `GET /muestras` | view | `{items: [MuestraResumen]}` de la empresa, recientes primero |
| Registrar | `POST /muestras` | sample (+ escritura permitida) | 201 `Muestra`; 422 §4.2; audita `GOV_AUDIT_SAMPLE_CREATED` |
| Muestra | `GET /muestras/{id}` | view | `Muestra {…, eventos: [EventoResumen]}`; 404 `GOV_AUDIT_SAMPLE_NOT_FOUND` |
| Exportar | `GET /muestras/{id}/exportar` | view | CSV `muestra-<codigo>.csv` (definición + partidas); audita `GOV_AUDIT_SAMPLE_EXPORTED` |

- Paginación de la población: `pagina` ≥ 1 y `por_pagina` 10–200 (por defecto 50).
- Orden: más recientes primero en la consulta; el orden de la población (§4.2) solo se usa para muestrear.

## 8. Roles, MFA y auditoría
- `gobierno_auditoria:view` es STANDARD; `gobierno_auditoria:sample` es STANDARD, porque es papel de trabajo y no toca la evidencia ni la autoridad.
- Las dos se conceden a FUNCIONAL_COMPLETO. ADMIN no las recibe por ser ADMIN.
- `audit:view` no da acceso a esta vista, y `gobierno_auditoria` no da acceso a `/audit/*`.
- Auditoría: `GOV_AUDIT_SAMPLE_CREATED` y `GOV_AUDIT_SAMPLE_EXPORTED` (entity `GovernmentAuditSample`). Consultar no se audita: eso es CTL-02, bloqueado.

## 9. Menú, pantallas y estados
- Menú: **Gobierno › Auditoría institucional** (`/gobierno/auditoria`).
- Pantalla `AuditoriaInstitucionalPage`:
  - filtros (Desde, Hasta, Proceso, Acción, Usuario, Buscar);
  - tabla de la población dentro de una región desplazable y enfocable;
  - selección de partidas (casillas) para el medio ESPECIFICA;
  - panel de evidencia del evento en la propia página (sin modal);
  - panel «Registrar muestra», solo con `:sample`;
  - pestaña o sección «Muestras guardadas».
- Ruta `/gobierno/auditoria/muestras/:muestraId`: la muestra con su definición, sus partidas, el botón «Exportar CSV» y el enlace a la evidencia de cada partida.
- Estados: cargando; módulo no habilitado; sin acceso; población vacía; fecha inválida; error de campo del registro; muestra inexistente; error de red con reintento.
- Accesible a 1280, 768 y 320 px.

## 10. Escenario de éxito para la prueba de la dueña
1. Con actividad de Gobierno en el ente (alta de un cargo y de un acto, por ejemplo), abra Gobierno › Auditoría institucional y filtre el mes por el proceso ORG-03.
2. Abra un evento: ve qué cambió, quién y cuándo, con enlace al cargo.
3. Registre una muestra ALEATORIA de 3 partidas con criterio y justificación: ve la semilla. Registre otra con la misma semilla y los mismos filtros: salen las mismas 3 partidas.
4. Registre una muestra ESPECIFICA marcando 2 partidas.
5. Exporte una muestra a CSV: trae la definición y las partidas, y queda en la auditoría.
6. Negativas:
   - un usuario sin la capacidad no ve el menú;
   - otro ente no ve los eventos;
   - no hay forma de editar ni borrar una muestra.
7. FIND-ORG07-01: un acto fechado cuando el cargo tenía la competencia se registra aunque hoy ya no la tenga; uno fechado antes de que la tuviera se rechaza.
