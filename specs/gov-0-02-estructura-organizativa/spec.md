# Spec · GOV-0-02 Estructura organizativa por ejercicio (ORG-02)

**Estado:** DESIGNED → IMPLEMENTED en el ciclo GOV-0-FUNCTIONAL-02 · **Línea:** Gobierno (OQ-GAB-1 = A) · **Requisitos:** GOV-ORG-002 (P0), GOV-ORG-008 (P1) · **Normas:** N02, N03, N04, N21, N24 (todas clase A) · **Depende de:** ORG-01 (`GovernmentEntity`, GOV-0-01).

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el responsable de la organización institucional podrá, desde **Gobierno › Estructura organizativa**:

1. Abrir la estructura de un ejercicio (un año) para su ente, vacía o como copia de la de un ejercicio anterior.
2. Registrar las unidades del ente —órganos, unidades administrativas, unidades ejecutoras locales, dependencias, sedes y centros gestores— con su código, su nombre, de quién dependen y desde cuándo valen, y verlas como un árbol.
3. Corregir la estructura libremente mientras es un borrador, y ponerla **en vigor** adjuntando el acto que la aprueba.
4. Una vez vigente, cambiarla solo con motivo, dejando cada cambio fechado en el historial de la unidad; una unidad que deja de existir se **desactiva con fecha**, nunca se borra.
5. **Cerrar** la estructura cuando el ejercicio terminó: queda de solo lectura y ningún expediente cerrado se reescribe.
6. Descargar el listado de la estructura del ejercicio en CSV y verificar en la auditoría quién hizo cada cambio.

Nadie de otro ente u otro tenant ve ni toca esa estructura.

## 2. Fuentes y decisiones

| Tipo | Id | Contenido |
|---|---|---|
| Requisito | GOV-ORG-002 | «Modelar órgano, ente, unidad administrativa, unidad ejecutora local, dependencia, sede y centro gestor con vigencia temporal» (IR §7.1) |
| Requisito | GOV-ORG-008 | «Permitir estructuras organizativas por ejercicio sin reescribir expedientes cerrados» (IR §7.1) |
| Modelo lógico | IR §9 | `GovernmentEntity`, `GovernmentUnit` en «Organización y autoridad»; `FiscalYear` en «Contexto presupuestario» (BUD-01) |
| Norma | N03 LOAFSP (G.O. 6.210 Extr., 30-12-2015) | El ejercicio económico-financiero va del 1 de enero al 31 de diciembre (artículo 7 u 8 según la reforma: número **pendiente de verificación textual** en la Gaceta; la regla coincide en todas las fuentes) |
| Norma | N04 | «Versionar ejercicio… no hardcodear una edición anual» |
| OWNER | OD-ORG02-01 | Ejercicio = **clave de año calendario**; no se construye el `FiscalYear` presupuestario (BUD-01, bloqueado por D-GOV-02), que se enganchará al mismo año |
| OWNER | OD-ORG02-02 | **BORRADOR → VIGENTE → CERRADA**; en VIGENTE, cambios con motivo y versión fechada, desactivar en lugar de borrar; CERRADA solo lectura; copia del ejercicio anterior |
| OWNER | OD-ORG02-03 | **Acto soporte obligatorio para poner la estructura VIGENTE** |
| OWNER | OD-ORG02-04 | **Listado «Estructura del ejercicio» + exportación CSV** |
| OWNER (vigentes) | OD-GOV0-01..03, OQ-GAB-1 = A | Ente = contenedor «empresa» 1:1; perfil de Gobierno separado |

**Prueba de bloqueo material: 0.** ORG-02 no exige el `FiscalYear` presupuestario (OD-ORG02-01); D-GOV-01/02 y las validaciones legales de N07/N08/N10 son de BUD-01; T052, TOTP y el anfitrión dedicado no impiden implementar ni probar ORG-02.

## 3. Modelo del proceso

