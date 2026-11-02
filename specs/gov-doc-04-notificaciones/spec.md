# Spec · GOV-DOC-04 Notificaciones administrativas con constancia de recepción por canal autorizado (DOC-04)

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el usuario podrá abrir un acto administrativo particular ya emitido, registrar a cada interesado al que hay
que notificarlo (persona natural o jurídica, con su identificación, su domicilio y, si lo tiene, su apoderado) y los recursos que
proceden contra el acto. Adjuntará el oficio de notificación con el texto íntegro y registrará la entrega personal con el recibo
firmado (quién lo recibió, con su cédula, y cuándo). Si la entrega personal no es posible, dejará constancia del intento fallido y
podrá entonces notificar por prensa, con el ejemplar del diario: el interesado queda notificado quince días después. Verá en todo
momento a quién falta notificar, y cuando todos estén notificados el acto pasará solo a «Eficaz» con la fecha que corresponde. Tendrá
una lista de notificaciones del año (pendientes, notificadas, anuladas) con exportación, y cada paso quedará en el historial y la
auditoría.

## 2. Fuentes y decisiones

| Fuente | Referencia | Uso |
|---|---|---|
| Requisito | GOV-DOC-005 (P0; N25, N29) | «Registrar notificaciones y constancia de recepción por canal autorizado» |
| Vecinos | GOV-DOC-003 (DOC-02 actos, OWNER_UAT_READY), GOV-DOC-001 (DOC-01 expediente, BLOCKED), GOV-DOC-006 (DOC-05 firma electrónica, BLOCKED), GOV-DOC-008 (búsqueda por tercero, P1), GOV-DIG-009 (publicar estados sin datos innecesarios) | fronteras |
| Norma | N25 LOPA, G.O. 2.818 Ext., 01-07-1981 (clase A; texto verificado el 2026-11-01 en venezuela.justia.com) | art. 72 (publicación de actos generales, sigue en DOC-02), 73 (notificar actos particulares con texto íntegro, recursos, términos y órganos), 74 (notificación defectuosa sin efecto), 75 (entrega en domicilio o residencia del interesado o su apoderado, recibo firmado con fecha, contenido, nombre y cédula de quien recibe), 76 (prensa cuando la personal es impracticable; notificado 15 días después; diario de la entidad o de la capital), 77 |
| Norma | N29 Decreto-Ley de Mensajes de Datos y Firmas Electrónicas, G.O. 37.148, 28-02-2001 (clase B; texto del PDF de CONATEL) | arts. 4 y 7–8: la constancia digitalizada y conservada íntegra tiene eficacia probatoria; arts. 6 y 16: la firma autógrafa del recibo solo la sustituye una firma electrónica (DOC-05) → **no** hay canal electrónico en este ciclo |
| Dueña | **OD-DOC04-01** | Canales autorizados: **personal** con recibo firmado (art. 75) y **prensa** solo tras un intento personal fallido (art. 76). Electrónico fuera hasta validación legal y DOC-05 |
| Dueña | **OD-DOC04-02** | Varios interesados: cada uno su notificación y su fecha; el acto es **eficaz cuando todos los destinatarios registrados están notificados**, con la fecha más tardía |
| Dueña | **OD-DOC04-03** | **DOC-04 es la única fuente** de la notificación de actos particulares y lleva el acto a EFICAZ; DOC-02 deja de registrar notificaciones de actos particulares y su botón abre DOC-04; la Gaceta de actos generales sigue en DOC-02 |
| Dueña | **OD-DOC04-04** | Destinatario: datos copiados en la notificación, sin maestro de terceros |

Prueba de bloqueo material (§11 del encargo): DOC-01 no hace falta (la notificación cuelga del acto de DOC-02); ORG-06 tampoco (trata
de quién ocupa cargos, no de destinatarios externos); DIG-02 no; N29 deja sin resolver el canal electrónico, que queda fuera por
OD-DOC04-01. El módulo compartido de notificaciones (047) avisa a usuarios internos y **no** se reutiliza: aquí el destinatario es
externo y la constancia es documental. `MATERIAL_BLOCKER = 0`, `MATERIAL_OQ = 0`.

## 3. Modelo del proceso

