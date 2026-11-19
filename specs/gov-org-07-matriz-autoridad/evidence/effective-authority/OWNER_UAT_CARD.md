# Tarjeta UAT · Matriz de autoridad efectiva (ORG-07)

**Use solo datos sintéticos.**

## Antes de empezar

- **Usuarios:**
  - uno con «Matriz de autoridad» y «Ocupación de cargos» (consulta, registro y activación);
  - un segundo usuario que active las asignaciones, porque quien registra una asignación no la puede activar;
  - un tercero con solo `gobierno_autoridad:view`, para la parte F.
- **Estructura del ejercicio vigente**, con un cargo **A** que tenga una competencia (por ejemplo, Aprobar · Contrataciones con un límite), en una unidad superior, y otro cargo **B** en una unidad que dependa de ella.
- **Funcionarios:** tres de prueba, y actos eficaces para las asignaciones.

## Ruta en el menú

- Gobierno › **Matriz de autoridad**
- Gobierno › **Ocupación de cargos** (para crear las asignaciones)

## A. Autoridad base

1. Abra la matriz y elija la fecha de hoy.
2. Busque el cargo A.

**Esperado:**
- la columna «Ejerce» dice «Sin ocupante» y «Cargo»;
- si A tiene titular, muestra su nombre y «Cargo».

## B. Delegación

1. En Ocupación de cargos, registre una **delegación de atribuciones** de A al titular de B, solo de Aprobar · Contrataciones, y actívela con el otro usuario.
2. Vuelva a la matriz.

**Esperado:**
- aparece una **fila nueva** de A con la persona delegada, «Delegación de atribuciones» y «Desde …»;
- el límite es el de la delegación;
- la fila del cargo sigue, porque el delegante conserva la titularidad;
- en «Ver el detalle» de A, la sección «Autoridad efectiva al …» muestra la fuente, el acto («Resolución …» y «Eficaz desde …»), el cargo de origen y el código de la asignación.

## C. Suplencia

1. Active una **suplencia** del titular de otro cargo, con fecha de inicio y de fin.
2. En la matriz, elija una fecha dentro de la suplencia.

**Esperado:**
- en las filas de ese cargo aparece el suplente, «Suplente», «Sustituye a {titular}» y la vigencia;
- hay **una** fila por competencia, sin duplicados.

## D. Histórico

Consulte tres fechas: antes, durante y después de la suplencia.

**Esperado:** antes y después muestran al titular; durante, al suplente. Una delegación o suplencia **revocada o finalizada** desaparece después de su fin y sigue apareciendo en las fechas en que estuvo vigente.

## E. CSV

Con la delegación vigente, pulse **Exportar CSV**.

**Esperado:**
- el archivo tiene las mismas filas que la pantalla;
- la fila delegada lleva `origen` DELEGACION_ATRIBUCIONES, la figura, la persona, el código de la asignación, sus fechas, el acto y el cargo de origen.

## F. Personas reservadas

Entre con el usuario que solo tiene `gobierno_autoridad:view`.

**Esperado:**
- las mismas filas, fuentes, actos y vigencias, pero la persona dice «Reservado», en pantalla y en el CSV;
- buscar por el nombre de la persona no devuelve filas.
