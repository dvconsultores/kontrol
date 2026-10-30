# GOV-0-01 · Configurar el ente (ORG-01)

| Campo | Valor |
|---|---|
| Línea | KONTROL Gobierno: primer corte vertical funcional |
| Encargo | GOV-0-FUNCTIONAL-START-01 (2026-10-29). La dueña lo autoriza **solo** para este proceso |
| Proceso | **ORG-01 «Configurar el ente y su tipo»** (módulo Government Core) |
| Requisitos | **GOV-ORG-001** (P0): «Configurar tipo de ente: nacional, estadal, municipal, instituto público, servicio desconcentrado o ente descentralizado, sin compartir reglas entre tenants por defecto.» Fuentes N01, N02, N03 y N24, todas de **clase A**. Además, RNF-GOV-001/004/005/006/012/014 |
| Selección | Primer requisito de §7.1 y primero de GOV-0 (IR §14: «normativa, autoridad…») sin bloqueo material. D-GOV-01 **no** bloquea el «modelo de ente genérico» (línea base, matriz D-GOV) |
| Decisiones de la dueña | **OD-GOV0-01**: el tipo va en dos campos (nivel político-territorial y forma organizativa). **OD-GOV0-02**: el acto de creación y su documento son obligatorios para activar; se puede guardar en borrador sin ellos; tras activar, cada cambio lleva motivo y queda versionado. **OD-GOV0-03**: cada ente vive en su propia «empresa» del núcleo, 1:1, que es su contenedor técnico; el tenant agrupa los entes del organismo; la UI de Gobierno dice «ente», nunca «empresa». OQ-GAB-1 = A (perfil de Gobierno separado) |
| Estado | IMPLEMENTING |

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el responsable institucional podrá:
1. Entrar en **Gobierno › Configuración del ente**, un menú propio de Gobierno que solo aparece en una instalación de Gobierno y a quien tiene autoridad.
2. Ver que el ente todavía no está configurado y pulsar **Configurar ente**.
3. Registrar la **identificación**: denominación oficial, siglas y RIF. Registrar también la **naturaleza** del ente: nivel político-territorial, forma organizativa, órgano de adscripción, entidad federal y municipio cuando apliquen.
4. Registrar el **acto de creación**: tipo de acto, número, fecha y publicación oficial. Adjuntar su **documento** (se analiza contra virus).
5. **Guardar como borrador** y completarlo después.
6. **Activar el ente.** El sistema solo lo permite cuando está completo, y si no, explica qué falta.
7. **Registrar una modificación** del ente activo con su **motivo**. Cada cambio queda como una versión nueva sin borrar la anterior.
8. Consultar el **historial de versiones** (quién, cuándo, por qué) y, como auditor, ver en **Sistema › Auditoría** los eventos de alta, modificación y activación.

## 2. Modelo del proceso

| Elemento | Valor |
|---|---|
| Propósito | Fijar la identidad y la naturaleza jurídica del ente, que determinan sus reglas. Sin ese dato no se pueden aplicar reglas por tipo de ente sin compartirlas entre tenants |
| Dueño de negocio | Máxima autoridad del ente |
| Actor principal | Responsable de configuración institucional: un usuario con `gobierno_ente:create/edit/activate` en el ente |
| Actores secundarios | Consulta (`gobierno_ente:view`); auditor (`audit:view`) |
| Disparador | Instalación de Gobierno habilitada y ente sin configurar en el contenedor activo |
| Precondiciones | Sesión; entitlement de licencia `gobierno`; capacidad en el ente activo |
| Entradas | Identificación, naturaleza, acto de creación y documento del acto |
| Pasos | crear borrador → completar → adjuntar el acto → activar → (en adelante) modificar con motivo |
| Decisiones | El sistema decide si está completo para activar: lista cerrada de faltantes |
| Aprobaciones | No las exige GOV-ORG-001. La activación la hace quien tiene `gobierno_ente:activate` |
| Rechazos | Activación con faltantes: 422 con la lista |
| Correcciones | En borrador, edición libre; activo, solo «modificación con motivo», que crea una versión nueva |
| Cancelación / anulación / reverso | Fuera del alcance de GOV-ORG-001: la supresión de un ente es otro proceso legal. Un borrador no se borra: se corrige |
| Salidas | Ente ACTIVO con su versión 1; versiones posteriores con motivo |
| Documentos | Acto de creación (obligatorio para activar) |
| Reportes | **N/A, justificado.** GOV-ORG-001 no pide reporte y se trata de un único registro. La consulta es la ficha y su historial (IR §12 no lista reportes de configuración del ente) |
| Auditoría | `GOV_ENTITY_CREATED`, `GOV_ENTITY_UPDATED`, `GOV_ENTITY_ACTIVATED` |
| Integraciones | Ninguna |
| Estado final | ACTIVO |