| Elemento | Valor |
|---|---|
| PROCESS_ID / NAME | ORG-02 · Estructura organizativa por ejercicio |
| Propósito | Fijar, por ejercicio, las unidades del ente y su dependencia jerárquica, con vigencia temporal, para que los procesos posteriores (cargos, responsables, presupuesto por unidad) usen la estructura del año correcto |
| Dueño de negocio | Máxima autoridad del ente |
| Actor principal | Responsable de la organización institucional (`gobierno_estructura:edit/publish/close`) |
| Secundarios | Consulta (`gobierno_estructura:view`); auditor (`audit:view`) |
| Disparador | Inicio de un ejercicio, reorganización aprobada o cierre del ejercicio |
| Precondiciones | Sesión; licencia con `gobierno`; ente configurado en el contenedor (ORG-01); para poner en vigor, ente ACTIVO |
| Pasos | abrir estructura del ejercicio (vacía o copia) → registrar unidades → adjuntar el acto → poner en vigor → (en adelante) cambios con motivo / desactivaciones fechadas → cerrar al terminar el ejercicio |
| Decisiones del sistema | Faltantes para poner en vigor (lista cerrada); integridad de la jerarquía; si el ejercicio terminó |
| Aprobaciones | La puesta en vigor exige `publish` y el acto soporte; no hay flujo de aprobación multinivel (GOV-ORG-002/008 no lo piden) |
| Correcciones | BORRADOR: edición y eliminación libres. VIGENTE: cambio con motivo (versión) o desactivación fechada |
| Anulación | No aplica: una estructura vigente no se anula; se reorganiza con cambios fechados |
| Período de efecto | El ejercicio (año); cada unidad, su `vigente_desde`–`vigente_hasta` dentro del ejercicio |
| Salidas | Estructura VIGENTE y luego CERRADA del ejercicio; historial por unidad; CSV |
| Documentos | Acto que aprueba la estructura (obligatorio para VIGENTE) |
| Reportes | «Estructura del ejercicio» (pantalla + CSV) |
| Auditoría | 8 acciones (§9) |
| Estado final | CERRADA |

### Máquina de estados de la estructura

| Desde | Acción | Capacidad | Precondición | Hacia | Efecto | Auditoría | Reversible |
|---|---|---|---|---|---|---|---|
| — | abrir | `edit` | ente configurado; no existe estructura de ese ejercicio | BORRADOR | versión 1; si se copia, unidades ACTIVAS del origen | GOV_STRUCTURE_CREATED | no aplica |
| BORRADOR | poner en vigor | `publish` | ≥ 1 unidad ACTIVA; acto ACTIVE vinculado; ente ACTIVO; `If-Match` | VIGENTE | `publicada_en/por`; versión + 1 | GOV_STRUCTURE_PUBLISHED | no |
| VIGENTE | cerrar | `close` | el ejercicio terminó (año < año civil de Caracas); `If-Match` | CERRADA | `cerrada_en/por`; versión + 1; todo pasa a solo lectura | GOV_STRUCTURE_CLOSED | no |

### Ciclo de la unidad (dentro de la estructura)

| Estado estructura | Crear | Editar | Mover | Cambiar código / vigente_desde | Desactivar | Eliminar | Motivo |
|---|---|---|---|---|---|---|---|
| BORRADOR | sí | sí | sí | sí | no (se elimina) | sí, sin subordinadas | opcional |
| VIGENTE | sí | sí | sí | **no** | sí, fecha + sin subordinadas activas | **no** | **obligatorio** (5–255) |
| CERRADA | no | no | no | no | no | no | — |

## 4. Contrato del ejercicio (EXERCISE_CONTRACT)

- Identidad: entero **AAAA** (2000 ≤ AAAA ≤ año civil de Caracas + 1): se puede preparar la del año siguiente.
- Período: 1 de enero – 31 de diciembre de AAAA (N03). Sin calendario, moneda, clasificadores ni estado presupuestario (son de BUD-01).
- Una estructura por ente y ejercicio (único). Puede haber estructuras de varios ejercicios a la vez (p. ej., la vigente del año y el borrador del siguiente).
- «Terminado» = AAAA < año civil de Caracas (`hoy_de_negocio().year`).
- Copia: al abrir el ejercicio B se puede copiar el A (A ≠ B, de la misma estructura del mismo ente, VIGENTE o CERRADA): se copian las unidades ACTIVAS con el mismo código, nombre, tipo y jerarquía; `vigente_desde` = 1 de enero de B.
- Historia inmutable: CERRADA no admite escritura; VIGENTE no admite borrado ni reescritura de código o inicio de vigencia.

