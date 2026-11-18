# Tarjeta UAT · Políticas de comisión (PROC-02, PROC-07 y PROC-08)

## Antes de empezar

- Necesita un usuario del ente con permiso para **configurar** comisiones y otro para **activar**. Activar pide la verificación en dos pasos.
- El ente debe tener su estructura y sus cargos vigentes, al menos 8 funcionarios activos y un acto publicado en Gaceta para crear la comisión.

## Ruta en el menú

**Gobierno · Contrataciones → Políticas de comisión**

## Pasos

### Crear y activar la política

1. Pulse **Nueva política**.
2. Rellene estos datos:
   - código y nombre;
   - tipo de comisión: «Permanente»;
   - base normativa: «Ley de Contrataciones Públicas, art. 14»;
   - fundamento;
   - fecha «Desde»: hoy;
   - «Máximo de principales»: 3.
3. En **Quórum**, elija «Mayoría simple».
4. En **Decisión**, elija «Mayoría calificada» con 2/3, sobre los miembros con voto.
5. Pulse **Añadir requisito**:
   - etiqueta: «Principal técnico»;
   - tipo: «Área de la comisión»;
   - área: «Técnica»;
   - mínimo: 1.
6. Pulse **Guardar borrador**.
7. En la ficha, con el usuario que activa, pulse **Activar**.

### Formar la comisión

8. Vaya a **Comisiones → Nueva comisión**, elija la política que acaba de crear y guarde.
9. En la ficha de la comisión, revise la sección **Regla aplicada**.
10. Añada 5 miembros principales con sus suplentes, más el secretario y su suplente.
11. Retire dos principales para dejar 3.
12. Pulse **Designar presidente** en uno de los principales.
13. Con el usuario que activa, pulse **Activar**.

### Revisar la historia y el consumo en PROC-07 y PROC-08

14. Vuelva a la política y revise **Historia** y **Versiones**.
15. Abra un expediente que tenga vinculada esa comisión y entre en **Evaluación** y en **Decisión**.

## Resultados esperados

- **Política:**
  - la lista muestra la política con «v1» y su estado;
  - al elegir la base LCP, las exigencias del piso legal quedan marcadas y bloqueadas.
- **Activación:** la política pasa a «Vigente» y la historia dice «Creada» y «Activada».
- **Comisión:**
  - «Regla aplicada» muestra el código de la política y «Se congelará al activar la comisión.»;
  - al activarla dice «Congelada al activarse: no cambia aunque cambie la política»;
  - el principal elegido aparece con la marca «Preside».
- **Expediente:** en Evaluación y en Decisión aparece «Regla: …» con la política. El quórum que se exige es el de la política, no uno fijo.

## Caso negativo

- Con 5 principales, la comisión **no se activa**. La ficha muestra «Se admiten como máximo 3 miembros principales; hay 5 (política …)».
- Si intenta activar una política LCP sin fundamento, la ficha muestra «No se puede activar la política» con el motivo.

## Comprobación de PROC-07 (apertura de ofertas)

- En la apertura, el contador dice «requerido N (Mayoría simple)», con el valor de la regla.
- Un miembro con una inhibición **aceptada** en ese expediente aparece deshabilitado; en su lugar actúa su suplente.
- En un expediente que declaró «no interviene comisión», la apertura la marcan los **responsables del expediente** y no hay quórum.

## Comprobación de PROC-08 (recomendación)

- Para recomendar, la mayoría que se exige es la de la política. Con la decisión 2/3 y 3 principales, una sola firma no basta y el sistema responde «Sin mayoría…».
- Sin comisión, firman los responsables del expediente.
