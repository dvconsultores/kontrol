# OWNER UAT CARD · GOV-0-01 · ORG-01 «Configurar el ente»

```
MÓDULO: Gobierno · PROCESO: ORG-01 Configurar el ente · ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Configuración del ente  (ruta /gobierno/ente)
ROL A USAR: un usuario funcional con las capacidades gobierno_ente (ver, crear, editar, activar) y documentos;
            en la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) las tiene.
            Para la parte de auditoría: un usuario con audit:view (el mismo administrador).
PRECONDICIONES:
  - Instalación de QA con la licencia sintética que habilita el módulo «gobierno» (la siembra de QA la importa;
    una base sembrada antes se actualiza sola en la siguiente siembra).
  - Un contenedor (empresa) activo sin ente configurado. Arriba, el selector dice «Ente activo: …».
  - Un tipo documental para PDF en ese contenedor (Documentos > Tipos documentales), p. ej. «Acto de creación».
DATOS DE PRUEBA (sintéticos):
  Denominación: Alcaldía del Municipio Demo · Siglas: (vacío al principio)
  Nivel: Municipal · Forma: Administración central · Entidad federal: Lara · Municipio: Iribarren
  Acto: Ordenanza N.º 1, fecha 15/01/2020, publicación «Gaceta Municipal N.º 1 del 15/01/2020»
  Documento: cualquier PDF pequeño de prueba (sin datos reales)
PASOS:
  1. Entre en Gobierno > Configuración del ente. Verá «El ente aún no está configurado». Pulse «Configurar el ente».
  2. Escriba solo la denominación y pulse «Guardar». Verá la ficha en «Borrador», versión 1, y la lista
     «Para activar el ente falta:». «Activar el ente» está deshabilitado.
  3. Pulse «Editar». Elija Municipal: aparecen «Entidad federal» y «Municipio». Complete la naturaleza y el acto. «Guardar».
     Ahora el único requisito pendiente es «Documento del acto de creación».
  4. En «Documento del acto de creación», elija el tipo documental, el PDF y pulse «Adjuntar». Al terminar el análisis,
     verá «El ente está completo y puede activarse.».
  5. Pulse «Activar el ente», lea la confirmación y pulse «Activar». La ficha pasa a «Activo».
  6. Pulse «Modificar», cambie las siglas a «AMD» e intente guardar sin motivo: el sistema pide el motivo.
     Escriba «Corrección de las siglas institucionales» y guarde.
  7. Mire «Historial de versiones»: 4 versiones (alta, edición, activación, modificación) y el motivo en la 4.
RESULTADO ESPERADO: ente ACTIVO con los datos del acto, el documento vinculado, siglas AMD y versión 4.
DOCUMENTOS A VERIFICAR: el PDF aparece en el panel con su estado de análisis y se puede descargar.
REPORTES A VERIFICAR: N/A (justificado en la Spec §2: GOV-ORG-001 no pide reporte; la consulta es la ficha y su historial).
AUDITORÍA A VERIFICAR: Sistema > Auditoría: «Ente de Gobierno creado», «Ente de Gobierno modificado» (dos; la segunda con el
                       motivo) y «Ente de Gobierno activado», en ese contenedor.
PRUEBA NEGATIVA:
  a) Con un usuario que solo puede ver el ente: ve la ficha, pero no aparecen «Editar», «Activar el ente» ni «Modificar».
  b) Cambie a otro contenedor sin ente: verá «El ente aún no está configurado» (cada ente es independiente).
  c) En el paso 6, sin motivo no se guarda.
LIMPIEZA: no hace falta; es una base de QA. (Un ente no se borra: la supresión es otro proceso legal, fuera de alcance.)
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - La compuerta «Seleccione una empresa» (cuando el usuario tiene varios contenedores y ninguno activo) todavía dice «empresa»;
    el selector de la barra superior ya dice «ente». Deuda de rótulo GOV0-UI-01.
  - El acto de creación se adjunta como documento del módulo 046; la validación jurídica del contenido del acto es humana.
  - Las notificaciones de éxito son persistentes en todo KONTROL (FR-001-063) y aparecen arriba a la derecha: si una tapa
    «Editar» o «Modificar», ciérrela con su botón «Cerrar notificación». Deuda transversal de ubicación GOV0-UI-02.
```