| Campo | Valor |
|---|---|
| PROCESS_ID | DOC-04 · notificación de actos administrativos particulares |
| Propósito | Que el acto particular surta efecto frente a cada interesado con constancia válida (LOPA 73–76) |
| Dueño de negocio | Unidad tramitadora del ente |
| Actor principal | Notificador (registra destinatarios, intentos, entregas y publicaciones) |
| Secundarios | Responsable de actos (DOC-02), consulta, auditor |
| Disparador | Un acto PARTICULAR pasa a EMITIDO (DOC-02) |
| Precondiciones | Ente ACTIVO; acto PARTICULAR EMITIDO; licencia `gobierno` |
| Pasos | registrar destinatario y recursos → adjuntar oficio de notificación → registrar intento personal: entregado (recibo firmado) o fallido (constancia del intento) → si fallido: nuevo intento personal o publicación en prensa (ejemplar) → notificado → cuando todos los destinatarios están notificados, el acto pasa a EFICAZ |
| Resultado | Notificaciones NOTIFICADAS con su fecha; acto EFICAZ con la fecha más tardía |

### Máquina de estados de la notificación

| Desde | Acción | Actor | Precondición | Hacia | Efecto | Documento | Efecto en el acto | Auditoría | Reversible |
|---|---|---|---|---|---|---|---|---|---|
| — | registrar destinatario | `edit` | acto PARTICULAR EMITIDO; destinatario no repetido en el acto | PENDIENTE | versión 1 | — | ninguno | GOV_NOTIFICATION_CREATED | sí (anular) |
| PENDIENTE | corregir datos | `edit` | sin intentos registrados; `If-Match` | PENDIENTE | versión + 1 con antes/después | — | ninguno | GOV_NOTIFICATION_UPDATED | — |
| PENDIENTE | registrar entrega personal | `record` | oficio vinculado; recibo vinculado; fecha ≥ fecha del acto, ≤ hoy; receptor con cédula | NOTIFICADA (fecha = fecha de entrega) | intento n (ENTREGADA); vínculos congelados | oficio + recibo | si todas NOTIFICADAS → EFICAZ | GOV_NOTIFICATION_DELIVERED (+ GOV_ACT_EFFECTIVENESS_RECORDED) | no |
| PENDIENTE | registrar intento fallido | `record` | oficio vinculado; constancia del intento vinculada; fecha válida; motivo | PENDIENTE | intento n (FALLIDA); vínculos congelados | oficio + constancia | ninguno | GOV_NOTIFICATION_ATTEMPT_FAILED | no |
| PENDIENTE | registrar publicación en prensa | `record` | ≥ 1 intento personal FALLIDO; ejemplar vinculado; diario y fecha | NOTIFICADA (fecha = publicación + 15 días) | intento n (PUBLICADA) | ejemplar | si todas NOTIFICADAS → EFICAZ | GOV_NOTIFICATION_PUBLISHED (+ GOV_ACT_EFFECTIVENESS_RECORDED) | no |
| PENDIENTE | anular | `edit` | sin entrega ni publicación; motivo; `If-Match` | ANULADA | versión + 1 | — | si las restantes ya están todas NOTIFICADAS → EFICAZ | GOV_NOTIFICATION_CANCELLED | no |
| NOTIFICADA / ANULADA | — | — | — | — | solo lectura | — | — | — | — |

Reglas: la fecha de un intento fallido no cierra nada; puede haber varios intentos personales. La prensa exige al menos un intento
personal fallido (impracticabilidad). Solo se registran intentos mientras el acto está EMITIDO. Una notificación NOTIFICADA no se
corrige ni se anula: el historial es inmutable (si hubo error, se documenta con un acto de corrección de DOC-02 o una revocación).

## 4. Contratos

### 4.1 Destinatario (OD-DOC04-04)
Persona natural (cédula) o jurídica (RIF), nombre o razón social, domicilio o residencia (art. 75), apoderado opcional (nombre y
cédula; si se registra, la entrega puede hacerse en su domicilio y el recibo puede firmarlo él). La identificación se normaliza
(mayúsculas, sin espacios ni puntos) y no se repite entre notificaciones no anuladas del mismo acto.

### 4.2 Canales (OD-DOC04-01)
| Canal | Datos | Constancia | Fecha de notificación | Fallo |
|---|---|---|---|---|
| PERSONAL entregada | fecha de entrega, nombre y cédula de quien recibe, en domicilio del interesado o apoderado | recibo firmado (PDF) | la fecha de entrega | — |
| PERSONAL fallida | fecha del intento, motivo | constancia del intento (PDF) | — | queda PENDIENTE; permite un nuevo intento o la prensa |
| PRENSA publicada | diario, edición o referencia, fecha de publicación | ejemplar del diario (PDF) | publicación + 15 días (art. 76) | — |
Electrónico: no autorizado (OD-DOC04-01). Gaceta: solo actos generales, en DOC-02.

