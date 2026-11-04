# OWNER UAT CARD · GOV-CTL-04 · CTL-04 «Consulta y muestreo read-only del auditor interno/externo» (GOV-CTL-005) + FIND-ORG07-01

```
MÓDULO: Gobierno · PROCESO: CTL-04 Auditoría institucional · ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Auditoría institucional  (ruta /gobierno/auditoria)
ROL A USAR: un usuario con gobierno_auditoria:view y gobierno_auditoria:sample. En la base de QA, el administrador «con todo»
            ADMIN + FUNCIONAL_COMPLETO los tiene (la migración 0069 se los concede a FUNCIONAL_COMPLETO; ADMIN no los recibe por ser ADMIN).
            Negativas: un usuario con solo gobierno_auditoria:view, y otro con solo audit:view.
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - Actividad de Gobierno en el ente: ORG-01 ente ACTIVO, ORG-02 estructura VIGENTE y ORG-03 al menos un cargo VIGENTE con sus
    competencias (cada alta deja eventos en la bitácora).
PASOS Y RESULTADO ESPERADO:
  1. Abra Gobierno › Auditoría institucional. Verá la nota «Vista de solo lectura…», el total «N eventos en la población», la tabla y
     «Muestras guardadas».
  2. FILTRAR: en «Proceso» elija «ORG-03 · Cargos y competencias» y acote «Desde» y «Hasta» al mes en curso: solo quedan eventos de cargos.
     «Buscar» filtra por motivo, usuario o acción al pulsar el botón. Un «Desde» posterior a «Hasta» muestra «Rango de fechas inválido».
  3. EVIDENCIA: «Ver evidencia» en un alta de cargo abre el panel: fecha y hora, proceso, acción, usuario, motivo, correlación, «Antes» y
     «Después» (solo claves seguras), documentos vinculados (cada uno enlaza a su ficha si usted tiene permiso de documentos) e «Ir al objeto», que lleva a la ficha del cargo. «Cerrar la evidencia» lo oculta.
  4. MUESTRA ALEATORIA: «Registrar muestra» → título, criterio y justificación; medio «Selección aleatoria», tamaño 3, semilla 12345.
     Al registrar se abre la muestra MU-<año>-<nnnn> con la semilla, la población, las 3 partidas y su definición.
  5. REPRODUCIBLE: vuelva, use los mismos filtros y registre otra muestra con la misma semilla y el mismo tamaño: salen las mismas 3 partidas.
     Si deja la semilla vacía, el sistema la genera y la muestra la enseña.
  6. MUESTRA ESPECÍFICA: marque 2 casillas de la tabla («2 partidas marcadas»), elija «Partidas específicas» y registre: la muestra tiene esas 2.
  7. TODAS: con un filtro estrecho, «Todas las partidas» guarda la población completa (hasta 2000 eventos).
  8. EXPORTAR: en la muestra, «Exportar CSV» descarga muestra-<código>.csv. Empieza por la definición (# titulo, # metodo, # semilla,
     # poblacion, # tamano, # criterio, # justificacion, # filtros, # registrada_por, # registrada_en) y sigue con la tabla de partidas.
     Sistema › Auditoría registra «Muestra de auditoría exportada».
  9. FIND-ORG07-01 (DOC-02): registre un acto fechado cuando el cargo tenía la competencia, aunque hoy ya no la tenga: se acepta. Uno
     fechado antes de que el cargo la tuviera se rechaza con «La competencia indicada no estaba vigente en el cargo en la fecha del acto».
PRUEBA NEGATIVA:
  a) Usuario con solo gobierno_auditoria:view: ve la población, la evidencia y las muestras, pero no «Registrar muestra» ni las casillas.
  b) Usuario con solo audit:view: el menú no muestra «Auditoría institucional»; la API responde 403.
  c) Otro ente: no ve los eventos ni las muestras de este («no encontrado»).
  d) Inmutabilidad: la muestra no tiene botones de editar ni borrar, y la API rechaza cambiarla o borrarla (405).
  e) Población vacía (filtros sin resultados) o tamaño mayor que la población: el registro lo rechaza con el mensaje correspondiente.
LIMPIEZA: no hace falta. La consulta no escribe nada; las muestras son papeles de trabajo permanentes por diseño (OD-CTL04-02).
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - CTL-01 (segregación de funciones) y CTL-02 (auditoría de consultas) siguen sin abrir, como se acordó.
  - FIND-ORG07-02 (LOW, cobertura multinavegador de pruebas no gubernamentales) sigue OPEN.
```
