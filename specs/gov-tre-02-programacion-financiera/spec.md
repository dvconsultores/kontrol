# Feature Specification: TRE-02 Programación financiera y disponibilidad de caja

**Feature Branch**: `develop` (rama única; Spec dueña `gov-tre-02-programacion-financiera`)

**Created**: 2026-11-05

**Status**: Draft

**Input**: GOV-TRE-002, P0: «Registrar programación financiera y disponibilidad de caja separada de la disponibilidad presupuestaria.» Encargo GOV-TRE-FUNCTIONAL-02.

## Fuentes y decisiones

- **IR §7.7:** GOV-TRE-002, fuentes N03 y N05. IR §5: Tesorería «programa caja».
- **N05, Reglamento N.º 3 de la LOAFSP (G.O. 38.433, 2006):** art. 60.1, programación de los flujos de ingresos y pagos; art. 61, presupuesto de caja de cada órgano con la programación mensual de desembolsos y su seguimiento; art. 63, los rubros y subperíodos los determina la Oficina Nacional del Tesoro; art. 64, las cuotas y reprogramaciones las aprueba el Ministerio de Finanzas; art. 24, los bancos informan disponibilidades a esa Oficina. Art. 62: desequilibrios transitorios de caja.
- **Alcance de N05:** el art. 3 lo extiende al sector público nacional y a los entes descentralizados sin fines empresariales. Estados y municipios usan el mismo modelo por decisión de producto, no por mandato de esa norma.

| Id | Decisión de la dueña (2026-11-05) |
|---|---|
| OD-TRE02-01 | Un programa por ejercicio y moneda, desagregado por mes. Sin totales entre monedas |
| OD-TRE02-02 | La disponibilidad inicial la declara Tesorería por cuenta de TRE-01, con fecha de corte y fundamento, bajo su responsabilidad. Se rotula como declarada |
| OD-TRE02-03 | Los rubros forman un catálogo del ente, de ingreso o de desembolso, sin precargar |
| OD-TRE02-04 | Tesorería activa con MFA, sin aprobador interno ni acto. Reprogramar crea una versión nueva con motivo; los meses pasados no cambian. Presupuesto solo consulta |

### Prueba de bloqueo material

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Qué se programa? | Ingresos previstos y desembolsos programados (art. 60.1, 61) |
| 2–3 | ¿Período y granularidad? | Ejercicio, por mes (art. 61; OD-TRE02-01) |
| 4 | ¿Por cuenta? | No. La cuenta solo sustenta la disponibilidad inicial |
| 5 | ¿Por moneda? | Sí, un programa por moneda |
| 6 | ¿Por fuente de Tesorería? | Por rubro del ente (art. 63; OD-TRE02-03) |
| 7 | ¿Consolidado por ente? | Sí, por moneda |
| 8–9 | ¿Qué abre la disponibilidad? | La declaración de Tesorería (OD-TRE02-02) |
| 10 | ¿Se deriva de saldos de la cuenta? | No: TRE-01 no guarda saldos |
| 11–14 | ¿Exige extractos, TRE-06, pagos reales o presupuesto? | No |
| 15 | ¿Acto formal de aprobación? | No (OD-TRE02-04) |
| 16 | ¿Ingresos y egresos previstos? | Sí |

SECURITY · DATA_INTEGRITY · LEGAL · NORMATIVE · ARCHITECTURAL · TESTABILITY · DOMAIN_DEPENDENCY = 0. TRE02_FULL_PROCESS_IMPLEMENTABLE = 1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Programar la caja del ejercicio y ver la disponibilidad (Priority: P1)

Tesorería prepara el programa de un ejercicio y una moneda: declara cuánto hay en cada cuenta, registra los ingresos previstos y los desembolsos programados por mes, ve la disponibilidad proyectada de cada mes y activa el programa.

**Why this priority**: es la capacidad de negocio del requisito; sin ella no hay programación.

**Independent Test**: desde el menú, con cuentas vigentes de TRE-01, crear un programa, declarar la disponibilidad, registrar líneas y activar; la consulta muestra la disponibilidad de cada mes.

**Acceptance Scenarios**:

1. **Given** una cuenta vigente en VES, **When** Tesorería crea el programa VES del ejercicio y declara 1.000,00 para esa cuenta, **Then** la disponibilidad inicial es 1.000,00, rotulada como declarada, con fecha de corte, fundamento y autor.
2. **Given** ingresos de 500,00 y desembolsos de 300,00 en el primer mes, **When** consulta el programa, **Then** ese mes cierra en 1.200,00 y el siguiente abre en 1.200,00.
3. **Given** un programa con declaración y al menos una línea, **When** lo activa con MFA, **Then** queda vigente en su versión 1.
4. **Given** un programa sin declaración o sin líneas, **When** intenta activarlo, **Then** el sistema dice qué falta.
5. **Given** un mes cuya disponibilidad final es negativa, **When** consulta o activa, **Then** ve el aviso de déficit proyectado y puede activar.

---

### User Story 2 - Reprogramar sin reescribir la historia (Priority: P1)

Tesorería cambia lo previsto con una versión nueva y un motivo. La versión anterior queda consultable y los meses pasados no cambian.

**Why this priority**: la programación cambia durante el ejercicio y el requisito de control exige no reescribirla.

**Independent Test**: reprogramar un programa vigente, cambiar un mes futuro, activar y comparar ambas versiones.

**Acceptance Scenarios**:

1. **Given** un programa vigente, **When** reprograma con motivo, **Then** nace un borrador versión 2 copiado de la versión 1, y la 1 sigue vigente.
2. **Given** ese borrador, **When** intenta cambiar un mes anterior al mes en curso, **Then** se rechaza; **When** cambia el mes en curso o uno futuro, **Then** se acepta.
3. **Given** el borrador activado, **When** consulta, **Then** la versión 2 está vigente, la 1 superada e intacta, y la historia muestra quién y cuándo.
4. **Given** un borrador de reprogramación, **When** lo descarta, **Then** queda descartado y la versión vigente no cambia.

---

### User Story 3 - Cerrar el programa (Priority: P2)

Tesorería cierra el programa del ejercicio con motivo. Queda de consulta permanente.

**Why this priority**: completa el ciclo de vida sin borrar nada.

**Independent Test**: cerrar un programa vigente y comprobar que no admite cambios.

**Acceptance Scenarios**:

1. **Given** un programa vigente sin reprogramación abierta, **When** lo cierra con motivo y MFA, **Then** queda cerrado y consultable.
2. **Given** un programa cerrado, **When** intenta reprogramarlo, **Then** se rechaza, y el ejercicio y la moneda no admiten otro programa.

---

### User Story 4 - Mantener el catálogo de rubros (Priority: P2)

Tesorería registra sus rubros de ingreso y desembolso, y retira los que ya no usa sin alterar la historia.

**Why this priority**: sin rubros no se puede registrar una línea.

**Independent Test**: crear un rubro, usarlo, inactivarlo y comprobar que no se ofrece en líneas nuevas y que las existentes lo conservan.

**Acceptance Scenarios**:

1. **Given** un código de rubro nuevo, **When** lo registra con nombre y tipo, **Then** queda activo; repetir el código se rechaza.
2. **Given** un rubro en uso, **When** lo inactiva, **Then** las líneas existentes lo conservan y no se ofrece para nuevas.

---

### User Story 5 - Consultar desde Presupuesto u otro rol (Priority: P3)

Un usuario con permiso de consulta ve programas, versiones y disponibilidad, sin poder cambiar nada.

**Why this priority**: Presupuesto participa como actor del proceso, solo como lectura (OD-TRE02-04).

**Independent Test**: entrar con un usuario de consulta y comprobar que no hay acciones.

**Acceptance Scenarios**:

1. **Given** un usuario solo de consulta, **When** abre un programa, **Then** ve todo y no ve acciones de escritura; las escrituras directas se rechazan.

---

### User Story 6 - Delta OBS-TRE01-E2E-01: revocación del acto de una cuenta (Priority: P2)

Una prueba de usuario recorre TRE-01 y DOC-02 a la vez: una cuenta vigente, su acto revocado o anulado, el aviso, los bloqueos, el acto de reemplazo y la historia.