### Máquina de estados

| Desde | Acción | Actor (capacidad) | Precondición | Hacia | Efecto | Documento | Auditoría | Reversible |
|---|---|---|---|---|---|---|---|---|
| — | crear | `gobierno_ente:create` | no existe ente en el contenedor | BORRADOR | versión 1 de trabajo | — | GOV_ENTITY_CREATED | no aplica |
| BORRADOR | editar | `gobierno_ente:edit` | `version` coincide | BORRADOR | version + 1 | — | GOV_ENTITY_UPDATED | sí (se edita de nuevo) |
| BORRADOR | activar | `gobierno_ente:activate` | completo + acto + documento ACTIVE vinculado + `version` coincide | ACTIVO | instantánea de versión inmutable; `activated_at`/`activated_by` | exigido | GOV_ENTITY_ACTIVATED | no (cambios solo con motivo) |
| ACTIVO | modificar | `gobierno_ente:edit` | motivo obligatorio + `version` coincide + el resultado sigue completo | ACTIVO | version + 1 e instantánea inmutable con motivo | sigue exigido | GOV_ENTITY_UPDATED (antes/después/motivo) | por otra modificación |

La máquina la impone el backend; la UI solo ofrece las acciones válidas en cada estado.

## 3. Menú y arquitectura de información

| Menú | Submenú | Ruta | Pantalla | Roles visibles | Orden | Migas |
|---|---|---|---|---|---|---|
| **Gobierno** (grupo nuevo, separado de los privados) | **Configuración del ente** | `/gobierno/ente` | `GobiernoEntePage` | quien tenga `gobierno_ente:view` en el ente activo, en una instalación con el entitlement `gobierno` | primer grupo tras «Principal» | Gobierno › Configuración del ente |

Sin el entitlement, el grupo no existe y la ruta directa muestra «módulo no habilitado». En una instalación de Gobierno, el selector de contexto de la barra superior se rotula **«Ente»** (OD-GOV0-03).

## 4. Contrato de campos

Abreviaturas: BOR = borrador, ACT = activo. «Para activar» = obligatorio para poder activar.

| Id | Etiqueta | Significado | Tipo / BD / API | Obligatorio | Validación | Edición | Ayuda |
|---|---|---|---|---|---|---|---|
| F01 | Denominación oficial | Nombre del ente según su acto de creación | texto / `String(200)` / string | sí (también en BOR) | 3–200 caracteres, sin solo espacios | BOR libre; ACT con motivo | «Tal como figura en el acto de creación» |
| F02 | Siglas | Abreviatura institucional | texto / `String(20)` / string \| null | no | ≤ 20 | igual | — |
| F03 | RIF | Registro de información fiscal del ente | texto / `String(12)` / string \| null | no | formato venezolano (`[JGVEP]-dddddddd-d`), normalizado en mayúsculas con guiones | igual | «Ej.: G-20000000-0» |
| F04 | Nivel político-territorial | Nacional, estadal o municipal (N01, N02, N24) | enum `NACIONAL\|ESTADAL\|MUNICIPAL` | para activar | catálogo cerrado | igual | — |
| F05 | Forma organizativa | Administración central, instituto público, servicio desconcentrado o ente descentralizado (N02) | enum `ADMINISTRACION_CENTRAL\|INSTITUTO_PUBLICO\|SERVICIO_DESCONCENTRADO\|ENTE_DESCENTRALIZADO` | para activar | catálogo cerrado | igual | — |
| F06 | Órgano de adscripción | Órgano al que está adscrito o del que depende (N02) | texto / `String(200)` | para activar si F05 ≠ ADMINISTRACION_CENTRAL | 3–200 | igual | «Ministerio, gobernación o alcaldía de adscripción» |
| F07 | Entidad federal | Estado (o Distrito Capital) del ámbito | texto / `String(120)` | para activar si F04 ∈ {ESTADAL, MUNICIPAL} | 2–120 | igual | — |
| F08 | Municipio | Municipio del ámbito | texto / `String(120)` | para activar si F04 = MUNICIPAL | 2–120 | igual | — |
| F09 | Tipo de acto de creación | Ley, decreto, ordenanza, resolución u otro | enum `LEY\|DECRETO\|ORDENANZA\|RESOLUCION\|OTRO` | para activar | catálogo cerrado | igual | — |
| F10 | Número del acto | Identificador del acto | texto / `String(60)` | para activar | 1–60 | igual | — |
| F11 | Fecha del acto | Fecha civil del acto (America/Caracas) | fecha / `Date` / `YYYY-MM-DD` | para activar | no futura respecto de la fecha civil de Caracas | igual | — |
| F12 | Publicación oficial | Gaceta Oficial, número y fecha, u otra publicación | texto / `String(200)` | para activar | 3–200 | igual | «Ej.: G.O. N.º 6.147 Extraordinario del 17/11/2014» |
| F13 | Documento del acto | Archivo del acto de creación (046, con análisis) | vínculo `DocumentLink(resource_type="GovernmentEntity")` a un documento `ACTIVE` | para activar | al menos un documento ACTIVE vinculado | adjuntar/sustituir según 046 | «PDF o imagen del acto publicado» |
| F14 | Motivo de la modificación | Razón del cambio de un ente activo | texto / `String(255)` | sí, en modificación de ACT | 5–255 (cabe en `audit_events.reason`, PDD-GOV0-03) | — | — |
| S1 | Estado | BORRADOR / ACTIVO | enum | — | lo fija el sistema | no editable | — |
| S2 | Versión | Contador de concurrencia y de historia | entero | — | lo fija el sistema; se envía en cada cambio | no editable | — |

