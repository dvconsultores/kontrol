# PROC-08 · Recomendación de la Comisión y decisión de la autoridad (GOV-PROC-010, GOV-PROC-011)

**Autorización:** mandato de la dueña «PROC-08 · RECOMENDACIÓN → DECISIÓN DE AUTORIDAD → RESULTADO DEL PROCEDIMIENTO», 2026-11-10 (Constitución P2). **Fuentes:** `FUENTES.md`. **Decisiones de diseño:** `DECISIONES.md` (PDD-PROC08-01 a 15).

## Qué podrá hacer el usuario que antes no podía

Con la evaluación concluida (PROC-07), en la misma ficha del expediente:
1. La Comisión emite su recomendación motivada, con su informe formal descargable, el rechazo motivado de ofertas y, si recomienda adjudicar, la primera, segunda y tercera opción.
2. La autoridad competente, con un acto administrativo de DOC-02, decide adjudicar, declarar desierta o terminar el procedimiento. Después puede declarar la nulidad de lo decidido.
3. Se ve a quién hay que notificar y en qué estado está cada notificación (DOC-04).

No crea contrato (CNT-01).

## Requisitos

- **FR-001 Recomendación.** Solo con la evaluación concluida y el expediente en curso.
  - Contenido:
    - resultado recomendado (adjudicar, declarar desierta o terminar);
    - motivación;
    - examen legal, financiero y técnico;
    - medidas de promoción (opcional);
    - resultado de la matriz;
    - firmantes de la comisión vinculada, con mayoría simple de los miembros principales con voto (LCP arts. 15 y 95).
  - Recomendar desierta exige una causal del art. 113.
- **FR-002 Opciones.** Si recomienda adjudicar: primera opción obligatoria; segunda y tercera solo si existen ofertas que las merezcan. Posiciones consecutivas, ofertas abiertas, distintas y no rechazadas (LCP art. 95). No hay ranking automático.
- **FR-003 Rechazo.** La Comisión rechaza ofertas abiertas con una causal del catálogo (LCP art. 76, num. 1-8; RLCP art. 102, num. 1-6) y motivación (LCP arts. 15.8 y 89). «Todas rechazadas» solo cuando lo están todas las ofertas abiertas.
- **FR-004 Inmutable e informe.** Al emitir se congela una instantánea: expediente, comisión, firmantes, matriz y versión, criterios, ofertas, resultados vigentes de la Comisión por criterio y rechazos. Con ella se genera el informe PDF, que queda descargable y con huella.
  - Lo emitido no se modifica.
  - Sustituirla crea una nueva recomendación, con motivo, si no hay decisión final vigente; la anterior queda «Sustituida».
- **FR-005 Decisión.** Sobre la recomendación vigente, la autoridad registra el resultado con un acto DOC-02.
  - El acto debe estar emitido o eficaz, ser de carácter particular, tener competencia APROBAR sobre CONTRATACIONES en vigor en su fecha y no estar usado por otra decisión.
  - Con la identidad de ORG-06 activa, quien registra ejerce ese cargo y no firmó la recomendación.
  - Se registran motivación, fecha y autoridad. Es inmutable.
- **FR-006 Resultados.**
  - **ADJUDICADA:** a la primera opción. A la segunda o la tercera solo si la adjudicación a la anterior fue anulada por información falsa (LCP arts. 109-111).
  - **DESIERTA:** con una causal de LCP art. 113, num. 1-5.
  - **TERMINADA:** acto motivado (art. 107). Cabe también tras una adjudicación vigente, que queda «Sustituida».
  - **NULIDAD:** de una decisión vigente, por información falsa o por violación de disposiciones legales (art. 112). La decisión anulada se conserva como «Anulada» y se puede decidir de nuevo.
  - Hay a lo sumo una decisión final vigente por expediente.
- **FR-007 Notificación.** Para el acto de la decisión vigente, se lista por oferente si tiene notificación DOC-04 y su estado (Pendiente o Notificada, con fecha y medio). Se indica cuándo el acto quedó eficaz (LCP art. 115). Sin envío electrónico.
- **FR-008 Cronología y auditoría.** Eventos del expediente para la recomendación, cada rechazo, la adjudicación, la desierta, la terminación y la nulidad. Auditoría CTL-02 de cada actuación.
- **FR-009 Permisos, SoD, aislamiento y concurrencia.**
  - Capacidad `gobierno_decision` (view, recommend, decide). Decide es sensible.
  - Códigos SoD `PROC03_RECOMENDAR` y `PROC03_RESOLVER`.
  - If-Match con la versión del expediente y bloqueo de fila; índices únicos para una sola recomendación vigente y una sola decisión final vigente.
  - Otro ente: 404.
- **FR-010 Interfaz.** Sección «Recomendación y decisión» tras «Apertura y evaluación»:
  - estado (evaluación, recomendación, decisión, resultado, siguiente acción);
  - formulario de recomendación con confirmación, vista de la vigente e informe;
  - formulario de decisión con confirmación que muestra resultado, oferente, acto y efecto;
  - nulidad;
  - notificaciones e historial.
  - Funciona a 390 y 320 px y es accesible.
- **FR-011** La siguiente acción de PROC-07 tras concluir dice «Preparar recomendación».

## Fuera de alcance
- Contrato, garantías, decaimiento y paso a la segunda o tercera opción por no firmar (CNT-01).
- Adjudicación parcial (OBS-PROC08-PARCIAL-01).
- Reposición (RLCP art. 98).
- Recursos administrativos.
- Indemnización del art. 107.
- Límites de monto (OBS-PROC08-MONTO-01).
- Envío electrónico de notificaciones.