**Why this priority**: cierra la cobertura que faltaba en TRE-01, sin reabrir ese proceso.

**Independent Test**: la propia prueba E2E.

**Acceptance Scenarios**:

1. **Given** una cuenta vigente con acto, **When** el acto se revoca o anula en DOC-02, **Then** la ficha avisa, y no admite autorizados nuevos ni reactivación.
2. **Given** ese estado, **When** se vincula un acto vigente, **Then** se restablece lo permitido, y la historia y la auditoría lo registran.

### Edge Cases

- Una cuenta de otra moneda, de otro ente, en borrador, inactiva o cerrada no admite declaración.
- Una cuenta que se cierra después conserva su declaración en las versiones existentes.
- Una versión activada, superada, descartada o cerrada no cambia nunca.
- No hay dos programas abiertos o cerrados para el mismo ejercicio y moneda del mismo ente; un borrador descartado no ocupa el lugar.
- No hay dos borradores de reprogramación a la vez, ni una versión con dos líneas para el mismo rubro y mes, ni dos declaraciones para la misma cuenta.
- Un ejercicio ya terminado no admite reprogramación: todos sus meses son pasados.
- Dos usuarios que actúan a la vez nunca pierden una actualización: el segundo recibe un aviso de versión.
- Un programa iniciado a mitad de año no tiene meses anteriores a su mes inicial.

## Requirements *(mandatory)*

### Functional Requirements

**Catálogo**

- **FR-001**: Tesorería MUST poder registrar, editar e inactivar rubros con código único por ente, nombre y tipo (ingreso o desembolso). El sistema no precarga ninguno.

**Programa**

- **FR-002**: Tesorería MUST poder crear un programa con ejercicio (desde el año anterior al de la fecha de Caracas), moneda y mes inicial. La moneda es VES, USD o EUR.
- **FR-003**: El sistema MUST impedir dos programas no descartados para el mismo ente, ejercicio y moneda.
- **FR-004**: Tesorería MUST poder declarar, en un borrador de primera versión, la disponibilidad de cada cuenta vigente de TRE-01 de esa moneda: monto no negativo, fecha de corte no futura y fundamento de 10 a 500 caracteres.
- **FR-005**: Una reprogramación MUST conservar sin cambios la disponibilidad inicial declarada.
- **FR-006**: Tesorería MUST poder registrar, cambiar y quitar líneas de un borrador: rubro activo, mes dentro del programa y monto mayor que cero con dos decimales.

**Disponibilidad**

- **FR-007**: El sistema MUST calcular por mes, con aritmética decimal exacta: inicial del primer mes = suma de lo declarado; final = inicial + ingresos − desembolsos; inicial del mes siguiente = final del anterior.
- **FR-008**: La pantalla MUST distinguir lo declarado de lo calculado, y rotular que es disponibilidad de caja proyectada, no disponibilidad presupuestaria ni saldo bancario.
- **FR-009**: El sistema MUST avisar los meses con disponibilidad final negativa, sin impedir la activación.
- **FR-010**: Las monedas MUST mantenerse separadas: ningún total ni conversión entre ellas.

**Ciclo de vida**

- **FR-011**: Activar MUST exigir el borrador, al menos una declaración en el programa y al menos una línea. Exige MFA.
- **FR-012**: Reprogramar MUST exigir un programa vigente, sin otro borrador y un motivo de 10 a 500 caracteres, y crear una versión nueva copiada de la vigente.
- **FR-013**: En una reprogramación no MUST poder alterarse ningún mes anterior al mes en curso, según la fecha de Caracas. Si el ejercicio ya terminó, reprogramar se rechaza.
- **FR-014**: Activar una reprogramación MUST dejar superada la versión vigente anterior, y nunca dos vigentes.
- **FR-015**: Un borrador MUST poder descartarse sin borrarse.
- **FR-016**: Cerrar MUST exigir un programa vigente, sin borrador abierto, con motivo de 10 a 500 caracteres y MFA. Un programa cerrado no admite cambios.
- **FR-017**: Una versión no borrador y sus datos MUST ser inmutables, también ante escrituras directas en la base.
- **FR-018**: Ningún programa, versión, declaración, línea ni rubro MUST borrarse tras la activación, y la historia MUST ser inmutable.

