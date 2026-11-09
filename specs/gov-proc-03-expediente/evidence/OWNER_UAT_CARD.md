# OWNER UAT CARD · GOV-PROC-03 · PROC-03 «Expediente único de contratación» (GOV-PROC-004, GOV-PROC-014)

```
MÓDULO: Gobierno · PROCESO: PROC-03 Expediente único de contratación
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

URL: http://localhost:15273/
MENÚ: Gobierno · Contrataciones › Expedientes (/gobierno/contrataciones/expedientes)

ROLES A USAR:
  - Crear, editar, descartar y sustanciar: gobierno_expedientes:view y :manage.
  - Cerrar: gobierno_expedientes:close (pide MFA).
  - Lector: solo gobierno_expedientes:view.
  - Para abrir documentos o actos hacen falta además documentos:view y gobierno_actos:view.
  En la base de QA, el administrador «con todo» los tiene.

QUÉ ES Y QUÉ NO ES:
  Reúne una contratación: quién responde, qué comisión interviene, qué documentos y actos tiene, qué se hizo y decidió,
  y qué hitos hay. NO determina la modalidad, NO valida montos ni excepciones, NO calcula lapsos ni días hábiles,
  NO adjudica, NO publica ni consulta SNC/RNC. Los estados En curso, Cerrado y Descartado son operativos, sin efecto jurídico.

PRECONDICIONES:
  - Ente activo, estructura vigente del año y al menos un funcionario activo.
  - Para vincular comisión: una comisión en vigor (PROC-02). Para folios: un documento con archivo o un acto emitido.

PASOS Y RESULTADO ESPERADO:
  1. CREAR: pulse «Nuevo expediente». Número, fecha de iniciación, objeto, tipo, unidad y responsable. Ve la ficha en «En curso».
  2. LEER LA SITUACIÓN: arriba ve siguiente acción, próximo hito, última actuación, responsable, comisión y lo pendiente.
  3. EDITAR: pulse «Editar», complete las partes y declare la modalidad con su fundamento. Pide motivo y queda en la cronología.
  4. COMISIÓN: pulse «Vincular comisión» y elija una en vigor, o declare que no interviene. «Abrir comisión» lleva a su ficha.
  5. RESPONSABLES: asigne otro funcionario con un rol (custodia, sustanciación, requirente) y luego termínelo con fecha y motivo.
  6. HITOS: pulse «Registrar hito» con nombre, fuente y fecha prevista. Con «Actualizar» ponga la fecha real. Reprogramar pide motivo.
  7. DOCUMENTOS: cargue un archivo en «Archivos del expediente» y pulse «Incorporar al expediente»: clase del art. 32 y documento.
     Recibe folio 1. Repita con un acto: folio 2. En «Contenido del expediente» ve qué clases faltan.
  8. ACTUACIONES: registre una actuación y una decisión con resultado. Pueden citar folio, hito y acto; ninguno es obligatorio.
  9. RECTIFICAR: pulse «Rectificar» en una actuación e indique el motivo. El registro original sigue, y ambos se señalan.
  10. CRONOLOGÍA: lea fecha, tipo, descripción, responsable, documento, resultado, actor y estado de cada registro.
  11. LISTADO: busque y filtre por estado, unidad, responsable, modalidad o fechas.
  11b. TELÉFONO: reduzca la ventana bajo 768 px o use un teléfono. El menú se abre con el botón de la barra superior y el contenido usa todo el ancho.
  12. CERRAR: pulse «Cerrar expediente» con fecha y motivo. Queda «Solo consulta» y no se puede reabrir: ciérrelo solo en un expediente de prueba.

NEGATIVAS:
  - Número repetido en el ente: se rechaza. Número o fecha de iniciación con folios: ya no cambian.
  - Decisión sin resultado o rectificación sin motivo: no se guarda. Rectificar dos veces el mismo registro: se rechaza.
  - Dos responsables principales vigentes: pide terminar primero al vigente.
  - Descartar con contenido: se rechaza. Sin permiso de gestión: no ve las acciones. Otro ente: el expediente no existe para él.

LÍMITES CONOCIDOS:
  - Un folio corresponde a un documento o acto, no a cada página. Un folio no se borra: un error se explica con una actuación.
  - Una versión nueva de un documento ya foliado no se ofrece para foliarla otra vez.
  - Quitar el vínculo de un archivo desde el panel de archivos no borra su folio.
  - «Partes» es texto declarado hasta que existan oferentes (PROC-05, bloqueado).
  - Sin reapertura, sin exportación, y sin acceso de oferentes al expediente (LCP art. 20, RLCP art. 31).
  - «Abrir bitácora» abre la bitácora general: aún no llega filtrada por este expediente.
  - Probado por interfaz: el flujo principal. Por API: descartar, terminar responsable y reprogramar. Sin ejercitar en navegador:
    terminar responsable, descartar, no interviene comisión, reserva de folio, reprogramar, marcar hito «no aplica» y paginación.
```
