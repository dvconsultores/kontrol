# Feature Specification: CTL-10 Controles materiales previos al cierre

**Feature Branch**: `develop` (rama única; Spec nueva `gov-ctl-10-controles-cierre`)

**Created**: 2026-11-06

**Status**: Draft

**Input**: GOV-CTL-012, P0, módulo Control interno: «Impedir cierre de ejercicio/proceso con controles materiales pendientes definidos por política institucional.» Fuentes N20 y N21. Actor principal: Control Interno. Diseño cerrado: `/home/maria/.cache/kontrol-qa/herramientas/ctl10/DISENO.md`.

## Fuentes y decisiones

- **IR:** GOV-CTL-012, fuentes N20 y N21. Es el último requisito de control interno que consume lo ya construido: hallazgos (CTL-06), actos (DOC-02), segregación de funciones (CTL-01) y auditoría (CTL-04).
- **Decisiones de la dueña (2026-11-06):**

| Id | Decisión |
|---|---|
| OD-CTL10-01 | Solo AÑADIDOS de registro en ficheros compartidos: `app/shared/audit_catalog_entries.py`, `specs/001-fundacion/evidence/audit-catalog/catalogo.md`, `app/modules/identity_access/mfa_policy.py`, `app/modules/setup/api.py`, `app/main.py`, `frontend/src/app/router.tsx`, `frontend/src/app/autoridad/pantallas.ts`, `frontend/src/layout/Sidebar.tsx`. Sin cambiar su lógica |
| OD-CTL10-02 | Se integran dos cierres: ORG-02 (cerrar la estructura del ejercicio) y TRE-02 (cerrar el programa). TRE-01 no |
| OD-CTL10-03 | Tipos de control: HALLAZGOS_ABIERTOS (hallazgo en estado distinto de CERRADO con riesgo igual o superior a `riesgo_minimo`, en todo el ente) y ACTOS_SIN_EFICACIA (acto en estado EMITIDO con fecha dentro del ejercicio del objeto). Catálogo cerrado |
| OD-CTL10-04 | La política exige fundamento escrito (mínimo 10 caracteres) y la activa Control Interno con MFA, sin acto ni documento |

### Prueba de bloqueo material

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Requiere contabilidad? | No. Los dos tipos de control leen hallazgos y actos |
| 2 | ¿Requiere presupuesto? | No |
| 3 | ¿Requiere ORG-06 (persona↔cargo)? | No. El actor es el usuario autenticado |
| 4 | ¿Requiere un motor genérico de reglas? | No. Dos tipos fijos, sin expresiones, sin SQL de usuario, sin JSON ejecutable |
| 5 | ¿Cambia la semántica de un núcleo compartido? | No. Solo añadidos de registro (OD-CTL10-01) y una llamada a la guarda dentro de los dos cierres integrados |
| 6 | ¿Tiene datos reales que sustenten los tipos? | Sí: `gov_findings` (estado, riesgo) y `gov_acts` (status, fecha) |
| 7 | ¿Cuántos cierres reales existen hoy y cuántos se integran? | Ver inventario en `evidence/CTL10_CLOSE_ACTION_INTEGRATION_MATRIX.md`: dos integrados |

SECURITY · DATA_INTEGRITY · LEGAL · NORMATIVE · ARCHITECTURAL · TESTABILITY · DOMAIN_DEPENDENCY = 0. CTL10_FULL_PROCESS_IMPLEMENTABLE = 1. TRE-08 sigue BLOCKED y no se toca.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definir y activar una política de cierre (Priority: P1)

Control Interno crea una política para una acción de cierre (cerrar la estructura o cerrar el programa de caja), le añade controles (hallazgos abiertos de cierto riesgo; actos emitidos sin eficacia), escribe el fundamento y la activa con MFA desde una fecha.

**Why this priority**: sin política vigente no hay control material; es la capacidad de negocio del requisito.

**Independent Test**: desde el menú, crear una política, añadir controles, activarla con MFA y verla vigente con su historia.

**Acceptance Scenarios**:

1. **Given** un usuario con gestión, **When** crea la política «PC-001» para la acción cerrar estructura con nombre y fundamento de al menos 10 caracteres, **Then** queda en BORRADOR con código por empresa y versión 1.
2. **Given** un borrador, **When** añade el control HALLAZGOS_ABIERTOS con riesgo mínimo MEDIO y la materialidad (10 a 500 caracteres), **Then** el control queda registrado; repetir el tipo se rechaza.
3. **Given** un borrador con un control, **When** activa con MFA, **Then** queda VIGENTE con quién y cuándo.
4. **Given** un borrador sin controles, **When** intenta activarlo, **Then** se rechaza y se explica qué falta.
5. **Given** una política VIGENTE para esa acción, **When** se activa otra para la misma acción, **Then** responde 409 GOV_CLOSURE_POLICY_ACTIVE_EXISTS.
6. **Given** un control ACTOS_SIN_EFICACIA, **When** se le indica riesgo mínimo, **Then** se rechaza; en HALLAZGOS_ABIERTOS el riesgo mínimo es obligatorio.

---

### User Story 2 - El cierre se bloquea con controles materiales pendientes (Priority: P1)

Quien cierra una estructura de ejercicio (ORG-02) o un programa de caja (TRE-02) con una política efectiva hoy recibe un bloqueo que dice qué lo impide, por qué es material, qué queda pendiente (con enlaces) y quién es dueño.

**Why this priority**: es el efecto de control que da nombre al requisito.

**Independent Test**: flujo A, cerrar la estructura de un ejercicio pasado con un hallazgo abierto; flujo B, cerrar un programa con un acto emitido sin eficacia en su ejercicio.

**Acceptance Scenarios**:

1. **Given** política efectiva con HALLAZGOS_ABIERTOS (riesgo mínimo MEDIO) y un hallazgo ABIERTO de riesgo ALTO, **When** se cierra la estructura, **Then** responde 409 GOV_MATERIAL_CLOSE_BLOCKED con política, proceso, objeto, total, dueño «Control Interno» y la muestra (hasta 5) con enlace; el cierre no ocurre; se audita GOV_MATERIAL_CLOSE_BLOCKED.
2. **Given** un hallazgo BAJO y riesgo mínimo MEDIO, **When** se cierra, **Then** no cuenta y el cierre procede.
3. **Given** política con ACTOS_SIN_EFICACIA y un acto EMITIDO con fecha dentro del ejercicio del objeto, **When** se cierra el programa de ese ejercicio, **Then** se bloquea; un acto de otro ejercicio no cuenta.
4. **Given** política efectiva y cero pendientes, **When** se cierra, **Then** procede y se audita GOV_MATERIAL_CLOSE_ALLOWED en la misma transacción.
5. **Given** ninguna política efectiva (inexistente, borrador, retirada, futura o vencida), **When** se cierra, **Then** el cierre actúa como hoy y no se audita nada nuevo.
6. **Given** que el cliente envía datos sobre controles o `company_id`, **When** se cierra, **Then** se ignoran o se rechazan: el servidor decide política, ejercicio y pendientes.
7. **Given** un cierre que el actor no puede hacer por estado o por SoD, **When** intenta cerrar, **Then** recibe ese error y no el de CTL-10 (orden de guardas).
8. **Given** el 409 en la pantalla de la estructura o del programa, **When** se muestra, **Then** aparece el panel `BloqueoDeCierre` con enlaces a `/gobierno/hallazgos/{id}` o `/gobierno/actos/{id}`.

---

### User Story 3 - Retirar una política (Priority: P1)

Control Interno retira una política cuando deja de aplicar, con MFA y motivo; no se edita una política activada: se retira y se crea otra.

**Why this priority**: cierra el ciclo de vida sin borrar historia ni editar lo vigente.

**Independent Test**: retirar una política vigente y comprobar que el cierre vuelve a proceder y la historia lo registra.

**Acceptance Scenarios**:

1. **Given** una política VIGENTE, **When** la retira con MFA y motivo, **Then** queda RETIRADA y deja de bloquear.
2. **Given** un borrador, **When** lo retira con MFA y motivo, **Then** queda RETIRADA sin haber sido vigente.
3. **Given** una política VIGENTE o RETIRADA, **When** intenta editarla, añadir o quitar controles, o borrarla, **Then** se rechaza, también ante escritura directa en la base.
4. **Given** un cierre en curso y un retiro simultáneo, **When** ambos corren, **Then** quedan serializados y el resultado es coherente con uno de los dos órdenes.

---

### User Story 4 - Consultar los cierres bloqueados (Priority: P2)

Control Interno consulta los cierres que el sistema impidió: política, proceso, objeto, quién lo intentó, cuándo y cuántos pendientes por tipo.

**Why this priority**: el control debe ser verificable a posteriori.

**Independent Test**: provocar un bloqueo y verlo en Cierres bloqueados con filtros.

**Acceptance Scenarios**:

1. **Given** un cierre bloqueado, **When** Control Interno abre «Cierres bloqueados», **Then** ve la fila con política, objeto, ejercicio, usuario, instante y total.
2. **Given** filtros de acción y periodo, **When** los aplica, **Then** la lista se acota; sin resultados se muestra el estado vacío.

---

### User Story 5 - Editar un borrador y mantener sus controles (Priority: P2)

Control Interno cambia nombre, fundamento y vigencia de un borrador, y añade o quita controles mientras sea BORRADOR.

**Why this priority**: permite preparar la política antes de activarla.

**Independent Test**: editar con versión, quitar un control, y recibir conflicto con versión vieja.

**Acceptance Scenarios**:

1. **Given** un borrador, **When** edita con la versión vigente, **Then** se guarda y la versión avanza; con versión vieja responde 409 GOV_CLOSURE_POLICY_STALE; sin If-Match, 428.
2. **Given** un control de un borrador, **When** lo quita con If-Match, **Then** se elimina y se registra CONTROL_RETIRADO en la historia.

---

### User Story 6 - Consulta y seguridad (Priority: P3)

Un usuario con consulta ve políticas, controles, historia y bloqueos sin poder cambiar nada; ningún usuario ve ni modifica políticas de otra empresa.

**Why this priority**: el requisito es de control; el acceso es parte del control.

**Independent Test**: usuario de solo consulta; usuario del administrador técnico sin la capacidad.

**Acceptance Scenarios**:

1. **Given** un usuario con `gobierno_cierre:view`, **When** abre una política, **Then** ve todo y ninguna acción de escritura; las escrituras directas se rechazan.
2. **Given** el administrador técnico sin la capacidad, **When** accede, **Then** no tiene acceso por serlo.
3. **Given** un UUID de otra empresa, **When** se solicita, **Then** responde 404 sin revelar datos.

### Edge Cases

- Política futura (`vigente_desde` > hoy) o vencida (`vigente_hasta` < hoy, fecha civil de Caracas): no bloquea.
- Hallazgos de todo el ente cuentan sin importar el ejercicio; actos solo los del ejercicio del objeto.
- Más de 5 pendientes: la muestra trae 5 y el total el recuento real; el enlace de lista lleva a la lista filtrada.
- Dos cierres simultáneos del mismo objeto: uno cierra y el otro recibe el error de estado, no el bloqueo.
- Dos activaciones simultáneas de políticas para la misma acción: solo una vence; la otra recibe 409.
- Un tipo de control manipulado por el cliente fuera del catálogo se rechaza con 422.
- Un cierre directo por otra vía (servicio sin pasar por la guarda) no existe: la guarda vive en el servicio de cierre.
- El actor que bloquea el cierre no necesita ser Control Interno: el bloqueo es del sistema.
- La política pertenece a una empresa; una política de otra empresa nunca se evalúa.

## Requirements *(mandatory)*

### Functional Requirements

**Políticas y controles**

