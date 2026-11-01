# OWNER UAT CARD · GOV-DOC-02 · DOC-02 «Actos administrativos con autoridad, competencia, motivación, eficacia y notificación»

```
MÓDULO: Gobierno · PROCESO: DOC-02 Actos administrativos (GOV-DOC-003) · ESTADO: OWNER_UAT_READY
        (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Actos administrativos  (ruta /gobierno/actos; cada acto en /gobierno/actos/<id>)
ROL A USAR: un usuario funcional de Gobierno con gobierno_actos (ver, editar, emitir, anular), gobierno_cargos:view y documentos.
            En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) las tiene (la migración 0066 se las concede a
            FUNCIONAL_COMPLETO). Para la auditoría: un usuario con audit:view.
            Para la prueba negativa b): un «registrador» con gobierno_actos:view + gobierno_actos:edit (sin emitir).
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - ORG-01: el ente configurado y ACTIVO.  ORG-02: la estructura del año VIGENTE.
  - ORG-03: un cargo VIGENTE, p. ej. DIR-ADM en DA-01, con la competencia «Aprobar · Contrataciones».
  - Un tipo documental para PDF en ese contenedor.
DATOS DE PRUEBA (sintéticos):
  Resolución Nº DA-001-AAAA, lugar Caracas, cargo DA-01 · DIR-ADM, competencia Aprobar · Contrataciones, fundamento «Reglamento
  interno, art. 12», funcionario «Funcionaria de prueba», Titular, Particular (se notifica), destinatario «Proveedor de prueba»,
  asunto «Adjudicación de prueba», hechos, fundamentos legales y decisión de prueba. Dos PDF pequeños de prueba (sin datos reales).
PASOS:
  1. Entre en Gobierno > Actos administrativos. Llega a «Actos administrativos» con el año en curso.
  2. «Registrar acto»: rellene los datos de prueba y «Guardar». Se abre la página del acto, insignia «Borrador».
  3. Mire «Requisitos para emitir»: falta «El PDF firmado del acto»; si borra la decisión, también la pedirá.
  4. En «Documentos del acto» elija el tipo documental, el primer PDF y «Adjuntar».
  5. «Emitir»: elija el PDF en «PDF firmado del acto» y pulse «Emitir». La insignia pasa a «Emitido» y el aviso dice
     «Emitido, pendiente de notificación.». Desde aquí los datos no se editan.
  6. Adjunte el segundo PDF (el recibo de notificación). «Registrar la notificación»: «Notificación personal», fecha de hoy,
     soporte = el segundo PDF, «Registrar». La insignia pasa a «Eficaz» y el aviso dice «Eficaz desde dd/mm/aaaa.».
  7. (Opcional) Repita con un acto Particular y «Publicación en prensa»: el sistema le muestra la eficacia a los 15 días
     (LOPA art. 76) y no le deja fijar una anterior.
  8. «Corregir error material»: cambie el asunto, escriba el motivo «Error de transcripción» y guarde. El historial lo muestra.
  9. Registre y emita un segundo acto del mismo cargo (p. ej. una Resolución Interna, que queda eficaz al emitir). Vuelva al
     primero: «Registrar revocación», elija el segundo en «Acto de referencia», motivo «Revocado por cambio de criterio».
     La insignia pasa a «Revocado» y el aviso enlaza al acto que lo revoca.
 10. Vuelva a «Actos administrativos» (miga de pan): use Buscar, Tipo, Carácter, Estado y Cargo; «Exportar CSV» descarga
     actos-AAAA.csv con una fila por acto.
RESULTADO ESPERADO: el primer acto REVOCADO, con su PDF firmado, su soporte de notificación, su corrección y su historial
                    (Borrador → Emitido → Eficaz → Corregido → Revocado); el segundo acto EFICAZ.
AUTORIDAD A VERIFICAR: solo se ofrecen cargos vigentes en la fecha del acto y solo sus competencias; si cambia de cargo, la
                       competencia elegida se vacía. Permiso de la aplicación ≠ autoridad institucional: el usuario registra,
                       el acto lo dicta el cargo.
DOCUMENTOS A VERIFICAR: el PDF firmado y el soporte aparecen en «Documentos del acto» con su análisis y se descargan; tras emitir
                        y tras registrar la eficacia quedan congelados (no se desvinculan).
REPORTES A VERIFICAR: la tabla del año (filtros) y su CSV.
AUDITORÍA A VERIFICAR: Sistema > Auditoría, en ese contenedor: acto registrado, emitido, eficacia registrada, corregido (antes,
                       después y motivo), revocado, exportación.
HISTORIA A VERIFICAR: cada paso deja una versión con estado, fecha y motivo; un acto emitido no cambia tipo, número, fecha,
                      autoridad ni carácter; revocado o nulo es de solo lectura.
PRUEBA NEGATIVA:
  a) Con un usuario de solo consulta: ve la lista, el acto y «Exportar CSV», pero no «Registrar acto», «Editar», «Eliminar» ni «Emitir».
  b) Con el «registrador»: registra y edita borradores, pero no ve «Emitir».
  c) Repita el número DA-001-AAAA con el mismo cargo y tipo: «Ya existe un acto con este cargo, tipo y número». Una fecha futura:
     «La fecha del acto no puede ser posterior a hoy». Guardar vacío: cada campo obligatorio dice qué falta.
  d) Intente revocar con un acto en borrador o anterior al revocado: no aparece como referencia.
LIMPIEZA: no hace falta; es una base de QA. (Un acto emitido no se borra: se revoca o se declara nulo.)
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Notificaciones persistentes arriba a la derecha (GOV0-UI-02, LOW): ciérrelas con «Cerrar notificación» si tapan un botón o una miga.
  - La firma electrónica, el expediente y la delegación como proceso llegan con DOC-03, DOC-01 y ORG-04; DOC-02 registra actos ya
    suscritos (OD-DOC02-01). Quién ocupa cada cargo llega con ORG-06.
```
