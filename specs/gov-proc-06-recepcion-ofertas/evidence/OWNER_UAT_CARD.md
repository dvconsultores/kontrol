# OWNER UAT CARD · GOV-PROC-06 · PROC-06 «Recepción confidencial de ofertas» (GOV-PROC-007)

```
MÓDULO: Gobierno · PROCESO: PROC-06 Recepción de ofertas
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

MENÚ: Gobierno · Contrataciones › Expedientes › (abrir un expediente) › sección «Ofertas»

ROLES A USAR:
  - Recibir y concluir la recepción: gobierno_ofertas:view y :receive.
  - Solo consultar: gobierno_ofertas:view.
  - Para marcar documentos en el formulario: documentos:view. Para cargar uno desde ahí: gobierno_expedientes:manage.
  En la base de QA, el administrador «con todo» los tiene. Nadie recibe apertura ni evaluación: eso es PROC-07.

QUÉ ES Y QUÉ NO ES:
  Registra cada oferta recibida: oferente declarado, canal, fecha y hora, receptor, documentos con su versión fijada,
  integridad y sello. NO abre ofertas, NO levanta sellos, NO evalúa ni adjudica, NO valida RNC/SNC (identidad declarada).

USE SOLO DATOS SINTÉTICOS. No registre ofertas reales.

PRECONDICIONES:
  - Un expediente «En curso» (PROC-03) y un funcionario activo.
  - Un documento con archivo vinculado al expediente (cárguelo en «Archivos del expediente» o desde el formulario).
  - En concurso: comisión vinculada o declaración de que no interviene.

PASOS Y RESULTADO ESPERADO:
  1. Abra la ficha del expediente y baje a «Ofertas»: ve «Sin ofertas recibidas».
  2. Pulse «Recibir oferta» y luego «Guardar» sin datos: ve los errores en cada campo; el formulario sigue abierto.
  3. Complete Oferente, Documento del oferente, Tipo de sobre, Canal, Fecha y hora y Funcionario receptor.
     Marque el documento en «Documentos de la oferta». Guarde.
  4. Ve «Oferta R-0001 registrada. Siguiente paso: pendiente de apertura.» y la tarjeta con referencia, oferente,
     canal, fecha y hora, receptor, «Integridad verificada», «Sellada hasta la apertura» y «Pendiente de apertura».
  5. Pulse «Ver detalle»: el documento aparece como «Contenido sellado hasta la apertura», con versión y huella.
  6. Arriba, en Situación, la siguiente acción es «Pendiente de apertura». En la cronología aparece la recepción,
     sin el nombre del documento.
  7. Vaya a Documentos y busque el documento sellado: ya no aparece; su enlace directo responde «no encontrado».
  8. Opcional: «Concluir recepción»: después no se admiten más ofertas.
  9. Teléfono: con la ventana bajo 400 px el formulario y la tarjeta siguen operables.

NEGATIVAS:
  - El mismo oferente (aunque escriba el documento con guiones o minúsculas) y el mismo tipo de sobre: se rechaza.
  - Un concurso no admite oferta sin sello. En consulta de precios o contratación directa, no sellar exige motivo.
  - Fecha futura o anterior al inicio del expediente: se rechaza.
  - Usuario de otro ente o sin permiso: no ve las ofertas.

LÍMITES CONOCIDOS:
  - La oferta no se edita ni se borra; no hay rectificación (ninguna fuente la prevé).
  - Quien cargó el archivo lo ve hasta que se recibe la oferta; el sello actúa desde la recepción.
  - Un paquete de auditoría generado antes del sello deja de poder descargarse; uno nuevo lo excluye.
```