## 5. Contrato de la estructura y de la unidad (STRUCTURE / HIERARCHY)

Tipos de unidad (GOV-ORG-002, catálogo cerrado): `ORGANO`, `UNIDAD_ADMINISTRATIVA`, `UNIDAD_EJECUTORA_LOCAL`, `DEPENDENCIA`, `SEDE`, `CENTRO_GESTOR`. El **ente** de GOV-ORG-002 es la raíz implícita: el `GovernmentEntity` de ORG-01. Una unidad sin unidad superior depende directamente del ente.

Reglas de jerarquía (el backend las impone; la BD las que puede):
- Unidad superior de la **misma estructura** (FK compuesta `(structure_id, parent_id)` → `(structure_id, id)`): ni de otro ente ni de otro ejercicio.
- **Sin autorreferencia** (CHECK en BD y backend) y **sin ciclos** (backend: recorrido de ancestros con la fila de la estructura bloqueada).
- La unidad superior debe estar ACTIVA.
- Una unidad con subordinadas no se elimina (BORRADOR) ni se desactiva si alguna sigue ACTIVA (VIGENTE).
- Varias raíces permitidas (todas dependen del ente). Sin niveles fijos por tipo: la norma no los fija (no se inventan).

## 6. Contrato de campos

| Id | Etiqueta | Significado | Tipo / BD / API | Oblig. | Validación | Edición | Ayuda |
|---|---|---|---|---|---|---|---|
| S01 | Ejercicio | Año del ejercicio | entero / `Integer` / int | sí al abrir | 2000 ≤ AAAA ≤ año de Caracas + 1; único por ente | inmutable | «Año del ejercicio (1 de enero a 31 de diciembre)» |
| S02 | Copiar del ejercicio | Ejercicio de origen | entero / `Integer` nulo / int\|null | no | existente, distinto, VIGENTE o CERRADA | solo al abrir | «Opcional: parte de la estructura de otro ejercicio» |
| S03 | Estado | BORRADOR / VIGENTE / CERRADA | enum | — | lo fija el sistema | no | — |
| S04 | Versión | Concurrencia de la estructura | entero | — | sistema; `If-Match` | no | — |
| S05 | Acto que aprueba la estructura | Documento 046 vinculado | `DocumentLink(resource_type="GovernmentStructure")` | para VIGENTE | ≥ 1 documento ACTIVE de la misma empresa | adjuntar según 046 | «Resolución o reglamento interno que aprueba la estructura» |
| U01 | Código | Identificador de la unidad en la estructura | texto / `String(30)` | sí | `^[A-Z0-9][A-Z0-9.-]{0,29}$` tras mayúsculas; único en la estructura | BORRADOR | «Ej.: DA-01» |
| U02 | Denominación | Nombre oficial de la unidad | texto / `String(200)` | sí | 3–200, no solo espacios | BORRADOR libre; VIGENTE con motivo | — |
| U03 | Tipo de unidad | Clase según GOV-ORG-002 | enum (6) | sí | catálogo cerrado | ídem | — |
| U04 | Unidad superior | De quién depende (vacío = del ente) | uuid \| null | no | misma estructura, ACTIVA, sin ciclo, no ella misma | ídem (mover) | «Déjelo vacío si depende directamente del ente» |
| U05 | Vigente desde | Inicio de vigencia | fecha / `Date` | sí | dentro del ejercicio; sin hora | BORRADOR | — |
| U06 | Vigente hasta | Fin de vigencia | fecha / `Date` nulo | — | la fija la desactivación: ≥ U05, dentro del ejercicio | solo al desactivar | — |
| U07 | Estado | ACTIVA / INACTIVA | enum | — | sistema | no | — |
| U08 | Motivo | Razón del cambio en una estructura VIGENTE | texto / `String(255)` | sí en VIGENTE | 5–255 | — | «Queda en el historial y en la auditoría» |
| U09 | Versión | Concurrencia de la unidad | entero | — | `If-Match` | no | — |