### 4.3 Contenido (art. 73–74)
Cada notificación lleva «Recursos que proceden» (recursos, plazos y órgano ante el cual se interponen, o «No proceden recursos»,
5–2000) y el **oficio de notificación** (PDF con el texto íntegro del acto y esas menciones) vinculado antes del primer intento.

### 4.4 Constancia
Es el documento del intento (recibo, constancia de intento fallido o ejemplar) más sus datos (fecha, receptor y cédula o diario y
referencia), quién lo registró y cuándo. Vía gestión documental 046 (`GovernmentNotification`): carga, análisis, alcance, descarga;
al registrar el intento sus vínculos se congelan. No se corrige: un error se documenta con otro intento o con DOC-02.

### 4.5 Integración con DOC-02 y eficacia (OD-DOC04-02/03)
- Fuente de verdad de la notificación: DOC-04. Fuente de verdad de la eficacia del acto: DOC-02 (`fecha_eficacia`), **escrita solo
  por DOC-04** para actos PARTICULARES.
- Al pasar una notificación a NOTIFICADA (o anularse otra), si el acto tiene ≥ 1 notificación no anulada y todas están NOTIFICADAS,
  el acto pasa EMITIDO → EFICAZ en la misma transacción, con `fecha_eficacia` = la fecha de notificación más tardía y, como soporte
  determinante, el medio, la referencia, la fecha y el documento de esa notificación; versión del acto + 1 y GOV_ACT_EFFECTIVENESS_RECORDED.
- `POST /gobierno/actos/{id}/eficacia` deja de aceptar actos PARTICULARES (422 `GOV_ACT_NOTIFICATION_REQUIRED`); sigue para GENERAL (Gaceta).
- Si el acto se revoca o anula estando EMITIDO, sus notificaciones pendientes quedan sin poder registrar intentos (409 `GOV_NOTIFICATION_ACT_NOT_EMITTED`).

### 4.6 Fronteras
DOC-04 no es el motor de avisos internos (047), ni correo, ni expediente (DOC-01), ni firma (DOC-05), ni maestro de terceros. El
permiso de la aplicación (`gobierno_notificaciones:*`) no es la autoridad que dictó el acto (sigue en DOC-02).

## 5. Campos (FIELD_CONTRACT)

| ID | Rótulo | Tipo / BD | Oblig. | Validación | Editable | Ayuda |
|---|---|---|---|---|---|---|
| N01 | Acto | uuid / FK `gov_acts` | sí | PARTICULAR, EMITIDO, misma empresa | al crear | — |
| N02 | Tipo de persona | enum NATURAL/JURIDICA / `String(8)` | sí | catálogo | PENDIENTE sin intentos | — |
| N03 | Nombre o razón social | texto / `String(200)` | sí | 3–200 | ídem | «Tal como consta en su documento» |
| N04 | Cédula o RIF | texto / `String(20)` + clave normalizada | sí | V/E-dígitos (natural) o J/G/V/E/P-dígitos (jurídica), 5–20; único por acto entre no anuladas | ídem | «Ej.: V-12345678 o J-12345678-9» |
| N05 | Domicilio o residencia | texto / `String(500)` | sí | 5–500 | ídem | «Donde se entregará la notificación (LOPA art. 75)» |
| N06 | Apoderado | texto / `String(200)` | no | 3–200 si se escribe | ídem | — |
| N07 | Cédula del apoderado | texto / `String(20)` | si N06 | formato de N04 natural | ídem | — |
| N08 | Recursos que proceden | texto / `Text` | sí | 5–2000 | ídem | «Recursos, plazos y órgano ante el cual se interponen (LOPA art. 73), o "No proceden recursos"» |
| I01 | Canal | enum PERSONAL/PRENSA | sí | PRENSA solo con intento personal fallido | una vez | — |
| I02 | Resultado | enum ENTREGADA/FALLIDA (PERSONAL), PUBLICADA (PRENSA) | sí | coherente con I01 | una vez | — |
| I03 | Fecha | fecha / `Date` | sí | ≥ fecha del acto, ≤ hoy (Caracas) | una vez | — |
| I04 | Recibido por | texto / `String(200)` | si ENTREGADA | 3–200 | una vez | «Quien firmó el recibo» |
| I05 | Cédula de quien recibe | texto / `String(20)` | si ENTREGADA | formato natural | una vez | — |
| I06 | Motivo del intento fallido | texto / `String(500)` | si FALLIDA | 5–500 | una vez | «Ej.: domicilio cerrado, se negó a recibir» |
| I07 | Diario | texto / `String(120)` | si PUBLICADA | 3–120 | una vez | «Diario de mayor circulación de la entidad (LOPA art. 76)» |
| I08 | Edición o referencia | texto / `String(120)` | si PUBLICADA | 3–120 | una vez | — |
| I09 | Constancia | uuid / FK `documents` | sí | vinculada a la notificación, ACTIVA, distinta del oficio | una vez | «Recibo firmado, constancia del intento o ejemplar del diario» |
| D01 | Oficio de notificación | uuid / FK `documents` | antes del primer intento | vinculado, ACTIVO | se fija en el primer intento | «Texto íntegro del acto con los recursos» |
| M01 | Motivo (anulación) | texto / `String(255)` | al anular | 5–255 | — | «Queda en el historial» |
Derivados: estado, fecha de notificación (N09), número de intento, «se entiende notificado el …» para prensa.