**Acceso, auditoría e integraciones**

- **FR-019**: El proceso MUST tener tres capacidades: consultar; gestionar (rubros, programas, declaraciones, líneas, reprogramar, descartar); activar y cerrar, con MFA. Presupuesto recibe solo consulta: el administrador le asigna ese permiso, porque no existe un rol sembrado de Presupuesto. El administrador técnico no recibe autoridad por serlo.
- **FR-020**: Toda consulta y escritura MUST limitarse al ente activo. Lo ajeno responde «no encontrado» o «no válido» sin revelar datos, y el cliente no elige la empresa.
- **FR-021**: Toda escritura MUST exigir versión, y una versión vieja recibe un aviso de conflicto.
- **FR-022**: Cada escritura MUST auditarse con su autor, sin números de cuenta, y la historia MUST responder quién cambió qué y cuándo.
- **FR-023**: Auditoría institucional MUST incluir el proceso TRE-02 con rastreo a la ficha.
- **FR-024**: Las acciones registrar (crea el programa), activar, reprogramar y cerrar MUST registrarse en el catálogo de segregación de funciones, con la guarda en las tres últimas. No se crea ninguna regla.
- **FR-025**: El proceso MUST ser ejecutable desde Gobierno · Tesorería › Programación financiera, con su acceso al catálogo de rubros, y funcionar a 1280, 768 y 320 px con accesibilidad WCAG AA.

**Clasificación y delta**

- **FR-026**: REPORTING_COMPLETE = NOT_APPLICABLE y DOCUMENT_COMPLETE = NOT_APPLICABLE para TRE-02: GOV-TRE-002 no exige exportación ni documento.
- **FR-027**: TRE-01 pasa a TRE01_REPORTING_COMPLETE = NOT_APPLICABLE en las matrices, sin CSV y sin reabrirse.
- **FR-028**: Se añade la prueba de usuario OBS-TRE01-E2E-01.

### Key Entities

- **Rubro**: clase de ingreso o desembolso del ente, con código, nombre, tipo y estado.
- **Programa**: la programación de un ente para un ejercicio y una moneda, con mes inicial, estado y código.
- **Versión del programa**: número, estado (borrador, vigente, superada, descartada, cerrada), motivo y autoría.
- **Declaración de disponibilidad**: cuenta de TRE-01, monto, fecha de corte y fundamento.
- **Línea de programación**: rubro, mes y monto dentro de una versión.
- **Historia**: registro inmutable de cada cambio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tesorería completa por la interfaz crear, declarar, programar, activar, reprogramar y cerrar sin usar otra herramienta.
- **SC-002**: En el 100 % de los casos probados, la disponibilidad mostrada coincide al céntimo con la fórmula FR-007.
- **SC-003**: Ninguna prueba hostil obtiene o modifica datos de otro ente.
- **SC-004**: Ninguna versión activada cambia tras reprogramar o cerrar, comprobado también con escrituras directas.
- **SC-005**: Las pruebas de concurrencia no producen actualizaciones perdidas ni dos versiones vigentes.
- **SC-006**: Un usuario identifica en una sola pantalla período, moneda, cuentas, lo previsto, lo disponible, la versión vigente, quién la cambió y cuándo.
- **SC-007**: Los once procesos previos pasan su regresión sin cambios de contrato.

## Assumptions

- La disponibilidad es una proyección: no incluye pagos reales ni conciliación, que llegarán con TRE-03, TRE-04 y TRE-06.
- La comparación entre lo programado y lo ejecutado (art. 61) queda fuera: no hay pagos en el sistema.
- La disponibilidad negativa se admite con aviso, porque la norma contempla desequilibrios transitorios (art. 62).
- El programa empieza en un mes inicial y llega a diciembre.
- Las cuotas del art. 64 las aprueba un organismo externo y no se modelan.
- El catálogo de cuentas y su estado vienen de TRE-01; no se duplica ningún modelo de cuenta.
