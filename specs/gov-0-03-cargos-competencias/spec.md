# Spec · GOV-0-03 Cargos con competencias y límites de firma/aprobación (ORG-03)

**Estado:** DESIGNED → IMPLEMENTED en el ciclo GOV-0-FUNCTIONAL-03 · **Línea:** Gobierno (OQ-GAB-1 = A) · **Requisito:** GOV-ORG-003 (P0) · **Normas:** N02, N20, N23 (clase A) · **Depende de:** ORG-01 (`GovernmentEntity`), ORG-02 (`GovernmentStructure`, `GovernmentUnit`).

## 1. Lo que podrá hacer el usuario (vista del sponsor)

Cuando este ciclo termine, el responsable de la organización institucional podrá, desde **Gobierno › Cargos y competencias**:

1. Elegir el ejercicio y registrar los **cargos** del ente en las unidades de su estructura (p. ej. «Director de Administración» en la Dirección de Administración).
2. Decir **qué puede hacer cada cargo**: por cada competencia, la acción (solicitar, comprometer, causar, ordenar el pago, pagar, registrar, custodiar, aprobar, auditar o firmar), la materia (presupuesto, contrataciones, tesorería, contabilidad, bienes públicos o expediente) y **hasta cuánto**: sin límite o un monto máximo por operación en bolívares, dólares o euros.
3. Adjuntar el **acto** que fija esas competencias y **poner el cargo en vigor**; sin acto, sin competencias o con la estructura del ejercicio sin vigencia, el sistema no lo deja.
4. Una vez vigente, cambiar sus competencias o límites solo con motivo y con la autoridad para poner cargos en vigor; cada cambio queda fechado en el historial del cargo. Un cargo que deja de existir se **desactiva con fecha**, nunca se borra.
5. Al abrir la estructura del ejercicio siguiente como copia, los cargos vigentes llegan en borrador con sus competencias; al cerrar el ejercicio, sus cargos quedan de solo lectura.
6. Descargar el listado de cargos y competencias del ejercicio en CSV y ver en la auditoría quién otorgó, cambió o retiró cada competencia.

La autoridad es del **cargo**, no de una persona (GOV-ORG-003: «no solo por usuario nominal»). Quién ocupa cada cargo, las delegaciones y suplencias y la matriz de quién puede qué llegan en otros procesos.

## 2. Fuentes y decisiones

| Tipo | Id | Contenido |
|---|---|---|
| Requisito | GOV-ORG-003 | «Asignar competencias y límites de firma/aprobación por cargo y no solo por usuario nominal» (IR §7.1) |
| Requisito (catálogo de acciones) | GOV-ORG-010 | «…quién puede solicitar, comprometer, causar, ordenar, pagar, registrar, custodiar, aprobar y auditar» (IR §7.1); la **matriz** es ORG-07, aquí solo se toma el vocabulario |
| Arquitectura | IR §6, §9 | Contextos (Budget, Procurement, Treasury & Accounting, Public Assets, Records & Audit); entidad `AuthorityGrant` en «Organización y autoridad» |
| Arquitectura | government-architecture-baseline §Organization Model | `AuthorityGrant` = cargo → competencia, límite, vigencia, acto |
| Principios | IR P-05, P-06, P-07 · RNF-GOV-002/004/005/006/012 | Backend decide; historia no destructiva; Decimal; auditoría completa; mínimo privilegio |
| Biblioteca normativa | §2, §6, §7 | Delegaciones y niveles de aprobación son normativa **local** del ente; el paquete de cada ente custodia «firmas autorizadas y límites»; los umbrales no se codifican como constantes |
| Norma | N02 (LOAP, G.O. 6.147 Extr.) | Órganos, competencias, delegación: «modelar competencia/autoridad y ámbito del ente» (control derivado de la Biblioteca) |
| Norma | N20 (NGCI, G.O. 40.851) · N23 (Ley contra la Corrupción, G.O. 6.699 Extr.) | Segregación, responsabilidades, trazabilidad (controles derivados de la Biblioteca) |
| OWNER | OD-ORG03-01 | Cargo **por ejercicio**, en una unidad de la estructura de ORG-02; copiar la estructura copia sus cargos vigentes en borrador; ejercicio cerrado congela sus cargos |
| OWNER | OD-ORG03-02 | Competencia = **acción × materia** (10 acciones: las 9 de GOV-ORG-010 + firmar; 6 materias: contextos del IR §6) |
| OWNER | OD-ORG03-03 | Límite = **sin límite** o **monto máximo por operación + moneda** (VES, USD, EUR), Decimal de 2 decimales; la conversión la hará el proceso que lo aplique |
| OWNER | OD-ORG03-04 | **Acto por cargo**: BORRADOR → VIGENTE solo con acto, ≥ 1 competencia y estructura VIGENTE; cambios posteriores con motivo y versión; desactivar con fecha y motivo |

