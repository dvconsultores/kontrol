# OWNER UAT CARD · GOV-DOC-04 · DOC-04 «Notificaciones administrativas con constancia de recepción por canal autorizado»

```
MÓDULO: Gobierno · PROCESO: DOC-04 Notificaciones administrativas (GOV-DOC-005) · ESTADO: OWNER_UAT_READY
        (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Notificaciones administrativas  (ruta /gobierno/notificaciones; cada notificación en
              /gobierno/notificaciones/<id>). Los destinatarios se agregan desde el acto: Gobierno > Actos administrativos > el acto.
ROL A USAR: un usuario funcional de Gobierno con gobierno_notificaciones (ver, editar, registrar), gobierno_actos y documentos.
            En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) las tiene (la migración 0067 se las concede a
            FUNCIONAL_COMPLETO). Para la auditoría: un usuario con audit:view.
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - ORG-01 ente ACTIVO, ORG-02 estructura VIGENTE, ORG-03 cargo VIGENTE con su competencia.
  - DOC-02: un acto PARTICULAR EMITIDO (p. ej. Resolución Nº DA-001-AAAA) con su PDF firmado.
  - Un tipo documental para PDF en ese contenedor.
DATOS DE PRUEBA (sintéticos):
  Destinatario 1: Persona natural «Pedro Pérez», V-12345678, «Calle 1, casa 2, Caracas».
  Destinatario 2: Persona jurídica «Comercial Ejemplo C.A.», J-12345678-9, «Av. Principal, local 3, Caracas».
  Recursos: «Reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)». Cinco PDF pequeños de prueba (sin datos reales).
PASOS:
  1. Abra el acto particular emitido. Verá la sección «Notificaciones» con «Agregue a cada interesado para notificarle el acto
     (LOPA art. 73).» y ya no el botón «Registrar la notificación» de DOC-02.
  2. «Agregar destinatario»: registre a Pedro y luego a Comercial. El resumen dice «Faltan 2 por notificar de 2.».
  3. Abra a Pedro. En «Oficio y constancias» adjunte el oficio (texto íntegro del acto con los recursos) y el recibo firmado.
  4. «Registrar entrega»: fecha de hoy, oficio = el primero, recibo = el segundo, «Recibido por» y su cédula. Estado «Notificada el …».
     Vuelva al acto: «Faltan 1 por notificar de 2.»; el acto sigue «Emitido».
  5. Abra a Comercial. Adjunte oficio y constancia del intento. «Registrar intento fallido» con el motivo «Domicilio cerrado».
     Aparece «Publicar en prensa» (LOPA art. 76) y el aviso «Tras el intento fallido puede publicarse en prensa».
  6. Adjunte el ejemplar del diario. «Publicar en prensa»: fecha de hoy, «Diario de prueba», «Ed. 123»; el formulario le anticipa
     «Se entenderá notificada el <hoy + 15 días>.». El oficio aparece fijado (el del primer intento).
  7. Estado «Se entiende notificada el <hoy + 15> (publicación en prensa más 15 días)». Vuelva al acto: insignia «Eficaz» y
     «Eficaz a partir de <hoy + 15>.» (la fecha más tardía de los destinatarios, OD-DOC04-02); medio «Publicación en prensa».
  8. Gobierno > Notificaciones administrativas: las dos filas «Notificada» (la de prensa con «(prensa)»); filtre por Estado y
     Buscar; «Exportar CSV» descarga notificaciones-AAAA.csv.
RESULTADO ESPERADO: dos notificaciones NOTIFICADAS con su oficio, constancias e historial; el acto EFICAZ con la fecha más tardía.
DOCUMENTOS A VERIFICAR: oficio y constancias en «Oficio y constancias» con su análisis; tras cada intento quedan congelados; una
                        constancia no puede ser el oficio ni repetirse.
REPORTES A VERIFICAR: la tabla del año (filtros) y su CSV; los contadores de la sección del acto.
AUDITORÍA A VERIFICAR: Sistema > Auditoría, en ese contenedor: destinatario registrado, notificación entregada, intento fallido,
                       publicada en prensa, eficacia del acto registrada, exportación (y, si la usa, anulación y corrección).
HISTORIA A VERIFICAR: cada paso deja una versión (alta, intento fallido, publicación en prensa); una notificación NOTIFICADA es de
                      solo lectura y sus intentos no se editan.
PRUEBA NEGATIVA:
  a) Con un usuario de solo consulta: ve la lista, la notificación y el CSV, pero ningún botón de registro, corrección o anulación,
     ni «Agregar destinatario» en el acto.
  b) Repita a Pedro (V-12345678) en el mismo acto: error en «Cédula o RIF». Escriba «123456»: «Escriba la cédula con su letra…».
  c) Intente «Publicar en prensa» sin un intento fallido: el botón no aparece (y el servidor lo rechaza).
  d) Un acto general (Gaceta) no admite destinatarios; un acto ya eficaz tampoco.
  e) Desde otro ente, la dirección de la notificación responde «Notificación no encontrada».
LIMPIEZA: no hace falta; es una base de QA. (Una notificación no se borra: se anula con motivo.)
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - FIND-DOC04-01 (transversal, LOW): los errores de campo del servidor llevan delante «Value error, » (manejador global de validación).
  - Notificaciones persistentes arriba a la derecha (GOV0-UI-02, LOW): ciérrelas con «Cerrar notificación» si tapan un botón.
  - Canal electrónico fuera de alcance hasta la validación legal y la firma electrónica (DOC-05, OD-DOC04-01).
```
