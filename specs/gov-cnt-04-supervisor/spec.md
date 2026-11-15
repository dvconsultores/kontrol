# Spec · CNT-04 Supervisor / responsable del contrato (GOV-CNT-004)

**Prioridad**: P0 · **Normas**: N11 (LCP arts. 136-138), N20 · **Actor**: Máxima autoridad (el contratante) · **Fecha**: 2026-11-15
**Decisiones de la dueña**:
- OD-CNT04-01: un solo supervisor vigente por contrato y por fecha.
- OD-CNT04-02: el acto de designación debe venir de un cargo emisor con APROBAR×CONTRATACIONES.

## Historias

**US1 (P1) · Designar al supervisor.** En un contrato FORMALIZADO, quien tiene el permiso técnico elige:
- un funcionario institucional (ORG-04);
- una de sus ocupaciones vigentes (cargo y unidad);
- un acto DOC-02 eficaz, emitido por un cargo con APROBAR×CONTRATACIONES;
- una fecha efectiva.

Formaliza con MFA. La ficha del contrato muestra al supervisor vigente.

- AC1. El contrato en BORRADOR, inexistente o de otra empresa no admite designación (409 o 404).
- AC2. El funcionario debe ser del ente, estar ACTIVO y tener una ocupación vigente en la fecha efectiva y hoy. Las delegaciones no cuentan como ocupación.
- AC3. El acto debe ser del ente, estar EFICAZ con eficacia ≤ fecha efectiva, y su cargo emisor debe tener APROBAR×CONTRATACIONES a la fecha del acto.
- AC4. La designación guarda las FK y la instantánea: funcionario (nombre y documento enmascarado), ocupación, figura, cargo, unidad, acto (etiqueta y cargo emisor) y desde.

**US2 (P1) · Sustituir al supervisor.** Una nueva designación con otro acto, fecha efectiva D y motivo. La anterior pasa a SUSTITUIDA con `hasta = D − 1` y se conserva íntegra.

- AC5. D debe ser posterior al «desde» del vigente, y el motivo es obligatorio.
- AC6. La sustitución no puede reutilizar el acto de la designación vigente.
- AC7. Sin retroactividad silenciosa: la consulta en una fecha anterior a D sigue devolviendo al anterior.

**US3 (P1) · Consultar la historia.** La historia completa en orden: designación, funcionario, cargo, unidad, acto, desde, hasta, motivo y estado. Además, `supervisor_en(fecha)` para CNT-03.

## Requisitos

- **FR-01 (C04-01).** Solo contratos FORMALIZADO del ente.
- **FR-02 (C04-02, C04-03).** El supervisor es un `GovernmentOfficial` con una ocupación ORG-04 vigente. No es texto libre ni un usuario técnico.
- **FR-03 (C04-04).** Instantánea del cargo y la unidad. No sustituye a ORG.
- **FR-04 (C04-05).** Acto DOC-02 obligatorio. Su documento es el soporte; no se pide un segundo PDF.
- **FR-05 (C04-06).** La autoridad que designa es el cargo emisor del acto, con APROBAR×CONTRATACIONES a la fecha del acto (titular, suplencia, encargaduría o delegación, según ORG-03/04). Si la política ORG-06 lo exige, el actor debe ejercer ese cargo (`exigir_autoridad_funcional`). No se crea la acción DESIGNAR.
- **FR-06 (C04-07).** Permiso técnico nuevo `gobierno_contratos:assign_supervisor`, SENSITIVE (MFA). No otorga autoridad institucional.
- **FR-07 (C04-08).** Una designación VIGENTE por contrato: índice único parcial más bloqueo del contrato.
- **FR-08 (C04-09).** Rango de la fecha efectiva:
  - mínimo: el más temprano entre el inicio del plazo y la fecha de formalización; con vigente, además el día siguiente a su «desde»;
  - máximo: fin del contrato. Una fecha futura deja la designación **programada**: la anterior sigue en ejercicio hasta el día previo. Decisión de diseño del 2026-11-15: con datos de un mismo día, una sustitución solo cabe con fecha futura; además refleja actos que designan con efecto posterior.
- **FR-09 (C04-10, C04-11).** Sustitución con historia; la consulta por fecha es por intervalos.
- **FR-10 (C04-12).** Inmutable en PG: sin DELETE ni TRUNCATE. La única UPDATE permitida es VIGENTE→SUSTITUIDA, fijando `hasta` y `sustituida_por_id`.
- **FR-11 (C04-13).** Concurrencia: dos designaciones simultáneas dan una 201 y una 409. El cliente envía `sustituye_id` (la designación vigente que ve, o null); si no coincide, responde 409 STALE.
- **FR-12 (C04-14).** SoD: se reutiliza CTL-01 con las funciones PROC03_CONTRATO_SUPERVISOR_DESIGNAR y PROC03_CONTRATO_SUPERVISOR_SUSTITUIR. Sin incompatibilidad codificada.
- **FR-13 (C04-15).** Aislamiento: otra empresa da 404; un funcionario, ocupación o acto ajeno da 422.
- **FR-14 (C04-16).** Auditoría CTL-02: GOV_CONTRACT_SUPERVISOR_ASSIGNED, GOV_CONTRACT_SUPERVISOR_REPLACED y GOV_CONTRACT_SUPERVISOR_BLOCKED (rechazo material). Además, un evento en la cronología del expediente.
- **FR-15 (C04-17).** Contrato para CNT-03: `supervisor_en(db, ctx, contrato_id, fecha)` y `supervisor_vigente(db, ctx, contrato_id)`, más GET `/supervision/en?fecha=`.
- **FR-16 (C04-18).** La pantalla está dentro de la ficha del contrato (sección «Supervisor / responsable del contrato»): vigente, historial y formulario. E2E a 1280, 390 y 320 px, con Axe.

## Fuera de alcance

- CNT-03 (atribuciones y conformaciones), CNT-02 (P2) y ORG-05.
- Revocación sin sucesor (las fuentes no la regulan).
- Varios supervisores a la vez (OQ-CNT04-01).
- Supervisión contratada a terceros.
- Reportes (REPORTING NOT_APPLICABLE).