Ninguna cita de artículo concreto: las normas sostienen el dominio (competencias, control interno), no una regla numérica. Ningún monto ni umbral sale del código.

**Fuera de ORG-03 (no se absorbe):** delegaciones, suplencias, encargadurías y designaciones con acto (ORG-04, GOV-ORG-004, bloqueado por N37); persona ↔ cargo (ORG-06, GOV-ORG-007); matriz «quién puede» (ORG-07, GOV-ORG-010); aplicación del límite en compromisos y pagos (BUD/TRE).

**Prueba de bloqueo material: 0.** SECURITY, DATA_INTEGRITY, LEGAL, NORMATIVE, ARCHITECTURAL y TESTABILITY: 0. ORG-04 bloqueado no bloquea ORG-03 (no hay delegación aquí); T052, TOTP y el anfitrión dedicado no impiden implementar ni probar.

## 3. Modelo del proceso

| Elemento | Valor |
|---|---|
| PROCESS_ID / NAME | ORG-03 · Cargos con competencias y límites de firma/aprobación |
| Propósito | Fijar, por ejercicio, qué cargos tiene el ente, en qué unidad, qué puede hacer cada uno y hasta qué monto, con su acto soporte, para que los procesos de gasto y la vinculación de personas exijan autoridad del cargo |
| Dueño de negocio | Máxima autoridad del ente |
| Actor principal | Responsable de la organización institucional (`gobierno_cargos:edit` prepara; `gobierno_cargos:publish` pone en vigor y cambia la autoridad vigente) |
| Secundarios | Consulta (`gobierno_cargos:view`); auditor (`audit:view`) |
| Disparador | Estructura del ejercicio abierta o en vigor; aprobación de un reglamento o resolución de competencias; supresión de un cargo |
| Precondiciones | Sesión; licencia con `gobierno`; estructura del ejercicio (ORG-02) no CERRADA; para poner en vigor, estructura VIGENTE |
| Pasos | elegir ejercicio → registrar cargo en una unidad → agregar competencias y límites → adjuntar acto → poner en vigor → (en adelante) cambios con motivo / retirar competencias / desactivar con fecha |
| Decisiones del sistema | Faltantes para poner en vigor (lista cerrada); coherencia del límite; competencia repetida; si el usuario tiene autoridad para cambiar un cargo vigente |
| Aprobaciones | Poner en vigor y todo cambio de autoridad de un cargo VIGENTE exigen `publish` (separación preparación / autoridad, N20); sin flujo multinivel (GOV-ORG-003 no lo pide) |
| Correcciones | Cargo BORRADOR: edición y eliminación libres. VIGENTE: cambios con motivo (versión); el código y el inicio de vigencia no cambian |
| Anulación | No aplica: un cargo vigente no se anula; se desactiva con fecha |
| Período de efecto | El ejercicio; cada cargo, su `vigente_desde`–`vigente_hasta` dentro del ejercicio |
| Salidas | Cargos VIGENTES con competencias y límites; historial por cargo; CSV |
| Documentos | Acto del cargo (obligatorio para VIGENTE) |
| Reportes | «Cargos y competencias del ejercicio» (pantalla + CSV) |
| Auditoría | 9 acciones (§9) |
| Estado final | INACTIVO, o congelado con la estructura CERRADA |