## 6. Datos
- `gov_notifications`: id, company_id, act_id (FK, índice), tipo_persona, nombre, identificacion, identificacion_clave, domicilio,
  apoderado_nombre, apoderado_identificacion, recursos, documento_oficio_id (nulo hasta el primer intento), status (PENDIENTE /
  NOTIFICADA / ANULADA), fecha_notificacion, medio_notificacion, motivo_anulacion, version, creado/actualizado. CHECKs de catálogo,
  `NOTIFICADA ⇔ fecha_notificacion y medio`, `ANULADA ⇔ motivo`, apoderado completo o vacío. Único parcial `(act_id,
  identificacion_clave)` donde status ≠ ANULADA.
- `gov_notification_attempts`: id, company_id, notification_id (FK), numero, medio, resultado, fecha, receptor_nombre,
  receptor_identificacion, motivo_fallo, diario, referencia, documento_id (FK documents), registrado_por, creado_en. Sin UPDATE ni
  DELETE en el servicio. CHECKs de coherencia por resultado. Único `(notification_id, numero)`.
- `gov_notification_versions`: id, company_id, notification_id, version, status, snapshot JSON, reason, actor_id, created_at.
- Migración `0067_gov_doc04_notificaciones`; concede `gobierno_notificaciones:view/edit/record` a FUNCIONAL_COMPLETO.

## 7. API (`/api/v1/gobierno/notificaciones`; guardas: permiso → empresa → módulo `gobierno`)
| # | Método | Ruta | Capacidad | Respuesta | Errores | Auditoría |
|---|---|---|---|---|---|---|
| 1 | GET | `?anio=&estado=&acto_id=` | view | `{anio, items, total}` | 404 ente; 422 | — |
| 2 | GET | `/exportar?anio=` | view | `text/csv` `notificaciones-AAAA.csv` | 404 | GOV_NOTIFICATIONS_EXPORTED |
| 3 | POST | `` | edit | 201 `NotificacionOut` | 404 acto; 409 GOV_NOTIFICATION_RECIPIENT_DUPLICATE / GOV_NOTIFICATION_ACT_NOT_EMITTED; 422 GOV_NOTIFICATION_ACT_NOT_PARTICULAR / validación | GOV_NOTIFICATION_CREATED |
| 4 | GET | `/{id}` | view | `NotificacionOut` (con intentos) | 404 GOV_NOTIFICATION_NOT_FOUND | — |
| 5 | PATCH | `/{id}` | edit | `NotificacionOut` | 428; 409 STALE / INVALID_STATE / RECIPIENT_DUPLICATE; 422 NO_CHANGES | GOV_NOTIFICATION_UPDATED |
| 6 | POST | `/{id}/anular` `{motivo}` | edit | `NotificacionOut` | 428; 409 STALE / INVALID_STATE | GOV_NOTIFICATION_CANCELLED |
| 7 | POST | `/{id}/intentos` | record | `NotificacionOut` | 428; 409 STALE / INVALID_STATE / ACT_NOT_EMITTED; 422 GOV_NOTIFICATION_OFFICE_REQUIRED / EVIDENCE_REQUIRED / PRESS_REQUIRES_FAILED_ATTEMPT / INVALID_DOCUMENT / fecha | GOV_NOTIFICATION_DELIVERED / ATTEMPT_FAILED / PUBLISHED (+ GOV_ACT_EFFECTIVENESS_RECORDED) |
| 8 | GET | `/{id}/versiones` | view | `{items, total}` | 404 | — |
Cuerpo de 7: `{medio, resultado, fecha, documento_oficio_id, documento_id, receptor_nombre?, receptor_identificacion?, motivo_fallo?,
diario?, referencia?}`. `If-Match` (versión de la notificación) en 5–7; las escrituras bloquean la fila de la notificación y, en 6–7,
la del acto (`FOR UPDATE`). Esquemas con `extra="forbid"`; consulta estricta. `NotificacionOut`: id, acto {id, tipo,
denominacion_tipo, numero, fecha, estado}, destinatario (N02–N07), recursos, documento_oficio_id, estado, fecha_notificacion,
medio_notificacion, intentos [{numero, medio, resultado, fecha, receptor_nombre, receptor_identificacion, motivo_fallo, diario,
referencia, documento_id, registrado_por, creado_en}], puede_publicar_en_prensa, version, creado_en.
DOC-02: `POST /gobierno/actos/{id}/eficacia` → 422 `GOV_ACT_NOTIFICATION_REQUIRED` para PARTICULAR; `ActoOut` añade
`notificaciones: {total, notificadas, pendientes}` para PARTICULAR.