- **FR-001**: Control Interno MUST poder crear una política con nombre (3 a 200), acción de cierre (ORG02_CERRAR_ESTRUCTURA o TRE02_CERRAR_PROGRAMA), fundamento (mínimo 10) y `vigente_desde`; el código `PC-###` es por empresa.
- **FR-002**: Una política MUST poder tener a lo sumo un control de cada tipo del catálogo cerrado: HALLAZGOS_ABIERTOS y ACTOS_SIN_EFICACIA.
- **FR-003**: HALLAZGOS_ABIERTOS MUST exigir `riesgo_minimo` (ALTO, MEDIO o BAJO) y contar los hallazgos del ente en estado distinto de CERRADO con riesgo igual o superior. ACTOS_SIN_EFICACIA MUST NO llevar riesgo mínimo y contar los actos EMITIDO con fecha dentro del ejercicio del objeto.
- **FR-004**: Cada control MUST llevar una materialidad de 10 a 500 caracteres que explica por qué es material.
- **FR-005**: El sistema MUST NOT aceptar expresiones, SQL, JSON ejecutable ni tipos fuera del catálogo.
- **FR-006**: A lo sumo una política VIGENTE por empresa y acción; activar con otra vigente MUST responder 409 GOV_CLOSURE_POLICY_ACTIVE_EXISTS, también ante activaciones concurrentes.

**Ciclo de vida**

- **FR-007**: Activar MUST exigir BORRADOR, al menos un control, fundamento y MFA, y registrar quién y cuándo. No exige acto ni documento.
- **FR-008**: Retirar MUST exigir motivo (10 a 500 caracteres) y MFA, desde BORRADOR o VIGENTE, porque la capacidad `activate` es SENSITIVE para activar y retirar (DISENO). Una política activada no se edita.
- **FR-009**: Una política VIGENTE o RETIRADA, sus controles y su historia MUST ser inmutables y no borrables, también ante escrituras directas; los controles solo cambian en BORRADOR.
- **FR-010**: Una política es efectiva hoy (fecha civil America/Caracas) si está VIGENTE, `vigente_desde` <= hoy y (`vigente_hasta` nulo o >= hoy). Una futura o vencida no bloquea.

**Guarda del cierre**

- **FR-011**: La guarda `evaluar_cierre` MUST ejecutarse en el cierre de estructura (ORG-02) y en el cierre de programa (TRE-02) después de estado y SoD, con la fila ya bloqueada, antes de la mutación. Orden: autenticación, permiso, ámbito, estado, SoD, CTL-10, mutación, auditoría.
- **FR-012**: Sin política efectiva, la guarda MUST NOT hacer nada ni auditar.
- **FR-013**: Con pendientes, la guarda MUST revertir, auditar GOV_MATERIAL_CLOSE_BLOCKED (REJECTION) tras la reversión con el contenido fijado en el contrato, y responder 409 GOV_MATERIAL_CLOSE_BLOCKED con política, proceso, objeto, total, dueño «Control Interno» y por control: tipo, etiqueta, materialidad, pendientes, muestra de hasta 5 con enlace interno y ruta de lista.
- **FR-014**: Con política efectiva y sin pendientes, la guarda MUST auditar GOV_MATERIAL_CLOSE_ALLOWED en la misma transacción del cierre.
- **FR-015**: La guarda MUST bloquear la política efectiva con FOR SHARE para serializar con retirar. El ejercicio MUST venir del objeto en el servidor y el cliente MUST NOT enviar nada sobre controles.
- **FR-016**: Las demás acciones de cierre existentes (TRE-01, regla SoD) y verificar hallazgo MUST permanecer sin cambio de comportamiento.

**Acceso, auditoría e integraciones**