### Máquina de estados del cargo

| Desde | Acción | Capacidad | Precondición | Hacia | Efecto | Auditoría | Reversible |
|---|---|---|---|---|---|---|---|
| — | registrar | `edit` | estructura no CERRADA; unidad ACTIVA de la misma estructura; código libre | BORRADOR | versión 1 | GOV_POSITION_CREATED | no aplica |
| BORRADOR | modificar | `edit` | `If-Match` | BORRADOR | versión + 1 | GOV_POSITION_UPDATED | sí |
| BORRADOR | eliminar | `edit` | sin acto vinculado; `If-Match` | — | borra cargo, competencias e historia de borrador | GOV_POSITION_DELETED | no |
| BORRADOR | poner en vigor | `publish` | estructura VIGENTE; ≥ 1 competencia; acto ACTIVE de la misma empresa; `If-Match` | VIGENTE | `activado_en/por`; versión + 1 | GOV_POSITION_ACTIVATED | no |
| VIGENTE | modificar denominación o unidad | `edit` | motivo; `If-Match` | VIGENTE | versión + 1 | GOV_POSITION_UPDATED | sí (otro cambio) |
| VIGENTE | desactivar | `publish` | fecha en el ejercicio ≥ `vigente_desde`; motivo; `If-Match` | INACTIVO | `vigente_hasta`; versión + 1 | GOV_POSITION_DEACTIVATED | no |
| cualquiera | — | — | estructura CERRADA | (solo lectura) | — | — | — |

### Competencias del cargo

| Estado del cargo | Agregar | Cambiar límite / fundamento | Retirar | Capacidad | Motivo |
|---|---|---|---|---|---|
| BORRADOR | sí | sí | sí | `edit` | opcional |
| VIGENTE | sí | sí | sí, salvo la última | `edit` **y** `publish` (sin `publish`: 403 `GOV_POSITION_AUTHORITY_REQUIRED`) | **obligatorio** (5–255) |
| INACTIVO / estructura CERRADA | no | no | no | — | — |

La acción y la materia de una competencia no cambian: se retira y se agrega otra. Cada operación sobre competencias incrementa la versión del cargo y guarda una instantánea con todas sus competencias.

## 4. Contrato del cargo (CARGO_CONTRACT)

- Un **cargo** es la posición institucional que porta autoridad (competencias y límites), no una persona ni un rol de software (GOV-ORG-003). Pertenece a **una unidad** de la estructura de **un ejercicio** del ente (OD-ORG03-01); su empresa y su ejercicio son los de la estructura.
- Código único en la estructura (`^[A-Z0-9][A-Z0-9.-]{0,29}$` tras pasar a mayúsculas). El mismo código puede repetirse en otro ejercicio. Una unidad puede tener varios cargos; un cargo, una sola unidad.
- Vigencia: `vigente_desde` dentro del ejercicio y no antes del `vigente_desde` de su unidad; `vigente_hasta` la fija la desactivación.
- Historia: cada cambio guarda una versión inmutable (instantánea con competencias, motivo, actor). Un cargo VIGENTE o INACTIVO no se borra. Con la estructura CERRADA, nada se escribe.
- Ocupantes, delegaciones, suplencias y encargadurías: **fuera de alcance** (ORG-04, ORG-06).
- **Cargo ≠ rol de seguridad:** no se usa `identity_access.roles`; las capacidades `gobierno_cargos:*` solo permiten administrar cargos, no ejercer su autoridad.

