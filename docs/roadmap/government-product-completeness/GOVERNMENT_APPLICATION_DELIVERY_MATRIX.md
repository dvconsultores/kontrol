# GOVERNMENT_APPLICATION_DELIVERY_MATRIX

Vista centrada en el usuario, generada desde `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`. No sustituye a esa matriz. El estado responde: ¿puede el usuario ejecutar el proceso en la aplicación?

El sponsor no enumera pantallas por proceso: `REQUIRED_SCREENS` solo se conoce donde el proceso ya se diseñó. Por eso no hay total de pantallas requeridas.

| Proceso | Requisitos | Módulo | Rol | Proceso de negocio | Menú | Pantalla | Backend | Reportes | Auditoría | ¿Ejecutable? | Estado | Falta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORG-01 | GOV-ORG-001 | Government Core: ente, estru | Administración institucional | Configurar el ente y su tipo | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | — |
| ORG-02 | GOV-ORG-002 GOV-ORG-008 | Government Core: ente, estru | Administración institucional | Estructura organizativa por ejercicio (órgano, unidad ejecutora, depen | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| ORG-03 | GOV-ORG-003 | Government Core: ente, estru | Máxima autoridad | Cargos con competencias y límites de firma/aprobación | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| ORG-04 | GOV-ORG-004 GOV-ORG-009 | Government Core: ente, estru | Máxima autoridad | Delegaciones, suplencias, encargadurías y designaciones con acto | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| ORG-05 | GOV-ORG-006 | Government Core: ente, estru | Administración institucional | Responsables por unidad, programa, cuenta, almacén, caja, contrato y b | no | no | no | no | no | no | NOT_STARTED (bloqueado) | DOMAIN_DEPENDENCY: 8 de 9 objetos sin modelo en Gobierno (BUD-03, ACC-01, WH-02, TRE-08, TRE-01, CNT-01, AST-01); MATERI |
| ORG-06 | GOV-ORG-007 GOV-ORG-005 | Government Core: ente, estru | Administración institucional | Vincular usuario con identidad, cargo, unidad y alcance; separación de | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| ORG-07 | GOV-ORG-010 | Government Core: ente, estru | Control Interno | Matriz auditable de quién puede solicitar, comprometer, causar, pagar, | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| BUD-01 | GOV-BUD-001 | Presupuesto público (Budget  | Planificación/Presupuesto | Ejercicio económico-financiero | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N1 |
| BUD-02 | GOV-BUD-002 | Presupuesto público (Budget  | Planificación/Presupuesto | Clasificador presupuestario versionado | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N10 (clase C) |
| BUD-03 | GOV-BUD-003 GOV-BUD-004 | Presupuesto público (Budget  | Planificación/Presupuesto | Plan, programas, proyectos, metas físicas e indicadores | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) |
| BUD-04 | GOV-BUD-005 | Presupuesto público (Budget  | Planificación/Presupuesto | Fuentes de financiamiento y restricciones | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) |
| BUD-05 | GOV-BUD-006 GOV-BUD-007 GOV-BUD-008 | Presupuesto público (Budget  | Planificación/Presupuesto | Formulación: anteproyecto, proyecto y presupuesto aprobado con su acto | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N3 |
| BUD-06 | GOV-BUD-009 GOV-BUD-010 | Presupuesto público (Budget  | Planificación/Presupuesto | Disponibilidad y certificación de disponibilidad | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| BUD-07 | GOV-BUD-011 | Presupuesto público (Budget  | Planificación/Presupuesto | Precompromiso / reserva | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| BUD-08 | GOV-BUD-012 | Presupuesto público (Budget  | Planificación/Presupuesto | Compromiso presupuestario | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| BUD-09 | GOV-BUD-013 | Presupuesto público (Budget  | Planificación/Presupuesto | Causado / devengado | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N36 (clase C) |
| BUD-10 | GOV-BUD-014 GOV-BUD-015 | Presupuesto público (Budget  | Planificación/Presupuesto | Modificaciones presupuestarias con flujo de aprobación (E2E-02) | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N09 (clase C); LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| BUD-11 | GOV-BUD-016 | Presupuesto público (Budget  | Planificación/Presupuesto | Ledger presupuestario inmutable y reconstruible | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| BUD-12 | GOV-BUD-017 | Presupuesto público (Budget  | Planificación/Presupuesto | Cierre y reconducción del ejercicio | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| BUD-13 | GOV-BUD-018 | Presupuesto público (Budget  | Planificación/Presupuesto | Formularios y reportes ONAPRE | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N0 |
| REQ-01 | GOV-REQ-001 GOV-REQ-003 GOV-REQ-006 GOV-REQ-007 GOV-REQ-008 GOV-REQ-009 | Requisiciones públicas | Unidad requirente | Registrar necesidad/requisición (bienes, servicios u obras) con estima | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| REQ-02 | GOV-REQ-002 | Requisiciones públicas | Planificación/Presupuesto | Verificación presupuestaria previa a la contratación | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| REQ-03 | GOV-REQ-004 | Requisiciones públicas | Unidad contratante | Consolidar necesidades compatibles | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REQ-04 | GOV-REQ-005 | Requisiciones públicas | Control Interno | Alertas de fraccionamiento | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REQ-05 | GOV-REQ-010 | Requisiciones públicas | Unidad requirente | Cerrar o cancelar requisición liberando reservas | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| PROC-01 | GOV-PROC-001 GOV-PROC-002 GOV-PROC-016 | Contrataciones públicas / Li | Unidad contratante | Determinar la modalidad de selección y conservar la regla y las excepc | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| PROC-02 | GOV-PROC-003 | Contrataciones públicas / Li | Máxima autoridad | Comisión de contrataciones (miembros, suplentes, impedimentos) | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | — |
| PROC-03 | GOV-PROC-004 GOV-PROC-014 | Contrataciones públicas / Li | Unidad contratante | Expediente único de contratación con cronología y lapsos | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| PROC-04 | GOV-PROC-005 GOV-PROC-015 | Contrataciones públicas / Li | Unidad contratante | Pliego, invitaciones, aclaratorias, prórrogas y avisos | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-03 |
| PROC-05 | GOV-PROC-006 | Contrataciones públicas / Li | Unidad contratante | Oferentes y contratistas (RNC/SNC) | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-03 |
| PROC-06 | GOV-PROC-007 | Contrataciones públicas / Li | Unidad contratante | Recepción y apertura de ofertas | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| PROC-07 | GOV-PROC-008 GOV-PROC-009 | Contrataciones públicas / Li | Comisión | Evaluación técnica, económica y legal con matriz bloqueada | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | Reporte propio: n/a (lo es la recomendación de PROC-08) |
| PROC-08 | GOV-PROC-010 GOV-PROC-011 | Contrataciones públicas / Li | Máxima autoridad | Recomendación, decisión, adjudicación, desierta, anulación o rechazo | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| PROC-09 | GOV-PROC-012 | Contrataciones públicas / Li | Unidad contratante | Compromiso de responsabilidad social | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| PROC-10 | GOV-PROC-013 | Contrataciones públicas / Li | Unidad contratante | Garantías y cauciones | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| PROC-11 | GOV-PROC-017 | Contrataciones públicas / Li | Control Interno | Conflictos SoD en contratación | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| PROC-12 | GOV-PROC-018 | Contrataciones públicas / Li | Control Interno | Trazabilidad completa de la compra pública (E2E-01) | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-01 | GOV-CNT-001 | Contratos públicos | Unidad contratante | Crear contrato u orden desde la adjudicación | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-02 | GOV-CNT-002 | Contratos públicos | Unidad contratante | Adendas, prórrogas y variaciones versionadas | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-03 | GOV-CNT-003 GOV-CNT-007 | Contratos públicos | Administrador/Supervisor de contrato | Ejecución: hitos, entregables, valuaciones, recepciones y cierre; fact | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-04 | GOV-CNT-004 | Contratos públicos | Máxima autoridad | Designación del supervisor del contrato | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| CNT-05 | GOV-CNT-005 | Contratos públicos | Tesorería | Bloqueo de pagos por encima del monto contractual | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-06 | GOV-CNT-006 | Contratos públicos | Administrador de contrato | Penalidades, retenciones, anticipos, amortizaciones y garantías del co | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N38 (clase C) |
| CNT-07 | GOV-CNT-008 | Contratos públicos | Máxima autoridad | Terminación, resolución o rescisión | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-08 | GOV-CNT-009 | Contratos públicos | Administrador de contrato | Expediente contractual completo | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CNT-09 | GOV-CNT-010 | Contratos públicos | Administrador de contrato | Alertas de vencimientos | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| WH-01 | GOV-WH-001 GOV-WH-002 | Almacén de consumo público | Almacén/Recepción | Recepción física contra orden/contrato separando consumo, capitalizabl | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N15 (clase C) |
| WH-02 | GOV-WH-003 GOV-WH-006 GOV-WH-007 | Almacén de consumo público | Almacén/Recepción | Inventario por almacén y movimientos sin negativo silencioso; consumo  | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| WH-03 | GOV-WH-004 | Almacén de consumo público | Almacén/Recepción | Salidas autorizadas con destino y beneficiario | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| WH-04 | GOV-WH-005 | Almacén de consumo público | Almacén/Recepción | Conteos físicos y conciliación con aprobación de ajustes | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| WH-05 | GOV-WH-008 | Almacén de consumo público | Almacén/Recepción | Kardex reproducible por artículo, almacén y período | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| TRE-01 | GOV-TRE-001 | Tesorería pública | Tesorería | Cuentas bancarias públicas con autorizados y acto habilitante | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | — |
| TRE-02 | GOV-TRE-002 | Tesorería pública | Tesorería | Programación financiera y disponibilidad de caja | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | — |
| TRE-03 | GOV-TRE-003 | Tesorería pública | Tesorería | Orden de pago desde obligación causada | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| TRE-04 | GOV-TRE-004 GOV-TRE-005 GOV-TRE-010 | Tesorería pública | Tesorería | Pago con maker-checker, medios autorizados y bloqueo de duplicados | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| TRE-05 | GOV-TRE-006 | Tesorería pública | Tesorería | Retenciones tributarias/contractuales y comprobantes | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C); LEGAL_VALIDATION_REQUIRED N38 (clase C) |
| TRE-06 | GOV-TRE-007 | Tesorería pública | Tesorería | Conciliación bancaria | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| TRE-07 | GOV-TRE-008 | Tesorería pública | Tesorería | Anulación y reverso de pago | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| TRE-08 | GOV-TRE-009 | Tesorería pública | Tesorería | Fondos y cajas autorizadas: reposición, rendición y arqueo | no | no | no | no | no | no | NOT_STARTED (bloqueado) | DOMAIN_DEPENDENCY: TRE-03/TRE-04 (orden de pago), BUD (compromiso y causado), ORG-06 (funcionario responsable) |
| TRE-09 | GOV-TRE-011 | Tesorería pública | Tesorería | Provenance de tasas BCV | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| TRE-10 | GOV-TRE-012 | Tesorería pública | Control Interno | Trazabilidad del pago hasta presupuesto y contrato | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| ACC-01 | GOV-ACC-002 GOV-ACC-012 | Contabilidad pública | Contabilidad | Plan de cuentas, mapeos presupuesto-contabilidad e historial de reglas | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) |
| ACC-02 | GOV-ACC-001 GOV-ACC-003 GOV-ACC-004 GOV-ACC-005 | Contabilidad pública | Contabilidad | Asientos de doble partida automáticos y manuales; momentos contables;  | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) |
| ACC-03 | GOV-ACC-006 | Contabilidad pública | Contabilidad | Cierres mensuales y anuales con checklist y reapertura excepcional | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| ACC-04 | GOV-ACC-007 | Contabilidad pública | Contabilidad | Balance de comprobación, estados y auxiliares | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) |
| ACC-05 | GOV-ACC-008 | Contabilidad pública | Contabilidad | Conciliación presupuesto vs contabilidad vs tesorería vs cuentas por p | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| ACC-06 | GOV-ACC-009 | Contabilidad pública | Contabilidad | Terceros y beneficiarios | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N38 (clase C) |
| ACC-07 | GOV-ACC-010 | Contabilidad pública | Contabilidad | Multimoneda autorizada | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| ACC-08 | GOV-ACC-011 | Contabilidad pública | Contabilidad | Exportaciones a sistemas rectores | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04 |
| AST-01 | GOV-AST-001 GOV-AST-003 GOV-AST-004 GOV-AST-005 | Bienes públicos / Activo fij | Bienes/Patrimonio | Incorporación del bien: registro, categoría, origen y valor | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C); LEGAL_VALIDATION_REQUIRED N17 (clase C); LEGAL_VALIDATION_REQUIRED N3 |
| AST-02 | GOV-AST-002 | Bienes públicos / Activo fij | Bienes/Patrimonio | Codificación y etiquetado SUDEBIP | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C) |
| AST-03 | GOV-AST-006 | Bienes públicos / Activo fij | Bienes/Patrimonio | Ubicación y custodia con historial | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| AST-04 | GOV-AST-007 | Bienes públicos / Activo fij | Bienes/Patrimonio | Transferencias internas e inter-ente con acta | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| AST-05 | GOV-AST-008 | Bienes públicos / Activo fij | Bienes/Patrimonio | Inventario físico patrimonial por campaña | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| AST-06 | GOV-AST-009 | Bienes públicos / Activo fij | Bienes/Patrimonio | Revalorización con avalúo | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N14 (clase C) |
| AST-07 | GOV-AST-010 | Bienes públicos / Activo fij | Bienes/Patrimonio | Arrendamiento de bienes públicos | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N16 (clase C) |
| AST-08 | GOV-AST-011 | Bienes públicos / Activo fij | Bienes/Patrimonio | Mantenimiento documental mínimo | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| AST-09 | GOV-AST-012 GOV-AST-013 | Bienes públicos / Activo fij | Bienes/Patrimonio | Desincorporación (baja, enajenación, pérdida, robo) sin borrado físico | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-05; LEGAL_VALIDATION_REQUIRED N17 (clase C) |
| AST-10 | GOV-AST-014 | Bienes públicos / Activo fij | Contabilidad | Relación con contabilidad y depreciación/valoración | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) |
| AST-11 | GOV-AST-015 | Bienes públicos / Activo fij | Bienes/Patrimonio | Actas de entrega de bienes por cambio de autoridad o custodio | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| DOC-01 | GOV-DOC-001 GOV-DOC-002 | Expedientes y actos administ | Unidad tramitadora | Expediente electrónico único con índice, foliado y versiones | no | no | no | no | no | no | NOT_STARTED (bloqueado) | N40 acotada: verificación de firma (N40-02, N40-03) y clasificación solo APN (N40-01), en revisión profesional; el exped |
| DOC-02 | GOV-DOC-003 | Expedientes y actos administ | Máxima autoridad | Actos administrativos con autoridad, motivación y eficacia | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| DOC-03 | GOV-DOC-004 | Expedientes y actos administ | Unidad tramitadora | Lapsos, suspensiones, subsanaciones y prórrogas | no | no | no | no | no | no | NOT_STARTED (bloqueado) | DOC-01 (expediente, N40 acotada); calendario oficial sin fuente ni responsable |
| DOC-04 | GOV-DOC-005 | Expedientes y actos administ | Unidad tramitadora | Notificaciones administrativas con constancia de recepción | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| DOC-05 | GOV-DOC-006 | Expedientes y actos administ | Máxima autoridad | Firma electrónica | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) |
| DOC-06 | GOV-DOC-007 GOV-DOC-009 | Expedientes y actos administ | Unidad tramitadora | Preservación y retención de evidencia sin borrado | no | no | no | no | no | no | NOT_STARTED (bloqueado) | LEGAL_VALIDATION_REQUIRED N37 (clase C) |
| DOC-07 | GOV-DOC-008 | Expedientes y actos administ | Usuarios autorizados | Búsqueda por expediente, acto, tercero, contrato, presupuesto, bien y  | no | no | no | no | no | no | NOT_STARTED (bloqueado) | DOMAIN_DEPENDENCY: objetos de búsqueda inexistentes en Gobierno (DOC-01, CNT-01, BUD-03, AST-01, terceros) |
| DOC-08 | GOV-DOC-010 | Expedientes y actos administ | Control Interno | Paquete de auditoría exportable | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| CTL-01 | GOV-CTL-001 | Control interno, auditoría y | Control Interno | Matriz SoD por proceso y detección previa | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| CTL-02 | GOV-CTL-002 GOV-CTL-003 | Control interno, auditoría y | Control Interno | Bitácora institucional append-only con actor, autoridad, unidad y corr | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| CTL-03 | GOV-CTL-004 | Control interno, auditoría y | Control Interno | Administrador técnico sin autoridad funcional | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CTL-04 | GOV-CTL-005 | Control interno, auditoría y | Auditor interno/externo | Consulta y muestreo read-only del auditor | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| CTL-05 | GOV-CTL-006 GOV-CTL-007 | Control interno, auditoría y | Control Interno | Expediente de cuenta y reportes de rendición | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CTL-06 | GOV-CTL-008 | Control interno, auditoría y | Control Interno | Hallazgos y planes de acción correctiva | sí | sí | sí | sí | sí | sí | OWNER_UAT_READY | — |
| CTL-07 | GOV-CTL-009 | Control interno, auditoría y | Control Interno | Alertas de operaciones atípicas | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CTL-08 | GOV-CTL-010 | Control interno, auditoría y | Control Interno | Historial de cambios de maestros sensibles | no | no | no | no | no | no | NOT_STARTED (bloqueado) | DOMAIN_DEPENDENCY: maestros de proveedores (PROC-01/GOV-ACC-009, N37) y clasificadores (BUD-02, D-GOV-02, N10) inexisten |
| CTL-09 | GOV-CTL-011 | Control interno, auditoría y | Máxima autoridad | Actas de entrega por cambio de responsable o autoridad | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| CTL-10 | GOV-CTL-012 | Control interno, auditoría y | Control Interno | Controles materiales que impiden cerrar ejercicio o proceso | sí | sí | sí | n/a | sí | sí | OWNER_UAT_READY | — |
| DIG-01 | GOV-DIG-001 GOV-DIG-002 GOV-DIG-008 | Gobierno Digital: trámites e | Unidad de trámites | Catálogo de trámites con requisitos versionados y captura única | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-06 |
| DIG-02 | GOV-DIG-006 GOV-DIG-007 GOV-DIG-009 | Gobierno Digital: trámites e | Ciudadano / Unidad de trámites | Solicitud, subsanación y seguimiento del trámite con estado visible (E | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-06; N40 acotada: clasificación previa a publicar, solo APN (N40-01) |
| DIG-03 | GOV-DIG-003 GOV-DIG-004 GOV-DIG-005 GOV-DIG-011 GOV-DIG-012 | Gobierno Digital: trámites e | Integración | Interoperabilidad: datos del Estado, API, provenance, base de intercam | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) |
| HR-01 | GOV-HR-001 GOV-HR-003 | Gasto de personal e interfaz | Planificación/Presupuesto | Estructura de cargos y plantillas presupuestarias de personal | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING); LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N0 |
| HR-02 | GOV-HR-002 GOV-HR-004 GOV-HR-005 | Gasto de personal e interfaz | Contabilidad | Interfaz de nómina Atenea con maker-checker y sin duplicados (E2E-04) | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING); N40 acotada: clasificación de datos de personal, solo APN (N40-01); t |
| HR-03 | GOV-HR-006 | Gasto de personal e interfaz | Recursos humanos | Reportes SISROE y de altos funcionarios | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| INT-01 | IR §11/§12 | Integraciones institucionale | Integración | Atenea: lotes de nómina idempotentes | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING) |
| INT-02 | IR §11/§12 | Integraciones institucionale | Integración | Bancos: archivos/APIs con contrato del banco | no | no | no | n/a | no | no | NOT_STARTED | Todo el proceso |
| INT-03 | IR §11/§12 | Integraciones institucionale | Integración | SNC/RNC: consulta de contratistas con provenance | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-03 |
| INT-04 | IR §11/§12 | Integraciones institucionale | Integración | SUDEBIP: reportes y codificación por mecanismo oficial | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-05 |
| INT-05 | IR §11/§12 | Integraciones institucionale | Integración | ONAPRE/ONCOP: formatos oficiales versionados | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-02; D-GOV-04 |
| INT-06 | IR §11/§12 | Integraciones institucionale | Integración | Interoperabilidad del Estado (N26/N28) | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-08 |
| INT-07 | IR §11/§12 | Integraciones institucionale | Integración | Firma electrónica: proveedor o certificado homologado | no | no | no | n/a | no | no | NOT_STARTED (bloqueado) | D-GOV-08 |
| REP-01 | IR §11/§12 | Reportes y tableros instituc | Planificación/Presupuesto | Ejecución presupuestaria (aprobado, modificado, comprometido, causado, | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02 |
| REP-02 | IR §11/§12 | Reportes y tableros instituc | Planificación/Presupuesto | Plan vs presupuesto vs ejecución físico-financiera | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-02 |
| REP-03 | IR §11/§12 | Reportes y tableros instituc | Unidad contratante | Contrataciones por modalidad, estado, unidad, proveedor, monto y tiemp | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-04 | IR §11/§12 | Reportes y tableros instituc | Administrador de contrato | Contratos: comprometido, ejecutado, pagado, garantías y vencimientos | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-05 | IR §11/§12 | Reportes y tableros instituc | Tesorería | Obligaciones causadas pendientes de orden o pago | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-06 | IR §11/§12 | Reportes y tableros instituc | Tesorería | Tesorería: disponibilidad, pagos, conciliaciones y partidas en tránsit | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-07 | IR §11/§12 | Reportes y tableros instituc | Contabilidad | Contabilidad: balance, diario, mayor, auxiliares y cierres | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-04 |
| REP-08 | IR §11/§12 | Reportes y tableros instituc | Bienes/Patrimonio | Bienes públicos: inventario, custodios, ubicaciones, diferencias y des | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-05 |
| REP-09 | IR §11/§12 | Reportes y tableros instituc | Control Interno | Rendición de cuentas por responsable y período | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-10 | IR §11/§12 | Reportes y tableros instituc | Control Interno | Control interno: overrides, conflictos SoD, duplicados, hallazgos | no | no | no | no | no | no | NOT_STARTED | Todo el proceso |
| REP-11 | IR §11/§12 | Reportes y tableros instituc | Unidad de trámites | Trámites: volumen, tiempos, subsanaciones y cuellos de botella | no | no | no | no | no | no | NOT_STARTED (bloqueado) | D-GOV-06 |

## Métricas de pantallas (corrección de la dueña, 2026-11-09)

Una ruta declarada no demuestra que la pantalla funcione. Una pantalla cuenta como verificada en navegador solo si frontend y backend reales funcionan juntos en un navegador.

| Métrica | Valor | Nota |
|---|---|---|
| `DECLARED_GOVERNMENT_ROUTES` | 59 | Rutas `gobierno/` en `pantallas.ts` |
| `BROWSER_VERIFIED_GOVERNMENT_SCREENS` | 8 medidas | PROC-02 y PROC-03 (4 cada uno). Las de los otros 16 procesos tienen E2E propia pero no se han medido con este criterio |
| `OWNER_UAT_READY_SCREENS` | Sin medir por pantalla | Se publica por proceso: 18 |
| `TOTAL_REQUIRED_SCREENS` | No se inventa | El sponsor no lo enumera |

## PROC-02: clasificación corregida

`PROC02_FUNCTIONAL_SLICE_COMPLETE = 1`; `OWNER_UAT_READY_PROC02 = YES`; `PROC02_FULL_BROWSER_ACTION_MATRIX_VERIFIED = NO`: descartar, retirar en borrador y designar con la comisión vigente no se ejercitaron por interfaz. No bloquea PROC-03.

## PROC-03 en detalle

| Requisito | Rol | Proceso | Superficie | Backend | BD | API | Permiso | Documentos | Auditoría | Navegador | UAT | Estado | Falta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GOV-PROC-004 | Unidad contratante | Expediente único | Listado, nuevo, ficha, editar | sí | 0080 | 16 rutas | `gobierno_expedientes` | Spec 046 y DOC-02, con folio | CTL-02, 13 eventos | sí, flujo principal | sí | OWNER_UAT_READY | Acciones auxiliares por interfaz; bitácora sin filtro por expediente |
| GOV-PROC-014 | Unidad contratante | Hitos y lapsos | Hitos y lapsos, cronología | sí | 0080 | hitos | `gobierno_expedientes:manage` | Folio ligado a hito | CTL-02 | sí: crear y fecha real | sí | OWNER_UAT_READY | Cálculo de lapsos: bloqueado por calendario DOC-03 |

## Actualización 2026-11-09

`PROC03_FUNCTIONAL_SLICE_COMPLETE = 1`: ficha y lista verificadas también a 320 y 390 px, con Axe dirigido sin violaciones. PROC-06 **no** está entregado: su estado en esta matriz no cambia.

## PROC-07 en detalle (2026-11-10, commit 4c4be3d)

| Requisito | Rol | Proceso | Superficie | Backend | BD | API | Permiso | Documentos | Auditoría | Navegador | UAT | Estado | Falta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GOV-PROC-008 | Comisión | Apertura y evaluación | Sección «Apertura y evaluación» en la ficha | sí | 0092 | 9 rutas | `gobierno_evaluacion` view/open/evaluate | Acta en Documentos; sello levantado con traza | CTL-02, 8 eventos | sí, flujo completo | sí | OWNER_UAT_READY | — |
| GOV-PROC-009 | Comisión | Matriz bloqueada | Matriz por aspecto, bloqueo | sí | 0092 | matriz, criterios, bloquear | `gobierno_evaluacion:criteria` | Pliego anclado con versión | CTL-02 | sí: bloqueo y rechazo posterior | sí | OWNER_UAT_READY | Sin cambio motivado (decisión de la dueña) |

`PROC07_FUNCTIONAL_SLICE_COMPLETE = 1`: verificado en Chromium a 1280, 390 y 320 px, con Axe dirigido en 4 puntos sin violaciones. `OWNER_ACCEPTED = NO`. PROC-06 (GOV-PROC-007) se publicó en 7e7d70d, pero su fila sigue sin actualizar: es una deuda previa (OBS-MATRIZ-PROC06-01).