Visibilidad: todos los campos los ve quien tenga `gobierno_ente:view`; los editan solo quienes tienen `edit` o `create` (en el alta).

## 5. Datos

| Tabla | Alcance | Columnas clave | Restricciones |
|---|---|---|---|
| `gov_entities` (`GovernmentEntity`) | COMPANY (contenedor del ente, OD-GOV0-03) | `company_id` (FK, **único**: un ente por contenedor), F01–F12, `status`, `version`, `activated_at`, `activated_by`, marcas de tiempo, `created_by` | CHECK de `status`, nivel, forma y tipo de acto; `version ≥ 1`; índice por `company_id` |
| `gov_entity_versions` (`GovernmentEntityVersion`) | COMPANY (`company_id` copiado) | `entity_id` (FK), `version`, `snapshot` (JSON con F01–F12 y estado), `reason`, `actor_id`, `created_at` | UNIQUE(`entity_id`, `version`); solo inserción (la API no expone UPDATE ni DELETE) |

La migración `0063` crea ambas tablas, sin relleno de datos. Clasificación: los dos modelos son **GOVERNMENT_ONLY**.

## 6. API (`/api/v1`, contexto de empresa = contenedor del ente; `require_module("gobierno")` en todas, salvo `modulo`)

| Método | Ruta | Capacidad | Petición | Respuesta | Errores | Auditoría |
|---|---|---|---|---|---|---|
| GET | `/gobierno/modulo` | sesión | — | `{"habilitado": bool}` | 401 | — |
| GET | `/gobierno/ente` | `gobierno_ente:view` | — | `EnteOut` (F01–F12, estado, versión, `faltantes_para_activar: [str]`, `documento_vinculado: bool`) | 404 `GOV_ENTITY_NOT_FOUND`, 403 | — |
| POST | `/gobierno/ente` | `gobierno_ente:create` | `EnteIn` (F01 obligatorio; resto opcional) | 201 `EnteOut` | 409 `GOV_ENTITY_ALREADY_EXISTS`, 422 | GOV_ENTITY_CREATED |
| PATCH | `/gobierno/ente` | `gobierno_ente:edit` | cabecera `If-Match: <version>` (obligatoria) + `EnteCambio` (campos parciales + `motivo`) | 200 `EnteOut` | 428 `GOV_ENTITY_IF_MATCH_REQUIRED`, 409 `GOV_ENTITY_STALE`, 422 `GOV_ENTITY_REASON_REQUIRED` (en ACT), 422 `GOV_ENTITY_INCOMPLETE` (si un ACT quedara incompleto), 422 `GOV_ENTITY_NO_CHANGES` (ningún valor cambia: no se crea una versión vacía), 404 | GOV_ENTITY_UPDATED |
| POST | `/gobierno/ente/activar` | `gobierno_ente:activate` | cabecera `If-Match: <version>` (obligatoria), cuerpo vacío | 200 `EnteOut` | 428 `GOV_ENTITY_IF_MATCH_REQUIRED`, 422 `GOV_ENTITY_INCOMPLETE` (`details.faltantes`), 409 `GOV_ENTITY_INVALID_STATE`, 409 `GOV_ENTITY_STALE`, 404 | GOV_ENTITY_ACTIVATED |
| GET | `/gobierno/ente/versiones` | `gobierno_ente:view` | — | `{"items": [VersionOut], "total": n}` | 404 | — |

