# CTL-03 · Decisiones y CONSTITUTION GATE (2026-11-11)

Decisiones de diseño de Claude (PDD), dentro de lo ya decidido (OD-DEL-10..12, ORG-03, ORG-04, ORG-06). Ninguna requiere a la
dueña: `MATERIAL_DECISION_REQUIRED = 0`.

| Id | Decisión |
|---|---|
| PDD-CTL03-01 | Escenario A: la matriz no halló fabricación posible. No se toca ninguna autoridad propietaria ni se crea un «guard CTL-03»; no hay migración. |
| PDD-CTL03-02 | «Administrador técnico» se decide por capacidades, no por nombre: cuenta con alguna de `SECURITY_ADMIN_CAPABILITIES` (`users:create`, `roles:edit`, `users:mfa_reset`) que valga en el ente. Un rol «ADMIN2» o «ROOT» con esas capacidades cuenta; el rol ADMIN sin ellas no existe. |
| PDD-CTL03-03 | Un rol es técnico si todas sus capacidades están en `TECHNICAL_CAPABILITIES`; si no, es funcional. Se reutiliza la constante de la Spec 003; sin segunda taxonomía. Las categorías de ORG-06 (incluida ADMINISTRACION_TECNICA) se muestran como metadato del ente, sin reemplazar esta regla. |
| PDD-CTL03-04 | La autoridad institucional derivada es la de ORG-06 (`contexto_institucional`): vínculo vigente → funcionario → ocupaciones que ejerce → cargo → competencias acción × materia. Tener un permiso funcional no es tener autoridad institucional. |
| PDD-CTL03-05 | Estados de separación por cuenta: **Solo técnico** (ningún rol funcional en el ente); **Técnico y funcional, con autoridad institucional** (roles funcionales concedidos aparte y vínculo con ocupación que ejerce); **Técnico y funcional, sin autoridad institucional** (roles funcionales sin vínculo vigente u ocupación; se muestra el motivo de ORG-06). Tener ambas funciones no es un conflicto. |
| PDD-CTL03-06 | Indicador de riesgo solo con evidencia: «Separación íntegra» si el rol protegido ADMIN no contiene ninguna capacidad fuera de las técnicas y FUNCIONAL_COMPLETO no contiene ninguna técnica; si no, «Separación alterada» con las capacidades fuera de lugar. No se marca riesgo por tener mucho acceso. |
| PDD-CTL03-07 | Origen de cada rol: el evento ROLE_ASSIGNED de su asignación (`entity_id` = asignación). Fuente SETUP → «Concedido en la instalación»; API → «Concedido por <usuario> el <fecha>»; sin evento → «Origen no registrado». |
| PDD-CTL03-08 | Evidencia de denegaciones: AuditEvent con acción AUTHORITY_DELEGATION_DENIED, LAST_ADMIN_OPERATION_DENIED, COMPANY_SCOPE_DENIED o GOV_IDENTITY_GUARD_BLOCKED, últimas 50, del tenant, con alcance del ente (evento con la empresa del ente, o sin empresa y con evidencia sin empresa o de este ente, de una cuenta con acceso al ente). Enlace a la bitácora solo para los eventos que la bitácora muestra; el resto se muestra en línea. Sin segunda bitácora. |
| PDD-CTL03-09 | La exigencia de identidad del ente (OD-ORG06-09) se muestra con su estado y su efecto: inactiva = las acciones protegidas no comprueban el cargo del usuario. Informativo; CTL-03 no la cambia. |
| PDD-CTL03-10 | Permiso de la pantalla: `gobierno_auditoria:view` (Control Interno; el mismo de la bitácora). Sin capacidad nueva, sin entrada de catálogo de auditoría nueva (la consulta no muta). Sólo lectura: ninguna acción de autoridad; enlaces a Usuarios, Identidad institucional y Bitácora según los permisos del usuario. |
| PDD-CTL03-11 | Ruta `/gobierno/control/separacion`, menú Gobierno, junto a la bitácora: «Separación técnica y funcional». API `GET /api/v1/gobierno/control/separacion`. |
| PDD-CTL03-12 | Prueba funcional sobre una acción real existente: emitir un acto DOC-02 (OD-ORG06-10) con la exigencia de identidad activa. Comprometer y pagar no existen en Gobierno: `COMMIT_PROCESS_NOT_IMPLEMENTED`, `PAY_PROCESS_NOT_IMPLEMENTED`; el control es transversal y lo usarán. |
| PDD-CTL03-13 | Invariantes permanentes: (a) ningún endpoint de mutación bajo `/gobierno`, `/aprobaciones` y los de autoridad de plataforma distintos de usuarios y roles se protege con una capacidad técnica; (b) en la cabeza de Alembic, ADMIN tiene exactamente capacidades técnicas y FUNCIONAL_COMPLETO ninguna técnica; (c) ADMIN puro: autoescalada, concesión a otro y rol sombra rechazados sin mutación, y tarea técnica permitida. |

## CONSTITUTION GATE

| Compuerta | Resultado | Motivo |
|---|---|---|
| SECURITY | PASS | Sólo lectura; permiso existente; alcance por ente; no amplía ninguna superficie |
| DATA_INTEGRITY | PASS | Sin escrituras ni tablas nuevas; proyección de autoridades existentes |
| LEGAL / NORMATIVE | PASS | N20 arts. 30, 32 y 39 num. 3 y 8; N23 arts. 6 y 7, leídos en copia oficial |
| ARCHITECTURAL | PASS | Reutiliza Spec 003, ORG-06 y AuditEvent; sin segundo motor |
| TESTABILITY | PASS | PostgreSQL y Chromium con actores reales |
| DOMAIN_DEPENDENCY | PASS | No depende de compromiso ni pago; los declara no implementados |

`CONSTITUTION_GATE = PASS`. `MATERIAL_DECISION_REQUIRED = 0`.
