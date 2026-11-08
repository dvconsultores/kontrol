# Plan PROC-03

**Módulo** `government`. Reutiliza ORG-02 (unidad), ORG-04 (funcionario y ocupación a la fecha), PROC-02 (comisión), DOC-02 (acto), Spec 046 (documento, versión, vínculo),
CTL-01 (SoD), CTL-02 (auditoría). `SHARED_CORE_CHANGE_REQUIRED = 0`: solo entradas declarativas de registro (`RESOURCE_KINDS`, catálogos, MFA, permisos), igual que los ciclos anteriores, sin cambiar semántica.

## Datos (migración nueva, cabeza única)

- `gov_procurement_files`: identificación, tipo, modalidad declarada, unidad, comisión o motivo de no intervención, estado, cierre, versión.
- `gov_procurement_file_responsibles`: funcionario, rol, instantánea de cargo y unidad, vigencia.
- `gov_procurement_file_milestones`: hito, fuente, fechas, responsable, estado.
- `gov_procurement_file_folios`: **inmutable**. Número correlativo, clase, documento+versión **o** acto, instantáneas, fecha de incorporación, reserva, hito.
- `gov_procurement_file_events`: **inmutable**. Cronología con secuencia, fecha, clase, título, detalle, resultado, responsable, acto, folio, hito, estado en ese momento y rectificación.

Actuaciones y decisiones son filas de la cronología: no hay tabla paralela que pueda divergir. Instantáneas para que la historia no cambie si cambia el nombre de un cargo.

## API `/gobierno/contrataciones/expedientes`

`GET catalogo, opciones, "", {id}, {id}/cronologia` · `POST "", {id}/descartar, {id}/cerrar, {id}/responsables, {id}/responsables/{r}/terminar, {id}/comision, {id}/actuaciones, {id}/folios, {id}/hitos, {id}/hitos/{h}/actualizar` · `PATCH {id}`.

## Interfaz

Menú «Gobierno · Contrataciones › Expedientes». Rutas: listado, nuevo, ficha, editar. Ficha con resumen de las ocho preguntas y secciones Responsables, Comisión, Actuaciones y decisiones, Documentos y actos, Hitos, Cronología y Auditoría (enlace a la bitácora).

## Constitution gate

P1 aislamiento: `company_id` en toda consulta y referencia validada. P2 autorización: este mandato. P8 sin reglas de negocio hardcodeadas sin fuente: clases y modalidades citan artículo; ningún lapso calculado. Auditoría: CTL-02. Sin decisión material abierta: `BLOCKER = 0`, `MATERIAL OQ = 0`. Limitaciones declaradas en la tarjeta.

## Decisiones de diseño (de Claude, sin efecto legal; reversibles)

- PD-1 Tipo obligatorio de los tres de RLCP art. 33. - PD-2 Modalidad de lista cerrada, opcional, con fundamento obligatorio si se declara. - PD-3 Folio = uno por documento, no por página. - PD-4 Responsable sin cargo vigente se admite y aparece como pendiente: responder no concede autoridad. - PD-5 Toda escritura usa If-Match del expediente; así se serializa el folio correlativo.