## 7. Datos

| Tabla | Alcance | Columnas clave | Restricciones |
|---|---|---|---|
| `gov_structures` (`GovernmentStructure`) | COMPANY | `company_id`, `entity_id` (FK `gov_entities`), `exercise`, `status`, `version`, `copied_from_exercise`, `published_at/by`, `closed_at/by` | UNIQUE(`company_id`, `exercise`); CHECK estado, `version ≥ 1`, `exercise` 2000–2100 |
| `gov_units` (`GovernmentUnit`) | COMPANY | `structure_id`, `company_id`, `code`, `name`, `unit_type`, `parent_id`, `status`, `valid_from`, `valid_to`, `version` | UNIQUE(`structure_id`, `code`); UNIQUE(`structure_id`, `id`); FK compuesta del padre a la misma estructura; CHECK tipo, estado, `parent_id <> id`, `valid_to ≥ valid_from`, INACTIVA ⇔ `valid_to` |
| `gov_unit_versions` (`GovernmentUnitVersion`) | COMPANY | `unit_id`, `structure_id`, `company_id`, `version`, `snapshot`, `reason`, `actor_id` | UNIQUE(`unit_id`, `version`); solo inserción (en BORRADOR, eliminar una unidad elimina su historia de borrador) |

Migración `0064`, sin relleno de datos; concede `gobierno_estructura:*` a FUNCIONAL_COMPLETO en instalaciones existentes.

## 8. API (`/api/v1`; guardas: permiso → contexto de empresa → módulo `gobierno`)

| # | Método | Ruta | Capacidad | Respuesta | Errores | Auditoría |
|---|---|---|---|---|---|---|
| 1 | GET | `/gobierno/estructuras` | view | `{items: [EstructuraResumen], total}` | 404 `GOV_ENTITY_NOT_FOUND` | — |
| 2 | POST | `/gobierno/estructuras` | edit | 201 `EstructuraOut` | 404 ente; 409 `GOV_STRUCTURE_ALREADY_EXISTS`; 422 `GOV_STRUCTURE_COPY_SOURCE_INVALID`; 422 validación | GOV_STRUCTURE_CREATED |
| 3 | GET | `/gobierno/estructuras/{ejercicio}` | view | `EstructuraOut` (con unidades y faltantes) | 404 `GOV_STRUCTURE_NOT_FOUND` | — |
| 4 | POST | `…/{ejercicio}/publicar` | publish | `EstructuraOut` | 428; 409 `GOV_STRUCTURE_STALE`; 409 `GOV_STRUCTURE_INVALID_STATE`; 422 `GOV_STRUCTURE_INCOMPLETE` (`details.faltantes`) | GOV_STRUCTURE_PUBLISHED |
| 5 | POST | `…/{ejercicio}/cerrar` | close | `EstructuraOut` | 428; 409 STALE / INVALID_STATE; 422 `GOV_STRUCTURE_EXERCISE_NOT_ENDED` | GOV_STRUCTURE_CLOSED |
| 6 | GET | `…/{ejercicio}/exportar` | view | `text/csv` (adjunto) | 404 | GOV_STRUCTURE_EXPORTED |
| 7 | POST | `…/{ejercicio}/unidades` | edit | 201 `UnidadOut` | 409 `GOV_STRUCTURE_CLOSED`; 409 `GOV_UNIT_CODE_DUPLICATE`; 422 `GOV_UNIT_INVALID_PARENT`; 422 `GOV_UNIT_REASON_REQUIRED`; 422 validación | GOV_UNIT_CREATED |
| 8 | PATCH | `…/unidades/{unidad_id}` | edit | `UnidadOut` | 428; 409 `GOV_UNIT_STALE`; 409 CLOSED; 404 `GOV_UNIT_NOT_FOUND`; 422 `GOV_UNIT_HIERARCHY_CYCLE` / INVALID_PARENT / REASON_REQUIRED / `GOV_UNIT_FIELD_LOCKED` / `GOV_UNIT_NO_CHANGES`; 409 CODE_DUPLICATE | GOV_UNIT_UPDATED |
| 9 | POST | `…/unidades/{unidad_id}/desactivar` | edit | `UnidadOut` | 428; 409 STALE; 409 `GOV_STRUCTURE_INVALID_STATE` (no VIGENTE); 409 `GOV_UNIT_HAS_ACTIVE_CHILDREN`; 409 `GOV_UNIT_INVALID_STATE` (ya inactiva); 422 fecha / motivo | GOV_UNIT_DEACTIVATED |
| 10 | DELETE | `…/unidades/{unidad_id}` | edit | 204 | 428; 409 STALE; 409 INVALID_STATE (no BORRADOR); 409 `GOV_UNIT_HAS_CHILDREN` | GOV_UNIT_DELETED |
| 11 | GET | `…/unidades/{unidad_id}/versiones` | view | `{items: [VersionUnidad], total}` | 404 | — |