En todas, sin el entitlement: 403 `MODULE_NOT_ENTITLED`. Esquemas con `extra="forbid"`; contrato estricto de consulta (ciclo 05) y fechas sin hora para F11. Un error de negocio nunca es 500.

## 7. Roles y permisos

| Actor | ver | crear | editar / modificar | activar | auditoría |
|---|---|---|---|---|---|
| Responsable de configuración institucional (FUNCIONAL_COMPLETO o rol con esas capacidades) | ✓ | ✓ | ✓ | ✓ | — |
| Consulta | ✓ | — | — | — | — |
| Auditor | — | — | — | — | ✓ (`audit:view`) |
| Administrador técnico (ADMIN) | — | — | — | — | según su rol técnico |

Las capacidades nuevas `gobierno_ente:view|create|edit|activate` son funcionales, no técnicas (GOV-CTL-004). Las aplica el backend; el frontend solo proyecta. Hay pruebas hostiles directas: sin capacidad, otro ente del mismo tenant y otro tenant.

## 8. Errores, concurrencia y numeración

- **Concurrencia:** optimista por `version`, con el patrón del proyecto `If-Match` (obligatorio, como en tareas 047). Sin `If-Match`: 428 `GOV_ENTITY_IF_MATCH_REQUIRED`. Con una versión vieja: 409 `GOV_ENTITY_STALE`. Un doble alta da 409 `GOV_ENTITY_ALREADY_EXISTS` por la restricción única; una doble activación, 409 `GOV_ENTITY_INVALID_STATE`. Cada cambio (alta, edición, activación, modificación) inserta una fila en `gov_entity_versions`; el historial es completo.
- **Numeración institucional:** no aplica (no se emiten series).
- **Errores:** estructurados (`code`, `message`, `details`) y en lenguaje institucional en la UI.

## 9. Trazabilidad

| Requisito | Regla | Datos | API | Pantalla | Prueba |
|---|---|---|---|---|---|
| GOV-ORG-001 «tipo de ente» | F04 + F05 (OD-GOV0-01) | `gov_entities.level/form` | POST/PATCH | formulario «Naturaleza» | directas, E2E |
| GOV-ORG-001 «sin compartir reglas entre tenants» | ente por contenedor y aislamiento del 07 | `company_id` único | contexto de empresa | — | hostiles (otro ente y otro tenant) |
| RNF-GOV-004 inmutabilidad | versiones inmutables, modificación con motivo | `gov_entity_versions` | PATCH en ACT | historial | directas, mutación |
| RNF-GOV-005 auditabilidad | 3 acciones catalogadas | `audit_events` | todas las escrituras | Sistema › Auditoría | directas, E2E |
| RNF-GOV-006 / 012 | autorización en backend, capacidades funcionales | permisos | `require_permission`, `require_module` | menú y botones proyectados | hostiles, mutación |
| RNF-GOV-014 accesibilidad | axe WCAG 2.1 AA, 320 px | — | — | `GobiernoEntePage` | E2E |
| OD-GOV0-02 acto obligatorio | activar exige F09–F13 | vínculo documental | activar | panel de documentos | directas, E2E, mutación |

## 10. Escenario de éxito para la prueba de la dueña

Entra en Gobierno › Configuración del ente con el usuario funcional. Configura «Alcaldía del Municipio Demo», municipal, administración central, entidad federal y municipio, y acto ordenanza N.º 1 con su publicación. El sistema no le deja activar y le dice qué falta: el documento del acto. Adjunta el PDF del acto y activa. Corrige las siglas con un motivo y ve la versión 4 en el historial (alta, edición, activación, modificación). Como auditor ve los tres tipos de evento.