Interacción con ORG-02 (estructura):
- Copiar la estructura del ejercicio A al B copia también los cargos **VIGENTES** de A cuya unidad se copió: en BORRADOR, mismo código y denominación, unidad equivalente de B (por código), `vigente_desde` = 1 de enero de B, con sus competencias; el acto no se copia (cada ejercicio adjunta el suyo). La auditoría de la apertura registra `cargos_copiados`.
- No se desactiva una unidad que tenga cargos BORRADOR o VIGENTES (409 `GOV_UNIT_HAS_POSITIONS`), ni se elimina una unidad con cargos (409 `GOV_UNIT_HAS_POSITIONS`).
- Cerrar la estructura deja sus cargos de solo lectura (409 `GOV_STRUCTURE_CLOSED`).

## 5. Contrato de competencia y límite (COMPETENCY / LIMIT)

- Acción (catálogo cerrado, OD-ORG03-02): `SOLICITAR`, `COMPROMETER`, `CAUSAR`, `ORDENAR_PAGO`, `PAGAR`, `REGISTRAR`, `CUSTODIAR`, `APROBAR`, `AUDITAR`, `FIRMAR`.
- Materia (catálogo cerrado): `PRESUPUESTO`, `CONTRATACIONES`, `TESORERIA`, `CONTABILIDAD`, `BIENES`, `EXPEDIENTE`.
- Única por cargo: (acción, materia).
- Límite (OD-ORG03-03): `SIN_LIMITE`, o `MONTO` con `monto` > 0 (texto decimal, hasta 16 enteros y 2 decimales, `Numeric(18,2)`) y `moneda` ∈ {`VES`, `USD`, `EUR`}. `SIN_LIMITE` no lleva monto ni moneda; `MONTO` los exige. El monto es **por operación**. No hay conversión ni monto por defecto.
- Fundamento: texto opcional (≤ 255), p. ej. el artículo del reglamento interno.
- AUTHORITY_MODEL: el cargo VIGENTE con sus competencias es el `AuthorityGrant` del IR §9 para su vigencia y su acto. Su **aplicación** (denegar un compromiso o un pago por encima del límite) es de los procesos de BUD/TRE; ORG-03 deja el dato estructurado, auditado y versionado para ello.

## 6. Contrato de campos

| Id | Etiqueta | Significado | Tipo / BD / API | Oblig. | Validación | Edición | Ayuda |
|---|---|---|---|---|---|---|---|
| C01 | Código | Identificador del cargo en la estructura | texto / `String(30)` | sí | regex de §4 tras mayúsculas; único en la estructura | cargo BORRADOR | «Ej.: DIR-ADM» |
| C02 | Denominación | Nombre oficial del cargo | texto / `String(200)` | sí | 3–200, no solo espacios | BORRADOR libre; VIGENTE con motivo | — |
| C03 | Unidad | Unidad de la estructura donde está el cargo | uuid | sí | unidad ACTIVA de la misma estructura | BORRADOR libre; VIGENTE con motivo | — |
| C04 | Vigente desde | Inicio de vigencia | fecha / `Date` | sí (por defecto 1 de enero si la estructura es borrador; si no, hoy dentro del ejercicio) | dentro del ejercicio; ≥ inicio de la unidad | cargo BORRADOR | — |
| C05 | Vigente hasta | Fin de vigencia | fecha / `Date` nulo | — | la fija la desactivación: ≥ C04, dentro del ejercicio | solo al desactivar | — |
| C06 | Estado | BORRADOR / VIGENTE / INACTIVO | enum | — | sistema | no | — |
| C07 | Motivo | Razón del cambio en un cargo VIGENTE | texto / `String(255)` | sí si VIGENTE | 5–255 | — | «Queda en el historial y en la auditoría» |
| C08 | Versión | Concurrencia del cargo | entero | — | `If-Match` | no | — |
| C09 | Acto del cargo | Documento 046 vinculado | `DocumentLink(resource_type="GovernmentPosition")` | para VIGENTE | ≥ 1 documento ACTIVE de la misma empresa | adjuntar según 046 | «Resolución o reglamento que fija sus competencias y límites» |
| K01 | Acción | Qué puede hacer | enum (10) | sí | catálogo | solo al agregar | — |
| K02 | Materia | Sobre qué | enum (6) | sí | catálogo; (K01, K02) único en el cargo | solo al agregar | — |
| K03 | Límite | Sin límite o hasta un monto | enum `SIN_LIMITE`/`MONTO` | sí | — | sí | — |
| K04 | Monto máximo por operación | Tope de firma/aprobación | texto decimal / `Numeric(18,2)` / string | si MONTO | > 0; ≤ 2 decimales; ≤ 16 enteros; número JSON rechazado | sí | «Por operación» |
| K05 | Moneda | Moneda del monto | enum `VES`/`USD`/`EUR` / `String(3)` | si MONTO | catálogo | sí | — |
| K06 | Fundamento | Norma interna que lo sostiene | texto / `String(255)` nulo | no | ≤ 255 | sí | «Ej.: Reglamento interno, art. 12» |

