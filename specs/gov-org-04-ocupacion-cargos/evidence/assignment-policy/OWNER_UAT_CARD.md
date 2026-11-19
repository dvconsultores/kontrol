# Tarjeta UAT · Políticas de asignación (ORG-04)

## Antes de empezar

- Use un usuario del ente con permiso para **configurar** y otro distinto para **activar**. Activar y cerrar piden la verificación en dos pasos.
- El ente debe estar activo, con su estructura y sus cargos vigentes, y con actos eficaces emitidos por los cargos que se usen.
- En **Configuración del ente** compruebe el **nivel territorial**: la LOPPM solo se aplica si el ente es MUNICIPAL.

## Ruta en el menú

- Gobierno › **Políticas de asignación** (nueva)
- Gobierno › **Ocupación de cargos** › Asignaciones

## A. Crear y activar una política

1. Pulse **Nueva política**.
2. Elija la figura «Suplente».
3. Escriba código, nombre, fundamento y la fecha «Vigente desde».
4. Revise el recuadro **Pisos legales del régimen del ente**:
   - en un ente municipal aparece la LOPPM art. 87;
   - en otro ente no aparece.
5. Configure:
   - «Máximo de días»: opcional;
   - «Medio del acto»;
   - «Emisor del acto»: por cargo o por competencia;
   - **Exige autorización especial**, con nombre (por ejemplo, «Autorización del Consejo Directivo»), ámbito y «más de N días»;
   - competencias permitidas (solo delegaciones);
   - documentos exigidos al activar o revocar.
6. Pulse **Guardar borrador**.
7. En la ficha, con el usuario que activa, pulse **Activar**.

**Esperado:** estado «Vigente», historia con «Creada» y «Activada», y la sección «Regla aplicada» con los pisos y la autorización.

## B. Ente sin requisito municipal (el defecto corregido)

1. Con un ente **no municipal** y sin política de suplencia, vaya a **Asignaciones › Nueva asignación**.
2. Elija «Suplente», el suplente, el cargo suplido, el cargo de origen, el acto y una vigencia de 20 días.
3. Marque **Suple a la máxima autoridad**.

**Esperado:**
- la sección **Regla aplicada** dice «Regla legal base, sin política institucional»;
- **no** aparece «Autorización del Concejo» ni ningún campo de autorización;
- se guarda; al activarla, la ocupación del cargo muestra al suplente.

## C. Política con autorización especial

1. Con la política de A vigente, cree una suplencia de 20 días.

**Esperado:**
- aparece el campo «Autorización del Consejo Directivo»;
- si se deja vacío, se rechaza con «La autorización debe tener entre 5 y 200 caracteres.»;
- con el texto, se guarda y se puede activar.

## D. Delegación

1. Cree una delegación de atribuciones:
   - delegante: el cargo de la asignación;
   - delegado: el cargo de origen, que depende de él;
   - competencias del cargo;
   - acto **publicado en gaceta**;
   - rendición de cuentas.
2. Active la delegación.

**Esperado:**
- si la política limita las competencias permitidas, una competencia fuera de la lista se rechaza;
- si la política prohíbe la avocación, la ficha no ofrece «Avocar» y la regla dice «No admite avocación».

## E. Encargaduría o designación

1. Cree una política de encargaduría con emisor «Cargo» y elija el cargo emisor.
2. Registre una encargaduría con un acto de otro cargo.
3. Vuelva a registrarla con un acto del cargo fijado.

**Esperado:** con el acto de otro cargo se rechaza («El acto debe emitirlo el cargo que fija la política»); con el acto del cargo fijado se acepta.

## F. Versiones

1. En la política vigente pulse **Nueva versión** y cambie un límite (por ejemplo, máximo de 15 días).
2. Active la nueva versión.

**Esperado:**
- la versión anterior queda «Cerrada (sustituida)»;
- la asignación ya activa sigue mostrando «Política … v1» y «Congelada al activarse: no cambia aunque cambie la política.»;
- una asignación nueva muestra la v2.

## G. Revocación o finalización

1. En una asignación activa, pulse **Revocar** (con acto) o **Finalizar**.

**Esperado:**
- la historia registra el cambio;
- desde la fecha efectiva, la ocupación del cargo ya no la muestra;
- si la política exige un documento de revocación, sin él se rechaza.
