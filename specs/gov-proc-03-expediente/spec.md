# PROC-03 · Expediente único de contratación (GOV-PROC-004, GOV-PROC-014)

**Autorización**: mandato de la dueña «PROCUREMENT-RELEASE-02 · PROC-03», 2026-11-08 (Constitución P2).
**Fuentes verificadas** en `evidence/FUENTES.md`: LCP arts. 6 (26-29), 18, 19, 20; RLCP arts. 31, 32, 33.

## Qué podrá hacer el usuario que antes no podía

Llevar en un solo lugar el expediente de una contratación: identificarlo como pide la ley, saber quién responde y qué
comisión interviene, incorporar documentos y actos en orden, registrar actuaciones y decisiones, mantener hitos con fechas
previstas y reales, y leer la cronología, lo pendiente y el siguiente paso.

## Historias

- **US1 Crear y consultar (P1)**: la unidad crea el expediente con número, fecha de iniciación, objeto, tipo, unidad y
  responsable; lo encuentra en un listado con búsqueda y filtros; abre una ficha que responde qué contratación es, en qué
  estado está, quién responde, qué comisión interviene, qué ocurrió, qué documentos hay, cuál es el próximo hito y qué falta.
- **US2 Sustanciar (P1)**: registra responsables, vincula la comisión o declara que no interviene, incorpora documentos y
  actos con folio, registra actuaciones y decisiones, y rectifica sin borrar.
- **US3 Hitos y lapsos (P1)**: crea hitos con fecha prevista y fuente, registra la fecha real, reprograma con motivo.
- **US4 Cronología (P1)**: lee la historia del expediente, que no se reescribe.
- **US5 Cerrar o descartar (P2)**: cierra el expediente con fecha y motivo, o descarta uno creado por error sin contenido.

## Requisitos

- **FR-001** Identificación (LCP art. 19): número asignado por el ente y único en él, fecha de iniciación, objeto, partes.
- **FR-002** Tipo: bienes, servicios u obras (RLCP art. 33).
- **FR-003** Modalidad **declarada**, con fundamento y fuente; el sistema no la determina, no valida umbrales ni la legalidad de una
  excepción (PROC-01 bloqueado por N37). Solo ofrece las cuatro modalidades que define LCP art. 6.
- **FR-004** Unidad responsable (ORG-02) y responsables (ORG-04) con cargo y unidad a la fecha; nunca una cuenta de usuario ni un
  empleado de Atenea. Un solo responsable principal vigente.
- **FR-005** Comisión: se vincula una comisión de PROC-02 en vigor, o se declara con motivo que no interviene (RLCP art. 33). No se
  copian sus miembros.
- **FR-006** Folios (LCP art. 19): cada documento o acto incorporado recibe un número correlativo por orden de incorporación y la fecha
  de incorporación la pone el sistema. Un folio no se borra ni cambia. Se conserva la versión incorporada.
- **FR-007** Clases de contenido de RLCP art. 32: 13 de selección y 10 de administración del contrato. La ficha muestra cuáles faltan,
  como aviso, porque varias dependen del caso («si las hubiere», «si fuere el caso»).
- **FR-008** Documentos reutilizando la gestión documental (Spec 046) y actos reutilizando DOC-02: nada de texto libre para un acto.
- **FR-009** Actuaciones y decisiones con fecha, responsable, descripción y, si cabe, acto y folio. Una decisión exige resultado. No
  se exige acto a todo evento. Una rectificación crea un registro nuevo con motivo y señala al anterior.
- **FR-010** Hitos: nombre, fuente, fecha prevista, fecha real, responsable, estado. Reprogramar, corregir la fecha real o marcar «no aplica»
  exige motivo. Nada calcula lapsos, días hábiles ni plazos legales: «fecha prevista superada» solo compara fechas.
- **FR-011** Cronología de negocio inmutable con fecha, tipo, descripción, actor, responsable, documento o acto, resultado y estado del
  expediente en ese momento. Es distinta de la bitácora CTL-02, que sigue siendo la auditoría.
- **FR-012** Pendientes y siguiente acción calculados por el backend; orientan y no bloquean ni producen efectos jurídicos.
- **FR-013** Reserva (LCP art. 20): un folio puede marcarse reservado con motivo. El derecho de revisión de los oferentes queda fuera: no
  hay oferentes ni selección culminada todavía.
- **FR-014** Capacidades `gobierno_expedientes`: `view`, `manage`, `close` (MFA). El administrador técnico no obtiene autoridad por serlo.
  SoD de CTL-01 sobre registrar, decidir y cerrar.
- **FR-015** Concurrencia: toda escritura con If-Match de la versión del expediente; versión vieja, 409.
- **FR-016** Aislamiento: otro ente recibe 404; funcionario, unidad, comisión, documento o acto de otro ente se rechazan.

## Fuera de alcance

Determinar modalidad (PROC-01), pliego e invitaciones (PROC-04), RNC/SNC (PROC-05), ofertas (PROC-06), evaluación (PROC-07), recomendación
y adjudicación (PROC-08), acceso de oferentes al expediente (art. 20, RLCP 31), cálculo de lapsos (DOC-03), reapertura, exportación.

## Criterios de éxito

- **SC-001** Por menú y en navegador real se recorre el flujo principal de §30 del mandato.
- **SC-002** La ficha responde las ocho preguntas de §18 sin salir de ella.
