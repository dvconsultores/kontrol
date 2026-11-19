# Tarjeta UAT · Políticas de actas de entrega (CTL-09)

**Use solo datos sintéticos.**

## Antes de empezar

- **Usuarios:** uno con permiso para configurar (`gobierno_actas:configure`), otro para activar (`gobierno_actas:activate`, pide la verificación en dos pasos) y uno para levantar actas (`gobierno_actas:manage`).
- **Ente:** activo, con su nivel territorial en «Configuración del ente».
- **Ocupación de cargos:** al menos dos titulares activos, uno de ellos en el cargo de la máxima autoridad, y anote el **código** de ese cargo. Además, otros funcionarios que reciban.

## Ruta en el menú

- Gobierno › **Políticas de actas** (nueva)
- Gobierno › **Actas de entrega** › Nueva acta

## A. Política

1. En «Políticas de actas», pulse **Nueva política**.
2. Escriba código, nombre, fundamento y «Vigente desde».
3. Revise el **Catálogo legal (N34)**:
   - el art. 11 «rige en toda acta»;
   - en un ente municipal, el art. 17 aparece como declarable;
   - en uno estadal, el art. 16.
4. Configure:
   - el **Código del cargo de máxima autoridad**;
   - si quiere, testigos en la entrega, un patrón de numeración (pulse **Vista previa**), requisitos del ente y plazos internos;
   - de momento **no** declare el art. 17.
5. Pulse **Guardar borrador**.
6. Con el usuario que activa, pulse **Activar**.

**Esperado:**
- estado «Vigente» e historia «Creada» y «Activada»;
- la «Regla aplicada» de un acta de la entidad muestra la norma, los anexos A11 y los plazos legales.

**Negativas:**
- un plazo interno mayor que el legal se rechaza («no puede superar el legal…»);
- un código de requisito `A17_9` se rechaza (reservado);
- en un ente municipal, el art. 16 no se puede declarar.

## B. Ente municipal sin el art. 17 declarado (el defecto corregido)

1. **Nueva acta** de quien ocupa el cargo de máxima autoridad.

**Esperado:**
- en «Regla aplicada» aparecen los anexos **A11** y ninguno **A17**;
- aparece el aviso: «Si el acta corresponde a una Alcaldía o Dirección de hacienda municipal, declárelo en la política de actas (N34 art. 17).»

2. Cree el acta y resuelva las pendientes con documentos o con la constancia del art. 19.
3. Pulse **Suscribir acta**.

**Esperado:** se suscribe sin pedir anexos A17.

## C. A17 aplicable

1. En la política vigente pulse **Nueva versión**.
2. En «Supuestos declarados», añada «N34 art. 17 · Alcaldía o hacienda municipal» con alcance **Entidad**. También puede declararlo para la **unidad** de la Dirección de hacienda.
3. Guarde y active.
4. **Nueva acta** de la máxima autoridad (otro titular).

**Esperado:**
- «Anexos exigidos» incluye A17_1 a A17_5, con su fuente («N34 art. 17…»);
- **Suscribir acta** está deshabilitado y el aviso de pendientes lista los A17.

5. Resuelva los anexos y suscriba.

**Esperado:** se suscribe.

## D. Ocupación de cargos

En la ficha del acta, revise **Responsables**.

**Esperado:**
- «Quien entrega» muestra el cargo y la figura del saliente, que ejerce el día del corte;
- «Quien recibe» dice «Sucesor en el cargo» o «Designado para recibir»;
- si elige una fecha de corte en la que el saliente ya no ejercía, el acta se rechaza.

## E. Versiones

Abra el acta de B.

**Esperado:**
- sigue mostrando la regla de la **v1**, sin A17, y «Congelada al suscribir: no cambia aunque cambie la política.»;
- el acta de C muestra la **v2**.

## F. Historia

**Esperado:**
- la ficha de cada política muestra los eventos («Creada», «Activada», «Cerrada (sustituida)», «Nueva versión») y sus versiones;
- la ficha de cada acta muestra su historial y la sección **Plazos**: los legales dicen «Sin calendario hábil oficial» o «Registrado»; los internos, en días continuos, muestran su vencimiento y su estado.