- **FR-017**: El proceso MUST tener la capacidad `gobierno_cierre` con `view` y `manage` STANDARD y `activate` SENSITIVE (MFA) para activar y retirar; se otorga a FUNCIONAL_COMPLETO y no al administrador técnico.
- **FR-018**: Toda consulta y escritura MUST limitarse al ente activo; lo ajeno responde «no encontrado» o «no válido» y el cliente no elige la empresa.
- **FR-019**: Toda edición, quitar control y retiro MUST exigir versión (If-Match); versión vieja responde GOV_CLOSURE_POLICY_STALE 409; ausente, GOV_CLOSURE_POLICY_IF_MATCH_REQUIRED 428.
- **FR-020**: Cada escritura MUST auditarse con autor: GOV_CLOSURE_POLICY_CREATED, _UPDATED, _CONTROL_ADDED, _CONTROL_REMOVED, _ACTIVATED, _RETIRED, más GOV_MATERIAL_CLOSE_BLOCKED y GOV_MATERIAL_CLOSE_ALLOWED, con owner_spec `gov-ctl-10`. La historia inmutable registra CREADA, ACTUALIZADA, CONTROL_ANADIDO, CONTROL_RETIRADO, ACTIVADA y RETIRADA, sin dinero.
- **FR-021**: Auditoría institucional (CTL-04) MUST incluir el proceso («CTL-10», «Controles de cierre», «gov-ctl-10») con rastreo a la política.
- **FR-022**: El catálogo SoD (CTL-01) MUST incluir el proceso CTL-10 con CTL10_REGISTRAR, CTL10_ACTIVAR y CTL10_RETIRAR, con guarda en activar y retirar y sin reglas por defecto.
- **FR-023**: El proceso MUST ser ejecutable desde Gobierno › Controles de cierre (`/gobierno/cierres`), con lista, nueva política, ficha (controles, activar, retirar, historia) y Cierres bloqueados (`/gobierno/cierres/bloqueos`), a 1280, 768 y 320 px con accesibilidad WCAG AA.
- **FR-024**: Los errores MUST ser GOV_CLOSURE_POLICY_INVALID 422, _IF_MATCH_REQUIRED 428, _STALE 409, _INVALID_STATE 409, _ACTIVE_EXISTS 409, _NOT_FOUND 404 y GOV_MATERIAL_CLOSE_BLOCKED 409.

**Clasificación**

- **FR-025**: REPORTING_COMPLETE = NOT_APPLICABLE y DOCUMENT_COMPLETE = NOT_APPLICABLE: GOV-CTL-012 no exige exportación ni documento.
- **FR-026**: Los cambios en ficheros compartidos MUST limitarse a los añadidos de OD-CTL10-01 más la llamada a la guarda en `service_estructura.cerrar` y `service_caja.cerrar`, sin alterar su lógica previa. Sin contabilidad, presupuesto, ORG-06 ni motor genérico.

### Key Entities

- **Política de cierre**: regla institucional para una acción de cierre, con código, nombre, fundamento, estado, vigencia y versión.
- **Control de cierre**: tipo del catálogo cerrado, riesgo mínimo cuando aplica y materialidad.
- **Historia de la política**: registro inmutable de cada cambio.
- **Bloqueo de cierre**: evento de auditoría de un cierre impedido, con pendientes por control.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Control Interno completa por la interfaz crear, controlar, activar y retirar una política sin otra herramienta.
- **SC-002**: En el 100 % de los casos probados, un cierre con pendientes materiales es impedido y uno sin pendientes o sin política efectiva procede.
- **SC-003**: Ninguna prueba hostil (rol, otra empresa, UUID directo, `company_id`, política inactiva, futura o vencida, tipo manipulado, bypass directo) obtiene o modifica datos ajenos ni evade el bloqueo.
- **SC-004**: Ninguna política activada, control o historia cambia tras activar o retirar, comprobado también con escrituras directas.
- **SC-005**: Las pruebas de concurrencia no producen dos cierres, dos políticas vigentes para la misma acción ni ediciones perdidas.
- **SC-006**: Quien recibe un bloqueo identifica en una pantalla qué lo impide, por qué es material, qué queda pendiente con enlaces y quién es dueño.
- **SC-007**: Los procesos previos de Gobierno pasan su regresión sin cambios de contrato.

## Assumptions

- Solo se integran dos acciones de cierre; las demás se evalúan en el inventario y quedan sin integrar por decisión (OD-CTL10-02) o por no ser cierre de proceso.
- «Fecha del acto» es el campo `fecha` del acto; el ejercicio del objeto es el año calendario de la estructura o del programa.
- Reportes y documentos: NOT_APPLICABLE. Sin Enterprise. Sin producción.
- TRE-08 permanece BLOCKED.