## 7. Datos

| Tabla | Alcance | Columnas clave | Restricciones |
|---|---|---|---|
| `gov_positions` (`GovernmentPosition`) | COMPANY | `structure_id`, `company_id`, `unit_id`, `code`, `name`, `status`, `valid_from`, `valid_to`, `activated_at/by`, `version` | UNIQUE(`structure_id`,`code`); FK compuesta (`structure_id`,`unit_id`) → `gov_units`(`structure_id`,`id`); CHECK estado; `valid_to ≥ valid_from`; INACTIVO ⇔ `valid_to`; BORRADOR o `activated_at`; `version ≥ 1` |
| `gov_position_competencies` (`GovernmentPositionCompetency`) | COMPANY | `position_id`, `company_id`, `action`, `subject`, `limit_type`, `limit_amount` `Numeric(18,2)`, `limit_currency`, `basis` | UNIQUE(`position_id`,`action`,`subject`); FK `position_id` → `gov_positions.id` (la empresa la impone el servicio, AD-ORG03-02); CHECK acción, materia, tipo, moneda; coherencia (`SIN_LIMITE` sin monto ni moneda; `MONTO` con monto > 0 y moneda) |
| `gov_position_versions` (`GovernmentPositionVersion`) | COMPANY | `position_id`, `structure_id`, `company_id`, `version`, `status`, `snapshot`, `reason`, `actor_id` | UNIQUE(`position_id`,`version`); solo inserción |

Migración `0065_gov0_cargos`, sin relleno de datos; concede `gobierno_cargos:view/edit/publish` a FUNCIONAL_COMPLETO en instalaciones existentes.

## 8. API (`/api/v1`; guardas: permiso → contexto de empresa → módulo `gobierno`)

Prefijo `/gobierno/estructuras/{ejercicio}/cargos`.

