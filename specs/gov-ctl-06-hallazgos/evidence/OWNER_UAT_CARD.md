# OWNER UAT CARD · GOV-CTL-06 · CTL-06 «Hallazgos, recomendaciones y planes de acción correctiva» (GOV-CTL-008)

```
MÓDULO: Gobierno · PROCESO: CTL-06 Hallazgos y acciones correctivas
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Menú > Gobierno > Hallazgos y acciones correctivas  (ruta /gobierno/hallazgos)
  - o, desde una muestra de CTL-04 (Gobierno › Auditoría institucional › muestra), el botón «Registrar hallazgo».

ROLES A USAR:
  - Control Interno: usuario con gobierno_hallazgos:view y :manage. En la base de QA, el administrador «con todo»
    (ADMIN + FUNCIONAL_COMPLETO) los tiene: la migración 0070 los concede a FUNCIONAL_COMPLETO.
  - Verificador: OTRO usuario con gobierno_hallazgos:verify (FUNCIONAL_COMPLETO también lo tiene).
    Cree un segundo usuario con ese rol, porque quien registra la evidencia o presenta no puede verificar.
  - Negativas: un usuario con solo gobierno_hallazgos:view, y otro sin ningún permiso de hallazgos.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno».
  - ORG-01 ente ACTIVO, ORG-02 estructura VIGENTE del año en curso y ORG-03 al menos un cargo VIGENTE de ese ejercicio
    (será el responsable).
  - Para el origen por muestra: una muestra de CTL-04 guardada.

PASOS Y RESULTADO ESPERADO:
  1. ORIGEN DESDE LA MUESTRA: en la muestra, pulse «Registrar hallazgo».
     Verá «Origen del hallazgo: Muestra de auditoría» y las partidas como casillas; marque una.
  2. ALTA: complete Título, Condición, Criterio, Causa, Efecto y Riesgo, y pulse «Registrar hallazgo».
     Se abre el hallazgo HA-<año>-<nnnn> en estado «Abierto».
     El origen enlaza a la muestra y a la evidencia de la partida.
  3. ORIGEN INDEPENDIENTE: desde Gobierno › Hallazgos › «Registrar hallazgo», elija «Independiente».
     El campo «Origen descrito» es obligatorio.
  4. RECOMENDACIÓN Y PLAN: añada una recomendación y, para ella, una acción con «Cargo responsable» (solo aparecen los cargos
     VIGENTES del ejercicio en curso) y una «Fecha objetivo» (hoy o posterior).
     «Registrar plan» se habilita cuando cada recomendación tiene al menos una acción; el estado pasa a «Plan de acción».
  5. EJECUCIÓN: «Iniciar ejecución» → «En remediación».
     Adjunte la evidencia en «Evidencia de la acción 1» (pasa por el analizador) y registre un avance del 100 % eligiendo el documento.
     La acción queda «Completada».
     Sin evidencia, el 100 % se rechaza; un porcentaje menor que el anterior también.
  6. PRESENTAR: «Presentar a verificación» → «Pendiente de verificación».
  7. MAKER-CHECKER: con el MISMO usuario, «Verificar y cerrar» y luego «Confirmar verificación».
     Aparece el aviso «Quien registró la evidencia o presentó el hallazgo no puede verificarlo…».
  8. VERIFICACIÓN: con el OTRO usuario, abra el hallazgo y pulse «Verificar y cerrar» con una nota → estado «Cerrado».
     Alternativa: «Devolver» con motivo lo vuelve a «En remediación».
  9. HISTORIA: la sección «Historia» lista cada paso con fecha y usuario, y termina en «Verificado y cerrado».
 10. LISTADO Y REPORTE: en Gobierno › Hallazgos verá los indicadores Abiertos, Acciones vencidas, Pendientes de verificación y
     Cerrados (al pulsarlos filtran). «Exportar plan (CSV)» descarga plan-acciones-<fecha>.csv, una fila por acción.
     Sistema › Auditoría registra cada paso; Gobierno › Auditoría institucional incluye el proceso
     «CTL-06 · Hallazgos y acciones correctivas».

PRUEBA NEGATIVA:
  a) Usuario con solo view: ve listado y ficha, pero no «Registrar hallazgo» ni los formularios.
  b) Usuario sin permisos de hallazgos: el menú no muestra la entrada; la API responde 403.
  c) Otro ente: no ve el hallazgo («Hallazgo no encontrado»).
  d) Inmutabilidad: recomendaciones, avances e historia no se editan ni se borran; un hallazgo CERRADO no admite cambios.
  e) Cargo BORRADOR o de otro ejercicio como responsable: rechazado.

LIMPIEZA: no hace falta. Los hallazgos y su historia son registros permanentes por diseño.

DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Un hallazgo CERRADO no se reabre (la IR no lo define).
  - El responsable es el cargo (OD-CTL06-01). Las personas llegarán con ORG-06.
```