## 8. Roles, MFA y auditoría
| Actor | view | edit | record |
|---|---|---|---|
| Notificador (FUNCIONAL_COMPLETO) | ✓ | ✓ | ✓ |
| Preparador (view + edit) | ✓ | ✓ | — |
| Consulta | ✓ | — | — |
DOC04_MFA_MATRIX: `view` ESTÁNDAR; `edit` y `record` SENSIBLES (crean o cambian la constancia oficial y pueden volver eficaz un acto).
Auditoría (COMPANY, `entity_type="GovernmentNotification"`; exportación con `GovernmentEntity`): GOV_NOTIFICATION_CREATED,
GOV_NOTIFICATION_UPDATED, GOV_NOTIFICATION_CANCELLED, GOV_NOTIFICATION_DELIVERED, GOV_NOTIFICATION_ATTEMPT_FAILED,
GOV_NOTIFICATION_PUBLISHED, GOV_NOTIFICATIONS_EXPORTED; detalle: acto, destinatario (tipo e identificación), canal, resultado, fecha,
documento, intento, versión, motivo. La eficacia del acto audita GOV_ACT_EFFECTIVENESS_RECORDED (DOC-02).

## 9. Menú, pantallas y estados
| Menú | Ruta | Pantalla |
|---|---|---|
| Gobierno › **Notificaciones administrativas** | `/gobierno/notificaciones` | Notificaciones del año: filtros por estado y búsqueda (acto, destinatario, identificación); tabla (acto, destinatario, identificación, estado, intentos, fecha de notificación); «Exportar CSV» |
| (tabla o acto) | `/gobierno/notificaciones/:id` | Notificación: acto (enlace), destinatario, recursos, documentos (panel 046 «Oficio y constancias»), intentos, historial; acciones Corregir, Anular, Registrar entrega, Registrar intento fallido, Publicar en prensa |
| Gobierno › Actos administrativos › acto PARTICULAR EMITIDO | `/gobierno/actos/:id` | Sección «Notificaciones» con cada destinatario y su estado, «Agregar destinatario» y el resumen «Faltan N por notificar»; sustituye al panel «Registrar la notificación» |
Estados: cargando; módulo; sin acceso; ente no configurado; sin notificaciones; filtro vacío; acto no notificable; pendiente con o sin
intentos; prensa habilitada tras intento fallido; notificada («Notificada el …» / «Se entiende notificada el …»); anulada; conflicto
de versión; errores de campo y de documento. Etiquetas: «Persona natural / Persona jurídica», «Notificación personal», «Publicación en
prensa», «Entregada / Intento fallido / Publicada», «Pendiente / Notificada / Anulada».

## 10. Escenario de éxito para la prueba de la dueña
Un acto particular emitido con dos interesados: al primero se le entrega en persona (recibo firmado); al segundo, tras un intento
fallido, se le notifica por prensa. La lista muestra ambos; cuando el segundo queda notificado (publicación + 15 días), el acto pasa a
«Eficaz» con esa fecha. Un usuario de consulta ve pero no registra; otro ente no ve nada.