| # | Método | Ruta | Capacidad | Respuesta | Errores | Auditoría |
|---|---|---|---|---|---|---|
| 1 | GET | `…/cargos` | view | `{estructura: {ejercicio, estado, version}, items: [CargoOut], total}` | 404 `GOV_STRUCTURE_NOT_FOUND` | — |
| 2 | POST | `…/cargos` | edit | 201 `CargoOut` | 404; 409 `GOV_STRUCTURE_CLOSED`; 409 `GOV_POSITION_CODE_DUPLICATE`; 422 `GOV_POSITION_INVALID_UNIT`; 422 validación | GOV_POSITION_CREATED |
| 3 | GET | `…/cargos/exportar` | view | `text/csv` (adjunto `cargos-AAAA.csv`) | 404 | GOV_POSITIONS_EXPORTED |
| 4 | GET | `…/cargos/{cargo_id}` | view | `CargoOut` | 404 `GOV_POSITION_NOT_FOUND` | — |
| 5 | PATCH | `…/cargos/{cargo_id}` | edit | `CargoOut` | 428 `GOV_POSITION_IF_MATCH_REQUIRED`; 409 `GOV_POSITION_STALE`; 409 CLOSED; 409 `GOV_POSITION_INVALID_STATE` (INACTIVO); 404; 422 INVALID_UNIT / `GOV_POSITION_REASON_REQUIRED` / `GOV_POSITION_FIELD_LOCKED` / `GOV_POSITION_NO_CHANGES`; 409 CODE_DUPLICATE | GOV_POSITION_UPDATED |
| 6 | DELETE | `…/cargos/{cargo_id}` | edit | 204 | 428; 409 STALE; 409 INVALID_STATE (no BORRADOR); 409 `GOV_POSITION_HAS_DOCUMENTS` | GOV_POSITION_DELETED |
| 7 | POST | `…/cargos/{cargo_id}/activar` | publish | `CargoOut` | 428; 409 STALE / INVALID_STATE / CLOSED; 422 `GOV_POSITION_INCOMPLETE` (`details.faltantes` ⊂ `ESTRUCTURA_VIGENTE`, `COMPETENCIAS`, `DOCUMENTO_ACTO`) | GOV_POSITION_ACTIVATED |
| 8 | POST | `…/cargos/{cargo_id}/desactivar` | publish | `CargoOut` | 428; 409 STALE / INVALID_STATE (no VIGENTE) / CLOSED; 422 fecha / REASON_REQUIRED | GOV_POSITION_DEACTIVATED |
| 9 | POST | `…/cargos/{cargo_id}/competencias` | edit (+ publish si VIGENTE) | 201 `CargoOut` | 428; 409 STALE / INVALID_STATE / CLOSED; 403 `GOV_POSITION_AUTHORITY_REQUIRED`; 409 `GOV_COMPETENCY_DUPLICATE`; 422 REASON_REQUIRED / validación del límite | GOV_COMPETENCY_GRANTED |
| 10 | PATCH | `…/cargos/{cargo_id}/competencias/{competencia_id}` | edit (+ publish si VIGENTE) | `CargoOut` | 428; 409 STALE / INVALID_STATE / CLOSED; 403 AUTHORITY_REQUIRED; 404 `GOV_COMPETENCY_NOT_FOUND`; 422 `GOV_COMPETENCY_NO_CHANGES` / REASON_REQUIRED / límite | GOV_COMPETENCY_CHANGED |
| 11 | POST | `…/cargos/{cargo_id}/competencias/{competencia_id}/retirar` | edit (+ publish si VIGENTE) | `CargoOut` | 428; 409 STALE / INVALID_STATE / CLOSED; 403 AUTHORITY_REQUIRED; 404; 409 `GOV_COMPETENCY_LAST` (la última de un VIGENTE); 422 REASON_REQUIRED | GOV_COMPETENCY_REVOKED |
| 12 | GET | `…/cargos/{cargo_id}/versiones` | view | `{items: [VersionCargo], total}` | 404 | — |

`CargoOut`: `id, codigo, denominacion, unidad_id, unidad_codigo, unidad_denominacion, estado, vigente_desde, vigente_hasta, version, competencias: [{id, accion, materia, tipo_limite, monto, moneda, fundamento}], faltantes_para_activar, documento_vinculado, activado_en, activado_por, creado_en`. `monto` sale como texto con 2 decimales o `null`.

Esquemas con `extra="forbid"`; fechas sin hora; el monto entra **solo como texto** (`app.shared.money.texto_decimal`); `If-Match` obligatorio en 5–11 (428 sin él), siempre con la versión del **cargo**. Toda escritura bloquea la fila de la estructura (`FOR UPDATE`). Un cargo o una competencia ajenos o inexistentes responden lo mismo: 404. Sin parámetros de consulta. Un error de negocio nunca es 500.

Cambios en ORG-02: `abrir` (copia de cargos), `desactivar_unidad` y `eliminar_unidad` (409 `GOV_UNIT_HAS_POSITIONS`).

## 9. Roles, MFA y auditoría

| Actor | view | edit | publish | audit |
|---|---|---|---|---|
| Responsable de la organización (FUNCIONAL_COMPLETO o rol con esas capacidades) | ✓ | ✓ | ✓ | — |
| Preparador (rol con `view` + `edit`) | ✓ | ✓ (borradores y datos descriptivos) | — | — |
| Consulta | ✓ | — | — | — |
| Auditor | — | — | — | `audit:view` |
| ADMIN técnico | — | — | — | según su rol (GOV-CTL-004: sin autoridad funcional) |

