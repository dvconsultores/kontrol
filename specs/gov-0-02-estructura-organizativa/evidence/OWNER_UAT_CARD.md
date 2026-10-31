# OWNER UAT CARD · GOV-0-02 · ORG-02 «Estructura organizativa por ejercicio»

```
MÓDULO: Gobierno · PROCESO: ORG-02 Estructura organizativa por ejercicio · ESTADO: OWNER_UAT_READY (pendiente de su prueba;
        OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Estructura organizativa  (ruta /gobierno/estructura; cada ejercicio en /gobierno/estructura/AAAA)
ROL A USAR: un usuario con las capacidades gobierno_estructura (ver, editar, poner en vigor, cerrar) y documentos;
            en la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) las tiene (la migración 0064 se las concede).
            Para la auditoría: un usuario con audit:view (el mismo administrador).
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - El ente de ORG-01 configurado y ACTIVO en el contenedor activo (Gobierno > Configuración del ente).
    Sin ente, la pantalla dice «Primero configure el ente» y enlaza con Configuración del ente.
  - Un tipo documental para PDF en ese contenedor (p. ej. «Acto de creación»), para el acto que aprueba la estructura.
DATOS DE PRUEBA (sintéticos):
  Ejercicio: el año en curso (AAAA) · Unidades: DESP «Despacho del Alcalde» (Órgano);
  DA-01 «Dirección de Administración» (Unidad administrativa, depende de DESP); SEDE «Sede principal» (Sede, depende del ente).
  Acto: cualquier PDF pequeño de prueba (sin datos reales).
PASOS:
  1. Entre en Gobierno > Estructura organizativa. En «Abrir la estructura de un ejercicio», escriba el año en curso y pulse
     «Abrir estructura». Llega a «Estructura organizativa AAAA», insignia «Borrador».
  2. «Agregar unidad»: código DESP, denominación «Despacho del Alcalde», tipo Órgano, «Guardar».
     En la fila de DESP pulse «Agregar subordinada» y registre DA-01. Registre también SEDE desde «Agregar unidad».
     El árbol sangra DA-01 bajo DESP; la columna «Depende de» dice DESP (y «Ente» para las raíces).
  3. Mire «Requisitos para poner en vigor»: falta «Acto que aprueba la estructura» y «Poner en vigor» está deshabilitado.
  4. En «Acto que aprueba la estructura», elija el tipo documental, el PDF y pulse «Adjuntar». Al terminar el análisis verá
     «La estructura está completa y puede ponerse en vigor.».
  5. Pulse «Poner en vigor», lea la confirmación y confirme. La insignia pasa a «Vigente».
  6. «Editar» DA-01, cambie la denominación a «Dirección General de Administración» e intente guardar sin motivo: el sistema
     pide el motivo. Escriba «Reorganización aprobada» y guarde. El código y el inicio de vigencia ya no se pueden cambiar.
  7. «Historial» de DA-01: dos versiones; la segunda con el motivo.
  8. «Desactivar» SEDE: fecha de fin (por defecto 31/12/AAAA) y motivo «Supresión de la sede»; la fila dice «Inactiva»
     con su vigencia «desde – hasta». No desaparece.
  9. «Exportar CSV»: se descarga estructura-AAAA.csv con código, denominación, tipo, superior, nivel, estado y vigencias.
 10. Vuelva a la lista: abra el ejercicio AAAA+1 eligiendo «Copiar del ejercicio» = AAAA. La copia trae las unidades ACTIVAS
     (DESP y DA-01, no SEDE), en «Borrador», vigentes desde el 01/01/AAAA+1.
RESULTADO ESPERADO: estructura AAAA VIGENTE con el acto vinculado, DA-01 renombrada (versión 2) y SEDE inactiva con fecha;
                    estructura AAAA+1 en borrador copiada de AAAA.
DOCUMENTOS A VERIFICAR: el PDF aparece en el panel «Acto que aprueba la estructura» con su análisis y se descarga.
REPORTES A VERIFICAR: listado «Estructura del ejercicio» (la tabla con búsqueda y filtros por tipo y estado) y su CSV.
AUDITORÍA A VERIFICAR: Sistema > Auditoría, en ese contenedor: estructura creada, puesta en vigor y exportada; unidades
                       creadas, una modificada con el motivo y una desactivada con motivo y fecha.
PRUEBA NEGATIVA:
  a) Con un usuario que solo puede ver la estructura: ve la tabla y «Exportar CSV», pero no «Agregar unidad», «Editar»
     ni «Poner en vigor».
  b) Intente que DESP dependa de DA-01: el desplegable «Depende de» no ofrece a sus subordinadas (y el servidor rechaza
     el ciclo).
  c) En el paso 6, sin motivo no se guarda. En una estructura vigente una unidad no se elimina: se desactiva.
  d) «Cerrar ejercicio» del año en curso está deshabilitado: un ejercicio se cierra a partir del 1 de enero siguiente.
     Una estructura cerrada se ve con «Estructura de un ejercicio cerrado: solo lectura.» y sin acciones.
LIMPIEZA: no hace falta; es una base de QA. (Una estructura no se borra; un ejercicio cerrado no se reabre.)
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Las notificaciones de éxito son persistentes en todo KONTROL (FR-001-063) y aparecen arriba a la derecha: si una tapa
    un botón de la cabecera, ciérrela con «Cerrar notificación». Deuda transversal de ubicación GOV0-UI-02 (LOW).
  - El árbol es una tabla jerárquica sangrada (PDD-ORG02-06), no un organigrama gráfico.
  - El ejercicio es el año calendario (OD-ORG02-01); el vínculo con el ejercicio presupuestario llega con BUD-01.
```
