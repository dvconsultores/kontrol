# Tarjeta UAT · Jerarquía del clasificador presupuestario (BUD-02)

**Use solo datos sintéticos.**

## Antes de empezar

- **Usuario:** uno con `gobierno_presupuesto:view` y `gobierno_presupuesto:manage`.
- **Datos:** un ejercicio en BORRADOR con el clasificador registrado (edición y procedencia).

## Ruta en el menú

Gobierno › Presupuesto › **Ejercicios presupuestarios** › el ejercicio › sección «Clasificador registrado por el ente».

## A. Un árbol válido de tres niveles

En «Nueva partida», con tipo Egreso, agregue:
1. `501`, nivel 1, sin código superior;
2. `501.01`, nivel 2, con código superior `501`;
3. `501.01.01`, nivel 3, con código superior `501.01`.

**Esperado:** las tres aparecen en «Partidas del clasificador», cada una con su código superior.

## B. Un padre que salta un nivel (el defecto corregido)

1. Agregue `501.01.02`, nivel 3, con código superior `501`.

**Esperado:**
- se rechaza, y bajo «Código superior» se lee «La partida padre «501» es de nivel 1; una partida de nivel 3 necesita un padre de nivel 2»;
- la partida no aparece en la lista.

## C. Corrección

1. Repita con código superior `501.01`.

**Esperado:** se acepta.

## D. Otros padres inválidos

Pruebe, una cada vez:
- nivel 3 con un padre de nivel 3;
- nivel 2 con un padre de nivel 3;
- nivel 1 con algún padre;
- un código superior que solo existe en el clasificador de otro ejercicio.

**Esperado:** todas se rechazan con un mensaje que dice el nivel encontrado y el esperado, o que el padre no existe en este clasificador.

## E. Importación CSV con un salto de nivel

1. Importe un CSV con estas filas, debajo de la cabecera `tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta`:
   - `EGRESO,502,Partida 502,1,,,`
   - `EGRESO,502.01,Partida 502.01,2,502,,`
   - `EGRESO,502.01.01,Partida 502.01.01,3,502,,`

**Esperado:**
- se rechaza el archivo con «Fila 4: La partida padre «502» es de nivel 1…»;
- no se importa ninguna fila, ni siquiera las dos válidas.

## F. Importación CSV válida

1. Importe el mismo archivo con la última fila corregida (`codigo_padre` = `502.01`).

**Esperado:** se importan las tres.

## Fuera de esta tarjeta

- No se reescriben ejercicios ya aprobados: sus clasificadores congelados se leen igual que antes.
- Sin cambios de permisos ni de pantallas.