Las pantallas de cargos leen además la estructura del ejercicio, así que todo rol de cargos incluye `gobierno_estructura:view` (PDD-ORG03-09).

ORG03_MFA_MATRIX: `gobierno_cargos:view` ESTÁNDAR; `gobierno_cargos:edit` y `gobierno_cargos:publish` SENSIBLES (crean o cambian autoridad institucional, como `gobierno_estructura:edit/publish`).

Auditoría (catálogo cerrado, ámbito COMPANY, `entity_type="GovernmentPosition"` salvo la exportación): `GOV_POSITION_CREATED`, `GOV_POSITION_UPDATED` (con motivo), `GOV_POSITION_ACTIVATED`, `GOV_POSITION_DEACTIVATED` (motivo y fecha), `GOV_POSITION_DELETED`, `GOV_COMPETENCY_GRANTED`, `GOV_COMPETENCY_CHANGED` (antes/después del límite), `GOV_COMPETENCY_REVOKED` (con la competencia retirada), `GOV_POSITIONS_EXPORTED` (`GovernmentStructure`). Contexto: actor, tenant, empresa, ejercicio, código de la unidad, cargo, antes/después, motivo.

## 10. Menú, pantallas y estados

| Menú | Ruta | Pantalla |
|---|---|---|
| Gobierno › **Cargos y competencias** | `/gobierno/cargos` | Ejercicios: estructuras del ente con su estado y enlace «Cargos AAAA»; sin estructuras, enlace a Estructura organizativa |
| (desde la lista) | `/gobierno/cargos/:ejercicio` | Cargos del ejercicio: aviso del estado de la estructura, tabla (código, denominación, unidad, competencias, vigencia, estado) con búsqueda y filtros por unidad y estado, «Agregar cargo», «Exportar CSV» |
| (desde la tabla) | `/gobierno/cargos/:ejercicio/:cargoId` | Cargo: datos, requisitos para poner en vigor, competencias y límites (agregar, cambiar límite, retirar), acto, historial, editar, poner en vigor, desactivar, eliminar |

Estados de UI: módulo no habilitado; sin acceso; sin estructuras; estructura inexistente; sin cargos; ningún resultado del filtro; estructura en borrador (aviso: «los cargos se ponen en vigor cuando la estructura esté vigente»); cargo con faltantes (Poner en vigor deshabilitado y descrito); vigente sin `publish` (sin acciones sobre competencias); inactivo; estructura cerrada (solo lectura); conflicto de versión; errores de campo, de límite, de duplicado y de motivo; error de red con reintento.

Etiquetas: acciones «Solicitar, Comprometer, Causar, Ordenar el pago, Pagar, Registrar, Custodiar, Aprobar, Auditar, Firmar»; materias «Presupuesto, Contrataciones, Tesorería, Contabilidad, Bienes públicos, Expediente y documentos»; límite «Sin límite» o «Hasta 1.500.000,00 VES por operación». Ningún código técnico como rótulo principal.

## 11. Escenario de éxito para la prueba de la dueña

Con el ente activo y la estructura del ejercicio vigente (ORG-01/02), entra en Gobierno › Cargos y competencias, abre los cargos del ejercicio y registra «Director de Administración» en la Dirección de Administración. Le agrega «Aprobar · Contrataciones hasta 50.000,00 USD por operación» y «Firmar · Tesorería sin límite». El sistema no le deja ponerlo en vigor sin el acto: lo adjunta y lo pone en vigor. Cambia el límite a 75.000,00 USD con motivo y ve la versión en el historial; un usuario sin autoridad de puesta en vigor no puede hacerlo. Desactiva otro cargo con fecha. Descarga el CSV. En Auditoría ve la competencia otorgada, cambiada y el cargo desactivado.