Esquemas con `extra="forbid"`; fechas sin hora; `If-Match` obligatorio en 4, 5, 8, 9 y 10 (428 sin él). Una unidad ajena o inexistente responde lo mismo: 404 `GOV_UNIT_NOT_FOUND`. Un error de negocio nunca es 500.

## 9. Roles, MFA y auditoría

| Actor | view | edit | publish | close | audit |
|---|---|---|---|---|---|
| Responsable de la organización (FUNCIONAL_COMPLETO o rol con esas capacidades) | ✓ | ✓ | ✓ | ✓ | — |
| Consulta | ✓ | — | — | — | — |
| Auditor | — | — | — | — | `audit:view` |
| ADMIN técnico | — | — | — | — | según su rol |

MFA (ORG02_MFA_MATRIX): `view` ESTÁNDAR; `edit`, `publish`, `close` SENSIBLES: definen las unidades sobre las que se asignará autoridad (GOV-ORG-003/007), como `organization:edit` y las escrituras del ente.

Auditoría (catálogo cerrado, ámbito COMPANY): `GOV_STRUCTURE_CREATED`, `GOV_STRUCTURE_PUBLISHED`, `GOV_STRUCTURE_CLOSED`, `GOV_STRUCTURE_EXPORTED` (`GovernmentStructure`); `GOV_UNIT_CREATED`, `GOV_UNIT_UPDATED` (con motivo), `GOV_UNIT_DEACTIVATED` (con motivo y fecha), `GOV_UNIT_DELETED` (`GovernmentUnit`). Contexto: actor, tenant, empresa, ejercicio, recurso, antes/después.

## 10. Menú, pantallas y estados

| Menú | Ruta | Pantalla |
|---|---|---|
| Gobierno › **Estructura organizativa** | `/gobierno/estructura` | Ejercicios: lista + «Abrir estructura de un ejercicio» |
| (desde la lista) | `/gobierno/estructura/:ejercicio` | Estructura del ejercicio: requisitos, árbol de unidades con búsqueda y filtros, formulario de unidad, desactivación, eliminación, historial, acto, poner en vigor, cerrar, exportar |

Estados de UI: módulo no habilitado; sin acceso; **ente no configurado** (enlace a Configuración del ente); sin estructuras; estructura sin unidades; borrador con faltantes; vigente; cerrada (solo lectura); conflicto de versión; errores de jerarquía, código duplicado, motivo, campo bloqueado; error de red con reintento.

**GOV0-UI-01 (corrección acotada):** en una instalación con el módulo de Gobierno, la compuerta de contexto que se muestra en las rutas `/gobierno/*` dice «ente» («Seleccione un ente», «No tiene entes asignados»…). Las rutas privadas conservan «empresa».

## 11. Escenario de éxito para la prueba de la dueña

Con el ente activo de ORG-01, entra en Gobierno › Estructura organizativa y abre la estructura del ejercicio actual. Registra «Despacho» (órgano), «Dirección de Administración» bajo el despacho y «Sede principal». El sistema no le deja poner en vigor sin el acto: lo adjunta y la pone en vigor. Cambia el nombre de una dirección con motivo y ve la versión en su historial; desactiva una unidad con fecha. Descarga el CSV. Abre el ejercicio siguiente como copia y ve las mismas unidades activas. En Auditoría ve los eventos.
