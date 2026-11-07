# N40_REQUIREMENT_INVENTORY

Extraído por programa de `GOVERNMENT_REQUIREMENTS_PRODUCT_MATRIX.csv`. N40_REQUIREMENTS_TOTAL = 21. Procesos con N40 en NORMS o BLOCKERS antes del ciclo: 10 (ORG-06, DOC-01, DOC-03 solo por dependencia, DOC-05, DOC-07, CTL-02, CTL-03, DIG-02, DIG-03, HR-02). Requisitos fundamento: 9.

| REQUIREMENT_ID | PROCESS_ID | PRIORITY | REQUIREMENT_TEXT | OTHER_SOURCES | N40_REFERENCE_TYPE | CURRENT_STATUS | CURRENT_BLOCKER | EVIDENCE |
|---|---|---|---|---|---|---|---|---|
| GOV-ORG-007 | ORG-06 | P0 | Relacionar cada usuario con identidad, cargo, unidad y alcance institucional; el frontend nunca decide company | N20,N27 | Cita en fuente | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | IR |
| GOV-DOC-002 | DOC-01 | P0 | Mantener documentos originales, versiones, anexos, autor, fecha, firma y hash/integridad cuando tecnicamente a | N27,N29 | Condicional | BLOCKED | N40 acotada: verificación de firma (N40-02, N40-03) y clasificación solo APN (N40-01), en  | IR |
| GOV-DOC-006 | DOC-05 | P1 | Permitir firma electronica cuando sea juridica y tecnicamente procedente, sin asumir que sustituye formalidade | N29 | Cita en fuente | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | IR |
| GOV-DOC-008 | DOC-07 | P1 | Implementar busqueda por expediente, acto, tercero, contrato, presupuesto, bien y fecha con control de acceso. | N27 | Cita en fuente | BLOCKED | DOMAIN_DEPENDENCY: objetos de búsqueda inexistentes en Gobierno (DOC-01, CNT-01, BUD-03, A | IR |
| GOV-CTL-002 | CTL-02 | P0 | Registrar bitacora append-only de autenticacion, consultas sensibles, cambios, aprobaciones, rechazos y accion | N18,N20,N27 | Cita en fuente | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | IR |
| GOV-CTL-003 | CTL-02 | P0 | Mantener autor, actor efectivo, rol, unidad, IP/sesion tecnica, timestamp y correlacion de cada evento auditab | N20,N27 | Cita en fuente | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | IR |
| GOV-CTL-004 | CTL-03 | P0 | No permitir al administrador tecnico fabricar autoridad funcional para comprometer/pagar/aprobar. | N20,N23 | Cita en fuente | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | IR |
| GOV-DIG-004 | DIG-03 | P0 | Implementar API/intercambio con autenticacion, autorizacion, minimizacion, trazabilidad y contratos de datos. | N28,N27 | Cita en fuente | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | IR |
| GOV-DIG-009 | DIG-02 | P0 | Publicar estados y notificaciones sin exponer informacion reservada o datos innecesarios. | N27 | Cita en fuente | BLOCKED | D-GOV-06; N40 acotada: clasificación previa a publicar, solo APN (N40-01) | IR |
| GOV-DIG-010 | F21 | P0 | Usar tecnologias y estandares compatibles con la Ley de Infogobierno y politicas tecnicas vigentes del Estado. | N27 | Cita en fuente | NOT_MEASURED | Sin proceso funcional | IR |
| GOV-DIG-011 | DIG-03 | P1 | Registrar consentimiento/base de intercambio y restricciones cuando el marco juridico lo requiera; no crear un | N28 | Condicional | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | IR |
| GOV-DIG-012 | DIG-03 | P1 | Mantener inventario de interoperabilidades, responsable, contrato, SLA, version y plan de contingencia. | N28,N20 | Cita en fuente | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | IR |
| GOV-HR-005 | HR-02 | P0 | Mantener enlace entre empleado/cargo/unidad/centro presupuestario y pago agregado sin exponer datos laborales  | N20,N27 | Cita en fuente | BLOCKED | D-GOV-07; N40 acotada: clasificación de datos de personal, solo APN (N40-01); transporte s | IR |
| RNF-GOV-001 | F05 F06 | P0 | Aislamiento Cada tenant/ente debe tener aislamiento de datos, llaves, configuracion y permisos; pruebas hostil | N20,N27 | Cita en fuente | PARTIAL | Sin proceso funcional | IR |
| RNF-GOV-006 | F03 F04 | P0 | Autorizacion Toda autorizacion critica se valida en backend; no confiar en UI ni claims sin verificacion conte | N20 | Cita en fuente | PASS | Sin proceso funcional | IR |
| RNF-GOV-010 | F11 F12 | P0 | Disponibilidad Definir RTO/RPO por instalacion y validar backup/restore antes de produccion. | N20,N27 | Cita en fuente | PARTIAL | Sin proceso funcional | IR |
| RNF-GOV-011 | F01 F18 | P0 | Seguridad Cifrado en transito, secretos fuera de codigo, MFA para roles privilegiados y rotacion de credencial | N27 | Cita en fuente | PARTIAL | Sin proceso funcional | IR |
| RNF-GOV-015 | F10 | P0 | Interoperabilidad APIs versionadas, contrato de esquema, errores deterministas y trazabilidad de mensajes. | N28 | Cita en fuente | PASS | Sin proceso funcional | IR |
| RNF-GOV-017 | F22 | P0 | Observabilidad Logs estructurados, metricas, health checks y correlacion sin filtrar secretos o datos innecesa | N20,N27 | Cita en fuente | PARTIAL | Sin proceso funcional | IR |
| RNF-GOV-021 | F26 | P0 | Privacidad operativa Minimizar exposicion de cedulas, bancos, declaraciones y datos personales por rol/finalid | N20,N27 | Cita en fuente | NOT_MEASURED | Sin proceso funcional | IR |
| RNF-GOV-023 | F16 | P0 | Configuracion segura Valores regulatorios y endpoints no se hardcodean; cambios requieren control de acceso y  | N20 | Cita en fuente | NOT_STARTED | Sin proceso funcional | IR |
